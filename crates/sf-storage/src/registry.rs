//! RecordBatch ↔ domain lock, plus the lock-free hot registry.

use crate::schema::domain_hypercube_arrow_schema;
use crate::validate::{load_validated_vec1024, LoadError};
use crate::{Calibration, CorpusManifest};
use arc_swap::ArcSwap;
use lancedb::arrow::arrow_array::{
    Array, FixedSizeBinaryArray, FixedSizeListArray, Float32Array, RecordBatch, StringArray,
    UInt16Array, UInt64Array, UInt8Array,
};
use lancedb::arrow::arrow_buffer::Buffer;
use lancedb::arrow::arrow_schema::Field;
use sf_kernels::{
    AlignedVec1024, DomainHypercubeLock, LockSpec, NoiseBitmask1024, DEFAULT_QUORUM_K, DIM,
    MAX_TOPK, NOISE_MASK_WORDS,
};
use std::collections::HashMap;
use std::sync::Arc;

#[derive(Debug)]
pub struct RegistryError {
    pub message: String,
}

impl std::fmt::Display for RegistryError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.message)
    }
}

impl std::error::Error for RegistryError {}

impl From<LoadError> for RegistryError {
    fn from(err: LoadError) -> Self {
        Self {
            message: err.to_string(),
        }
    }
}

#[derive(Clone, Debug)]
pub struct DomainRegistry {
    pub locks_by_id: HashMap<String, Arc<DomainHypercubeLock>>,
    pub all_locks: Vec<Arc<DomainHypercubeLock>>,
    pub manifests: HashMap<String, CorpusManifest>,
}

impl DomainRegistry {
    pub fn from_record_batches(batches: Vec<RecordBatch>) -> Result<Self, RegistryError> {
        let mut locks_by_id = HashMap::new();
        let mut all_locks = Vec::new();
        let mut manifests = HashMap::new();
        for batch in batches {
            append_batch(&batch, &mut locks_by_id, &mut all_locks, &mut manifests)?;
        }
        Ok(Self {
            locks_by_id,
            all_locks,
            manifests,
        })
    }

    pub fn from_locks(locks: impl IntoIterator<Item = DomainHypercubeLock>) -> Self {
        let mut locks_by_id = HashMap::new();
        let mut all_locks = Vec::new();
        let mut manifests = HashMap::new();
        for lock in locks {
            let arc = Arc::new(lock);
            manifests.insert(arc.domain_id.clone(), CorpusManifest::UNPROVIDED);
            locks_by_id.insert(arc.domain_id.clone(), Arc::clone(&arc));
            all_locks.push(arc);
        }
        Self {
            locks_by_id,
            all_locks,
            manifests,
        }
    }

    pub fn get(&self, domain_id: &str) -> Option<Arc<DomainHypercubeLock>> {
        self.locks_by_id.get(domain_id).cloned()
    }

    pub fn locks(&self) -> &[Arc<DomainHypercubeLock>] {
        &self.all_locks
    }

    pub fn is_empty(&self) -> bool {
        self.all_locks.is_empty()
    }

    pub fn len(&self) -> usize {
        self.all_locks.len()
    }

    pub fn manifest(&self, domain_id: &str) -> Option<CorpusManifest> {
        self.manifests.get(domain_id).copied()
    }
}

pub struct HotRegistry {
    inner: ArcSwap<DomainRegistry>,
}

impl HotRegistry {
    pub fn new(initial: Arc<DomainRegistry>) -> Self {
        Self {
            inner: ArcSwap::from(initial),
        }
    }

    pub fn from_domain_registry(registry: DomainRegistry) -> Self {
        Self::new(Arc::new(registry))
    }

    pub fn from_locks(locks: impl IntoIterator<Item = DomainHypercubeLock>) -> Self {
        Self::new(Arc::new(DomainRegistry::from_locks(locks)))
    }

    pub async fn load_from_lancedb(uri: &str, table_name: &str) -> Result<Self, RegistryError> {
        let registry = crate::lance_store::load_registry_table(uri, table_name).await?;
        Ok(Self::new(Arc::new(registry)))
    }

    pub async fn reload_from_lancedb(
        &self,
        uri: &str,
        table_name: &str,
    ) -> Result<(), RegistryError> {
        let registry = crate::lance_store::load_registry_table(uri, table_name).await?;
        self.store(Arc::new(registry));
        Ok(())
    }

    pub fn load(&self) -> arc_swap::Guard<Arc<DomainRegistry>> {
        self.inner.load()
    }

