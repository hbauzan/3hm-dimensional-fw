//! Lossless AABB contract: 1 ULP and 16 ULP rejection, Welford, tiers, rogue mask.

use sf_kernels::{
    classify_movement_tiers, compute_fhv1_profile_stats, evaluate_fhv1_batch, evaluate_fhv1_chunk,
    fhv1_evaluated_dims, DimBoundStatus, Fhv1Error, Fhv1EvalGranularity, Fhv1Quantiles,
    MovementMetric, MovementTier, DIM, UNIVERSAL_NOISE_INDICES,
};

fn standard() -> Fhv1Quantiles {
    Fhv1Quantiles::standard()
}

fn envelope(lo: f64, hi: f64) -> Box<sf_kernels::Fhv1ProfileStats> {
    let rows = [[lo; DIM], [hi; DIM]];
    compute_fhv1_profile_stats(&rows, 0, MovementMetric::Span, standard()).expect("envelope")
}

fn add_ulps(value: f64, ulps: u64) -> f64 {
    f64::from_bits(value.to_bits() + ulps)
}

fn sub_ulps(value: f64, ulps: u64) -> f64 {
    f64::from_bits(value.to_bits() - ulps)
}

#[test]
fn one_ulp_and_sixteen_ulp_outside_the_envelope_fail() {
    let stats = envelope(1.0, 2.0);
    let inside_lo = [1.0; DIM];
    let inside_hi = [2.0; DIM];
    let below = [sub_ulps(1.0, 1); DIM];
    let above_one = [add_ulps(2.0, 1); DIM];
    let above_sixteen = [add_ulps(2.0, 16); DIM];

    let lo = evaluate_fhv1_chunk(&stats, &inside_lo, false).expect("lo");
    let hi = evaluate_fhv1_chunk(&stats, &inside_hi, false).expect("hi");
    assert!(lo.chunk_passed);
    assert!(hi.chunk_passed);
    assert_eq!(lo.dimensions[0].status, DimBoundStatus::InBounds);
    assert_eq!(lo.dimensions[0].violation_delta.to_bits(), 0.0f64.to_bits());
    assert_eq!(lo.dimensions[0].observed_bits, 1.0f64.to_bits());

    let under = evaluate_fhv1_chunk(&stats, &below, false).expect("under");
    assert!(!under.chunk_passed);
    assert_eq!(under.underflow_count, DIM as u16);
    assert_eq!(under.overflow_count, 0);
    assert_eq!(under.dimensions[0].status, DimBoundStatus::Underflow);
    let expected_under = 1.0 - below[0];
    assert_eq!(
        under.dimensions[0].violation_delta.to_bits(),
        expected_under.to_bits()
    );
    assert_eq!(
        under.max_violation_delta.to_bits(),
        expected_under.to_bits()
    );

    let over = evaluate_fhv1_chunk(&stats, &above_one, false).expect("over");
    assert!(!over.chunk_passed);
    assert_eq!(over.overflow_count, DIM as u16);
    assert_eq!(over.dimensions[3].status, DimBoundStatus::Overflow);

    let over16 = evaluate_fhv1_chunk(&stats, &above_sixteen, false).expect("over16");
    assert!(!over16.chunk_passed);
    let expected_over = above_sixteen[0] - 2.0;
    assert_eq!(
        over16.dimensions[0].violation_delta.to_bits(),
        expected_over.to_bits()
    );
    assert!(expected_over > (above_one[0] - 2.0));
}

#[test]
fn welford_population_moments_match_the_closed_form() {
    let mut rows = Vec::new();
    for value in [1.0, 2.0, 3.0, 4.0, 5.0] {
        rows.push([value; DIM]);
    }
    let stats =
        compute_fhv1_profile_stats(&rows, 0, MovementMetric::Variance, standard()).expect("stats");
    assert_eq!(stats.sample_count, 5);
    assert_eq!(stats.polarity, 0);
    assert_eq!(stats.mean[0].to_bits(), 3.0f64.to_bits());
    assert_eq!(stats.min[0].to_bits(), 1.0f64.to_bits());
    assert_eq!(stats.max[0].to_bits(), 5.0f64.to_bits());
    assert_eq!(stats.span[0].to_bits(), 4.0f64.to_bits());
    assert_eq!(stats.variance[0].to_bits(), 2.0f64.to_bits());
    assert_eq!(stats.std_dev[0].to_bits(), 2.0f64.sqrt().to_bits());
}

