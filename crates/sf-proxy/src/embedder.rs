//! Embedder seam. Slice 1 ships the mock. TEI adapters land in Slice 4.

use std::collections::HashMap;

use async_trait::async_trait;
use sf_kernels::{AlignedVec1024, DomainHypercubeLock, DIM};

const RAW_F64_FAIL_CLOSED: &str =
    "fail-closed: fhv1 raw float64 evaluation requires TeiHttpEmbedder (SF_EMBEDDER=http)";

const SPECTRAL_MARKER: &str = "permutation_noise";
const SPECTRAL_IN_BOX_VOTES: usize = 75;
const OUTSIDE_MARGIN: f32 = 1.0e-3;

#[async_trait]
pub trait BatchEmbedderClient: Send + Sync {
    async fn embed_batch_f32(&self, texts: &[&str]) -> Result<Vec<AlignedVec1024>, String>;

    /// Domain-aware batch. The default ignores `domain_id` and calls [`Self::embed_batch_f32`].
    async fn embed_batch_for_domain(
        &self,
        domain_id: Option<&str>,
        texts: &[&str],
    ) -> Result<Vec<AlignedVec1024>, String> {
        let _ = domain_id;
        self.embed_batch_f32(texts).await
    }

    /// Synthetic centroids are not bge-m3 points. Differential locks calibrated on real
    /// embeddings false-breach every mock vector.
    fn is_mock(&self) -> bool {
        false
    }

    /// Lossless binary64 batch. The default fails closed; only `TeiHttpEmbedder` preserves raw `f64`.
    async fn embed_batch_raw_f64(
        &self,
        texts: &[&str],
        normalize: bool,
    ) -> Result<Vec<[f64; DIM]>, String> {
        let _ = (texts, normalize);
        Err(RAW_F64_FAIL_CLOSED.to_string())
    }
}

/// Synthetic embedder.
///
/// The exact token `BREACH` maps to `breach_vector`.
///
/// [`BatchEmbedderClient::embed_batch_for_domain`] returns the centroid stored for a known
/// `domain_id`. A missing id, an unknown id, and the wildcard `*` fall back to `pass_vector`,
/// the configured default-domain centroid. Lookup does not panic and does not substitute a
/// zero vector while `pass_vector` is set. An empty `centroids` map keeps that fallback for
/// every non-`BREACH` text, matching [`BatchEmbedderClient::embed_batch_f32`].
pub struct MockBatchEmbedder {
    pub pass_vector: AlignedVec1024,
    pub breach_vector: AlignedVec1024,
    /// Known domain centroids. Empty means every non-`BREACH` text uses `pass_vector`.
    pub centroids: HashMap<String, AlignedVec1024>,
}

#[async_trait]
impl BatchEmbedderClient for MockBatchEmbedder {
    fn is_mock(&self) -> bool {
        true
    }

    async fn embed_batch_f32(&self, texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
        self.embed_batch_for_domain(None, texts).await
    }

    async fn embed_batch_for_domain(
        &self,
        domain_id: Option<&str>,
        texts: &[&str],
    ) -> Result<Vec<AlignedVec1024>, String> {
        let centroid = match domain_id {
            Some(id) if id != "*" => self.centroids.get(id).copied().unwrap_or(self.pass_vector),
            _ => self.pass_vector,
        };
        Ok(texts
            .iter()
            .map(|text| {
                if *text == "BREACH" {
                    self.breach_vector
                } else {
                    centroid
                }
            })
            .collect())
    }

    async fn embed_batch_raw_f64(
        &self,
        texts: &[&str],
        normalize: bool,
    ) -> Result<Vec<[f64; DIM]>, String> {
        let _ = (self, texts, normalize);
        Err(RAW_F64_FAIL_CLOSED.to_string())
    }
}

/// Case-insensitive fixture token. The playground's Spectral L3 chip carries it.
pub fn contains_permutation_noise(text: &str) -> bool {
    let needle = SPECTRAL_MARKER.as_bytes();
    text.as_bytes()
        .windows(needle.len())
        .any(|window| window.eq_ignore_ascii_case(needle))
}

/// Starts at the centroid and steps the nearest bound on every active coordinate past the
/// 75th in-box vote. Inactive coordinates stay on the centroid so cosine does not collapse.
pub fn project_spectral_drift(lock: &DomainHypercubeLock) -> AlignedVec1024 {
    let mut vector = lock.centroid;
    let mut votes = 0usize;
    for dim in 0..DIM {
        if !lock.noise_mask.is_active(dim) {
            continue;
        }
        if votes < SPECTRAL_IN_BOX_VOTES {
            vector.data[dim] = inside_value(
                lock.lo_dilated.data[dim],
                lock.hi_dilated.data[dim],
                lock.centroid.data[dim],
            );
            votes += 1;
        } else {
            vector.data[dim] = nearest_outside(
                lock.centroid.data[dim],
                lock.lo_dilated.data[dim],
                lock.hi_dilated.data[dim],
            );
        }
    }
    vector
}

