use std::sync::Arc;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use sf_kernels::{AlignedVec1024, DomainHypercubeLock, LockSpec, NoiseBitmask1024, DIM, MAX_TOPK};
use sf_proxy::{router, MockBatchEmbedder, MockUpstreamForwarder, ProxyAppState};
use sf_storage::HotRegistry;
use tower::ServiceExt;

fn pass_vector() -> AlignedVec1024 {
    let mut vector = AlignedVec1024::zeros();
    vector.data[0] = 1.0;
    vector
}

fn python_lock(centroid: AlignedVec1024) -> DomainHypercubeLock {
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
        l1_cosine_threshold: 0.5,
        l2_clause_threshold: 0.5,
        polarity: 0,
        domain_version: 1,
    })
}

fn app() -> axum::Router {
    let centroid = pass_vector();
    let state = Arc::new(ProxyAppState {
        registry: Arc::new(HotRegistry::from_locks([python_lock(centroid)])),
        embedder: Arc::new(MockBatchEmbedder {
            pass_vector: centroid,
            breach_vector: AlignedVec1024::zeros(),
            centroids: std::collections::HashMap::new(),
        }),
        upstream: Arc::new(MockUpstreamForwarder),
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
        fhv1_store: None,
    });
    router(state)
}

async fn post(body: &str) -> (StatusCode, axum::http::HeaderMap, String) {
    let response = app()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/v1/chat/completions")
                .header("content-type", "application/json")
                .header("x-semantic-domain", "python")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, headers, String::from_utf8(bytes.to_vec()).unwrap())
}

#[tokio::test]
async fn valid_prompt_returns_pass() {
    let (status, headers, body) =
        post(r#"{"messages":[{"role":"user","content":"hello kernel. keep going"}]}"#).await;
    assert_eq!(status, StatusCode::OK, "{body}");
    assert_eq!(headers.get("x-sf-decision").unwrap(), "PASS");
    assert!(headers.get("x-sf-clauses-evaluated").is_some());
    assert!(body.contains("chat.completion"));
}

#[tokio::test]
async fn breach_token_is_forbidden() {
    let (status, headers, body) =
        post(r#"{"messages":[{"role":"user","content":"BREACH"}]}"#).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{body}");
    assert!(headers.get("x-sf-decision").is_none());
    assert!(body.contains("SEMANTIC_CONTAINMENT_BREACH"), "{body}");
    assert!(body.contains("L1_CATEGORICAL_COSINE"), "{body}");
}

#[tokio::test]
async fn clause_breach_reports_l2() {
    let (status, _, body) =
        post(r#"{"messages":[{"role":"user","content":"hello kernel. BREACH"}]}"#).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{body}");
    assert!(body.contains("L2_SLIDING_WINDOW"), "{body}");
    assert!(body.contains("breaching_clause_sha256"), "{body}");
}

#[test]
fn layout_constant_matches_contract() {
    assert_eq!(DIM, 1024);
}
