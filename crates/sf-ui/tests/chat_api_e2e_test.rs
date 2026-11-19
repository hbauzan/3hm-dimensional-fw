//! `POST /api/v1/chat` behavior: SSE on pass, 403 telemetry on breach, live L1 override.
//!
//! The studio binary has no TEI client. These tests inject the prompt vector so the
//! cascade math is what the assertions measure.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};

use bytes::Bytes;
use sf_bench::{generate_canonical_locks, generate_corpus};
use sf_kernels::{
    cosine_similarity_1024, evaluate_l3_gate, AlignedVec1024, DomainHypercubeLock,
    L3InspectionMode, LockSpec, NoiseBitmask1024, DIM, MAX_TOPK, NOISE_MASK_WORDS,
};
use sf_storage::HotRegistry;
use sf_ui::chat::{PromptEmbedder, RecordingMockForwarder};
use sf_ui::{router, UiAppState};
use tokio::net::TcpListener;

const PYTHON_DOMAIN: &str = "python_receta";
const RECIPE: &str = "Dame la receta para cocinar un risotto de hongos";

struct FixedEmbedder(AlignedVec1024);

impl PromptEmbedder for FixedEmbedder {
    fn embed(&self, _text: &str, _lock: &DomainHypercubeLock) -> AlignedVec1024 {
        self.0
    }
}

struct ChatServer {
    base_url: String,
    hits: Arc<AtomicUsize>,
    last_body: Arc<Mutex<Bytes>>,
    _server: tokio::task::JoinHandle<()>,
}

fn python_lock() -> DomainHypercubeLock {
    generate_canonical_locks()
        .into_iter()
        .find(|lock| lock.domain_id == PYTHON_DOMAIN)
        .expect("python_receta lock")
}

fn orthogonal_to(lock: &DomainHypercubeLock) -> AlignedVec1024 {
    let spike = lock
        .centroid
        .data
        .iter()
        .position(|value| *value != 0.0)
        .expect("centroid spike");
    let mut vector = AlignedVec1024::zeros();
    let other = if spike + 1 < DIM { spike + 1 } else { 0 };
    vector.data[other] = 1.0;
    vector
}

/// In-box vector whose cosine with the centroid sits in `[0.50, 0.75)`.
fn mid_cosine_in_box(lock: &DomainHypercubeLock) -> AlignedVec1024 {
    let mut vector = AlignedVec1024::zeros();
    for dim in 0..DIM {
        vector.data[dim] = if lock.centroid.data[dim] != 0.0 {
            lock.lo_dilated.data[dim]
        } else {
            lock.hi_dilated.data[dim]
        };
    }
    vector
}

async fn spawn_chat_server(embedder: Arc<dyn PromptEmbedder>) -> ChatServer {
    spawn_chat_server_with(
        Arc::new(HotRegistry::from_locks(generate_canonical_locks())),
        embedder,
    )
    .await
}

async fn spawn_chat_server_with(
    registry: Arc<HotRegistry>,
    embedder: Arc<dyn PromptEmbedder>,
) -> ChatServer {
    let recorder = RecordingMockForwarder::new();
    let hits = Arc::clone(&recorder.hits);
    let last_body = Arc::clone(&recorder.last_body);
    let mut state = UiAppState::diagnostic(registry, generate_corpus(), None, "domain_hypercubes");
    state.prompt_embedder = embedder;
    state.upstream = Arc::new(recorder);
    let app = router(Arc::new(state));
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind ephemeral port");
    let addr = listener.local_addr().expect("local addr");
    let base_url = format!("http://{addr}");
    let server = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("serve test server");
    });
    ChatServer {
        base_url,
        hits,
        last_body,
        _server: server,
    }
}

fn http_client() -> reqwest::Client {
    reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .expect("http client")
}

