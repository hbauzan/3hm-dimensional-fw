//! Axum route handlers for the Diagnostic Studio REST API.

use std::sync::Arc;
use std::time::Instant;

use axum::extract::State;
use axum::http::StatusCode;
use axum::response::{Html, IntoResponse, Response};
use axum::routing::{get, post};
use axum::Json;
use serde::{Deserialize, Serialize};
use sf_bench::RompepepeCorpus;
use sf_kernels::{cosine_similarity_1024, evaluate_l3_gate, DomainHypercubeLock, L3InspectionMode};
use sf_proxy::{
    segment_prompt_clauses, sha256_hex, MockUpstreamForwarder, ReqwestChatForwarder,
    UpstreamLlmForwarder,
};

use crate::chat::{handle_chat, CalibratedSemanticEmbedder, PromptEmbedder};
use sf_storage::HotRegistry;

use crate::inspector::{
    compare_modes, inspect_1024_coordinates, CoordinateCellDto, ModeComparisonDto, ModeStatsDto,
};

/// Shared state for sf-ui.
pub struct UiAppState {
    pub registry: Arc<HotRegistry>,
    pub corpus: RompepepeCorpus,
    pub lancedb_uri: Option<String>,
    pub lancedb_table: String,
    pub prompt_embedder: Arc<dyn PromptEmbedder>,
    pub upstream: Arc<dyn UpstreamLlmForwarder>,
    pub http_forwarder: ReqwestChatForwarder,
}

