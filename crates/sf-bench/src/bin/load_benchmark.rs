use std::path::Path;
use std::sync::Arc;
use std::time::{Duration, Instant};

use axum::body::Body;
use axum::http::Request;
use bytes::Bytes;
use clap::Parser;
use hdrhistogram::Histogram;
use http_body_util::BodyExt;
use serde_json::json;
use sf_bench::{generate_canonical_locks, run_oos_benchmark, suite2_locks};
use sf_kernels::{AlignedVec1024, DomainHypercubeLock, DEFAULT_QUORUM_K, DIM};
use sf_proxy::{router, MockBatchEmbedder, MockUpstreamForwarder, ProxyAppState};
use sf_storage::{write_locks, CorpusManifest, HotRegistry, TABLE_NAME};
use tokio::sync::Semaphore;
use tower::ServiceExt;

const MOCK_REPORT_PATH: &str = "reports/load_benchmark_mock.json";
const EMBEDDER_REPORT_PATH: &str = "reports/load_benchmark_mps_http.json";
/// Iteration count of the suite-2 gate loop that `run_oos_benchmark` times.
const SUITE2_GATE_ITERATIONS: u64 = 1_000;
const EMBEDDER_REQUESTS: u64 = 16;
const EMBEDDER_URL: &str = "http://127.0.0.1:8080";
const EMBED_CLAUSE: &str = "a short clause";

#[derive(Debug, Parser)]
struct Args {
    #[arg(long, default_value_t = 1000)]
    rps: u64,
    #[arg(long, default_value_t = 60)]
    duration_secs: u64,
    #[arg(long, default_value_t = 2.0)]
    assert_p99_ms: f64,
}

fn prompt_m16() -> String {
    (0..16)
        .map(|idx| format!("clause {idx} stays inside the python lock"))
        .collect::<Vec<_>>()
        .join(". ")
}

fn rss_mb() -> f64 {
    let pid = std::process::id().to_string();
    let output = std::process::Command::new("ps")
        .args(["-o", "rss=", "-p", &pid])
        .output()
        .expect("ps rss");
    let text = String::from_utf8_lossy(&output.stdout);
    let kb: f64 = text.trim().parse().unwrap_or(0.0);
    kb / 1024.0
}

