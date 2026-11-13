//! Envelope, centroid, and SNR noise pruning. Accumulators stay in `f64`.

use sf_kernels::{
    AlignedVec1024, DomainHypercubeLock, LockSpec, NoiseBitmask1024, DEFAULT_QUORUM_K, DIM,
    MAX_TOPK, NOISE_MASK_WORDS,
};
use sha2::Digest;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CalibrationError {
    pub message: String,
}

impl std::fmt::Display for CalibrationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.message)
    }
}

impl std::error::Error for CalibrationError {}

pub struct Calibration {
    pub lo: [f32; DIM],
    pub hi: [f32; DIM],
    pub centroid: [f32; DIM],
    pub mu: [f64; DIM],
    pub noise_mask: NoiseBitmask1024,
    pub top_k: [u16; 103],
    pub top_k_len: u16,
    pub sha256: [u8; 32],
    pub rows: u64,
}

/// Corpus provenance stored beside a hypercube row.
///
/// `UNPROVIDED` is the only value legal when ingestion has no external file.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CorpusManifest {
    pub doc_count: u64,
    pub sha256: [u8; 32],
}

impl CorpusManifest {
    pub const UNPROVIDED: Self = Self {
        doc_count: 0,
        sha256: [0u8; 32],
    };
}

impl Calibration {
    pub fn manifest(&self) -> CorpusManifest {
        CorpusManifest {
            doc_count: self.rows,
            sha256: self.sha256,
        }
    }
}

/// SHA-256 of the little-endian `f32` payload and the total row count.
/// An empty list is [`CorpusManifest::UNPROVIDED`], not a one-row digest.
pub fn manifest_from_matrices(matrices: &[&[f32]]) -> Result<CorpusManifest, CalibrationError> {
    if matrices.is_empty() {
        return Ok(CorpusManifest::UNPROVIDED);
    }
    for matrix in matrices {
        if matrix.is_empty() || !matrix.len().is_multiple_of(DIM) {
            return Err(CalibrationError {
                message: format!(
                    "matrix length {} is not a positive multiple of {DIM}",
                    matrix.len()
                ),
            });
        }
        for (offset, value) in matrix.iter().copied().enumerate() {
            if !value.is_finite() {
                return Err(CalibrationError {
                    message: format!("non-finite sample at flat index {offset}"),
                });
            }
        }
    }
    Ok(digest_f32_rows(matrices))
}

fn digest_f32_rows(matrices: &[&[f32]]) -> CorpusManifest {
    let mut hasher = sha2::Sha256::new();
    let mut doc_count = 0u64;
    for matrix in matrices {
        doc_count += (matrix.len() / DIM) as u64;
        for value in *matrix {
            hasher.update(value.to_le_bytes());
        }
    }
    let digest = hasher.finalize();
    let mut sha256 = [0u8; 32];
    sha256.copy_from_slice(&digest);
    CorpusManifest { doc_count, sha256 }
}

pub fn calibrate_matrix(
    rows: &[f32],
    extra_pruned_dims: usize,
) -> Result<Calibration, CalibrationError> {
    if !rows.len().is_multiple_of(DIM) || rows.is_empty() {
        return Err(CalibrationError {
            message: format!(
                "matrix length {} is not a positive multiple of {DIM}",
                rows.len()
            ),
        });
    }
    let n = rows.len() / DIM;
    let mut lo = [f32::INFINITY; DIM];
    let mut hi = [f32::NEG_INFINITY; DIM];
    let mut sum = [0.0f64; DIM];
    for (dim, value) in rows.iter().copied().enumerate() {
        if !value.is_finite() {
            return Err(CalibrationError {
                message: format!("non-finite sample at flat index {dim}"),
            });
        }
        let coord = dim % DIM;
        lo[coord] = lo[coord].min(value);
        hi[coord] = hi[coord].max(value);
        sum[coord] += f64::from(value);
    }
    let inv_n = 1.0 / n as f64;
    let mut mu = [0.0f64; DIM];
    for dim in 0..DIM {
        mu[dim] = sum[dim] * inv_n;
    }
    let mut norm_sq = 0.0f64;
    for value in mu {
        norm_sq += value * value;
    }
    let inv_norm = if norm_sq > 0.0 {
        1.0 / norm_sq.sqrt()
    } else {
        0.0
    };
    let mut centroid = [0.0f32; DIM];
    for dim in 0..DIM {
        centroid[dim] = (mu[dim] * inv_norm) as f32;
    }
    let noise_mask = calibrate_noise_bitmask(&mu, &lo, &hi, extra_pruned_dims);
    let top_k = top_k_indices(&mu, &lo, &hi, &noise_mask);
    let manifest = digest_f32_rows(&[rows]);
    let active = usize::try_from(noise_mask.active_count()).unwrap_or(0);
    let top_k_len = u16::try_from(active.min(usize::from(DEFAULT_QUORUM_K))).unwrap_or(0);
    Ok(Calibration {
        lo,
        hi,
        centroid,
        mu,
        noise_mask,
        top_k,
        top_k_len,
        sha256: manifest.sha256,
        rows: manifest.doc_count,
    })
}