    pub fn store(&self, next: Arc<DomainRegistry>) {
        self.inner.store(next);
    }

    pub fn get(&self, domain_id: &str) -> Option<Arc<DomainHypercubeLock>> {
        self.load().get(domain_id)
    }

    pub fn locks(&self) -> Vec<Arc<DomainHypercubeLock>> {
        self.load().locks().to_vec()
    }

    pub fn manifest(&self, domain_id: &str) -> Option<CorpusManifest> {
        self.load().manifest(domain_id)
    }

    /// Pairwise locks whose id names `domain_id` on one side. Empty unless `domain_id` is canonical.
    pub fn pairwise_locks_for(&self, domain_id: &str) -> Vec<Arc<DomainHypercubeLock>> {
        if !crate::is_canonical_domain(domain_id) {
            return Vec::new();
        }
        let snapshot = self.load();
        let mut found = Vec::new();
        for lock in snapshot.locks() {
            let Some((left, right)) = crate::pair_lock_sides(&lock.domain_id) else {
                continue;
            };
            if left == domain_id || right == domain_id {
                found.push(Arc::clone(lock));
            }
        }
        found.sort_by(|left, right| left.domain_id.cmp(&right.domain_id));
        found
    }
}

pub struct LockMeta<'a> {
    pub domain_id: &'a str,
    pub version: u64,
    pub polarity: u8,
    pub l1: f32,
    pub l2: f32,
    pub epsilon: f32,
    pub quorum_k: u16,
}

pub fn record_batch_from_calibration(
    meta: LockMeta<'_>,
    calibration: &Calibration,
) -> Result<RecordBatch, RegistryError> {
    let schema = domain_hypercube_arrow_schema();
    let centroid = list_f32(&calibration.centroid)?;
    let lo = list_f32(&calibration.lo)?;
    let hi = list_f32(&calibration.hi)?;
    let top_k = list_u16(&calibration.top_k)?;
    let mask = mask_array(&calibration.noise_mask)?;
    let digest = FixedSizeBinaryArray::try_new(32, Buffer::from(calibration.sha256.to_vec()), None)
        .map_err(|err| RegistryError {
            message: err.to_string(),
        })?;
    RecordBatch::try_new(
        schema,
        vec![
            Arc::new(StringArray::from(vec![meta.domain_id.to_string()])),
            Arc::new(UInt64Array::from(vec![meta.version])),
            Arc::new(UInt8Array::from(vec![meta.polarity])),
            Arc::new(Float32Array::from(vec![meta.l1])),
            Arc::new(Float32Array::from(vec![meta.l2])),
            Arc::new(Float32Array::from(vec![meta.epsilon])),
            Arc::new(UInt16Array::from(vec![meta.quorum_k])),
            Arc::new(centroid),
            Arc::new(lo),
            Arc::new(hi),
            Arc::new(top_k),
            Arc::new(UInt16Array::from(vec![bounded_top_k_len(
                calibration.top_k_len,
                DEFAULT_QUORUM_K,
            )])),
            Arc::new(mask),
            Arc::new(UInt64Array::from(vec![calibration.rows])),
            Arc::new(digest),
        ],
    )
    .map_err(|err| RegistryError {
        message: err.to_string(),
    })
}

