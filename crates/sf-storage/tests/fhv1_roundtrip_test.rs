//! 0-ULP round trip of fhv1 rows through LanceDB, xlsx, zip, csv, and parquet.

use std::fs::File;
use std::io::{Cursor, Read};
use std::path::PathBuf;

use lancedb::arrow::arrow_array::{Array, Float64Array};
use lancedb::arrow::arrow_schema::DataType;
use parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use sf_kernels::{
    AlignedVec1024, DomainHypercubeLock, Fhv1Quantiles, LockSpec, MovementMetric, NoiseBitmask1024,
    DIM, MAX_TOPK,
};
use sf_storage::{
    export_csv, export_parquet, export_xlsx, fhv1_audit_trace_schema, fhv1_benchmark_run_schema,
    fhv1_calibration_sample_schema, fhv1_profile_schema, load_registry, write_locks,
    Fhv1AuditTrace, Fhv1BenchmarkRun, Fhv1CalibrationRequest, Fhv1RawSample, Fhv1Store,
    Fhv1TraceQuery, Fhv1XlsxPayload, TABLE_NAME,
};
use zip::ZipArchive;

fn marker() -> f64 {
    f64::from_bits(0.1f64.to_bits() + 1)
}

fn temp_dir(label: &str) -> PathBuf {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let path = std::env::temp_dir().join(format!("fhv1-{label}-{}-{nanos}", std::process::id()));
    std::fs::create_dir_all(&path).expect("temp dir");
    path
}

fn planted_vector(value: f64) -> Box<[f64; DIM]> {
    let mut values = vec![0.0; DIM];
    values[0] = value;
    let boxed: Box<[f64]> = values.into_boxed_slice();
    match boxed.try_into() {
        Ok(vector) => vector,
        Err(_) => unreachable!("fhv1 dim"),
    }
}

fn sample(id: &str, value: f64) -> Fhv1RawSample {
    Fhv1RawSample {
        sample_id: id.to_string(),
        source_ref: "unit".to_string(),
        strategy_tag: "full_doc".to_string(),
        raw_text: id.to_string(),
        text_sha256: [0x11; 32],
        vector: planted_vector(value),
    }
}

fn request(samples: Vec<Fhv1RawSample>) -> Fhv1CalibrationRequest {
    Fhv1CalibrationRequest {
        policy_id: "python".to_string(),
        normalize: true,
        use_rogue_mask_default: false,
        polarity: 0,
        model_id: "BAAI/bge-m3".to_string(),
        source_dtype: "float64".to_string(),
        augmented_llm: false,
        corpus_sha256: [0xAB; 32],
        metric: MovementMetric::Span,
        quantiles: Fhv1Quantiles::standard(),
        samples,
    }
}

fn canonical_lock() -> DomainHypercubeLock {
    DomainHypercubeLock::from_spec(LockSpec {
        domain_id: "python".to_string(),
        centroid: AlignedVec1024::zeros(),
        lo: AlignedVec1024::zeros(),
        hi: AlignedVec1024::zeros(),
        epsilon: 0.0,
        noise_mask: NoiseBitmask1024::new_bge_m3_default(),
        top_k_indices: [0u16; MAX_TOPK],
        top_k_len: 1,
        quorum_k: 103,
        l1_cosine_threshold: 0.5,
        l2_clause_threshold: 0.42,
        polarity: 0,
        domain_version: 7,
    })
}

struct TempUri {
    path: PathBuf,
}

impl TempUri {
    fn new(label: &str) -> Self {
        Self {
            path: temp_dir(label),
        }
    }

    fn uri(&self) -> &str {
        self.path.to_str().expect("utf8 temp path")
    }
}

impl Drop for TempUri {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.path);
    }
}