#[test]
fn welford_keeps_variance_when_one_pass_squares_collapse() {
    let base = (1u64 << 40) as f64;
    let mut rows = Vec::new();
    for offset in [1.0, 2.0, 3.0, 4.0, 5.0] {
        rows.push([base + offset; DIM]);
    }
    let stats =
        compute_fhv1_profile_stats(&rows, 0, MovementMetric::Variance, standard()).expect("stats");
    assert_eq!(stats.mean[0].to_bits(), (base + 3.0).to_bits());
    assert_eq!(stats.variance[0].to_bits(), 2.0f64.to_bits());
    let mean = rows.iter().map(|row| row[0]).sum::<f64>() / 5.0;
    let naive = rows.iter().map(|row| row[0] * row[0]).sum::<f64>() / 5.0 - mean * mean;
    assert_eq!(naive.to_bits(), 0.0f64.to_bits());
}

#[test]
fn non_finite_empty_and_short_rows_fail_closed() {
    let nan = {
        let mut row = [0.0; DIM];
        row[7] = f64::NAN;
        row
    };
    let err = compute_fhv1_profile_stats(&[nan], 0, MovementMetric::Span, standard()).unwrap_err();
    assert_eq!(
        err,
        Fhv1Error::NonFinite {
            sample_index: 0,
            dim: 7
        }
    );

    let mut later = [0.0; DIM];
    later[0] = f64::INFINITY;
    let err = compute_fhv1_profile_stats(&[[0.0; DIM], later], 0, MovementMetric::Span, standard())
        .unwrap_err();
    assert_eq!(
        err,
        Fhv1Error::NonFinite {
            sample_index: 1,
            dim: 0
        }
    );

    let empty: [&[f64]; 0] = [];
    assert_eq!(
        compute_fhv1_profile_stats(&empty, 0, MovementMetric::Span, standard()).unwrap_err(),
        Fhv1Error::EmptyCorpus
    );
    let short = vec![0.0; 3];
    assert_eq!(
        compute_fhv1_profile_stats(&[short], 0, MovementMetric::Span, standard()).unwrap_err(),
        Fhv1Error::BadDim { len: 3 }
    );
    let bad_q = Fhv1Quantiles {
        p25: 0.9,
        p75: 0.2,
        p90: 0.95,
    };
    assert_eq!(
        compute_fhv1_profile_stats(&[[0.0; DIM]], 0, MovementMetric::Span, bad_q).unwrap_err(),
        Fhv1Error::InvalidQuantiles
    );
    let nan_q = Fhv1Quantiles {
        p25: f64::NAN,
        p75: 0.5,
        p90: 0.9,
    };
    assert_eq!(nan_q.validate(), Err(Fhv1Error::InvalidQuantiles));
}

#[test]
fn zero_span_is_zero_span_and_positive_spans_follow_quantile_brackets() {
    let row_lo = [0.0; DIM];
    let mut row_hi = [0.0; DIM];
    for (dim, slot) in row_hi.iter_mut().take(8).enumerate() {
        *slot = (dim as f64) + 1.0;
    }
    let stats = compute_fhv1_profile_stats(&[row_lo, row_hi], 0, MovementMetric::Span, standard())
        .expect("tiers");
    for dim in 8..DIM {
        assert_eq!(
            stats.movement_tier_codes[dim],
            MovementTier::ZeroSpan.code()
        );
        assert_eq!(stats.span[dim].to_bits(), 0.0f64.to_bits());
    }
    let spans = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0];
    let p25 = linear_reference(&spans, 0.25);
    let p75 = linear_reference(&spans, 0.75);
    let p90 = linear_reference(&spans, 0.90);
    assert_eq!(stats.cutoffs.p25.to_bits(), p25.to_bits());
    assert_eq!(stats.cutoffs.p75.to_bits(), p75.to_bits());
    assert_eq!(stats.cutoffs.p90.to_bits(), p90.to_bits());
    assert_eq!(stats.movement_tier_codes[0], MovementTier::LowAnchor.code());
    assert_eq!(stats.movement_tier_codes[1], MovementTier::LowAnchor.code());
    assert_eq!(stats.movement_tier_codes[2], MovementTier::Moderate.code());
    assert_eq!(stats.movement_tier_codes[5], MovementTier::Moderate.code());
    assert_eq!(
        stats.movement_tier_codes[6],
        MovementTier::HighVolatility.code()
    );
    assert_eq!(
        stats.movement_tier_codes[7],
        MovementTier::ExtremeMovement.code()
    );

    let again = classify_movement_tiers(
        &stats.span,
        &stats.variance,
        &stats.std_dev,
        MovementMetric::Span,
        standard(),
    )
    .expect("reclass");
    assert_eq!(again.codes.as_ref(), &stats.movement_tier_codes);
}

