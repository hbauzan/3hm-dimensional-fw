//! Arrow `=58.4.1` schemas for the four `fhv1_*` LanceDB tables.
//! `domain_hypercubes` is not part of this module.

use lancedb::arrow::arrow_schema::{DataType, Field, Schema};
use sf_kernels::DIM;
use std::sync::Arc;

pub const FHV1_CALIBRATION_SAMPLES_TABLE: &str = "fhv1_calibration_samples";
pub const FHV1_PROFILES_TABLE: &str = "fhv1_profiles";
pub const FHV1_BENCHMARK_RUNS_TABLE: &str = "fhv1_benchmark_runs";
pub const FHV1_AUDIT_TRACES_TABLE: &str = "fhv1_audit_traces";

pub fn fhv1_calibration_sample_schema() -> Arc<Schema> {
    Arc::new(Schema::new(vec![
        text("sample_id"),
        text("profile_id"),
        text("policy_id"),
        Field::new("version", DataType::UInt64, false),
        text("source_ref"),
        text("strategy_tag"),
        text("raw_text"),
        Field::new("text_sha256", DataType::FixedSizeBinary(32), false),
        Field::new("normalize", DataType::Boolean, false),
        text("model_id"),
        text("source_dtype"),
        f64_vector("vector"),
        Field::new("created_at_ms", DataType::Int64, false),
    ]))
}

pub fn fhv1_profile_schema() -> Arc<Schema> {
    Arc::new(Schema::new(vec![
        text("profile_id"),
        text("policy_id"),
        Field::new("version", DataType::UInt64, false),
        Field::new("polarity", DataType::UInt8, false),
        Field::new("normalize", DataType::Boolean, false),
        Field::new("use_rogue_mask_default", DataType::Boolean, false),
        Field::new("sample_count", DataType::UInt64, false),
        Field::new("corpus_sha256", DataType::FixedSizeBinary(32), false),
        text("model_id"),
        text("source_dtype"),
        Field::new("augmented_llm", DataType::Boolean, false),
        f64_vector("min_vector"),
        f64_vector("max_vector"),
        f64_vector("mean_vector"),
        f64_vector("span_vector"),
        f64_vector("variance_vector"),
        f64_vector("std_dev_vector"),
        Field::new(
            "movement_tier_codes",
            DataType::FixedSizeList(u8_item(), DIM as i32),
            false,
        ),
        Field::new("created_at_ms", DataType::Int64, false),
    ]))
}

pub fn fhv1_benchmark_run_schema() -> Arc<Schema> {
    Arc::new(Schema::new(vec![
        text("run_id"),
        text("profile_id"),
        text("policy_id"),
        text("dataset_name"),
        Field::new("dataset_sha256", DataType::FixedSizeBinary(32), false),
        text("eval_granularity"),
        Field::new("use_rogue_mask", DataType::Boolean, false),
        Field::new("total_inputs", DataType::UInt64, false),
        Field::new("total_chunks", DataType::UInt64, false),
        text("summary_metrics_json"),
        Field::new("created_at_ms", DataType::Int64, false),
    ]))
}

pub fn fhv1_audit_trace_schema() -> Arc<Schema> {
    Arc::new(Schema::new(vec![
        text("trace_id"),
        text("run_id"),
        text("source_kind"),
        text("profile_id"),
        text("policy_id"),
        text("category"),
        Field::new("expected_pass", DataType::Boolean, true),
        text("input_id"),
        text("raw_text"),
        text("eval_granularity"),
        Field::new("use_rogue_mask", DataType::Boolean, false),
        Field::new("chunk_index", DataType::UInt32, false),
        text("chunk_strategy"),
        text("chunk_text"),
        f64_vector("input_vector"),
        Field::new("chunk_passed", DataType::Boolean, false),
        Field::new("overall_passed", DataType::Boolean, false),
        Field::new("full_text_passed", DataType::Boolean, false),
        Field::new("all_chunks_passed", DataType::Boolean, false),
        Field::new("evaluated_dims", DataType::UInt16, false),
        Field::new("failed_dims_count", DataType::UInt16, false),
        Field::new("underflow_count", DataType::UInt16, false),
        Field::new("overflow_count", DataType::UInt16, false),
        Field::new("max_violation_delta", DataType::Float64, false),
        Field::new("mean_abs_delta_vs_mean", DataType::Float64, false),
        Field::new("eval_latency_ns", DataType::UInt64, false),
        Field::new("embedding_ms", DataType::Float64, false),
        Field::new("created_at_ms", DataType::Int64, false),
    ]))
}

fn text(name: &str) -> Field {
    Field::new(name, DataType::Utf8, false)
}

fn f64_item() -> Arc<Field> {
    Arc::new(Field::new("item", DataType::Float64, false))
}

fn u8_item() -> Arc<Field> {
    Arc::new(Field::new("item", DataType::UInt8, false))
}

fn f64_vector(name: &str) -> Field {
    Field::new(name, DataType::FixedSizeList(f64_item(), DIM as i32), false)
}
