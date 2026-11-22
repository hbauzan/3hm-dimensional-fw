//! Calibration records and the pure assembly step in front of LanceDB.

use serde::Serialize;
use sf_kernels::{
    compute_fhv1_profile_stats, Fhv1DimComparison, Fhv1Error, Fhv1ProfileStats,
    Fhv1QuantileCutoffs, Fhv1Quantiles, MovementMetric, DIM,
};

/// One raw embedded chunk before it is bound to a profile id.
#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1RawSample {
    pub sample_id: String,
    pub source_ref: String,
    pub strategy_tag: String,
    pub raw_text: String,
    pub text_sha256: [u8; 32],
    pub vector: Box<[f64; DIM]>,
}

/// Inputs for one calibration write. Version and profile id are assigned by the store.
#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1CalibrationRequest {
    pub policy_id: String,
    pub normalize: bool,
    pub use_rogue_mask_default: bool,
    pub polarity: u8,
    pub model_id: String,
    pub source_dtype: String,
    pub augmented_llm: bool,
    pub corpus_sha256: [u8; 32],
    pub metric: MovementMetric,
    pub quantiles: Fhv1Quantiles,
    pub samples: Vec<Fhv1RawSample>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1CalibrationSample {
    pub sample_id: String,
    pub profile_id: String,
    pub policy_id: String,
    pub version: u64,
    pub source_ref: String,
    pub strategy_tag: String,
    pub raw_text: String,
    pub text_sha256: [u8; 32],
    pub normalize: bool,
    pub model_id: String,
    pub source_dtype: String,
    pub vector: Box<[f64; DIM]>,
    pub created_at_ms: i64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1ProfileRecord {
    pub profile_id: String,
    pub policy_id: String,
    pub version: u64,
    pub polarity: u8,
    pub normalize: bool,
    pub use_rogue_mask_default: bool,
    pub sample_count: u64,
    pub corpus_sha256: [u8; 32],
    pub model_id: String,
    pub source_dtype: String,
    pub augmented_llm: bool,
    pub min_vector: Box<[f64; DIM]>,
    pub max_vector: Box<[f64; DIM]>,
    pub mean_vector: Box<[f64; DIM]>,
    pub span_vector: Box<[f64; DIM]>,
    pub variance_vector: Box<[f64; DIM]>,
    pub std_dev_vector: Box<[f64; DIM]>,
    pub movement_tier_codes: Box<[u8; DIM]>,
    pub created_at_ms: i64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1BenchmarkRun {
    pub run_id: String,
    pub profile_id: String,
    pub policy_id: String,
    pub dataset_name: String,
    pub dataset_sha256: [u8; 32],
    pub eval_granularity: String,
    pub use_rogue_mask: bool,
    pub total_inputs: u64,
    pub total_chunks: u64,
    pub summary_metrics_json: String,
    pub created_at_ms: i64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1AuditTrace {
    pub trace_id: String,
    pub run_id: String,
    pub source_kind: String,
    pub profile_id: String,
    pub policy_id: String,
    pub category: String,
    pub expected_pass: Option<bool>,
    pub input_id: String,
    pub raw_text: String,
    pub eval_granularity: String,
    pub use_rogue_mask: bool,
    pub chunk_index: u32,
    pub chunk_strategy: String,
    pub chunk_text: String,
    pub input_vector: Box<[f64; DIM]>,
    pub chunk_passed: bool,
    pub overall_passed: bool,
    pub full_text_passed: bool,
    pub all_chunks_passed: bool,
    pub evaluated_dims: u16,
    pub failed_dims_count: u16,
    pub underflow_count: u16,
    pub overflow_count: u16,
    pub max_violation_delta: f64,
    pub mean_abs_delta_vs_mean: f64,
    pub eval_latency_ns: u64,
    pub embedding_ms: f64,
    pub created_at_ms: i64,
}

/// Compact trace row. The 1024-d vector stays in the table and out of this struct.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Fhv1AuditTraceSummary {
    pub trace_id: String,
    pub run_id: String,
    pub source_kind: String,
    pub profile_id: String,
    pub policy_id: String,
    pub category: String,
    pub expected_pass: Option<bool>,
    pub input_id: String,
    pub raw_text: String,
    pub eval_granularity: String,
    pub use_rogue_mask: bool,
    pub chunk_index: u32,
    pub chunk_strategy: String,
    pub chunk_text: String,
    pub chunk_passed: bool,
    pub overall_passed: bool,
    pub full_text_passed: bool,
    pub all_chunks_passed: bool,
    pub evaluated_dims: u16,
    pub failed_dims_count: u16,
    pub underflow_count: u16,
    pub overflow_count: u16,
    pub max_violation_delta: f64,
    pub mean_abs_delta_vs_mean: f64,
    pub eval_latency_ns: u64,
    pub embedding_ms: f64,
    pub created_at_ms: i64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1TraceQuery {
    pub trace_id: Option<String>,
    pub run_id: Option<String>,
    pub profile_id: Option<String>,
    pub source_kind: Option<String>,
    pub category: Option<String>,
    pub passed: Option<bool>,
    pub page: u32,
    pub page_size: u32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1TracePage {
    pub page: u32,
    pub page_size: u32,
    pub total: u64,
    pub rows: Vec<Fhv1AuditTraceSummary>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1TraceChunkDrilldown {
    pub trace: Fhv1AuditTrace,
    pub dimensions: Box<[Fhv1DimComparison; DIM]>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1TraceDrilldown {
    pub trace_id: String,
    pub profile: Fhv1ProfileRecord,
    pub chunks: Vec<Fhv1TraceChunkDrilldown>,
}

#[derive(Debug)]
pub struct Fhv1StorageError {
    pub message: String,
}

impl std::fmt::Display for Fhv1StorageError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.message)
    }
}

impl std::error::Error for Fhv1StorageError {}

impl From<Fhv1Error> for Fhv1StorageError {
    fn from(err: Fhv1Error) -> Self {
        Self {
            message: err.to_string(),
        }
    }
}

impl Fhv1StorageError {
    pub(crate) fn new(err: impl std::fmt::Display) -> Self {
        Self {
            message: err.to_string(),
        }
    }
}

/// `python-v1-` plus 12 lowercase hex chars from the corpus digest.
pub fn profile_id_for(policy_id: &str, version: u64, corpus_sha256: &[u8; 32]) -> String {
    let mut hex = String::with_capacity(12);
    for byte in corpus_sha256.iter().take(6) {
        hex.push_str(&format!("{byte:02x}"));
    }
    format!("{policy_id}-v{version}-{hex}")
}

#[inline(never)]
pub fn assemble_calibration(
    request: &Fhv1CalibrationRequest,
    version: u64,
    created_at_ms: i64,
) -> Result<(Fhv1ProfileRecord, Vec<Fhv1CalibrationSample>), Fhv1StorageError> {
    let rows: Vec<&[f64]> = request
        .samples
        .iter()
        .map(|sample| sample.vector.as_slice())
        .collect();
    let stats =
        compute_fhv1_profile_stats(&rows, request.polarity, request.metric, request.quantiles)?;
    let profile_id = profile_id_for(&request.policy_id, version, &request.corpus_sha256);
    let profile = profile_from_stats(request, &profile_id, version, created_at_ms, &stats);
    let samples = request
        .samples
        .iter()
        .map(|sample| Fhv1CalibrationSample {
            sample_id: sample.sample_id.clone(),
            profile_id: profile_id.clone(),
            policy_id: request.policy_id.clone(),
            version,
            source_ref: sample.source_ref.clone(),
            strategy_tag: sample.strategy_tag.clone(),
            raw_text: sample.raw_text.clone(),
            text_sha256: sample.text_sha256,
            normalize: request.normalize,
            model_id: request.model_id.clone(),
            source_dtype: request.source_dtype.clone(),
            vector: sample.vector.clone(),
            created_at_ms,
        })
        .collect();
    Ok((profile, samples))
}

pub fn trace_summaries_json(rows: &[Fhv1AuditTraceSummary]) -> Result<String, Fhv1StorageError> {
    serde_json::to_string(rows).map_err(Fhv1StorageError::new)
}

/// Separate frame so the inline kernel arrays are not part of an async state machine.
#[inline(never)]
pub fn stats_from_profile(profile: &Fhv1ProfileRecord) -> Box<Fhv1ProfileStats> {
    Box::new(Fhv1ProfileStats {
        min: *profile.min_vector.as_ref(),
        max: *profile.max_vector.as_ref(),
        mean: *profile.mean_vector.as_ref(),
        span: *profile.span_vector.as_ref(),
        variance: *profile.variance_vector.as_ref(),
        std_dev: *profile.std_dev_vector.as_ref(),
        movement_tier_codes: *profile.movement_tier_codes.as_ref(),
        quantiles: Fhv1Quantiles::standard(),
        sample_count: profile.sample_count,
        polarity: profile.polarity,
        metric: MovementMetric::Variance,
        cutoffs: Fhv1QuantileCutoffs {
            p25: 0.0,
            p75: 0.0,
            p90: 0.0,
        },
    })
}

pub(crate) fn box_f64_vector(values: &[f64; DIM]) -> Box<[f64; DIM]> {
    let boxed: Box<[f64]> = values.to_vec().into_boxed_slice();
    match boxed.try_into() {
        Ok(vector) => vector,
        Err(_) => unreachable!("fhv1 vector width is {DIM}"),
    }
}

pub(crate) fn box_u8_vector(values: &[u8; DIM]) -> Box<[u8; DIM]> {
    let boxed: Box<[u8]> = values.to_vec().into_boxed_slice();
    match <Box<[u8; DIM]>>::try_from(boxed) {
        Ok(vector) => vector,
        Err(_) => unreachable!("fhv1 tier width is {DIM}"),
    }
}

fn profile_from_stats(
    request: &Fhv1CalibrationRequest,
    profile_id: &str,
    version: u64,
    created_at_ms: i64,
    stats: &Fhv1ProfileStats,
) -> Fhv1ProfileRecord {
    Fhv1ProfileRecord {
        profile_id: profile_id.to_string(),
        policy_id: request.policy_id.clone(),
        version,
        polarity: request.polarity,
        normalize: request.normalize,
        use_rogue_mask_default: request.use_rogue_mask_default,
        sample_count: stats.sample_count,
        corpus_sha256: request.corpus_sha256,
        model_id: request.model_id.clone(),
        source_dtype: request.source_dtype.clone(),
        augmented_llm: request.augmented_llm,
        min_vector: box_f64_vector(&stats.min),
        max_vector: box_f64_vector(&stats.max),
        mean_vector: box_f64_vector(&stats.mean),
        span_vector: box_f64_vector(&stats.span),
        variance_vector: box_f64_vector(&stats.variance),
        std_dev_vector: box_f64_vector(&stats.std_dev),
        movement_tier_codes: box_u8_vector(&stats.movement_tier_codes),
        created_at_ms,
    }
}

#[cfg(test)]
mod tests {
    use sf_kernels::{Fhv1Quantiles, MovementMetric, DIM};

    use super::{assemble_calibration, stats_from_profile, Fhv1CalibrationRequest, Fhv1RawSample};

    #[test]
    fn stats_from_profile_defaults_to_variance_metric() {
        let req = Fhv1CalibrationRequest {
            policy_id: "python".to_string(),
            normalize: true,
            use_rogue_mask_default: false,
            polarity: 0,
            model_id: "BAAI/bge-m3".to_string(),
            source_dtype: "float64".to_string(),
            augmented_llm: false,
            corpus_sha256: [0x11; 32],
            metric: MovementMetric::Variance,
            quantiles: Fhv1Quantiles::standard(),
            samples: vec![Fhv1RawSample {
                sample_id: "s0".to_string(),
                source_ref: "unit".to_string(),
                strategy_tag: "full_doc".to_string(),
                raw_text: "hello".to_string(),
                text_sha256: [0x22; 32],
                vector: vec![0.1; DIM].into_boxed_slice().try_into().expect("dim"),
            }],
        };
        let (profile, _) = assemble_calibration(&req, 1, 100).expect("assemble");
        let stats = stats_from_profile(&profile);
        assert_eq!(stats.metric, MovementMetric::Variance);
    }
}
