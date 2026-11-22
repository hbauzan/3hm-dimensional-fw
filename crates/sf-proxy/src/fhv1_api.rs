//! `/api/v1/fhv1` routes and the realtime chat gate.
#![allow(clippy::result_large_err)]

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use axum::extract::{Path, Query, State};
use axum::http::{header, HeaderMap, HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Deserialize;
use serde_json::{json, Value};
use sf_kernels::{
    classify_movement_tiers, evaluate_fhv1_batch, AlignedVec1024, DimBoundStatus,
    Fhv1EvalGranularity, Fhv1Quantiles, MovementMetric, DIM,
};
use sf_storage::{
    export_csv, export_parquet, export_xlsx, stats_from_profile, Fhv1AuditTrace, Fhv1BenchmarkRun,
    Fhv1ProfileRecord, Fhv1Store, Fhv1TraceQuery, Fhv1XlsxPayload, FHV1_XLSX_MAX_ROWS,
};
use sha2::{Digest, Sha256};

use crate::chat_api::ChatRequestDto;
use crate::fhv1_pipeline::{
    evaluate_fhv1_input, expand_for_granularity, Fhv1CalibrateSpec, Fhv1EvaluateSpec,
};
use crate::handler::ProxyAppState;

pub fn routes() -> Router<Arc<ProxyAppState>> {
    Router::new()
        .route("/api/v1/fhv1/profiles", get(list_profiles))
        .route(
            "/api/v1/fhv1/profiles/{profile_id}/export",
            get(export_profile),
        )
        .route("/api/v1/fhv1/profiles/{profile_id}", get(get_profile))
        .route("/api/v1/fhv1/calibrate", post(calibrate))
        .route("/api/v1/fhv1/evaluate", post(evaluate))
        .route("/api/v1/fhv1/benchmarks/run", post(run_benchmark))
        .route("/api/v1/fhv1/benchmarks/{run_id}", get(get_benchmark))
        .route("/api/v1/fhv1/benchmarks", get(list_benchmarks))
        .route("/api/v1/fhv1/traces/{trace_id}", get(get_trace))
        .route("/api/v1/fhv1/traces", get(list_traces))
}

pub struct RealtimeChatFhv1<'a> {
    pub payload: &'a ChatRequestDto,
    pub user_text: &'a str,
    pub preserve_3hm_breach: bool,
    pub reused_texts: &'a [&'a str],
    pub reused_vectors: &'a [AlignedVec1024],
    pub embedding_ms: f64,
}

pub fn chat_filter_mode(payload: &ChatRequestDto) -> Result<&str, Response> {
    match payload.filter_mode.as_deref() {
        None | Some("3hm_default") => Ok("3hm_default"),
        Some("fhv1") | Some("3hm_plus_fhv1") => {
            Ok(payload.filter_mode.as_deref().unwrap_or("fhv1"))
        }
        Some(other) => Err(error_response(
            StatusCode::BAD_REQUEST,
            &format!("unknown filter_mode {other}"),
        )),
    }
}

pub async fn run_realtime_chat(
    state: &ProxyAppState,
    request: RealtimeChatFhv1<'_>,
) -> Result<Option<String>, Response> {
    let mode = chat_filter_mode(request.payload)?;
    if mode == "3hm_default" {
        return Ok(None);
    }
    let store = require_store(state)?;
    let profile_id =
        request.payload.fhv1_profile_id.as_deref().ok_or_else(|| {
            error_response(StatusCode::BAD_REQUEST, "fhv1_profile_id is required")
        })?;
    let profile = store
        .get_profile(profile_id)
        .await
        .map_err(store_error)?
        .ok_or_else(|| error_response(StatusCode::NOT_FOUND, "fhv1 profile was not found"))?;
    let granularity = parse_granularity(request.payload.fhv1_granularity.as_deref())?;
    let use_rogue_mask = request
        .payload
        .fhv1_use_rogue_mask
        .unwrap_or(profile.use_rogue_mask_default);
    let evaluated = score_realtime(
        state,
        &profile,
        request.user_text,
        granularity,
        use_rogue_mask,
        ReusedBatch {
            texts: request.reused_texts,
            vectors: request.reused_vectors,
            embedding_ms: request.embedding_ms,
        },
    )
    .await?;
    let trace_id = new_trace_id("rt");
    let created_at_ms = now_ms();
    persist_eval_traces(
        store,
        &profile,
        &TraceMeta {
            trace_id: &trace_id,
            run_id: "",
            source_kind: "REALTIME_CHAT",
            category: "REALTIME",
            expected_pass: None,
            raw_text: request.user_text,
            input_id: &trace_id,
            granularity,
            use_rogue_mask,
            embedding_ms: evaluated.embedding_ms,
            created_at_ms,
        },
        &evaluated.chunks,
        &evaluated.vectors,
        &evaluated.scored,
    )
    .await?;
    if request.preserve_3hm_breach {
        return Ok(None);
    }
    if evaluated.scored.batch.overall_passed {
        return Ok(Some(trace_id));
    }
    Err(fhv1_breach_response(
        &profile,
        &trace_id,
        granularity,
        use_rogue_mask,
        &evaluated,
    ))
}

