//! Lazy LanceDB store for the four `fhv1_*` tables.
//! Reads of a missing table return an empty result. Writes create or append.
//! `domain_hypercubes` is never opened here.

use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use futures_util::TryStreamExt;
use lancedb::arrow::arrow_array::{
    Array, BooleanArray, FixedSizeBinaryArray, FixedSizeListArray, Float64Array, Int64Array,
    RecordBatch, StringArray, UInt16Array, UInt32Array, UInt64Array, UInt8Array,
};
use lancedb::arrow::arrow_buffer::Buffer;
use lancedb::arrow::arrow_schema::{DataType, Field, SchemaRef};
use lancedb::query::{ColumnOrdering, ExecutableQuery, QueryBase, Select};
use sf_kernels::{evaluate_fhv1_chunk, Fhv1ChunkEval, Fhv1Error, Fhv1ProfileStats, DIM};

use crate::fhv1_calibration::{
    assemble_calibration, stats_from_profile, Fhv1AuditTrace, Fhv1AuditTraceSummary,
    Fhv1BenchmarkRun, Fhv1CalibrationRequest, Fhv1CalibrationSample, Fhv1ProfileRecord,
    Fhv1StorageError, Fhv1TraceChunkDrilldown, Fhv1TraceDrilldown, Fhv1TracePage, Fhv1TraceQuery,
};
use crate::fhv1_schema::{
    fhv1_audit_trace_schema, fhv1_benchmark_run_schema, fhv1_calibration_sample_schema,
    fhv1_profile_schema, FHV1_AUDIT_TRACES_TABLE, FHV1_BENCHMARK_RUNS_TABLE,
    FHV1_CALIBRATION_SAMPLES_TABLE, FHV1_PROFILES_TABLE,
};

const TRACE_SUMMARY_COLUMNS: &[&str] = &[
    "trace_id",
    "run_id",
    "source_kind",
    "profile_id",
    "policy_id",
    "category",
    "expected_pass",
    "input_id",
    "raw_text",
    "eval_granularity",
    "use_rogue_mask",
    "chunk_index",
    "chunk_strategy",
    "chunk_text",
    "chunk_passed",
    "overall_passed",
    "full_text_passed",
    "all_chunks_passed",
    "evaluated_dims",
    "failed_dims_count",
    "underflow_count",
    "overflow_count",
    "max_violation_delta",
    "mean_abs_delta_vs_mean",
    "eval_latency_ns",
    "embedding_ms",
    "created_at_ms",
];

pub struct Fhv1Store {
    pub uri: String,
}

impl Fhv1Store {
    pub fn new(uri: impl Into<String>) -> Self {
        Self { uri: uri.into() }
    }

    pub async fn save_calibration_profile(
        &self,
        request: &Fhv1CalibrationRequest,
    ) -> Result<Fhv1ProfileRecord, Fhv1StorageError> {
        let version = self.next_version(&request.policy_id).await?;
        let (profile, samples) = assemble_calibration(request, version, now_ms())?;
        self.append_batch(FHV1_CALIBRATION_SAMPLES_TABLE, samples_batch(&samples)?)
            .await?;
        self.append_batch(
            FHV1_PROFILES_TABLE,
            profiles_batch(std::slice::from_ref(&profile))?,
        )
        .await?;
        Ok(profile)
    }

    pub async fn list_profiles(&self) -> Result<Vec<Fhv1ProfileRecord>, Fhv1StorageError> {
        let batches = self.read_batches(FHV1_PROFILES_TABLE, None, None).await?;
        let mut rows = Vec::new();
        for_each_row(&batches, |batch, row| {
            rows.push(read_profile(batch, row)?);
            Ok(())
        })?;
        rows.sort_by(|left, right| left.profile_id.cmp(&right.profile_id));
        Ok(rows)
    }

    pub async fn get_profile(
        &self,
        profile_id: &str,
    ) -> Result<Option<Fhv1ProfileRecord>, Fhv1StorageError> {
        let filter = format!("profile_id = {}", sql_string(profile_id));
        let batches = self
            .read_batches(FHV1_PROFILES_TABLE, Some(filter), None)
            .await?;
        let mut found = None;
        for_each_row(&batches, |batch, row| {
            found = Some(read_profile(batch, row)?);
            Ok(())
        })?;
        Ok(found)
    }

    pub async fn list_samples_for_profile(
        &self,
        profile_id: &str,
    ) -> Result<Vec<Fhv1CalibrationSample>, Fhv1StorageError> {
        let filter = format!("profile_id = {}", sql_string(profile_id));
        let batches = self
            .read_batches(FHV1_CALIBRATION_SAMPLES_TABLE, Some(filter), None)
            .await?;
        let mut rows = Vec::new();
        for_each_row(&batches, |batch, row| {
            rows.push(read_sample(batch, row)?);
            Ok(())
        })?;
        rows.sort_by(|left, right| left.sample_id.cmp(&right.sample_id));
        Ok(rows)
    }

