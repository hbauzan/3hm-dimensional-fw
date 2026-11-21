//! Offline `fhv1` overlap gate, confusion metrics, and benchmark persistence.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::time::Instant;

use serde_json::{json, Value};
use sf_kernels::{evaluate_fhv1_batch, DimBoundStatus, Fhv1EvalGranularity, DIM};
use sf_proxy::{expand_for_granularity, expand_text_multi_granularity, BatchEmbedderClient};
use sf_storage::{Fhv1AuditTrace, Fhv1BenchmarkRun, Fhv1ProfileRecord, Fhv1Store};
use sha2::{Digest, Sha256};
use unicode_normalization::UnicodeNormalization;

pub const CATEGORIES: [&str; 4] = [
    "IN_DOMAIN_VALID",
    "OUT_OF_DOMAIN_BENIGN",
    "HYBRID_BOUNDARY",
    "ADVERSARIAL_FUZZING",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Fhv1Prompt {
    pub input_id: String,
    pub category: String,
    pub expected_pass: bool,
    pub text: String,
}

#[derive(Debug, Clone)]
pub struct PreparedView {
    pub granularity: Fhv1EvalGranularity,
    pub chunks: Vec<sf_proxy::ExpandedChunk>,
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

fn box_row(row: &[f64; DIM]) -> Box<[f64; DIM]> {
    let boxed: Box<[f64]> = row.to_vec().into_boxed_slice();
    match boxed.try_into() {
        Ok(vector) => vector,
        Err(_) => unreachable!("fhv1 vector width is {DIM}"),
    }
}

const ALL_GRANULARITIES: [Fhv1EvalGranularity; 3] = [
    Fhv1EvalGranularity::FullOnly,
    Fhv1EvalGranularity::Clauses,
    Fhv1EvalGranularity::FullMirror,
];

/// Embed every distinct chunk once, then fan the vectors out to each granularity.
pub async fn prepare_prompts<E>(
    embedder: &E,
    prompts: &[Fhv1Prompt],
    normalize: bool,
) -> Result<Vec<PreparedPrompt>, String>
where
    E: BatchEmbedderClient + ?Sized,
{
    let mut order: Vec<String> = Vec::new();
    let mut owners: Vec<Vec<usize>> = Vec::new();
    let mut index_of: HashMap<String, usize> = HashMap::new();
    let mut views_chunks = Vec::with_capacity(prompts.len());
    for (prompt_index, prompt) in prompts.iter().enumerate() {
        let mut views = Vec::with_capacity(ALL_GRANULARITIES.len());
        for granularity in ALL_GRANULARITIES {
            let chunks = expand_for_granularity(&prompt.text, granularity);
            if chunks.is_empty() {
                return Err(format!(
                    "prompt {} expanded to zero chunks",
                    prompt.input_id
                ));
            }
            for chunk in &chunks {
                if let Some(existing) = index_of.get(&chunk.text) {
                    owners[*existing].push(prompt_index);
                } else {
                    index_of.insert(chunk.text.clone(), order.len());
                    owners.push(vec![prompt_index]);
                    order.push(chunk.text.clone());
                }
            }
            views.push((granularity, chunks));
        }
        views_chunks.push(views);
    }
    let mut vectors = Vec::with_capacity(order.len());
    let mut prompt_embed_ms = vec![0.0; prompts.len()];
    const BATCH: usize = 16;
    for (batch_index, batch) in order.chunks(BATCH).enumerate() {
        let started = Instant::now();
        let texts: Vec<&str> = batch.iter().map(String::as_str).collect();
        let embedded = embedder.embed_batch_raw_f64(&texts, normalize).await?;
        if embedded.len() != batch.len() {
            return Err(format!(
                "embedder returned {} rows for {} chunks",
                embedded.len(),
                batch.len()
            ));
        }
        let elapsed_ms = started.elapsed().as_secs_f64() * 1_000.0;
        let base = batch_index * BATCH;
        for (offset, row) in embedded.iter().enumerate() {
            let share = elapsed_ms / batch.len() as f64;
            for prompt_index in &owners[base + offset] {
                prompt_embed_ms[*prompt_index] += share;
            }
            vectors.push(box_row(row));
        }
    }
    let mut prepared = Vec::with_capacity(prompts.len());
    for (prompt_index, prompt) in prompts.iter().enumerate() {
        let mut views = Vec::new();
        for (granularity, chunks) in &views_chunks[prompt_index] {
            let mut view_vectors = Vec::with_capacity(chunks.len());
            for chunk in chunks {
                let index = index_of[&chunk.text];
                view_vectors.push(vectors[index].clone());
            }
            views.push(PreparedView {
                granularity: *granularity,
                chunks: chunks.clone(),
                vectors: view_vectors,
                embedding_ms: prompt_embed_ms[prompt_index],
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
    })
}

pub struct RunMetrics {
    pub counts: ConfusionCounts,
    pub summary: Value,
    pub comparison_row: Value,
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
    for category in CATEGORIES {
        let mut category_expected = Vec::new();
        let mut category_passed = Vec::new();
        for (prompt, row) in prompts.iter().zip(scored.iter()) {
            if prompt.category == category {
                category_expected.push(prompt.expected_pass);
                category_passed.push(row.overall_passed);
            }
        }
        per_category.insert(
            category.to_string(),
            confusion_json(confusion_from_flags(&category_expected, &category_passed)),
        );
    }
    let mut histogram: BTreeMap<u16, u64> = BTreeMap::new();
    let mut in_domain_fail = vec![0u64; DIM];
    let mut oob_catch = vec![0u64; DIM];
    for (prompt, row) in prompts.iter().zip(scored.iter()) {
        for failed in &row.chunk_failed_dims {
            *histogram.entry(*failed).or_insert(0) += 1;
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
    let histogram_json: BTreeMap<String, u64> = histogram
        .into_iter()
        .map(|(key, value)| (key.to_string(), value))
        .collect();
    let summary = json!({
        "confusion": confusion_json(counts),
        "per_category": per_category,
        "failed_dims_count_histogram": histogram_json,
        "attribution": {
            "in_domain_fail_counts": in_domain_fail,
            "oob_catch_counts": oob_catch,
            "movement_tier_codes": tier_codes.to_vec(),
        },
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

pub async fn persist_benchmark_run(
    store: &Fhv1Store,
    profile: &Fhv1ProfileRecord,
    prepared: &[PreparedPrompt],
    scored: &[ScoredView],
    request: &PersistRequest<'_>,
) -> Result<(), String> {
    let total_chunks: u64 = scored.iter().map(|row| row.chunk_passed.len() as u64).sum();
    let run = Fhv1BenchmarkRun {
        run_id: request.run_id.to_string(),
        profile_id: profile.profile_id.clone(),
        policy_id: profile.policy_id.clone(),
        dataset_name: request.dataset_name.to_string(),
        dataset_sha256: request.dataset_sha256,
        eval_granularity: granularity_name(request.granularity).to_string(),
        use_rogue_mask: request.use_rogue_mask,
        total_inputs: prepared.len() as u64,
        total_chunks,
        summary_metrics_json: request.summary.to_string(),
        created_at_ms: request.created_at_ms,
    };
    store
        .save_benchmark_run(&run)
        .await
        .map_err(|err| err.to_string())?;
    let granularity_label = granularity_name(request.granularity);
    for (prepared_prompt, row) in prepared.iter().zip(scored.iter()) {
        let view = prepared_prompt
            .views
            .iter()
            .find(|candidate| candidate.granularity == request.granularity)
            .ok_or_else(|| format!("missing view {granularity_label}"))?;
        let mut traces = Vec::with_capacity(view.chunks.len());
        for (index, chunk) in view.chunks.iter().enumerate() {
            traces.push(Fhv1AuditTrace {
                trace_id: format!("{}-{}", request.run_id, prepared_prompt.prompt.input_id),
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
        }
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
    use sf_kernels::{Fhv1EvalGranularity, DIM};
    use sf_proxy::ExpandedChunk;

    use super::{
        attach_comparison, metrics_for, parse_granularity, select_view, Fhv1Prompt, PreparedPrompt,
        PreparedView, ScoredView,
    };

    fn prompt(id: &str, category: &str, expected_pass: bool) -> Fhv1Prompt {
        Fhv1Prompt {
            input_id: id.to_string(),
            category: category.to_string(),
            expected_pass,
            text: id.to_string(),
        }
    }

    fn scored(passed: bool, failed_dims: u16, violated: &[u16]) -> ScoredView {
        ScoredView {
            overall_passed: passed,
            full_text_passed: passed,
            all_chunks_passed: passed,
            evaluated_dims: 1024,
            chunk_failed_dims: vec![failed_dims],
            chunk_passed: vec![passed],
            underflow: vec![0],
            overflow: vec![if passed { 0 } else { failed_dims }],
            max_violation_delta: vec![0.0],
            mean_abs_delta_vs_mean: vec![0.0],
            violated_dims: vec![violated.to_vec()],
            eval_latency_ns: 7,
        }
    }

    fn f64_bits(value: &serde_json::Value) -> u64 {
        value.as_f64().expect("rate").to_bits()
    }

    #[test]
    fn metrics_cover_histogram_attribution_rates_and_comparison() {
        let prompts = vec![
            prompt("p0", "IN_DOMAIN_VALID", true),
            prompt("p1", "IN_DOMAIN_VALID", true),
            prompt("p2", "OUT_OF_DOMAIN_BENIGN", false),
            prompt("p3", "OUT_OF_DOMAIN_BENIGN", false),
            prompt("p4", "HYBRID_BOUNDARY", true),
            prompt("p5", "ADVERSARIAL_FUZZING", false),
        ];
        let scored = vec![
            scored(true, 0, &[]),
            scored(false, 2, &[4]),
            scored(false, 3, &[4, 7]),
            scored(true, 0, &[]),
            scored(false, 1, &[9]),
            scored(false, 3, &[7]),
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
        let in_precision = 1.0f64;
        let in_recall = 0.5f64;
        let in_f1 = 2.0 * in_precision * in_recall / (in_precision + in_recall);
        assert_eq!(f64_bits(&in_domain["precision"]), in_precision.to_bits());
        assert_eq!(f64_bits(&in_domain["recall"]), in_recall.to_bits());
        assert_eq!(f64_bits(&in_domain["f1"]), in_f1.to_bits());
        assert!(in_domain["far_fpr"].is_null());
        assert_eq!(f64_bits(&in_domain["frr_fnr"]), 0.5f64.to_bits());

        let out_of_domain = &metrics.summary["per_category"]["OUT_OF_DOMAIN_BENIGN"];
        assert_eq!(f64_bits(&out_of_domain["precision"]), 0.0f64.to_bits());
        assert!(out_of_domain["recall"].is_null());
        assert!(out_of_domain["f1"].is_null());
        assert_eq!(f64_bits(&out_of_domain["far_fpr"]), 0.5f64.to_bits());
        assert!(out_of_domain["frr_fnr"].is_null());

        let adversarial = &metrics.summary["per_category"]["ADVERSARIAL_FUZZING"];
        assert_eq!(f64_bits(&adversarial["far_fpr"]), 0.0f64.to_bits());
        assert!(adversarial["precision"].is_null());

        let histogram = &metrics.summary["failed_dims_count_histogram"];
        assert_eq!(histogram["0"], 2);
        assert_eq!(histogram["1"], 1);
        assert_eq!(histogram["2"], 1);
        assert_eq!(histogram["3"], 2);

        let oob = metrics.summary["attribution"]["oob_catch_counts"]
            .as_array()
            .expect("oob");
        assert_eq!(oob.len(), DIM);
        assert_eq!(oob[4], 1);
        assert_eq!(oob[7], 2);
        assert_eq!(
            metrics.summary["attribution"]["in_domain_fail_counts"][4],
            1
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
        assert_eq!(
            rows[0]["confusion"]["f1"],
            metrics.summary["confusion"]["f1"]
        );
    }

    #[test]
    fn select_view_and_parse_granularity_fail_closed() {
        let prepared = PreparedPrompt {
            prompt: prompt("only", "IN_DOMAIN_VALID", true),
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
}