struct ScoredRealtime {
    chunks: Vec<crate::fhv1_pipeline::ExpandedChunk>,
    vectors: Vec<Box<[f64; DIM]>>,
    scored: crate::fhv1_pipeline::Fhv1EvaluatedInput,
    embedding_ms: f64,
}

struct ReusedBatch<'a> {
    texts: &'a [&'a str],
    vectors: &'a [AlignedVec1024],
    embedding_ms: f64,
}

async fn score_realtime(
    state: &ProxyAppState,
    profile: &Fhv1ProfileRecord,
    user_text: &str,
    granularity: Fhv1EvalGranularity,
    use_rogue_mask: bool,
    reused: ReusedBatch<'_>,
) -> Result<ScoredRealtime, Response> {
    let chunks = expand_for_granularity(user_text, granularity);
    let reuse = profile.normalize
        && granularity != Fhv1EvalGranularity::FullMirror
        && chunks.len() == reused.texts.len()
        && chunks.len() == reused.vectors.len()
        && chunks
            .iter()
            .zip(reused.texts)
            .all(|(chunk, text)| chunk.text == *text);
    if reuse {
        let vectors: Vec<Box<[f64; DIM]>> = reused.vectors.iter().map(promote_f32).collect();
        let rows: Vec<&[f64]> = vectors.iter().map(|row| row.as_slice()).collect();
        let stats = stats_from_profile(profile);
        let eval_started = Instant::now();
        let batch = evaluate_fhv1_batch(&stats, &rows, granularity, use_rogue_mask)
            .map_err(|err| error_response(StatusCode::BAD_REQUEST, &err.to_string()))?;
        let eval_latency_ns = u64::try_from(eval_started.elapsed().as_nanos()).unwrap_or(u64::MAX);
        let scored = crate::fhv1_pipeline::Fhv1EvaluatedInput {
            chunks: chunks.clone(),
            vectors: vectors.clone(),
            batch,
            embedding_ms: reused.embedding_ms,
            eval_latency_ns,
        };
        return Ok(ScoredRealtime {
            chunks,
            vectors,
            scored,
            embedding_ms: reused.embedding_ms,
        });
    }
    let scored = evaluate_fhv1_input(
        state.embedder.as_ref(),
        profile,
        &Fhv1EvaluateSpec {
            raw_text: user_text,
            granularity,
            normalize_embeddings: profile.normalize,
            use_rogue_mask,
        },
    )
    .await
    .map_err(|err| error_response(StatusCode::BAD_GATEWAY, &err))?;
    let chunks = scored.chunks.clone();
    let vectors = scored.vectors.clone();
    let embedding_ms = scored.embedding_ms;
    Ok(ScoredRealtime {
        chunks,
        vectors,
        scored,
        embedding_ms,
    })
}

fn promote_f32(vector: &AlignedVec1024) -> Box<[f64; DIM]> {
    let mut row = vec![0.0; DIM];
    for (index, value) in vector.data.iter().enumerate() {
        row[index] = f64::from(*value);
    }
    let boxed: Box<[f64]> = row.into_boxed_slice();
    boxed.try_into().unwrap_or_else(|_| unreachable!("dim"))
}

fn fhv1_breach_response(
    profile: &Fhv1ProfileRecord,
    trace_id: &str,
    granularity: Fhv1EvalGranularity,
    use_rogue_mask: bool,
    evaluated: &ScoredRealtime,
) -> Response {
    let failing = evaluated
        .scored
        .batch
        .chunks
        .iter()
        .position(|chunk| !chunk.chunk_passed)
        .unwrap_or(0);
    let chunk = &evaluated.scored.batch.chunks[failing];
    let body = json!({
        "error": {
            "kind": "fhv1_ingress_breach",
            "code": "SEMANTIC_CONTAINMENT_BREACH",
            "message": "fhv1 AABB envelope rejected the prompt",
            "telemetry": {
                "trace_id": trace_id,
                "profile_id": profile.profile_id,
                "policy_id": profile.policy_id,
                "failing_tier": "FHV1_AABB_ENVELOPE",
                "eval_granularity": granularity_name(granularity),
                "use_rogue_mask": use_rogue_mask,
                "full_text_passed": evaluated.scored.batch.full_text_passed,
                "all_chunks_passed": evaluated.scored.batch.all_chunks_passed,
                "failing_chunk_index": failing,
                "failed_dims_count": chunk.failed_dims_count,
                "underflow_count": chunk.underflow_count,
                "overflow_count": chunk.overflow_count,
                "max_violation_delta": chunk.max_violation_delta,
                "embedding_ms": evaluated.embedding_ms,
                "eval_latency_ns": evaluated.scored.eval_latency_ns,
            }
        }
    });
    let mut response = (StatusCode::FORBIDDEN, Json(body)).into_response();
    stamp_fhv1_headers(response.headers_mut(), trace_id, "BREACH");
    response
}

fn stamp_fhv1_headers(headers: &mut HeaderMap, trace_id: &str, decision: &'static str) {
    if let Ok(value) = HeaderValue::from_str(trace_id) {
        headers.insert("x-sf-trace-id", value);
    }
    headers.insert("x-sf-fhv1-decision", HeaderValue::from_static(decision));
}