    pub async fn save_benchmark_run(&self, run: &Fhv1BenchmarkRun) -> Result<(), Fhv1StorageError> {
        self.append_batch(
            FHV1_BENCHMARK_RUNS_TABLE,
            runs_batch(std::slice::from_ref(run))?,
        )
        .await
    }

    pub async fn list_benchmark_runs(&self) -> Result<Vec<Fhv1BenchmarkRun>, Fhv1StorageError> {
        let batches = self
            .read_batches(FHV1_BENCHMARK_RUNS_TABLE, None, None)
            .await?;
        let mut rows = Vec::new();
        for_each_row(&batches, |batch, row| {
            rows.push(read_run(batch, row)?);
            Ok(())
        })?;
        rows.sort_by(|left, right| left.run_id.cmp(&right.run_id));
        Ok(rows)
    }

    pub async fn get_benchmark_run(
        &self,
        run_id: &str,
    ) -> Result<Option<Fhv1BenchmarkRun>, Fhv1StorageError> {
        let filter = format!("run_id = {}", sql_string(run_id));
        let batches = self
            .read_batches(FHV1_BENCHMARK_RUNS_TABLE, Some(filter), None)
            .await?;
        let mut found = None;
        for_each_row(&batches, |batch, row| {
            found = Some(read_run(batch, row)?);
            Ok(())
        })?;
        Ok(found)
    }

    pub async fn append_audit_traces(
        &self,
        traces: &[Fhv1AuditTrace],
    ) -> Result<(), Fhv1StorageError> {
        if traces.is_empty() {
            return Ok(());
        }
        self.append_batch(FHV1_AUDIT_TRACES_TABLE, traces_batch(traces)?)
            .await
    }

    pub async fn query_audit_trace_summaries(
        &self,
        query: &Fhv1TraceQuery,
    ) -> Result<Fhv1TracePage, Fhv1StorageError> {
        let (page, page_size) = page_window(query.page, query.page_size);
        let Some(table) = self.open_existing_table(FHV1_AUDIT_TRACES_TABLE).await? else {
            return Ok(Fhv1TracePage {
                page,
                page_size,
                total: 0,
                rows: Vec::new(),
            });
        };
        let filter = trace_filter(query);
        let row_count = Box::pin(table.count_rows(filter.clone()))
            .await
            .map_err(Fhv1StorageError::new)?;
        let total = u64::try_from(row_count).unwrap_or(u64::MAX);
        let start_u64 = u64::from(page - 1).saturating_mul(u64::from(page_size));
        if total == 0 || start_u64 >= total {
            return Ok(Fhv1TracePage {
                page,
                page_size,
                total,
                rows: Vec::new(),
            });
        }
        let Ok(start) = usize::try_from(start_u64) else {
            return Ok(Fhv1TracePage {
                page,
                page_size,
                total,
                rows: Vec::new(),
            });
        };
        let limit = usize::try_from(page_size).unwrap_or(usize::MAX);
        let mut lancedb_query = table
            .query()
            .select(Select::columns(TRACE_SUMMARY_COLUMNS))
            .order_by(Some(vec![
                ColumnOrdering::desc_nulls_last("created_at_ms".to_string()),
                ColumnOrdering::asc_nulls_last("chunk_index".to_string()),
                ColumnOrdering::asc_nulls_last("trace_id".to_string()),
            ]))
            .offset(start)
            .limit(limit);
        if let Some(filter) = filter.as_deref() {
            lancedb_query = lancedb_query.only_if(filter);
        }
        let batches = collect_query_batches(lancedb_query).await?;
        let mut rows = Vec::with_capacity(batches.iter().map(RecordBatch::num_rows).sum());
        for_each_row(&batches, |batch, index| {
            rows.push(read_summary(batch, index)?);
            Ok(())
        })?;
        Ok(Fhv1TracePage {
            page,
            page_size,
            total,
            rows,
        })
    }

    pub async fn get_trace_drilldown(
        &self,
        trace_id: &str,
    ) -> Result<Option<Fhv1TraceDrilldown>, Fhv1StorageError> {
        let filter = format!("trace_id = {}", sql_string(trace_id));
        let batches = self
            .read_batches(FHV1_AUDIT_TRACES_TABLE, Some(filter), None)
            .await?;
        let mut traces = Vec::new();
        for_each_row(&batches, |batch, row| {
            traces.push(read_trace(batch, row)?);
            Ok(())
        })?;
        if traces.is_empty() {
            return Ok(None);
        }
        traces.sort_by_key(|trace| trace.chunk_index);
        let profile_id = traces[0].profile_id.clone();
        let profile = self
            .get_profile(&profile_id)
            .await?
            .ok_or_else(|| Fhv1StorageError::new(format!("missing fhv1 profile {profile_id}")))?;
        let stats = stats_from_profile(&profile);
        let mut chunks = Vec::with_capacity(traces.len());
        for trace in traces {
            let evaluated =
                evaluate_stored_chunk(&stats, &trace.input_vector, trace.use_rogue_mask)?;
            chunks.push(Fhv1TraceChunkDrilldown {
                trace,
                dimensions: evaluated.dimensions,
            });
        }
        Ok(Some(Fhv1TraceDrilldown {
            trace_id: trace_id.to_string(),
            profile,
            chunks,
        }))
    }

