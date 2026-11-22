//! Shared `fhv1` overlap gate, batched chunk preparation, metrics aggregation, and persistence.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::time::Instant;

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sf_kernels::{evaluate_fhv1_batch, DimBoundStatus, Fhv1EvalGranularity, DIM};
use sf_storage::{Fhv1AuditTrace, Fhv1BenchmarkRun, Fhv1ProfileRecord, Fhv1Store};
use sha2::{Digest, Sha256};
use unicode_normalization::UnicodeNormalization;

use crate::embedder::BatchEmbedderClient;
use crate::fhv1_pipeline::{
    box_row, embed_raw_f64_batched, expand_for_granularity, expand_text_multi_granularity,
    ExpandedChunk,
};

pub const CATEGORIES: [&str; 4] = [
    "IN_DOMAIN_VALID",
    "OUT_OF_DOMAIN_BENIGN",
    "HYBRID_BOUNDARY",
    "ADVERSARIAL_FUZZING",
];

pub const ALL_GRANULARITIES: [Fhv1EvalGranularity; 3] = [
    Fhv1EvalGranularity::FullOnly,
    Fhv1EvalGranularity::Clauses,
    Fhv1EvalGranularity::FullMirror,
];

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
pub struct Fhv1Prompt {
    pub input_id: String,
    pub category: String,
    pub expected_pass: bool,
    pub text: String,
    #[serde(default)]
    pub subtype: Option<String>,
}

#[derive(Debug, Clone)]
pub struct PreparedView {
    pub granularity: Fhv1EvalGranularity,
    pub chunks: Vec<ExpandedChunk>,
    pub vectors: Vec<Box<[f64; DIM]>>,
    pub embedding_ms: f64,
}

#[derive(Debug, Clone)]
pub struct PreparedPrompt {
    pub prompt: Fhv1Prompt,
    pub views: Vec<PreparedView>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ConfusionCounts {
    pub tp: u64,
    pub tn: u64,
    pub fp: u64,
    pub fn_: u64,
}

#[derive(Debug, Clone)]
pub struct ScoredView {
    pub overall_passed: bool,
    pub full_text_passed: bool,
    pub all_chunks_passed: bool,
    pub evaluated_dims: u16,
    pub chunk_failed_dims: Vec<u16>,
    pub chunk_passed: Vec<bool>,
    pub underflow: Vec<u16>,
    pub overflow: Vec<u16>,
    pub max_violation_delta: Vec<f64>,
    pub mean_abs_delta_vs_mean: Vec<f64>,
    pub violated_dims: Vec<Vec<u16>>,
    pub eval_latency_ns: u64,
    pub embedding_ms: f64,
}

pub fn nfkc_lower(text: &str) -> String {
    text.nfkc().collect::<String>().to_lowercase()
}

fn digest(text: &str) -> [u8; 32] {
    let hashed = Sha256::digest(text.as_bytes());
    let mut out = [0u8; 32];
    out.copy_from_slice(hashed.as_slice());
    out
}

fn remember(set: &mut BTreeSet<[u8; 32]>, text: &str) {
    set.insert(digest(text));
    set.insert(digest(&nfkc_lower(text)));
}

/// Remember texts that are already calibration surfaces (stored chunks or raw inputs).
pub fn forbid_surface(set: &mut BTreeSet<[u8; 32]>, texts: &[impl AsRef<str>]) {
    for text in texts {
        remember(set, text.as_ref());
    }
}

/// Exact and NFKC-lowercase digests of calibration inputs and their expanded chunks.
pub fn forbidden_digests(texts: &[impl AsRef<str>]) -> BTreeSet<[u8; 32]> {
    let mut set = BTreeSet::new();
    for text in texts {
        let raw = text.as_ref();
        remember(&mut set, raw);
        for chunk in expand_text_multi_granularity(raw) {
            remember(&mut set, &chunk.text);
        }
    }
    set
}

/// Prompt ids whose exact text or NFKC-lowercase form hits the calibration set.
pub fn overlap_ids<'a>(forbidden: &BTreeSet<[u8; 32]>, prompts: &'a [Fhv1Prompt]) -> Vec<&'a str> {
    prompts
        .iter()
        .filter(|prompt| {
            forbidden.contains(&digest(&prompt.text))
                || forbidden.contains(&digest(&nfkc_lower(&prompt.text)))
        })
        .map(|prompt| prompt.input_id.as_str())
        .collect()
}

pub fn confusion_from_flags(expected_pass: &[bool], overall_passed: &[bool]) -> ConfusionCounts {
    let mut counts = ConfusionCounts {
        tp: 0,
        tn: 0,
        fp: 0,
        fn_: 0,
    };
    for (expected, passed) in expected_pass.iter().zip(overall_passed.iter()) {
        match (*expected, *passed) {
            (true, true) => counts.tp += 1,
            (true, false) => counts.fn_ += 1,
            (false, false) => counts.tn += 1,
            (false, true) => counts.fp += 1,
        }
    }
    counts
}

fn rate(numerator: u64, denominator: u64) -> Value {
    if denominator == 0 {
        Value::Null
    } else {
        json!(numerator as f64 / denominator as f64)
    }
}

