//! Suite 2: out-of-scope and adversarial prompt benchmark.
//!
//! Each prompt is normalized, segmented, and scored on the 66 calibrated locks.
//! The primary lock uses the live Mode C cascade. Pairwise locks that name the
//! target domain are scored with Mode A on their calibrated top-k coordinates.
//! A clean false positive records the first failing tier. A second count keeps
//! that cascade and scores the original pair locks with
//! `evaluate_pairwise_containment`.
//! Rates are counts over the English matrix, the Spanish matrix, and a pooled row.

use std::collections::HashMap;
use std::sync::{Arc, OnceLock};
use std::time::Instant;

use hdrhistogram::Histogram;
use serde::Deserialize;
use sf_kernels::{
    cosine_similarity_1024, evaluate_l3_gate, AlignedVec1024, DomainHypercubeLock,
    L3InspectionMode, DIM,
};
use sf_proxy::{evaluate_pairwise_containment, evaluate_three_tier_cascade, InputNormalizer};
use sf_storage::{assemble_canonical_catalog, pair_lock_sides};

use crate::canonical_corpus::canonical_seed_corpus;
use crate::suite2_catalog::{suite2_matrix_label, suite2_prompts, Suite2Kind};

pub static OOS_VECTORS_RAW: &[u8] = include_bytes!("../fixtures/oos_bge_m3_vectors.bin");
pub static OOS_METADATA_RAW: &str = include_str!("../fixtures/oos_bge_m3_metadata.json");

pub const OOS_BENCHMARK_SEED: u64 = 0x005_1DE5_E701;
const PRIMARY_MODE: &str = "ModeCSpectralQuorum";
const PAIRWISE_MODE: &str = "ModeATopK";

/// First-failure counts for clean false positives.
///
/// `l1`, `l2`, and `l3` are the primary Mode C cascade. `pairs` is the pairwise
/// check for this mode. The four buckets sum to `fp`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Suite2FpTier {
    pub l1: usize,
    pub l2: usize,
    pub l3: usize,
    pub pairs: usize,
    pub fp: usize,
}

/// One language matrix, or the explicitly pooled row.
#[derive(Debug, Clone, PartialEq)]
pub struct Suite2Matrix {
    pub label: &'static str,
    pub n_clean: usize,
    pub false_positives: usize,
    pub fpr: f64,
    pub n_attack: usize,
    pub cosine_leaks: usize,
    pub leak_rate: f64,
    pub blocked: usize,
    pub recall: f64,
    /// Attacks with `!contained_prod`: primary Mode C cascade, then
    /// `evaluate_pairwise_containment`.
    pub blocked_prod: usize,
    pub recall_prod: f64,
    /// Mode A suite: primary Mode C cascade, then eligible pairwise locks in Mode A.
    pub fp_tier_mode_a: Suite2FpTier,
    /// Same cascade, then `evaluate_pairwise_containment`.
    pub fp_tier_mode_c: Suite2FpTier,
}

/// One scored prompt after normalization and segmentation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Suite2Sample {
    pub matrix: &'static str,
    pub kind: &'static str,
    pub attack_type: Option<&'static str>,
    pub target_domain: &'static str,
    pub prompt: String,
    pub normalized: String,
    pub clauses: Vec<String>,
    pub contained: bool,
    /// Primary Mode C cascade passed and `evaluate_pairwise_containment` passed.
    pub contained_prod: bool,
    pub cosine_leak: bool,
    pub primary_mode: &'static str,
    pub pairwise_mode: &'static str,
    pub pairwise_lock_ids: Vec<String>,
    pub(crate) fp_bucket_mode_a: Option<FpBucket>,
    pub(crate) fp_bucket_mode_c: Option<FpBucket>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum FpBucket {
    L1,
    L2,
    L3,
    Pairs,
}

struct ModeAGate {
    contained: bool,
    primary_fail: Option<FpBucket>,
}