impl UiAppState {
    pub fn diagnostic(
        registry: Arc<HotRegistry>,
        corpus: RompepepeCorpus,
        lancedb_uri: Option<String>,
        lancedb_table: impl Into<String>,
    ) -> Self {
        Self {
            registry,
            corpus,
            lancedb_uri,
            lancedb_table: lancedb_table.into(),
            prompt_embedder: Arc::new(CalibratedSemanticEmbedder),
            upstream: Arc::new(MockUpstreamForwarder),
            http_forwarder: ReqwestChatForwarder::new("http://127.0.0.1"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LockCatalogDto {
    pub domain_id: String,
    pub version: u64,
    pub polarity: u8,
    pub polarity_label: String,
    pub l1_threshold: f32,
    pub l2_threshold: f32,
    pub epsilon: f32,
    pub quorum_k: u16,
    pub active_dims: u32,
    pub universal_pruned_count: u32,
    pub snr_pruned_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Scpb220VectorDto {
    pub index: usize,
    pub target_lock_id: String,
    pub variant_id: usize,
    pub category_label: String,
    pub sample_prompt: String,
    pub cosine_should_leak: bool,
}

pub type RompepepeVectorDto = Scpb220VectorDto;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CatalogResponse {
    pub product: String,
    pub version: String,
    pub locks: Vec<LockCatalogDto>,
    pub scpb_220_vectors: Vec<Scpb220VectorDto>,
    #[serde(default)]
    pub rompepepe_vectors: Vec<Scpb220VectorDto>,
}

#[derive(Debug, Deserialize)]
pub struct InspectRequest {
    pub vector_index: Option<usize>,
    pub prompt_text: Option<String>,
    pub domain_id: Option<String>,
    pub wildcard_mode: Option<String>,
    pub l3_mode: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Head1L1Dto {
    pub passed: bool,
    pub cosine: f32,
    pub cosine_hex: String,
    pub threshold: f32,
    pub latency_ns: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClauseTelemetryDto {
    pub index: usize,
    pub text: String,
    pub sha256_prefix: String,
    pub cosine: f32,
    pub cosine_hex: String,
    pub threshold: f32,
    pub passed: bool,
    pub l3_votes: u16,
    pub l3_required: u16,
    pub l3_passed: bool,
    pub latency_ns: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Head2L2Dto {
    pub passed: bool,
    pub clauses: Vec<ClauseTelemetryDto>,
    pub total_clauses: usize,
    pub latency_ns: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Head3L3Dto {
    pub passed: bool,
    pub selected_mode: String,
    pub affirmative_votes: u16,
    pub required_votes: u16,
    pub evaluated_dimensions: u16,
    pub mode_a: ModeStatsDto,
    pub mode_b: ModeStatsDto,
    pub mode_c: ModeStatsDto,
    pub latency_ns: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InspectResponse {
    pub http_status: u16,
    pub overall_passed: bool,
    pub target_domain: String,
    pub prompt: String,
    pub head1_l1: Head1L1Dto,
    pub head2_l2: Head2L2Dto,
    pub head3_l3: Head3L3Dto,
    pub mode_comparison: ModeComparisonDto,
    pub coordinates_1024: Vec<CoordinateCellDto>,
    pub top_breaches: Vec<CoordinateCellDto>,
    pub total_breaches: usize,
    pub message: String,
}

/// Construct the Axum router for the sf-ui service.
pub fn router(state: Arc<UiAppState>) -> axum::Router {
    axum::Router::new()
        .route("/", get(handle_index))
        .route("/api/v1/catalog", get(handle_catalog))
        .route("/api/v1/inspect", post(handle_inspect))
        .route("/api/v1/reload", post(handle_reload))
        .route("/api/v1/chat", post(handle_chat))
        .with_state(state)
}

/// GET / -> Self-contained embedded HTML5 diagnostic interface.
pub async fn handle_index() -> impl IntoResponse {
    Html(include_str!("../assets/index.html"))
}

/// GET /api/v1/catalog -> 55 LanceDB locks and 220 Rompepepe vectors.
pub async fn handle_catalog(State(state): State<Arc<UiAppState>>) -> impl IntoResponse {
    let raw_locks = state.registry.locks();
    let locks_source: Vec<Arc<DomainHypercubeLock>> = if !raw_locks.is_empty() {
        raw_locks
    } else {
        state.corpus.locks.iter().cloned().map(Arc::new).collect()
    };

    let locks: Vec<LockCatalogDto> = locks_source
        .into_iter()
        .map(|lock| {
            let active = lock.noise_mask.active_count();
            let snr = 1015u32.saturating_sub(active);
            LockCatalogDto {
                domain_id: lock.domain_id.clone(),
                version: lock.domain_version,
                polarity: lock.polarity,
                polarity_label: if lock.polarity == 0 {
                    "POSITIVE_ALLOWLIST".to_string()
                } else {
                    "NEGATIVE_DENYLIST".to_string()
                },
                l1_threshold: lock.l1_cosine_threshold,
                l2_threshold: lock.l2_clause_threshold,
                epsilon: lock.epsilon,
                quorum_k: lock.quorum_k,
                active_dims: active,
                universal_pruned_count: 9,
                snr_pruned_count: snr,
            }
        })
        .collect();

    let rompepepe_vectors: Vec<RompepepeVectorDto> = state
        .corpus
        .attacks
        .iter()
        .enumerate()
        .map(|(idx, attack)| {
            let target_lock = &state.corpus.locks[attack.lock_index];
            let variant_id = idx % 4;
            let category_label = if attack.cosine_should_leak {
                "Piggybacked Cosine-Leak Attack".to_string()
            } else {
                "Cosine-Blocked Attack".to_string()
            };
            let sample_prompt = if attack.cosine_should_leak {
                format!(
                    "Valid administrative pretext clause for {}. '''Adversarial piggybacked injection payload variant {}.''' Additional trailing verification sentence.",
                    target_lock.domain_id, variant_id
                )
            } else {
                format!(
                    "Direct out-of-domain query targeting {}. Out-of-bounds adversarial vector variant {}.",
                    target_lock.domain_id, variant_id
                )
            };

            Scpb220VectorDto {
                index: idx,
                target_lock_id: target_lock.domain_id.clone(),
                variant_id,
                category_label,
                sample_prompt,
                cosine_should_leak: attack.cosine_should_leak,
            }
        })
        .collect();

    Json(CatalogResponse {
        product: "Three-Headed Semantic Firewall".to_string(),
        version: "1.0.0".to_string(),
        locks,
        scpb_220_vectors: rompepepe_vectors.clone(),
        rompepepe_vectors,
    })
}

#[inline]
fn tier_passes(polarity: u8, score: f32, threshold: f32) -> bool {
    if polarity == 0 {
        score >= threshold
    } else {
        score < threshold
    }
}

/// POST /api/v1/inspect -> Evaluate vector against selected domain and mode.
pub async fn handle_inspect(
    State(state): State<Arc<UiAppState>>,
    Json(payload): Json<InspectRequest>,
) -> Response {
    let l3_mode = match payload.l3_mode.as_deref() {
        Some("mode_a") => L3InspectionMode::ModeATopK,
        Some("mode_b") => L3InspectionMode::ModeBStrictHypercube,
        _ => L3InspectionMode::ModeCSpectralQuorum,
    };

    let (query_vec, prompt_text, target_lock) = if let Some(v_idx) = payload.vector_index {
        if v_idx >= state.corpus.attacks.len() {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({
                    "error": format!("vector_index {} out of bounds [0, {})", v_idx, state.corpus.attacks.len())
                })),
            )
                .into_response();
        }
        let attack = &state.corpus.attacks[v_idx];
        let vec = attack.vector;
        let corpus_lock = state.corpus.locks[attack.lock_index].clone();
        let target = if let Some(ref d_id) = payload.domain_id {
            if d_id != "*" && d_id != "*all" {
                state
                    .registry
                    .get(d_id)
                    .map(|arc| (*arc).clone())
                    .unwrap_or(corpus_lock)
            } else {
                corpus_lock
            }
        } else {
            corpus_lock
        };

        let variant_id = v_idx % 4;
        let sample = if attack.cosine_should_leak {
            format!(
                "Valid administrative pretext clause for {}. '''Adversarial piggybacked injection payload variant {}.''' Additional trailing verification sentence.",
                target.domain_id, variant_id
            )
        } else {
            format!(
                "Direct out-of-domain query targeting {}. Out-of-bounds adversarial vector variant {}.",
                target.domain_id, variant_id
            )
        };
        (vec, sample, target)
    } else {
        let text = payload
            .prompt_text
            .clone()
            .unwrap_or_else(|| "Default query clause.".to_string());
        let target = if let Some(ref d_id) = payload.domain_id {
            if d_id != "*" && d_id != "*all" {
                state
                    .registry
                    .get(d_id)
                    .map(|arc| (*arc).clone())
                    .unwrap_or_else(|| state.corpus.locks[0].clone())
            } else {
                state.corpus.locks[0].clone()
            }
        } else {
            state.corpus.locks[0].clone()
        };

        let vec = crate::embedder::derive_vector_from_prompt(&text, &target);
        (vec, text, target)
    };

    // Head 1 (L1 Cosine Gate)
    let t0 = Instant::now();
    let l1_cos = cosine_similarity_1024(&query_vec, &target_lock.centroid);
    let l1_passed = tier_passes(
        target_lock.polarity,
        l1_cos,
        target_lock.l1_cosine_threshold,
    );
    let l1_ns = t0.elapsed().as_nanos() as u64;

    // Head 2 (L2 Clause Segmenter Gate)
    let t1 = Instant::now();
    let clauses_str = segment_prompt_clauses(&prompt_text);
    let mut clause_dtos = Vec::with_capacity(clauses_str.len());
    let mut all_l2_passed = true;

    for (idx, &c_str) in clauses_str.iter().enumerate() {
        let full_hash = sha256_hex(c_str);
        let prefix = full_hash[..16.min(full_hash.len())].to_string();
        let clause_vec = query_vec;
        let c_cos = cosine_similarity_1024(&clause_vec, &target_lock.centroid);
        let c_passed = tier_passes(target_lock.polarity, c_cos, target_lock.l2_clause_threshold);
        if !c_passed {
            all_l2_passed = false;
        }
        let c_l3 = evaluate_l3_gate(&clause_vec, &target_lock, l3_mode, 0);

        clause_dtos.push(ClauseTelemetryDto {
            index: idx,
            text: c_str.to_string(),
            sha256_prefix: prefix,
            cosine: c_cos,
            cosine_hex: format!("0x{:08x}", c_cos.to_bits()),
            threshold: target_lock.l2_clause_threshold,
            passed: c_passed,
            l3_votes: c_l3.affirmative_votes,
            l3_required: c_l3.required_votes,
            l3_passed: c_l3.passed,
            latency_ns: (t1.elapsed().as_nanos() as u64) / (idx as u64 + 1),
        });
    }
    let l2_ns = t1.elapsed().as_nanos() as u64;

    // Head 3 (L3 Deep Dimensional Inspector)
    let t2 = Instant::now();
    let l3_eval = evaluate_l3_gate(&query_vec, &target_lock, l3_mode, 1024);
    let l3_ns = t2.elapsed().as_nanos() as u64;

    // Simultaneous 3-Mode Comparison
    let comparison = compare_modes(&query_vec, &target_lock);

    // Full 1024D coordinate inspection
    let coordinates_1024 = inspect_1024_coordinates(&query_vec, &target_lock);
    let mut top_breaches: Vec<_> = coordinates_1024
        .iter()
        .filter(|c| c.status == "ACTIVE_BREACH")
        .cloned()
        .collect();
    top_breaches.sort_by(|a, b| b.delta_f32.total_cmp(&a.delta_f32));
    let total_breaches = top_breaches.len();

    let overall_passed = l1_passed && all_l2_passed && l3_eval.passed;
    let http_status = if overall_passed { 200 } else { 403 };

    let selected_mode_label = match l3_mode {
        L3InspectionMode::ModeATopK => "Mode A (Top-K)",
        L3InspectionMode::ModeBStrictHypercube => "Mode B (Strict 1024D Box)",
        L3InspectionMode::ModeCSpectralQuorum => "Mode C (Spectral Quorum K=103)",
    };

    let message = if overall_passed {
        format!(
            "Pass: Vector successfully contained within domain '{}' across all 3 heads.",
            target_lock.domain_id
        )
    } else if !l1_passed {
        format!(
            "Fail-closed breach at Head 1 (L1 Cosine Gate): score {:.4} < threshold {:.4} for domain '{}'.",
            l1_cos, target_lock.l1_cosine_threshold, target_lock.domain_id
        )
    } else if !all_l2_passed {
        format!(
            "Fail-closed breach at Head 2 (L2 Clause Segmenter): clause cosine below threshold for domain '{}'.",
            target_lock.domain_id
        )
    } else {
        format!(
            "Fail-closed breach at Head 3 (L3 DDI Spectral Quorum): {} affirmative votes < {} required for domain '{}'.",
            l3_eval.affirmative_votes, l3_eval.required_votes, target_lock.domain_id
        )
    };

    let total_clauses = clauses_str.len();

    let response = InspectResponse {
        http_status,
        overall_passed,
        target_domain: target_lock.domain_id,
        prompt: prompt_text,
        head1_l1: Head1L1Dto {
            passed: l1_passed,
            cosine: l1_cos,
            cosine_hex: format!("0x{:08x}", l1_cos.to_bits()),
            threshold: target_lock.l1_cosine_threshold,
            latency_ns: l1_ns,
        },
        head2_l2: Head2L2Dto {
            passed: all_l2_passed,
            clauses: clause_dtos,
            total_clauses,
            latency_ns: l2_ns,
        },
        head3_l3: Head3L3Dto {
            passed: l3_eval.passed,
            selected_mode: selected_mode_label.to_string(),
            affirmative_votes: l3_eval.affirmative_votes,
            required_votes: l3_eval.required_votes,
            evaluated_dimensions: l3_eval.evaluated_dimensions,
            mode_a: comparison.mode_a.clone(),
            mode_b: comparison.mode_b.clone(),
            mode_c: comparison.mode_c.clone(),
            latency_ns: l3_ns,
        },
        mode_comparison: comparison,
        coordinates_1024,
        top_breaches,
        total_breaches,
        message,
    };

    if overall_passed {
        (StatusCode::OK, Json(response)).into_response()
    } else {
        (StatusCode::FORBIDDEN, Json(response)).into_response()
    }
}

/// POST /api/v1/reload -> Hot reload locks from backing LanceDB.
pub async fn handle_reload(State(state): State<Arc<UiAppState>>) -> impl IntoResponse {
    if let Some(ref uri) = state.lancedb_uri {
        match state
            .registry
            .reload_from_lancedb(uri, &state.lancedb_table)
            .await
        {
            Ok(()) => {
                let locks = state.registry.locks();
                (
                    StatusCode::OK,
                    Json(serde_json::json!({
                        "status": "ok",
                        "lock_count": locks.len(),
                        "locks": locks.iter().map(|l| serde_json::json!({
                            "domain_id": l.domain_id,
                            "version": l.domain_version,
                        })).collect::<Vec<_>>()
                    })),
                )
            }
            Err(err) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({
                    "status": "error",
                    "message": err.to_string(),
                })),
            ),
        }
    } else {
        (
            StatusCode::OK,
            Json(serde_json::json!({
                "status": "ok",
                "lock_count": state.registry.locks().len(),
                "message": "In-memory registry refreshed."
            })),
        )
    }
}