pub fn confusion_json(counts: ConfusionCounts) -> Value {
    let total = counts.tp + counts.tn + counts.fp + counts.fn_;
    let precision_den = counts.tp + counts.fp;
    let recall_den = counts.tp + counts.fn_;
    let precision = if precision_den == 0 {
        None
    } else {
        Some(counts.tp as f64 / precision_den as f64)
    };
    let recall = if recall_den == 0 {
        None
    } else {
        Some(counts.tp as f64 / recall_den as f64)
    };
    let f1 = match (precision, recall) {
        (Some(p), Some(r)) if p + r > 0.0 => Some(2.0 * p * r / (p + r)),
        (Some(_), Some(_)) => Some(0.0),
        _ => None,
    };
    json!({
        "tp": counts.tp,
        "tn": counts.tn,
        "fp": counts.fp,
        "fn": counts.fn_,
        "accuracy": rate(counts.tp + counts.tn, total),
        "precision": precision.map(|value| json!(value)).unwrap_or(Value::Null),
        "recall": recall.map(|value| json!(value)).unwrap_or(Value::Null),
        "f1": f1.map(|value| json!(value)).unwrap_or(Value::Null),
        "far_fpr": rate(counts.fp, counts.fp + counts.tn),
        "frr_fnr": rate(counts.fn_, counts.fn_ + counts.tp),
    })
}

pub fn granularity_name(granularity: Fhv1EvalGranularity) -> &'static str {
    match granularity {
        Fhv1EvalGranularity::FullOnly => "full_only",
        Fhv1EvalGranularity::Clauses => "clauses",
        Fhv1EvalGranularity::FullMirror => "full_mirror",
    }
}

pub fn parse_granularity(text: &str) -> Result<Fhv1EvalGranularity, String> {
    match text {
        "full_only" => Ok(Fhv1EvalGranularity::FullOnly),
        "clauses" => Ok(Fhv1EvalGranularity::Clauses),
        "full_mirror" => Ok(Fhv1EvalGranularity::FullMirror),
        other => Err(format!("unknown fhv1 granularity {other}")),
    }
}

/// Embed every distinct chunk once across all granularities, then fan vectors out to all 3 views.
pub async fn prepare_prompts<E>(
    embedder: &E,
    prompts: &[Fhv1Prompt],
    normalize: bool,
) -> Result<Vec<PreparedPrompt>, String>
where
    E: BatchEmbedderClient + ?Sized,
{
    prepare_prompts_for(embedder, prompts, normalize, &ALL_GRANULARITIES).await
}

/// Embed every distinct chunk once across `granularities`, bounded at `EMBED_BATCH_SIZE` per call.
pub async fn prepare_prompts_for<E>(
    embedder: &E,
    prompts: &[Fhv1Prompt],
    normalize: bool,
    granularities: &[Fhv1EvalGranularity],
) -> Result<Vec<PreparedPrompt>, String>
where
    E: BatchEmbedderClient + ?Sized,
{
    if granularities.is_empty() {
        return Err("fhv1 prepare_prompts_for requires at least one granularity".to_string());
    }
    let mut order: Vec<String> = Vec::new();
    let mut index_of: HashMap<String, usize> = HashMap::new();
    let mut views_chunks = Vec::with_capacity(prompts.len());
    for prompt in prompts {
        let mut views = Vec::with_capacity(granularities.len());
        for &granularity in granularities {
            let chunks = expand_for_granularity(&prompt.text, granularity);
            if chunks.is_empty() {
                return Err(format!(
                    "prompt {} expanded to zero chunks",
                    prompt.input_id
                ));
            }
            let mut chunk_indices = Vec::with_capacity(chunks.len());
            for chunk in &chunks {
                let index = if let Some(&existing) = index_of.get(&chunk.text) {
                    existing
                } else {
                    let next = order.len();
                    index_of.insert(chunk.text.clone(), next);
                    order.push(chunk.text.clone());
                    next
                };
                chunk_indices.push(index);
            }
            views.push((granularity, chunks, chunk_indices));
        }
        views_chunks.push(views);
    }
    let text_refs: Vec<&str> = order.iter().map(String::as_str).collect();
    let embedded = embed_raw_f64_batched(embedder, &text_refs, normalize).await?;

    let mut prepared = Vec::with_capacity(prompts.len());
    for (prompt_index, prompt) in prompts.iter().enumerate() {
        let mut views = Vec::with_capacity(granularities.len());
        for (granularity, chunks, chunk_indices) in &views_chunks[prompt_index] {
            let mut view_vectors = Vec::with_capacity(chunks.len());
            let mut seen_indices = BTreeSet::new();
            let mut view_embed_ms = 0.0f64;
            for &index in chunk_indices {
                view_vectors.push(box_row(embedded.vectors[index].as_ref()));
                if seen_indices.insert(index) {
                    view_embed_ms += embedded.per_item_ms[index];
                }
            }
            views.push(PreparedView {
                granularity: *granularity,
                chunks: chunks.clone(),
                vectors: view_vectors,
                embedding_ms: view_embed_ms,
            });
        }
        prepared.push(PreparedPrompt {
            prompt: prompt.clone(),
            views,
        });
    }
    Ok(prepared)
}

