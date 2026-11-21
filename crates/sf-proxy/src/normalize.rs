//! Boundary check for embedder outputs. The norm is accumulated in `f64`.

use sf_kernels::{AlignedVec1024, DIM};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NormalizeError {
    BadLen { len: usize },
    NonFinite { index: usize },
    ZeroNorm,
}

impl std::fmt::Display for NormalizeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::BadLen { len } => write!(f, "expected {DIM} floats, got {len}"),
            Self::NonFinite { index } => write!(f, "non-finite embedding coordinate {index}"),
            Self::ZeroNorm => write!(f, "embedding norm is zero"),
        }
    }
}

impl std::error::Error for NormalizeError {}

/// Accept a finite 1024-d binary64 row. No L2 normalization and no binary32 cast.
pub fn validate_raw_f64_slice(src: &[f64]) -> Result<[f64; DIM], NormalizeError> {
    if src.len() != DIM {
        return Err(NormalizeError::BadLen { len: src.len() });
    }
    for (index, value) in src.iter().copied().enumerate() {
        if !value.is_finite() {
            return Err(NormalizeError::NonFinite { index });
        }
    }
    let mut out = [0.0; DIM];
    out.copy_from_slice(src);
    Ok(out)
}

pub fn validate_and_normalize_f32_slice(src: &[f32]) -> Result<AlignedVec1024, NormalizeError> {
    if src.len() != DIM {
        return Err(NormalizeError::BadLen { len: src.len() });
    }
    let mut norm_sq = 0.0f64;
    for (index, value) in src.iter().copied().enumerate() {
        if !value.is_finite() {
            return Err(NormalizeError::NonFinite { index });
        }
        let widened = f64::from(value);
        norm_sq += widened * widened;
    }
    if norm_sq == 0.0 {
        return Err(NormalizeError::ZeroNorm);
    }
    let inv = 1.0 / norm_sq.sqrt();
    let mut out = AlignedVec1024::zeros();
    for (index, value) in src.iter().copied().enumerate() {
        out.data[index] = (f64::from(value) * inv) as f32;
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::validate_raw_f64_slice;
    use sf_kernels::DIM;

    #[test]
    fn raw_f64_keeps_bits_and_rejects_bad_rows() {
        let mut row = [0.1f64; DIM];
        row[3] = f64::from_bits(0.1f64.to_bits() + 1);
        let out = validate_raw_f64_slice(&row).expect("raw");
        assert_eq!(out[3].to_bits(), row[3].to_bits());
        assert_ne!(out[3].to_bits(), f64::from(row[3] as f32).to_bits());
        assert!(validate_raw_f64_slice(&[0.0; 4]).is_err());
        let mut poisoned = [0.0; DIM];
        poisoned[2] = f64::NAN;
        assert!(validate_raw_f64_slice(&poisoned).is_err());
    }
}