#[test]
fn mean_offset_inside_the_box_still_passes() {
    let stats = envelope(-10.0, 10.0);
    assert_eq!(stats.mean[0].to_bits(), 0.0f64.to_bits());
    let mut observed = [9.0; DIM];
    let hit = evaluate_fhv1_chunk(&stats, &observed, false).expect("inside");
    assert!(hit.chunk_passed);
    assert_eq!(hit.dimensions[0].status, DimBoundStatus::InBounds);
    assert_eq!(hit.dimensions[0].delta_vs_mean.to_bits(), 9.0f64.to_bits());
    assert_eq!(
        hit.dimensions[0].norm_pos.unwrap().to_bits(),
        0.95f64.to_bits()
    );

    observed[4] = add_ulps(10.0, 1);
    let miss = evaluate_fhv1_chunk(&stats, &observed, false).expect("outside");
    assert!(!miss.chunk_passed);
    assert_eq!(miss.dimensions[4].status, DimBoundStatus::Overflow);
    assert_eq!(miss.failed_dims_count, 1);
}

#[test]
fn rogue_mask_drops_nine_coordinates_and_full_width_keeps_them() {
    let stats = envelope(0.0, 1.0);
    assert_eq!(fhv1_evaluated_dims(false), 1024);
    assert_eq!(fhv1_evaluated_dims(true), 1015);
    let mut observed = [0.5; DIM];
    let rogue = UNIVERSAL_NOISE_INDICES[0] as usize;
    observed[rogue] = 50.0;

    let masked = evaluate_fhv1_chunk(&stats, &observed, true).expect("masked");
    assert!(masked.chunk_passed);
    assert_eq!(masked.evaluated_dims, 1015);
    assert_eq!(masked.failed_dims_count, 0);
    assert_eq!(masked.dimensions[rogue].status, DimBoundStatus::PrunedRogue);
    assert_eq!(
        masked.dimensions[rogue].violation_delta.to_bits(),
        0.0f64.to_bits()
    );
    assert_eq!(masked.dimensions[rogue].observed_bits, 50.0f64.to_bits());

    let full = evaluate_fhv1_chunk(&stats, &observed, false).expect("full");
    assert!(!full.chunk_passed);
    assert_eq!(full.evaluated_dims, 1024);
    assert_eq!(full.failed_dims_count, 1);
    assert_eq!(full.dimensions[rogue].status, DimBoundStatus::Overflow);

    observed[1] = -1.0;
    let both = evaluate_fhv1_chunk(&stats, &observed, true).expect("both");
    assert!(!both.chunk_passed);
    assert_eq!(both.evaluated_dims, 1015);
    assert_eq!(both.dimensions[1].status, DimBoundStatus::Underflow);
    assert_eq!(both.dimensions[rogue].status, DimBoundStatus::PrunedRogue);
    assert_eq!(both.failed_dims_count, 1);
}