/// Suite 2 report. Rates are `fp/n_clean`, `leaks/n_attack`, `blocked/n_attack`
/// (Mode A), and `blocked_prod/n_attack` (production Mode C).
#[derive(Debug, Clone, PartialEq)]
pub struct OosBenchmarkResult {
    pub en: Suite2Matrix,
    pub es: Suite2Matrix,
    pub pooled: Suite2Matrix,
    pub samples: Vec<Suite2Sample>,
    pub latency_p50_us: f64,
    pub latency_p95_us: f64,
    pub latency_p99_us: f64,
}

#[derive(Debug, Deserialize)]
struct VectorManifest {
    strings: Vec<String>,
    vector_dim: usize,
}

struct Prepared {
    vectors: HashMap<String, AlignedVec1024>,
    locks: Vec<DomainHypercubeLock>,
}

struct PreparedSample {
    prompt_vec: AlignedVec1024,
    clause_vecs: Vec<AlignedVec1024>,
    clause_refs_owned: Vec<String>,
    normalized: String,
}

fn prepared() -> &'static Prepared {
    static PREPARED: OnceLock<Prepared> = OnceLock::new();
    PREPARED.get_or_init(|| {
        let vectors = load_vectors();
        let locks = build_locks(&vectors);
        Prepared { vectors, locks }
    })
}

fn load_vectors() -> HashMap<String, AlignedVec1024> {
    let manifest: VectorManifest =
        serde_json::from_str(OOS_METADATA_RAW).expect("suite 2 vector manifest");
    if manifest.vector_dim != DIM {
        panic!(
            "suite 2 vector manifest dim {}, expected {DIM}",
            manifest.vector_dim
        );
    }
    let row_bytes = manifest.vector_dim * 4;
    if OOS_VECTORS_RAW.len() != manifest.strings.len() * row_bytes {
        panic!(
            "suite 2 vector file has {} bytes for {} strings",
            OOS_VECTORS_RAW.len(),
            manifest.strings.len()
        );
    }
    let mut vectors = HashMap::with_capacity(manifest.strings.len());
    for (index, text) in manifest.strings.iter().enumerate() {
        let start = index * row_bytes;
        let slice = &OOS_VECTORS_RAW[start..start + row_bytes];
        let mut data = [0.0f32; DIM];
        for (slot, chunk) in slice.chunks_exact(4).enumerate() {
            let mut bytes = [0u8; 4];
            bytes.copy_from_slice(chunk);
            data[slot] = f32::from_le_bytes(bytes);
        }
        let vector = AlignedVec1024::from_slice(&data).expect("1024-d vector");
        if vectors.insert(text.clone(), vector).is_some() {
            panic!("duplicate suite 2 vector key: {text}");
        }
    }
    vectors
}

fn require_vector(vectors: &HashMap<String, AlignedVec1024>, text: &str) -> AlignedVec1024 {
    vectors
        .get(text)
        .cloned()
        .unwrap_or_else(|| panic!("missing BAAI/bge-m3 vector for string: {text}"))
}

fn build_locks(vectors: &HashMap<String, AlignedVec1024>) -> Vec<DomainHypercubeLock> {
    let mut owned = Vec::new();
    for entry in canonical_seed_corpus() {
        let mut flat = Vec::with_capacity(entry.sentences.len() * DIM);
        for sentence in entry.sentences {
            let vector = require_vector(vectors, sentence);
            flat.extend_from_slice(&vector.data);
        }
        owned.push((entry.domain_id.to_string(), flat));
    }
    let borrowed: Vec<(&str, &[f32])> = owned
        .iter()
        .map(|(name, rows)| (name.as_str(), rows.as_slice()))
        .collect();
    assemble_canonical_catalog(&borrowed)
        .unwrap_or_else(|err| panic!("canonical lock calibration failed: {err}"))
        .locks
}

/// The 11 base locks plus the 55 pairwise locks, calibrated from the fixture vectors.
pub fn suite2_locks() -> Vec<DomainHypercubeLock> {
    prepared().locks.clone()
}