async fn post_chat(server: &ChatServer, payload: serde_json::Value) -> (u16, String, String) {
    let response = http_client()
        .post(format!("{}/api/v1/chat", server.base_url))
        .json(&payload)
        .send()
        .await
        .expect("POST /api/v1/chat");
    let status = response.status().as_u16();
    let content_type = response
        .headers()
        .get(reqwest::header::CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .unwrap_or("")
        .to_string();
    let body = response.text().await.expect("response body");
    (status, content_type, body)
}

fn chat_body(content: &str, l1_threshold: Option<f32>, api_key: Option<&str>) -> serde_json::Value {
    let mut payload = serde_json::json!({
        "messages": [{"role": "user", "content": content}],
        "domain_id": PYTHON_DOMAIN,
        "upstream": {"provider": "mock", "model": "mock-model"}
    });
    if let Some(api_key) = api_key {
        payload["upstream"]["api_key"] = serde_json::json!(api_key);
    }
    if let Some(threshold) = l1_threshold {
        payload["overrides"] = serde_json::json!({ "l1_threshold": threshold });
    }
    payload
}

#[tokio::test]
async fn test_chat_pass_streams_sse_with_mock_upstream() {
    let lock = python_lock();
    let server = spawn_chat_server(Arc::new(FixedEmbedder(lock.centroid))).await;
    let (status, content_type, body) = post_chat(
        &server,
        chat_body(
            "How do I write a Python generator?",
            Some(0.2),
            Some("sk-test-secret"),
        ),
    )
    .await;

    assert_eq!(status, 200, "{body}");
    assert!(
        content_type.starts_with("text/event-stream"),
        "{content_type}"
    );
    assert!(
        body.contains("data: {\"object\":\"chat.completion.chunk\",\"mock\":true}"),
        "{body}"
    );
    assert_eq!(server.hits.load(Ordering::SeqCst), 1);

    let recorded = server
        .last_body
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .clone();
    let wire: serde_json::Value = serde_json::from_slice(&recorded).expect("openai body");
    assert_eq!(wire["stream"], true);
    assert_eq!(wire["model"], "mock-model");
    assert_eq!(
        wire["messages"][0]["content"],
        "How do I write a Python generator?"
    );
    let raw = String::from_utf8(recorded.to_vec()).expect("utf8 body");
    assert!(
        !raw.contains("sk-test-secret"),
        "api key leaked into upstream body: {raw}"
    );
    assert!(!raw.contains("domain_id"), "{raw}");
    assert!(!raw.contains("l1_threshold"), "{raw}");
}

#[tokio::test]
async fn test_chat_breach_returns_403_structured_telemetry() {
    let lock = python_lock();
    let vector = orthogonal_to(&lock);
    let cosine = cosine_similarity_1024(&vector, &lock.centroid);
    assert!(
        cosine < lock.l1_cosine_threshold,
        "recipe stand-in cosine {cosine} must miss the python lock"
    );

    let server = spawn_chat_server(Arc::new(FixedEmbedder(vector))).await;
    let (status, content_type, body) = post_chat(&server, chat_body(RECIPE, None, None)).await;

    assert_eq!(status, 403, "{body}");
    assert!(
        content_type.starts_with("application/json"),
        "{content_type}"
    );
    let parsed: serde_json::Value = serde_json::from_str(&body).expect("breach json");
    assert_eq!(parsed["decision"], "BREACH");
    assert_eq!(parsed["failing_tier"], "L1_CENTROID_COSINE");
    assert_eq!(parsed["l1"]["passed"], false);
    let reported = parsed["l1"]["cosine"].as_f64().expect("cosine");
    assert!((reported - f64::from(cosine)).abs() < 1e-5, "{reported}");
    let threshold = parsed["l1"]["threshold"].as_f64().expect("threshold");
    assert!((threshold - f64::from(lock.l1_cosine_threshold)).abs() < 1e-6);
    assert!(
        parsed["l2"].get("breached_clause_index").is_none(),
        "{body}"
    );
    assert_eq!(parsed["l3"]["evaluated"], false);
    assert!(parsed["l3"].get("passed").is_none(), "{body}");
    assert_eq!(server.hits.load(Ordering::SeqCst), 0);
}

#[tokio::test]
async fn test_chat_runtime_overrides_alter_gate_decision() {
    let lock = python_lock();
    let vector = mid_cosine_in_box(&lock);
    let cosine = cosine_similarity_1024(&vector, &lock.centroid);
    assert!(
        (0.50..0.75).contains(&cosine),
        "override probe cosine {cosine} must sit between 0.50 and 0.75"
    );
    let l3 = evaluate_l3_gate(&vector, &lock, L3InspectionMode::ModeCSpectralQuorum, 0);
    assert!(
        l3.passed,
        "in-box probe failed quorum {}/{}",
        l3.affirmative_votes, l3.required_votes
    );

    let server = spawn_chat_server(Arc::new(FixedEmbedder(vector))).await;
    let (status, _content_type, body) =
        post_chat(&server, chat_body("threshold probe", Some(0.75), None)).await;
    assert_eq!(status, 403, "{body}");
    let parsed: serde_json::Value = serde_json::from_str(&body).expect("breach json");
    assert_eq!(parsed["decision"], "BREACH");
    assert_eq!(parsed["failing_tier"], "L1_CENTROID_COSINE");
    assert_eq!(parsed["l1"]["passed"], false);
    let threshold = parsed["l1"]["threshold"].as_f64().expect("threshold");
    assert!((threshold - 0.75).abs() < 1e-6, "{threshold}");
    assert_eq!(server.hits.load(Ordering::SeqCst), 0);

    let (status, content_type, body) =
        post_chat(&server, chat_body("threshold probe", Some(0.50), None)).await;
    assert_eq!(status, 200, "{body}");
    assert!(
        content_type.starts_with("text/event-stream"),
        "{content_type}"
    );
    assert!(body.contains("chat.completion.chunk"), "{body}");
    assert_eq!(server.hits.load(Ordering::SeqCst), 1);
}

fn unit_axis() -> AlignedVec1024 {
    let mut vector = AlignedVec1024::zeros();
    vector.data[0] = 1.0;
    vector
}

fn wide_python_lock() -> DomainHypercubeLock {
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
        centroid: unit_axis(),
        lo,
        hi,
        epsilon: 0.0,
        noise_mask: NoiseBitmask1024::new_bge_m3_default(),
        top_k_indices: top_k,
        top_k_len: 4,
        quorum_k: 103,
        l1_cosine_threshold: 0.5,
        l2_clause_threshold: 0.5,
        polarity: 0,
        domain_version: 1,
    })
}

