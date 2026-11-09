//! SCPB-220 (Sub-Clause Piggybacking Benchmark) fixtures, OOS injection benchmark, and the in-process load harness.

mod canonical_corpus;
mod oos_benchmark;
mod synthetic_fixtures;

pub use canonical_corpus::{canonical_seed_corpus, CanonicalDomainCorpus};
pub use oos_benchmark::{run_oos_benchmark, OosBenchmarkResult, OOS_BENCHMARK_SEED};

pub use synthetic_fixtures::{
    assert_publication_bounds, evaluate_matrix, generate_canonical_locks, generate_corpus,
    generate_scpb_220_corpus, AttackCase, EvalMatrix, RompepepeCorpus, Scpb220Corpus, DOMAIN_NAMES,
    FIXTURE_SEED,
};
