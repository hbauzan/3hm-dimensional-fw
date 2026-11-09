//! Cache-aligned binary32 tensors and domain locks.

use std::fmt;

/// Dense width of `BAAI/bge-m3`.
pub const DIM: usize = 1024;
/// `1024 / 64` little-endian mask words.
pub const NOISE_MASK_WORDS: usize = 16;
/// `ceil(0.10 * 1024)`.
pub const DEFAULT_QUORUM_K: u16 = 103;
/// Storage capacity for Top-K indices. 128 keeps the tail 64-byte friendly.
pub const MAX_TOPK: usize = 128;
/// Anisotropic Rogue Dimensions (Timkey & van Schijndel, 2021).
/// The nine universal background coordinates pruned by [`NoiseBitmask1024::new_bge_m3_default`]:
/// `[292, 297, 308, 329, 386, 404, 577, 616, 780]`.
pub const UNIVERSAL_NOISE_INDICES: [u16; 9] = [292, 297, 308, 329, 386, 404, 577, 616, 780];

/// 64-byte aligned 1024-d binary32 tensor on the 1024D Contrastive Embedding Manifold ($S^{1023} \subset \mathbb{R}^{1024}$).
/// Deterministic IEEE 754 binary32 evaluation with 0 ULP cross-architecture parity. Size is 4096 bytes.
#[repr(C, align(64))]
#[derive(Clone, Copy)]
pub struct AlignedVec1024 {
    pub data: [f32; DIM],
}

const _: () = assert!(std::mem::size_of::<AlignedVec1024>() == 4096);
const _: () = assert!(std::mem::align_of::<AlignedVec1024>() == 64);
const _: () = assert!(std::mem::align_of::<NoiseBitmask1024>() == 64);

impl AlignedVec1024 {
    #[inline]
    pub const fn zeros() -> Self {
        Self { data: [0.0; DIM] }
    }

    #[inline]
    pub fn from_slice(src: &[f32]) -> Result<Self, DimError> {
        if src.len() != DIM {
            return Err(DimError { len: src.len() });
        }
        let mut out = Self::zeros();
        out.data.copy_from_slice(src);
        Ok(out)
    }
}

impl fmt::Debug for AlignedVec1024 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "AlignedVec1024([f32; 1024] @ {:p})", self.data.as_ptr())
    }
}

impl PartialEq for AlignedVec1024 {
    fn eq(&self, other: &Self) -> bool {
        self.data
            .iter()
            .zip(other.data.iter())
            .all(|(a, b)| a.to_bits() == b.to_bits())
    }
}

impl Eq for AlignedVec1024 {}

/// Length was not 1024.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DimError {
    pub len: usize,
}

impl fmt::Display for DimError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "expected {DIM} floats, got {}", self.len)
    }
}

impl std::error::Error for DimError {}

/// 1024-bit noise mask. Bit `d == 1` means coordinate `d` is active.
#[repr(C, align(64))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct NoiseBitmask1024 {
    pub words: [u64; NOISE_MASK_WORDS],
}

impl NoiseBitmask1024 {
    /// Every coordinate active.
    #[inline]
    pub const fn all_active() -> Self {
        Self {
            words: [u64::MAX; NOISE_MASK_WORDS],
        }
    }

    /// Clears the nine universal BGE-M3 noise coordinates (1015 active).
    #[inline]
    pub const fn new_bge_m3_default() -> Self {
        let mut words = [u64::MAX; NOISE_MASK_WORDS];
        let mut i = 0;
        while i < UNIVERSAL_NOISE_INDICES.len() {
            let idx = UNIVERSAL_NOISE_INDICES[i] as usize;
            let word_idx = idx >> 6;
            let bit_idx = idx & 63;
            words[word_idx] &= !(1u64 << bit_idx);
            i += 1;
        }
        Self { words }
    }

    #[inline]
    pub fn prune_coordinate(&mut self, dim: u16) {
        assert!(
            (dim as usize) < DIM,
            "dimension index out of bounds [0, 1024)"
        );
        let word_idx = (dim as usize) >> 6;
        let bit_idx = (dim as usize) & 63;
        self.words[word_idx] &= !(1u64 << bit_idx);
    }