    async fn next_version(&self, policy_id: &str) -> Result<u64, Fhv1StorageError> {
        let max = self
            .list_profiles()
            .await?
            .into_iter()
            .filter(|profile| profile.policy_id == policy_id)
            .map(|profile| profile.version)
            .max()
            .unwrap_or(0);
        Ok(max + 1)
    }

    async fn connect(&self) -> Result<lancedb::Connection, Fhv1StorageError> {
        Box::pin(lancedb::connect(&self.uri).execute())
            .await
            .map_err(Fhv1StorageError::new)
    }

    async fn append_batch(
        &self,
        table_name: &str,
        batch: RecordBatch,
    ) -> Result<(), Fhv1StorageError> {
        let conn = self.connect().await?;
        if table_exists(&conn, table_name).await? {
            let table = Box::pin(conn.open_table(table_name).execute())
                .await
                .map_err(Fhv1StorageError::new)?;
            Box::pin(table.add(batch).execute())
                .await
                .map_err(Fhv1StorageError::new)?;
        } else {
            Box::pin(conn.create_table(table_name, batch).execute())
                .await
                .map_err(Fhv1StorageError::new)?;
        }
        Ok(())
    }

    async fn open_existing_table(
        &self,
        table_name: &str,
    ) -> Result<Option<lancedb::Table>, Fhv1StorageError> {
        let conn = self.connect().await?;
        if !table_exists(&conn, table_name).await? {
            return Ok(None);
        }
        let table = Box::pin(conn.open_table(table_name).execute())
            .await
            .map_err(Fhv1StorageError::new)?;
        Ok(Some(table))
    }

    async fn read_batches(
        &self,
        table_name: &str,
        filter: Option<String>,
        columns: Option<&[&str]>,
    ) -> Result<Vec<RecordBatch>, Fhv1StorageError> {
        let Some(table) = self.open_existing_table(table_name).await? else {
            return Ok(Vec::new());
        };
        let mut query = table.query();
        if let Some(filter) = filter.as_deref() {
            query = query.only_if(filter);
        }
        if let Some(columns) = columns {
            query = query.select(Select::columns(columns));
        }
        collect_query_batches(query).await
    }
}

async fn collect_query_batches(
    query: lancedb::query::Query,
) -> Result<Vec<RecordBatch>, Fhv1StorageError> {
    let stream = Box::pin(query.execute())
        .await
        .map_err(Fhv1StorageError::new)?;
    Box::pin(stream.try_collect())
        .await
        .map_err(Fhv1StorageError::new)
}

/// Keeps the 1024-d comparison buffer out of the caller's async state machine.
#[inline(never)]
fn evaluate_stored_chunk(
    stats: &Fhv1ProfileStats,
    observed: &[f64; DIM],
    use_rogue_mask: bool,
) -> Result<Fhv1ChunkEval, Fhv1Error> {
    evaluate_fhv1_chunk(stats, observed, use_rogue_mask)
}

async fn table_exists(conn: &lancedb::Connection, name: &str) -> Result<bool, Fhv1StorageError> {
    let names = Box::pin(conn.table_names().execute())
        .await
        .map_err(Fhv1StorageError::new)?;
    Ok(names.iter().any(|candidate| candidate == name))
}

fn now_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|elapsed| i64::try_from(elapsed.as_millis()).unwrap_or(i64::MAX))
        .unwrap_or(0)
}

fn sql_string(value: &str) -> String {
    format!("'{}'", value.replace('\'', "''"))
}

fn page_window(page: u32, page_size: u32) -> (u32, u32) {
    let page = if page == 0 { 1 } else { page };
    let page_size = if page_size == 0 { 50 } else { page_size };
    (page, page_size)
}