pub fn calibrate_noise_bitmask(
    mu: &[f64; DIM],
    lo: &[f32; DIM],
    hi: &[f32; DIM],
    extra_pruned_dims: usize,
) -> NoiseBitmask1024 {
    let mut mask = NoiseBitmask1024::new_bge_m3_default();
    if extra_pruned_dims == 0 {
        return mask;
    }
    let mut ranked: Vec<(f64, usize)> = (0..DIM)
        .filter(|dim| mask.is_active(*dim))
        .map(|dim| (snr(mu[dim], lo[dim], hi[dim]), dim))
        .collect();
    ranked.sort_by(|left, right| {
        left.0
            .total_cmp(&right.0)
            .then_with(|| left.1.cmp(&right.1))
    });
    for (_, dim) in ranked.into_iter().take(extra_pruned_dims) {
        mask.prune_coordinate(dim as u16);
    }
    mask
}

pub fn top_k_indices(
    mu: &[f64; DIM],
    lo: &[f32; DIM],
    hi: &[f32; DIM],
    mask: &NoiseBitmask1024,
) -> [u16; 103] {
    let mut ranked: Vec<(f64, usize)> = (0..DIM)
        .filter(|dim| mask.is_active(*dim))
        .map(|dim| (snr(mu[dim], lo[dim], hi[dim]), dim))
        .collect();
    ranked.sort_by(|left, right| {
        right
            .0
            .total_cmp(&left.0)
            .then_with(|| left.1.cmp(&right.1))
    });
    let mut top_k = [292u16; 103];
    for (slot, (_, dim)) in top_k.iter_mut().zip(ranked.into_iter().take(103)) {
        *slot = dim as u16;
    }
    top_k
}

fn snr(mu: f64, lo: f32, hi: f32) -> f64 {
    let width = f64::from(hi) - f64::from(lo);
    mu.abs() / (width + f64::from(f32::EPSILON))
}

pub fn read_f32_matrix(bytes: &[u8]) -> Result<Vec<f32>, CalibrationError> {
    if bytes.len() < 8 {
        return Err(CalibrationError {
            message: "f32 matrix file is missing the row-count header".to_string(),
        });
    }
    let mut header = [0u8; 8];
    header.copy_from_slice(&bytes[..8]);
    let rows = u64::from_le_bytes(header) as usize;
    let payload = &bytes[8..];
    let expected = rows.saturating_mul(DIM).saturating_mul(4);
    if payload.len() != expected {
        return Err(CalibrationError {
            message: format!(
                "payload {} bytes, expected {expected} for {rows} rows",
                payload.len()
            ),
        });
    }
    let mut out = Vec::with_capacity(rows * DIM);
    for chunk in payload.chunks_exact(4) {
        let mut buf = [0u8; 4];
        buf.copy_from_slice(chunk);
        out.push(f32::from_le_bytes(buf));
    }
    Ok(out)
}

/// The eleven domains of the canonical differential registry, in list order.
pub const CANONICAL_DOMAINS: [&str; 11] = [
    "python",
    "receta",
    "legal",
    "medicina",
    "astronomia",
    "finanzas",
    "filosofia",
    "musica",
    "geologia",
    "botanica",
    "arquitectura",
];

const CANONICAL_COSINE: f32 = 0.50;

pub fn is_canonical_domain(domain_id: &str) -> bool {
    CANONICAL_DOMAINS.contains(&domain_id)
}

/// `left_right` when both sides are canonical domain names. The left side owns the envelope.
pub fn pair_lock_sides(domain_id: &str) -> Option<(&str, &str)> {
    let (left, right) = domain_id.split_once('_')?;
    if left != right && is_canonical_domain(left) && is_canonical_domain(right) {
        Some((left, right))
    } else {
        None
    }
}

