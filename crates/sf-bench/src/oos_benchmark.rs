//! Out-of-Scope & Adversarial Prompt Injection Benchmark Suite.
//!
//! Evaluates clean In-Domain legitimate traffic (False Positive Rate / FPR)
//! vs. Out-of-Scope (OOS) and Adversarial Prompt Injection Payloads (True Positive Rate / Recall)
//! using authentic BAAI/bge-m3 1024D float32 vectors in strict IEEE 754 binary32 determinism.
//! Measures SIMD gate kernel latency (p50, p95, p99) under 1,000 iterations.

use std::collections::HashMap;
use std::time::Instant;

use hdrhistogram::Histogram;
use serde::Deserialize;
use sf_kernels::{
    scalar_cosine_similarity, AlignedVec1024, DomainHypercubeLock, L3InspectionMode, LockSpec,
    NoiseBitmask1024, MAX_TOPK,
};
use sf_proxy::evaluate_three_tier_cascade;

pub static OOS_VECTORS_RAW: &[u8] = include_bytes!("../fixtures/oos_bge_m3_vectors.bin");
pub static OOS_METADATA_RAW: &str = include_str!("../fixtures/oos_bge_m3_metadata.json");

pub const OOS_BENCHMARK_SEED: u64 = 0x005_1DE5_E701;

/// Metrics for Out-of-Scope & Adversarial Injection validation.
#[derive(Debug, Clone)]
pub struct OosBenchmarkResult {
    pub total_indomain: usize,
    pub false_positives: usize,
    pub fpr: f64,
    pub total_oos_injections: usize,
    pub global_cosine_leaks: usize,
    pub global_cosine_leak_rate: f64,
    pub true_positives_blocked: usize,
    pub recall: f64,
    pub latency_p50_us: f64,
    pub latency_p95_us: f64,
    pub latency_p99_us: f64,
}

#[derive(Debug, Deserialize)]
struct OosManifest {
    pub domain_locks: HashMap<String, DomainLockSpecDto>,
    pub indomain_samples: Vec<IndomainSampleDto>,
    pub oos_injections_samples: Vec<OosInjectionSampleDto>,
}

#[derive(Debug, Deserialize)]
struct DomainLockSpecDto {
    pub centroid: Vec<f32>,
    pub lo: Vec<f32>,
    pub hi: Vec<f32>,
}

#[derive(Debug, Deserialize)]
struct IndomainSampleDto {
    pub target_domain: String,
    #[allow(dead_code)]
    pub prompt: String,
    pub clauses: Vec<String>,
    pub prompt_vec_idx: usize,
    pub clause_vec_indices: Vec<usize>,
}

#[derive(Debug, Deserialize)]
struct OosInjectionSampleDto {
    pub target_domain: String,
    #[allow(dead_code)]
    pub prompt: String,
    pub clauses: Vec<String>,
    #[allow(dead_code)]
    pub attack_type: String,
    pub prompt_vec_idx: usize,
    pub clause_vec_indices: Vec<usize>,
}

fn get_vector(idx: usize) -> AlignedVec1024 {
    let start = idx * 4096;
    let end = start + 4096;
    let slice = &OOS_VECTORS_RAW[start..end];
    let mut vec = AlignedVec1024::zeros();
    for (i, chunk) in slice.chunks_exact(4).enumerate() {
        let mut bytes = [0u8; 4];
        bytes.copy_from_slice(chunk);
        vec.data[i] = f32::from_le_bytes(bytes);
    }
    vec
}