#[tokio::main]
async fn main() {
    let args = Args::parse();

    // 1. Generate the 55 canonical locks (quorum_k = 103, 985 active dims)
    let locks = generate_canonical_locks();
    assert_eq!(locks.len(), 55, "canonical registry has 55 locks");
    assert_eq!(
        locks[0].noise_mask.active_count(),
        985,
        "active dimensions must be 985"
    );
    assert_eq!(locks[0].quorum_k, 103, "quorum_k must be 103");

    // 2. Persist all 55 locks into a temporary LanceDB table on disk
    let temp_dir = std::env::temp_dir().join(format!("sf-loadbench-lance-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&temp_dir);
    std::fs::create_dir_all(&temp_dir).expect("create temp dir");
    let uri = temp_dir.to_str().expect("uri to str");
    write_locks(uri, TABLE_NAME, &locks)
        .await
        .expect("persist 55 locks to lancedb");

    // 3. Load HotRegistry from that LanceDB table into ProxyAppState
    let registry = Arc::new(
        HotRegistry::load_from_lancedb(uri, TABLE_NAME)
            .await
            .expect("load hot registry from lancedb"),
    );
    assert_eq!(registry.locks().len(), 55);

    let target_lock = registry
        .get("python_receta")
        .expect("canonical lock python_receta must exist in registry");
    let centroid = target_lock.centroid;

    let state = Arc::new(ProxyAppState {
        registry,
        embedder: Arc::new(MockBatchEmbedder {
            pass_vector: centroid,
            breach_vector: AlignedVec1024 { data: [0.0; DIM] },
            centroids: std::collections::HashMap::new(),
        }),
        upstream: Arc::new(MockUpstreamForwarder),
        mock_upstream: Arc::new(MockUpstreamForwarder),
        default_domain: "python_receta".to_string(),
        max_telemetry_coords: 1,
    });
    let app = router(state);

    let body = Bytes::from(format!(
        r#"{{"messages":[{{"role":"user","content":"{}"}}]}}"#,
        prompt_m16()
    ));

    // 4. Execute the load test evaluating Mode C (quorum_k = 103, 985 active dims)
    let total = args.rps.saturating_mul(args.duration_secs).max(1);
    let interval = Duration::from_nanos(1_000_000_000 / args.rps.max(1));
    let semaphore = Arc::new(Semaphore::new(128));
    let mut histogram = Histogram::<u64>::new(3).expect("histogram");
    let mut next = tokio::time::Instant::now();
    let mut inflight = tokio::task::JoinSet::new();

    for _ in 0..total {
        tokio::time::sleep_until(next).await;
        next += interval;
        let permit = semaphore.clone().acquire_owned().await.expect("permit");
        let app = app.clone();
        let body = body.clone();
        inflight.spawn(async move {
            let started = Instant::now();
            let response = app
                .oneshot(
                    Request::builder()
                        .method("POST")
                        .uri("/v1/chat/completions")
                        .header("content-type", "application/json")
                        .header("x-semantic-domain", "python_receta")
                        .header("x-ddi-mode", "mode_c")
                        .body(Body::from(body))
                        .unwrap(),
                )
                .await
                .expect("response");
            let status = response.status();
            let _ = response.into_body().collect().await;
            drop(permit);
            (status, started.elapsed())
        });
        while let Some(joined) = inflight.try_join_next() {
            record(&mut histogram, joined);
        }
    }
    while let Some(joined) = inflight.join_next().await {
        record(&mut histogram, joined);
    }

    // 5. Sample RSS after LanceDB load and requests complete, then persist this run.
    let p50_ms = histogram.value_at_quantile(0.50) as f64 / 1_000_000.0;
    let p95_ms = histogram.value_at_quantile(0.95) as f64 / 1_000_000.0;
    let p99_ms = histogram.value_at_quantile(0.99) as f64 / 1_000_000.0;
    let rss = rss_mb();
    println!(
        "requests={total} rps={} duration_secs={} p50_ms={p50_ms:.4} p95_ms={p95_ms:.4} p99_ms={p99_ms:.4} rss_mb={rss:.2}",
        args.rps, args.duration_secs
    );

    let gate = run_oos_benchmark();
    let mock_report = mock_load_report(
        LoadObservation {
            rps: args.rps,
            duration_secs: args.duration_secs,
            p50_ms,
            p95_ms,
            p99_ms,
            rss_mb: rss,
            requests: total,
        },
        GateObservation {
            p50_us: gate.latency_p50_us,
            p99_us: gate.latency_p99_us,
            iterations: SUITE2_GATE_ITERATIONS,
        },
    );
    write_report_file(Path::new(MOCK_REPORT_PATH), &mock_report).expect("write mock report");
    report_calibrated_row_bytes();
    let embedder_report = embedder_report_from_local_service();
    write_report_file(Path::new(EMBEDDER_REPORT_PATH), &embedder_report)
        .expect("write embedder report");
    if let Some(error) = embedder_report
        .get("error")
        .and_then(|value| value.as_str())
    {
        println!("embedder error={error}");
    } else {
        println!(
            "embedder mode={} device={} requests={} p50_ms={} p95_ms={} p99_ms={}",
            embedder_report["mode"],
            embedder_report["device"],
            embedder_report["requests"],
            embedder_report["p50_ms"],
            embedder_report["p95_ms"],
            embedder_report["p99_ms"]
        );
    }

    let _ = std::fs::remove_dir_all(&temp_dir);

    let mut failed = false;
    if p99_ms >= args.assert_p99_ms.min(1.50) {
        eprintln!("p99 {p99_ms:.4} ms exceeds the SLA");
        failed = true;
    }
    if p50_ms >= 0.15 {
        eprintln!("p50 {p50_ms:.4} ms exceeds 0.15 ms");
        failed = true;
    }
    if rss >= 45.0 {
        eprintln!("rss {rss:.2} MB exceeds 45 MB");
        failed = true;
    }
    if failed {
        std::process::exit(1);
    }
}

fn record(
    histogram: &mut Histogram<u64>,
    joined: Result<(axum::http::StatusCode, Duration), tokio::task::JoinError>,
) {
    let (status, elapsed) = joined.expect("task");
    assert!(status.is_success(), "{status}");
    let nanos = u64::try_from(elapsed.as_nanos()).unwrap_or(u64::MAX);
    histogram.record(nanos.max(1)).expect("record");
}

struct LoadObservation {
    rps: u64,
    duration_secs: u64,
    p50_ms: f64,
    p95_ms: f64,
    p99_ms: f64,
    rss_mb: f64,
    requests: u64,
}

struct GateObservation {
    p50_us: f64,
    p99_us: f64,
    iterations: u64,
}

struct StoredRowParts {
    centroid: usize,
    lo: usize,
    hi: usize,
    noise_mask: usize,
    top_k: usize,
    small_fields: usize,
}

fn compile_profile() -> &'static str {
    if cfg!(debug_assertions) {
        "dev"
    } else {
        "release"
    }
}

fn mock_load_report(load: LoadObservation, gate: GateObservation) -> serde_json::Value {
    json!({
        "mode": "mock",
        "rps": load.rps,
        "duration_secs": load.duration_secs,
        "p50_ms": load.p50_ms,
        "p95_ms": load.p95_ms,
        "p99_ms": load.p99_ms,
        "rss_mb": load.rss_mb,
        "requests": load.requests,
        "gate_release": {
            "profile": compile_profile(),
            "iterations": gate.iterations,
            "p50_us": gate.p50_us,
            "p99_us": gate.p99_us,
        }
    })
}

fn embedder_http_report(
    device: &str,
    p50_ms: f64,
    p95_ms: f64,
    p99_ms: f64,
    requests: u64,
) -> serde_json::Value {
    let mode = match device {
        "mps" => "http+mps",
        "cpu" => "http+cpu",
        other => {
            return embedder_error_report(&format!("refusing device {other}"));
        }
    };
    json!({
        "mode": mode,
        "device": device,
        "p50_ms": p50_ms,
        "p95_ms": p95_ms,
        "p99_ms": p99_ms,
        "requests": requests,
    })
}

fn embedder_error_report(message: &str) -> serde_json::Value {
    json!({
        "mode": "unmeasured",
        "error": message,
    })
}

fn write_report_file(path: &Path, report: &serde_json::Value) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent)?;
        }
    }
    let mut body = serde_json::to_vec_pretty(report)
        .map_err(|err| std::io::Error::new(std::io::ErrorKind::InvalidData, err))?;
    body.push(b'\n');
    std::fs::write(path, body)
}