pub fn score_view(
    profile: &Fhv1ProfileRecord,
    view: &PreparedView,
    use_rogue_mask: bool,
) -> Result<ScoredView, String> {
    let stats = sf_storage::stats_from_profile(profile);
    let rows: Vec<&[f64]> = view.vectors.iter().map(|row| row.as_slice()).collect();
    let started = Instant::now();
    let batch = evaluate_fhv1_batch(&stats, &rows, view.granularity, use_rogue_mask)
        .map_err(|err| err.to_string())?;
    let eval_latency_ns = u64::try_from(started.elapsed().as_nanos()).unwrap_or(u64::MAX);
    let mut violated_dims = Vec::with_capacity(batch.chunks.len());
    for chunk in &batch.chunks {
        let mut dims = Vec::new();
        for (dim, comparison) in chunk.dimensions.iter().enumerate() {
            if matches!(
                comparison.status,
                DimBoundStatus::Underflow | DimBoundStatus::Overflow
            ) {
                dims.push(u16::try_from(dim).unwrap_or(u16::MAX));
            }
        }
        violated_dims.push(dims);
    }
    Ok(ScoredView {
        overall_passed: batch.overall_passed,
        full_text_passed: batch.full_text_passed,
        all_chunks_passed: batch.all_chunks_passed,
        evaluated_dims: batch
            .chunks
            .first()
            .map(|chunk| chunk.evaluated_dims)
            .unwrap_or(0),
        chunk_failed_dims: batch
            .chunks
            .iter()
            .map(|chunk| chunk.failed_dims_count)
            .collect(),
        chunk_passed: batch
            .chunks
            .iter()
            .map(|chunk| chunk.chunk_passed)
            .collect(),
        underflow: batch
            .chunks
            .iter()
            .map(|chunk| chunk.underflow_count)
            .collect(),
        overflow: batch
            .chunks
            .iter()
            .map(|chunk| chunk.overflow_count)
            .collect(),
        max_violation_delta: batch
            .chunks
            .iter()
            .map(|chunk| chunk.max_violation_delta)
            .collect(),
        mean_abs_delta_vs_mean: batch
            .chunks
            .iter()
            .map(|chunk| chunk.mean_abs_delta_vs_mean)
            .collect(),
        violated_dims,
        eval_latency_ns,
        embedding_ms: view.embedding_ms,
    })
}

pub struct RunMetrics {
    pub counts: ConfusionCounts,
    pub summary: Value,
    pub comparison_row: Value,
}

/// Hyndman-Fan type 7: `rank = p * (n - 1)` with linear interpolation on a non-empty sorted slice.
fn linear_quantile(sorted: &[f64], p: f64) -> f64 {
    debug_assert!(!sorted.is_empty());
    let n = sorted.len();
    if n == 1 {
        return sorted[0];
    }
    let rank = p * (n as f64 - 1.0);
    let lo = (rank.floor() as usize).min(n - 1);
    let hi = (rank.ceil() as usize).min(n - 1);
    let weight = rank - lo as f64;
    sorted[lo] * (1.0 - weight) + sorted[hi] * weight
}

fn histogram_json(counts: &BTreeMap<u16, u64>) -> BTreeMap<String, u64> {
    counts
        .iter()
        .map(|(key, value)| (key.to_string(), *value))
        .collect()
}

fn category_stats_json(
    failed_counts: &[u16],
    prompt_count: u64,
    prompt_zero_fail_count: u64,
) -> Value {
    let chunk_count = failed_counts.len() as u64;
    let zero_fail_count = failed_counts.iter().filter(|&&count| count == 0).count() as u64;
    if failed_counts.is_empty() {
        return json!({
            "min": Value::Null,
            "p25": Value::Null,
            "median": Value::Null,
            "p75": Value::Null,
            "p90": Value::Null,
            "max": Value::Null,
            "zero_fail_count": 0,
            "chunk_count": 0,
            "prompt_count": prompt_count,
            "prompt_zero_fail_count": prompt_zero_fail_count,
        });
    }
    let mut sorted_u16 = failed_counts.to_vec();
    sorted_u16.sort_unstable();
    let sorted_f64: Vec<f64> = sorted_u16.iter().map(|&v| f64::from(v)).collect();
    json!({
        "min": sorted_u16[0],
        "p25": linear_quantile(&sorted_f64, 0.25),
        "median": linear_quantile(&sorted_f64, 0.50),
        "p75": linear_quantile(&sorted_f64, 0.75),
        "p90": linear_quantile(&sorted_f64, 0.90),
        "max": sorted_u16[sorted_u16.len() - 1],
        "zero_fail_count": zero_fail_count,
        "chunk_count": chunk_count,
        "prompt_count": prompt_count,
        "prompt_zero_fail_count": prompt_zero_fail_count,
    })
}

struct SubtypeAccum {
    category: String,
    expected: Vec<bool>,
    passed: Vec<bool>,
}

fn per_subtype_json(
    prompts: &[Fhv1Prompt],
    scored: &[ScoredView],
) -> serde_json::Map<String, Value> {
    let mut grouped: BTreeMap<String, SubtypeAccum> = BTreeMap::new();
    for (prompt, row) in prompts.iter().zip(scored.iter()) {
        let Some(subtype) = prompt
            .subtype
            .as_deref()
            .map(str::trim)
            .filter(|s| !s.is_empty())
        else {
            continue;
        };
        let entry = grouped
            .entry(subtype.to_string())
            .or_insert_with(|| SubtypeAccum {
                category: prompt.category.clone(),
                expected: Vec::new(),
                passed: Vec::new(),
            });
        entry.expected.push(prompt.expected_pass);
        entry.passed.push(row.overall_passed);
    }
    let mut out = serde_json::Map::new();
    for (subtype, accum) in grouped {
        let total = accum.passed.len() as u64;
        let passed = accum.passed.iter().filter(|&&flag| flag).count() as u64;
        let failed = total - passed;
        let counts = confusion_from_flags(&accum.expected, &accum.passed);
        out.insert(
            subtype,
            json!({
                "category": accum.category,
                "total": total,
                "passed": passed,
                "failed": failed,
                "confusion": confusion_json(counts),
            }),
        );
    }
    out
}