#[test]
fn zero_span_norm_pos_is_absent_and_batch_does_not_stop_early() {
    let stats = compute_fhv1_profile_stats(&[[0.25; DIM]], 0, MovementMetric::Span, standard())
        .expect("point");
    assert_eq!(stats.span[0].to_bits(), 0.0f64.to_bits());
    assert_eq!(stats.movement_tier_codes[0], MovementTier::ZeroSpan.code());
    let exact = evaluate_fhv1_chunk(&stats, &[0.25; DIM], false).expect("exact");
    assert!(exact.chunk_passed);
    assert!(exact.dimensions[0].norm_pos.is_none());

    let wide = envelope(0.0, 1.0);
    let pass = [0.5; DIM];
    let mut fail_early = [0.5; DIM];
    fail_early[2] = 4.0;
    let mut fail_late = [0.5; DIM];
    fail_late[9] = -3.0;

    for granularity in [
        Fhv1EvalGranularity::FullOnly,
        Fhv1EvalGranularity::Clauses,
        Fhv1EvalGranularity::FullMirror,
    ] {
        let batch = evaluate_fhv1_batch(&wide, &[pass, fail_early, fail_late], granularity, false)
            .expect("batch");
        assert_eq!(batch.chunks.len(), 3);
        assert!(batch.full_text_passed);
        assert!(!batch.all_chunks_passed);
        assert!(batch.chunks[1].failed_dims_count > 0);
        assert_eq!(
            batch.chunks[2].dimensions[9].status,
            DimBoundStatus::Underflow
        );
        let expect_overall = matches!(granularity, Fhv1EvalGranularity::FullOnly);
        assert_eq!(batch.overall_passed, expect_overall);
        assert_eq!(batch.granularity, granularity);
    }

    let all_fail = evaluate_fhv1_batch(
        &wide,
        &[fail_early, pass],
        Fhv1EvalGranularity::FullOnly,
        false,
    )
    .expect("full fails");
    assert!(!all_fail.full_text_passed);
    assert!(!all_fail.overall_passed);
    assert!(all_fail.chunks[1].chunk_passed);

    let empty: [&[f64]; 0] = [];
    assert_eq!(
        evaluate_fhv1_batch(&wide, &empty, Fhv1EvalGranularity::Clauses, false).unwrap_err(),
        Fhv1Error::EmptyCorpus
    );
}

#[test]
fn variance_and_std_dev_metrics_split_equal_spans() {
    let mut rows = [[0.0; DIM]; 4];
    rows[3][0] = 4.0;
    rows[1][1] = 4.0;
    rows[3][1] = 4.0;
    rows[1][2] = 1.0;
    rows[2][2] = 3.0;
    rows[3][2] = 4.0;
    rows[1][3] = 2.0;
    rows[2][3] = 2.0;
    rows[3][3] = 4.0;

    let span_stats =
        compute_fhv1_profile_stats(&rows, 0, MovementMetric::Span, standard()).expect("span");
    for dim in 0..4 {
        assert_eq!(span_stats.span[dim].to_bits(), 4.0f64.to_bits());
        assert_eq!(
            span_stats.movement_tier_codes[dim],
            MovementTier::LowAnchor.code()
        );
    }
    for dim in 4..DIM {
        assert_eq!(
            span_stats.movement_tier_codes[dim],
            MovementTier::ZeroSpan.code()
        );
    }

    let variance: [f64; 4] = [3.0, 4.0, 2.5, 2.0];
    let var_stats =
        compute_fhv1_profile_stats(&rows, 0, MovementMetric::Variance, standard()).expect("var");
    assert_eq!(var_stats.metric, MovementMetric::Variance);
    for (dim, expected) in variance.iter().enumerate() {
        assert_eq!(var_stats.variance[dim].to_bits(), expected.to_bits());
    }
    let mut sorted_variance = variance;
    sorted_variance.sort_by(f64::total_cmp);
    assert_eq!(
        var_stats.cutoffs.p25.to_bits(),
        linear_reference(&sorted_variance, 0.25).to_bits()
    );
    assert_eq!(
        var_stats.cutoffs.p75.to_bits(),
        linear_reference(&sorted_variance, 0.75).to_bits()
    );
    assert_eq!(
        var_stats.cutoffs.p90.to_bits(),
        linear_reference(&sorted_variance, 0.90).to_bits()
    );
    assert_eq!(
        var_stats.movement_tier_codes[3],
        MovementTier::LowAnchor.code()
    );
    assert_eq!(
        var_stats.movement_tier_codes[2],
        MovementTier::Moderate.code()
    );
    assert_eq!(
        var_stats.movement_tier_codes[0],
        MovementTier::Moderate.code()
    );
    assert_eq!(
        var_stats.movement_tier_codes[1],
        MovementTier::ExtremeMovement.code()
    );
    for dim in 4..DIM {
        assert_eq!(
            var_stats.movement_tier_codes[dim],
            MovementTier::ZeroSpan.code()
        );
    }
    let reclass = classify_movement_tiers(
        &var_stats.span,
        &var_stats.variance,
        &var_stats.std_dev,
        MovementMetric::Variance,
        standard(),
    )
    .expect("reclass variance");
    assert_eq!(reclass.codes.as_ref(), &var_stats.movement_tier_codes);
    assert_eq!(
        reclass.cutoffs.p90.to_bits(),
        var_stats.cutoffs.p90.to_bits()
    );

    let std_dev: [f64; 4] = [3.0f64.sqrt(), 2.0, 2.5f64.sqrt(), 2.0f64.sqrt()];
    let std_stats =
        compute_fhv1_profile_stats(&rows, 0, MovementMetric::StdDev, standard()).expect("std");
    assert_eq!(std_stats.metric, MovementMetric::StdDev);
    for (dim, expected) in std_dev.iter().enumerate() {
        assert_eq!(std_stats.std_dev[dim].to_bits(), expected.to_bits());
        assert_eq!(std_stats.variance[dim].to_bits(), variance[dim].to_bits());
    }
    let mut sorted_std = std_dev;
    sorted_std.sort_by(f64::total_cmp);
    assert_eq!(
        std_stats.cutoffs.p25.to_bits(),
        linear_reference(&sorted_std, 0.25).to_bits()
    );
    assert_eq!(
        std_stats.cutoffs.p75.to_bits(),
        linear_reference(&sorted_std, 0.75).to_bits()
    );
    assert_eq!(
        std_stats.cutoffs.p90.to_bits(),
        linear_reference(&sorted_std, 0.90).to_bits()
    );
    assert_eq!(
        std_stats.movement_tier_codes[3],
        MovementTier::LowAnchor.code()
    );
    assert_eq!(
        std_stats.movement_tier_codes[2],
        MovementTier::Moderate.code()
    );
    assert_eq!(
        std_stats.movement_tier_codes[0],
        MovementTier::Moderate.code()
    );
    assert_eq!(
        std_stats.movement_tier_codes[1],
        MovementTier::ExtremeMovement.code()
    );
    for dim in 4..DIM {
        assert_eq!(
            std_stats.movement_tier_codes[dim],
            MovementTier::ZeroSpan.code()
        );
    }
    let reclass_std = classify_movement_tiers(
        &std_stats.span,
        &std_stats.variance,
        &std_stats.std_dev,
        MovementMetric::StdDev,
        standard(),
    )
    .expect("reclass std");
    assert_eq!(reclass_std.codes.as_ref(), &std_stats.movement_tier_codes);
}

