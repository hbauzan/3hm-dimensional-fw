//! LanceDB persistence for domain hypercubes.

mod calibration;
mod lance_store;
mod mem_registry;
mod registry;
mod schema;
mod validate;

pub use calibration::{
    assemble_canonical_catalog, assemble_canonical_locks, calibrate_matrix,
    calibrate_noise_bitmask, calibrate_pairwise_lock, is_canonical_domain, manifest_from_matrices,
    pair_lock_sides, read_f32_matrix, top_k_indices, Calibration, CalibrationError,
    CanonicalCatalog, CorpusManifest, CANONICAL_DOMAINS,
};
pub use lance_store::{
    load_registry, load_registry_table, write_calibration, write_locks, write_locks_with_manifests,
    IngestSpec,
};
pub use mem_registry::MemoryRegistry;
pub use registry::{
    record_batch_from_calibration, record_batch_from_locks, DomainRegistry, HotRegistry,
    RegistryError,
};
pub use schema::{domain_hypercube_arrow_schema, TABLE_NAME};
pub use sf_kernels::DIM;
pub use validate::{load_validated_vec1024, LoadError, UNALIGNED_ARROW_BUFFER_LOADS};
