//! Re-exports the shared `fhv1` evaluation engine from `sf_proxy`.

pub use sf_proxy::{
    attach_comparison, confusion_from_flags, confusion_json, forbid_surface, forbidden_digests,
    granularity_name, metrics_for, nfkc_lower, overlap_ids, parse_granularity,
    persist_benchmark_run, prepare_prompts, prepare_prompts_for, score_view, select_view,
    ConfusionCounts, Fhv1Prompt, PersistRequest, PreparedPrompt, PreparedView, RunMetrics,
    ScoredView, ALL_GRANULARITIES, CATEGORIES,
};
