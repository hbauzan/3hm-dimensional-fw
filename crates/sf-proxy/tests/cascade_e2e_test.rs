use std::sync::Arc;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use sf_kernels::{AlignedVec1024, DomainHypercubeLock, LockSpec, NoiseBitmask1024, DIM, MAX_TOPK};
use sf_proxy::{router, MockBatchEmbedder, MockUpstreamForwarder, ProxyAppState};
use sf_storage::HotRegistry;
use tower::ServiceExt;

fn vector_at(index: usize) -> AlignedVec1024 {
    let mut vector = AlignedVec1024::zeros();
    vector.data[index] = 1.0;
    vector
}

fn lock(id: &str, axis: usize, polarity: u8, contains_unit_axis: bool) -> DomainHypercubeLock {
    let centroid = vector_at(axis);
    let mut lo = AlignedVec1024::zeros();
    let mut hi = AlignedVec1024::zeros();
    if contains_unit_axis {
        lo.data.fill(-0.05);
        hi.data.fill(0.05);
        hi.data[axis] = 1.2;
    } else {
        lo.data.fill(0.5);
        hi.data.fill(0.6);
    }
    DomainHypercubeLock::from_spec(LockSpec {
        domain_id: id.to_string(),
        centroid,
        lo,
        hi,
        epsilon: 0.0,
        noise_mask: NoiseBitmask1024::new_bge_m3_default(),
        top_k_indices: [0u16; MAX_TOPK],
        top_k_len: 4,
        quorum_k: 103,
        l1_cosine_threshold: 0.8,
        l2_clause_threshold: 0.8,
        polarity,
        domain_version: 1,
    })
}

struct Harness {
    app: axum::Router,
}

impl Harness {
    fn new(pass_axis: usize) -> Self {
        let pass = vector_at(pass_axis);
        let state = Arc::new(ProxyAppState {
            registry: Arc::new(HotRegistry::from_locks([
                lock("python", 0, 0, true),
                lock("legal", 1, 0, false),
                lock("deny-sql", 2, 1, false),
            ])),
            embedder: Arc::new(MockBatchEmbedder {
                pass_vector: pass,
                breach_vector: AlignedVec1024::zeros(),
                centroids: std::collections::HashMap::new(),
            }),
            upstream: Arc::new(MockUpstreamForwarder),
            mock_upstream: Arc::new(MockUpstreamForwarder),
            default_domain: "python".to_string(),
            max_telemetry_coords: 4,
            fhv1_store: None,
        });
        Self { app: router(state) }
    }

    async fn post(
        &self,
        domain: &str,
        wildcard_mode: Option<&str>,
        body: &str,
    ) -> (StatusCode, String) {
        let mut builder = Request::builder()
            .method("POST")
            .uri("/v1/chat/completions")
            .header("content-type", "application/json")
            .header("x-semantic-domain", domain);
        if let Some(mode) = wildcard_mode {
            builder = builder.header("x-sf-wildcard-mode", mode);
        }
        let response = self
            .app
            .clone()
            .oneshot(builder.body(Body::from(body.to_string())).unwrap())
            .await
            .unwrap();
        let status = response.status();
        let bytes = response.into_body().collect().await.unwrap().to_bytes();
        (status, String::from_utf8(bytes.to_vec()).unwrap())
    }
}

#[tokio::test]
async fn wildcard_any_allowlist_passes_when_one_lock_matches() {
    let harness = Harness::new(0);
    let (status, body) = harness
        .post(
            "*",
            None,
            r#"{"messages":[{"role":"user","content":"hello kernel"}]}"#,
        )
        .await;
    assert_eq!(status, StatusCode::OK, "{body}");
    assert!(body.contains("data:"), "{body}");
}

#[tokio::test]
async fn wildcard_all_rejects_when_another_allowlist_misses() {
    let harness = Harness::new(0);
    let (status, body) = harness
        .post(
            "*",
            Some("all"),
            r#"{"messages":[{"role":"user","content":"hello kernel"}]}"#,
        )
        .await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{body}");
    assert!(body.contains("SEMANTIC_CONTAINMENT_BREACH"), "{body}");
}