pub fn record_batch_from_locks<'a>(
    locks: impl IntoIterator<Item = &'a DomainHypercubeLock>,
    manifests: impl IntoIterator<Item = &'a CorpusManifest>,
) -> Result<RecordBatch, RegistryError> {
    let schema = domain_hypercube_arrow_schema();
    let locks: Vec<&'a DomainHypercubeLock> = locks.into_iter().collect();
    let manifests: Vec<&'a CorpusManifest> = manifests.into_iter().collect();
    if locks.len() != manifests.len() {
        return Err(RegistryError {
            message: format!(
                "lock/manifest length mismatch: {} locks and {} manifests",
                locks.len(),
                manifests.len()
            ),
        });
    }
    let n = locks.len();

    let mut domain_ids = Vec::with_capacity(n);
    let mut versions = Vec::with_capacity(n);
    let mut polarities = Vec::with_capacity(n);
    let mut l1_vec = Vec::with_capacity(n);
    let mut l2_vec = Vec::with_capacity(n);
    let mut eps_vec = Vec::with_capacity(n);
    let mut quorum_vec = Vec::with_capacity(n);
    let mut centroid_floats = Vec::with_capacity(n * DIM);
    let mut lo_floats = Vec::with_capacity(n * DIM);
    let mut hi_floats = Vec::with_capacity(n * DIM);
    let mut top_k_u16 = Vec::with_capacity(n * usize::from(DEFAULT_QUORUM_K));
    let mut top_k_lens = Vec::with_capacity(n);
    let mut mask_bytes = Vec::with_capacity(n * 128);
    let mut doc_counts = Vec::with_capacity(n);
    let mut digest_bytes = Vec::with_capacity(n * 32);

    for (lock, manifest) in locks.into_iter().zip(manifests) {
        domain_ids.push(lock.domain_id.clone());
        versions.push(lock.domain_version);
        polarities.push(lock.polarity);
        l1_vec.push(lock.l1_cosine_threshold);
        l2_vec.push(lock.l2_clause_threshold);
        eps_vec.push(lock.epsilon);
        quorum_vec.push(lock.quorum_k);
        centroid_floats.extend_from_slice(&lock.centroid.data);
        for dim in 0..DIM {
            lo_floats.push(lock.lo_dilated.data[dim] + lock.epsilon);
            hi_floats.push(lock.hi_dilated.data[dim] - lock.epsilon);
        }
        let k = usize::from(DEFAULT_QUORUM_K);
        top_k_u16.extend_from_slice(&lock.top_k_indices[..k]);
        top_k_lens.push(bounded_top_k_len(lock.top_k_len, DEFAULT_QUORUM_K));
        for word in lock.noise_mask.words {
            mask_bytes.extend_from_slice(&word.to_le_bytes());
        }
        doc_counts.push(manifest.doc_count);
        digest_bytes.extend_from_slice(&manifest.sha256);
    }

    let centroid_child = Float32Array::from(centroid_floats);
    let centroid_arr = FixedSizeListArray::try_new(
        Arc::new(Field::new(
            "item",
            lancedb::arrow::arrow_schema::DataType::Float32,
            false,
        )),
        DIM as i32,
        Arc::new(centroid_child),
        None,
    )
    .map_err(|err| RegistryError {
        message: err.to_string(),
    })?;

    let lo_child = Float32Array::from(lo_floats);
    let lo_arr = FixedSizeListArray::try_new(
        Arc::new(Field::new(
            "item",
            lancedb::arrow::arrow_schema::DataType::Float32,
            false,
        )),
        DIM as i32,
        Arc::new(lo_child),
        None,
    )
    .map_err(|err| RegistryError {
        message: err.to_string(),
    })?;

    let hi_child = Float32Array::from(hi_floats);
    let hi_arr = FixedSizeListArray::try_new(
        Arc::new(Field::new(
            "item",
            lancedb::arrow::arrow_schema::DataType::Float32,
            false,
        )),
        DIM as i32,
        Arc::new(hi_child),
        None,
    )
    .map_err(|err| RegistryError {
        message: err.to_string(),
    })?;

    let topk_child = UInt16Array::from(top_k_u16);
    let topk_arr = FixedSizeListArray::try_new(
        Arc::new(Field::new(
            "item",
            lancedb::arrow::arrow_schema::DataType::UInt16,
            false,
        )),
        i32::from(DEFAULT_QUORUM_K),
        Arc::new(topk_child),
        None,
    )
    .map_err(|err| RegistryError {
        message: err.to_string(),
    })?;

    let mask_arr =
        FixedSizeBinaryArray::try_new(128, Buffer::from(mask_bytes), None).map_err(|err| {
            RegistryError {
                message: err.to_string(),
            }
        })?;
    let digest_arr =
        FixedSizeBinaryArray::try_new(32, Buffer::from(digest_bytes), None).map_err(|err| {
            RegistryError {
                message: err.to_string(),
            }
        })?;

    RecordBatch::try_new(
        schema,
        vec![
            Arc::new(StringArray::from(domain_ids)),
            Arc::new(UInt64Array::from(versions)),
            Arc::new(UInt8Array::from(polarities)),
            Arc::new(Float32Array::from(l1_vec)),
            Arc::new(Float32Array::from(l2_vec)),
            Arc::new(Float32Array::from(eps_vec)),
            Arc::new(UInt16Array::from(quorum_vec)),
            Arc::new(centroid_arr),
            Arc::new(lo_arr),
            Arc::new(hi_arr),
            Arc::new(topk_arr),
            Arc::new(UInt16Array::from(top_k_lens)),
            Arc::new(mask_arr),
            Arc::new(UInt64Array::from(doc_counts)),
            Arc::new(digest_arr),
        ],
    )
    .map_err(|err| RegistryError {
        message: err.to_string(),
    })
}