fn latency_json(scored: &[ScoredView]) -> Value {
    if scored.is_empty() {
        return json!({
            "prompt_eval_p50_ns": Value::Null,
            "prompt_eval_p99_ns": Value::Null,
            "prompt_embed_p50_ms": Value::Null,
            "prompt_embed_p99_ms": Value::Null,
            "prompt_total_p50_ms": Value::Null,
            "prompt_total_p99_ms": Value::Null,
            "chunks_per_sec": Value::Null,
        });
    }
    let mut eval_ns = Vec::with_capacity(scored.len());
    let mut embed_ms = Vec::with_capacity(scored.len());
    let mut total_ms = Vec::with_capacity(scored.len());
    let mut total_chunks = 0u64;
    let mut total_sec = 0.0f64;
    for row in scored {
        let eval_f64 = row.eval_latency_ns as f64;
        let embed_f64 = if row.embedding_ms.is_finite() && row.embedding_ms >= 0.0 {
            row.embedding_ms
        } else {
            0.0
        };
        let prompt_total_ms = embed_f64 + (eval_f64 / 1_000_000.0);
        eval_ns.push(eval_f64);
        embed_ms.push(embed_f64);
        total_ms.push(prompt_total_ms);
        total_chunks += row.chunk_passed.len() as u64;
        total_sec += prompt_total_ms / 1_000.0;
    }
    eval_ns.sort_by(f64::total_cmp);
    embed_ms.sort_by(f64::total_cmp);
    total_ms.sort_by(f64::total_cmp);
    let chunks_per_sec = if total_sec > 0.0 {
        json!(total_chunks as f64 / total_sec)
    } else {
        Value::Null
    };
    json!({
        "prompt_eval_p50_ns": linear_quantile(&eval_ns, 0.50),
        "prompt_eval_p99_ns": linear_quantile(&eval_ns, 0.99),
        "prompt_embed_p50_ms": linear_quantile(&embed_ms, 0.50),
        "prompt_embed_p99_ms": linear_quantile(&embed_ms, 0.99),
        "prompt_total_p50_ms": linear_quantile(&total_ms, 0.50),
        "prompt_total_p99_ms": linear_quantile(&total_ms, 0.99),
        "chunks_per_sec": chunks_per_sec,
    })
}

pub fn metrics_for(
    prompts: &[Fhv1Prompt],
    scored: &[ScoredView],
    granularity: Fhv1EvalGranularity,
    use_rogue_mask: bool,
    tier_codes: &[u8; DIM],
) -> RunMetrics {
    let expected: Vec<bool> = prompts.iter().map(|prompt| prompt.expected_pass).collect();
    let passed: Vec<bool> = scored.iter().map(|row| row.overall_passed).collect();
    let counts = confusion_from_flags(&expected, &passed);

    let mut per_category = serde_json::Map::new();
    let mut histogram_by_category = serde_json::Map::new();
    let mut stats_by_category = serde_json::Map::new();
    for category in CATEGORIES {
        let mut category_expected = Vec::new();
        let mut category_passed = Vec::new();
        let mut category_histogram: BTreeMap<u16, u64> = BTreeMap::new();
        let mut category_failed_dims = Vec::new();
        let mut prompt_zero_fail_count = 0u64;
        for (prompt, row) in prompts.iter().zip(scored.iter()) {
            if prompt.category != category {
                continue;
            }
            category_expected.push(prompt.expected_pass);
            category_passed.push(row.overall_passed);
            if row.overall_passed {
                prompt_zero_fail_count += 1;
            }
            for &failed in &row.chunk_failed_dims {
                *category_histogram.entry(failed).or_insert(0) += 1;
                category_failed_dims.push(failed);
            }
        }
        per_category.insert(
            category.to_string(),
            confusion_json(confusion_from_flags(&category_expected, &category_passed)),
        );
        histogram_by_category.insert(
            category.to_string(),
            json!(histogram_json(&category_histogram)),
        );
        stats_by_category.insert(
            category.to_string(),
            category_stats_json(
                &category_failed_dims,
                category_expected.len() as u64,
                prompt_zero_fail_count,
            ),
        );
    }

    let per_subtype = per_subtype_json(prompts, scored);

    let mut histogram: BTreeMap<u16, u64> = BTreeMap::new();
    let mut in_domain_fail = vec![0u64; DIM];
    let mut oob_catch = vec![0u64; DIM];
    for (prompt, row) in prompts.iter().zip(scored.iter()) {
        for &failed in &row.chunk_failed_dims {
            *histogram.entry(failed).or_insert(0) += 1;
        }
        if row.overall_passed {
            continue;
        }
        let target = if prompt.category == "IN_DOMAIN_VALID" {
            &mut in_domain_fail
        } else if !prompt.expected_pass {
            &mut oob_catch
        } else {
            continue;
        };
        for dims in &row.violated_dims {
            for dim in dims {
                let index = usize::from(*dim);
                if index < target.len() {
                    target[index] += 1;
                }
            }
        }
    }

    let summary = json!({
        "confusion": confusion_json(counts),
        "per_category": per_category,
        "per_subtype": per_subtype,
        "failed_dims_count_histogram": histogram_json(&histogram),
        "failed_dims_count_histogram_by_category": histogram_by_category,
        "failed_dims_stats_by_category": stats_by_category,
        "attribution": {
            "in_domain_fail_counts": in_domain_fail,
            "oob_catch_counts": oob_catch,
            "movement_tier_codes": tier_codes.to_vec(),
        },
        "latency": latency_json(scored),
    });
    let comparison_row = json!({
        "granularity": granularity_name(granularity),
        "use_rogue_mask": use_rogue_mask,
        "evaluated_dims": scored.first().map(|row| row.evaluated_dims).unwrap_or(0),
        "confusion": confusion_json(counts),
    });
    RunMetrics {
        counts,
        summary,
        comparison_row,
    }
}