    #[inline]
    pub const fn is_active(&self, dim: usize) -> bool {
        let word_idx = dim >> 6;
        let bit_idx = dim & 63;
        ((self.words[word_idx] >> bit_idx) & 1) == 1
    }

    #[inline]
    pub fn active_count(&self) -> u32 {
        self.words.iter().map(|w| w.count_ones()).sum()
    }
}

/// Inputs for a lock. Bounds are raw envelopes; the constructor pre-dilates them.
pub struct LockSpec {
    pub domain_id: String,
    pub centroid: AlignedVec1024,
    pub lo: AlignedVec1024,
    pub hi: AlignedVec1024,
    pub epsilon: f32,
    pub noise_mask: NoiseBitmask1024,
    pub top_k_indices: [u16; MAX_TOPK],
    pub top_k_len: u16,
    pub quorum_k: u16,
    pub l1_cosine_threshold: f32,
    pub l2_clause_threshold: f32,
    pub polarity: u8,
    pub domain_version: u64,
}

/// Pre-dilated domain lock. `lo_dilated = lo - eps`, `hi_dilated = hi + eps` in binary32.
#[repr(C, align(64))]
#[derive(Clone, Debug)]
pub struct DomainHypercubeLock {
    pub centroid: AlignedVec1024,
    pub lo_dilated: AlignedVec1024,
    pub hi_dilated: AlignedVec1024,
    pub noise_mask: NoiseBitmask1024,
    pub top_k_indices: [u16; MAX_TOPK],
    pub top_k_len: u16,
    pub quorum_k: u16,
    pub l1_cosine_threshold: f32,
    pub l2_clause_threshold: f32,
    pub epsilon: f32,
    pub polarity: u8,
    pub domain_version: u64,
    pub domain_id: String,
}

impl DomainHypercubeLock {
    pub fn from_spec(spec: LockSpec) -> Self {
        let mut lo_dilated = spec.lo;
        let mut hi_dilated = spec.hi;
        let eps = spec.epsilon;
        for dim in 0..DIM {
            lo_dilated.data[dim] = spec.lo.data[dim] - eps;
            hi_dilated.data[dim] = spec.hi.data[dim] + eps;
        }
        Self {
            centroid: spec.centroid,
            lo_dilated,
            hi_dilated,
            noise_mask: spec.noise_mask,
            top_k_indices: spec.top_k_indices,
            top_k_len: spec.top_k_len,
            quorum_k: spec.quorum_k,
            l1_cosine_threshold: spec.l1_cosine_threshold,
            l2_clause_threshold: spec.l2_clause_threshold,
            epsilon: eps,
            polarity: spec.polarity,
            domain_version: spec.domain_version,
            domain_id: spec.domain_id,
        }
    }
}

/// Tier-3 coordinate subspace strategy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum L3InspectionMode {
    /// Mode A: Top-K coordinate bounding box.
    ModeATopK,
    /// Mode B: Strict 1024-dimensional hypercube envelope.
    ModeBStrictHypercube,
    /// Mode C: Subspace Coordinate Quorum (K-of-D L∞ Gate).
    /// Operates in the canonical coordinate basis via ℓ_∞ bounding boxes and bitmask popcount.
    ModeCSpectralQuorum,
}

/// One coordinate outside the pre-dilated box.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CoordinateBreach {
    pub dim: u16,
    pub observed_val: f32,
    pub observed_bits: u32,
    pub lo_bound: f32,
    pub hi_bound: f32,
    pub delta_out_of_bounds: f32,
}

/// Tier-3 result. `failing_coordinates` is empty on pass.
#[derive(Debug, Clone, PartialEq)]
pub struct L3EvalResult {
    pub passed: bool,
    pub affirmative_votes: u16,
    pub evaluated_dimensions: u16,
    pub required_votes: u16,
    pub failing_coordinates: Vec<CoordinateBreach>,
}