async fn list_profiles(State(state): State<Arc<ProxyAppState>>) -> Response {
    let Some(store) = state.fhv1_store.as_deref() else {
        return Json(json!([])).into_response();
    };
    match store.list_profiles().await {
        Ok(profiles) => {
            Json(profiles.iter().map(profile_summary).collect::<Vec<_>>()).into_response()
        }
        Err(err) => store_error(err),
    }
}

async fn get_profile(
    State(state): State<Arc<ProxyAppState>>,
    Path(profile_id): Path<String>,
    Query(query): Query<ProfileQuery>,
) -> Response {
    let store = match require_store(&state) {
        Ok(store) => store,
        Err(response) => return response,
    };
    let profile = match store.get_profile(&profile_id).await {
        Ok(Some(profile)) => profile,
        Ok(None) => return error_response(StatusCode::NOT_FOUND, "fhv1 profile was not found"),
        Err(err) => return store_error(err),
    };
    let metric = match parse_metric(query.metric.as_deref()) {
        Ok(metric) => metric,
        Err(response) => return response,
    };
    let quantiles = Fhv1Quantiles {
        p25: query.p25.unwrap_or(0.25),
        p75: query.p75.unwrap_or(0.75),
        p90: query.p90.unwrap_or(0.90),
    };
    let tiers = classify_movement_tiers(
        profile.span_vector.as_ref(),
        profile.variance_vector.as_ref(),
        profile.std_dev_vector.as_ref(),
        metric,
        quantiles,
    );
    let tiers = match tiers {
        Ok(tiers) => tiers,
        Err(err) => return error_response(StatusCode::BAD_REQUEST, &err.to_string()),
    };
    let mut body = profile_summary(&profile);
    body["min"] = json!(profile.min_vector.as_ref().as_slice());
    body["max"] = json!(profile.max_vector.as_ref().as_slice());
    body["mean"] = json!(profile.mean_vector.as_ref().as_slice());
    body["span"] = json!(profile.span_vector.as_ref().as_slice());
    body["variance"] = json!(profile.variance_vector.as_ref().as_slice());
    body["std_dev"] = json!(profile.std_dev_vector.as_ref().as_slice());
    body["movement_tier_codes"] = json!(tiers.codes.as_ref().as_slice());
    body["quantile_cutoffs"] = json!({
        "p25": tiers.cutoffs.p25,
        "p75": tiers.cutoffs.p75,
        "p90": tiers.cutoffs.p90,
    });
    Json(body).into_response()
}

async fn calibrate(
    State(state): State<Arc<ProxyAppState>>,
    Json(body): Json<CalibrateBody>,
) -> Response {
    let store = match require_store(&state) {
        Ok(store) => store,
        Err(response) => return response,
    };
    let profile = crate::fhv1_pipeline::calibrate_fhv1_corpus(
        store,
        state.embedder.as_ref(),
        &Fhv1CalibrateSpec {
            policy_id: &body.policy_id,
            raw_texts: &body.texts,
            normalize: body.normalize.unwrap_or(true),
            use_rogue_mask_default: body.use_rogue_mask_default.unwrap_or(false),
            polarity: 0,
            model_id: "BAAI/bge-m3",
            augmented_llm: false,
            metric: MovementMetric::Span,
            quantiles: Fhv1Quantiles::standard(),
        },
    )
    .await;
    match profile {
        Ok(profile) => (StatusCode::OK, Json(profile_summary(&profile))).into_response(),
        Err(err) => error_response(StatusCode::BAD_GATEWAY, &err),
    }
}

async fn export_profile(
    State(state): State<Arc<ProxyAppState>>,
    Path(profile_id): Path<String>,
    Query(query): Query<ExportQuery>,
) -> Response {
    let store = match require_store(&state) {
        Ok(store) => store,
        Err(response) => return response,
    };
    let profile = match store.get_profile(&profile_id).await {
        Ok(Some(profile)) => profile,
        Ok(None) => return error_response(StatusCode::NOT_FOUND, "fhv1 profile was not found"),
        Err(err) => return store_error(err),
    };
    let samples = match store.list_samples_for_profile(&profile_id).await {
        Ok(samples) => samples,
        Err(err) => return store_error(err),
    };
    let format = query.format.as_deref().unwrap_or("xlsx");
    let max_rows = query.max_rows.unwrap_or(FHV1_XLSX_MAX_ROWS);
    match format {
        "csv" => attachment(
            export_csv(&profile),
            "text/csv",
            &format!("{profile_id}.csv"),
        ),
        "parquet" => match export_parquet(&profile) {
            Ok(bytes) => attachment(
                bytes,
                "application/vnd.apache.parquet",
                &format!("{profile_id}.parquet"),
            ),
            Err(err) => store_error(err),
        },
        "xlsx" => match export_xlsx(&profile, &samples, max_rows) {
            Ok(Fhv1XlsxPayload::Xlsx(bytes)) => attachment(
                bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                &format!("{profile_id}.xlsx"),
            ),
            Ok(Fhv1XlsxPayload::Zip(bytes)) => {
                attachment(bytes, "application/zip", &format!("{profile_id}.zip"))
            }
            Err(err) => store_error(err),
        },
        other => error_response(
            StatusCode::BAD_REQUEST,
            &format!("unknown export format {other}"),
        ),
    }
}