fn list_f32(values: &[f32; DIM]) -> Result<FixedSizeListArray, RegistryError> {
    let child = Float32Array::from(values.to_vec());
    FixedSizeListArray::try_new(
        Arc::new(Field::new(
            "item",
            lancedb::arrow::arrow_schema::DataType::Float32,
            false,
        )),
        DIM as i32,
        Arc::new(child),
        None,
    )
    .map_err(|err| RegistryError {
        message: err.to_string(),
    })
}

fn list_u16(values: &[u16; 103]) -> Result<FixedSizeListArray, RegistryError> {
    let child = UInt16Array::from(values.to_vec());
    FixedSizeListArray::try_new(
        Arc::new(Field::new(
            "item",
            lancedb::arrow::arrow_schema::DataType::UInt16,
            false,
        )),
        i32::from(DEFAULT_QUORUM_K),
        Arc::new(child),
        None,
    )
    .map_err(|err| RegistryError {
        message: err.to_string(),
    })
}

fn mask_array(mask: &NoiseBitmask1024) -> Result<FixedSizeBinaryArray, RegistryError> {
    let mut bytes = Vec::with_capacity(128);
    for word in mask.words {
        bytes.extend_from_slice(&word.to_le_bytes());
    }
    FixedSizeBinaryArray::try_new(128, Buffer::from(bytes), None).map_err(|err| RegistryError {
        message: err.to_string(),
    })
}

/// Declared Mode A length, capped by the in-memory slot array and the indices actually stored.
/// A shorter real length is kept. `DEFAULT_QUORUM_K` is only the FixedSizeList width, not a substitute.
fn bounded_top_k_len(declared: u16, index_width: u16) -> u16 {
    declared.min(MAX_TOPK as u16).min(index_width)
}

fn append_batch(
    batch: &RecordBatch,
    locks_by_id: &mut HashMap<String, Arc<DomainHypercubeLock>>,
    all_locks: &mut Vec<Arc<DomainHypercubeLock>>,
    manifests: &mut HashMap<String, CorpusManifest>,
) -> Result<(), RegistryError> {
    let domain_ids = col_string(batch, "domain_id")?;
    let versions = col_u64(batch, "version")?;
    let polarities = col_u8(batch, "polarity")?;
    let l1 = col_f32(batch, "l1_cosine_threshold")?;
    let l2 = col_f32(batch, "l2_clause_threshold")?;
    let epsilons = col_f32(batch, "epsilon")?;
    let quorums = col_u16(batch, "quorum_k")?;
    let centroids = col_fsl(batch, "centroid_vector")?;
    let los = col_fsl(batch, "lo_vector")?;
    let his = col_fsl(batch, "hi_vector")?;
    let topk = col_fsl(batch, "top_k_indices")?;
    let masks = col_bin(batch, "noise_mask")?;
    let doc_counts = col_u64(batch, "corpus_doc_count")?;
    let digests = col_bin(batch, "sha256_manifest")?;
    let centroid_vals = f32_child(centroids)?;
    let lo_vals = f32_child(los)?;
    let hi_vals = f32_child(his)?;
    let topk_vals = u16_child(topk)?;
    let stored_lengths = match batch.column_by_name("top_k_len") {
        Some(column) => Some(col_u16_array(column)?),
        None => None,
    };
    let index_width = u16::try_from(topk.value_length()).map_err(|_| RegistryError {
        message: format!(
            "top_k_indices width {} does not fit in u16",
            topk.value_length()
        ),
    })?;
    let width = usize::from(index_width);
    if width > MAX_TOPK {
        return Err(RegistryError {
            message: format!("top_k_indices width {width} exceeds MAX_TOPK {MAX_TOPK}"),
        });
    }

    for row in 0..batch.num_rows() {
        let centroid = row_f32(centroid_vals, row)?;
        let lo = row_f32(lo_vals, row)?;
        let hi = row_f32(hi_vals, row)?;
        let epsilon = epsilons.value(row);
        let mut words = [0u64; NOISE_MASK_WORDS];
        let mask_bytes = masks.value(row);
        if mask_bytes.len() != 128 {
            return Err(RegistryError {
                message: format!("noise_mask width {}", mask_bytes.len()),
            });
        }
        for (idx, word) in words.iter_mut().enumerate() {
            let start = idx * 8;
            let mut buf = [0u8; 8];
            buf.copy_from_slice(&mask_bytes[start..start + 8]);
            *word = u64::from_le_bytes(buf);
        }
        let mut top_k_indices = [0u16; MAX_TOPK];
        for (slot, index) in top_k_indices.iter_mut().take(width).enumerate() {
            *index = topk_vals.value(row * width + slot);
        }
        let declared = match stored_lengths {
            Some(values) => values.value(row),
            // Catalogs written before the column existed only have the fixed index list.
            None => index_width,
        };
        let top_k_len = bounded_top_k_len(declared, index_width);
        let digest = digests.value(row);
        if digest.len() != 32 {
            return Err(RegistryError {
                message: format!("sha256_manifest width {}", digest.len()),
            });
        }
        let mut sha256 = [0u8; 32];
        sha256.copy_from_slice(digest);
        let domain_id = domain_ids.value(row).to_string();
        manifests.insert(
            domain_id.clone(),
            CorpusManifest {
                doc_count: doc_counts.value(row),
                sha256,
            },
        );
        let lock = Arc::new(DomainHypercubeLock::from_spec(LockSpec {
            domain_id: domain_id.clone(),
            centroid,
            lo,
            hi,
            epsilon,
            noise_mask: NoiseBitmask1024 { words },
            top_k_indices,
            top_k_len,
            quorum_k: quorums.value(row),
            l1_cosine_threshold: l1.value(row),
            l2_clause_threshold: l2.value(row),
            polarity: polarities.value(row),
            domain_version: versions.value(row),
        }));
        locks_by_id.insert(domain_id, Arc::clone(&lock));
        all_locks.push(lock);
    }
    Ok(())
}

