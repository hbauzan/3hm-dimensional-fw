//! Out-of-Scope & Adversarial Prompt Injection Benchmark Suite.
//!
//! Evaluates clean In-Domain legitimate traffic (False Positive Rate / FPR)
//! vs. Out-of-Scope (OOS) and Adversarial Prompt Injection Payloads (True Positive Rate / Recall).
//! Measures SIMD gate kernel latency (p50, p95, p99) under 1,000 iterations.

use std::time::Instant;

use hdrhistogram::Histogram;
use rand::Rng;
use rand::SeedableRng;
use rand_chacha::ChaCha8Rng;
use sf_kernels::{
    scalar_cosine_similarity, AlignedVec1024, DomainHypercubeLock, L3InspectionMode, DIM,
};
use sf_proxy::evaluate_three_tier_cascade;

use crate::synthetic_fixtures::generate_canonical_locks;

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

/// Generates a deterministic in-domain vector slightly perturbed inside the hypercube bounds.
fn generate_clean_indomain_vector(
    lock: &DomainHypercubeLock,
    rng: &mut ChaCha8Rng,
) -> AlignedVec1024 {
    let mut vec = lock.centroid;
    // Add small in-bounds jitter that stays within the coordinate envelope
    for dim in 0..DIM {
        if lock.noise_mask.is_active(dim) {
            let lo = lock.lo_dilated.data[dim];
            let hi = lock.hi_dilated.data[dim];
            let mid = (lo + hi) * 0.5;
            let span = (hi - lo) * 0.25;
            let jitter = (rng.gen::<f32>() - 0.5) * span;
            vec.data[dim] = (mid + jitter).clamp(lo, hi);
        }
    }
    vec
}

/// Generates an adversarial out-of-scope / prompt injection payload vector.
/// Designed to simulate piggybacked injections with high cosine similarity to host centroid
/// but coordinate-level subspace drift breaching K-of-D quorum.
fn generate_adversarial_injection_vector(
    lock: &DomainHypercubeLock,
    rng: &mut ChaCha8Rng,
) -> (AlignedVec1024, bool) {
    let mut vec = lock.centroid;
    // 50% are piggybacked attacks that leak under global sequence cosine
    let leaks_cosine = rng.gen_bool(0.48);

    if leaks_cosine {
        // High cosine proximity to centroid, but coordinates drift out-of-bounds across active dimensions
        let drift_dims = 150..600;
        for dim in drift_dims {
            if lock.noise_mask.is_active(dim) {
                // Shift coordinates outside the hypercube bounds
                vec.data[dim] = lock.hi_dilated.data[dim] + 0.08 + (rng.gen::<f32>() * 0.02);
            }
        }
    } else {
        // Direct orthogonal / out-of-domain injection
        vec = AlignedVec1024::zeros();
        vec.data[950] = 1.0;
        for dim in 0..100 {
            vec.data[dim] = 0.04 + (rng.gen::<f32>() * 0.01);
        }
    }

    (vec, leaks_cosine)
}

/// Run Suite 2: Out-of-Scope & Adversarial Injection Benchmark.
pub fn run_oos_benchmark() -> OosBenchmarkResult {
    let mut rng = ChaCha8Rng::seed_from_u64(OOS_BENCHMARK_SEED);
    let locks = generate_canonical_locks();
    let num_locks = locks.len();

    // 1. Evaluate 100 Clean In-Domain Legitimate Traffic samples
    let total_indomain = 100;
    let mut false_positives = 0;

    for i in 0..total_indomain {
        let lock = &locks[i % num_locks];
        let indomain_vec = generate_clean_indomain_vector(lock, &mut rng);
        let clauses = ["clean legitimate query"];
        let res = evaluate_three_tier_cascade(
            &indomain_vec,
            std::slice::from_ref(&indomain_vec),
            &clauses,
            lock,
            L3InspectionMode::ModeCSpectralQuorum,
            1,
        );
        if res.is_err() {
            false_positives += 1;
        }
    }

    // 2. Evaluate 100 Out-of-Scope / Prompt Injection samples
    let total_oos_injections = 100;
    let mut global_cosine_leaks = 0;
    let mut true_positives_blocked = 0;

    for i in 0..total_oos_injections {
        let lock = &locks[i % num_locks];
        let (injection_vec, _) = generate_adversarial_injection_vector(lock, &mut rng);

        // Global sequence cosine baseline
        let global_cos = scalar_cosine_similarity(&injection_vec, &lock.centroid);
        if global_cos >= lock.l1_cosine_threshold {
            global_cosine_leaks += 1;
        }

        // 3HM Evaluation
        let clauses = ["adversarial prompt injection payload"];
        let res = evaluate_three_tier_cascade(
            &injection_vec,
            std::slice::from_ref(&injection_vec),
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
    let test_lock = &locks[0];
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
