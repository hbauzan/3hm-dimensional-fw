//! `POST /api/v1/chat` on the gateway. Breach JSON is `ChatBreachDto`.
//! Overrides clone the lock for the request. The registry row stays as stored.

use std::sync::Arc;

use axum::extract::State;
use axum::http::{HeaderMap, HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::Json;
use bytes::Bytes;
use serde::{Deserialize, Serialize};
use sf_kernels::{
    cosine_similarity_1024, evaluate_l3_gate, AlignedVec1024, DomainHypercubeLock,
    L3InspectionMode, DIM,
};

use crate::cascade::{
    evaluate_pairwise_containment, mock_batch_requires_pairwise, pairwise_breach_envelope,
};
use crate::embedder::{contains_permutation_noise, project_spectral_drift};
use crate::handler::ProxyAppState;
use crate::upstream::ReqwestChatForwarder;

const DECISION_BREACH: &str = "BREACH";
const TIER_L1: &str = "L1_CENTROID_COSINE";
const TIER_L2: &str = "L2_CLAUSE_GATE";
const TIER_L3: &str = "L3_SPECTRAL_QUORUM";

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ChatMessageDto {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ChatOverridesDto {
    pub l1_threshold: Option<f32>,
    pub l2_threshold: Option<f32>,
    pub quorum_k: Option<u16>,
    pub epsilon: Option<f32>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct UpstreamConfigDto {
    pub provider: Option<String>,
    pub model: Option<String>,
    pub api_key: Option<String>,
    pub base_url: Option<String>,
    pub use_env: Option<bool>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ChatRequestDto {
    pub messages: Vec<ChatMessageDto>,
    pub domain_id: Option<String>,
    pub overrides: Option<ChatOverridesDto>,
    pub upstream: Option<UpstreamConfigDto>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tier1BreachDto {
    pub passed: bool,
    pub cosine: f32,
    pub threshold: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tier2BreachDto {
    pub passed: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub breached_clause_index: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub breached_clause_text: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub clause_cosine: Option<f32>,
    pub threshold: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tier3BreachDto {
    pub evaluated: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub passed: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub affirmative_votes: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub required_votes: Option<u16>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatBreachDto {
    pub decision: String,
    pub failing_tier: String,
    pub l1: Tier1BreachDto,
    pub l2: Tier2BreachDto,
    pub l3: Tier3BreachDto,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub clauses_skipped: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub normalizer_segmenter_us: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub embedding_inference_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub simd_gate_kernel_us: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub total_pipeline_ms: Option<f64>,
}

#[derive(Debug, Clone)]
pub struct ChatReject {
    pub status: StatusCode,
    pub message: String,
}

#[derive(Debug, Clone)]
pub enum ChatUpstream {
    Mock {
        model: String,
    },
    Http {
        model: String,
        base_url: String,
        api_key: Option<String>,
    },
}

impl ChatUpstream {
    pub fn model(&self) -> &str {
        match self {
            Self::Mock { model } | Self::Http { model, .. } => model,
        }
    }
}

/// Allowlist polarity `0` passes when `score >= threshold`.
/// Denylist polarity `1` passes when `score < threshold`.
fn tier_passes(polarity: u8, score: f32, threshold: f32) -> bool {
    if polarity == 0 {
        score >= threshold
    } else {
        score < threshold
    }
}

pub fn latest_chat_user_text(messages: &[ChatMessageDto]) -> Option<&str> {
    messages
        .iter()
        .rev()
        .find(|message| message.role == "user")
        .map(|message| message.content.trim())
        .filter(|text| !text.is_empty())
}

/// Clone `lock` and apply request overrides. The caller's registry value is untouched.
pub fn apply_chat_overrides(
    lock: &DomainHypercubeLock,
    overrides: &ChatOverridesDto,
) -> DomainHypercubeLock {
    let mut next = lock.clone();
    if let Some(threshold) = overrides.l1_threshold {
        next.l1_cosine_threshold = threshold;
    }
    if let Some(threshold) = overrides.l2_threshold {
        next.l2_clause_threshold = threshold;
    }
    if let Some(quorum_k) = overrides.quorum_k {
        let cap = u16::try_from(next.noise_mask.active_count())
            .unwrap_or(u16::MAX)
            .max(1);
        next.quorum_k = quorum_k.clamp(1, cap);
    }
    if let Some(epsilon) = overrides.epsilon {
        let previous = next.epsilon;
        for dim in 0..DIM {
            let lo = next.lo_dilated.data[dim] + previous;
            let hi = next.hi_dilated.data[dim] - previous;
            next.lo_dilated.data[dim] = lo - epsilon;
            next.hi_dilated.data[dim] = hi + epsilon;
        }
        next.epsilon = epsilon;
    }
    next
}

fn l1_dto(passed: bool, cosine: f32, threshold: f32) -> Tier1BreachDto {
    Tier1BreachDto {
        passed,
        cosine,
        threshold,
    }
}

fn l2_clear(threshold: f32) -> Tier2BreachDto {
    Tier2BreachDto {
        passed: true,
        breached_clause_index: None,
        breached_clause_text: None,
        clause_cosine: None,
        threshold,
    }
}

fn l3_skipped() -> Tier3BreachDto {
    Tier3BreachDto {
        evaluated: false,
        passed: None,
        affirmative_votes: None,
        required_votes: None,
    }
}

fn breach(
    failing_tier: &str,
    l1: Tier1BreachDto,
    l2: Tier2BreachDto,
    l3: Tier3BreachDto,
    clauses_skipped: Option<usize>,
) -> ChatBreachDto {
    ChatBreachDto {
        decision: DECISION_BREACH.to_string(),
        failing_tier: failing_tier.to_string(),
        l1,
        l2,
        l3,
        clauses_skipped,
        normalizer_segmenter_us: None,
        embedding_inference_ms: None,
        simd_gate_kernel_us: None,
        total_pipeline_ms: None,
    }
}

/// `Ok(ChatBreachDto)` releases the prompt with gate telemetry. `Err` is the playground breach card.
pub fn evaluate_chat_cascade(
    prompt_vec: &AlignedVec1024,
    clauses: &[&str],
    clause_vecs: &[AlignedVec1024],
    lock: &DomainHypercubeLock,
) -> Result<ChatBreachDto, Box<ChatBreachDto>> {
    let l1_cosine = cosine_similarity_1024(prompt_vec, &lock.centroid);
    let l1_threshold = lock.l1_cosine_threshold;
    if !tier_passes(lock.polarity, l1_cosine, l1_threshold) {
        return Err(Box::new(breach(
            TIER_L1,
            l1_dto(false, l1_cosine, l1_threshold),
            l2_clear(lock.l2_clause_threshold),
            l3_skipped(),
            Some(clauses.len()),
        )));
    }

    let l2_threshold = lock.l2_clause_threshold;
    let mut min_clause_cosine = f32::MAX;
    let mut min_clause_idx = 0;
    let mut min_affirmative_votes = u16::MAX;
    let mut required_votes = lock.quorum_k;

    for (idx, (clause, clause_vec)) in clauses.iter().zip(clause_vecs.iter()).enumerate() {
        let clause_cosine = cosine_similarity_1024(clause_vec, &lock.centroid);
        if clause_cosine < min_clause_cosine {
            min_clause_cosine = clause_cosine;
            min_clause_idx = idx;
        }
        if !tier_passes(lock.polarity, clause_cosine, l2_threshold) {
            let skipped = clauses.len().saturating_sub(1 + idx);
            return Err(Box::new(breach(
                TIER_L2,
                l1_dto(true, l1_cosine, l1_threshold),
                Tier2BreachDto {
                    passed: false,
                    breached_clause_index: Some(idx),
                    breached_clause_text: Some((*clause).to_string()),
                    clause_cosine: Some(clause_cosine),
                    threshold: l2_threshold,
                },
                l3_skipped(),
                Some(skipped),
            )));
        }

        let l3 = evaluate_l3_gate(clause_vec, lock, L3InspectionMode::ModeCSpectralQuorum, 0);
        if l3.affirmative_votes < min_affirmative_votes {
            min_affirmative_votes = l3.affirmative_votes;
        }
        required_votes = l3.required_votes;
        if !l3.passed {
            let skipped = clauses.len().saturating_sub(1 + idx);
            return Err(Box::new(breach(
                TIER_L3,
                l1_dto(true, l1_cosine, l1_threshold),
                l2_clear(l2_threshold),
                Tier3BreachDto {
                    evaluated: true,
                    passed: Some(false),
                    affirmative_votes: Some(l3.affirmative_votes),
                    required_votes: Some(l3.required_votes),
                },
                Some(skipped),
            )));
        }
    }

    Ok(ChatBreachDto {
        decision: "PASS".to_string(),
        failing_tier: "NONE".to_string(),
        l1: l1_dto(true, l1_cosine, l1_threshold),
        l2: Tier2BreachDto {
            passed: true,
            breached_clause_index: Some(min_clause_idx),
            breached_clause_text: None,
            clause_cosine: if min_clause_cosine == f32::MAX {
                None
            } else {
                Some(min_clause_cosine)
            },
            threshold: l2_threshold,
        },
        l3: Tier3BreachDto {
            evaluated: true,
            passed: Some(true),
            affirmative_votes: if min_affirmative_votes == u16::MAX {
                None
            } else {
                Some(min_affirmative_votes)
            },
            required_votes: Some(required_votes),
        },
        clauses_skipped: Some(0),
        normalizer_segmenter_us: None,
        embedding_inference_ms: None,
        simd_gate_kernel_us: None,
        total_pipeline_ms: None,
    })
}

fn nonempty(value: Option<&str>, default_value: &str) -> String {
    value
        .map(str::trim)
        .filter(|text| !text.is_empty())
        .unwrap_or(default_value)
        .to_string()
}

fn reject(status: StatusCode, message: impl Into<String>) -> ChatReject {
    ChatReject {
        status,
        message: message.into(),
    }
}

fn bearer_token(raw: Option<&str>) -> Result<Option<String>, ChatReject> {
    let Some(raw) = raw else {
        return Ok(None);
    };
    let token = raw.trim();
    if token.is_empty() {
        return Ok(None);
    }
    if HeaderValue::from_str(&format!("Bearer {token}")).is_err() {
        return Err(reject(
            StatusCode::BAD_REQUEST,
            "api_key contains characters that cannot be sent as an Authorization header",
        ));
    }
    Ok(Some(token.to_string()))
}

pub fn resolve_chat_upstream(cfg: Option<&UpstreamConfigDto>) -> Result<ChatUpstream, ChatReject> {
    let Some(cfg) = cfg else {
        return Ok(ChatUpstream::Mock {
            model: "mock".to_string(),
        });
    };
    let provider_name = cfg.provider.as_deref().unwrap_or("mock");
    if provider_name == "mock" {
        return Ok(ChatUpstream::Mock {
            model: nonempty(cfg.model.as_deref(), "mock"),
        });
    }

    let env_info = crate::env_config::get_provider_env(provider_name);
    let use_env = cfg.use_env.unwrap_or(false)
        || cfg
            .api_key
            .as_deref()
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .is_none();

    let effective_key = if use_env && !env_info.api_key.is_empty() {
        Some(env_info.api_key.clone())
    } else {
        cfg.api_key.clone()
    };

    let effective_base = cfg
        .base_url
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .unwrap_or(&env_info.base_url);

    let effective_model = cfg
        .model
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .unwrap_or(&env_info.model);

    match provider_name {
        "deepseek" | "openai" | "gemini" | "groq" | "ollama" => Ok(ChatUpstream::Http {
            model: effective_model.to_string(),
            base_url: effective_base.to_string(),
            api_key: bearer_token(effective_key.as_deref())?,
        }),
        other => Err(reject(
            StatusCode::BAD_REQUEST,
            format!("unsupported upstream provider '{other}'"),
        )),
    }
}

pub fn chat_upstream_body(model: &str, messages: &[ChatMessageDto]) -> Result<Bytes, String> {
    #[derive(Serialize)]
    struct Body<'a> {
        model: &'a str,
        messages: &'a [ChatMessageDto],
        stream: bool,
    }
    serde_json::to_vec(&Body {
        model,
        messages,
        stream: true,
    })
    .map(Bytes::from)
    .map_err(|err| err.to_string())
}

fn json_error(status: StatusCode, message: impl Into<String>) -> Response {
    (status, Json(serde_json::json!({ "error": message.into() }))).into_response()
}

fn resolve_lock(
    state: &ProxyAppState,
    domain_id: Option<&str>,
) -> Result<DomainHypercubeLock, ChatReject> {
    if let Some(id) = domain_id {
        return state
            .registry
            .get(id)
            .map(|lock| (*lock).clone())
            .ok_or_else(|| reject(StatusCode::NOT_FOUND, format!("unknown domain_id '{id}'")));
    }
    state
        .registry
        .locks()
        .into_iter()
        .next()
        .map(|lock| (*lock).clone())
        .ok_or_else(|| reject(StatusCode::SERVICE_UNAVAILABLE, "no domain lock is loaded"))
}

pub async fn handle_api_v1_chat(
    State(state): State<Arc<ProxyAppState>>,
    Json(payload): Json<ChatRequestDto>,
) -> Response {
    let Some(user_text) = latest_chat_user_text(&payload.messages) else {
        return json_error(StatusCode::BAD_REQUEST, "missing user message");
    };
    let user_text = user_text.to_string();

    let mut lock = match resolve_lock(&state, payload.domain_id.as_deref()) {
        Ok(lock) => lock,
        Err(reject) => return json_error(reject.status, reject.message),
    };
    if let Some(overrides) = payload.overrides.as_ref() {
        lock = apply_chat_overrides(&lock, overrides);
    }

    let pipeline_start = std::time::Instant::now();

    let t_norm_start = std::time::Instant::now();
    let normalized = crate::normalizer::InputNormalizer::normalize(&user_text);
    let clauses = normalized.segment_all_clauses();
    let normalizer_segmenter_us = t_norm_start.elapsed().as_micros() as u64;

    if clauses.is_empty() {
        return json_error(StatusCode::BAD_REQUEST, "prompt produced no clauses");
    }
    let mut batch = Vec::with_capacity(1 + clauses.len());
    batch.push(normalized.text.as_str());
    batch.extend(clauses.iter().copied());

    let t_embed_start = std::time::Instant::now();
    let mut vectors = match state.embedder.embed_batch_f32(&batch).await {
        Ok(vectors) if vectors.len() == batch.len() => vectors,
        Ok(_) => {
            return json_error(
                StatusCode::FORBIDDEN,
                "Fail-closed: embedder returned mismatched batch vector count.",
            );
        }
        Err(err) => {
            return json_error(
                StatusCode::FORBIDDEN,
                format!("Fail-closed: embedding subsystem error: {err}"),
            );
        }
    };
    let embedding_inference_ms = t_embed_start.elapsed().as_secs_f64() * 1000.0;

    if batch.iter().any(|text| contains_permutation_noise(text)) {
        let drifted = project_spectral_drift(&lock);
        for (idx, text) in batch.iter().enumerate() {
            if contains_permutation_noise(text) {
                vectors[idx] = drifted;
            }
        }
    }

    let t_simd_start = std::time::Instant::now();
    let mut gate_dto = match evaluate_chat_cascade(&vectors[0], &clauses, &vectors[1..], &lock) {
        Ok(dto) => dto,
        Err(mut dto) => {
            let simd_gate_kernel_us = t_simd_start.elapsed().as_micros() as u64;
            let total_pipeline_ms = pipeline_start.elapsed().as_secs_f64() * 1000.0;
            dto.normalizer_segmenter_us = Some(normalizer_segmenter_us);
            dto.embedding_inference_ms = Some(embedding_inference_ms);
            dto.simd_gate_kernel_us = Some(simd_gate_kernel_us);
            dto.total_pipeline_ms = Some(total_pipeline_ms);
            let skipped = dto.clauses_skipped.unwrap_or(0);
            let mut res = (StatusCode::FORBIDDEN, Json(*dto)).into_response();
            let h = res.headers_mut();
            add_latency_headers(
                h,
                normalizer_segmenter_us,
                embedding_inference_ms,
                simd_gate_kernel_us,
                total_pipeline_ms,
                skipped,
            );
            return res;
        }
    };
    let simd_gate_kernel_us = t_simd_start.elapsed().as_micros() as u64;
    let total_pipeline_ms = pipeline_start.elapsed().as_secs_f64() * 1000.0;
    gate_dto.normalizer_segmenter_us = Some(normalizer_segmenter_us);
    gate_dto.embedding_inference_ms = Some(embedding_inference_ms);
    gate_dto.simd_gate_kernel_us = Some(simd_gate_kernel_us);
    gate_dto.total_pipeline_ms = Some(total_pipeline_ms);

    let enforce_pairwise = !state.embedder.is_mock() || mock_batch_requires_pairwise(&batch);
    if enforce_pairwise {
        let pairs = state.registry.pairwise_locks_for(&lock.domain_id);
        if let Err(breach) =
            evaluate_pairwise_containment(&vectors[0], &vectors[1..], &lock.domain_id, &pairs)
        {
            let mut res = (
                StatusCode::FORBIDDEN,
                Json(pairwise_breach_envelope(breach)),
            )
                .into_response();
            let h = res.headers_mut();
            add_latency_headers(
                h,
                normalizer_segmenter_us,
                embedding_inference_ms,
                simd_gate_kernel_us,
                total_pipeline_ms,
                0,
            );
            return res;
        }
    }

    let upstream = match resolve_chat_upstream(payload.upstream.as_ref()) {
        Ok(upstream) => upstream,
        Err(reject) => return json_error(reject.status, reject.message),
    };
    let bytes = match chat_upstream_body(upstream.model(), &payload.messages) {
        Ok(bytes) => bytes,
        Err(err) => return json_error(StatusCode::INTERNAL_SERVER_ERROR, err),
    };

    let forwarded = match upstream {
        ChatUpstream::Mock { .. } => {
            state
                .mock_upstream
                .forward_chat_completion(&HeaderMap::new(), bytes)
                .await
        }
        ChatUpstream::Http {
            base_url, api_key, ..
        } => {
            ReqwestChatForwarder::new(base_url.clone())
                .forward_dynamic(&base_url, api_key.as_deref(), bytes)
                .await
        }
    };

    match forwarded {
        Ok(mut response) => {
            let headers = response.headers_mut();
            headers.insert("x-sf-decision", HeaderValue::from_static("PASS"));
            if let Ok(value) = HeaderValue::from_str(&clauses.len().to_string()) {
                headers.insert("x-sf-clauses-evaluated", value);
            }
            add_latency_headers(
                headers,
                normalizer_segmenter_us,
                embedding_inference_ms,
                simd_gate_kernel_us,
                total_pipeline_ms,
                0,
            );
            if let Ok(json_str) = serde_json::to_string(&gate_dto) {
                if let Ok(val) = HeaderValue::from_str(&json_str) {
                    headers.insert("x-sf-telemetry", val);
                }
            }
            response
        }
        Err(err) => json_error(StatusCode::BAD_GATEWAY, err),
    }
}

pub(crate) fn add_latency_headers(
    headers: &mut HeaderMap,
    normalizer_segmenter_us: u64,
    embedding_inference_ms: f64,
    simd_gate_kernel_us: u64,
    total_pipeline_ms: f64,
    clauses_skipped: usize,
) {
    if let Ok(val) = HeaderValue::from_str(&normalizer_segmenter_us.to_string()) {
        headers.insert("x-sf-normalizer-segmenter-us", val);
    }
    if let Ok(val) = HeaderValue::from_str(&format!("{embedding_inference_ms:.3}")) {
        headers.insert("x-sf-embedding-inference-ms", val);
    }
    if let Ok(val) = HeaderValue::from_str(&simd_gate_kernel_us.to_string()) {
        headers.insert("x-sf-simd-gate-kernel-us", val);
    }
    if let Ok(val) = HeaderValue::from_str(&format!("{total_pipeline_ms:.3}")) {
        headers.insert("x-sf-total-pipeline-ms", val);
    }
    if let Ok(val) = HeaderValue::from_str(&clauses_skipped.to_string()) {
        headers.insert("x-sf-clauses-skipped", val);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sf_kernels::{LockSpec, NoiseBitmask1024, MAX_TOPK};

    fn sample_lock(epsilon: f32) -> DomainHypercubeLock {
        let lo = AlignedVec1024::zeros();
        let mut hi = AlignedVec1024::zeros();
        hi.data.fill(1.0);
        DomainHypercubeLock::from_spec(LockSpec {
            domain_id: "unit".to_string(),
            centroid: AlignedVec1024::zeros(),
            lo,
            hi,
            epsilon,
            noise_mask: NoiseBitmask1024::new_bge_m3_default(),
            top_k_indices: [0u16; MAX_TOPK],
            top_k_len: 1,
            quorum_k: 103,
            l1_cosine_threshold: 0.65,
            l2_clause_threshold: 0.65,
            polarity: 0,
            domain_version: 1,
        })
    }

    #[test]
    fn quorum_override_is_clamped_to_the_active_mask() {
        let source = sample_lock(0.0);
        let active = u16::try_from(source.noise_mask.active_count()).unwrap();
        assert_eq!(active, 1015);
        let high = apply_chat_overrides(
            &source,
            &ChatOverridesDto {
                l1_threshold: None,
                l2_threshold: None,
                quorum_k: Some(4_000),
                epsilon: None,
            },
        );
        let low = apply_chat_overrides(
            &source,
            &ChatOverridesDto {
                l1_threshold: None,
                l2_threshold: None,
                quorum_k: Some(0),
                epsilon: None,
            },
        );
        assert_eq!(high.quorum_k, active);
        assert_eq!(low.quorum_k, 1);
        assert_eq!(source.quorum_k, 103);
    }

    #[test]
    fn overrides_clone_thresholds_and_redilate_epsilon() {
        let source = sample_lock(0.05);
        let updated = apply_chat_overrides(
            &source,
            &ChatOverridesDto {
                l1_threshold: Some(0.5),
                l2_threshold: Some(0.4),
                quorum_k: Some(11),
                epsilon: Some(0.2),
            },
        );
        assert_eq!(source.epsilon.to_bits(), 0.05f32.to_bits());
        assert_eq!(source.l1_cosine_threshold.to_bits(), 0.65f32.to_bits());
        assert_eq!(source.quorum_k, 103);
        assert_eq!(updated.l1_cosine_threshold.to_bits(), 0.5f32.to_bits());
        assert_eq!(updated.l2_clause_threshold.to_bits(), 0.4f32.to_bits());
        assert_eq!(updated.quorum_k, 11);
        assert_eq!(updated.epsilon.to_bits(), 0.2f32.to_bits());
        let raw_lo = source.lo_dilated.data[0] + source.epsilon;
        let raw_hi = source.hi_dilated.data[0] - source.epsilon;
        assert_eq!(
            updated.lo_dilated.data[0].to_bits(),
            (raw_lo - 0.2).to_bits()
        );
        assert_eq!(
            updated.hi_dilated.data[0].to_bits(),
            (raw_hi + 0.2).to_bits()
        );
        assert_eq!(updated.domain_id, source.domain_id);
    }

    #[test]
    fn resolve_chat_upstream_handles_mock_and_env_defaults() {
        let none_upstream = resolve_chat_upstream(None).expect("mock default");
        assert_eq!(none_upstream.model(), "mock");

        let mock_upstream = resolve_chat_upstream(Some(&UpstreamConfigDto {
            provider: Some("mock".to_string()),
            model: Some("custom-mock".to_string()),
            api_key: None,
            base_url: None,
            use_env: None,
        }))
        .expect("mock");
        assert_eq!(mock_upstream.model(), "custom-mock");

        let gemini = resolve_chat_upstream(Some(&UpstreamConfigDto {
            provider: Some("gemini".to_string()),
            model: None,
            api_key: Some("explicit-key".to_string()),
            base_url: None,
            use_env: Some(false),
        }))
        .expect("gemini explicit");
        assert_eq!(gemini.model(), "gemini-3.8-flash");
        if let ChatUpstream::Http {
            base_url, api_key, ..
        } = gemini
        {
            assert_eq!(
                base_url,
                "https://generativelanguage.googleapis.com/v1beta/openai"
            );
            assert_eq!(api_key, Some("explicit-key".to_string()));
        } else {
            panic!("expected Http upstream");
        }
    }
}
