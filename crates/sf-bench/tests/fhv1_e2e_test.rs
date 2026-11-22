//! Overlap gate, confusion/granularity differentiation, and LanceDB persistence.

use async_trait::async_trait;
use sf_bench::{
    canonical_fhv1_documents, confusion_from_flags, forbidden_digests, metrics_for, overlap_ids,
    persist_benchmark_run, prepare_prompts, score_view, select_view, Fhv1Prompt, PersistRequest,
};
use sf_kernels::{AlignedVec1024, Fhv1EvalGranularity, Fhv1Quantiles, MovementMetric, DIM};
use sf_proxy::{
    calibrate_fhv1_corpus, expand_for_granularity, BatchEmbedderClient, Fhv1CalibrateSpec,
};
use sf_storage::{Fhv1Store, Fhv1TraceQuery};

const INSIDE: &str = "Inside document stays within the calibrated envelope.";
const LEAVING: &str = "Leaving clause exits the calibrated envelope";
const ROGUE: &str = "Rogue coordinate probe stays otherwise inside.";

struct TestRawF64Embedder;

#[async_trait]
impl BatchEmbedderClient for TestRawF64Embedder {
    async fn embed_batch_f32(&self, _texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
        Err("test embedder has no f32 path".to_string())
    }

    async fn embed_batch_raw_f64(
        &self,
        texts: &[&str],
        _normalize: bool,
    ) -> Result<Vec<[f64; DIM]>, String> {
        let mut rows = Vec::with_capacity(texts.len());
        for text in texts {
            let mut row = vec![0.0; DIM];
            if *text == LEAVING {
                row[0] = 25.0;
            }
            if *text == ROGUE {
                row[292] = 25.0;
            }
            let boxed: Box<[f64]> = row.into_boxed_slice();
            let array: Box<[f64; DIM]> = boxed.try_into().expect("dim");
            rows.push(*array);
        }
        Ok(rows)
    }
}

fn prompt_with_subtype(
    id: &str,
    category: &str,
    expected: bool,
    text: &str,
    subtype: Option<&str>,
) -> Fhv1Prompt {
    Fhv1Prompt {
        input_id: id.to_string(),
        category: category.to_string(),
        expected_pass: expected,
        text: text.to_string(),
        subtype: subtype.map(str::to_string),
    }
}

fn prompt(id: &str, category: &str, expected: bool, text: &str) -> Fhv1Prompt {
    prompt_with_subtype(id, category, expected, text, None)
}

#[test]
fn overlap_gate_rejects_exact_windows_and_nfkc_casefold() {
    let docs = vec!["alpha beta gamma delta epsilon zeta".to_string()];
    let forbidden = forbidden_digests(&docs);
    let window = prompt(
        "window",
        "OUT_OF_DOMAIN_BENIGN",
        false,
        "alpha beta gamma delta epsilon",
    );
    assert_eq!(overlap_ids(&forbidden, &[window]), vec!["window"]);

    let folded = forbidden_digests(&["Hello Envelope".to_string()]);
    let lower = prompt("case", "ADVERSARIAL_FUZZING", false, "hello envelope");
    assert_eq!(overlap_ids(&folded, &[lower]), vec!["case"]);
    let fresh = prompt(
        "fresh",
        "IN_DOMAIN_VALID",
        true,
        "A completely different calibration-safe sentence about sockets.",
    );
    assert!(overlap_ids(&folded, &[fresh]).is_empty());
}

#[test]
fn confusion_counts_cover_all_four_cells() {
    let counts = confusion_from_flags(&[true, true, false, false], &[true, false, false, true]);
    assert_eq!(counts.tp, 1);
    assert_eq!(counts.fn_, 1);
    assert_eq!(counts.tn, 1);
    assert_eq!(counts.fp, 1);
}