async fn evaluate(
    State(state): State<Arc<ProxyAppState>>,
    Json(body): Json<EvaluateBody>,
) -> Response {
    let store = match require_store(&state) {
        Ok(store) => store,
        Err(response) => return response,
    };
    let profile = match store.get_profile(&body.profile_id).await {
        Ok(Some(profile)) => profile,
        Ok(None) => return error_response(StatusCode::NOT_FOUND, "fhv1 profile was not found"),
        Err(err) => return store_error(err),
    };
    let granularity = match parse_granularity(body.eval_granularity.as_deref()) {
        Ok(granularity) => granularity,
        Err(response) => return response,
    };
    let use_rogue_mask = body
        .use_rogue_mask
        .unwrap_or(profile.use_rogue_mask_default);
    let scored = match evaluate_fhv1_input(
        state.embedder.as_ref(),
        &profile,
        &Fhv1EvaluateSpec {
            raw_text: &body.text,
            granularity,
            normalize_embeddings: profile.normalize,
            use_rogue_mask,
        },
    )
    .await
    {
        Ok(scored) => scored,
        Err(err) => return error_response(StatusCode::BAD_GATEWAY, &err),
    };
    let trace_id = new_trace_id("lab");
    let created_at_ms = now_ms();
    if let Err(response) = persist_eval_traces(
        store,
        &profile,
        &TraceMeta {
            trace_id: &trace_id,
            run_id: "",
            source_kind: "REALTIME_LAB",
            category: "REALTIME",
            expected_pass: None,
            raw_text: &body.text,
            input_id: &trace_id,
            granularity,
            use_rogue_mask,
            embedding_ms: scored.embedding_ms,
            created_at_ms,
        },
        &scored.chunks,
        &scored.vectors,
        &scored,
    )
    .await
    {
        return response;
    }
    let chunks: Vec<Value> = scored
        .chunks
        .iter()
        .zip(scored.batch.chunks.iter())
        .enumerate()
        .map(|(index, (chunk, eval))| {
            json!({
                "chunk_index": index,
                "chunk_strategy": chunk.strategy_tag,
                "chunk_text": chunk.text,
                "chunk_passed": eval.chunk_passed,
                "evaluated_dims": eval.evaluated_dims,
                "failed_dims_count": eval.failed_dims_count,
                "underflow_count": eval.underflow_count,
                "overflow_count": eval.overflow_count,
                "max_violation_delta": eval.max_violation_delta,
                "mean_abs_delta_vs_mean": eval.mean_abs_delta_vs_mean,
                "dimensions": eval.dimensions.iter().map(dim_dto).collect::<Vec<_>>(),
            })
        })
        .collect();
    let mut response = Json(json!({
        "trace_id": trace_id,
        "profile_id": profile.profile_id,
        "policy_id": profile.policy_id,
        "eval_granularity": granularity_name(granularity),
        "use_rogue_mask": use_rogue_mask,
        "overall_passed": scored.batch.overall_passed,
        "full_text_passed": scored.batch.full_text_passed,
        "all_chunks_passed": scored.batch.all_chunks_passed,
        "embedding_ms": scored.embedding_ms,
        "eval_latency_ns": scored.eval_latency_ns,
        "chunks": chunks,
    }))
    .into_response();
    stamp_fhv1_headers(
        response.headers_mut(),
        &trace_id,
        if scored.batch.overall_passed {
            "PASS"
        } else {
            "BREACH"
        },
    );
    response
}

async fn list_benchmarks(State(state): State<Arc<ProxyAppState>>) -> Response {
    let Some(store) = state.fhv1_store.as_deref() else {
        return Json(json!([])).into_response();
    };
    match store.list_benchmark_runs().await {
        Ok(runs) => Json(runs.iter().map(run_summary).collect::<Vec<_>>()).into_response(),
        Err(err) => store_error(err),
    }
}

async fn get_benchmark(
    State(state): State<Arc<ProxyAppState>>,
    Path(run_id): Path<String>,
) -> Response {
    let store = match require_store(&state) {
        Ok(store) => store,
        Err(response) => return response,
    };
    match store.get_benchmark_run(&run_id).await {
        Ok(Some(run)) => {
            let parsed =
                serde_json::from_str::<Value>(&run.summary_metrics_json).unwrap_or(Value::Null);
            let mut body = run_summary(&run);
            body["summary_metrics"] = parsed;
            Json(body).into_response()
        }
        Ok(None) => error_response(StatusCode::NOT_FOUND, "fhv1 benchmark run was not found"),
        Err(err) => store_error(err),
    }
}

