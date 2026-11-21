//! Exhaustive coordinate-wise axis-aligned bounding box in IEEE 754 binary64.
//!
//! A chunk passes iff every evaluated coordinate lies in `[min_d, max_d]` (allowlist).
//! `mean_d` is recorded as `delta_vs_mean` and never changes the verdict.
//! Population variance is Welford's `M2 / N`. Movement tiers use linear quantiles
//! (Hyndman-Fan type 7) on dimensions whose `span > 0`. `span == 0` is `ZeroSpan`.

use std::fmt;

use crate::{DIM, UNIVERSAL_NOISE_INDICES};

/// Calibration or evaluation rejected the input.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Fhv1Error {
    BadDim { len: usize },
    NonFinite { sample_index: usize, dim: usize },
    EmptyCorpus,
    InvalidQuantiles,
}

impl fmt::Display for Fhv1Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::BadDim { len } => write!(f, "expected {DIM} floats, got {len}"),
            Self::NonFinite { sample_index, dim } => {
                write!(f, "non-finite value at sample {sample_index} dim {dim}")
            }
            Self::EmptyCorpus => write!(f, "fhv1 corpus is empty"),
            Self::InvalidQuantiles => {
                write!(f, "fhv1 quantiles require 0 <= p25 < p75 < p90 <= 1")
            }
        }
    }
}

impl std::error::Error for Fhv1Error {}

/// Statistic ranked when assigning movement tiers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MovementMetric {
    Variance,
    StdDev,
    Span,
}

/// Ordinal movement class. Discriminants are the stored `movement_tier_codes`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum MovementTier {
    ZeroSpan = 0,
    LowAnchor = 1,
    Moderate = 2,
    HighVolatility = 3,
    ExtremeMovement = 4,
}

impl MovementTier {
    #[inline]
    pub const fn code(self) -> u8 {
        self as u8
    }

    #[inline]
    pub const fn from_code(code: u8) -> Option<Self> {
        match code {
            0 => Some(Self::ZeroSpan),
            1 => Some(Self::LowAnchor),
            2 => Some(Self::Moderate),
            3 => Some(Self::HighVolatility),
            4 => Some(Self::ExtremeMovement),
            _ => None,
        }
    }
}

/// Quantile levels in `(0, 1]`, strictly increasing.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Fhv1Quantiles {
    pub p25: f64,
    pub p75: f64,
    pub p90: f64,
}

impl Fhv1Quantiles {
    pub const fn standard() -> Self {
        Self {
            p25: 0.25,
            p75: 0.75,
            p90: 0.90,
        }
    }

    pub fn validate(self) -> Result<(), Fhv1Error> {
        let finite = self.p25.is_finite() && self.p75.is_finite() && self.p90.is_finite();
        let ordered =
            self.p25 >= 0.0 && self.p90 <= 1.0 && self.p25 < self.p75 && self.p75 < self.p90;
        if finite && ordered {
            Ok(())
        } else {
            Err(Fhv1Error::InvalidQuantiles)
        }
    }
}

/// Realized quantile cutoffs on the positive-span dimensions.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Fhv1QuantileCutoffs {
    pub p25: f64,
    pub p75: f64,
    pub p90: f64,
}

/// Per-dimension envelope and Welford moments for one calibrated profile.
#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1ProfileStats {
    pub min: [f64; DIM],
    pub max: [f64; DIM],
    pub mean: [f64; DIM],
    pub span: [f64; DIM],
    pub variance: [f64; DIM],
    pub std_dev: [f64; DIM],
    pub movement_tier_codes: [u8; DIM],
    pub quantiles: Fhv1Quantiles,
    pub sample_count: u64,
    pub polarity: u8,
    pub metric: MovementMetric,
    pub cutoffs: Fhv1QuantileCutoffs,
}

/// How many chunks decide `overall_passed`. Every chunk is still evaluated.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Fhv1EvalGranularity {
    /// `overall_passed` follows chunk 0 (`full_text_passed`).
    FullOnly,
    /// `overall_passed` follows `all_chunks_passed`.
    Clauses,
    /// `overall_passed` follows `all_chunks_passed`.
    FullMirror,
}