fn trace_filter(query: &Fhv1TraceQuery) -> Option<String> {
    let mut parts = Vec::new();
    if let Some(trace_id) = &query.trace_id {
        parts.push(format!("trace_id = {}", sql_string(trace_id)));
    }
    if let Some(run_id) = &query.run_id {
        parts.push(format!("run_id = {}", sql_string(run_id)));
    }
    if let Some(profile_id) = &query.profile_id {
        parts.push(format!("profile_id = {}", sql_string(profile_id)));
    }
    if let Some(source_kind) = &query.source_kind {
        parts.push(format!("source_kind = {}", sql_string(source_kind)));
    }
    if let Some(category) = &query.category {
        parts.push(format!("category = {}", sql_string(category)));
    }
    if let Some(passed) = query.passed {
        parts.push(format!(
            "overall_passed = {}",
            if passed { "true" } else { "false" }
        ));
    }
    if parts.is_empty() {
        None
    } else {
        Some(parts.join(" AND "))
    }
}

fn for_each_row(
    batches: &[RecordBatch],
    mut visit: impl FnMut(&RecordBatch, usize) -> Result<(), Fhv1StorageError>,
) -> Result<(), Fhv1StorageError> {
    for batch in batches {
        for row in 0..batch.num_rows() {
            visit(batch, row)?;
        }
    }
    Ok(())
}

fn samples_batch(rows: &[Fhv1CalibrationSample]) -> Result<RecordBatch, Fhv1StorageError> {
    let vectors = copied_f64_rows(rows.iter().map(|row| row.vector.as_ref()));
    batch(
        fhv1_calibration_sample_schema(),
        vec![
            strings(rows.iter().map(|row| row.sample_id.as_str())),
            strings(rows.iter().map(|row| row.profile_id.as_str())),
            strings(rows.iter().map(|row| row.policy_id.as_str())),
            uint64(rows.iter().map(|row| row.version)),
            strings(rows.iter().map(|row| row.source_ref.as_str())),
            strings(rows.iter().map(|row| row.strategy_tag.as_str())),
            strings(rows.iter().map(|row| row.raw_text.as_str())),
            fixed32(&rows.iter().map(|row| row.text_sha256).collect::<Vec<_>>())?,
            bools(rows.iter().map(|row| row.normalize)),
            strings(rows.iter().map(|row| row.model_id.as_str())),
            strings(rows.iter().map(|row| row.source_dtype.as_str())),
            f64_matrix(&vectors)?,
            int64(rows.iter().map(|row| row.created_at_ms)),
        ],
    )
}

fn profiles_batch(rows: &[Fhv1ProfileRecord]) -> Result<RecordBatch, Fhv1StorageError> {
    batch(
        fhv1_profile_schema(),
        vec![
            strings(rows.iter().map(|row| row.profile_id.as_str())),
            strings(rows.iter().map(|row| row.policy_id.as_str())),
            uint64(rows.iter().map(|row| row.version)),
            uint8(rows.iter().map(|row| row.polarity)),
            bools(rows.iter().map(|row| row.normalize)),
            bools(rows.iter().map(|row| row.use_rogue_mask_default)),
            uint64(rows.iter().map(|row| row.sample_count)),
            fixed32(&rows.iter().map(|row| row.corpus_sha256).collect::<Vec<_>>())?,
            strings(rows.iter().map(|row| row.model_id.as_str())),
            strings(rows.iter().map(|row| row.source_dtype.as_str())),
            bools(rows.iter().map(|row| row.augmented_llm)),
            f64_matrix(&copied_f64_rows(
                rows.iter().map(|row| row.min_vector.as_ref()),
            ))?,
            f64_matrix(&copied_f64_rows(
                rows.iter().map(|row| row.max_vector.as_ref()),
            ))?,
            f64_matrix(&copied_f64_rows(
                rows.iter().map(|row| row.mean_vector.as_ref()),
            ))?,
            f64_matrix(&copied_f64_rows(
                rows.iter().map(|row| row.span_vector.as_ref()),
            ))?,
            f64_matrix(&copied_f64_rows(
                rows.iter().map(|row| row.variance_vector.as_ref()),
            ))?,
            f64_matrix(&copied_f64_rows(
                rows.iter().map(|row| row.std_dev_vector.as_ref()),
            ))?,
            u8_matrix(&copied_u8_rows(
                rows.iter().map(|row| row.movement_tier_codes.as_ref()),
            ))?,
            int64(rows.iter().map(|row| row.created_at_ms)),
        ],
    )
}

fn runs_batch(rows: &[Fhv1BenchmarkRun]) -> Result<RecordBatch, Fhv1StorageError> {
    batch(
        fhv1_benchmark_run_schema(),
        vec![
            strings(rows.iter().map(|row| row.run_id.as_str())),
            strings(rows.iter().map(|row| row.profile_id.as_str())),
            strings(rows.iter().map(|row| row.policy_id.as_str())),
            strings(rows.iter().map(|row| row.dataset_name.as_str())),
            fixed32(
                &rows
                    .iter()
                    .map(|row| row.dataset_sha256)
                    .collect::<Vec<_>>(),
            )?,
            strings(rows.iter().map(|row| row.eval_granularity.as_str())),
            bools(rows.iter().map(|row| row.use_rogue_mask)),
            uint64(rows.iter().map(|row| row.total_inputs)),
            uint64(rows.iter().map(|row| row.total_chunks)),
            strings(rows.iter().map(|row| row.summary_metrics_json.as_str())),
            int64(rows.iter().map(|row| row.created_at_ms)),
        ],
    )
}

