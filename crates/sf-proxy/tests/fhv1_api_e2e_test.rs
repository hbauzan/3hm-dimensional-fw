//! REST coverage for `/api/v1/fhv1` and the chat filter modes.

use std::io::{Cursor, Read};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

use async_trait::async_trait;
use axum::body::Body;
use axum::http::{HeaderMap, Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::Value;
use sf_kernels::{AlignedVec1024, DomainHypercubeLock, LockSpec, NoiseBitmask1024, DIM, MAX_TOPK};
use sf_proxy::{
    router, validate_and_normalize_f32_slice, BatchEmbedderClient, DualEmbedBatch,
    MockUpstreamForwarder, ProxyAppState, TeiHttpEmbedder, EMBED_BATCH_SIZE,
};
use sf_storage::{Fhv1Store, HotRegistry};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;
use tower::ServiceExt;
use zip::ZipArchive;

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

struct GateEmbedder {
    centroid: AlignedVec1024,
    f32_calls: AtomicU64,
    f64_calls: AtomicU64,
}

impl GateEmbedder {
    fn new(centroid: AlignedVec1024) -> Self {
        Self {
            centroid,
            f32_calls: AtomicU64::new(0),
            f64_calls: AtomicU64::new(0),
        }
    }

    fn reset(&self) {
        self.f32_calls.store(0, Ordering::Relaxed);
        self.f64_calls.store(0, Ordering::Relaxed);
    }

    fn counts(&self) -> (u64, u64) {
        (
            self.f32_calls.load(Ordering::Relaxed),
            self.f64_calls.load(Ordering::Relaxed),
        )
    }

    fn f32_rows(&self, texts: &[&str]) -> Vec<AlignedVec1024> {
        texts
            .iter()
            .map(|text| {
                if *text == "BREACH" {
                    AlignedVec1024::zeros()
                } else {
                    self.centroid
                }
            })
            .collect()
    }

    fn raw_f64_rows(texts: &[&str]) -> Vec<[f64; DIM]> {
        texts
            .iter()
            .map(|text| {
                let mut row = [0.0; DIM];
                row[0] = if *text == "hello from the lab" {
                    1.0
                } else {
                    9.0
                };
                row
            })
            .collect()
    }
}

#[async_trait]
impl BatchEmbedderClient for GateEmbedder {
    async fn embed_batch_f32(&self, texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
        self.f32_calls.fetch_add(1, Ordering::Relaxed);
        Ok(self.f32_rows(texts))
    }

    fn is_mock(&self) -> bool {
        true
    }

    async fn embed_batch_raw_f64(
        &self,
        texts: &[&str],
        _normalize: bool,
    ) -> Result<Vec<[f64; DIM]>, String> {
        self.f64_calls.fetch_add(1, Ordering::Relaxed);
        Ok(Self::raw_f64_rows(texts))
    }

    async fn embed_batch_dual(
        &self,
        _domain_id: Option<&str>,
        texts: &[&str],
    ) -> Result<DualEmbedBatch, String> {
        self.f32_calls.fetch_add(1, Ordering::Relaxed);
        Ok(DualEmbedBatch {
            f32_vectors: self.f32_rows(texts),
            raw_f64_vectors: Some(Self::raw_f64_rows(texts)),
        })
    }
}

struct TempDir(PathBuf);

impl TempDir {
    fn new(label: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "{label}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("clock")
                .as_nanos()
        ));
        std::fs::create_dir_all(&path).expect("temp");
        Self(path)
    }

    fn uri(&self) -> &str {
        self.0.to_str().expect("utf8 temp path")
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn router_for(
    store: Option<Arc<Fhv1Store>>,
    embedder: Arc<dyn BatchEmbedderClient>,
) -> axum::Router {
    let registry = HotRegistry::from_locks([lock()]);
    router(Arc::new(ProxyAppState {
        registry: Arc::new(registry),
        embedder,
        upstream: Arc::new(MockUpstreamForwarder),
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
        fhv1_store: store,
    }))
}

fn header<'a>(headers: &'a HeaderMap, name: &str) -> &'a str {
    headers
        .get(name)
        .and_then(|value| value.to_str().ok())
        .unwrap_or("")
}

async fn body_json(
    app: axum::Router,
    method: &str,
    uri: &str,
    body: &str,
) -> (StatusCode, HeaderMap, Value) {
    let (status, headers, bytes) = oneshot(app, json_request(method, uri, body)).await;
    let value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes)
            .unwrap_or_else(|_| Value::String(String::from_utf8_lossy(&bytes).into_owned()))
    };
    (status, headers, value)
}

async fn calibrate_texts(app: &axum::Router, texts: &[&str], normalize: bool) -> String {
    let body = serde_json::json!({
        "policy_id": "python",
        "texts": texts,
        "normalize": normalize,
    })
    .to_string();
    let (status, _, value) = body_json(app.clone(), "POST", "/api/v1/fhv1/calibrate", &body).await;
    assert_eq!(status, StatusCode::OK, "{value}");
    value["profile_id"]
        .as_str()
        .expect("profile id")
        .to_string()
}

