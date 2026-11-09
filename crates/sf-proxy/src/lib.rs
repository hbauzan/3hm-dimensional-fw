//! OpenAI-compatible proxy and gateway daemon.

mod cascade;
mod chat_api;
mod cors;
mod embedder;
mod env_config;
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
    apply_chat_overrides, chat_upstream_body, evaluate_chat_cascade, latest_chat_user_text,
    resolve_chat_upstream, ChatBreachDto, ChatMessageDto, ChatOverridesDto, ChatReject,
    ChatRequestDto, ChatUpstream, Tier1BreachDto, Tier2BreachDto, Tier3BreachDto,
    UpstreamConfigDto,
};
pub use cors::CorsAllow;
pub use embedder::{
    contains_permutation_noise, project_spectral_drift, BatchEmbedderClient, MockBatchEmbedder,
};
pub use env_config::{
    find_env_file, get_all_providers_env, get_provider_env, load_dotenv, parse_env_content,
    read_env_file_map, ProviderEnvInfo, UpstreamEnvCatalog,
};
pub use handler::{
    handle_api_v1_upstream_env, handle_v1_chat_completions, router, router_with_cors, ProxyAppState,
};
pub use normalize::validate_and_normalize_f32_slice;
pub use normalizer::{InputNormalizer, NormalizedInput};
pub use segmenter::segment_prompt_clauses;
pub use tei::{embed_request, TeiGrpcEmbedder, TeiHttpEmbedder};
pub use telemetry::BreachErrorEnvelope;
pub use upstream::{MockUpstreamForwarder, ReqwestChatForwarder, UpstreamLlmForwarder};