fn traces_batch(rows: &[Fhv1AuditTrace]) -> Result<RecordBatch, Fhv1StorageError> {
    let vectors = copied_f64_rows(rows.iter().map(|row| row.input_vector.as_ref()));
    batch(
        fhv1_audit_trace_schema(),
        vec![
            strings(rows.iter().map(|row| row.trace_id.as_str())),
            strings(rows.iter().map(|row| row.run_id.as_str())),
            strings(rows.iter().map(|row| row.source_kind.as_str())),
            strings(rows.iter().map(|row| row.profile_id.as_str())),
            strings(rows.iter().map(|row| row.policy_id.as_str())),
            strings(rows.iter().map(|row| row.category.as_str())),
            optional_bools(rows.iter().map(|row| row.expected_pass)),
            strings(rows.iter().map(|row| row.input_id.as_str())),
            strings(rows.iter().map(|row| row.raw_text.as_str())),
            strings(rows.iter().map(|row| row.eval_granularity.as_str())),
            bools(rows.iter().map(|row| row.use_rogue_mask)),
            uint32(rows.iter().map(|row| row.chunk_index)),
            strings(rows.iter().map(|row| row.chunk_strategy.as_str())),
            strings(rows.iter().map(|row| row.chunk_text.as_str())),
            f64_matrix(&vectors)?,
            bools(rows.iter().map(|row| row.chunk_passed)),
            bools(rows.iter().map(|row| row.overall_passed)),
            bools(rows.iter().map(|row| row.full_text_passed)),
            bools(rows.iter().map(|row| row.all_chunks_passed)),
            uint16(rows.iter().map(|row| row.evaluated_dims)),
            uint16(rows.iter().map(|row| row.failed_dims_count)),
            uint16(rows.iter().map(|row| row.underflow_count)),
            uint16(rows.iter().map(|row| row.overflow_count)),
            float64(rows.iter().map(|row| row.max_violation_delta)),
            float64(rows.iter().map(|row| row.mean_abs_delta_vs_mean)),
            uint64(rows.iter().map(|row| row.eval_latency_ns)),
            float64(rows.iter().map(|row| row.embedding_ms)),
            int64(rows.iter().map(|row| row.created_at_ms)),
        ],
    )
}

fn batch(schema: SchemaRef, columns: Vec<Arc<dyn Array>>) -> Result<RecordBatch, Fhv1StorageError> {
    RecordBatch::try_new(schema, columns).map_err(Fhv1StorageError::new)
}

fn strings<'a>(values: impl Iterator<Item = &'a str>) -> Arc<dyn Array> {
    Arc::new(StringArray::from_iter_values(values))
}

fn bools(values: impl Iterator<Item = bool>) -> Arc<dyn Array> {
    Arc::new(BooleanArray::from(values.collect::<Vec<_>>()))
}

fn optional_bools(values: impl Iterator<Item = Option<bool>>) -> Arc<dyn Array> {
    Arc::new(BooleanArray::from(values.collect::<Vec<_>>()))
}

fn uint64(values: impl Iterator<Item = u64>) -> Arc<dyn Array> {
    Arc::new(UInt64Array::from(values.collect::<Vec<_>>()))
}

fn uint32(values: impl Iterator<Item = u32>) -> Arc<dyn Array> {
    Arc::new(UInt32Array::from(values.collect::<Vec<_>>()))
}

fn uint16(values: impl Iterator<Item = u16>) -> Arc<dyn Array> {
    Arc::new(UInt16Array::from(values.collect::<Vec<_>>()))
}

fn uint8(values: impl Iterator<Item = u8>) -> Arc<dyn Array> {
    Arc::new(UInt8Array::from(values.collect::<Vec<_>>()))
}

fn int64(values: impl Iterator<Item = i64>) -> Arc<dyn Array> {
    Arc::new(Int64Array::from(values.collect::<Vec<_>>()))
}

fn float64(values: impl Iterator<Item = f64>) -> Arc<dyn Array> {
    Arc::new(Float64Array::from(values.collect::<Vec<_>>()))
}

fn fixed32(rows: &[[u8; 32]]) -> Result<Arc<dyn Array>, Fhv1StorageError> {
    let mut bytes = Vec::with_capacity(rows.len() * 32);
    for row in rows {
        bytes.extend_from_slice(row);
    }
    let array = FixedSizeBinaryArray::try_new(32, Buffer::from(bytes), None)
        .map_err(Fhv1StorageError::new)?;
    Ok(Arc::new(array))
}