pub fn attach_comparison(summary: &mut Value, comparison: &[Value]) {
    if let Some(object) = summary.as_object_mut() {
        object.insert("granularity_comparison".to_string(), json!(comparison));
    }
}

pub struct PersistRequest<'a> {
    pub granularity: Fhv1EvalGranularity,
    pub use_rogue_mask: bool,
    pub dataset_name: &'a str,
    pub dataset_sha256: [u8; 32],
    pub summary: &'a Value,
    pub run_id: &'a str,
    pub created_at_ms: i64,
}

pub(crate) fn build_benchmark_run(
    profile: &Fhv1ProfileRecord,
    total_inputs: u64,
    scored: &[ScoredView],
    request: &PersistRequest<'_>,
) -> Fhv1BenchmarkRun {
    let total_chunks: u64 = scored.iter().map(|row| row.chunk_passed.len() as u64).sum();
    Fhv1BenchmarkRun {
        run_id: request.run_id.to_string(),
        profile_id: profile.profile_id.clone(),
        policy_id: profile.policy_id.clone(),
        dataset_name: request.dataset_name.to_string(),
        dataset_sha256: request.dataset_sha256,
        eval_granularity: granularity_name(request.granularity).to_string(),
        use_rogue_mask: request.use_rogue_mask,
        total_inputs,
        total_chunks,
        summary_metrics_json: request.summary.to_string(),
        created_at_ms: request.created_at_ms,
    }
}

pub async fn persist_benchmark_run(
    store: &Fhv1Store,
    profile: &Fhv1ProfileRecord,
    prepared: &[PreparedPrompt],
    scored: &[ScoredView],
    request: &PersistRequest<'_>,
) -> Result<(), String> {
    if prepared.len() != scored.len() {
        return Err(format!(
            "prepared prompt count ({}) does not match scored count ({})",
            prepared.len(),
            scored.len()
        ));
    }
    let run = build_benchmark_run(profile, prepared.len() as u64, scored, request);
    store
        .save_benchmark_run(&run)
        .await
        .map_err(|err| err.to_string())?;
    let granularity_label = granularity_name(request.granularity);
    const TRACE_WRITE_BATCH: usize = 4096;
    let mut traces = Vec::with_capacity(TRACE_WRITE_BATCH);
    for (prepared_prompt, row) in prepared.iter().zip(scored.iter()) {
        let view = select_view(prepared_prompt, request.granularity)?;
        if view.chunks.len() != row.chunk_passed.len() || view.vectors.len() != view.chunks.len() {
            return Err(format!(
                "scored chunk count mismatch for prompt {}",
                prepared_prompt.prompt.input_id
            ));
        }
        let trace_id = format!("{}-{}", request.run_id, prepared_prompt.prompt.input_id);
        for (index, chunk) in view.chunks.iter().enumerate() {
            traces.push(Fhv1AuditTrace {
                trace_id: trace_id.clone(),
                run_id: request.run_id.to_string(),
                source_kind: "BENCHMARK".to_string(),
                profile_id: profile.profile_id.clone(),
                policy_id: profile.policy_id.clone(),
                category: prepared_prompt.prompt.category.clone(),
                expected_pass: Some(prepared_prompt.prompt.expected_pass),
                input_id: prepared_prompt.prompt.input_id.clone(),
                raw_text: prepared_prompt.prompt.text.clone(),
                eval_granularity: granularity_label.to_string(),
                use_rogue_mask: request.use_rogue_mask,
                chunk_index: u32::try_from(index).unwrap_or(u32::MAX),
                chunk_strategy: chunk.strategy_tag.to_string(),
                chunk_text: chunk.text.clone(),
                input_vector: view.vectors[index].clone(),
                chunk_passed: row.chunk_passed[index],
                overall_passed: row.overall_passed,
                full_text_passed: row.full_text_passed,
                all_chunks_passed: row.all_chunks_passed,
                evaluated_dims: row.evaluated_dims,
                failed_dims_count: row.chunk_failed_dims[index],
                underflow_count: row.underflow[index],
                overflow_count: row.overflow[index],
                max_violation_delta: row.max_violation_delta[index],
                mean_abs_delta_vs_mean: row.mean_abs_delta_vs_mean[index],
                eval_latency_ns: row.eval_latency_ns,
                embedding_ms: view.embedding_ms,
                created_at_ms: request.created_at_ms,
            });
            if traces.len() >= TRACE_WRITE_BATCH {
                store
                    .append_audit_traces(&traces)
                    .await
                    .map_err(|err| err.to_string())?;
                traces.clear();
            }
        }
    }
    if !traces.is_empty() {
        store
            .append_audit_traces(&traces)
            .await
            .map_err(|err| err.to_string())?;
    }
    Ok(())
}