async fn run_benchmark(
    State(state): State<Arc<ProxyAppState>>,
    Json(body): Json<BenchmarkBody>,
) -> Response {
    let store = match require_store(&state) {
        Ok(store) => store,
        Err(response) => return response,
    };
    let profile = match store.get_profile(&body.profile_id).await {
        Ok(Some(profile)) => profile,
        Ok(None) => return error_response(StatusCode::NOT_FOUND, "fhv1 profile was not found"),
        Err(err) => return store_error(err),
    };
    let prompts = match load_benchmark_prompts(&body) {
        Ok(prompts) => prompts,
        Err(response) => return response,
    };
    let samples = match store.list_samples_for_profile(&profile.profile_id).await {
        Ok(samples) => samples,
        Err(err) => return store_error(err),
    };
    let mut banned = std::collections::BTreeSet::new();
    for sample in &samples {
        banned.insert(digest_text(&sample.raw_text));
        banned.insert(digest_text(&nfkc_lower(&sample.raw_text)));
    }
    for prompt in &prompts {
        if banned.contains(&digest_text(&prompt.text))
            || banned.contains(&digest_text(&nfkc_lower(&prompt.text)))
        {
            return error_response(StatusCode::CONFLICT, "calibration overlap fail-closed");
        }
    }
    let granularity = match parse_granularity(body.eval_granularity.as_deref()) {
        Ok(granularity) => granularity,
        Err(response) => return response,
    };
    let use_rogue_mask = body.use_rogue_mask.unwrap_or(false);
    let mut traces = Vec::new();
    let mut passed_flags = Vec::new();
    let run_id = new_trace_id("bench");
    let created_at_ms = now_ms();
    for prompt in &prompts {
        let scored = match evaluate_fhv1_input(
            state.embedder.as_ref(),
            &profile,
            &Fhv1EvaluateSpec {
                raw_text: &prompt.text,
                granularity,
                normalize_embeddings: profile.normalize,
                use_rogue_mask,
            },
        )
        .await
        {
            Ok(scored) => scored,
            Err(err) => return error_response(StatusCode::BAD_GATEWAY, &err),
        };
        passed_flags.push(scored.batch.overall_passed);
        let prompt_trace_id = format!("{run_id}-{}", prompt.input_id);
        push_traces(
            &mut traces,
            &profile,
            &TraceMeta {
                trace_id: &prompt_trace_id,
                run_id: &run_id,
                source_kind: "BENCHMARK",
                category: &prompt.category,
                expected_pass: Some(prompt.expected_pass),
                raw_text: &prompt.text,
                input_id: &prompt.input_id,
                granularity,
                use_rogue_mask,
                embedding_ms: scored.embedding_ms,
                created_at_ms,
            },
            &scored.chunks,
            &scored.vectors,
            &scored,
        );
    }
    if let Err(err) = store.append_audit_traces(&traces).await {
        return store_error(err);
    }
    let summary = confusion_summary(&prompts, &passed_flags);
    let run = Fhv1BenchmarkRun {
        run_id: run_id.clone(),
        profile_id: profile.profile_id.clone(),
        policy_id: profile.policy_id.clone(),
        dataset_name: body
            .dataset_path
            .clone()
            .unwrap_or_else(|| "samples".to_string()),
        dataset_sha256: digest_bytes(&serde_json::to_vec(&prompts).unwrap_or_default()),
        eval_granularity: granularity_name(granularity).to_string(),
        use_rogue_mask,
        total_inputs: prompts.len() as u64,
        total_chunks: traces.len() as u64,
        summary_metrics_json: summary.to_string(),
        created_at_ms,
    };
    if let Err(err) = store.save_benchmark_run(&run).await {
        return store_error(err);
    }
    let mut body = run_summary(&run);
    body["summary_metrics"] = summary;
    Json(body).into_response()
}

async fn list_traces(
    State(state): State<Arc<ProxyAppState>>,
    Query(query): Query<TraceQuery>,
) -> Response {
    let Some(store) = state.fhv1_store.as_deref() else {
        return Json(json!({"page": 1, "page_size": 50, "total": 0, "rows": []})).into_response();
    };
    let passed = match query.passed.as_deref() {
        None => None,
        Some("true") => Some(true),
        Some("false") => Some(false),
        Some(other) => {
            return error_response(
                StatusCode::BAD_REQUEST,
                &format!("unknown passed filter {other}"),
            )
        }
    };
    let request = Fhv1TraceQuery {
        trace_id: query.trace_id,
        run_id: query.run_id,
        profile_id: query.profile_id,
        source_kind: query.source_kind,
        category: query.category,
        passed,
        page: query.page.unwrap_or(1),
        page_size: query.page_size.unwrap_or(50),
    };
    match store.query_audit_trace_summaries(&request).await {
        Ok(page) => Json(json!({
            "page": page.page,
            "page_size": page.page_size,
            "total": page.total,
            "rows": page.rows,
        }))
        .into_response(),
        Err(err) => store_error(err),
    }
}

