//! Daemon seam: CORS, dual breach JSON, ephemeral chat overrides, concurrent SSE.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use async_trait::async_trait;
use axum::body::Body;
use axum::http::{HeaderMap, Request, StatusCode};
use axum::response::Response;
use bytes::Bytes;
use futures_util::stream;
use http_body_util::BodyExt;
use sf_kernels::{
    AlignedVec1024, DomainHypercubeLock, LockSpec, NoiseBitmask1024, MAX_TOPK, NOISE_MASK_WORDS,
};
use sf_proxy::{
    router, router_with_cors, BatchEmbedderClient, CorsAllow, InputNormalizer, MockBatchEmbedder,
    MockUpstreamForwarder, ProxyAppState, ReqwestChatForwarder, UpstreamLlmForwarder,
};
use sf_storage::HotRegistry;
use tower::ServiceExt;

fn unit_axis() -> AlignedVec1024 {
    let mut vector = AlignedVec1024::zeros();
    vector.data[0] = 1.0;
    vector
}

fn python_lock(l1_threshold: f32) -> DomainHypercubeLock {
    let centroid = unit_axis();
    let mut lo = AlignedVec1024::zeros();
    let mut hi = AlignedVec1024::zeros();
    lo.data.fill(-0.1);
    hi.data.fill(1.1);
    let mut top_k = [0u16; MAX_TOPK];
    for (idx, slot) in top_k.iter_mut().enumerate().take(4) {
        *slot = u16::try_from(idx).unwrap();
    }
    DomainHypercubeLock::from_spec(LockSpec {
        domain_id: "python".to_string(),
        centroid,
        lo,
        hi,
        epsilon: 0.0,
        noise_mask: NoiseBitmask1024::new_bge_m3_default(),
        top_k_indices: top_k,
        top_k_len: 4,
        quorum_k: 103,
        l1_cosine_threshold: l1_threshold,
        l2_clause_threshold: 0.5,
        polarity: 0,
        domain_version: 1,
    })
}

fn state(
    lock: DomainHypercubeLock,
    upstream: Arc<dyn UpstreamLlmForwarder>,
) -> (Arc<HotRegistry>, Arc<ProxyAppState>) {
    let centroid = lock.centroid;
    let registry = Arc::new(HotRegistry::from_locks([lock]));
    let app_state = Arc::new(ProxyAppState {
        registry: Arc::clone(&registry),
        embedder: Arc::new(MockBatchEmbedder {
            pass_vector: centroid,
            breach_vector: AlignedVec1024::zeros(),
            centroids: std::collections::HashMap::new(),
        }),
        upstream: Arc::clone(&upstream),
        mock_upstream: upstream,
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
    });
    (registry, app_state)
}

fn app(lock: DomainHypercubeLock) -> axum::Router {
    let (_registry, app_state) = state(lock, Arc::new(MockUpstreamForwarder));
    router(app_state)
}

async fn oneshot(app: axum::Router, request: Request<Body>) -> (StatusCode, HeaderMap, String) {
    let response = app.oneshot(request).await.unwrap();
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, headers, String::from_utf8(bytes.to_vec()).unwrap())
}

#[tokio::test]
async fn preflight_uses_configured_origin_on_both_routes() {
    let allow = CorsAllow::parse(Some("https://studio.example")).expect("origin");
    let (_registry, app_state) = state(python_lock(0.5), Arc::new(MockUpstreamForwarder));
    let app = router_with_cors(app_state, allow);
    for path in ["/v1/chat/completions", "/api/v1/chat"] {
        let (status, headers, body) = oneshot(
            app.clone(),
            Request::builder()
                .method("OPTIONS")
                .uri(path)
                .header("origin", "https://studio.example")
                .header("access-control-request-method", "POST")
                .header("access-control-request-headers", "content-type")
                .body(Body::empty())
                .unwrap(),
        )
        .await;
        assert_eq!(status, StatusCode::OK, "{path} {body}");
        assert_eq!(
            headers
                .get("access-control-allow-origin")
                .and_then(|value| value.to_str().ok()),
            Some("https://studio.example"),
            "{path}"
        );
        let methods = headers
            .get("access-control-allow-methods")
            .and_then(|value| value.to_str().ok())
            .unwrap_or("");
        assert!(methods.contains("POST"), "{path} {methods}");
    }
}