/// Coordinate verdict against `[min_d, max_d]`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DimBoundStatus {
    InBounds,
    Underflow,
    Overflow,
    PrunedRogue,
}

/// One coordinate of a chunk, with the observed value stored as raw bits.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Fhv1DimComparison {
    pub observed_bits: u64,
    pub observed: f64,
    pub min: f64,
    pub max: f64,
    pub mean: f64,
    pub status: DimBoundStatus,
    pub violation_delta: f64,
    pub delta_vs_mean: f64,
    pub norm_pos: Option<f64>,
}

/// Full 1024-d evaluation of one chunk. Dimensions live on the heap.
#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1ChunkEval {
    pub chunk_passed: bool,
    pub evaluated_dims: u16,
    pub failed_dims_count: u16,
    pub underflow_count: u16,
    pub overflow_count: u16,
    pub max_violation_delta: f64,
    pub mean_abs_delta_vs_mean: f64,
    pub dimensions: Box<[Fhv1DimComparison; DIM]>,
}

/// Every chunk of one input. `chunk[0]` is the full-text observation.
#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1BatchEval {
    pub chunks: Vec<Fhv1ChunkEval>,
    pub full_text_passed: bool,
    pub all_chunks_passed: bool,
    pub overall_passed: bool,
    pub granularity: Fhv1EvalGranularity,
}

/// Tier codes plus the cutoffs that produced them.
#[derive(Debug, Clone, PartialEq)]
pub struct Fhv1TierClassification {
    pub codes: Box<[u8; DIM]>,
    pub cutoffs: Fhv1QuantileCutoffs,
}

#[inline]
pub fn is_fhv1_rogue_dimension(dim: usize) -> bool {
    dim < DIM && UNIVERSAL_NOISE_INDICES.binary_search(&(dim as u16)).is_ok()
}

#[inline]
pub fn fhv1_evaluated_dims(use_rogue_mask: bool) -> u16 {
    if use_rogue_mask {
        (DIM - UNIVERSAL_NOISE_INDICES.len()) as u16
    } else {
        DIM as u16
    }
}

/// Welford envelopes and movement tiers. Rejects an empty corpus, a short row, and any non-finite coordinate.
pub fn compute_fhv1_profile_stats<R>(
    rows: &[R],
    polarity: u8,
    metric: MovementMetric,
    quantiles: Fhv1Quantiles,
) -> Result<Box<Fhv1ProfileStats>, Fhv1Error>
where
    R: AsRef<[f64]>,
{
    if rows.is_empty() {
        return Err(Fhv1Error::EmptyCorpus);
    }
    quantiles.validate()?;
    let moments = accumulate_rows(rows)?;
    let sample_count = rows.len() as u64;
    let mut span = [0.0; DIM];
    let mut variance = [0.0; DIM];
    let mut std_dev = [0.0; DIM];
    let inv_n = 1.0 / sample_count as f64;
    for dim in 0..DIM {
        span[dim] = moments.max[dim] - moments.min[dim];
        variance[dim] = moments.m2[dim] * inv_n;
        std_dev[dim] = variance[dim].sqrt();
    }
    let tiers = classify_movement_tiers(&span, &variance, &std_dev, metric, quantiles)?;
    let mut movement_tier_codes = [0u8; DIM];
    movement_tier_codes.copy_from_slice(tiers.codes.as_ref());
    Ok(Box::new(Fhv1ProfileStats {
        min: *moments.min,
        max: *moments.max,
        mean: *moments.mean,
        span,
        variance,
        std_dev,
        movement_tier_codes,
        quantiles,
        sample_count,
        polarity,
        metric,
        cutoffs: tiers.cutoffs,
    }))
}

