//! SCPB-220 (Sub-Clause Piggybacking Benchmark) fixtures, OOS injection benchmark, and the in-process load harness.

mod canonical_corpus;
mod fhv1_corpus;
mod fhv1_eval;
mod oos_benchmark;
mod suite2_catalog;
mod synthetic_fixtures;

pub use canonical_corpus::{canonical_seed_corpus, CanonicalDomainCorpus};
pub use fhv1_corpus::{canonical_fhv1_documents, read_corpus_path, text_sha256};
pub use fhv1_eval::{
    attach_comparison, confusion_from_flags, confusion_json, forbid_surface, forbidden_digests,
    granularity_name, metrics_for, nfkc_lower, overlap_ids, parse_granularity,
    persist_benchmark_run, prepare_prompts, score_view, select_view, ConfusionCounts, Fhv1Prompt,
    PersistRequest, PreparedPrompt, PreparedView, RunMetrics, ScoredView, CATEGORIES,
};
pub use oos_benchmark::{
    format_suite2_metrics, run_oos_benchmark, suite2_embed_jsonl, suite2_locks, OosBenchmarkResult,
    Suite2FpTier, Suite2Matrix, Suite2Sample, OOS_BENCHMARK_SEED,
};
pub use suite2_catalog::{suite2_matrix_label, suite2_prompts, Suite2Kind, Suite2Prompt};

pub use synthetic_fixtures::{
    assert_publication_bounds, evaluate_matrix, generate_canonical_locks, generate_corpus,
    generate_scpb_220_corpus, generate_seed_catalog, AttackCase, EvalMatrix, RompepepeCorpus,
    Scpb220Corpus, DOMAIN_NAMES, FIXTURE_SEED,
};