/// Bytes copied into one `domain_hypercubes` row: three 1024-d vectors, the
/// noise mask, the stored top-k list, and the scalar columns beside them.
fn stored_lock_row_bytes(lock: &DomainHypercubeLock) -> (usize, StoredRowParts) {
    let centroid = std::mem::size_of_val(&lock.centroid.data);
    let lo = std::mem::size_of_val(&lock.lo_dilated.data);
    let hi = std::mem::size_of_val(&lock.hi_dilated.data);
    let noise_mask = std::mem::size_of_val(&lock.noise_mask.words);
    let top_k_width = usize::from(DEFAULT_QUORUM_K);
    let top_k = std::mem::size_of_val(&lock.top_k_indices[..top_k_width]);
    let manifest = CorpusManifest::UNPROVIDED;
    let small_fields = std::mem::size_of_val(&lock.top_k_len)
        + std::mem::size_of_val(&lock.quorum_k)
        + std::mem::size_of_val(&lock.l1_cosine_threshold)
        + std::mem::size_of_val(&lock.l2_clause_threshold)
        + std::mem::size_of_val(&lock.epsilon)
        + std::mem::size_of_val(&lock.polarity)
        + std::mem::size_of_val(&lock.domain_version)
        + lock.domain_id.len()
        + std::mem::size_of_val(&manifest.doc_count)
        + manifest.sha256.len();
    let parts = StoredRowParts {
        centroid,
        lo,
        hi,
        noise_mask,
        top_k,
        small_fields,
    };
    let bytes =
        parts.centroid + parts.lo + parts.hi + parts.noise_mask + parts.top_k + parts.small_fields;
    (bytes, parts)
}

fn report_calibrated_row_bytes() {
    let locks = suite2_locks();
    let lock = locks
        .iter()
        .find(|lock| lock.domain_id == "python")
        .expect("calibrated python lock");
    let (bytes, _) = stored_lock_row_bytes(lock);
    let catalog: usize = locks.iter().map(|lock| stored_lock_row_bytes(lock).0).sum();
    println!(
        "stored_row domain=python bytes={bytes} catalog66={catalog} size_of={}",
        std::mem::size_of::<DomainHypercubeLock>()
    );
}