async fn get_trace(
    State(state): State<Arc<ProxyAppState>>,
    Path(trace_id): Path<String>,
) -> Response {
    let store = match require_store(&state) {
        Ok(store) => store,
        Err(response) => return response,
    };
    match store.get_trace_drilldown(&trace_id).await {
        Ok(Some(drill)) => {
            let chunks: Vec<Value> = drill
                .chunks
                .iter()
                .map(|chunk| {
                    json!({
                        "chunk_index": chunk.trace.chunk_index,
                        "chunk_strategy": chunk.trace.chunk_strategy,
                        "chunk_text": chunk.trace.chunk_text,
                        "chunk_passed": chunk.trace.chunk_passed,
                        "input_vector": chunk.trace.input_vector.as_ref().as_slice(),
                        "dimensions": chunk.dimensions.iter().map(dim_dto).collect::<Vec<_>>(),
                    })
                })
                .collect();
            Json(json!({
                "trace_id": drill.trace_id,
                "profile_id": drill.profile.profile_id,
                "chunks": chunks,
            }))
            .into_response()
        }
        Ok(None) => error_response(StatusCode::NOT_FOUND, "fhv1 trace was not found"),
        Err(err) => store_error(err),
    }
}

#[derive(Debug, Deserialize)]
struct ProfileQuery {
    metric: Option<String>,
    p25: Option<f64>,
    p75: Option<f64>,
    p90: Option<f64>,
}

#[derive(Debug, Deserialize)]
struct CalibrateBody {
    policy_id: String,
    texts: Vec<String>,
    normalize: Option<bool>,
    use_rogue_mask_default: Option<bool>,
}

#[derive(Debug, Deserialize)]
struct ExportQuery {
    format: Option<String>,
    max_rows: Option<usize>,
}

#[derive(Debug, Deserialize)]
struct EvaluateBody {
    profile_id: String,
    text: String,
    eval_granularity: Option<String>,
    use_rogue_mask: Option<bool>,
}

#[derive(Debug, Clone, Deserialize, serde::Serialize)]
struct BenchmarkPrompt {
    input_id: String,
    category: String,
    expected_pass: bool,
    text: String,
}

#[derive(Debug, Deserialize)]
struct BenchmarkBody {
    profile_id: String,
    dataset_path: Option<String>,
    samples: Option<Vec<BenchmarkPrompt>>,
    eval_granularity: Option<String>,
    use_rogue_mask: Option<bool>,
}

#[derive(Debug, Deserialize)]
struct TraceQuery {
    trace_id: Option<String>,
    run_id: Option<String>,
    profile_id: Option<String>,
    source_kind: Option<String>,
    category: Option<String>,
    passed: Option<String>,
    page: Option<u32>,
    page_size: Option<u32>,
}

fn load_benchmark_prompts(body: &BenchmarkBody) -> Result<Vec<BenchmarkPrompt>, Response> {
    if let Some(samples) = &body.samples {
        if samples.is_empty() {
            return Err(error_response(
                StatusCode::BAD_REQUEST,
                "benchmark samples are empty",
            ));
        }
        return Ok(samples.clone());
    }
    let Some(path) = body.dataset_path.as_deref() else {
        return Err(error_response(
            StatusCode::BAD_REQUEST,
            "benchmark run requires samples or dataset_path",
        ));
    };
    let text = std::fs::read_to_string(path)
        .map_err(|err| error_response(StatusCode::BAD_REQUEST, &format!("read dataset: {err}")))?;
    let mut prompts = Vec::new();
    for (index, line) in text.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let prompt: BenchmarkPrompt = serde_json::from_str(trimmed).map_err(|err| {
            error_response(
                StatusCode::BAD_REQUEST,
                &format!("dataset line {}: {err}", index + 1),
            )
        })?;
        prompts.push(prompt);
    }
    if prompts.is_empty() {
        return Err(error_response(
            StatusCode::BAD_REQUEST,
            "benchmark dataset is empty",
        ));
    }
    Ok(prompts)
}