pub fn select_view(
    prepared: &PreparedPrompt,
    granularity: Fhv1EvalGranularity,
) -> Result<&PreparedView, String> {
    prepared
        .views
        .iter()
        .find(|view| view.granularity == granularity)
        .ok_or_else(|| format!("missing {} view", granularity_name(granularity)))
}

#[cfg(test)]
mod tests {
    use std::sync::Mutex;

    use async_trait::async_trait;
    use sf_kernels::{AlignedVec1024, Fhv1EvalGranularity, DIM};

    use super::{
        attach_comparison, metrics_for, parse_granularity, prepare_prompts_for, select_view,
        Fhv1Prompt, PreparedPrompt, PreparedView, ScoredView, CATEGORIES,
    };
    use crate::embedder::BatchEmbedderClient;
    use crate::fhv1_pipeline::{ExpandedChunk, EMBED_BATCH_SIZE};

    fn prompt(id: &str, category: &str, expected_pass: bool, subtype: Option<&str>) -> Fhv1Prompt {
        Fhv1Prompt {
            input_id: id.to_string(),
            category: category.to_string(),
            expected_pass,
            text: format!("{id} body text"),
            subtype: subtype.map(str::to_string),
        }
    }

    fn scored_chunks(
        overall_passed: bool,
        chunk_failed_dims: Vec<u16>,
        violated: Vec<Vec<u16>>,
        eval_latency_ns: u64,
        embedding_ms: f64,
    ) -> ScoredView {
        let len = chunk_failed_dims.len();
        ScoredView {
            overall_passed,
            full_text_passed: chunk_failed_dims.first().copied() == Some(0),
            all_chunks_passed: chunk_failed_dims.iter().all(|&c| c == 0),
            evaluated_dims: 1024,
            chunk_passed: chunk_failed_dims.iter().map(|&c| c == 0).collect(),
            underflow: vec![0; len],
            overflow: chunk_failed_dims.clone(),
            chunk_failed_dims,
            max_violation_delta: vec![0.0; len],
            mean_abs_delta_vs_mean: vec![0.0; len],
            violated_dims: violated,
            eval_latency_ns,
            embedding_ms,
        }
    }

    fn scored(passed: bool, failed_dims: u16, violated: &[u16]) -> ScoredView {
        scored_chunks(passed, vec![failed_dims], vec![violated.to_vec()], 7, 1.0)
    }

    fn f64_bits(value: &serde_json::Value) -> u64 {
        value.as_f64().expect("rate").to_bits()
    }

    #[test]
    fn metrics_cover_histogram_by_category_percentiles_subtypes_and_latency() {
        let prompts = vec![
            prompt("p0", "IN_DOMAIN_VALID", true, Some("short_en")),
            prompt("p1", "IN_DOMAIN_VALID", true, Some("short_en")),
            prompt("p2", "OUT_OF_DOMAIN_BENIGN", false, Some("clinc_oos")),
            prompt("p3", "OUT_OF_DOMAIN_BENIGN", false, Some("clinc_oos")),
            prompt("p4", "HYBRID_BOUNDARY", true, Some("dilution_50_50")),
            prompt("p5", "ADVERSARIAL_FUZZING", false, None),
        ];
        let scored = vec![
            scored_chunks(true, vec![0, 0], vec![vec![], vec![]], 100, 1.0),
            scored_chunks(
                false,
                vec![0, 2, 4],
                vec![vec![], vec![4], vec![4]],
                200,
                2.0,
            ),
            scored_chunks(false, vec![3], vec![vec![4, 7]], 300, 3.0),
            scored_chunks(true, vec![0], vec![vec![]], 400, 4.0),
            scored_chunks(false, vec![1], vec![vec![9]], 500, 5.0),
            scored_chunks(false, vec![3], vec![vec![7]], 600, 6.0),
        ];
        let tier_codes = [0u8; DIM];
        let mut metrics = metrics_for(
            &prompts,
            &scored,
            Fhv1EvalGranularity::Clauses,
            true,
            &tier_codes,
        );
        let confusion = &metrics.summary["confusion"];
        assert_eq!(confusion["tp"], 1);
        assert_eq!(confusion["tn"], 2);
        assert_eq!(confusion["fp"], 1);
        assert_eq!(confusion["fn"], 2);
        let precision = 0.5f64;
        let recall = 1.0f64 / 3.0;
        let f1 = 2.0 * precision * recall / (precision + recall);
        assert_eq!(f64_bits(&confusion["precision"]), precision.to_bits());
        assert_eq!(f64_bits(&confusion["recall"]), recall.to_bits());
        assert_eq!(f64_bits(&confusion["f1"]), f1.to_bits());
        assert_eq!(f64_bits(&confusion["far_fpr"]), (1.0f64 / 3.0).to_bits());
        assert_eq!(f64_bits(&confusion["frr_fnr"]), (2.0f64 / 3.0).to_bits());

        let in_domain = &metrics.summary["per_category"]["IN_DOMAIN_VALID"];
        assert_eq!(f64_bits(&in_domain["precision"]), 1.0f64.to_bits());
        assert_eq!(f64_bits(&in_domain["recall"]), 0.5f64.to_bits());
        assert!(in_domain["far_fpr"].is_null());
        assert_eq!(f64_bits(&in_domain["frr_fnr"]), 0.5f64.to_bits());

        let out_of_domain = &metrics.summary["per_category"]["OUT_OF_DOMAIN_BENIGN"];
        assert_eq!(f64_bits(&out_of_domain["far_fpr"]), 0.5f64.to_bits());

        // Global histogram sums cleanly across all per-category histograms.
        let histogram = metrics.summary["failed_dims_count_histogram"]
            .as_object()
            .expect("global hist");
        let by_cat = metrics.summary["failed_dims_count_histogram_by_category"]
            .as_object()
            .expect("cat hist");
        for category in CATEGORIES {
            assert!(by_cat.contains_key(category), "missing {category}");
        }
        assert_eq!(by_cat["IN_DOMAIN_VALID"]["0"], 3);
        assert_eq!(by_cat["IN_DOMAIN_VALID"]["2"], 1);
        assert_eq!(by_cat["IN_DOMAIN_VALID"]["4"], 1);
        assert_eq!(histogram["0"], 4);
        assert_eq!(histogram["1"], 1);
        assert_eq!(histogram["2"], 1);
        assert_eq!(histogram["3"], 2);
        assert_eq!(histogram["4"], 1);
        for (bucket, global_count) in histogram {
            let cat_sum: u64 = CATEGORIES
                .iter()
                .map(|cat| {
                    by_cat[*cat]
                        .get(bucket)
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0)
                })
                .sum();
            assert_eq!(
                cat_sum,
                global_count.as_u64().expect("count"),
                "bucket {bucket}"
            );
        }

