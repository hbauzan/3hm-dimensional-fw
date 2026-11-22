//! OpenAI-compatible proxy and gateway daemon.

mod cascade;
mod chat_api;
mod cors;
mod embedder;
mod env_config;
mod fhv1_api;
mod fhv1_eval;
mod fhv1_pipeline;
mod handler;
mod normalize;
mod normalizer;
mod routing;
mod segmenter;
mod tei;
mod telemetry;
mod upstream;

pub use cascade::{
    evaluate_pairwise_containment, evaluate_three_tier_cascade, mock_batch_requires_pairwise,
    pairwise_breach_envelope, sha256_hex, PairwiseBreach, PairwiseBreachEnvelope,
};
pub use chat_api::{
    apply_chat_overrides, chat_upstream_body, decode_chat_request, evaluate_chat_cascade,
    latest_chat_user_text, resolve_chat_upstream, ChatBreachDto, ChatMessageDto, ChatOverridesDto,
    ChatReject, ChatRequestDto, ChatUpstream, Tier1BreachDto, Tier2BreachDto, Tier3BreachDto,
    UpstreamConfigDto,
};
pub use cors::CorsAllow;
pub use embedder::{
    contains_permutation_noise, project_spectral_drift, BatchEmbedderClient, DualEmbedBatch,
    MockBatchEmbedder,
};
pub use env_config::{
    find_env_file, get_all_providers_env, get_provider_env, load_dotenv, parse_env_content,
    read_env_file_map, ProviderEnvInfo, UpstreamEnvCatalog,
};
pub use fhv1_eval::{
    attach_comparison, confusion_from_flags, confusion_json, forbid_surface, forbidden_digests,
    granularity_name, metrics_for, nfkc_lower, overlap_ids, parse_granularity,
    persist_benchmark_run, prepare_prompts, prepare_prompts_for, score_view, select_view,
    ConfusionCounts, Fhv1Prompt, PersistRequest, PreparedPrompt, PreparedView, RunMetrics,
    ScoredView, ALL_GRANULARITIES, CATEGORIES,
};
pub use fhv1_pipeline::{
    calibrate_fhv1_corpus, corpus_sha256, evaluate_fhv1_input, expand_for_granularity,
    expand_text_multi_granularity, strategy_tags, ExpandedChunk, Fhv1CalibrateSpec,
    Fhv1EvaluateSpec, Fhv1EvaluatedInput, EMBED_BATCH_SIZE,
};
pub use handler::{
    handle_api_v1_upstream_env, handle_v1_chat_completions, router, router_with_cors, ProxyAppState,
};
pub use normalize::{validate_and_normalize_f32_slice, validate_raw_f64_slice};
pub use normalizer::{InputNormalizer, NormalizedInput};
pub use segmenter::segment_prompt_clauses;
pub use tei::{embed_request, TeiGrpcEmbedder, TeiHttpEmbedder};
pub use telemetry::BreachErrorEnvelope;
pub use upstream::{MockUpstreamForwarder, ReqwestChatForwarder, UpstreamLlmForwarder};