fn f64_matrix(rows: &[[f64; DIM]]) -> Result<Arc<dyn Array>, Fhv1StorageError> {
    let mut flat = Vec::with_capacity(rows.len() * DIM);
    for row in rows {
        flat.extend_from_slice(row);
    }
    let child = Float64Array::from(flat);
    let array = FixedSizeListArray::try_new(
        Arc::new(Field::new("item", DataType::Float64, false)),
        DIM as i32,
        Arc::new(child),
        None,
    )
    .map_err(Fhv1StorageError::new)?;
    Ok(Arc::new(array))
}

fn u8_matrix(rows: &[[u8; DIM]]) -> Result<Arc<dyn Array>, Fhv1StorageError> {
    let mut flat = Vec::with_capacity(rows.len() * DIM);
    for row in rows {
        flat.extend_from_slice(row);
    }
    let child = UInt8Array::from(flat);
    let array = FixedSizeListArray::try_new(
        Arc::new(Field::new("item", DataType::UInt8, false)),
        DIM as i32,
        Arc::new(child),
        None,
    )
    .map_err(Fhv1StorageError::new)?;
    Ok(Arc::new(array))
}

fn read_sample(batch: &RecordBatch, row: usize) -> Result<Fhv1CalibrationSample, Fhv1StorageError> {
    Ok(Fhv1CalibrationSample {
        sample_id: utf8(batch, "sample_id", row)?,
        profile_id: utf8(batch, "profile_id", row)?,
        policy_id: utf8(batch, "policy_id", row)?,
        version: u64_at(batch, "version", row)?,
        source_ref: utf8(batch, "source_ref", row)?,
        strategy_tag: utf8(batch, "strategy_tag", row)?,
        raw_text: utf8(batch, "raw_text", row)?,
        text_sha256: bytes32(batch, "text_sha256", row)?,
        normalize: bool_at(batch, "normalize", row)?,
        model_id: utf8(batch, "model_id", row)?,
        source_dtype: utf8(batch, "source_dtype", row)?,
        vector: f64_row(batch, "vector", row)?,
        created_at_ms: i64_at(batch, "created_at_ms", row)?,
    })
}

fn read_profile(batch: &RecordBatch, row: usize) -> Result<Fhv1ProfileRecord, Fhv1StorageError> {
    Ok(Fhv1ProfileRecord {
        profile_id: utf8(batch, "profile_id", row)?,
        policy_id: utf8(batch, "policy_id", row)?,
        version: u64_at(batch, "version", row)?,
        polarity: u8_at(batch, "polarity", row)?,
        normalize: bool_at(batch, "normalize", row)?,
        use_rogue_mask_default: bool_at(batch, "use_rogue_mask_default", row)?,
        sample_count: u64_at(batch, "sample_count", row)?,
        corpus_sha256: bytes32(batch, "corpus_sha256", row)?,
        model_id: utf8(batch, "model_id", row)?,
        source_dtype: utf8(batch, "source_dtype", row)?,
        augmented_llm: bool_at(batch, "augmented_llm", row)?,
        min_vector: f64_row(batch, "min_vector", row)?,
        max_vector: f64_row(batch, "max_vector", row)?,
        mean_vector: f64_row(batch, "mean_vector", row)?,
        span_vector: f64_row(batch, "span_vector", row)?,
        variance_vector: f64_row(batch, "variance_vector", row)?,
        std_dev_vector: f64_row(batch, "std_dev_vector", row)?,
        movement_tier_codes: u8_row(batch, "movement_tier_codes", row)?,
        created_at_ms: i64_at(batch, "created_at_ms", row)?,
    })
}

fn read_run(batch: &RecordBatch, row: usize) -> Result<Fhv1BenchmarkRun, Fhv1StorageError> {
    Ok(Fhv1BenchmarkRun {
        run_id: utf8(batch, "run_id", row)?,
        profile_id: utf8(batch, "profile_id", row)?,
        policy_id: utf8(batch, "policy_id", row)?,
        dataset_name: utf8(batch, "dataset_name", row)?,
        dataset_sha256: bytes32(batch, "dataset_sha256", row)?,
        eval_granularity: utf8(batch, "eval_granularity", row)?,
        use_rogue_mask: bool_at(batch, "use_rogue_mask", row)?,
        total_inputs: u64_at(batch, "total_inputs", row)?,
        total_chunks: u64_at(batch, "total_chunks", row)?,
        summary_metrics_json: utf8(batch, "summary_metrics_json", row)?,
        created_at_ms: i64_at(batch, "created_at_ms", row)?,
    })
}