#[tokio::test]
async fn unset_origin_allows_any() {
    let allow = CorsAllow::parse(None).expect("fallback");
    assert!(matches!(allow, CorsAllow::Any));
    let (_registry, app_state) = state(python_lock(0.5), Arc::new(MockUpstreamForwarder));
    let (status, headers, _) = oneshot(
        router_with_cors(app_state, allow),
        Request::builder()
            .method("OPTIONS")
            .uri("/api/v1/chat")
            .header("origin", "https://other.example")
            .header("access-control-request-method", "POST")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        headers
            .get("access-control-allow-origin")
            .and_then(|value| value.to_str().ok()),
        Some("*")
    );
}

#[test]
fn cors_parse_rejects_a_header_illegal_origin() {
    let parsed = CorsAllow::parse(Some("https://studio.example\r\nX-Injected: 1"));
    assert!(parsed.is_err(), "{parsed:?}");
    assert!(matches!(
        CorsAllow::parse(Some("*")).unwrap(),
        CorsAllow::Any
    ));
    assert!(matches!(
        CorsAllow::parse(Some("  ")).unwrap(),
        CorsAllow::Any
    ));
}

#[tokio::test]
async fn dual_routes_keep_distinct_breach_json() {
    let app = app(python_lock(0.5));
    let (chat_status, _, chat_body) = oneshot(
        app.clone(),
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .header("origin", "https://studio.example")
            .body(Body::from(
                r#"{"messages":[{"role":"user","content":"BREACH"}],"domain_id":"python"}"#,
            ))
            .unwrap(),
    )
    .await;
    assert_eq!(chat_status, StatusCode::FORBIDDEN, "{chat_body}");
    let chat: serde_json::Value = serde_json::from_str(&chat_body).unwrap();
    assert_eq!(chat["decision"], "BREACH");
    assert_eq!(chat["failing_tier"], "L1_CENTROID_COSINE");
    assert_eq!(chat["l1"]["passed"], false);
    assert!(chat.get("error").is_none(), "{chat_body}");

    let (v1_status, v1_headers, v1_body) = oneshot(
        app,
        Request::builder()
            .method("POST")
            .uri("/v1/chat/completions")
            .header("content-type", "application/json")
            .header("origin", "https://studio.example")
            .header("x-semantic-domain", "python")
            .body(Body::from(
                r#"{"messages":[{"role":"user","content":"BREACH"}]}"#,
            ))
            .unwrap(),
    )
    .await;
    assert_eq!(v1_status, StatusCode::FORBIDDEN, "{v1_body}");
    assert!(v1_body.contains("SEMANTIC_CONTAINMENT_BREACH"), "{v1_body}");
    assert!(v1_body.contains("L1_CATEGORICAL_COSINE"), "{v1_body}");
    assert!(!v1_body.contains("L1_CENTROID_COSINE"), "{v1_body}");
    assert_eq!(
        v1_headers
            .get("access-control-allow-origin")
            .and_then(|value| value.to_str().ok()),
        Some("*")
    );
}