fn confusion_summary(prompts: &[BenchmarkPrompt], passed: &[bool]) -> Value {
    let mut tp = 0u64;
    let mut tn = 0u64;
    let mut fp = 0u64;
    let mut fn_ = 0u64;
    for (prompt, flag) in prompts.iter().zip(passed.iter()) {
        match (prompt.expected_pass, *flag) {
            (true, true) => tp += 1,
            (true, false) => fn_ += 1,
            (false, false) => tn += 1,
            (false, true) => fp += 1,
        }
    }
    json!({"confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn_}})
}

fn profile_summary(profile: &Fhv1ProfileRecord) -> Value {
    json!({
        "profile_id": profile.profile_id,
        "policy_id": profile.policy_id,
        "version": profile.version,
        "polarity": profile.polarity,
        "normalize": profile.normalize,
        "use_rogue_mask_default": profile.use_rogue_mask_default,
        "sample_count": profile.sample_count,
        "model_id": profile.model_id,
        "source_dtype": profile.source_dtype,
        "augmented_llm": profile.augmented_llm,
        "created_at_ms": profile.created_at_ms,
    })
}

fn run_summary(run: &Fhv1BenchmarkRun) -> Value {
    json!({
        "run_id": run.run_id,
        "profile_id": run.profile_id,
        "policy_id": run.policy_id,
        "dataset_name": run.dataset_name,
        "dataset_sha256": hex_bytes(&run.dataset_sha256),
        "eval_granularity": run.eval_granularity,
        "use_rogue_mask": run.use_rogue_mask,
        "total_inputs": run.total_inputs,
        "total_chunks": run.total_chunks,
        "created_at_ms": run.created_at_ms,
    })
}

fn dim_dto(dim: &sf_kernels::Fhv1DimComparison) -> Value {
    json!({
        "observed": dim.observed,
        "observed_bits_hex": format!("0x{:016x}", dim.observed_bits),
        "min": dim.min,
        "max": dim.max,
        "mean": dim.mean,
        "status": match dim.status {
            DimBoundStatus::InBounds => "in_bounds",
            DimBoundStatus::Underflow => "underflow",
            DimBoundStatus::Overflow => "overflow",
            DimBoundStatus::PrunedRogue => "pruned_rogue",
        },
        "violation_delta": dim.violation_delta,
        "delta_vs_mean": dim.delta_vs_mean,
        "norm_pos": dim.norm_pos,
    })
}

struct TraceMeta<'a> {
    trace_id: &'a str,
    run_id: &'a str,
    source_kind: &'a str,
    category: &'a str,
    expected_pass: Option<bool>,
    raw_text: &'a str,
    input_id: &'a str,
    granularity: Fhv1EvalGranularity,
    use_rogue_mask: bool,
    embedding_ms: f64,
    created_at_ms: i64,
}

async fn persist_eval_traces(
    store: &Fhv1Store,
    profile: &Fhv1ProfileRecord,
    meta: &TraceMeta<'_>,
    chunks: &[crate::fhv1_pipeline::ExpandedChunk],
    vectors: &[Box<[f64; DIM]>],
    scored: &crate::fhv1_pipeline::Fhv1EvaluatedInput,
) -> Result<(), Response> {
    let mut traces = Vec::new();
    push_traces(&mut traces, profile, meta, chunks, vectors, scored);
    store
        .append_audit_traces(&traces)
        .await
        .map_err(store_error)
}

fn push_traces(
    traces: &mut Vec<Fhv1AuditTrace>,
    profile: &Fhv1ProfileRecord,
    meta: &TraceMeta<'_>,
    chunks: &[crate::fhv1_pipeline::ExpandedChunk],
    vectors: &[Box<[f64; DIM]>],
    scored: &crate::fhv1_pipeline::Fhv1EvaluatedInput,
) {
    for (index, chunk) in chunks.iter().enumerate() {
        let eval = &scored.batch.chunks[index];
        traces.push(Fhv1AuditTrace {
            trace_id: meta.trace_id.to_string(),
            run_id: meta.run_id.to_string(),
            source_kind: meta.source_kind.to_string(),
            profile_id: profile.profile_id.clone(),
            policy_id: profile.policy_id.clone(),
            category: meta.category.to_string(),
            expected_pass: meta.expected_pass,
            input_id: meta.input_id.to_string(),
            raw_text: meta.raw_text.to_string(),
            eval_granularity: granularity_name(meta.granularity).to_string(),
            use_rogue_mask: meta.use_rogue_mask,
            chunk_index: u32::try_from(index).unwrap_or(u32::MAX),
            chunk_strategy: chunk.strategy_tag.to_string(),
            chunk_text: chunk.text.clone(),
            input_vector: vectors[index].clone(),
            chunk_passed: eval.chunk_passed,
            overall_passed: scored.batch.overall_passed,
            full_text_passed: scored.batch.full_text_passed,
            all_chunks_passed: scored.batch.all_chunks_passed,
            evaluated_dims: eval.evaluated_dims,
            failed_dims_count: eval.failed_dims_count,
            underflow_count: eval.underflow_count,
            overflow_count: eval.overflow_count,
            max_violation_delta: eval.max_violation_delta,
            mean_abs_delta_vs_mean: eval.mean_abs_delta_vs_mean,
            eval_latency_ns: scored.eval_latency_ns,
            embedding_ms: meta.embedding_ms,
            created_at_ms: meta.created_at_ms,
        });
    }
}

fn require_store(state: &ProxyAppState) -> Result<&Fhv1Store, Response> {
    state.fhv1_store.as_deref().ok_or_else(|| {
        error_response(
            StatusCode::SERVICE_UNAVAILABLE,
            "fhv1 store is not configured",
        )
    })
}

fn attachment(bytes: Vec<u8>, content_type: &str, filename: &str) -> Response {
    let mut response = (StatusCode::OK, bytes).into_response();
    let headers = response.headers_mut();
    if let Ok(value) = HeaderValue::from_str(content_type) {
        headers.insert(header::CONTENT_TYPE, value);
    }
    if let Ok(value) = HeaderValue::from_str(&format!("attachment; filename=\"{filename}\"")) {
        headers.insert(header::CONTENT_DISPOSITION, value);
    }
    response
}

fn error_response(status: StatusCode, message: &str) -> Response {
    (status, Json(json!({"error": {"message": message}}))).into_response()
}

fn store_error(err: impl ToString) -> Response {
    error_response(StatusCode::INTERNAL_SERVER_ERROR, &err.to_string())
}

fn parse_granularity(text: Option<&str>) -> Result<Fhv1EvalGranularity, Response> {
    match text.unwrap_or("clauses") {
        "full_only" => Ok(Fhv1EvalGranularity::FullOnly),
        "clauses" => Ok(Fhv1EvalGranularity::Clauses),
        "full_mirror" => Ok(Fhv1EvalGranularity::FullMirror),
        other => Err(error_response(
            StatusCode::BAD_REQUEST,
            &format!("unknown eval_granularity {other}"),
        )),
    }
}

fn granularity_name(granularity: Fhv1EvalGranularity) -> &'static str {
    match granularity {
        Fhv1EvalGranularity::FullOnly => "full_only",
        Fhv1EvalGranularity::Clauses => "clauses",
        Fhv1EvalGranularity::FullMirror => "full_mirror",
    }
}

