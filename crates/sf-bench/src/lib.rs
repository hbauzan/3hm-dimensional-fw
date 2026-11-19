//! SCPB-220 (Sub-Clause Piggybacking Benchmark) fixtures, OOS injection benchmark, and the in-process load harness.

mod canonical_corpus;
mod oos_benchmark;
mod suite2_catalog;
mod synthetic_fixtures;

pub use canonical_corpus::{canonical_seed_corpus, CanonicalDomainCorpus};
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