fn read_trace(batch: &RecordBatch, row: usize) -> Result<Fhv1AuditTrace, Fhv1StorageError> {
    Ok(Fhv1AuditTrace {
        trace_id: utf8(batch, "trace_id", row)?,
        run_id: utf8(batch, "run_id", row)?,
        source_kind: utf8(batch, "source_kind", row)?,
        profile_id: utf8(batch, "profile_id", row)?,
        policy_id: utf8(batch, "policy_id", row)?,
        category: utf8(batch, "category", row)?,
        expected_pass: optional_bool(batch, "expected_pass", row)?,
        input_id: utf8(batch, "input_id", row)?,
        raw_text: utf8(batch, "raw_text", row)?,
        eval_granularity: utf8(batch, "eval_granularity", row)?,
        use_rogue_mask: bool_at(batch, "use_rogue_mask", row)?,
        chunk_index: u32_at(batch, "chunk_index", row)?,
        chunk_strategy: utf8(batch, "chunk_strategy", row)?,
        chunk_text: utf8(batch, "chunk_text", row)?,
        input_vector: f64_row(batch, "input_vector", row)?,
        chunk_passed: bool_at(batch, "chunk_passed", row)?,
        overall_passed: bool_at(batch, "overall_passed", row)?,
        full_text_passed: bool_at(batch, "full_text_passed", row)?,
        all_chunks_passed: bool_at(batch, "all_chunks_passed", row)?,
        evaluated_dims: u16_at(batch, "evaluated_dims", row)?,
        failed_dims_count: u16_at(batch, "failed_dims_count", row)?,
        underflow_count: u16_at(batch, "underflow_count", row)?,
        overflow_count: u16_at(batch, "overflow_count", row)?,
        max_violation_delta: f64_at(batch, "max_violation_delta", row)?,
        mean_abs_delta_vs_mean: f64_at(batch, "mean_abs_delta_vs_mean", row)?,
        eval_latency_ns: u64_at(batch, "eval_latency_ns", row)?,
        embedding_ms: f64_at(batch, "embedding_ms", row)?,
        created_at_ms: i64_at(batch, "created_at_ms", row)?,
    })
}

fn read_summary(
    batch: &RecordBatch,
    row: usize,
) -> Result<Fhv1AuditTraceSummary, Fhv1StorageError> {
    Ok(Fhv1AuditTraceSummary {
        trace_id: utf8(batch, "trace_id", row)?,
        run_id: utf8(batch, "run_id", row)?,
        source_kind: utf8(batch, "source_kind", row)?,
        profile_id: utf8(batch, "profile_id", row)?,
        policy_id: utf8(batch, "policy_id", row)?,
        category: utf8(batch, "category", row)?,
        expected_pass: optional_bool(batch, "expected_pass", row)?,
        input_id: utf8(batch, "input_id", row)?,
        raw_text: utf8(batch, "raw_text", row)?,
        eval_granularity: utf8(batch, "eval_granularity", row)?,
        use_rogue_mask: bool_at(batch, "use_rogue_mask", row)?,
        chunk_index: u32_at(batch, "chunk_index", row)?,
        chunk_strategy: utf8(batch, "chunk_strategy", row)?,
        chunk_text: utf8(batch, "chunk_text", row)?,
        chunk_passed: bool_at(batch, "chunk_passed", row)?,
        overall_passed: bool_at(batch, "overall_passed", row)?,
        full_text_passed: bool_at(batch, "full_text_passed", row)?,
        all_chunks_passed: bool_at(batch, "all_chunks_passed", row)?,
        evaluated_dims: u16_at(batch, "evaluated_dims", row)?,
        failed_dims_count: u16_at(batch, "failed_dims_count", row)?,
        underflow_count: u16_at(batch, "underflow_count", row)?,
        overflow_count: u16_at(batch, "overflow_count", row)?,
        max_violation_delta: f64_at(batch, "max_violation_delta", row)?,
        mean_abs_delta_vs_mean: f64_at(batch, "mean_abs_delta_vs_mean", row)?,
        eval_latency_ns: u64_at(batch, "eval_latency_ns", row)?,
        embedding_ms: f64_at(batch, "embedding_ms", row)?,
        created_at_ms: i64_at(batch, "created_at_ms", row)?,
    })
}

fn column<'a, T: Array + 'static>(
    batch: &'a RecordBatch,
    name: &str,
) -> Result<&'a T, Fhv1StorageError> {
    let array = batch
        .column_by_name(name)
        .ok_or_else(|| Fhv1StorageError::new(format!("missing column {name}")))?;
    array
        .as_any()
        .downcast_ref::<T>()
        .ok_or_else(|| Fhv1StorageError::new(format!("column {name} has an unexpected type")))
}

fn utf8(batch: &RecordBatch, name: &str, row: usize) -> Result<String, Fhv1StorageError> {
    Ok(column::<StringArray>(batch, name)?.value(row).to_string())
}