fn parse_metric(text: Option<&str>) -> Result<MovementMetric, Response> {
    match text.unwrap_or("span") {
        "variance" => Ok(MovementMetric::Variance),
        "std_dev" => Ok(MovementMetric::StdDev),
        "span" => Ok(MovementMetric::Span),
        other => Err(error_response(
            StatusCode::BAD_REQUEST,
            &format!("unknown metric {other}"),
        )),
    }
}

fn nfkc_lower(text: &str) -> String {
    use unicode_normalization::UnicodeNormalization;
    text.nfkc().collect::<String>().to_lowercase()
}

fn digest_text(text: &str) -> [u8; 32] {
    digest_bytes(text.as_bytes())
}

fn digest_bytes(bytes: &[u8]) -> [u8; 32] {
    let hashed = Sha256::digest(bytes);
    let mut out = [0u8; 32];
    out.copy_from_slice(hashed.as_slice());
    out
}

fn hex_bytes(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn now_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|elapsed| i64::try_from(elapsed.as_millis()).unwrap_or(i64::MAX))
        .unwrap_or(0)
}

fn new_trace_id(prefix: &str) -> String {
    static TRACE_SEQ: AtomicU64 = AtomicU64::new(0);
    let seq = TRACE_SEQ.fetch_add(1, Ordering::Relaxed);
    format!("{prefix}-{}-{seq}", now_ms())
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;
    use std::sync::Arc;

    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use serde_json::Value;
    use sf_kernels::{AlignedVec1024, DIM};
    use sf_storage::{Fhv1AuditTrace, Fhv1Store, HotRegistry};
    use tower::ServiceExt;

    use crate::{router, MockBatchEmbedder, MockUpstreamForwarder, ProxyAppState};

    fn sample_trace(trace_id: &str, created_at_ms: i64) -> Fhv1AuditTrace {
        let vec = vec![0.0; DIM].into_boxed_slice().try_into().expect("dim");
        Fhv1AuditTrace {
            trace_id: trace_id.to_string(),
            run_id: String::new(),
            source_kind: "REALTIME_LAB".to_string(),
            profile_id: "python-v1-test".to_string(),
            policy_id: "python".to_string(),
            category: "REALTIME".to_string(),
            expected_pass: None,
            input_id: trace_id.to_string(),
            raw_text: "hello".to_string(),
            eval_granularity: "full_only".to_string(),
            use_rogue_mask: false,
            chunk_index: 0,
            chunk_strategy: "full_doc".to_string(),
            chunk_text: "hello".to_string(),
            input_vector: vec,
            chunk_passed: true,
            overall_passed: true,
            full_text_passed: true,
            all_chunks_passed: true,
            evaluated_dims: 1024,
            failed_dims_count: 0,
            underflow_count: 0,
            overflow_count: 0,
            max_violation_delta: 0.0,
            mean_abs_delta_vs_mean: 0.0,
            eval_latency_ns: 10,
            embedding_ms: 1.0,
            created_at_ms,
        }
    }

    #[tokio::test]
    async fn list_traces_pushes_down_trace_id_query_param() {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("fhv1-api-trace-id-{}-{nanos}", std::process::id()));
        std::fs::create_dir_all(&path).expect("temp dir");
        let store = Arc::new(Fhv1Store::new(path.to_str().expect("utf8")));
        store
            .append_audit_traces(&[
                sample_trace("trace-keep", 100),
                sample_trace("trace-drop", 200),
            ])
            .await
            .expect("append traces");

        let app = router(Arc::new(ProxyAppState {
            registry: Arc::new(HotRegistry::from_locks([])),
            embedder: Arc::new(MockBatchEmbedder {
                pass_vector: AlignedVec1024::zeros(),
                breach_vector: AlignedVec1024::zeros(),
                centroids: HashMap::new(),
            }),
            upstream: Arc::new(MockUpstreamForwarder),
            mock_upstream: Arc::new(MockUpstreamForwarder),
            default_domain: "python".to_string(),
            max_telemetry_coords: 4,
            fhv1_store: Some(store),
        }));

        let response = app
            .oneshot(
                Request::builder()
                    .method("GET")
                    .uri("/api/v1/fhv1/traces?trace_id=trace-keep")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::OK);
        let bytes = response
            .into_body()
            .collect()
            .await
            .expect("body")
            .to_bytes();
        let payload: Value = serde_json::from_slice(&bytes).expect("json");
        assert_eq!(payload["total"], 1);
        let rows = payload["rows"].as_array().expect("rows");
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0]["trace_id"], "trace-keep");
        let _ = std::fs::remove_dir_all(&path);
    }
}
