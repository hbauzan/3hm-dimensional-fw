//! LanceDB write and read of the domain-hypercube table.

use crate::registry::{
    record_batch_from_calibration, record_batch_from_locks, DomainRegistry, LockMeta, RegistryError,
};
use crate::schema::TABLE_NAME;
use crate::{Calibration, CorpusManifest};
use futures_util::TryStreamExt;
use lancedb::arrow::arrow_array::RecordBatch;
use lancedb::query::{ExecutableQuery, QueryBase};
use sf_kernels::DomainHypercubeLock;

pub struct IngestSpec<'a> {
    pub uri: &'a str,
    pub domain_id: &'a str,
    pub version: u64,
    pub polarity: u8,
    pub l1: f32,
    pub l2: f32,
    pub epsilon: f32,
    pub quorum_k: u16,
    pub calibration: &'a Calibration,
}

pub async fn write_calibration(spec: IngestSpec<'_>) -> Result<(), RegistryError> {
    let batch = record_batch_from_calibration(
        LockMeta {
            domain_id: spec.domain_id,
            version: spec.version,
            polarity: spec.polarity,
            l1: spec.l1,
            l2: spec.l2,
            epsilon: spec.epsilon,
            quorum_k: spec.quorum_k,
        },
        spec.calibration,
    )?;
    let conn = lancedb::connect(spec.uri).execute().await.map_err(err)?;
    conn.create_table(TABLE_NAME, batch)
        .mode(lancedb::database::CreateTableMode::Overwrite)
        .execute()
        .await
        .map_err(err)?;
    Ok(())
}

pub async fn write_locks(
    uri: &str,
    table_name: &str,
    locks: &[DomainHypercubeLock],
) -> Result<(), RegistryError> {
    let manifests = vec![CorpusManifest::UNPROVIDED; locks.len()];
    write_locks_with_manifests(uri, table_name, locks, &manifests).await
}

pub async fn write_locks_with_manifests(
    uri: &str,
    table_name: &str,
    locks: &[DomainHypercubeLock],
    manifests: &[CorpusManifest],
) -> Result<(), RegistryError> {
    let batch = record_batch_from_locks(locks, manifests)?;
    let conn = lancedb::connect(uri).execute().await.map_err(err)?;
    conn.create_table(table_name, batch)
        .mode(lancedb::database::CreateTableMode::Overwrite)
        .execute()
        .await
        .map_err(err)?;
    Ok(())
}

pub async fn load_registry(uri: &str) -> Result<DomainRegistry, RegistryError> {
    load_registry_table(uri, TABLE_NAME).await
}

pub async fn load_registry_table(
    uri: &str,
    table_name: &str,
) -> Result<DomainRegistry, RegistryError> {
    let conn = lancedb::connect(uri).execute().await.map_err(err)?;
    let table = conn.open_table(table_name).execute().await.map_err(err)?;
    let stream = table
        .query()
        .limit(1_000_000)
        .execute()
        .await
        .map_err(err)?;
    let batches: Vec<RecordBatch> = stream.try_collect().await.map_err(err)?;
    DomainRegistry::from_record_batches(batches)
}

fn err(error: impl std::fmt::Display) -> RegistryError {
    RegistryError {
        message: error.to_string(),
    }
}