/// Normalized prompts and segmented clauses the generator must embed.
pub fn suite2_lookup_strings() -> Vec<String> {
    let mut texts = Vec::new();
    for prompt in suite2_prompts() {
        let normalized = InputNormalizer::normalize(&prompt.text);
        texts.push(normalized.text.clone());
        for clause in normalized.segment_all_clauses() {
            texts.push(clause.to_string());
        }
    }
    texts
}

/// JSON lines: canonical seed sentences, then every string [`suite2_lookup_strings`] emits.
pub fn suite2_embed_jsonl() -> String {
    let mut lines = Vec::new();
    for entry in canonical_seed_corpus() {
        for sentence in entry.sentences {
            lines.push(
                serde_json::json!({
                    "kind": "seed",
                    "domain": entry.domain_id,
                    "text": sentence,
                })
                .to_string(),
            );
        }
    }
    for text in suite2_lookup_strings() {
        lines.push(serde_json::json!({"kind": "lookup", "text": text}).to_string());
    }
    lines.join("\n")
}

fn polarity_for_target(pair_id: &str, target: &str) -> Option<u8> {
    let (left, right) = pair_lock_sides(pair_id)?;
    if target == left {
        Some(0)
    } else if target == right {
        Some(1)
    } else {
        None
    }
}

fn tuned_pairs(locks: &[DomainHypercubeLock], domain: &str) -> Vec<DomainHypercubeLock> {
    let mut tuned = Vec::new();
    for lock in locks {
        let Some(polarity) = polarity_for_target(&lock.domain_id, domain) else {
            continue;
        };
        // An empty discriminative mask has no Mode A coordinates. The live
        // registry skips that lock. Suite 2 uses the same eligibility.
        if lock.top_k_len == 0 || lock.noise_mask.active_count() == 0 {
            continue;
        }
        let mut copy = lock.clone();
        copy.polarity = polarity;
        tuned.push(copy);
    }
    tuned
}

fn mode_a_passes(
    lock: &DomainHypercubeLock,
    prompt_vec: &AlignedVec1024,
    clause_vecs: &[AlignedVec1024],
) -> bool {
    let mut passed = evaluate_l3_gate(prompt_vec, lock, L3InspectionMode::ModeATopK, 0).passed;
    for clause_vec in clause_vecs {
        passed &= evaluate_l3_gate(clause_vec, lock, L3InspectionMode::ModeATopK, 0).passed;
    }
    passed
}

fn primary_bucket(tier: &str) -> FpBucket {
    match tier {
        "L1_CATEGORICAL_COSINE" => FpBucket::L1,
        "L2_SLIDING_WINDOW" => FpBucket::L2,
        "L3_DDI_INSPECTOR" => FpBucket::L3,
        other => panic!("suite 2 primary cascade returned an unknown failing tier: {other}"),
    }
}

fn mode_a_gate(
    prompt_vec: &AlignedVec1024,
    clause_vecs: &[AlignedVec1024],
    clauses: &[&str],
    primary: &DomainHypercubeLock,
    pairs: &[DomainHypercubeLock],
) -> ModeAGate {
    let primary_fail = match evaluate_three_tier_cascade(
        prompt_vec,
        clause_vecs,
        clauses,
        primary,
        L3InspectionMode::ModeCSpectralQuorum,
        0,
    ) {
        Ok(_) => None,
        Err(error) => Some(primary_bucket(error.error.telemetry.failing_tier)),
    };
    let mut pairwise_ok = true;
    for lock in pairs {
        pairwise_ok &= mode_a_passes(lock, prompt_vec, clause_vecs);
    }
    ModeAGate {
        contained: primary_fail.is_none() && pairwise_ok,
        primary_fail,
    }
}

fn mode_a_failure(gate: &ModeAGate) -> Option<FpBucket> {
    gate.primary_fail.or(if gate.contained {
        None
    } else {
        Some(FpBucket::Pairs)
    })
}