#[tokio::test]
async fn chat_override_does_not_mutate_the_registry_lock() {
    let (registry, app_state) = state(python_lock(1.1), Arc::new(MockUpstreamForwarder));
    let app = router(app_state);
    let (pass_status, pass_headers, pass_body) = oneshot(
        app.clone(),
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .body(Body::from(
                r#"{"messages":[{"role":"user","content":"hello kernel"}],"domain_id":"python","overrides":{"l1_threshold":0.5}}"#,
            ))
            .unwrap(),
    )
    .await;
    assert_eq!(pass_status, StatusCode::OK, "{pass_body}");
    assert!(
        pass_headers
            .get("content-type")
            .and_then(|value| value.to_str().ok())
            .unwrap_or("")
            .starts_with("text/event-stream"),
        "{pass_headers:?}"
    );
    assert!(pass_body.contains("chat.completion.chunk"), "{pass_body}");

    let stored = registry.get("python").expect("python lock");
    assert_eq!(stored.l1_cosine_threshold.to_bits(), 1.1f32.to_bits());

    let (breach_status, _, breach_body) = oneshot(
        app,
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .body(Body::from(
                r#"{"messages":[{"role":"user","content":"hello kernel"}],"domain_id":"python"}"#,
            ))
            .unwrap(),
    )
    .await;
    assert_eq!(breach_status, StatusCode::FORBIDDEN, "{breach_body}");
    let breach: serde_json::Value = serde_json::from_str(&breach_body).unwrap();
    assert_eq!(breach["failing_tier"], "L1_CENTROID_COSINE");
    let threshold = breach["l1"]["threshold"].as_f64().expect("threshold") as f32;
    assert_eq!(threshold.to_bits(), 1.1f32.to_bits());
}

struct LaneEcho {
    current: Arc<AtomicUsize>,
    max_inflight: Arc<AtomicUsize>,
}