#[tokio::test]
async fn granularity_mask_and_lance_persistence_diverge() {
    let path = std::env::temp_dir().join(format!(
        "fhv1-bench-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("clock")
            .as_nanos()
    ));
    std::fs::create_dir_all(&path).expect("temp");
    let store = Fhv1Store::new(path.to_str().expect("utf8"));
    let corpus = vec![INSIDE.to_string()];
    let profile = calibrate_fhv1_corpus(
        &store,
        &TestRawF64Embedder,
        &Fhv1CalibrateSpec {
            policy_id: "python",
            raw_texts: &corpus,
            normalize: false,
            use_rogue_mask_default: false,
            polarity: 0,
            model_id: "BAAI/bge-m3",
            augmented_llm: false,
            metric: MovementMetric::Span,
            quantiles: Fhv1Quantiles::standard(),
        },
    )
    .await
    .expect("calibrate");
    let mixed = format!("{INSIDE} {LEAVING}.");
    let prompts = vec![
        prompt_with_subtype("in", "IN_DOMAIN_VALID", true, INSIDE, Some("short_en")),
        prompt_with_subtype(
            "hybrid",
            "IN_DOMAIN_VALID",
            true,
            &mixed,
            Some("clause_mix"),
        ),
        prompt_with_subtype(
            "rogue",
            "ADVERSARIAL_FUZZING",
            false,
            ROGUE,
            Some("rogue_probe"),
        ),
    ];
    let prepared = prepare_prompts(&TestRawF64Embedder, &prompts, false)
        .await
        .expect("prepare");

    let score = |granularity, mask| {
        let mut rows = Vec::new();
        for item in &prepared {
            let view = select_view(item, granularity).expect("view");
            rows.push(score_view(&profile, view, mask).expect("score"));
        }
        rows
    };
    let full = score(Fhv1EvalGranularity::FullOnly, false);
    let clauses = score(Fhv1EvalGranularity::Clauses, false);
    let mirror = score(Fhv1EvalGranularity::FullMirror, false);
    let rogue_open = score(Fhv1EvalGranularity::FullOnly, false);
    let rogue_masked = score(Fhv1EvalGranularity::FullOnly, true);

    assert!(full[0].overall_passed);
    assert!(
        full[1].overall_passed,
        "full text of the mixed prompt stays inside"
    );
    assert!(
        !clauses[1].overall_passed,
        "the leaving clause fails the envelope"
    );
    assert!(!mirror[1].overall_passed);
    assert_eq!(full[1].evaluated_dims, 1024);
    assert!(!rogue_open[2].overall_passed);
    assert!(rogue_masked[2].overall_passed, "rogue dim 292 is pruned");
    assert_eq!(rogue_masked[2].evaluated_dims, 1015);

    let full_metrics = metrics_for(
        &prompts,
        &full,
        Fhv1EvalGranularity::FullOnly,
        false,
        profile.movement_tier_codes.as_ref(),
    );
    let clause_metrics = metrics_for(
        &prompts,
        &clauses,
        Fhv1EvalGranularity::Clauses,
        false,
        profile.movement_tier_codes.as_ref(),
    );
    assert_ne!(full_metrics.counts.fn_, clause_metrics.counts.fn_);
    assert!(
        clause_metrics.summary["attribution"]["in_domain_fail_counts"][0]
            .as_u64()
            .expect("count")
            > 0
    );
    assert!(
        clause_metrics.summary["failed_dims_count_histogram_by_category"]["IN_DOMAIN_VALID"]
            .is_object()
    );
    assert_eq!(
        clause_metrics.summary["failed_dims_stats_by_category"]["IN_DOMAIN_VALID"]["prompt_count"],
        2
    );
    assert_eq!(
        clause_metrics.summary["per_subtype"]["short_en"]["passed"],
        1
    );
    assert!(clause_metrics.summary["latency"]["prompt_eval_p50_ns"]
        .as_f64()
        .is_some());
    let run_id = "fhv1-e2e-clauses";
    persist_benchmark_run(
        &store,
        &profile,
        &prepared,
        &clauses,
        &PersistRequest {
            granularity: Fhv1EvalGranularity::Clauses,
            use_rogue_mask: false,
            dataset_name: "e2e",
            dataset_sha256: [7u8; 32],
            summary: &clause_metrics.summary,
            run_id,
            created_at_ms: 1,
        },
    )
    .await
    .expect("persist");
    let runs = store.list_benchmark_runs().await.expect("runs");
    assert_eq!(runs.len(), 1);
    assert_eq!(runs[0].run_id, run_id);
    assert!(runs[0].summary_metrics_json.contains("confusion"));
    let page = store
        .query_audit_trace_summaries(&Fhv1TraceQuery {
            trace_id: None,
            run_id: Some(run_id.to_string()),
            profile_id: None,
            source_kind: Some("BENCHMARK".to_string()),
            category: None,
            passed: None,
            page: 1,
            page_size: 50,
        })
        .await
        .expect("traces");
    assert!(page.total > 0);
    assert!(page.rows.iter().all(|row| row.source_kind == "BENCHMARK"));
    assert!(!path.join("domain_hypercubes.lance").exists());
    let _ = std::fs::remove_dir_all(&path);
}

#[test]
fn curated_corpus_and_benchmark_banks_have_zero_rust_overlap_and_nonempty_chunks() {
    let banks: serde_json::Value =
        serde_json::from_str(include_str!("../../../tools/fhv1_benchmark_banks.json"))
            .expect("parse fhv1_benchmark_banks.json");

    for policy_id in ["python", "receta"] {
        let corpus = canonical_fhv1_documents(policy_id).expect("corpus");
        let forbidden = forbidden_digests(&corpus);
        let domain_bank = banks
            .get(policy_id)
            .and_then(|v| v.as_object())
            .expect("domain bank");
        let mut prompts = Vec::new();
        for (quadrant, entries) in domain_bank {
            for (idx, item) in entries.as_array().expect("entries").iter().enumerate() {
                let text = item
                    .get("text")
                    .and_then(|v| v.as_str())
                    .expect("text")
                    .to_string();
                prompts.push(prompt_with_subtype(
                    &format!("{policy_id}-{quadrant}-{idx}"),
                    quadrant,
                    quadrant == "in_domain_valid",
                    &text,
                    item.get("subtype").and_then(|v| v.as_str()),
                ));
            }
        }
        let hits = overlap_ids(&forbidden, &prompts);
        assert!(
            hits.is_empty(),
            "{policy_id} Rust forbidden_digests overlap with benchmark banks: {hits:?}"
        );
        for item in &prompts {
            for gran in [
                Fhv1EvalGranularity::FullOnly,
                Fhv1EvalGranularity::Clauses,
                Fhv1EvalGranularity::FullMirror,
            ] {
                let chunks = expand_for_granularity(&item.text, gran);
                assert!(
                    !chunks.is_empty(),
                    "{policy_id} prompt {} expanded to zero chunks for {gran:?}: {:?}",
                    item.input_id,
                    item.text
                );
            }
        }
    }
}