/// Reclassify stored moments. `span == 0` stays `ZeroSpan` for every metric.
pub fn classify_movement_tiers(
    span: &[f64; DIM],
    variance: &[f64; DIM],
    std_dev: &[f64; DIM],
    metric: MovementMetric,
    quantiles: Fhv1Quantiles,
) -> Result<Fhv1TierClassification, Fhv1Error> {
    quantiles.validate()?;
    let mut sample = Vec::new();
    for dim in 0..DIM {
        if span[dim] > 0.0 {
            sample.push(metric_value(span, variance, std_dev, metric, dim));
        }
    }
    sample.sort_by(|left, right| left.total_cmp(right));
    let cutoffs = if sample.is_empty() {
        Fhv1QuantileCutoffs {
            p25: 0.0,
            p75: 0.0,
            p90: 0.0,
        }
    } else {
        Fhv1QuantileCutoffs {
            p25: linear_quantile(&sample, quantiles.p25),
            p75: linear_quantile(&sample, quantiles.p75),
            p90: linear_quantile(&sample, quantiles.p90),
        }
    };
    let mut codes = Box::new([0u8; DIM]);
    for dim in 0..DIM {
        codes[dim] = if span[dim] == 0.0 {
            MovementTier::ZeroSpan.code()
        } else {
            let value = metric_value(span, variance, std_dev, metric, dim);
            tier_for_value(value, cutoffs).code()
        };
    }
    Ok(Fhv1TierClassification { codes, cutoffs })
}

/// Score one 1024-d vector. Rogue coordinates are `PrunedRogue` when `use_rogue_mask` is set.
pub fn evaluate_fhv1_chunk(
    stats: &Fhv1ProfileStats,
    observed: &[f64],
    use_rogue_mask: bool,
) -> Result<Fhv1ChunkEval, Fhv1Error> {
    evaluate_row(stats, observed, use_rogue_mask, 0)
}

/// Score every chunk. No short-circuit: a failing chunk does not skip the rest.
///
/// `full_text_passed` is chunk 0. `overall_passed` is chunk 0 for [`Fhv1EvalGranularity::FullOnly`]
/// and `all_chunks_passed` for clause and full-mirror granularity.
pub fn evaluate_fhv1_batch<R>(
    stats: &Fhv1ProfileStats,
    rows: &[R],
    granularity: Fhv1EvalGranularity,
    use_rogue_mask: bool,
) -> Result<Fhv1BatchEval, Fhv1Error>
where
    R: AsRef<[f64]>,
{
    if rows.is_empty() {
        return Err(Fhv1Error::EmptyCorpus);
    }
    let mut chunks = Vec::with_capacity(rows.len());
    for (index, row) in rows.iter().enumerate() {
        chunks.push(evaluate_row(stats, row.as_ref(), use_rogue_mask, index)?);
    }
    let full_text_passed = chunks[0].chunk_passed;
    let all_chunks_passed = chunks.iter().all(|chunk| chunk.chunk_passed);
    let overall_passed = match granularity {
        Fhv1EvalGranularity::FullOnly => full_text_passed,
        Fhv1EvalGranularity::Clauses | Fhv1EvalGranularity::FullMirror => all_chunks_passed,
    };
    Ok(Fhv1BatchEval {
        chunks,
        full_text_passed,
        all_chunks_passed,
        overall_passed,
        granularity,
    })
}

struct WelfordMoments {
    min: Box<[f64; DIM]>,
    max: Box<[f64; DIM]>,
    mean: Box<[f64; DIM]>,
    m2: Box<[f64; DIM]>,
}

fn accumulate_rows<R>(rows: &[R]) -> Result<WelfordMoments, Fhv1Error>
where
    R: AsRef<[f64]>,
{
    let mut min = Box::new([f64::INFINITY; DIM]);
    let mut max = Box::new([f64::NEG_INFINITY; DIM]);
    let mut mean = Box::new([0.0; DIM]);
    let mut m2 = Box::new([0.0; DIM]);
    for (sample_index, row) in rows.iter().enumerate() {
        let values = row.as_ref();
        if values.len() != DIM {
            return Err(Fhv1Error::BadDim { len: values.len() });
        }
        let n = (sample_index as f64) + 1.0;
        for dim in 0..DIM {
            let value = values[dim];
            if !value.is_finite() {
                return Err(Fhv1Error::NonFinite { sample_index, dim });
            }
            let delta = value - mean[dim];
            mean[dim] += delta / n;
            let delta2 = value - mean[dim];
            m2[dim] += delta * delta2;
            if value < min[dim] {
                min[dim] = value;
            }
            if value > max[dim] {
                max[dim] = value;
            }
        }
    }
    Ok(WelfordMoments { min, max, mean, m2 })
}

