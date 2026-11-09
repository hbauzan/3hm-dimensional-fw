//! L1 → L2 → L3 cascade. The first failing tier returns the breach envelope.

use crate::telemetry::{
    f32_hex, BreachErrorBody, BreachErrorEnvelope, BreachMetricsDto, BreachTelemetryDto,
    CoordinateBreachDto,
};
use serde::Serialize;
use sf_kernels::{
    cosine_similarity_1024, evaluate_l3_gate, AlignedVec1024, DomainHypercubeLock, L3InspectionMode,
};
use sf_storage::pair_lock_sides;
use sha2::{Digest, Sha256};
use std::sync::Arc;
use std::time::Instant;

pub fn sha256_hex(input: &str) -> String {
    let digest = Sha256::digest(input.as_bytes());
    let mut out = String::with_capacity(64);
    for byte in digest {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

fn polarity_label(polarity: u8) -> &'static str {
    if polarity == 0 {
        "POSITIVE_ALLOWLIST"
    } else {
        "NEGATIVE_DENYLIST"
    }
}

fn mode_label(mode: L3InspectionMode) -> &'static str {
    match mode {
        L3InspectionMode::ModeATopK => "MODE_A_TOPK",
        L3InspectionMode::ModeBStrictHypercube => "MODE_B_STRICT_HYPERCUBE",
        L3InspectionMode::ModeCSpectralQuorum => "MODE_C_SPECTRAL_QUORUM",
    }
}

fn tier_passes(polarity: u8, score: f32, threshold: f32) -> bool {
    if polarity == 0 {
        score >= threshold
    } else {
        score < threshold
    }
}

struct GateClock {
    start: Instant,
}

impl GateClock {
    fn start() -> Self {
        Self {
            start: Instant::now(),
        }
    }

    fn elapsed_ns(&self) -> u64 {
        u64::try_from(self.start.elapsed().as_nanos()).unwrap_or(u64::MAX)
    }
}

pub fn evaluate_three_tier_cascade(
    full_prompt_vec: &AlignedVec1024,
    clause_vecs: &[AlignedVec1024],
    clauses_text: &[&str],
    lock: &DomainHypercubeLock,
    l3_mode: L3InspectionMode,
    max_telemetry_coords: usize,
) -> Result<u64, Box<BreachErrorEnvelope>> {
    let clock = GateClock::start();
    let polarity = polarity_label(lock.polarity);
    let mode = mode_label(l3_mode);
    let l1_cos = cosine_similarity_1024(full_prompt_vec, &lock.centroid);

    if !tier_passes(lock.polarity, l1_cos, lock.l1_cosine_threshold) {
        return Err(Box::new(breach(BreachParts {
            lock,
            polarity,
            mode,
            failing_tier: "L1_CATEGORICAL_COSINE",
            breaching_clause_index: None,
            breaching_clause_sha256: None,
            total_clauses_extracted: clause_vecs.len(),
            gate_latency_ns: clock.elapsed_ns(),
            metrics: metrics_l1(l1_cos, lock),
            message: format!(
                "Fail-closed containment breach at Tier L1_CATEGORICAL_COSINE for domain '{}'.",
                lock.domain_id
            ),
        })));
    }

    for (idx, clause_vec) in clause_vecs.iter().enumerate() {
        let clause_cos = cosine_similarity_1024(clause_vec, &lock.centroid);
        if !tier_passes(lock.polarity, clause_cos, lock.l2_clause_threshold) {
            let clause_hash = sha256_hex(clauses_text.get(idx).copied().unwrap_or(""));
            return Err(Box::new(breach(BreachParts {
                lock,
                polarity,
                mode,
                failing_tier: "L2_SLIDING_WINDOW",
                breaching_clause_index: Some(idx),
                breaching_clause_sha256: Some(clause_hash),
                total_clauses_extracted: clause_vecs.len(),
                gate_latency_ns: clock.elapsed_ns(),
                metrics: metrics_l2(l1_cos, clause_cos, lock),
                message: format!(
                    "Fail-closed containment breach at Tier L2_SLIDING_WINDOW on clause {idx} for domain '{}'.",
                    lock.domain_id
                ),
            })));
        }

        let l3 = evaluate_l3_gate(clause_vec, lock, l3_mode, max_telemetry_coords);
        if !l3.passed {
            let clause_hash = sha256_hex(clauses_text.get(idx).copied().unwrap_or(""));
            let failing_coordinates = l3
                .failing_coordinates
                .into_iter()
                .map(|item| CoordinateBreachDto {
                    dim: item.dim,
                    observed_val: item.observed_val,
                    observed_bits: format!("0x{:08x}", item.observed_bits),
                    lo_bound: item.lo_bound,
                    hi_bound: item.hi_bound,
                    delta_out_of_bounds: item.delta_out_of_bounds,
                })
                .collect();
            return Err(Box::new(breach(BreachParts {
                lock,
                polarity,
                mode,
                failing_tier: "L3_DDI_INSPECTOR",
                breaching_clause_index: Some(idx),
                breaching_clause_sha256: Some(clause_hash),
                total_clauses_extracted: clause_vecs.len(),
                gate_latency_ns: clock.elapsed_ns(),
                metrics: BreachMetricsDto {
                    l1_prompt_cosine: l1_cos,
                    l1_prompt_cosine_bits: f32_hex(l1_cos),
                    l1_threshold: lock.l1_cosine_threshold,
                    l2_clause_cosine: Some(clause_cos),
                    l2_clause_cosine_bits: Some(f32_hex(clause_cos)),
                    l2_threshold: lock.l2_clause_threshold,
                    l3_affirmative_votes: Some(l3.affirmative_votes),
                    l3_required_quorum: Some(l3.required_votes),
                    l3_evaluated_dimensions: Some(l3.evaluated_dimensions),
                    failing_coordinates,
                },
                message: format!(
                    "Fail-closed containment breach at Tier L3_DDI_INSPECTOR ({mode}) on clause {idx} for domain '{}'.",
                    lock.domain_id
                ),
            })));
        }
    }

    Ok(clock.elapsed_ns())
}