fn rejecting_python_receta(primary: &DomainHypercubeLock) -> DomainHypercubeLock {
    let mut pair = primary.clone();
    pair.domain_id = "python_receta".to_string();
    pair.noise_mask = NoiseBitmask1024 {
        words: [0; NOISE_MASK_WORDS],
    };
    pair.quorum_k = 1;
    pair.noise_mask.words[0] = 1;
    pair.lo_dilated.data[0] = 5.0;
    pair.hi_dilated.data[0] = 6.0;
    pair
}

fn python_chat_body(content: &str, overrides: Option<&str>) -> String {
    let overrides = overrides
        .map(|value| format!(r#","overrides":{value}"#))
        .unwrap_or_default();
    format!(
        r#"{{"messages":[{{"role":"user","content":"{content}"}}],"domain_id":"python","upstream":{{"provider":"mock","model":"mock-model"}}{overrides}}}"#
    )
}

async fn post_raw(server: &ChatServer, body: &str) -> (u16, String, reqwest::header::HeaderMap) {
    let response = http_client()
        .post(format!("{}/api/v1/chat", server.base_url))
        .header(reqwest::header::CONTENT_TYPE, "application/json")
        .body(body.to_string())
        .send()
        .await
        .expect("POST /api/v1/chat");
    let status = response.status().as_u16();
    let headers = response.headers().clone();
    let text = response.text().await.expect("response body");
    (status, text, headers)
}

#[tokio::test]
async fn mock_embedder_skips_pairwise_unless_the_prompt_is_breach() {
    let primary = wide_python_lock();
    let registry = Arc::new(HotRegistry::from_locks([
        primary.clone(),
        rejecting_python_receta(&primary),
    ]));
    let server = spawn_chat_server_with(registry, Arc::new(FixedEmbedder(primary.centroid))).await;

    let (status, body, _) = post_raw(
        &server,
        &python_chat_body("Cómo implementar un generador con yield en Python", None),
    )
    .await;
    assert_eq!(status, 200, "{body}");
    assert!(body.contains("chat.completion.chunk"), "{body}");
    assert_eq!(server.hits.load(Ordering::SeqCst), 1);

    let (status, body, _) = post_raw(&server, &python_chat_body("BREACH", None)).await;
    assert_eq!(status, 403, "{body}");
    let parsed: serde_json::Value = serde_json::from_str(&body).expect("pairwise json");
    assert_eq!(
        parsed["error"]["telemetry"]["failing_tier"], "L3_PAIRWISE_QUORUM",
        "{body}"
    );
    assert_eq!(
        parsed["error"]["telemetry"]["breaching_pair_lock"], "python_receta",
        "{body}"
    );
    assert!(parsed.get("decision").is_none(), "{body}");
    assert_eq!(server.hits.load(Ordering::SeqCst), 1);
}

#[tokio::test]
async fn invalid_chat_overrides_return_400_before_dilation() {
    let lock = python_lock();
    let original = f64::from(lock.l1_cosine_threshold);
    let server = spawn_chat_server(Arc::new(FixedEmbedder(orthogonal_to(&lock)))).await;
    let cases = [
        (r#"{"epsilon":-0.05}"#, "epsilon"),
        (r#"{"epsilon":NaN}"#, "epsilon"),
        (r#"{"epsilon":Infinity}"#, "epsilon"),
        (r#"{"epsilon":-Infinity}"#, "epsilon"),
        (r#"{"l1_threshold":NaN}"#, "l1_threshold"),
        (r#"{"l2_threshold":Infinity}"#, "l2_threshold"),
        (r#"{"l1_threshold":1.1}"#, "l1_threshold"),
        (r#"{"l2_threshold":-1.1}"#, "l2_threshold"),
    ];
    for (overrides, field) in cases {
        let (status, body, _) = post_raw(
            &server,
            &format!(
                r#"{{"messages":[{{"role":"user","content":"threshold probe"}}],"domain_id":"{PYTHON_DOMAIN}","upstream":{{"provider":"mock","model":"mock-model"}},"overrides":{overrides}}}"#
            ),
        )
        .await;
        assert_eq!(status, 400, "{overrides} -> {body}");
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
        assert_eq!(server.hits.load(Ordering::SeqCst), 0, "{overrides}");
    }

    let (status, _content_type, body) =
        post_chat(&server, chat_body("threshold probe", None, None)).await;
    assert_eq!(status, 403, "{body}");
    let parsed: serde_json::Value = serde_json::from_str(&body).expect("breach json");
    assert_eq!(parsed["decision"], "BREACH");
    assert_eq!(parsed["failing_tier"], "L1_CENTROID_COSINE");
    let threshold = parsed["l1"]["threshold"].as_f64().expect("threshold");
    assert!(
        (threshold - original).abs() < 1e-6,
        "follow-up saw {threshold}, original lock is {original}"
    );
    assert_eq!(server.hits.load(Ordering::SeqCst), 0);
}

#[tokio::test]
async fn threshold_endpoints_and_zero_epsilon_still_apply() {
    let lock = python_lock();
    let server = spawn_chat_server(Arc::new(FixedEmbedder(lock.centroid))).await;
    let cases = [
        (r#"{"l1_threshold":-1.0}"#, -1.0f64),
        (r#"{"l1_threshold":1.0}"#, 1.0),
        (r#"{"epsilon":0.0}"#, f64::from(lock.l1_cosine_threshold)),
    ];
    for (index, (overrides, expected_l1)) in cases.iter().enumerate() {
        let (status, body, headers) = post_raw(
            &server,
            &format!(
                r#"{{"messages":[{{"role":"user","content":"threshold probe"}}],"domain_id":"{PYTHON_DOMAIN}","upstream":{{"provider":"mock","model":"mock-model"}},"overrides":{overrides}}}"#
            ),
        )
        .await;
        assert_eq!(status, 200, "{overrides} -> {body}");
        let telemetry = headers
            .get("x-sf-telemetry")
            .and_then(|value| value.to_str().ok())
            .unwrap_or("");
        let parsed: serde_json::Value = serde_json::from_str(telemetry)
            .unwrap_or_else(|_| panic!("{overrides} telemetry {telemetry}"));
        let threshold = parsed["l1"]["threshold"].as_f64().expect("threshold");
        assert!(
            (threshold - expected_l1).abs() < 1e-6,
            "{overrides} applied {threshold}, expected {expected_l1}"
        );
        assert_eq!(server.hits.load(Ordering::SeqCst), index + 1);
    }
}