fn embedder_report_from_local_service() -> serde_json::Value {
    let device = match health_device() {
        Ok(device) => device,
        Err(error) => return embedder_error_report(&error),
    };
    let mut samples_us = Vec::with_capacity(usize::try_from(EMBEDDER_REQUESTS).unwrap_or(0));
    for _ in 0..EMBEDDER_REQUESTS {
        match time_embed_us() {
            Ok(micros) => samples_us.push(micros),
            Err(error) => return embedder_error_report(&error),
        }
    }
    let (p50_ms, p95_ms, p99_ms) = quantiles_ms(&samples_us);
    embedder_http_report(&device, p50_ms, p95_ms, p99_ms, EMBEDDER_REQUESTS)
}

fn quantiles_ms(samples_us: &[u64]) -> (f64, f64, f64) {
    let mut histogram = Histogram::<u64>::new(3).expect("histogram");
    for sample in samples_us {
        histogram
            .record((*sample).max(1))
            .expect("record embed latency");
    }
    (
        histogram.value_at_quantile(0.50) as f64 / 1_000.0,
        histogram.value_at_quantile(0.95) as f64 / 1_000.0,
        histogram.value_at_quantile(0.99) as f64 / 1_000.0,
    )
}

fn health_device() -> Result<String, String> {
    let output = std::process::Command::new("curl")
        .args([
            "-sS",
            "--max-time",
            "2",
            "-w",
            "\n%{http_code}",
            &format!("{EMBEDDER_URL}/health"),
        ])
        .output()
        .map_err(|err| format!("curl health: {err}"))?;
    if !output.status.success() {
        return Err(format!(
            "embedder health failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    let text = String::from_utf8_lossy(&output.stdout);
    let (body, code) = split_trailing_status(&text)?;
    if code != 200 {
        return Err(format!("embedder health status {code}"));
    }
    let payload: serde_json::Value =
        serde_json::from_str(body.trim()).map_err(|err| format!("health json: {err}"))?;
    payload
        .get("device")
        .and_then(|value| value.as_str())
        .map(str::to_string)
        .ok_or_else(|| "health json has no device".to_string())
}

fn time_embed_us() -> Result<u64, String> {
    let body = format!(r#"{{"inputs":"{EMBED_CLAUSE}","normalize":true}}"#);
    let output = std::process::Command::new("curl")
        .args([
            "-sS",
            "--max-time",
            "30",
            "-o",
            "/dev/null",
            "-w",
            "%{time_total} %{http_code}",
            "-X",
            "POST",
            "-H",
            "content-type: application/json",
            "--data",
            &body,
            &format!("{EMBEDDER_URL}/embed"),
        ])
        .output()
        .map_err(|err| format!("curl embed: {err}"))?;
    if !output.status.success() {
        return Err(format!(
            "embed call failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    let text = String::from_utf8_lossy(&output.stdout);
    let (seconds, code) = parse_curl_timing(text.trim())?;
    if code != 200 {
        return Err(format!("embed status {code}"));
    }
    let micros = (seconds * 1_000_000.0).round();
    if !micros.is_finite() || micros < 0.0 {
        return Err("embed timing was not finite".to_string());
    }
    Ok(micros as u64)
}

fn split_trailing_status(text: &str) -> Result<(&str, u16), String> {
    let (body, code) = text
        .rsplit_once('\n')
        .ok_or_else(|| "curl health output has no status line".to_string())?;
    let code = code
        .trim()
        .parse::<u16>()
        .map_err(|err| format!("curl health status: {err}"))?;
    Ok((body, code))
}

fn parse_curl_timing(text: &str) -> Result<(f64, u16), String> {
    let mut parts = text.split_whitespace();
    let seconds = parts
        .next()
        .ok_or_else(|| "empty curl timing".to_string())?
        .parse::<f64>()
        .map_err(|err| format!("curl time_total: {err}"))?;
    let code = parts
        .next()
        .ok_or_else(|| "curl timing has no status".to_string())?
        .parse::<u16>()
        .map_err(|err| format!("curl embed status: {err}"))?;
    Ok((seconds, code))
}

#[cfg(test)]
mod tests {
    use super::{
        compile_profile, embedder_error_report, embedder_http_report, mock_load_report,
        stored_lock_row_bytes, write_report_file, GateObservation, LoadObservation,
    };
    use sf_bench::suite2_locks;

    #[test]
    fn mock_report_records_the_run_and_does_not_claim_a_gpu() {
        let report = mock_load_report(
            LoadObservation {
                rps: 200,
                duration_secs: 5,
                p50_ms: 0.11,
                p95_ms: 0.22,
                p99_ms: 0.33,
                rss_mb: 9.5,
                requests: 1000,
            },
            GateObservation {
                p50_us: 1.25,
                p99_us: 2.5,
                iterations: 1000,
            },
        );
        assert_eq!(report["mode"], "mock");
        assert_eq!(report["rps"], 200);
        assert_eq!(report["duration_secs"], 5);
        assert_eq!(report["p50_ms"], 0.11);
        assert_eq!(report["p95_ms"], 0.22);
        assert_eq!(report["p99_ms"], 0.33);
        assert_eq!(report["rss_mb"], 9.5);
        assert_eq!(report["requests"], 1000);
        assert_eq!(report["gate_release"]["profile"], compile_profile());
        assert_eq!(report["gate_release"]["iterations"], 1000);
        assert_eq!(report["gate_release"]["p50_us"], 1.25);
        assert_eq!(report["gate_release"]["p99_us"], 2.5);
        let text = report.to_string();
        assert!(!text.contains("mps"));
        assert!(!text.contains("gpu"));
        assert!(!text.contains("http+"));
    }

    #[test]
    fn embedder_report_mode_matches_the_device() {
        let mps = embedder_http_report("mps", 3.5, 4.5, 6.5, 16);
        assert_eq!(mps["mode"], "http+mps");
        assert_eq!(mps["p50_ms"], 3.5);
        assert_eq!(mps["p95_ms"], 4.5);
        assert_eq!(mps["p99_ms"], 6.5);
        assert_eq!(mps["requests"], 16);
        assert!(mps.get("error").is_none());

        let cpu = embedder_http_report("cpu", 10.0, 11.0, 12.0, 4);
        assert_eq!(cpu["mode"], "http+cpu");

        let unknown = embedder_http_report("cuda", 1.0, 1.0, 1.0, 4);
        assert!(unknown.get("p50_ms").is_none());
        assert!(unknown["error"].as_str().is_some());
    }

    #[test]
    fn embedder_error_report_has_no_invented_latency() {
        let report = embedder_error_report("model failed to load");
        assert!(report["error"].as_str().unwrap().contains("model failed"));
        assert!(report.get("p50_ms").is_none());
        assert!(report.get("p95_ms").is_none());
        assert!(report.get("p99_ms").is_none());
        assert_ne!(report["mode"], "http+mps");
        assert_ne!(report["mode"], "mock");
    }

    #[test]
    fn write_report_file_persists_the_document() {
        let dir = std::env::temp_dir().join(format!("sf-load-report-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("load_benchmark_mock.json");
        let report = mock_load_report(
            LoadObservation {
                rps: 1,
                duration_secs: 1,
                p50_ms: 0.1,
                p95_ms: 0.2,
                p99_ms: 0.3,
                rss_mb: 1.0,
                requests: 1,
            },
            GateObservation {
                p50_us: 0.5,
                p99_us: 0.6,
                iterations: 1000,
            },
        );
        write_report_file(&path, &report).unwrap();
        let parsed: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
        assert_eq!(parsed["mode"], "mock");
        assert_eq!(parsed["requests"], 1);
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn calibrated_lock_stored_row_counts_its_fields() {
        let locks = suite2_locks();
        assert_eq!(locks.len(), 66);
        let lock = locks
            .iter()
            .find(|lock| lock.domain_id == "python")
            .expect("calibrated python lock");
        let (bytes, parts) = stored_lock_row_bytes(lock);
        let summed = parts.centroid
            + parts.lo
            + parts.hi
            + parts.noise_mask
            + parts.top_k
            + parts.small_fields;
        assert_eq!(bytes, summed);
        assert!(parts.centroid > 0);
        assert!(parts.lo > 0);
        assert!(parts.hi > 0);
        assert!(parts.noise_mask > 0);
        assert!(parts.top_k > 0);
        assert!(parts.small_fields > 0);
        let catalog: usize = locks.iter().map(|lock| stored_lock_row_bytes(lock).0).sum();
        eprintln!(
            "stored_row domain={} bytes={bytes} centroid={} lo={} hi={} mask={} top_k={} small={} catalog66={catalog} size_of={}",
            lock.domain_id,
            parts.centroid,
            parts.lo,
            parts.hi,
            parts.noise_mask,
            parts.top_k,
            parts.small_fields,
            std::mem::size_of::<sf_kernels::DomainHypercubeLock>()
        );
    }
}