fn col_u16_array(column: &dyn Array) -> Result<&UInt16Array, RegistryError> {
    column
        .as_any()
        .downcast_ref::<UInt16Array>()
        .ok_or_else(|| RegistryError {
            message: "top_k_len is not UInt16".to_string(),
        })
}

fn row_f32(values: &Float32Array, row: usize) -> Result<AlignedVec1024, RegistryError> {
    let start = row * DIM;
    let slice = &values.values()[start..start + DIM];
    load_validated_vec1024(slice).map_err(RegistryError::from)
}

fn col_string<'a>(batch: &'a RecordBatch, name: &str) -> Result<&'a StringArray, RegistryError> {
    batch
        .column_by_name(name)
        .and_then(|col| col.as_any().downcast_ref::<StringArray>())
        .ok_or_else(|| RegistryError {
            message: format!("missing {name}"),
        })
}

fn col_u64<'a>(batch: &'a RecordBatch, name: &str) -> Result<&'a UInt64Array, RegistryError> {
    downcast(batch, name)
}

fn col_u8<'a>(batch: &'a RecordBatch, name: &str) -> Result<&'a UInt8Array, RegistryError> {
    downcast(batch, name)
}

fn col_u16<'a>(batch: &'a RecordBatch, name: &str) -> Result<&'a UInt16Array, RegistryError> {
    downcast(batch, name)
}

fn col_f32<'a>(batch: &'a RecordBatch, name: &str) -> Result<&'a Float32Array, RegistryError> {
    downcast(batch, name)
}

fn col_fsl<'a>(
    batch: &'a RecordBatch,
    name: &str,
) -> Result<&'a FixedSizeListArray, RegistryError> {
    downcast(batch, name)
}

fn col_bin<'a>(
    batch: &'a RecordBatch,
    name: &str,
) -> Result<&'a FixedSizeBinaryArray, RegistryError> {
    downcast(batch, name)
}

fn downcast<'a, T: 'static>(batch: &'a RecordBatch, name: &str) -> Result<&'a T, RegistryError> {
    batch
        .column_by_name(name)
        .and_then(|col| col.as_any().downcast_ref::<T>())
        .ok_or_else(|| RegistryError {
            message: format!("missing {name}"),
        })
}

fn f32_child(list: &FixedSizeListArray) -> Result<&Float32Array, RegistryError> {
    list.values()
        .as_any()
        .downcast_ref::<Float32Array>()
        .ok_or_else(|| RegistryError {
            message: "fixed-size list child is not Float32".to_string(),
        })
}

fn u16_child(list: &FixedSizeListArray) -> Result<&UInt16Array, RegistryError> {
    list.values()
        .as_any()
        .downcast_ref::<UInt16Array>()
        .ok_or_else(|| RegistryError {
            message: "fixed-size list child is not UInt16".to_string(),
        })
}