/// Original pair locks that name `domain`. Polarity stays as calibrated.
/// `evaluate_pairwise_containment` assigns polarity and skips empty masks.
fn named_pair_arcs(locks: &[DomainHypercubeLock], domain: &str) -> Vec<Arc<DomainHypercubeLock>> {
    locks
        .iter()
        .filter(|lock| polarity_for_target(&lock.domain_id, domain).is_some())
        .map(|lock| Arc::new(lock.clone()))
        .collect()
}

fn production_failure(
    gate: &ModeAGate,
    prompt_vec: &AlignedVec1024,
    clause_vecs: &[AlignedVec1024],
    target_domain: &str,
    pair_locks: &[Arc<DomainHypercubeLock>],
) -> (bool, Option<FpBucket>) {
    if let Some(bucket) = gate.primary_fail {
        return (false, Some(bucket));
    }
    let pairs_ok =
        evaluate_pairwise_containment(prompt_vec, clause_vecs, target_domain, pair_locks).is_ok();
    if pairs_ok {
        (true, None)
    } else {
        (false, Some(FpBucket::Pairs))
    }
}

fn gate_contains(
    prompt_vec: &AlignedVec1024,
    clause_vecs: &[AlignedVec1024],
    clauses: &[&str],
    primary: &DomainHypercubeLock,
    pairs: &[DomainHypercubeLock],
) -> bool {
    mode_a_gate(prompt_vec, clause_vecs, clauses, primary, pairs).contained
}

fn embed_prompt(prompt: &str, vectors: &HashMap<String, AlignedVec1024>) -> PreparedSample {
    let normalized = InputNormalizer::normalize(prompt);
    let clauses: Vec<String> = normalized
        .segment_all_clauses()
        .into_iter()
        .map(str::to_string)
        .collect();
    let prompt_vec = require_vector(vectors, &normalized.text);
    let clause_vecs = clauses
        .iter()
        .map(|clause| require_vector(vectors, clause))
        .collect();
    PreparedSample {
        prompt_vec,
        clause_vecs,
        clause_refs_owned: clauses,
        normalized: normalized.text,
    }
}

fn bump_tier(tier: &mut Suite2FpTier, bucket: FpBucket) {
    match bucket {
        FpBucket::L1 => tier.l1 += 1,
        FpBucket::L2 => tier.l2 += 1,
        FpBucket::L3 => tier.l3 += 1,
        FpBucket::Pairs => tier.pairs += 1,
    }
}

fn matrix_from(label: &'static str, samples: &[&Suite2Sample]) -> Suite2Matrix {
    let mut n_clean = 0usize;
    let mut false_positives = 0usize;
    let mut n_attack = 0usize;
    let mut cosine_leaks = 0usize;
    let mut blocked = 0usize;
    let mut blocked_prod = 0usize;
    let mut fp_tier_mode_a = Suite2FpTier::default();
    let mut fp_tier_mode_c = Suite2FpTier::default();
    for sample in samples {
        if sample.kind == "clean" {
            n_clean += 1;
            if !sample.contained {
                false_positives += 1;
                fp_tier_mode_a.fp += 1;
                let bucket = sample.fp_bucket_mode_a.unwrap_or_else(|| {
                    panic!(
                        "suite 2 {label} clean sample in {} is a mode A false positive without a tier",
                        sample.target_domain
                    )
                });
                bump_tier(&mut fp_tier_mode_a, bucket);
            } else if sample.fp_bucket_mode_a.is_some() {
                panic!(
                    "suite 2 {label} clean sample in {} passed mode A and still recorded a tier",
                    sample.target_domain
                );
            }
            if !sample.contained_prod {
                fp_tier_mode_c.fp += 1;
                let bucket = sample.fp_bucket_mode_c.unwrap_or_else(|| {
                    panic!(
                        "suite 2 {label} clean sample in {} is a production false positive without a tier",
                        sample.target_domain
                    )
                });
                bump_tier(&mut fp_tier_mode_c, bucket);
            } else if sample.fp_bucket_mode_c.is_some() {
                panic!(
                    "suite 2 {label} clean sample in {} passed production pairs and still recorded a tier",
                    sample.target_domain
                );
            }
        } else {
            n_attack += 1;
            if sample.cosine_leak {
                cosine_leaks += 1;
            }
            if !sample.contained {
                blocked += 1;
            }
            if !sample.contained_prod {
                blocked_prod += 1;
            }
            if sample.fp_bucket_mode_a.is_some() || sample.fp_bucket_mode_c.is_some() {
                panic!(
                    "suite 2 {label} attack sample in {} recorded a clean false-positive tier",
                    sample.target_domain
                );
            }
        }
    }
    if n_clean == 0 || n_attack == 0 {
        panic!("suite 2 matrix {label} has an empty denominator");
    }
    Suite2Matrix {
        label,
        n_clean,
        false_positives,
        fpr: false_positives as f64 / n_clean as f64,
        n_attack,
        cosine_leaks,
        leak_rate: cosine_leaks as f64 / n_attack as f64,
        blocked,
        recall: blocked as f64 / n_attack as f64,
        blocked_prod,
        recall_prod: blocked_prod as f64 / n_attack as f64,
        fp_tier_mode_a,
        fp_tier_mode_c,
    }
}