/// One pairwise Mode C failure. `breaching_clause_index` is `None` when the full prompt failed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PairwiseBreach {
    pub domain_id: String,
    pub breaching_pair_lock: String,
    pub breaching_clause_index: Option<usize>,
    pub clauses_skipped: Option<usize>,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct PairwiseTelemetry {
    pub domain_id: String,
    pub breaching_pair_lock: String,
    pub breaching_clause_index: Option<usize>,
    pub failing_tier: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub clauses_skipped: Option<usize>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct PairwiseBreachBody {
    pub kind: &'static str,
    pub code: &'static str,
    pub message: String,
    pub telemetry: PairwiseTelemetry,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct PairwiseBreachEnvelope {
    pub error: PairwiseBreachBody,
}

pub fn pairwise_breach_envelope(breach: PairwiseBreach) -> PairwiseBreachEnvelope {
    PairwiseBreachEnvelope {
        error: PairwiseBreachBody {
            kind: "ddi_ingress_breach",
            code: "SEMANTIC_CONTAINMENT_BREACH",
            message: breach.message,
            telemetry: PairwiseTelemetry {
                domain_id: breach.domain_id,
                breaching_pair_lock: breach.breaching_pair_lock,
                breaching_clause_index: breach.breaching_clause_index,
                failing_tier: "L3_PAIRWISE_QUORUM",
                clauses_skipped: breach.clauses_skipped,
            },
        },
    }
}

/// The mock embedder maps the exact token `BREACH` to its breach vector. Every other mock
/// string is the domain centroid and cannot sit in a bge-m3 differential envelope.
pub fn mock_batch_requires_pairwise(texts: &[&str]) -> bool {
    texts.contains(&"BREACH")
}

/// Tier-3 Mode C on the prompt and every clause, against each pairwise lock that names the target.
///
/// The stored envelope belongs to the left side of the pair id. The right side is evaluated with
/// denylist polarity so the same lock admits its own side and rejects the other.
///
/// An empty discriminative mask has no separating coordinates. Normalized bge-m3 ranges overlap
/// on those pairs, and allowlist quorum 1 would reject every in-domain vector. Those locks are
/// skipped. The kernel gate still fail-closes if a caller scores the empty mask directly.
pub fn evaluate_pairwise_containment(
    prompt_vec: &AlignedVec1024,
    clause_vecs: &[AlignedVec1024],
    target_domain: &str,
    pair_locks: &[Arc<DomainHypercubeLock>],
) -> Result<(), PairwiseBreach> {
    for lock in pair_locks {
        if lock.noise_mask.active_count() == 0 {
            continue;
        }
        let Some(polarity) = polarity_for_target(&lock.domain_id, target_domain) else {
            continue;
        };
        let mut tuned = (**lock).clone();
        tuned.polarity = polarity;
        if !pairwise_l3_passes(prompt_vec, &tuned) {
            return Err(pairwise_breach(
                target_domain,
                &lock.domain_id,
                None,
                clause_vecs.len(),
            ));
        }
        for (idx, clause_vec) in clause_vecs.iter().enumerate() {
            if !pairwise_l3_passes(clause_vec, &tuned) {
                return Err(pairwise_breach(
                    target_domain,
                    &lock.domain_id,
                    Some(idx),
                    clause_vecs.len(),
                ));
            }
        }
    }
    Ok(())
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

fn pairwise_l3_passes(vector: &AlignedVec1024, lock: &DomainHypercubeLock) -> bool {
    evaluate_l3_gate(vector, lock, L3InspectionMode::ModeCSpectralQuorum, 0).passed
}

fn pairwise_breach(
    domain_id: &str,
    pair_id: &str,
    clause_index: Option<usize>,
    total_clauses: usize,
) -> PairwiseBreach {
    let clauses_skipped = match clause_index {
        Some(idx) => Some(total_clauses.saturating_sub(1 + idx)),
        None => Some(total_clauses),
    };
    let message = match clause_index {
        Some(idx) => format!(
            "Fail-closed containment breach on pairwise lock '{pair_id}' for clause #{idx}."
        ),
        None => format!(
            "Fail-closed containment breach on pairwise lock '{pair_id}' for the full prompt."
        ),
    };
    PairwiseBreach {
        domain_id: domain_id.to_string(),
        breaching_pair_lock: pair_id.to_string(),
        breaching_clause_index: clause_index,
        clauses_skipped,
        message,
    }
}

fn metrics_l1(l1_cos: f32, lock: &DomainHypercubeLock) -> BreachMetricsDto {
    BreachMetricsDto {
        l1_prompt_cosine: l1_cos,
        l1_prompt_cosine_bits: f32_hex(l1_cos),
        l1_threshold: lock.l1_cosine_threshold,
        l2_clause_cosine: None,
        l2_clause_cosine_bits: None,
        l2_threshold: lock.l2_clause_threshold,
        l3_affirmative_votes: None,
        l3_required_quorum: None,
        l3_evaluated_dimensions: None,
        failing_coordinates: Vec::new(),
    }
}

fn metrics_l2(l1_cos: f32, l2_cos: f32, lock: &DomainHypercubeLock) -> BreachMetricsDto {
    BreachMetricsDto {
        l1_prompt_cosine: l1_cos,
        l1_prompt_cosine_bits: f32_hex(l1_cos),
        l1_threshold: lock.l1_cosine_threshold,
        l2_clause_cosine: Some(l2_cos),
        l2_clause_cosine_bits: Some(f32_hex(l2_cos)),
        l2_threshold: lock.l2_clause_threshold,
        l3_affirmative_votes: None,
        l3_required_quorum: None,
        l3_evaluated_dimensions: None,
        failing_coordinates: Vec::new(),
    }
}

struct BreachParts<'a> {
    lock: &'a DomainHypercubeLock,
    polarity: &'static str,
    mode: &'static str,
    failing_tier: &'static str,
    breaching_clause_index: Option<usize>,
    breaching_clause_sha256: Option<String>,
    total_clauses_extracted: usize,
    gate_latency_ns: u64,
    metrics: BreachMetricsDto,
    message: String,
}

fn breach(parts: BreachParts<'_>) -> BreachErrorEnvelope {
    let BreachParts {
        lock,
        polarity,
        mode,
        failing_tier,
        breaching_clause_index,
        breaching_clause_sha256,
        total_clauses_extracted,
        gate_latency_ns,
        metrics,
        message,
    } = parts;
    let clauses_skipped = match breaching_clause_index {
        Some(idx) => total_clauses_extracted.saturating_sub(1 + idx),
        None => total_clauses_extracted,
    };
    BreachErrorEnvelope {
        error: BreachErrorBody {
            kind: "ddi_ingress_breach",
            code: "SEMANTIC_CONTAINMENT_BREACH",
            message,
            telemetry: BreachTelemetryDto {
                domain_id: lock.domain_id.clone(),
                domain_version: lock.domain_version,
                polarity,
                failing_tier,
                l3_mode: mode,
                breaching_clause_index,
                breaching_clause_sha256,
                total_clauses_extracted,
                clauses_skipped,
                gate_latency_ns,
                normalizer_segmenter_us: None,
                embedding_inference_ms: None,
                simd_gate_kernel_us: Some(gate_latency_ns / 1_000),
                total_pipeline_ms: None,
                metrics,
            },
        },
    }
}

#[cfg(test)]
mod tests {
    use super::mock_batch_requires_pairwise;

    #[test]
    fn only_the_exact_breach_token_keeps_mock_pairwise() {
        assert!(!mock_batch_requires_pairwise(&[
            "Cómo implementar un generador con yield en Python"
        ]));
        assert!(mock_batch_requires_pairwise(&["hello", "BREACH"]));
        assert!(!mock_batch_requires_pairwise(&["breach"]));
    }
}