#[tokio::test]
async fn named_denylist_uses_inverted_cosine() {
    let harness = Harness::new(0);
    let (status, body) = harness
        .post(
            "deny-sql",
            None,
            r#"{"messages":[{"role":"user","content":"hello kernel"}]}"#,
        )
        .await;
    assert_eq!(status, StatusCode::OK, "{body}");
}

#[tokio::test]
async fn live_hot_swap_from_lancedb_increments_domain_version() {
    let temp_dir = std::env::temp_dir().join(format!("sf-e2e-lance-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&temp_dir);
    std::fs::create_dir_all(&temp_dir).unwrap();
    let uri = temp_dir.to_str().unwrap();

    let lock_v1 = lock("python", 0, 0, true);
    assert_eq!(lock_v1.domain_version, 1);
    sf_storage::write_locks(uri, sf_storage::TABLE_NAME, &[lock_v1])
        .await
        .unwrap();

    let hot_registry = Arc::new(
        sf_storage::HotRegistry::load_from_lancedb(uri, sf_storage::TABLE_NAME)
            .await
            .unwrap(),
    );

    let pass = vector_at(0);
    let breach = AlignedVec1024::zeros();

    let state = Arc::new(ProxyAppState {
        registry: Arc::clone(&hot_registry),
        embedder: Arc::new(MockBatchEmbedder {
            pass_vector: pass,
            breach_vector: breach,
            centroids: std::collections::HashMap::new(),
        }),
        upstream: Arc::new(MockUpstreamForwarder),
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
        fhv1_store: None,
    });
    let app = router(state);

    // 1. In-domain vector -> 200 OK (X-SF-Decision: PASS)
    let pass_req = Request::builder()
        .method("POST")
        .uri("/v1/chat/completions")
        .header("content-type", "application/json")
        .header("x-semantic-domain", "python")
        .body(Body::from(
            r#"{"messages":[{"role":"user","content":"hello safe kernel"}]}"#,
        ))
        .unwrap();
    let resp = app.clone().oneshot(pass_req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    assert_eq!(resp.headers().get("x-sf-decision").unwrap(), "PASS");

    // 2. Breaching clause -> 403 Forbidden (ddi_ingress_breach) with domain_version = 1
    let breach_req = Request::builder()
        .method("POST")
        .uri("/v1/chat/completions")
        .header("content-type", "application/json")
        .header("x-semantic-domain", "python")
        .body(Body::from(
            r#"{"messages":[{"role":"user","content":"hello safe. BREACH"}]}"#,
        ))
        .unwrap();
    let resp = app.clone().oneshot(breach_req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(json["error"]["type"], "ddi_ingress_breach");
    assert_eq!(json["error"]["telemetry"]["domain_version"], 1);

    // 3. Update lock in LanceDB to version 2, and hot-reload
    let mut lock_v2 = lock("python", 0, 0, true);
    lock_v2.domain_version = 2;
    sf_storage::write_locks(uri, sf_storage::TABLE_NAME, &[lock_v2])
        .await
        .unwrap();
    hot_registry
        .reload_from_lancedb(uri, sf_storage::TABLE_NAME)
        .await
        .unwrap();

    // 4. Send breaching request again -> 403 Forbidden with domain_version = 2
    let breach_req2 = Request::builder()
        .method("POST")
        .uri("/v1/chat/completions")
        .header("content-type", "application/json")
        .header("x-semantic-domain", "python")
        .body(Body::from(
            r#"{"messages":[{"role":"user","content":"hello safe. BREACH"}]}"#,
        ))
        .unwrap();
    let resp2 = app.oneshot(breach_req2).await.unwrap();
    assert_eq!(resp2.status(), StatusCode::FORBIDDEN);
    let bytes2 = resp2.into_body().collect().await.unwrap().to_bytes();
    let json2: serde_json::Value = serde_json::from_slice(&bytes2).unwrap();
    assert_eq!(json2["error"]["type"], "ddi_ingress_breach");
    assert_eq!(json2["error"]["telemetry"]["domain_version"], 2);

    let _ = std::fs::remove_dir_all(&temp_dir);
}

#[test]
fn dim_constant() {
    assert_eq!(DIM, 1024);
}
