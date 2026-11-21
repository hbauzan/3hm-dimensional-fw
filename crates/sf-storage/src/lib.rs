//! LanceDB persistence for domain hypercubes.

mod calibration;
mod fhv1_calibration;
mod fhv1_export;
mod fhv1_schema;
mod fhv1_store;
mod lance_store;
mod mem_registry;
mod registry;
mod schema;
mod validate;

pub use fhv1_calibration::{
    assemble_calibration, profile_id_for, trace_summaries_json, Fhv1AuditTrace,
    Fhv1AuditTraceSummary, Fhv1BenchmarkRun, Fhv1CalibrationRequest, Fhv1CalibrationSample,
    Fhv1ProfileRecord, Fhv1RawSample, Fhv1StorageError, Fhv1TraceChunkDrilldown,
    Fhv1TraceDrilldown, Fhv1TracePage, Fhv1TraceQuery,
};
pub use fhv1_export::{
    export_csv, export_parquet, export_xlsx, Fhv1XlsxPayload, FHV1_XLSX_MAX_ROWS,
};
pub use fhv1_schema::{
    fhv1_audit_trace_schema, fhv1_benchmark_run_schema, fhv1_calibration_sample_schema,
    fhv1_profile_schema, FHV1_AUDIT_TRACES_TABLE, FHV1_BENCHMARK_RUNS_TABLE,
    FHV1_CALIBRATION_SAMPLES_TABLE, FHV1_PROFILES_TABLE,
};
pub use fhv1_store::Fhv1Store;

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