        // Per-category stats: IN_DOMAIN_VALID sorted chunk failed_dims = [0, 0, 0, 2, 4].
        let stats_by_cat = metrics.summary["failed_dims_stats_by_category"]
            .as_object()
            .expect("stats_by_cat");
        for category in CATEGORIES {
            assert!(
                stats_by_cat.contains_key(category),
                "missing stats {category}"
            );
        }
        let in_stats = &stats_by_cat["IN_DOMAIN_VALID"];
        assert_eq!(in_stats["min"], 0);
        assert_eq!(f64_bits(&in_stats["p25"]), 0.0f64.to_bits());
        assert_eq!(f64_bits(&in_stats["median"]), 0.0f64.to_bits());
        assert_eq!(f64_bits(&in_stats["p75"]), 2.0f64.to_bits());
        assert_eq!(
            f64_bits(&in_stats["p90"]),
            (2.0f64 * 0.4 + 4.0f64 * 0.6).to_bits()
        );
        assert_eq!(in_stats["max"], 4);
        assert_eq!(in_stats["zero_fail_count"], 3);
        assert_eq!(in_stats["chunk_count"], 5);
        assert_eq!(in_stats["prompt_count"], 2);
        assert_eq!(in_stats["prompt_zero_fail_count"], 1);

        // Per-subtype aggregation ignores None and computes confusion.
        let per_subtype = metrics.summary["per_subtype"]
            .as_object()
            .expect("subtypes");
        assert_eq!(per_subtype.len(), 3);
        assert_eq!(per_subtype["short_en"]["category"], "IN_DOMAIN_VALID");
        assert_eq!(per_subtype["short_en"]["total"], 2);
        assert_eq!(per_subtype["short_en"]["passed"], 1);
        assert_eq!(per_subtype["short_en"]["failed"], 1);
        assert_eq!(per_subtype["short_en"]["confusion"]["tp"], 1);
        assert_eq!(per_subtype["short_en"]["confusion"]["fn"], 1);
        assert_eq!(per_subtype["clinc_oos"]["total"], 2);
        assert_eq!(per_subtype["clinc_oos"]["confusion"]["tn"], 1);
        assert_eq!(per_subtype["clinc_oos"]["confusion"]["fp"], 1);
        assert_eq!(per_subtype["dilution_50_50"]["total"], 1);
        assert_eq!(per_subtype["dilution_50_50"]["failed"], 1);

        // Latency stats over 6 prompts, 9 total chunks.
        let latency = &metrics.summary["latency"];
        assert_eq!(f64_bits(&latency["prompt_eval_p50_ns"]), 350.0f64.to_bits());
        assert_eq!(
            f64_bits(&latency["prompt_eval_p99_ns"]),
            (500.0f64 * 0.05 + 600.0f64 * 0.95).to_bits()
        );
        assert_eq!(f64_bits(&latency["prompt_embed_p50_ms"]), 3.5f64.to_bits());
        assert!(latency["prompt_total_p50_ms"].as_f64().expect("p50") > 3.5);
        assert!(latency["chunks_per_sec"].as_f64().expect("cps") > 0.0);

        // Attribution sanity
        let oob = metrics.summary["attribution"]["oob_catch_counts"]
            .as_array()
            .expect("oob");
        assert_eq!(oob.len(), DIM);
        assert_eq!(oob[4], 1);
        assert_eq!(oob[7], 2);
        assert_eq!(
            metrics.summary["attribution"]["in_domain_fail_counts"][4],
            2
        );
        assert_eq!(
            metrics.summary["attribution"]["in_domain_fail_counts"][9],
            0
        );