#[test]
fn schemas_pin_float64_lists_and_column_counts() {
    let samples = fhv1_calibration_sample_schema();
    let profiles = fhv1_profile_schema();
    let runs = fhv1_benchmark_run_schema();
    let traces = fhv1_audit_trace_schema();
    assert_eq!(samples.fields().len(), 13);
    assert_eq!(profiles.fields().len(), 19);
    assert_eq!(runs.fields().len(), 11);
    assert_eq!(traces.fields().len(), 28);
    let field = profiles.field_with_name("min_vector").expect("min_vector");
    match field.data_type() {
        DataType::FixedSizeList(item, 1024) => {
            assert_eq!(item.data_type(), &DataType::Float64);
            assert!(!item.is_nullable());
        }
        other => panic!("min_vector type {other:?}"),
    }
    let digest = samples.field_with_name("text_sha256").expect("text_sha256");
    assert_eq!(digest.data_type(), &DataType::FixedSizeBinary(32));
    let expected = traces
        .field_with_name("expected_pass")
        .expect("expected_pass");
    assert!(expected.is_nullable());
}

#[tokio::test]
async fn lance_xlsx_csv_parquet_and_zip_keep_raw_f64_bits() {
    let planted = marker();
    assert_ne!(planted.to_bits(), f64::from(planted as f32).to_bits());
    let dir = TempUri::new("roundtrip");
    let untouched = TempUri::new("untouched");
    {
        let locks = [canonical_lock()];
        write_locks(dir.uri(), TABLE_NAME, &locks)
            .await
            .expect("seed domain_hypercubes");
    }

    {
        let empty = Fhv1Store::new(untouched.uri());
        let profiles = empty.list_profiles().await.expect("empty profiles");
        assert!(profiles.is_empty());
        let runs = empty.list_benchmark_runs().await.expect("empty runs");
        assert!(runs.is_empty());
        assert!(!untouched.path.join("fhv1_profiles.lance").exists());
    }

    let store = Fhv1Store::new(dir.uri());
    let profile_id = {
        let batch = request(vec![sample("s0", planted), sample("s1", 1.0)]);
        let saved = store.save_calibration_profile(&batch).await.expect("save");
        assert_eq!(saved.profile_id, "python-v1-abababababab");
        assert_eq!(saved.version, 1);
        assert_eq!(saved.min_vector[0].to_bits(), planted.to_bits());
        assert_eq!(saved.max_vector[0].to_bits(), 1.0f64.to_bits());
        assert_eq!(saved.sample_count, 2);
        saved.profile_id
    };
    {
        let batch = request(vec![sample("s2", planted)]);
        let again = store
            .save_calibration_profile(&batch)
            .await
            .expect("second save");
        assert_eq!(again.version, 2);
        assert_eq!(again.profile_id, "python-v2-abababababab");
    }
    {
        let loaded = store
            .get_profile(&profile_id)
            .await
            .expect("get")
            .expect("profile");
        assert_eq!(loaded.min_vector[0].to_bits(), planted.to_bits());
        assert_eq!(loaded.std_dev_vector[1].to_bits(), 0.0f64.to_bits());
        let samples = store
            .list_samples_for_profile(&profile_id)
            .await
            .expect("samples");
        assert_eq!(samples.len(), 2);
        let first = samples
            .iter()
            .find(|row| row.sample_id == "s0")
            .expect("s0");
        assert_eq!(first.vector[0].to_bits(), planted.to_bits());
        assert_eq!(first.vector[1].to_bits(), 0.0f64.to_bits());
        assert_eq!(first.text_sha256, [0x11; 32]);
    }

    {
        let runs_before = store.list_benchmark_runs().await.expect("runs");
        assert!(runs_before.is_empty());
    }
    {
        let run = Fhv1BenchmarkRun {
            run_id: "run-1".to_string(),
            profile_id: profile_id.clone(),
            policy_id: "python".to_string(),
            dataset_name: "unit".to_string(),
            dataset_sha256: [0x22; 32],
            eval_granularity: "full_mirror".to_string(),
            use_rogue_mask: false,
            total_inputs: 1,
            total_chunks: 1,
            summary_metrics_json: "{}".to_string(),
            created_at_ms: 10,
        };
        store.save_benchmark_run(&run).await.expect("run");
    }
    {
        let run = store
            .get_benchmark_run("run-1")
            .await
            .expect("get run")
            .expect("run row");
        assert_eq!(run.dataset_sha256, [0x22; 32]);
        assert_eq!(run.total_chunks, 1);
    }

    {
        let traces = [
            trace(&profile_id, "t-1", 0, planted, true),
            trace(&profile_id, "t-1", 1, planted, false),
            trace(&profile_id, "t-2", 0, planted, false),
        ];
        store.append_audit_traces(&traces).await.expect("traces");
    }
    {
        let query = Fhv1TraceQuery {
            run_id: Some(String::new()),
            profile_id: Some(profile_id.clone()),
            source_kind: Some("REALTIME_LAB".to_string()),
            category: None,
            passed: Some(true),
            page: 1,
            page_size: 1,
        };
        let page = store
            .query_audit_trace_summaries(&query)
            .await
            .expect("page");
        assert_eq!(page.total, 1);
        assert_eq!(page.rows.len(), 1);
        assert_eq!(page.rows[0].trace_id, "t-1");
        assert_eq!(page.rows[0].embedding_ms.to_bits(), planted.to_bits());
        assert!(page.rows[0].expected_pass.is_none());
    }
    {
        let drill = store
            .get_trace_drilldown("t-1")
            .await
            .expect("drill")
            .expect("chunks");
        assert_eq!(drill.chunks.len(), 2);
        assert_eq!(
            drill.chunks[0].dimensions[0].observed_bits,
            planted.to_bits()
        );
        assert_eq!(
            drill.chunks[0].trace.input_vector[0].to_bits(),
            planted.to_bits()
        );
    }

    {
        let registry = load_registry(dir.uri()).await.expect("domain registry");
        assert_eq!(registry.len(), 1);
        let lock = registry.get("python").expect("python lock");
        assert_eq!(lock.l1_cosine_threshold.to_bits(), 0.5f32.to_bits());
        assert_eq!(lock.domain_version, 7);
    }

    {
        let loaded = store
            .get_profile(&profile_id)
            .await
            .expect("reload")
            .expect("profile");
        let samples = store
            .list_samples_for_profile(&profile_id)
            .await
            .expect("reload samples");
        let Fhv1XlsxPayload::Xlsx(xlsx) = export_xlsx(&loaded, &samples, 10_000).expect("xlsx")
        else {
            panic!("single workbook");
        };
        let numbers = workbook_numbers(&xlsx);
        assert!(
            numbers
                .iter()
                .any(|value| value.to_bits() == planted.to_bits()),
            "xlsx dropped the planted f64"
        );

        let csv = String::from_utf8(export_csv(&loaded)).expect("csv utf8");
        let min_cell = csv
            .lines()
            .nth(1)
            .expect("dim 0")
            .split(',')
            .nth(2)
            .expect("min")
            .parse::<f64>()
            .expect("parse min");
        assert_eq!(min_cell.to_bits(), planted.to_bits());

        let parquet_bytes = export_parquet(&loaded).expect("parquet");
        let parquet_path = dir.path.join("envelope.parquet");
        std::fs::write(&parquet_path, &parquet_bytes).expect("write parquet");
        let reader =
            ParquetRecordBatchReaderBuilder::try_new(File::open(&parquet_path).expect("open"))
                .expect("builder")
                .build()
                .expect("reader");
        let batch = reader
            .into_iter()
            .next()
            .expect("batch")
            .expect("batch result");
        let min = batch
            .column_by_name("min")
            .expect("min")
            .as_any()
            .downcast_ref::<Float64Array>()
            .expect("f64");
        assert_eq!(min.value(0).to_bits(), planted.to_bits());

        let mut split_samples = samples.clone();
        for index in 0..3 {
            let mut extra = samples[0].clone();
            extra.sample_id = format!("extra-{index}");
            extra.vector[0] = f64::from_bits(planted.to_bits() + (index as u64) + 1);
            split_samples.push(extra);
        }
        assert_eq!(split_samples.len(), 5);
        let Fhv1XlsxPayload::Zip(zip_bytes) = export_xlsx(&loaded, &split_samples, 2).expect("zip")
        else {
            panic!("expected a zip split");
        };
        let mut archive = ZipArchive::new(Cursor::new(zip_bytes)).expect("zip archive");
        let mut names = Vec::new();
        let mut zipped_numbers = Vec::new();
        for index in 0..archive.len() {
            let mut file = archive.by_index(index).expect("zip entry");
            names.push(file.name().to_string());
            let mut bytes = Vec::new();
            file.read_to_end(&mut bytes).expect("read part");
            zipped_numbers.extend(workbook_numbers(&bytes));
        }
        names.sort();
        assert_eq!(
            names,
            vec![
                "part_001.xlsx".to_string(),
                "part_002.xlsx".to_string(),
                "part_003.xlsx".to_string()
            ]
        );
        for index in 0..3 {
            let bits = f64::from_bits(planted.to_bits() + (index as u64) + 1).to_bits();
            assert!(
                zipped_numbers.iter().any(|value| value.to_bits() == bits),
                "missing split value {bits:016x}"
            );
        }
    }
}

