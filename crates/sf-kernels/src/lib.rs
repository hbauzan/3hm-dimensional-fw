//! Numerical kernels. Cosine and hypercube masks dispatch to the active ISA.

mod fhv1;
mod scalar;
mod simd;
mod types;

pub use fhv1::{
    classify_movement_tiers, compute_fhv1_profile_stats, evaluate_fhv1_batch, evaluate_fhv1_chunk,
    fhv1_evaluated_dims, is_fhv1_rogue_dimension, DimBoundStatus, Fhv1BatchEval, Fhv1ChunkEval,
    Fhv1DimComparison, Fhv1Error, Fhv1EvalGranularity, Fhv1ProfileStats, Fhv1QuantileCutoffs,
    Fhv1Quantiles, Fhv1TierClassification, MovementMetric, MovementTier,
};

pub use scalar::{
    evaluate_l3_gate, scalar_cosine_f64, scalar_cosine_similarity, scalar_hypercube_bitmask,
    COSINE_PARITY_ABS_BOUND,
};
pub use simd::{dispatch_cosine_f64, dispatch_hypercube_bitmask};
pub use types::*;

/// Dispatched cosine, narrowed to binary32 after the `f64` accumulation.
#[inline]
pub fn cosine_similarity_1024(q: &AlignedVec1024, c: &AlignedVec1024) -> f32 {
    dispatch_cosine_f64(q, c) as f32
}

/// `f64` cosine used by the parity suite. SIMD must stay within [`COSINE_PARITY_ABS_BOUND`].
#[inline]
pub fn cosine_similarity_1024_f64(q: &AlignedVec1024, c: &AlignedVec1024) -> f64 {
    dispatch_cosine_f64(q, c)
}

/// Dispatched in-box mask. Active noise bits are already applied.
#[inline]
pub fn evaluate_hypercube_bitmask(
    q: &AlignedVec1024,
    lock: &DomainHypercubeLock,
) -> [u64; NOISE_MASK_WORDS] {
    dispatch_hypercube_bitmask(q, lock)
}
