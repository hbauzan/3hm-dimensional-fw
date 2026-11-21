//! REST coverage for `/api/v1/fhv1` and the chat filter modes.

use std::sync::Arc;

use async_trait::async_trait;
use axum::body::Body;
use axum::http::{HeaderMap, Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::Value;
use sf_kernels::{AlignedVec1024, DomainHypercubeLock, LockSpec, NoiseBitmask1024, DIM, MAX_TOPK};
use sf_proxy::{router, BatchEmbedderClient, MockUpstreamForwarder, ProxyAppState};
use sf_storage::{Fhv1Store, HotRegistry};
use tower::ServiceExt;

const INSIDE: &str = "inside the lab envelope";
const MARKER: f64 = 0.125;

struct LabEmbedder {
    centroid: AlignedVec1024,
}

#[async_trait]
impl BatchEmbedderClient for LabEmbedder {
    async fn embed_batch_f32(&self, texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
        Ok(texts
            .iter()
            .map(|text| {
                if text.contains("BREACH") {
                    AlignedVec1024::zeros()
                } else {
                    self.centroid
                }
            })
            .collect())
    }

    fn is_mock(&self) -> bool {
        true
    }

    async fn embed_batch_raw_f64(
        &self,
        texts: &[&str],
        _normalize: bool,
    ) -> Result<Vec<[f64; DIM]>, String> {
        Ok(texts
            .iter()
            .map(|text| {
                let mut row = [MARKER; DIM];
                if text.contains("OUTSIDE") {
                    row[0] = 9.0;
                }
                row
            })
            .collect())
    }
}

fn lock() -> DomainHypercubeLock {
    let mut centroid = AlignedVec1024::zeros();
    centroid.data[0] = 1.0;
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

async fn oneshot(app: axum::Router, request: Request<Body>) -> (StatusCode, HeaderMap, Vec<u8>) {
    let response = app.oneshot(request).await.expect("response");
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response
        .into_body()
        .collect()
        .await
        .expect("body")
        .to_bytes();
    (status, headers, bytes.to_vec())
}

fn json_request(method: &str, uri: &str, body: &str) -> Request<Body> {
    Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .expect("request")
}

#[tokio::test]
async fn fhv1_routes_and_chat_modes_keep_3hm_breach_semantics() {
    let path = std::env::temp_dir().join(format!(
        "fhv1-api-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("clock")
            .as_nanos()
    ));
    std::fs::create_dir_all(&path).expect("temp");
    let store = Arc::new(Fhv1Store::new(path.to_str().expect("utf8")));
    let domain_lock = lock();
    let centroid = domain_lock.centroid;
    let registry = HotRegistry::from_locks([domain_lock]);
    let state = Arc::new(ProxyAppState {
        registry: Arc::new(registry),
        embedder: Arc::new(LabEmbedder { centroid }),
        upstream: Arc::new(MockUpstreamForwarder),
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
        fhv1_store: Some(Arc::clone(&store)),
    });
    let app = router(state);

    let (status, _, body) = oneshot(
        app.clone(),
        json_request("GET", "/api/v1/fhv1/profiles", ""),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        serde_json::from_slice::<Value>(&body).expect("json"),
        serde_json::json!([])
    );

    let (status, _, body) = oneshot(
        app.clone(),
        json_request(
            "POST",
            "/api/v1/fhv1/calibrate",
            &format!(r#"{{"policy_id":"python","texts":["{INSIDE}"],"normalize":false}}"#),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{}", String::from_utf8_lossy(&body));
    let created: Value = serde_json::from_slice(&body).expect("profile");
    let profile_id = created["profile_id"].as_str().expect("id").to_string();

    let (status, _, body) = oneshot(
        app.clone(),
        json_request(
            "POST",
            "/api/v1/fhv1/evaluate",
            &format!(
                r#"{{"profile_id":"{profile_id}","text":"{INSIDE}","eval_granularity":"full_only"}}"#
            ),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{}", String::from_utf8_lossy(&body));
    let evaluated: Value = serde_json::from_slice(&body).expect("eval");
    assert_eq!(evaluated["overall_passed"], true);
    let trace_id = evaluated["trace_id"].as_str().expect("trace").to_string();
    let observed = evaluated["chunks"][0]["dimensions"][0]["observed_bits_hex"]
        .as_str()
        .expect("bits");
    assert_eq!(observed, format!("0x{:016x}", MARKER.to_bits()));

    let (status, _, body) = oneshot(
        app.clone(),
        json_request("GET", &format!("/api/v1/fhv1/traces/{trace_id}"), ""),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{}", String::from_utf8_lossy(&body));
    let drill: Value = serde_json::from_slice(&body).expect("drill");
    assert_eq!(
        drill["chunks"][0]["dimensions"][0]["observed_bits_hex"].as_str(),
        Some(observed)
    );
    assert_eq!(
        drill["chunks"][0]["input_vector"][0]
            .as_f64()
            .expect("f64")
            .to_bits(),
        MARKER.to_bits()
    );

    let (status, headers, body) = oneshot(
        app.clone(),
        json_request(
            "GET",
            &format!("/api/v1/fhv1/profiles/{profile_id}/export?format=csv"),
            "",
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    let disposition = headers
        .get("content-disposition")
        .and_then(|value| value.to_str().ok())
        .unwrap_or("");
    assert!(disposition.contains(".csv"), "{disposition}");
    assert!(String::from_utf8_lossy(&body).contains(&MARKER.to_string()));

    let (status, headers, _) = oneshot(
        app.clone(),
        json_request(
            "GET",
            &format!("/api/v1/fhv1/profiles/{profile_id}/export?format=xlsx&max_rows=1"),
            "",
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    let disposition = headers
        .get("content-disposition")
        .and_then(|value| value.to_str().ok())
        .unwrap_or("");
    assert!(disposition.contains(".zip"), "{disposition}");

    let (status, headers, body) = oneshot(
        app.clone(),
        json_request(
            "GET",
            &format!("/api/v1/fhv1/profiles/{profile_id}/export?format=parquet"),
            "",
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{}", String::from_utf8_lossy(&body));
    let disposition = headers
        .get("content-disposition")
        .and_then(|value| value.to_str().ok())
        .unwrap_or("");
    assert!(disposition.contains(".parquet"), "{disposition}");
    assert!(body.len() > 8);

    let (status, _, body) = oneshot(
        app.clone(),
        json_request(
            "POST",
            "/api/v1/chat",
            r#"{"messages":[{"role":"user","content":"hello from the lab"}]}"#,
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{}", String::from_utf8_lossy(&body));

    let (status, _, body) = oneshot(
        app.clone(),
        json_request(
            "POST",
            "/api/v1/chat",
            &format!(
                r#"{{"messages":[{{"role":"user","content":"OUTSIDE the lab"}}],"filter_mode":"fhv1","fhv1_profile_id":"{profile_id}","fhv1_granularity":"full_only"}}"#
            ),
        ),
    )
    .await;
    assert_eq!(
        status,
        StatusCode::FORBIDDEN,
        "{}",
        String::from_utf8_lossy(&body)
    );
    let breach: Value = serde_json::from_slice(&body).expect("breach");
    assert_eq!(breach["error"]["kind"], "fhv1_ingress_breach");
    assert_eq!(
        breach["error"]["telemetry"]["failing_tier"],
        "FHV1_AABB_ENVELOPE"
    );

    let (status, _, body) = oneshot(
        app.clone(),
        json_request(
            "POST",
            "/api/v1/chat",
            &format!(
                r#"{{"messages":[{{"role":"user","content":"BREACH"}}],"filter_mode":"3hm_plus_fhv1","fhv1_profile_id":"{profile_id}","fhv1_granularity":"full_only"}}"#
            ),
        ),
    )
    .await;
    assert_eq!(
        status,
        StatusCode::FORBIDDEN,
        "{}",
        String::from_utf8_lossy(&body)
    );
    let plus: Value = serde_json::from_slice(&body).expect("plus");
    assert_ne!(plus["error"]["kind"], "fhv1_ingress_breach");
    assert_eq!(plus["failing_tier"], "L1_CENTROID_COSINE");

    let (status, _, body) = oneshot(
        app.clone(),
        json_request(
            "GET",
            "/api/v1/fhv1/traces?source_kind=REALTIME_CHAT&page=1&page_size=50",
            "",
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{}", String::from_utf8_lossy(&body));
    let traces: Value = serde_json::from_slice(&body).expect("traces");
    assert!(traces["total"].as_u64().expect("total") >= 1);
    assert!(traces["rows"]
        .as_array()
        .expect("rows")
        .iter()
        .any(|row| row["source_kind"] == "REALTIME_CHAT"));
    assert!(!path.join("domain_hypercubes.lance").exists());
    let _ = std::fs::remove_dir_all(&path);
}