async fn calibrate_text(app: &axum::Router, text: &str, normalize: bool) -> String {
    calibrate_texts(app, &[text], normalize).await
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

#[tokio::test]
async fn empty_store_lists_and_missing_store_fail_closed() {
    let centroid = lock().centroid;
    let none = router_for(None, Arc::new(LabEmbedder { centroid }));
    let (status, _, profiles) = body_json(none.clone(), "GET", "/api/v1/fhv1/profiles", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(profiles, serde_json::json!([]));
    let (status, _, runs) = body_json(none.clone(), "GET", "/api/v1/fhv1/benchmarks", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(runs, serde_json::json!([]));
    let (status, _, traces) = body_json(none.clone(), "GET", "/api/v1/fhv1/traces", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(traces["rows"], serde_json::json!([]));
    assert_eq!(traces["total"], 0);
    for (method, uri, body) in [
        (
            "POST",
            "/api/v1/fhv1/calibrate",
            r#"{"policy_id":"python","texts":["x"]}"#,
        ),
        (
            "POST",
            "/api/v1/fhv1/evaluate",
            r#"{"profile_id":"missing","text":"x"}"#,
        ),
        (
            "POST",
            "/api/v1/fhv1/benchmarks/run",
            r#"{"profile_id":"missing","samples":[{"input_id":"a","category":"IN_DOMAIN_VALID","expected_pass":true,"text":"x"}]}"#,
        ),
    ] {
        let (status, _, value) = body_json(none.clone(), method, uri, body).await;
        assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{uri} {value}");
    }

    let dir = TempDir::new("fhv1-uninit");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let empty = router_for(Some(store), Arc::new(LabEmbedder { centroid }));
    let (status, _, profiles) = body_json(empty.clone(), "GET", "/api/v1/fhv1/profiles", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(profiles, serde_json::json!([]));
    let (status, _, runs) = body_json(empty.clone(), "GET", "/api/v1/fhv1/benchmarks", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(runs, serde_json::json!([]));
    let (status, _, traces) = body_json(empty, "GET", "/api/v1/fhv1/traces", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(traces["rows"], serde_json::json!([]));
    assert_eq!(traces["total"], 0);
}

#[tokio::test]
async fn profile_detail_reclassifies_quantiles_and_rejects_bad_ids() {
    let dir = TempDir::new("fhv1-profile");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let app = router_for(Some(store), Arc::new(GateEmbedder::new(lock().centroid)));
    let profile_id = calibrate_texts(&app, &["hello from the lab", "other words here"], true).await;
    let (status, _, default_detail) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/profiles/{profile_id}"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{default_detail}");
    let (status, _, variance_default) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/profiles/{profile_id}?metric=variance"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{variance_default}");
    let (status, _, span_detail) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/profiles/{profile_id}?metric=span"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{span_detail}");
    assert_eq!(
        default_detail["quantile_cutoffs"], variance_default["quantile_cutoffs"],
        "omitted metric must default to variance"
    );
    assert_eq!(
        default_detail["movement_tier_codes"],
        variance_default["movement_tier_codes"]
    );
    assert_ne!(
        default_detail["quantile_cutoffs"]["p25"]
            .as_f64()
            .expect("default p25")
            .to_bits(),
        span_detail["quantile_cutoffs"]["p25"]
            .as_f64()
            .expect("span p25")
            .to_bits()
    );
    let (status, _, detail) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/profiles/{profile_id}?metric=variance&p25=0.1&p75=0.6&p90=0.8"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{detail}");
    let codes = detail["movement_tier_codes"].as_array().expect("codes");
    assert_eq!(codes.len(), DIM);
    assert_eq!(codes[0], 1);
    assert_eq!(codes[1], 0);
    assert!(detail["quantile_cutoffs"]["p25"].as_f64().expect("p25") > 0.0);
    let (status, _, std_dev) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/profiles/{profile_id}?metric=std_dev"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{std_dev}");
    assert_eq!(std_dev["movement_tier_codes"][0], 1);
    let (status, _, bad) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/profiles/{profile_id}?metric=variance&p25=0.8&p75=0.2&p90=0.9"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{bad}");
    let (status, _, missing) = body_json(
        app,
        "GET",
        "/api/v1/fhv1/profiles/missing-profile?metric=variance",
        "",
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND, "{missing}");
}

#[tokio::test]
async fn evaluate_granularities_stamp_headers_and_reject_bad_input() {
    let dir = TempDir::new("fhv1-eval");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let app = router_for(Some(store), Arc::new(GateEmbedder::new(lock().centroid)));
    let profile_id = calibrate_text(&app, "hello from the lab", true).await;
    for granularity in ["full_only", "clauses", "full_mirror"] {
        let (status, headers, value) = body_json(
            app.clone(),
            "POST",
            "/api/v1/fhv1/evaluate",
            &format!(
                r#"{{"profile_id":"{profile_id}","text":"hello from the lab","eval_granularity":"{granularity}"}}"#
            ),
        )
        .await;
        assert_eq!(status, StatusCode::OK, "{granularity} {value}");
        assert_eq!(value["overall_passed"], true);
        assert_eq!(value["eval_granularity"], granularity);
        let trace_id = value["trace_id"].as_str().expect("trace");
        assert_eq!(header(&headers, "x-sf-trace-id"), trace_id);
        assert_eq!(header(&headers, "x-sf-fhv1-decision"), "PASS");
    }
    let (status, _, bad) = body_json(
        app.clone(),
        "POST",
        "/api/v1/fhv1/evaluate",
        &format!(
            r#"{{"profile_id":"{profile_id}","text":"hello from the lab","eval_granularity":"nope"}}"#
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{bad}");
    let (status, _, missing) = body_json(
        app,
        "POST",
        "/api/v1/fhv1/evaluate",
        r#"{"profile_id":"missing-profile","text":"hello from the lab"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND, "{missing}");
}

#[tokio::test]
async fn benchmark_run_groups_chunks_and_fail_closes_overlap() {
    let dir = TempDir::new("fhv1-bench");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let app = router_for(Some(store), Arc::new(GateEmbedder::new(lock().centroid)));
    let profile_id = calibrate_text(&app, "hello from the lab", true).await;
    let (status, _, created) = body_json(
        app.clone(),
        "POST",
        "/api/v1/fhv1/benchmarks/run",
        &format!(
            r#"{{"profile_id":"{profile_id}","dataset_path":"inline-and-path.jsonl","eval_granularity":"clauses","samples":[{{"input_id":"in-1","category":"HYBRID_BOUNDARY","expected_pass":true,"text":"fresh benchmark prompt"}}]}}"#
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{created}");
    let run_id = created["run_id"].as_str().expect("run").to_string();
    let (status, _, listed) = body_json(app.clone(), "GET", "/api/v1/fhv1/benchmarks", "").await;
    assert_eq!(status, StatusCode::OK, "{listed}");
    assert!(listed
        .as_array()
        .expect("runs")
        .iter()
        .any(|row| row["run_id"] == run_id));
    let (status, _, detail) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/benchmarks/{run_id}"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{detail}");
    assert_eq!(detail["run_id"], run_id);
    assert!(detail["summary_metrics"]["confusion"]["tp"]
        .as_u64()
        .is_some());
    let trace_id = format!("{run_id}-in-1");
    let (status, _, drill) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/traces/{trace_id}"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{drill}");
    let chunks = drill["chunks"].as_array().expect("chunks");
    assert!(chunks.len() >= 2, "{}", chunks.len());
    let indexes: Vec<u64> = chunks
        .iter()
        .map(|chunk| chunk["chunk_index"].as_u64().expect("index"))
        .collect();
    assert_eq!(indexes.first().copied(), Some(0));
    assert_eq!(indexes.last().copied(), Some((chunks.len() - 1) as u64));
    let (status, _, overlap) = body_json(
        app.clone(),
        "POST",
        "/api/v1/fhv1/benchmarks/run",
        &format!(
            r#"{{"profile_id":"{profile_id}","dataset_path":"overlap.jsonl","samples":[{{"input_id":"dup","category":"IN_DOMAIN_VALID","expected_pass":true,"text":"hello from the lab"}}]}}"#
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CONFLICT, "{overlap}");
    let (status, _, missing) =
        body_json(app, "GET", "/api/v1/fhv1/benchmarks/missing-run", "").await;
    assert_eq!(status, StatusCode::NOT_FOUND, "{missing}");
}

#[tokio::test]
async fn xlsx_export_is_a_workbook_and_rejects_bad_requests() {
    let dir = TempDir::new("fhv1-xlsx");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let app = router_for(Some(store), Arc::new(GateEmbedder::new(lock().centroid)));
    let profile_id = calibrate_text(&app, "hello from the lab", true).await;
    let (status, headers, bytes) = oneshot(
        app.clone(),
        json_request(
            "GET",
            &format!("/api/v1/fhv1/profiles/{profile_id}/export?format=xlsx&max_rows=100"),
            "",
        ),
    )
    .await;
    assert_eq!(
        status,
        StatusCode::OK,
        "{}",
        String::from_utf8_lossy(&bytes)
    );
    assert!(header(&headers, "content-disposition").contains(".xlsx"));
    let mut archive = ZipArchive::new(Cursor::new(bytes)).expect("xlsx zip");
    let mut workbook = String::new();
    archive
        .by_name("xl/workbook.xml")
        .expect("workbook")
        .read_to_string(&mut workbook)
        .expect("workbook xml");
    assert!(workbook.contains("Summary_Envelope"), "{workbook}");
    assert!(workbook.contains("Raw_Samples_Matrix"), "{workbook}");
    let (status, _, bad) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/profiles/{profile_id}/export?format=nope"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{bad}");
    let (status, _, missing) = body_json(
        app,
        "GET",
        "/api/v1/fhv1/profiles/missing-profile/export?format=xlsx",
        "",
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND, "{missing}");
}

#[tokio::test]
async fn chat_matrix_reuses_one_embed_and_records_pass_traces() {
    let dir = TempDir::new("fhv1-chat");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let embedder = Arc::new(GateEmbedder::new(lock().centroid));
    let app = router_for(
        Some(Arc::clone(&store)),
        Arc::clone(&embedder) as Arc<dyn BatchEmbedderClient>,
    );
    let pass_profile = calibrate_text(&app, "hello from the lab", true).await;
    let fail_profile = calibrate_text(&app, "other words here", true).await;
    let raw_profile = calibrate_text(&app, "hello from the lab", false).await;

    let (status, headers, _) = body_json(
        app.clone(),
        "POST",
        "/api/v1/chat",
        r#"{"messages":[{"role":"user","content":"hello from the lab"}]}"#,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(header(&headers, "x-sf-decision"), "PASS");
    assert!(headers.get("x-sf-fhv1-decision").is_none());
    assert!(headers.get("x-sf-trace-id").is_none());

    embedder.reset();
    let (status, headers, _) = body_json(
        app.clone(),
        "POST",
        "/api/v1/chat",
        &format!(
            r#"{{"messages":[{{"role":"user","content":"hello from the lab"}}],"filter_mode":"fhv1","fhv1_profile_id":"{pass_profile}","fhv1_granularity":"full_only"}}"#
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert!(header(&headers, "content-type").starts_with("text/event-stream"));
    assert_eq!(header(&headers, "x-sf-fhv1-decision"), "PASS");
    let fhv1_trace = header(&headers, "x-sf-trace-id").to_string();
    assert!(!fhv1_trace.is_empty());
    let (status, _, traces) = body_json(
        app.clone(),
        "GET",
        "/api/v1/fhv1/traces?source_kind=REALTIME_CHAT&page_size=50",
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{traces}");
    assert!(traces["rows"]
        .as_array()
        .expect("rows")
        .iter()
        .any(|row| row["trace_id"] == fhv1_trace && row["source_kind"] == "REALTIME_CHAT"));

    embedder.reset();
    let (status, headers, _) = body_json(
        app.clone(),
        "POST",
        "/api/v1/chat",
        &format!(
            r#"{{"messages":[{{"role":"user","content":"hello from the lab"}}],"filter_mode":"3hm_plus_fhv1","fhv1_profile_id":"{pass_profile}","fhv1_granularity":"clauses"}}"#
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert!(header(&headers, "content-type").starts_with("text/event-stream"));
    assert_eq!(header(&headers, "x-sf-fhv1-decision"), "PASS");
    let plus_trace = header(&headers, "x-sf-trace-id").to_string();
    assert_ne!(plus_trace, fhv1_trace);
    assert_eq!(embedder.counts(), (1, 0));
    let (status, _, traces) = body_json(
        app.clone(),
        "GET",
        "/api/v1/fhv1/traces?source_kind=REALTIME_CHAT&page_size=50",
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert!(traces["rows"]
        .as_array()
        .expect("rows")
        .iter()
        .any(|row| row["trace_id"] == plus_trace));

    embedder.reset();
    let (status, _, breach) = body_json(
        app.clone(),
        "POST",
        "/api/v1/chat",
        &format!(
            r#"{{"messages":[{{"role":"user","content":"hello from the lab"}}],"filter_mode":"3hm_plus_fhv1","fhv1_profile_id":"{fail_profile}","fhv1_granularity":"clauses"}}"#
        ),
    )
    .await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{breach}");
    assert_eq!(breach["error"]["kind"], "fhv1_ingress_breach");
    assert_eq!(
        breach["error"]["telemetry"]["failing_tier"],
        "FHV1_AABB_ENVELOPE"
    );
    assert!(
        breach["error"]["telemetry"]["eval_latency_ns"]
            .as_u64()
            .expect("latency")
            > 0
    );
    assert_eq!(embedder.counts(), (1, 0));

    embedder.reset();
    let (status, _, _) = body_json(
        app.clone(),
        "POST",
        "/api/v1/chat",
        &format!(
            r#"{{"messages":[{{"role":"user","content":"hello from the lab"}}],"filter_mode":"3hm_plus_fhv1","fhv1_profile_id":"{pass_profile}","fhv1_granularity":"full_mirror"}}"#
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(embedder.counts(), (1, 1));

    embedder.reset();
    let (status, _, value) = body_json(
        app,
        "POST",
        "/api/v1/chat",
        &format!(
            r#"{{"messages":[{{"role":"user","content":"hello from the lab"}}],"filter_mode":"3hm_plus_fhv1","fhv1_profile_id":"{raw_profile}","fhv1_granularity":"clauses"}}"#
        ),
    )
    .await;
    assert!(
        status == StatusCode::OK || status == StatusCode::FORBIDDEN,
        "{status} {value}"
    );
    assert_eq!(embedder.counts(), (1, 1));
}

#[tokio::test]
async fn trace_filters_page_and_burst_ids_stay_distinct() {
    let dir = TempDir::new("fhv1-traces");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let app = router_for(Some(store), Arc::new(GateEmbedder::new(lock().centroid)));
    let profile_id = calibrate_text(&app, "other words here", true).await;
    let mut failure_ids = Vec::new();
    for _ in 0..3 {
        let (status, headers, value) = body_json(
            app.clone(),
            "POST",
            "/api/v1/fhv1/evaluate",
            &format!(
                r#"{{"profile_id":"{profile_id}","text":"hello from the lab","eval_granularity":"full_only"}}"#
            ),
        )
        .await;
        assert_eq!(status, StatusCode::OK, "{value}");
        assert_eq!(value["overall_passed"], false);
        assert_eq!(header(&headers, "x-sf-fhv1-decision"), "BREACH");
        failure_ids.push(header(&headers, "x-sf-trace-id").to_string());
    }
    let (status, _, pass) = body_json(
        app.clone(),
        "POST",
        "/api/v1/fhv1/evaluate",
        &format!(
            r#"{{"profile_id":"{profile_id}","text":"other words here","eval_granularity":"full_only"}}"#
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{pass}");
    assert_eq!(pass["overall_passed"], true);
    let (status, _, page) = body_json(
        app.clone(),
        "GET",
        "/api/v1/fhv1/traces?category=REALTIME&passed=false&page=2&page_size=1",
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{page}");
    assert_eq!(page["page"], 2);
    assert_eq!(page["total"], 3);
    assert_eq!(page["rows"].as_array().expect("rows").len(), 1);
    assert_eq!(page["rows"][0]["overall_passed"], false);
    assert_eq!(page["rows"][0]["category"], "REALTIME");
    let (status, _, first) = body_json(
        app.clone(),
        "GET",
        "/api/v1/fhv1/traces?category=REALTIME&passed=false&page=1&page_size=1",
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_ne!(first["rows"][0]["trace_id"], page["rows"][0]["trace_id"]);
    let (status, _, bad) =
        body_json(app.clone(), "GET", "/api/v1/fhv1/traces?passed=maybe", "").await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{bad}");

    let (status, _, created) = body_json(
        app.clone(),
        "POST",
        "/api/v1/fhv1/benchmarks/run",
        &format!(
            r#"{{"profile_id":"{profile_id}","samples":[{{"input_id":"oob","category":"OUT_OF_DOMAIN_BENIGN","expected_pass":false,"text":"bench surface alpha"}}],"eval_granularity":"full_only"}}"#
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{created}");
    let run_id = created["run_id"].as_str().expect("run");
    let (status, _, by_run) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/traces?run_id={run_id}&page_size=20"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{by_run}");
    assert!(by_run["total"].as_u64().expect("total") >= 1);
    assert!(by_run["rows"]
        .as_array()
        .expect("rows")
        .iter()
        .all(|row| row["run_id"] == run_id && row["category"] == "OUT_OF_DOMAIN_BENIGN"));
    let (status, _, by_category) = body_json(
        app.clone(),
        "GET",
        "/api/v1/fhv1/traces?category=OUT_OF_DOMAIN_BENIGN&page_size=20",
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{by_category}");
    assert_eq!(by_category["total"], by_run["total"]);

    let mut burst = failure_ids;
    for _ in 0..5 {
        let (status, headers, _) = body_json(
            app.clone(),
            "POST",
            "/api/v1/fhv1/evaluate",
            &format!(
                r#"{{"profile_id":"{profile_id}","text":"hello from the lab","eval_granularity":"full_only"}}"#
            ),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        burst.push(header(&headers, "x-sf-trace-id").to_string());
    }
    let mut unique = burst.clone();
    unique.sort();
    unique.dedup();
    assert_eq!(unique.len(), burst.len());
}

fn find_subsequence(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack
        .windows(needle.len())
        .position(|window| window == needle)
}

fn header_content_length(header: &str) -> usize {
    header
        .lines()
        .find_map(|line| {
            let (name, value) = line.split_once(':')?;
            if name.eq_ignore_ascii_case("content-length") {
                value.trim().parse().ok()
            } else {
                None
            }
        })
        .unwrap_or(0)
}

struct MockTeiServer {
    addr: std::net::SocketAddr,
    requests: Arc<std::sync::Mutex<Vec<String>>>,
}

impl MockTeiServer {
    fn take_requests(&self) -> Vec<String> {
        std::mem::take(&mut *self.requests.lock().expect("requests"))
    }
}

fn ulp_row(dim0: f64, dim2: f64) -> [f64; DIM] {
    let mut row = [0.0f64; DIM];
    row[0] = dim0;
    row[1] = (1.0f64 - dim0 * dim0 - dim2 * dim2).sqrt();
    row[2] = dim2;
    row
}

async fn spawn_mock_tei_server() -> MockTeiServer {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let addr = listener.local_addr().expect("addr");
    let requests = Arc::new(std::sync::Mutex::new(Vec::new()));
    let requests_bg = Arc::clone(&requests);
    let base0 = 0.1f64;
    let hi0 = f64::from_bits(base0.to_bits() + 2);
    let pass0 = f64::from_bits(base0.to_bits() + 1);
    let breach0 = f64::from_bits(base0.to_bits() + 3);
    let low2 = 0.699f64;
    let hi2 = 0.7f64;
    let breach2 = f64::from_bits(hi2.to_bits() + 1);
    tokio::spawn(async move {
        loop {
            let Ok((mut socket, _)) = listener.accept().await else {
                break;
            };
            let requests_ref = Arc::clone(&requests_bg);
            tokio::spawn(async move {
                let mut buf = Vec::new();
                let mut tmp = [0u8; 4096];
                let header_end = loop {
                    let n = socket.read(&mut tmp).await.unwrap_or(0);
                    if n == 0 {
                        break None;
                    }
                    buf.extend_from_slice(&tmp[..n]);
                    if let Some(pos) = find_subsequence(&buf, b"\r\n\r\n") {
                        let header = String::from_utf8_lossy(&buf[..pos]);
                        let len = header_content_length(&header);
                        if buf.len() >= pos + 4 + len {
                            break Some((pos, len));
                        }
                    }
                };
                let Some((pos, len)) = header_end else {
                    return;
                };
                let body_bytes = &buf[pos + 4..pos + 4 + len];
                let raw_req = String::from_utf8_lossy(body_bytes).into_owned();
                let parsed: Value = serde_json::from_str(&raw_req).expect("tei json req");
                requests_ref.lock().expect("lock").push(raw_req);
                let inputs = parsed["inputs"].as_array().expect("inputs array");
                let mut out_rows = Vec::with_capacity(inputs.len());
                for item in inputs {
                    let text = item.as_str().expect("input str");
                    let row = match text {
                        "calibration lower alpha" => ulp_row(base0, low2),
                        "calibration upper beta" => ulp_row(hi0, hi2),
                        "inside one ulp" => ulp_row(pass0, hi2),
                        "outside one ulp" => ulp_row(breach0, breach2),
                        _ => ulp_row(hi0, hi2),
                    };
                    out_rows.push(row.to_vec());
                }
                let resp_body = serde_json::to_string(&out_rows).expect("json resp");
                let response = format!(
                    "HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{}",
                    resp_body.len(),
                    resp_body
                );
                let _ = socket.write_all(response.as_bytes()).await;
            });
        }
    });
    MockTeiServer { addr, requests }
}

fn ulp_router(store: Arc<Fhv1Store>, tei_url: &str) -> axum::Router {
    let base_vec = ulp_row(0.1f64, 0.7f64);
    let mut centroid = AlignedVec1024::zeros();
    for (idx, val) in base_vec.iter().enumerate() {
        centroid.data[idx] = *val as f32;
    }
    let mut lo = AlignedVec1024::zeros();
    let mut hi = AlignedVec1024::zeros();
    lo.data.fill(-0.1);
    hi.data.fill(1.1);
    let mut top_k = [0u16; MAX_TOPK];
    for (idx, slot) in top_k.iter_mut().enumerate().take(4) {
        *slot = u16::try_from(idx).unwrap();
    }
    let domain_lock = DomainHypercubeLock::from_spec(LockSpec {
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
    });
    let registry = HotRegistry::from_locks([domain_lock]);
    router(Arc::new(ProxyAppState {
        registry: Arc::new(registry),
        embedder: Arc::new(TeiHttpEmbedder::new(tei_url)),
        upstream: Arc::new(MockUpstreamForwarder),
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python".to_string(),
        max_telemetry_coords: 4,
        fhv1_store: Some(store),
    }))
}

#[tokio::test]
async fn three_hm_plus_fhv1_single_http_call_keeps_zero_ulp_parity() {
    let dir = TempDir::new("fhv1-1ulp-http");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let server = spawn_mock_tei_server().await;
    let app = ulp_router(store, &format!("http://{}", server.addr));

    let base0 = 0.1f64;
    let hi0 = f64::from_bits(base0.to_bits() + 2);
    let pass0 = f64::from_bits(base0.to_bits() + 1);
    let breach2 = f64::from_bits(0.7f64.to_bits() + 1);
    assert_ne!((pass0 as f32) as f64, pass0);
    assert_ne!((breach2 as f32) as f64, breach2);

    // Show why promote_f32 would have flipped verdicts on these exact vectors:
    let pass_f32_src = ulp_row(pass0, 0.7f64).map(|v| v as f32);
    let pass_promoted = validate_and_normalize_f32_slice(&pass_f32_src).expect("f32 norm");
    assert!(
        f64::from(pass_promoted.data[0]) > hi0,
        "lossy f32 promotion drifts above hi0 and would falsely breach"
    );
    let breach_f32_src = ulp_row(f64::from_bits(base0.to_bits() + 3), breach2).map(|v| v as f32);
    let breach_promoted = validate_and_normalize_f32_slice(&breach_f32_src).expect("f32 norm");
    assert!(
        f64::from(breach_promoted.data[2]) <= 0.7f64,
        "lossy f32 promotion on dim 2 drifts <= 0.7 and would hide dim 2 breach"
    );

    let norm_profile = calibrate_texts(
        &app,
        &["calibration lower alpha", "calibration upper beta"],
        true,
    )
    .await;
    let raw_profile = calibrate_texts(
        &app,
        &["calibration lower alpha", "calibration upper beta"],
        false,
    )
    .await;
    let _ = server.take_requests();

    for (prompt, expected_status) in [
        ("inside one ulp", StatusCode::OK),
        ("outside one ulp", StatusCode::FORBIDDEN),
    ] {
        let (status_standalone, headers_standalone, body_standalone) = body_json(
            app.clone(),
            "POST",
            "/api/v1/chat",
            &format!(
                r#"{{"messages":[{{"role":"user","content":"{prompt}"}}],"filter_mode":"fhv1","fhv1_profile_id":"{norm_profile}","fhv1_granularity":"clauses"}}"#
            ),
        )
        .await;
        assert_eq!(status_standalone, expected_status, "{body_standalone}");
        let trace_standalone = header(&headers_standalone, "x-sf-trace-id").to_string();
        assert!(!trace_standalone.is_empty());
        let standalone_reqs = server.take_requests();
        assert_eq!(standalone_reqs.len(), 1, "{standalone_reqs:?}");

        let (status_plus, headers_plus, body_plus) = body_json(
            app.clone(),
            "POST",
            "/api/v1/chat",
            &format!(
                r#"{{"messages":[{{"role":"user","content":"{prompt}"}}],"filter_mode":"3hm_plus_fhv1","fhv1_profile_id":"{norm_profile}","fhv1_granularity":"clauses"}}"#
            ),
        )
        .await;
        assert_eq!(status_plus, expected_status, "{body_plus}");
        let trace_plus = header(&headers_plus, "x-sf-trace-id").to_string();
        assert!(!trace_plus.is_empty());
        let plus_reqs = server.take_requests();
        assert_eq!(
            plus_reqs.len(),
            1,
            "3hm_plus_fhv1 normalize=true clauses must issue exactly 1 HTTP POST /embed: {plus_reqs:?}"
        );
        assert!(plus_reqs[0].contains("\"normalize\":true"));

        let (s1, _, drill_standalone) = body_json(
            app.clone(),
            "GET",
            &format!("/api/v1/fhv1/traces/{trace_standalone}"),
            "",
        )
        .await;
        assert_eq!(s1, StatusCode::OK, "{drill_standalone}");
        let (s2, _, drill_plus) = body_json(
            app.clone(),
            "GET",
            &format!("/api/v1/fhv1/traces/{trace_plus}"),
            "",
        )
        .await;
        assert_eq!(s2, StatusCode::OK, "{drill_plus}");
        let vec_standalone: Vec<u64> = drill_standalone["chunks"][0]["input_vector"]
            .as_array()
            .expect("vec")
            .iter()
            .map(|v| v.as_f64().expect("f64").to_bits())
            .collect();
        let vec_plus: Vec<u64> = drill_plus["chunks"][0]["input_vector"]
            .as_array()
            .expect("vec")
            .iter()
            .map(|v| v.as_f64().expect("f64").to_bits())
            .collect();
        assert_eq!(
            vec_standalone, vec_plus,
            "input_vector bits must match 0-ULP between standalone fhv1 and 3hm_plus_fhv1"
        );
    }

    let (status_raw, _, body_raw) = body_json(
        app.clone(),
        "POST",
        "/api/v1/chat",
        &format!(
            r#"{{"messages":[{{"role":"user","content":"inside one ulp"}}],"filter_mode":"3hm_plus_fhv1","fhv1_profile_id":"{raw_profile}","fhv1_granularity":"clauses"}}"#
        ),
    )
    .await;
    assert_eq!(status_raw, StatusCode::OK, "{body_raw}");
    let raw_reqs = server.take_requests();
    assert_eq!(
        raw_reqs.len(),
        2,
        "3hm_plus_fhv1 with normalize=false profile must issue 2 HTTP POST /embed calls: {raw_reqs:?}"
    );
    assert!(raw_reqs[0].contains("\"normalize\":true"), "{raw_reqs:?}");
    assert!(raw_reqs[1].contains("\"normalize\":false"), "{raw_reqs:?}");
}

struct BenchBatchEmbedder {
    batches: std::sync::Mutex<Vec<Vec<String>>>,
}

impl BenchBatchEmbedder {
    fn new() -> Self {
        Self {
            batches: std::sync::Mutex::new(Vec::new()),
        }
    }

    fn take_batches(&self) -> Vec<Vec<String>> {
        std::mem::take(&mut *self.batches.lock().expect("batches"))
    }
}

#[async_trait]
impl BatchEmbedderClient for BenchBatchEmbedder {
    async fn embed_batch_f32(&self, _texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
        Err("unused in fhv1 benchmark test".to_string())
    }

    async fn embed_batch_raw_f64(
        &self,
        texts: &[&str],
        _normalize: bool,
    ) -> Result<Vec<[f64; DIM]>, String> {
        self.batches
            .lock()
            .expect("batches")
            .push(texts.iter().map(|text| (*text).to_string()).collect());
        Ok(texts
            .iter()
            .map(|text| {
                let mut row = [MARKER; DIM];
                if text.contains("OUTSIDE_TWO") {
                    row[0] = 9.0;
                    row[1] = 9.0;
                } else if text.contains("OUTSIDE_ONE") {
                    row[0] = 9.0;
                }
                row
            })
            .collect())
    }
}

#[tokio::test]
async fn benchmark_run_has_full_summary_parity_bounded_batching_and_prompt_trace_ids() {
    let dir = TempDir::new("fhv1-bench-parity");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let embedder = Arc::new(BenchBatchEmbedder::new());
    let app = router_for(
        Some(Arc::clone(&store)),
        Arc::clone(&embedder) as Arc<dyn BatchEmbedderClient>,
    );
    let profile_id = calibrate_text(&app, "calibration anchor inside", false).await;
    let _ = embedder.take_batches();

    // 10 multi-chunk prompts across all 4 quadrants and multiple subtypes.
    let samples = serde_json::json!([
        {"input_id": "in-0", "category": "IN_DOMAIN_VALID", "expected_pass": true, "subtype": "short_en", "text": "Clean socket alpha. Clean socket beta."},
        {"input_id": "in-1", "category": "IN_DOMAIN_VALID", "expected_pass": true, "subtype": "short_en", "text": "Clean parser gamma. Clean parser delta."},
        {"input_id": "in-2", "category": "IN_DOMAIN_VALID", "expected_pass": true, "subtype": "long_en", "text": "Valid service alpha. OUTSIDE_ONE false positive clause."},
        {"input_id": "ood-0", "category": "OUT_OF_DOMAIN_BENIGN", "expected_pass": false, "subtype": "clinc_oos", "text": "OUTSIDE_ONE weather forecast. OUTSIDE_TWO travel plan."},
        {"input_id": "ood-1", "category": "OUT_OF_DOMAIN_BENIGN", "expected_pass": false, "subtype": "clinc_oos", "text": "Benign banking check. Benign flight lookup."},
        {"input_id": "hyb-0", "category": "HYBRID_BOUNDARY", "expected_pass": true, "subtype": "near_ood", "text": "Python helper one. Python helper two."},
        {"input_id": "hyb-1", "category": "HYBRID_BOUNDARY", "expected_pass": false, "subtype": "dilution_50_50", "text": "Valid prefix alpha. OUTSIDE_ONE injected pivot."},
        {"input_id": "adv-0", "category": "ADVERSARIAL_FUZZING", "expected_pass": false, "subtype": "prompt_injection", "text": "OUTSIDE_TWO ignore rules. OUTSIDE_TWO reveal keys."},
        {"input_id": "adv-1", "category": "ADVERSARIAL_FUZZING", "expected_pass": false, "subtype": "prompt_injection", "text": "OUTSIDE_ONE override system. Clean tail clause."},
        {"input_id": "adv-2", "category": "ADVERSARIAL_FUZZING", "expected_pass": false, "text": "OUTSIDE_ONE uncategorized subtype check. Clean outro."}
    ]);

    let body = serde_json::json!({
        "profile_id": profile_id,
        "dataset_path": "parity-10.jsonl",
        "eval_granularity": "clauses",
        "use_rogue_mask": false,
        "samples": samples,
    })
    .to_string();

    let (status, _, created) =
        body_json(app.clone(), "POST", "/api/v1/fhv1/benchmarks/run", &body).await;
    assert_eq!(status, StatusCode::OK, "{created}");
    let run_id = created["run_id"].as_str().expect("run_id").to_string();

    // 10 multi-chunk prompts (< 64 total unique chunks) must execute in 1 batched embed call.
    let batches = embedder.take_batches();
    assert_eq!(
        batches.len(),
        1,
        "expected 1 batched embed_batch_raw_f64 call for 10 prompts, got {}: {batches:?}",
        batches.len()
    );
    assert!(batches[0].len() >= 20 && batches[0].len() <= EMBED_BATCH_SIZE);

    let (status, _, detail) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/benchmarks/{run_id}"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{detail}");
    assert_eq!(created["summary_metrics"], detail["summary_metrics"]);

    let summary = &detail["summary_metrics"];
    // Confusion rates parity: TP=3 (in-0,in-1,hyb-0), FN=1 (in-2), TN=5 (ood-0,hyb-1,adv-0,adv-1,adv-2), FP=1 (ood-1)
    let confusion = &summary["confusion"];
    assert_eq!(confusion["tp"], 3);
    assert_eq!(confusion["fn"], 1);
    assert_eq!(confusion["tn"], 5);
    assert_eq!(confusion["fp"], 1);
    assert_eq!(confusion["accuracy"].as_f64(), Some(0.8));
    assert_eq!(confusion["precision"].as_f64(), Some(0.75));
    assert_eq!(confusion["recall"].as_f64(), Some(0.75));
    assert_eq!(confusion["f1"].as_f64(), Some(0.75));
    assert_eq!(confusion["far_fpr"].as_f64(), Some(1.0 / 6.0));
    assert_eq!(confusion["frr_fnr"].as_f64(), Some(0.25));

    // Per-category confusion, histograms, and stats parity across all 4 quadrants.
    let global_hist = summary["failed_dims_count_histogram"]
        .as_object()
        .expect("global hist");
    let cat_hist = summary["failed_dims_count_histogram_by_category"]
        .as_object()
        .expect("cat hist");
    let cat_stats = summary["failed_dims_stats_by_category"]
        .as_object()
        .expect("cat stats");
    for category in [
        "IN_DOMAIN_VALID",
        "OUT_OF_DOMAIN_BENIGN",
        "HYBRID_BOUNDARY",
        "ADVERSARIAL_FUZZING",
    ] {
        assert!(summary["per_category"][category].is_object());
        assert!(cat_hist.contains_key(category));
        assert!(cat_stats.contains_key(category));
    }
    for (bucket, count) in global_hist {
        let summed: u64 = cat_hist
            .values()
            .map(|hist| hist.get(bucket).and_then(|v| v.as_u64()).unwrap_or(0))
            .sum();
        assert_eq!(summed, count.as_u64().expect("count"));
    }
    assert_eq!(cat_stats["IN_DOMAIN_VALID"]["prompt_count"], 3);
    assert_eq!(cat_stats["IN_DOMAIN_VALID"]["prompt_zero_fail_count"], 2);
    assert!(cat_stats["ADVERSARIAL_FUZZING"]["median"]
        .as_f64()
        .is_some());

    // Per-subtype parity (excludes adv-2 without subtype).
    let subtypes = summary["per_subtype"].as_object().expect("per_subtype");
    assert_eq!(subtypes["short_en"]["total"], 2);
    assert_eq!(subtypes["short_en"]["passed"], 2);
    assert_eq!(subtypes["short_en"]["failed"], 0);
    assert_eq!(subtypes["clinc_oos"]["confusion"]["fp"], 1);
    assert_eq!(subtypes["clinc_oos"]["confusion"]["tn"], 1);
    assert_eq!(subtypes["prompt_injection"]["total"], 2);

    // Attribution, comparison, and latency parity.
    assert_eq!(
        summary["attribution"]["in_domain_fail_counts"]
            .as_array()
            .expect("in_domain")
            .len(),
        DIM
    );
    assert!(
        summary["attribution"]["oob_catch_counts"][0]
            .as_u64()
            .expect("oob")
            > 0
    );
    assert_eq!(
        summary["attribution"]["movement_tier_codes"]
            .as_array()
            .expect("tiers")
            .len(),
        DIM
    );
    assert_eq!(
        summary["granularity_comparison"][0]["granularity"],
        "clauses"
    );
    assert_eq!(
        summary["granularity_comparison"][0]["confusion"]["f1"],
        confusion["f1"]
    );
    let latency = &summary["latency"];
    assert!(latency["prompt_eval_p50_ns"].as_f64().is_some());
    assert!(latency["prompt_eval_p99_ns"].as_f64().is_some());
    assert!(latency["prompt_embed_p50_ms"].as_f64().is_some());
    assert!(latency["prompt_embed_p99_ms"].as_f64().is_some());
    assert!(latency["prompt_total_p50_ms"].as_f64().is_some());
    assert!(latency["prompt_total_p99_ms"].as_f64().is_some());
    assert!(latency["chunks_per_sec"].as_f64().is_some());

    // Prompt-scoped trace_id = {run_id}-{input_id} across all chunks.
    for input_id in ["in-0", "in-2", "adv-0"] {
        let expected_trace_id = format!("{run_id}-{input_id}");
        let (status, _, drill) = body_json(
            app.clone(),
            "GET",
            &format!("/api/v1/fhv1/traces/{expected_trace_id}"),
            "",
        )
        .await;
        assert_eq!(status, StatusCode::OK, "{drill}");
        assert_eq!(drill["trace_id"], expected_trace_id);
        let chunks = drill["chunks"].as_array().expect("chunks");
        assert_eq!(chunks.len(), 3, "{chunks:?}");
    }
    let (status, _, run_traces) = body_json(
        app.clone(),
        "GET",
        &format!("/api/v1/fhv1/traces?run_id={run_id}&page_size=100"),
        "",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{run_traces}");
    let rows = run_traces["rows"].as_array().expect("rows");
    assert_eq!(
        rows.len(),
        created["total_chunks"].as_u64().expect("chunks") as usize
    );
    for row in rows {
        let expected = format!("{run_id}-{}", row["input_id"].as_str().expect("input_id"));
        assert_eq!(row["trace_id"], expected);
    }

    // > EMBED_BATCH_SIZE prompts on full_only split cleanly at 64 and do not embed clauses.
    let overflow_count = EMBED_BATCH_SIZE + 6;
    let overflow_samples: Vec<Value> = (0..overflow_count)
        .map(|idx| {
            serde_json::json!({
                "input_id": format!("ov-{idx}"),
                "category": "IN_DOMAIN_VALID",
                "expected_pass": true,
                "text": format!("Clean alpha {idx}. Clean beta {idx}.")
            })
        })
        .collect();
    let overflow_body = serde_json::json!({
        "profile_id": profile_id,
        "eval_granularity": "full_only",
        "samples": overflow_samples,
    })
    .to_string();
    let (status, _, overflow_res) =
        body_json(app, "POST", "/api/v1/fhv1/benchmarks/run", &overflow_body).await;
    assert_eq!(status, StatusCode::OK, "{overflow_res}");
    assert_eq!(overflow_res["total_inputs"], overflow_count as u64);
    assert_eq!(overflow_res["total_chunks"], overflow_count as u64);
    let overflow_batches = embedder.take_batches();
    let batch_lengths: Vec<usize> = overflow_batches.iter().map(Vec::len).collect();
    assert_eq!(batch_lengths, vec![EMBED_BATCH_SIZE, 6]);
}

#[tokio::test]
async fn full_only_blocks_breaching_decoded_base64_payload_in_evaluate_and_chat() {
    let dir = TempDir::new("fhv1-b64-fullonly");
    let store = Arc::new(Fhv1Store::new(dir.uri()));
    let domain_lock = lock();
    let app = router_for(
        Some(Arc::clone(&store)),
        Arc::new(LabEmbedder {
            centroid: domain_lock.centroid,
        }),
    );
    let profile_id = calibrate_text(&app, INSIDE, false).await;

    // Decodes to "OUTSIDE envelope secret payload" while outer text lacks "OUTSIDE".
    let prompt = "inside the lab payload T1VUU0lERSBlbnZlbG9wZSBzZWNyZXQgcGF5bG9hZA== check";

    let (status, headers, eval_body) = body_json(
        app.clone(),
        "POST",
        "/api/v1/fhv1/evaluate",
        &serde_json::json!({
            "profile_id": profile_id,
            "text": prompt,
            "eval_granularity": "full_only",
        })
        .to_string(),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{eval_body}");
    assert_eq!(eval_body["eval_granularity"], "full_only");
    assert_eq!(eval_body["full_text_passed"], true);
    assert_eq!(eval_body["all_chunks_passed"], false);
    assert_eq!(eval_body["overall_passed"], false);
    assert_eq!(header(&headers, "x-sf-fhv1-decision"), "BREACH");
    let chunks = eval_body["chunks"].as_array().expect("chunks");
    assert_eq!(chunks.len(), 2);
    assert_eq!(chunks[0]["chunk_strategy"], "full_doc");
    assert_eq!(chunks[0]["chunk_passed"], true);
    assert_eq!(chunks[1]["chunk_strategy"], "full_doc");
    assert_eq!(chunks[1]["chunk_text"], "OUTSIDE envelope secret payload");
    assert_eq!(chunks[1]["chunk_passed"], false);

    let (chat_status, chat_headers, chat_body) = body_json(
        app,
        "POST",
        "/api/v1/chat",
        &serde_json::json!({
            "messages": [{"role": "user", "content": prompt}],
            "filter_mode": "fhv1",
            "fhv1_profile_id": profile_id,
            "fhv1_granularity": "full_only",
        })
        .to_string(),
    )
    .await;
    assert_eq!(chat_status, StatusCode::FORBIDDEN, "{chat_body}");
    assert_eq!(header(&chat_headers, "x-sf-fhv1-decision"), "BREACH");
    assert_eq!(chat_body["error"]["kind"], "fhv1_ingress_breach");
    assert_eq!(
        chat_body["error"]["telemetry"]["failing_tier"],
        "FHV1_AABB_ENVELOPE"
    );
    assert_eq!(chat_body["error"]["telemetry"]["full_text_passed"], true);
    assert_eq!(chat_body["error"]["telemetry"]["all_chunks_passed"], false);
    assert_eq!(chat_body["error"]["telemetry"]["failing_chunk_index"], 1);
}
