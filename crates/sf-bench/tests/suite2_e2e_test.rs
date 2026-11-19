use std::collections::BTreeSet;

use sf_bench::{format_suite2_metrics, run_oos_benchmark, suite2_locks, suite2_matrix_label};
use sf_proxy::InputNormalizer;
use sf_storage::pair_lock_sides;

#[test]
fn suite2_scores_segmented_prompts_on_sixty_six_calibrated_locks() {
    let locks = suite2_locks();
    assert_eq!(locks.len(), 66);
    assert!(locks.iter().any(|lock| lock.domain_id == "python"));
    assert!(locks.iter().any(|lock| lock.domain_id == "python_receta"));

    let bases: Vec<_> = locks
        .iter()
        .filter(|lock| pair_lock_sides(&lock.domain_id).is_none())
        .collect();
    let pairs: Vec<_> = locks
        .iter()
        .filter(|lock| pair_lock_sides(&lock.domain_id).is_some())
        .collect();
    assert_eq!(bases.len(), 11);
    assert_eq!(pairs.len(), 55);
    assert!(pairs.iter().any(|lock| lock.top_k_len > 0));
    let python_receta = locks
        .iter()
        .find(|lock| lock.domain_id == "python_receta")
        .unwrap();
    assert_eq!(
        python_receta.noise_mask.active_count(),
        u32::from(python_receta.top_k_len)
    );
    assert!(
        python_receta.top_k_len != 103
            || python_receta.top_k_indices[..103]
                .iter()
                .any(|dim| *dim != 0)
    );

    for lock in &bases {
        assert_eq!(lock.quorum_k, 103);
        let active = lock.noise_mask.active_count();
        assert_eq!(u32::from(lock.top_k_len), active.min(103));
        assert!(lock.top_k_len > 0);
        assert!(lock.top_k_indices[..usize::from(lock.top_k_len)]
            .iter()
            .any(|dim| *dim != 0));
    }
    for lock in &pairs {
        assert_eq!(lock.noise_mask.active_count(), u32::from(lock.top_k_len));
        let mut seen = BTreeSet::new();
        for &dim in &lock.top_k_indices[..usize::from(lock.top_k_len)] {
            assert!(
                lock.noise_mask.is_active(usize::from(dim)),
                "{} dim {dim}",
                lock.domain_id
            );
            assert!(seen.insert(dim), "duplicate dim on {}", lock.domain_id);
        }
    }

    let report = run_oos_benchmark();
    assert!(!report.samples.is_empty());
    for sample in &report.samples {
        assert_eq!(sample.matrix, suite2_matrix_label(sample.target_domain));
        assert_eq!(sample.primary_mode, "ModeCSpectralQuorum");
        assert_eq!(sample.pairwise_mode, "ModeATopK");
        assert!(!sample.prompt.to_lowercase().contains("y de paso"));

        let normalized = InputNormalizer::normalize(&sample.prompt);
        assert_eq!(sample.normalized, normalized.text);
        let clauses: Vec<String> = normalized
            .segment_all_clauses()
            .into_iter()
            .map(str::to_string)
            .collect();
        assert_eq!(sample.clauses, clauses);

        let expected: Vec<String> = locks
            .iter()
            .filter(|lock| match pair_lock_sides(&lock.domain_id) {
                Some((left, right)) => {
                    (left == sample.target_domain || right == sample.target_domain)
                        && lock.top_k_len > 0
                        && lock.noise_mask.active_count() > 0
                }
                None => false,
            })
            .map(|lock| lock.domain_id.clone())
            .collect();
        assert_eq!(sample.pairwise_lock_ids, expected);
        for id in &sample.pairwise_lock_ids {
            let lock = locks.iter().find(|lock| lock.domain_id == *id).unwrap();
            assert!(lock.top_k_len > 0);
            assert_eq!(lock.noise_mask.active_count(), u32::from(lock.top_k_len));
        }
    }

    assert!(report
        .samples
        .iter()
        .filter(|sample| sample.matrix == "EN")
        .all(|sample| sample.target_domain == "python"));
    assert!(report
        .samples
        .iter()
        .filter(|sample| sample.matrix == "ES")
        .all(|sample| sample.target_domain != "python"));

    for matrix in [&report.en, &report.es, &report.pooled] {
        assert!(matrix.n_clean > 0);
        assert!(matrix.n_attack > 0);
        assert_eq!(
            matrix.fpr,
            matrix.false_positives as f64 / matrix.n_clean as f64
        );
        assert_eq!(
            matrix.leak_rate,
            matrix.cosine_leaks as f64 / matrix.n_attack as f64
        );
        assert_eq!(
            matrix.recall,
            matrix.blocked as f64 / matrix.n_attack as f64
        );
        let label = matrix.label;
        let rows = report
            .samples
            .iter()
            .filter(|sample| label == "pooled" || sample.matrix == label);
        let rows: Vec<_> = rows.collect();
        assert_eq!(
            matrix.n_clean,
            rows.iter().filter(|sample| sample.kind == "clean").count()
        );
        assert_eq!(
            matrix.false_positives,
            rows.iter()
                .filter(|sample| sample.kind == "clean" && !sample.contained)
                .count()
        );
        assert_eq!(
            matrix.n_attack,
            rows.iter().filter(|sample| sample.kind == "attack").count()
        );
        assert_eq!(
            matrix.cosine_leaks,
            rows.iter()
                .filter(|sample| sample.kind == "attack" && sample.cosine_leak)
                .count()
        );
        assert_eq!(
            matrix.blocked,
            rows.iter()
                .filter(|sample| sample.kind == "attack" && !sample.contained)
                .count()
        );
    }
    assert_eq!(report.pooled.n_clean, report.en.n_clean + report.es.n_clean);
    assert_eq!(
        report.pooled.false_positives,
        report.en.false_positives + report.es.false_positives
    );
    assert_eq!(
        report.pooled.n_attack,
        report.en.n_attack + report.es.n_attack
    );
    assert_eq!(
        report.pooled.cosine_leaks,
        report.en.cosine_leaks + report.es.cosine_leaks
    );
    assert_eq!(report.pooled.blocked, report.en.blocked + report.es.blocked);

    let printed = format_suite2_metrics(&report);
    for matrix in [&report.en, &report.es, &report.pooled] {
        let needle = format!(
            "matrix={} n_clean={} fp={} fpr={}/{} n_attack={} cosine_leaks={} leak_rate={}/{} blocked={} recall={}/{}",
            matrix.label,
            matrix.n_clean,
            matrix.false_positives,
            matrix.false_positives,
            matrix.n_clean,
            matrix.n_attack,
            matrix.cosine_leaks,
            matrix.cosine_leaks,
            matrix.n_attack,
            matrix.blocked,
            matrix.blocked,
            matrix.n_attack,
        );
        assert!(printed.contains(&needle), "{printed}");
    }
    assert!(printed.contains("matrix=EN"));
    assert!(printed.contains("matrix=ES"));
    assert!(printed.contains("matrix=pooled"));
    assert!(report.latency_p50_us.is_finite() && report.latency_p50_us > 0.0);
    assert!(report.latency_p99_us >= report.latency_p50_us);
}