#[async_trait]
impl UpstreamLlmForwarder for LaneEcho {
    async fn forward_chat_completion(
        &self,
        _headers: &HeaderMap,
        raw_body: Bytes,
    ) -> Result<Response, String> {
        let payload: serde_json::Value =
            serde_json::from_slice(&raw_body).map_err(|err| err.to_string())?;
        let lane = payload["messages"]
            .as_array()
            .and_then(|messages| {
                messages
                    .iter()
                    .rev()
                    .find(|message| message["role"] == "user")
            })
            .and_then(|message| message["content"].as_str())
            .unwrap_or("")
            .to_string();
        let current = Arc::clone(&self.current);
        let max_inflight = Arc::clone(&self.max_inflight);
        let first = format!("data: A-{lane}\n\n");
        let second = format!("data: B-{lane}\n\n");
        let stream = stream::unfold(0u8, move |step| {
            let first = first.clone();
            let second = second.clone();
            let current = Arc::clone(&current);
            let max_inflight = Arc::clone(&max_inflight);
            async move {
                match step {
                    0 => {
                        let now = current.fetch_add(1, Ordering::SeqCst) + 1;
                        max_inflight.fetch_max(now, Ordering::SeqCst);
                        tokio::time::sleep(Duration::from_millis(30)).await;
                        Some((Ok::<Bytes, std::io::Error>(Bytes::from(first)), 1u8))
                    }
                    1 => {
                        tokio::time::sleep(Duration::from_millis(30)).await;
                        current.fetch_sub(1, Ordering::SeqCst);
                        Some((Ok(Bytes::from(second)), 2u8))
                    }
                    _ => None,
                }
            }
        });
        Response::builder()
            .status(StatusCode::OK)
            .header(axum::http::header::CONTENT_TYPE, "text/event-stream")
            .body(Body::from_stream(stream))
            .map_err(|err| err.to_string())
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn concurrent_chat_sse_lanes_stay_unmixed() {
    const LANES: usize = 16;
    let current = Arc::new(AtomicUsize::new(0));
    let max_inflight = Arc::new(AtomicUsize::new(0));
    let echo = Arc::new(LaneEcho {
        current: Arc::clone(&current),
        max_inflight: Arc::clone(&max_inflight),
    });
    let (_registry, app_state) = state(python_lock(0.5), echo);
    let app = router(app_state);
    let mut tasks = Vec::with_capacity(LANES);
    for lane in 0..LANES {
        let app = app.clone();
        tasks.push(tokio::spawn(async move {
            let body = format!(
                r#"{{"messages":[{{"role":"user","content":"lane-{lane:02}"}}],"domain_id":"python","upstream":{{"provider":"mock"}}}}"#
            );
            let (status, headers, text) = oneshot(
                app,
                Request::builder()
                    .method("POST")
                    .uri("/api/v1/chat")
                    .header("content-type", "application/json")
                    .body(Body::from(body))
                    .unwrap(),
            )
            .await;
            (lane, status, headers, text)
        }));
    }
    for task in tasks {
        let (lane, status, headers, text) = task.await.unwrap();
        assert_eq!(status, StatusCode::OK, "lane-{lane} {text}");
        assert!(
            headers
                .get("content-type")
                .and_then(|value| value.to_str().ok())
                .unwrap_or("")
                .starts_with("text/event-stream"),
            "lane-{lane}"
        );
        assert!(
            text.contains(&format!("data: A-lane-{lane:02}\n")),
            "{text}"
        );
        assert!(
            text.contains(&format!("data: B-lane-{lane:02}\n")),
            "{text}"
        );
        let marker_at = text.find(&format!("A-lane-{lane:02}")).unwrap();
        let end_at = text.find(&format!("B-lane-{lane:02}")).unwrap();
        assert!(marker_at < end_at, "{text}");
        for other in 0..LANES {
            if other == lane {
                continue;
            }
            assert!(
                !text.contains(&format!("lane-{other:02}")),
                "lane-{lane:02} mixed with lane-{other:02}: {text}"
            );
        }
    }
    assert!(
        max_inflight.load(Ordering::SeqCst) > 1,
        "streams never overlapped"
    );
}

#[tokio::test]
async fn chat_mock_upstream_does_not_forward_to_unreachable_network_upstream() {
    let lock = python_lock(0.5);
    let centroid = lock.centroid;
    let registry = Arc::new(HotRegistry::from_locks([lock]));

    // Unreachable network upstream in app_state.upstream:
    let unreachable_upstream = Arc::new(ReqwestChatForwarder::new("http://127.0.0.1:9"));
    let app_state = Arc::new(ProxyAppState {
        registry: Arc::clone(&registry),
        embedder: Arc::new(MockBatchEmbedder {
            pass_vector: centroid,
            breach_vector: AlignedVec1024::zeros(),
            centroids: std::collections::HashMap::new(),
        }),
        upstream: unreachable_upstream,
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
    });
    let app = router(app_state);

    let (status, headers, text) = oneshot(
        app,
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .body(Body::from(
                r#"{"messages":[{"role":"user","content":"pass prompt"}],"upstream":{"provider":"mock"}}"#,
            ))
            .unwrap(),
    )
    .await;

    assert_eq!(status, StatusCode::OK, "text: {text}");
    assert!(
        headers
            .get("content-type")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("")
            .starts_with("text/event-stream"),
        "headers: {headers:?}"
    );
    assert!(
        text.contains(r#"data: {"object":"chat.completion.chunk","mock":true}"#),
        "text: {text}"
    );
}

fn empty_python_receta(primary: &DomainHypercubeLock) -> DomainHypercubeLock {
    let mut pair = primary.clone();
    pair.domain_id = "python_receta".to_string();
    pair.noise_mask = NoiseBitmask1024 {
        words: [0; NOISE_MASK_WORDS],
    };
    pair.quorum_k = 1;
    pair
}

fn rejecting_python_receta(primary: &DomainHypercubeLock) -> DomainHypercubeLock {
    let mut pair = empty_python_receta(primary);
    pair.noise_mask.words[0] = 1;
    pair.lo_dilated.data[0] = 5.0;
    pair.hi_dilated.data[0] = 6.0;
    pair
}

fn app_with_pair(
    embedder: Arc<dyn BatchEmbedderClient>,
    pair: DomainHypercubeLock,
) -> axum::Router {
    let primary = python_lock(0.5);
    let registry = Arc::new(HotRegistry::from_locks([primary, pair]));
    router(Arc::new(ProxyAppState {
        registry,
        embedder,
        upstream: Arc::new(MockUpstreamForwarder),
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
    }))
}

fn chat_body(content: &str) -> Body {
    Body::from(format!(
        r#"{{"messages":[{{"role":"user","content":"{content}"}}],"domain_id":"python","upstream":{{"provider":"mock"}}}}"#
    ))
}

#[tokio::test]
async fn mock_embedder_skips_pairwise_unless_the_prompt_is_the_breach_sentinel() {
    let primary = python_lock(0.5);
    let centroid = primary.centroid;
    let app = app_with_pair(
        Arc::new(MockBatchEmbedder {
            pass_vector: centroid,
            breach_vector: centroid,
            centroids: std::collections::HashMap::new(),
        }),
        rejecting_python_receta(&primary),
    );
    let (pass_status, _, pass_body) = oneshot(
        app.clone(),
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .body(chat_body(
                "Cómo implementar un generador con yield en Python",
            ))
            .unwrap(),
    )
    .await;
    assert_eq!(pass_status, StatusCode::OK, "{pass_body}");
    assert!(pass_body.contains("chat.completion.chunk"), "{pass_body}");

    let (breach_status, _, breach_body) = oneshot(
        app,
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .body(chat_body("BREACH"))
            .unwrap(),
    )
    .await;
    assert_eq!(breach_status, StatusCode::FORBIDDEN, "{breach_body}");
    let breach: serde_json::Value = serde_json::from_str(&breach_body).expect(&breach_body);
    assert_eq!(
        breach["error"]["telemetry"]["failing_tier"],
        "L3_PAIRWISE_QUORUM"
    );
    assert_eq!(
        breach["error"]["telemetry"]["breaching_pair_lock"],
        "python_receta"
    );
}

struct FixedEmbedder(AlignedVec1024);

#[async_trait]
impl BatchEmbedderClient for FixedEmbedder {
    async fn embed_batch_f32(&self, texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
        Ok(texts.iter().map(|_| self.0).collect())
    }
}

#[tokio::test]
async fn empty_discriminative_mask_does_not_false_breach_an_in_domain_prompt() {
    let primary = python_lock(0.5);
    let app = app_with_pair(
        Arc::new(FixedEmbedder(primary.centroid)),
        empty_python_receta(&primary),
    );
    let (status, _, body) = oneshot(
        app,
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .body(chat_body("hello kernel"))
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{body}");
}

#[tokio::test]
async fn non_mock_embedder_still_fail_closes_a_discriminative_pairwise_lock() {
    let primary = python_lock(0.5);
    let app = app_with_pair(
        Arc::new(FixedEmbedder(primary.centroid)),
        rejecting_python_receta(&primary),
    );
    let (status, _, body) = oneshot(
        app,
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .body(chat_body("hello kernel"))
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{body}");
    assert!(body.contains("L3_PAIRWISE_QUORUM"), "{body}");
}

fn tight_around_centroid(mut lock: DomainHypercubeLock) -> DomainHypercubeLock {
    for dim in 0..lock.centroid.data.len() {
        let center = lock.centroid.data[dim];
        lock.lo_dilated.data[dim] = center - 0.02;
        lock.hi_dilated.data[dim] = center + 0.02;
    }
    lock
}

#[tokio::test]
async fn permutation_noise_breaches_spectral_quorum_on_an_in_domain_embedding() {
    let primary = tight_around_centroid(python_lock(0.5));
    let centroid = primary.centroid;
    let app = router(Arc::new(ProxyAppState {
        registry: Arc::new(HotRegistry::from_locks([primary])),
        embedder: Arc::new(FixedEmbedder(centroid)),
        upstream: Arc::new(MockUpstreamForwarder),
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
    }));
    let (status, _, body) = oneshot(
        app,
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .body(chat_body(
                "Python asyncio event loop optimization with PERMUTATION_NOISE coordinate drift.",
            ))
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{body}");
    let breach: serde_json::Value = serde_json::from_str(&body).expect(&body);
    assert_eq!(breach["failing_tier"], "L3_SPECTRAL_QUORUM", "{body}");
    assert_eq!(breach["l3"]["passed"], false);
}

#[tokio::test]
async fn stored_python_lock_spectral_marker_stays_above_l1_and_misses_quorum() {
    let uri = concat!(env!("CARGO_MANIFEST_DIR"), "/../../data/sf-lancedb");
    if !std::path::Path::new(uri)
        .join("domain_hypercubes.lance")
        .exists()
    {
        return;
    }
    let registry = sf_storage::HotRegistry::load_from_lancedb(uri, sf_storage::TABLE_NAME)
        .await
        .expect("registry");
    let lock = registry.get("python").expect("python");
    let vector = sf_proxy::project_spectral_drift(&lock);
    let cosine = sf_kernels::cosine_similarity_1024(&vector, &lock.centroid);
    let l3 = sf_kernels::evaluate_l3_gate(
        &vector,
        &lock,
        sf_kernels::L3InspectionMode::ModeCSpectralQuorum,
        0,
    );
    assert!(
        cosine >= lock.l1_cosine_threshold,
        "cosine {cosine} threshold {}",
        lock.l1_cosine_threshold
    );
    assert!(
        !l3.passed,
        "votes {}/{}",
        l3.affirmative_votes, l3.required_votes
    );
    assert!(l3.affirmative_votes < lock.quorum_k);
}

fn denylist_python_lock() -> DomainHypercubeLock {
    let mut lock = python_lock(1.1);
    lock.l2_clause_threshold = 1.1;
    lock.polarity = 1;
    // Half-width is 0, so epsilon -0.05 swaps lo_dilated above hi_dilated.
    lock.lo_dilated.data.fill(0.0);
    lock.hi_dilated.data.fill(0.0);
    lock
}

fn chat_with_overrides(overrides: &str) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri("/api/v1/chat")
        .header("content-type", "application/json")
        .body(Body::from(format!(
            r#"{{"messages":[{{"role":"user","content":"hello kernel"}}],"domain_id":"python","overrides":{overrides}}}"#
        )))
        .unwrap()
}

#[tokio::test]
async fn invalid_overrides_are_rejected_before_dilation() {
    let app = app(denylist_python_lock());
    let cases = [
        (r#"{"epsilon":-0.05}"#, "epsilon"),
        (r#"{"epsilon":NaN}"#, "epsilon"),
        (r#"{"epsilon":Infinity}"#, "epsilon"),
        (r#"{"epsilon":-Infinity}"#, "epsilon"),
        (r#"{"epsilon":1e999}"#, "epsilon"),
        (r#"{"l1_threshold":NaN}"#, "l1_threshold"),
        (r#"{"l2_threshold":Infinity}"#, "l2_threshold"),
        (r#"{"l1_threshold":1.1}"#, "l1_threshold"),
        (r#"{"l1_threshold":-1.1}"#, "l1_threshold"),
        (r#"{"l2_threshold":1.1}"#, "l2_threshold"),
        (r#"{"l2_threshold":-1.1}"#, "l2_threshold"),
    ];
    for (overrides, field) in cases {
        let (status, _, body) = oneshot(app.clone(), chat_with_overrides(overrides)).await;
        assert_ne!(status, StatusCode::OK, "{overrides} -> {body}");
        assert_eq!(status, StatusCode::BAD_REQUEST, "{overrides} -> {body}");
        let json: serde_json::Value = serde_json::from_str(&body)
            .unwrap_or_else(|_| panic!("typed JSON error required for {overrides}, got {body}"));
        assert_eq!(
            json["error"]["type"], "invalid_request_error",
            "{overrides} -> {body}"
        );
        assert_eq!(
            json["error"]["code"], "invalid_chat_override",
            "{overrides} -> {body}"
        );
        assert_eq!(json["error"]["field"], field, "{overrides} -> {body}");
        let message = json["error"]["message"].as_str().unwrap_or("");
        assert!(!message.is_empty(), "{overrides} -> {body}");
        assert!(json.get("decision").is_none(), "{overrides} -> {body}");
    }
}

#[tokio::test]
async fn studio_override_edges_remain_on_the_chat_contract() {
    let app = app(python_lock(0.5));
    let cases = [
        r#"{"l1_threshold":1.0}"#,
        r#"{"l1_threshold":-1.0}"#,
        r#"{"l1_threshold":0.0}"#,
        r#"{"l2_threshold":0.0}"#,
        r#"{"l2_threshold":1.0}"#,
        r#"{"l2_threshold":-1.0}"#,
        r#"{"epsilon":0.0}"#,
        r#"{"epsilon":0.5}"#,
        r#"{"l1_threshold":0.5,"l2_threshold":0.5,"quorum_k":11,"epsilon":0.0}"#,
    ];
    for overrides in cases {
        let (status, _, body) = oneshot(app.clone(), chat_with_overrides(overrides)).await;
        assert_ne!(status, StatusCode::BAD_REQUEST, "{overrides} -> {body}");
        assert_eq!(status, StatusCode::OK, "{overrides} -> {body}");
    }
}

struct CountingFirstClauseEmbedder {
    calls: AtomicUsize,
    batches: Mutex<Vec<Vec<String>>>,
    pass_vector: AlignedVec1024,
    breach_vector: AlignedVec1024,
    breaching_clause: String,
}

#[async_trait]
impl BatchEmbedderClient for CountingFirstClauseEmbedder {
    async fn embed_batch_f32(&self, texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
        let recorded: Vec<String> = texts.iter().copied().map(str::to_string).collect();
        self.calls.fetch_add(1, Ordering::SeqCst);
        self.batches.lock().expect("embed batch log").push(recorded);
        let breaching = self.breaching_clause.as_str();
        Ok(texts
            .iter()
            .map(|text| {
                if *text == breaching {
                    self.breach_vector
                } else {
                    self.pass_vector
                }
            })
            .collect())
    }
}

#[tokio::test]
async fn one_embed_batch_keeps_skipped_clauses_when_the_first_clause_breaches() {
    let prompt = "orthogonal clause, retained clause";
    let normalized = InputNormalizer::normalize(prompt);
    let clauses = normalized.segment_all_clauses();
    assert!(
        clauses.len() >= 2,
        "prompt must segment into at least two clauses, got {clauses:?}"
    );

    let lock = python_lock(0.5);
    let mut breach_vector = AlignedVec1024::zeros();
    breach_vector.data[100] = 1.0;
    let embedder = Arc::new(CountingFirstClauseEmbedder {
        calls: AtomicUsize::new(0),
        batches: Mutex::new(Vec::new()),
        pass_vector: lock.centroid,
        breach_vector,
        breaching_clause: clauses[0].to_string(),
    });
    let app = router(Arc::new(ProxyAppState {
        registry: Arc::new(HotRegistry::from_locks([lock])),
        embedder: Arc::clone(&embedder) as Arc<dyn BatchEmbedderClient>,
        upstream: Arc::new(MockUpstreamForwarder),
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
    }));

    let (status, _, body) = oneshot(
        app,
        Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("content-type", "application/json")
            .body(chat_body(prompt))
            .unwrap(),
    )
    .await;

    assert_eq!(status, StatusCode::FORBIDDEN, "{body}");
    let breach: serde_json::Value = serde_json::from_str(&body).expect(&body);
    assert_eq!(breach["decision"], "BREACH", "{body}");
    assert_eq!(breach["failing_tier"], "L2_CLAUSE_GATE", "{body}");
    assert_eq!(breach["l2"]["breached_clause_index"], 0, "{body}");
    let skipped = breach["clauses_skipped"].as_u64().expect("clauses_skipped") as usize;
    assert!(skipped > 0, "{body}");
    assert!(skipped < clauses.len(), "{body}");

    assert_eq!(embedder.calls.load(Ordering::SeqCst), 1);
    let batches = embedder.batches.lock().expect("embed batch log");
    assert_eq!(batches.len(), 1, "embed_batch_f32 must run once");
    let batch = &batches[0];
    let mut expected = Vec::with_capacity(1 + clauses.len());
    expected.push(normalized.text.clone());
    expected.extend(clauses.iter().copied().map(str::to_string));
    assert_eq!(batch, &expected);
    let ungated = &clauses[clauses.len() - skipped..];
    assert!(!ungated.is_empty());
    for clause in ungated {
        assert!(
            batch.iter().any(|text| text == *clause),
            "clause counted by clauses_skipped was absent from the embed batch: {clause}"
        );
    }
}