        let comparison = metrics.comparison_row.clone();
        attach_comparison(&mut metrics.summary, &[comparison]);
        let rows = metrics.summary["granularity_comparison"]
            .as_array()
            .expect("comparison");
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0]["granularity"], "clauses");
        assert_eq!(rows[0]["use_rogue_mask"], true);
        assert_eq!(rows[0]["evaluated_dims"], 1024);
    }

    #[test]
    fn empty_category_and_empty_subtype_emit_null_stats() {
        let prompts = vec![
            prompt("p0", "IN_DOMAIN_VALID", true, Some("   ")),
            prompt("p1", "IN_DOMAIN_VALID", true, None),
        ];
        let scored = vec![scored(true, 0, &[]), scored(true, 1, &[0])];
        let metrics = metrics_for(
            &prompts,
            &scored,
            Fhv1EvalGranularity::FullOnly,
            false,
            &[0u8; DIM],
        );
        assert_eq!(metrics.summary["per_subtype"], serde_json::json!({}));
        let empty_cat = &metrics.summary["failed_dims_stats_by_category"]["ADVERSARIAL_FUZZING"];
        assert!(empty_cat["min"].is_null());
        assert!(empty_cat["p25"].is_null());
        assert!(empty_cat["median"].is_null());
        assert!(empty_cat["p75"].is_null());
        assert!(empty_cat["p90"].is_null());
        assert!(empty_cat["max"].is_null());
        assert_eq!(empty_cat["zero_fail_count"], 0);
        assert_eq!(empty_cat["chunk_count"], 0);
        assert_eq!(empty_cat["prompt_count"], 0);
        assert_eq!(empty_cat["prompt_zero_fail_count"], 0);
        assert_eq!(
            metrics.summary["failed_dims_count_histogram_by_category"]["ADVERSARIAL_FUZZING"],
            serde_json::json!({})
        );
    }

    #[test]
    fn prompt_serde_defaults_missing_subtype_to_none() {
        let without_subtype: Fhv1Prompt = serde_json::from_str(
            r#"{"input_id":"id0","category":"IN_DOMAIN_VALID","expected_pass":true,"text":"hi"}"#,
        )
        .expect("without subtype");
        assert_eq!(without_subtype.subtype, None);

        let with_subtype: Fhv1Prompt = serde_json::from_str(
            r#"{"input_id":"id1","category":"HYBRID_BOUNDARY","expected_pass":false,"text":"hi","subtype":"sql_neighbor"}"#,
        )
        .expect("with subtype");
        assert_eq!(with_subtype.subtype.as_deref(), Some("sql_neighbor"));
    }

    #[test]
    fn select_view_and_parse_granularity_fail_closed() {
        let prepared = PreparedPrompt {
            prompt: prompt("only", "IN_DOMAIN_VALID", true, None),
            views: vec![PreparedView {
                granularity: Fhv1EvalGranularity::FullOnly,
                chunks: vec![ExpandedChunk {
                    strategy_tag: "full_doc",
                    text: "only".to_string(),
                    text_sha256: [0; 32],
                }],
                vectors: Vec::new(),
                embedding_ms: 0.0,
            }],
        };
        let err = select_view(&prepared, Fhv1EvalGranularity::Clauses).expect_err("missing");
        assert!(err.contains("missing clauses view"), "{err}");
        let err = parse_granularity("not-a-mode").expect_err("unknown");
        assert!(err.contains("unknown fhv1 granularity not-a-mode"), "{err}");
        assert_eq!(
            parse_granularity("full_mirror").expect("mirror"),
            Fhv1EvalGranularity::FullMirror
        );
    }

    struct RecordingEmbedder {
        batches: Mutex<Vec<Vec<String>>>,
    }

    impl RecordingEmbedder {
        fn new() -> Self {
            Self {
                batches: Mutex::new(Vec::new()),
            }
        }

        fn batch_sizes(&self) -> Vec<usize> {
            self.batches
                .lock()
                .expect("batches")
                .iter()
                .map(Vec::len)
                .collect()
        }
    }

    #[async_trait]
    impl BatchEmbedderClient for RecordingEmbedder {
        async fn embed_batch_f32(&self, _texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
            Err("unused".to_string())
        }

        async fn embed_batch_raw_f64(
            &self,
            texts: &[&str],
            _normalize: bool,
        ) -> Result<Vec<[f64; DIM]>, String> {
            self.batches
                .lock()
                .expect("batches")
                .push(texts.iter().map(|s| (*s).to_string()).collect());
            Ok(vec![[0.25; DIM]; texts.len()])
        }
    }

    #[tokio::test]
    async fn prepare_prompts_for_only_embeds_requested_granularity_in_bounded_batches() {
        let prompts: Vec<Fhv1Prompt> = (0..(EMBED_BATCH_SIZE + 5))
            .map(|idx| Fhv1Prompt {
                input_id: format!("p-{idx}"),
                category: "IN_DOMAIN_VALID".to_string(),
                expected_pass: true,
                text: format!(
                    "Prompt number {idx} writes clean Python modules. Extra clause {idx} validates sockets."
                ),
                subtype: Some("medium_en".to_string()),
            })
            .collect();

        let embedder = RecordingEmbedder::new();
        let prepared =
            prepare_prompts_for(&embedder, &prompts, true, &[Fhv1EvalGranularity::FullOnly])
                .await
                .expect("prepare");
        assert_eq!(prepared.len(), EMBED_BATCH_SIZE + 5);
        assert_eq!(embedder.batch_sizes(), vec![EMBED_BATCH_SIZE, 5]);
        for item in &prepared {
            assert_eq!(item.views.len(), 1);
            assert_eq!(item.views[0].granularity, Fhv1EvalGranularity::FullOnly);
            assert_eq!(item.views[0].chunks.len(), 1);
        }
    }
}