fn bool_at(batch: &RecordBatch, name: &str, row: usize) -> Result<bool, Fhv1StorageError> {
    Ok(column::<BooleanArray>(batch, name)?.value(row))
}

fn optional_bool(
    batch: &RecordBatch,
    name: &str,
    row: usize,
) -> Result<Option<bool>, Fhv1StorageError> {
    let array = column::<BooleanArray>(batch, name)?;
    if array.is_null(row) {
        Ok(None)
    } else {
        Ok(Some(array.value(row)))
    }
}

fn u64_at(batch: &RecordBatch, name: &str, row: usize) -> Result<u64, Fhv1StorageError> {
    Ok(column::<UInt64Array>(batch, name)?.value(row))
}

fn u32_at(batch: &RecordBatch, name: &str, row: usize) -> Result<u32, Fhv1StorageError> {
    Ok(column::<UInt32Array>(batch, name)?.value(row))
}

fn u16_at(batch: &RecordBatch, name: &str, row: usize) -> Result<u16, Fhv1StorageError> {
    Ok(column::<UInt16Array>(batch, name)?.value(row))
}

fn u8_at(batch: &RecordBatch, name: &str, row: usize) -> Result<u8, Fhv1StorageError> {
    Ok(column::<UInt8Array>(batch, name)?.value(row))
}

fn i64_at(batch: &RecordBatch, name: &str, row: usize) -> Result<i64, Fhv1StorageError> {
    Ok(column::<Int64Array>(batch, name)?.value(row))
}

fn f64_at(batch: &RecordBatch, name: &str, row: usize) -> Result<f64, Fhv1StorageError> {
    Ok(column::<Float64Array>(batch, name)?.value(row))
}

fn bytes32(batch: &RecordBatch, name: &str, row: usize) -> Result<[u8; 32], Fhv1StorageError> {
    let array = column::<FixedSizeBinaryArray>(batch, name)?;
    let value = array.value(row);
    let mut out = [0u8; 32];
    if value.len() != 32 {
        return Err(Fhv1StorageError::new(format!(
            "{name} width is {}",
            value.len()
        )));
    }
    out.copy_from_slice(value);
    Ok(out)
}

fn copied_f64_rows<'a>(rows: impl Iterator<Item = &'a [f64; DIM]>) -> Vec<[f64; DIM]> {
    rows.copied().collect()
}

fn copied_u8_rows<'a>(rows: impl Iterator<Item = &'a [u8; DIM]>) -> Vec<[u8; DIM]> {
    rows.copied().collect()
}

fn boxed_f64_slice(values: &[f64]) -> Result<Box<[f64; DIM]>, Fhv1StorageError> {
    if values.len() != DIM {
        return Err(Fhv1StorageError::new(format!(
            "float64 width is {}, expected {DIM}",
            values.len()
        )));
    }
    let boxed: Box<[f64]> = values.to_vec().into_boxed_slice();
    boxed
        .try_into()
        .map_err(|_| Fhv1StorageError::new(format!("float64 width is not {DIM}")))
}

fn boxed_u8_slice(values: &[u8]) -> Result<Box<[u8; DIM]>, Fhv1StorageError> {
    if values.len() != DIM {
        return Err(Fhv1StorageError::new(format!(
            "uint8 width is {}, expected {DIM}",
            values.len()
        )));
    }
    let boxed: Box<[u8]> = values.to_vec().into_boxed_slice();
    boxed
        .try_into()
        .map_err(|_| Fhv1StorageError::new(format!("uint8 width is not {DIM}")))
}

fn f64_row(
    batch: &RecordBatch,
    name: &str,
    row: usize,
) -> Result<Box<[f64; DIM]>, Fhv1StorageError> {
    let list = column::<FixedSizeListArray>(batch, name)?;
    let child = list
        .values()
        .as_any()
        .downcast_ref::<Float64Array>()
        .ok_or_else(|| Fhv1StorageError::new(format!("{name} is not float64")))?;
    let start = list.value_offset(row) as usize;
    if list.value_length() as usize != DIM {
        return Err(Fhv1StorageError::new(format!("{name} width is not {DIM}")));
    }
    boxed_f64_slice(&child.values()[start..start + DIM])
}

fn u8_row(batch: &RecordBatch, name: &str, row: usize) -> Result<Box<[u8; DIM]>, Fhv1StorageError> {
    let list = column::<FixedSizeListArray>(batch, name)?;
    let child = list
        .values()
        .as_any()
        .downcast_ref::<UInt8Array>()
        .ok_or_else(|| Fhv1StorageError::new(format!("{name} is not uint8")))?;
    let start = list.value_offset(row) as usize;
    if list.value_length() as usize != DIM {
        return Err(Fhv1StorageError::new(format!("{name} width is not {DIM}")));
    }
    boxed_u8_slice(&child.values()[start..start + DIM])
}