#[test]
fn envelope_edges_record_norm_pos_and_a_negative_mean_delta() {
    let stats = envelope(1.0, 2.0);
    let at_min = evaluate_fhv1_chunk(&stats, &[1.0; DIM], false).expect("min");
    assert!(at_min.chunk_passed);
    assert_eq!(
        at_min.dimensions[0].norm_pos.unwrap().to_bits(),
        0.0f64.to_bits()
    );
    assert_eq!(
        at_min.dimensions[0].delta_vs_mean.to_bits(),
        (-0.5f64).to_bits()
    );
    assert!(at_min.dimensions[0].delta_vs_mean < 0.0);

    let at_max = evaluate_fhv1_chunk(&stats, &[2.0; DIM], false).expect("max");
    assert!(at_max.chunk_passed);
    assert_eq!(
        at_max.dimensions[7].norm_pos.unwrap().to_bits(),
        1.0f64.to_bits()
    );
    assert_eq!(at_max.dimensions[7].status, DimBoundStatus::InBounds);
}

#[test]
fn evaluate_chunk_rejects_bad_dim_and_non_finite() {
    let stats = envelope(0.0, 1.0);
    let short = [0.5; 3];
    assert_eq!(
        evaluate_fhv1_chunk(&stats, &short, false).unwrap_err(),
        Fhv1Error::BadDim { len: 3 }
    );
    let mut nan = [0.5; DIM];
    nan[4] = f64::NAN;
    assert_eq!(
        evaluate_fhv1_chunk(&stats, &nan, false).unwrap_err(),
        Fhv1Error::NonFinite {
            sample_index: 0,
            dim: 4
        }
    );
    let mut infinite = [0.5; DIM];
    infinite[9] = f64::NEG_INFINITY;
    assert_eq!(
        evaluate_fhv1_chunk(&stats, &infinite, false).unwrap_err(),
        Fhv1Error::NonFinite {
            sample_index: 0,
            dim: 9
        }
    );
}

fn linear_reference(sorted: &[f64], p: f64) -> f64 {
    let n = sorted.len();
    let rank = p * (n as f64 - 1.0);
    let lo = rank.floor() as usize;
    let hi = rank.ceil() as usize;
    let weight = rank - lo as f64;
    sorted[lo] * (1.0 - weight) + sorted[hi] * weight
}