fn measure_gate_us(
    prompt_vec: &AlignedVec1024,
    clause_vecs: &[AlignedVec1024],
    clauses: &[&str],
    primary: &DomainHypercubeLock,
    pairs: &[DomainHypercubeLock],
) -> (f64, f64, f64) {
    let mut histogram = Histogram::<u64>::new(3).expect("histogram");
    for _ in 0..1_000 {
        let start = Instant::now();
        let _ = gate_contains(prompt_vec, clause_vecs, clauses, primary, pairs);
        let nanos = u64::try_from(start.elapsed().as_nanos()).unwrap_or(u64::MAX);
        histogram.record(nanos.max(1)).expect("record latency");
    }
    (
        histogram.value_at_quantile(0.50) as f64 / 1_000.0,
        histogram.value_at_quantile(0.95) as f64 / 1_000.0,
        histogram.value_at_quantile(0.99) as f64 / 1_000.0,
    )
}

/// Run Suite 2 on the committed `BAAI/bge-m3` fixtures.
pub fn run_oos_benchmark() -> OosBenchmarkResult {
    let state = prepared();
    let mut samples = Vec::new();
    let mut first_clean: Option<(PreparedSample, Vec<DomainHypercubeLock>, String)> = None;

    for prompt in suite2_prompts() {
        let embedded = embed_prompt(&prompt.text, &state.vectors);
        let primary = state
            .locks
            .iter()
            .find(|lock| lock.domain_id == prompt.domain)
            .unwrap_or_else(|| panic!("missing primary lock for {}", prompt.domain));
        let pairs = tuned_pairs(&state.locks, prompt.domain);
        let named_pairs = named_pair_arcs(&state.locks, prompt.domain);
        let clause_refs: Vec<&str> = embedded
            .clause_refs_owned
            .iter()
            .map(String::as_str)
            .collect();
        let cosine = cosine_similarity_1024(&embedded.prompt_vec, &primary.centroid);
        let cosine_leak = cosine >= primary.l1_cosine_threshold;
        let gate = mode_a_gate(
            &embedded.prompt_vec,
            &embedded.clause_vecs,
            &clause_refs,
            primary,
            &pairs,
        );
        let (contained_prod, production_bucket) = production_failure(
            &gate,
            &embedded.prompt_vec,
            &embedded.clause_vecs,
            prompt.domain,
            &named_pairs,
        );
        let contained = gate.contained;
        let clean = prompt.kind == Suite2Kind::Clean;
        let kind = match prompt.kind {
            Suite2Kind::Clean => "clean",
            Suite2Kind::Attack => "attack",
        };
        if first_clean.is_none() && prompt.kind == Suite2Kind::Clean {
            first_clean = Some((
                PreparedSample {
                    prompt_vec: embedded.prompt_vec,
                    clause_vecs: embedded.clause_vecs.clone(),
                    clause_refs_owned: embedded.clause_refs_owned.clone(),
                    normalized: embedded.normalized.clone(),
                },
                pairs.clone(),
                prompt.domain.to_string(),
            ));
        }
        samples.push(Suite2Sample {
            matrix: suite2_matrix_label(prompt.domain),
            kind,
            attack_type: prompt.attack_type,
            target_domain: prompt.domain,
            prompt: prompt.text,
            normalized: embedded.normalized,
            clauses: embedded.clause_refs_owned,
            contained,
            contained_prod,
            cosine_leak,
            primary_mode: PRIMARY_MODE,
            pairwise_mode: PAIRWISE_MODE,
            pairwise_lock_ids: pairs.iter().map(|lock| lock.domain_id.clone()).collect(),
            fp_bucket_mode_a: if clean { mode_a_failure(&gate) } else { None },
            fp_bucket_mode_c: if clean { production_bucket } else { None },
        });
    }

    let en_refs: Vec<&Suite2Sample> = samples
        .iter()
        .filter(|sample| sample.matrix == "EN")
        .collect();
    let es_refs: Vec<&Suite2Sample> = samples
        .iter()
        .filter(|sample| sample.matrix == "ES")
        .collect();
    let all_refs: Vec<&Suite2Sample> = samples.iter().collect();
    let (latency_p50_us, latency_p95_us, latency_p99_us) = {
        let (embedded, pairs, domain) = first_clean.expect("suite 2 has a clean prompt");
        let primary = state
            .locks
            .iter()
            .find(|lock| lock.domain_id == domain)
            .expect("primary lock for the latency probe");
        let clause_refs: Vec<&str> = embedded
            .clause_refs_owned
            .iter()
            .map(String::as_str)
            .collect();
        measure_gate_us(
            &embedded.prompt_vec,
            &embedded.clause_vecs,
            &clause_refs,
            primary,
            &pairs,
        )
    };

    let result = OosBenchmarkResult {
        en: matrix_from("EN", &en_refs),
        es: matrix_from("ES", &es_refs),
        pooled: matrix_from("pooled", &all_refs),
        samples,
        latency_p50_us,
        latency_p95_us,
        latency_p99_us,
    };
    println!("{}", format_suite2_metrics(&result));
    result
}