fn trace(
    profile_id: &str,
    trace_id: &str,
    chunk_index: u32,
    value: f64,
    overall_passed: bool,
) -> Fhv1AuditTrace {
    Fhv1AuditTrace {
        trace_id: trace_id.to_string(),
        run_id: String::new(),
        source_kind: "REALTIME_LAB".to_string(),
        profile_id: profile_id.to_string(),
        policy_id: "python".to_string(),
        category: "REALTIME".to_string(),
        expected_pass: None,
        input_id: trace_id.to_string(),
        raw_text: "raw".to_string(),
        eval_granularity: "clauses".to_string(),
        use_rogue_mask: false,
        chunk_index,
        chunk_strategy: "full_doc".to_string(),
        chunk_text: "raw".to_string(),
        input_vector: planted_vector(value),
        chunk_passed: overall_passed,
        overall_passed,
        full_text_passed: true,
        all_chunks_passed: overall_passed,
        evaluated_dims: 1024,
        failed_dims_count: if overall_passed { 0 } else { 1 },
        underflow_count: 0,
        overflow_count: if overall_passed { 0 } else { 1 },
        max_violation_delta: 0.0,
        mean_abs_delta_vs_mean: 0.0,
        eval_latency_ns: 12,
        embedding_ms: value,
        created_at_ms: 20,
    }
}

fn workbook_numbers(xlsx: &[u8]) -> Vec<f64> {
    let mut archive = ZipArchive::new(Cursor::new(xlsx)).expect("xlsx zip");
    let mut numbers = Vec::new();
    for index in 0..archive.len() {
        let mut file = archive.by_index(index).expect("xlsx entry");
        if !file.name().contains("xl/worksheets/sheet") {
            continue;
        }
        let mut xml = String::new();
        file.read_to_string(&mut xml).expect("sheet xml");
        numbers.extend(xml_values(&xml));
    }
    numbers
}

fn xml_values(xml: &str) -> Vec<f64> {
    let mut values = Vec::new();
    let mut rest = xml;
    while let Some(start) = rest.find("<v>") {
        rest = &rest[start + 3..];
        let Some(end) = rest.find("</v>") else {
            break;
        };
        if let Ok(value) = rest[..end].parse::<f64>() {
            values.push(value);
        }
        rest = &rest[end + 4..];
    }
    values
}