fn inside_value(lo: f32, hi: f32, preferred: f32) -> f32 {
    let (lo, hi) = if lo <= hi { (lo, hi) } else { (hi, lo) };
    if preferred >= lo && preferred <= hi {
        preferred
    } else {
        lo.midpoint(hi)
    }
}

fn nearest_outside(value: f32, lo: f32, hi: f32) -> f32 {
    let (lo, hi) = if lo <= hi { (lo, hi) } else { (hi, lo) };
    let below = lo - OUTSIDE_MARGIN;
    let above = hi + OUTSIDE_MARGIN;
    if value <= lo {
        return if below.is_finite() {
            below
        } else {
            lo.next_down()
        };
    }
    if value >= hi {
        return if above.is_finite() {
            above
        } else {
            hi.next_up()
        };
    }
    if (value - lo) <= (hi - value) {
        if below.is_finite() {
            below
        } else {
            lo.next_down()
        }
    } else if above.is_finite() {
        above
    } else {
        hi.next_up()
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use sf_kernels::{AlignedVec1024, DIM};

    use super::{BatchEmbedderClient, MockBatchEmbedder};

    fn spike(index: usize) -> AlignedVec1024 {
        let mut vector = AlignedVec1024::zeros();
        vector.data[index] = 1.0;
        vector
    }

    fn bits(vector: &AlignedVec1024) -> [u32; DIM] {
        vector.data.map(f32::to_bits)
    }

    #[tokio::test]
    async fn mock_embedder_resolves_requested_domain_centroid() {
        let python = spike(0);
        let receta = spike(1);
        let breach = spike(2);
        assert_ne!(bits(&python), bits(&receta));

        let embedder = MockBatchEmbedder {
            pass_vector: python,
            breach_vector: breach,
            centroids: HashMap::from([
                ("python".to_string(), python),
                ("receta".to_string(), receta),
            ]),
        };
        let client: &dyn BatchEmbedderClient = &embedder;

        let receta_batch = client
            .embed_batch_for_domain(Some("receta"), &["clause-a", "clause-b"])
            .await
            .expect("receta batch");
        assert_eq!(bits(&receta_batch[0]), bits(&receta));
        assert_eq!(bits(&receta_batch[1]), bits(&receta));

        let unknown = client
            .embed_batch_for_domain(Some("unknown-domain"), &["clause-a"])
            .await
            .expect("unknown domain");
        assert_eq!(bits(&unknown[0]), bits(&python));

        let missing = client
            .embed_batch_for_domain(None, &["clause-a"])
            .await
            .expect("missing domain");
        assert_eq!(bits(&missing[0]), bits(&python));

        let wildcard = client
            .embed_batch_for_domain(Some("*"), &["clause-a"])
            .await
            .expect("wildcard");
        assert_eq!(bits(&wildcard[0]), bits(&python));

        let breach_hit = client
            .embed_batch_for_domain(Some("receta"), &["BREACH"])
            .await
            .expect("breach token");
        assert_eq!(bits(&breach_hit[0]), bits(&breach));

        let plain = client
            .embed_batch_f32(&["clause-a", "BREACH"])
            .await
            .expect("domainless batch");
        assert_eq!(bits(&plain[0]), bits(&python));
        assert_eq!(bits(&plain[1]), bits(&breach));

        let empty = MockBatchEmbedder {
            pass_vector: python,
            breach_vector: breach,
            centroids: HashMap::new(),
        };
        let empty_client: &dyn BatchEmbedderClient = &empty;
        let empty_domain = empty_client
            .embed_batch_for_domain(Some("receta"), &["clause-a"])
            .await
            .expect("empty map");
        assert_eq!(bits(&empty_domain[0]), bits(&python));
        let empty_batch = empty_client
            .embed_batch_f32(&["clause-a", "BREACH"])
            .await
            .expect("empty map batch");
        assert_eq!(bits(&empty_batch[0]), bits(&python));
        assert_eq!(bits(&empty_batch[1]), bits(&breach));
    }

    #[tokio::test]
    async fn mock_raw_f64_fails_closed() {
        let embedder = MockBatchEmbedder {
            pass_vector: AlignedVec1024::zeros(),
            breach_vector: AlignedVec1024::zeros(),
            centroids: HashMap::new(),
        };
        let err = embedder
            .embed_batch_raw_f64(&["clause"], false)
            .await
            .expect_err("mock raw");
        assert_eq!(
            err,
            "fail-closed: fhv1 raw float64 evaluation requires TeiHttpEmbedder (SF_EMBEDDER=http)"
        );
        let normalized = embedder
            .embed_batch_raw_f64(&["clause"], true)
            .await
            .expect_err("mock raw normalized");
        assert_eq!(normalized, err);
    }
}