/// Differential lock for one unordered pair.
///
/// The id is `min_max` in lexicographic order. The stored envelope belongs to the
/// lexicographically smaller domain. Callers that target the other side invert polarity.
pub fn calibrate_pairwise_lock(
    domain_a: &str,
    domain_b: &str,
    rows_a: &[f32],
    rows_b: &[f32],
) -> Result<DomainHypercubeLock, CalibrationError> {
    require_canonical(domain_a)?;
    require_canonical(domain_b)?;
    if domain_a == domain_b {
        return Err(CalibrationError {
            message: format!("pairwise lock needs two distinct domains, got '{domain_a}'"),
        });
    }
    let (left_name, left_rows, right_name, right_rows) = if domain_a < domain_b {
        (domain_a, rows_a, domain_b, rows_b)
    } else {
        (domain_b, rows_b, domain_a, rows_a)
    };
    let left = calibrate_matrix(left_rows, 0)?;
    let right = calibrate_matrix(right_rows, 0)?;
    let mut centroid = [0.0f32; DIM];
    let mut norm_sq = 0.0f64;
    let mut diff = [0.0f64; DIM];
    for ((slot, left_mu), right_mu) in diff.iter_mut().zip(left.mu).zip(right.mu) {
        let value = left_mu - right_mu;
        *slot = value;
        norm_sq += value * value;
    }
    if norm_sq > 0.0 {
        let inv_norm = 1.0 / norm_sq.sqrt();
        for (slot, value) in centroid.iter_mut().zip(diff) {
            *slot = (value * inv_norm) as f32;
        }
    }
    let (mask, ranked) = discriminative_mask(&left.lo, &left.hi, &right.lo, &right.hi);
    let keep_n = ranked.len();
    let quorum_k = pairwise_quorum(keep_n);
    let mut top_k = [0u16; MAX_TOPK];
    for (slot, dim) in top_k.iter_mut().zip(ranked.iter().copied()) {
        *slot = u16::try_from(dim).map_err(|_| CalibrationError {
            message: format!("discriminative dimension {dim} does not fit in u16"),
        })?;
    }
    if keep_n < usize::from(DEFAULT_QUORUM_K) {
        let pad = ranked.first().copied().unwrap_or(0);
        let pad = u16::try_from(pad).unwrap_or(0);
        for slot in top_k
            .iter_mut()
            .take(usize::from(DEFAULT_QUORUM_K))
            .skip(keep_n)
        {
            *slot = pad;
        }
    }
    Ok(DomainHypercubeLock::from_spec(LockSpec {
        domain_id: format!("{left_name}_{right_name}"),
        centroid: aligned(&centroid)?,
        lo: aligned(&left.lo)?,
        hi: aligned(&left.hi)?,
        epsilon: 0.0,
        noise_mask: mask,
        top_k_indices: top_k,
        top_k_len: u16::try_from(keep_n.min(usize::from(DEFAULT_QUORUM_K))).unwrap_or(0),
        quorum_k,
        l1_cosine_threshold: CANONICAL_COSINE,
        l2_clause_threshold: CANONICAL_COSINE,
        polarity: 0,
        domain_version: 1,
    }))
}

#[derive(Clone, Debug)]
pub struct CanonicalCatalog {
    pub locks: Vec<DomainHypercubeLock>,
    pub manifests: Vec<CorpusManifest>,
}

/// Eleven single-domain locks plus the 55 unordered pairwise locks.
pub fn assemble_canonical_locks(
    domains: &[(&str, &[f32])],
) -> Result<Vec<DomainHypercubeLock>, CalibrationError> {
    Ok(assemble_canonical_catalog(domains)?.locks)
}

/// Locks plus the corpus manifest each row was calibrated from.
pub fn assemble_canonical_catalog(
    domains: &[(&str, &[f32])],
) -> Result<CanonicalCatalog, CalibrationError> {
    if domains.len() != CANONICAL_DOMAINS.len() {
        return Err(CalibrationError {
            message: format!(
                "expected {} canonical domains, got {}",
                CANONICAL_DOMAINS.len(),
                domains.len()
            ),
        });
    }
    let mut rows: [Option<&[f32]>; 11] = [None; 11];
    for (name, matrix) in domains {
        let Some(index) = CANONICAL_DOMAINS.iter().position(|item| item == name) else {
            return Err(CalibrationError {
                message: format!("unknown canonical domain '{name}'"),
            });
        };
        if rows[index].is_some() {
            return Err(CalibrationError {
                message: format!("duplicate canonical domain '{name}'"),
            });
        }
        rows[index] = Some(*matrix);
    }
    let mut calibrated = Vec::with_capacity(CANONICAL_DOMAINS.len());
    for (index, name) in CANONICAL_DOMAINS.iter().enumerate() {
        let matrix = rows[index].ok_or_else(|| CalibrationError {
            message: format!("missing canonical domain '{name}'"),
        })?;
        calibrated.push(calibrate_matrix(matrix, 0)?);
    }
    let mut locks = Vec::with_capacity(66);
    let mut manifests = Vec::with_capacity(66);
    for (index, name) in CANONICAL_DOMAINS.iter().enumerate() {
        manifests.push(calibrated[index].manifest());
        locks.push(domain_lock(name, &calibrated[index])?);
    }
    for left in 0..CANONICAL_DOMAINS.len() {
        for right in (left + 1)..CANONICAL_DOMAINS.len() {
            let (name_a, name_b, rows_a, rows_b) = ordered_pair(left, right, &rows);
            manifests.push(manifest_from_matrices(&[rows_a, rows_b])?);
            locks.push(calibrate_pairwise_lock(name_a, name_b, rows_a, rows_b)?);
        }
    }
    Ok(CanonicalCatalog { locks, manifests })
}

