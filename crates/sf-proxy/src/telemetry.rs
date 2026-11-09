//! Fail-closed breach envelope. Float fields exist on this cold path; the gate itself
//! compares raw binary32 values and records `to_bits` hex beside them.

use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct CoordinateBreachDto {
    pub dim: u16,
    pub observed_val: f32,
    pub observed_bits: String,
    pub lo_bound: f32,
    pub hi_bound: f32,
    pub delta_out_of_bounds: f32,
}

#[derive(Debug, Clone, Serialize)]
pub struct BreachMetricsDto {
    pub l1_prompt_cosine: f32,
    pub l1_prompt_cosine_bits: String,
    pub l1_threshold: f32,
    pub l2_clause_cosine: Option<f32>,
    pub l2_clause_cosine_bits: Option<String>,
    pub l2_threshold: f32,
    pub l3_affirmative_votes: Option<u16>,
    pub l3_required_quorum: Option<u16>,
    pub l3_evaluated_dimensions: Option<u16>,
    pub failing_coordinates: Vec<CoordinateBreachDto>,
}

#[derive(Debug, Clone, Serialize)]
pub struct BreachTelemetryDto {
    pub domain_id: String,
    pub domain_version: u64,
    pub polarity: &'static str,
    pub failing_tier: &'static str,
    pub l3_mode: &'static str,
    pub breaching_clause_index: Option<usize>,
    pub breaching_clause_sha256: Option<String>,
    pub total_clauses_extracted: usize,
    pub clauses_skipped: usize,
    pub gate_latency_ns: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub normalizer_segmenter_us: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub embedding_inference_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub simd_gate_kernel_us: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub total_pipeline_ms: Option<f64>,
    pub metrics: BreachMetricsDto,
}

#[derive(Debug, Clone, Serialize)]
pub struct BreachErrorEnvelope {
    pub error: BreachErrorBody,
}

#[derive(Debug, Clone, Serialize)]
pub struct BreachErrorBody {
    #[serde(rename = "type")]
    pub kind: &'static str,
    pub code: &'static str,
    pub message: String,
    pub telemetry: BreachTelemetryDto,
}

pub fn f32_hex(value: f32) -> String {
    format!("0x{:08x}", value.to_bits())
}