fn evaluate_row(
    stats: &Fhv1ProfileStats,
    observed: &[f64],
    use_rogue_mask: bool,
    sample_index: usize,
) -> Result<Fhv1ChunkEval, Fhv1Error> {
    if observed.len() != DIM {
        return Err(Fhv1Error::BadDim {
            len: observed.len(),
        });
    }
    let mut dimensions = Box::new(
        [Fhv1DimComparison {
            observed_bits: 0,
            observed: 0.0,
            min: 0.0,
            max: 0.0,
            mean: 0.0,
            status: DimBoundStatus::InBounds,
            violation_delta: 0.0,
            delta_vs_mean: 0.0,
            norm_pos: None,
        }; DIM],
    );
    let mut failed_dims_count = 0u16;
    let mut underflow_count = 0u16;
    let mut overflow_count = 0u16;
    let mut max_violation_delta = 0.0f64;
    let mut abs_delta_sum = 0.0f64;
    let evaluated_dims = fhv1_evaluated_dims(use_rogue_mask);
    for dim in 0..DIM {
        let value = observed[dim];
        if !value.is_finite() {
            return Err(Fhv1Error::NonFinite { sample_index, dim });
        }
        let min = stats.min[dim];
        let max = stats.max[dim];
        let mean = stats.mean[dim];
        let span = stats.span[dim];
        let pruned = use_rogue_mask && is_fhv1_rogue_dimension(dim);
        let (status, violation_delta) = if pruned {
            (DimBoundStatus::PrunedRogue, 0.0)
        } else if value < min {
            (DimBoundStatus::Underflow, min - value)
        } else if value > max {
            (DimBoundStatus::Overflow, value - max)
        } else {
            (DimBoundStatus::InBounds, 0.0)
        };
        if !pruned {
            abs_delta_sum += (value - mean).abs();
            match status {
                DimBoundStatus::Underflow => {
                    underflow_count += 1;
                    failed_dims_count += 1;
                }
                DimBoundStatus::Overflow => {
                    overflow_count += 1;
                    failed_dims_count += 1;
                }
                DimBoundStatus::InBounds | DimBoundStatus::PrunedRogue => {}
            }
            if violation_delta > max_violation_delta {
                max_violation_delta = violation_delta;
            }
        }
        let norm_pos = if span == 0.0 {
            None
        } else {
            Some((value - min) / span)
        };
        dimensions[dim] = Fhv1DimComparison {
            observed_bits: value.to_bits(),
            observed: value,
            min,
            max,
            mean,
            status,
            violation_delta,
            delta_vs_mean: value - mean,
            norm_pos,
        };
    }
    let mean_abs_delta_vs_mean = if evaluated_dims == 0 {
        0.0
    } else {
        abs_delta_sum / f64::from(evaluated_dims)
    };
    Ok(Fhv1ChunkEval {
        chunk_passed: failed_dims_count == 0,
        evaluated_dims,
        failed_dims_count,
        underflow_count,
        overflow_count,
        max_violation_delta,
        mean_abs_delta_vs_mean,
        dimensions,
    })
}

fn metric_value(
    span: &[f64; DIM],
    variance: &[f64; DIM],
    std_dev: &[f64; DIM],
    metric: MovementMetric,
    dim: usize,
) -> f64 {
    match metric {
        MovementMetric::Variance => variance[dim],
        MovementMetric::StdDev => std_dev[dim],
        MovementMetric::Span => span[dim],
    }
}

fn tier_for_value(value: f64, cutoffs: Fhv1QuantileCutoffs) -> MovementTier {
    if value <= cutoffs.p25 {
        MovementTier::LowAnchor
    } else if value <= cutoffs.p75 {
        MovementTier::Moderate
    } else if value <= cutoffs.p90 {
        MovementTier::HighVolatility
    } else {
        MovementTier::ExtremeMovement
    }
}

/// Hyndman-Fan type 7: `rank = p * (n - 1)` with linear interpolation.
fn linear_quantile(sorted: &[f64], p: f64) -> f64 {
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