fn ordered_pair<'a>(
    left: usize,
    right: usize,
    rows: &[Option<&'a [f32]>; 11],
) -> (&'static str, &'static str, &'a [f32], &'a [f32]) {
    let name_left = CANONICAL_DOMAINS[left];
    let name_right = CANONICAL_DOMAINS[right];
    let rows_left = rows[left].unwrap_or(&[]);
    let rows_right = rows[right].unwrap_or(&[]);
    if name_left < name_right {
        (name_left, name_right, rows_left, rows_right)
    } else {
        (name_right, name_left, rows_right, rows_left)
    }
}

fn domain_lock(
    name: &str,
    calibration: &Calibration,
) -> Result<DomainHypercubeLock, CalibrationError> {
    let mut top_k = [0u16; MAX_TOPK];
    top_k[..usize::from(DEFAULT_QUORUM_K)].copy_from_slice(&calibration.top_k);
    Ok(DomainHypercubeLock::from_spec(LockSpec {
        domain_id: name.to_string(),
        centroid: aligned(&calibration.centroid)?,
        lo: aligned(&calibration.lo)?,
        hi: aligned(&calibration.hi)?,
        epsilon: 0.0,
        noise_mask: calibration.noise_mask,
        top_k_indices: top_k,
        top_k_len: calibration.top_k_len,
        quorum_k: DEFAULT_QUORUM_K,
        l1_cosine_threshold: CANONICAL_COSINE,
        l2_clause_threshold: CANONICAL_COSINE,
        polarity: 0,
        domain_version: 1,
    }))
}

fn require_canonical(name: &str) -> Result<(), CalibrationError> {
    if is_canonical_domain(name) {
        Ok(())
    } else {
        Err(CalibrationError {
            message: format!("unknown canonical domain '{name}'"),
        })
    }
}

fn discriminative_mask(
    lo_a: &[f32; DIM],
    hi_a: &[f32; DIM],
    lo_b: &[f32; DIM],
    hi_b: &[f32; DIM],
) -> (NoiseBitmask1024, Vec<usize>) {
    let base = NoiseBitmask1024::new_bge_m3_default();
    let mut ranked = Vec::new();
    for dim in 0..DIM {
        if !base.is_active(dim) {
            continue;
        }
        let separation = coordinate_separation(lo_a[dim], hi_a[dim], lo_b[dim], hi_b[dim]);
        if separation > 0.0 {
            ranked.push((separation, dim));
        }
    }
    ranked.sort_by(|left, right| {
        right
            .0
            .total_cmp(&left.0)
            .then_with(|| left.1.cmp(&right.1))
    });
    let keep_n = if ranked.len() >= usize::from(DEFAULT_QUORUM_K) {
        usize::from(DEFAULT_QUORUM_K)
    } else {
        ranked.len()
    };
    ranked.truncate(keep_n);
    let mut mask = NoiseBitmask1024 {
        words: [0; NOISE_MASK_WORDS],
    };
    for (_, dim) in &ranked {
        let word = dim >> 6;
        let bit = dim & 63;
        mask.words[word] |= 1u64 << bit;
    }
    let dims: Vec<usize> = ranked.into_iter().map(|(_, dim)| dim).collect();
    (mask, dims)
}

fn pairwise_quorum(active: usize) -> u16 {
    if active == 0 {
        return 1;
    }
    if active >= usize::from(DEFAULT_QUORUM_K) {
        return DEFAULT_QUORUM_K;
    }
    let scaled = active.div_ceil(10);
    u16::try_from(scaled.max(1).min(active)).unwrap_or(1)
}

fn coordinate_separation(lo_a: f32, hi_a: f32, lo_b: f32, hi_b: f32) -> f64 {
    let left = f64::from(lo_a) - f64::from(hi_b);
    let right = f64::from(lo_b) - f64::from(hi_a);
    left.max(right).max(0.0)
}

fn aligned(values: &[f32; DIM]) -> Result<AlignedVec1024, CalibrationError> {
    AlignedVec1024::from_slice(values).map_err(|err| CalibrationError {
        message: err.to_string(),
    })
}