fn fp_tier_line(label: &str, mode: &str, tier: &Suite2FpTier) -> String {
    format!(
        "suite2 fp_tier matrix={label} mode={mode} l1={l1} l2={l2} l3={l3} pairs={pairs} fp={fp}",
        l1 = tier.l1,
        l2 = tier.l2,
        l3 = tier.l3,
        pairs = tier.pairs,
        fp = tier.fp,
    )
}

pub fn format_suite2_metrics(result: &OosBenchmarkResult) -> String {
    let mut lines = Vec::with_capacity(10);
    for matrix in [&result.en, &result.es, &result.pooled] {
        lines.push(format!(
            "suite2 matrix={label} n_clean={n_clean} fp={fp} fpr={fp}/{n_clean} n_attack={n_attack} cosine_leaks={leaks} leak_rate={leaks}/{n_attack} blocked={blocked} recall={blocked}/{n_attack} blocked_prod={blocked_prod} recall_prod={blocked_prod}/{n_attack}",
            label = matrix.label,
            n_clean = matrix.n_clean,
            fp = matrix.false_positives,
            n_attack = matrix.n_attack,
            leaks = matrix.cosine_leaks,
            blocked = matrix.blocked,
            blocked_prod = matrix.blocked_prod,
        ));
    }
    for matrix in [&result.en, &result.es, &result.pooled] {
        lines.push(fp_tier_line(matrix.label, "A", &matrix.fp_tier_mode_a));
        lines.push(fp_tier_line(matrix.label, "C", &matrix.fp_tier_mode_c));
    }
    lines.push(format!(
        "suite2 gate_us p50={:.3} p95={:.3} p99={:.3}",
        result.latency_p50_us, result.latency_p95_us, result.latency_p99_us
    ));
    lines.join("\n")
}