/// Run Suite 2: Out-of-Scope & Adversarial Injection Benchmark.
/// Evaluates authentic BAAI/bge-m3 embeddings from CLINC OOS and Deepset Prompt Injections.
pub fn run_oos_benchmark() -> OosBenchmarkResult {
    let manifest: OosManifest =
        serde_json::from_str(OOS_METADATA_RAW).expect("valid oos metadata manifest");

    // Construct calibrated DomainHypercubeLocks for the 11 domains
    let mut locks_by_name: HashMap<String, DomainHypercubeLock> =
        HashMap::with_capacity(manifest.domain_locks.len());

    for (name, spec) in manifest.domain_locks {
        let centroid = AlignedVec1024::from_slice(&spec.centroid).expect("1024 centroid");
        let lo = AlignedVec1024::from_slice(&spec.lo).expect("1024 lo");
        let hi = AlignedVec1024::from_slice(&spec.hi).expect("1024 hi");

        let lock = DomainHypercubeLock::from_spec(LockSpec {
            domain_id: name.clone(),
            centroid,
            lo,
            hi,
            epsilon: 0.0,
            noise_mask: NoiseBitmask1024::new_bge_m3_default(),
            top_k_indices: [0u16; MAX_TOPK],
            top_k_len: 103,
            quorum_k: 103,
            l1_cosine_threshold: 0.50,
            l2_clause_threshold: 0.50,
            polarity: 0,
            domain_version: 1,
        });
        locks_by_name.insert(name, lock);
    }

    // 1. Evaluate Clean In-Domain Legitimate Traffic samples (False Positive Rate)
    let total_indomain = manifest.indomain_samples.len();
    let mut false_positives = 0;

    for sample in &manifest.indomain_samples {
        let lock = locks_by_name
            .get(&sample.target_domain)
            .unwrap_or_else(|| panic!("missing domain lock for {}", sample.target_domain));
        let prompt_vec = get_vector(sample.prompt_vec_idx);
        let clause_vecs: Vec<AlignedVec1024> = sample
            .clause_vec_indices
            .iter()
            .map(|&idx| get_vector(idx))
            .collect();
        let clauses: Vec<&str> = sample.clauses.iter().map(|s| s.as_str()).collect();

        let res = evaluate_three_tier_cascade(
            &prompt_vec,
            &clause_vecs,
            &clauses,
            lock,
            L3InspectionMode::ModeCSpectralQuorum,
            1,
        );
        if res.is_err() {
            false_positives += 1;
        }
    }

    // 2. Evaluate Out-of-Scope & Prompt Injection samples
    let total_oos_injections = manifest.oos_injections_samples.len();
    let mut global_cosine_leaks = 0;
    let mut true_positives_blocked = 0;

    for sample in &manifest.oos_injections_samples {
        let lock = locks_by_name
            .get(&sample.target_domain)
            .unwrap_or_else(|| panic!("missing domain lock for {}", sample.target_domain));
        let prompt_vec = get_vector(sample.prompt_vec_idx);
        let clause_vecs: Vec<AlignedVec1024> = sample
            .clause_vec_indices
            .iter()
            .map(|&idx| get_vector(idx))
            .collect();
        let clauses: Vec<&str> = sample.clauses.iter().map(|s| s.as_str()).collect();

        // Global sequence cosine baseline
        let global_cos = scalar_cosine_similarity(&prompt_vec, &lock.centroid);
        if global_cos >= lock.l1_cosine_threshold {
            global_cosine_leaks += 1;
        }

        // 3HM Evaluation
        let res = evaluate_three_tier_cascade(
            &prompt_vec,
            &clause_vecs,
            &clauses,
            lock,
            L3InspectionMode::ModeCSpectralQuorum,
            1,
        );
        if res.is_err() {
            true_positives_blocked += 1;
        }
    }

    // 3. Measure SIMD gate kernel latency at 1,000 iterations
    let mut histogram = Histogram::<u64>::new(3).expect("histogram");
    let test_lock = locks_by_name.values().next().expect("test lock");
    let probe_vec = test_lock.centroid;
    let probe_clauses = ["probe clause"];

    for _ in 0..1_000 {
        let start = Instant::now();
        let _ = evaluate_three_tier_cascade(
            &probe_vec,
            std::slice::from_ref(&probe_vec),
            &probe_clauses,
            test_lock,
            L3InspectionMode::ModeCSpectralQuorum,
            0,
        );
        let nanos = start.elapsed().as_nanos() as u64;
        histogram.record(nanos.max(1)).expect("record latency");
    }

    let latency_p50_us = (histogram.value_at_quantile(0.50) as f64) / 1_000.0;
    let latency_p95_us = (histogram.value_at_quantile(0.95) as f64) / 1_000.0;
    let latency_p99_us = (histogram.value_at_quantile(0.99) as f64) / 1_000.0;

    OosBenchmarkResult {
        total_indomain,
        false_positives,
        fpr: false_positives as f64 / total_indomain as f64,
        total_oos_injections,
        global_cosine_leaks,
        global_cosine_leak_rate: global_cosine_leaks as f64 / total_oos_injections as f64,
        true_positives_blocked,
        recall: true_positives_blocked as f64 / total_oos_injections as f64,
        latency_p50_us,
        latency_p95_us,
        latency_p99_us,
    }
}
