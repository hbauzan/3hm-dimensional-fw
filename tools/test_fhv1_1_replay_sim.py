#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "lancedb>=0.20.0",
#     "numpy>=2.0.0",
#     "pyarrow>=18.0.0",
# ]
# ///
"""Deterministic offline unit tests for tools/fhv1_1_replay_sim.py (no LanceDB)."""

from __future__ import annotations

import math
import unittest

import numpy as np

import fhv1_1_replay_sim as sim
import fhv1_1_replay_v2 as v2


def _synthetic_cls_report(
    dim: int = 12,
    backbone_dims: tuple[int, ...] = (0, 1),
    anchor_dims: tuple[int, ...] = (2, 3, 4),
    neg_dims: tuple[int, ...] = (5, 6, 7),
) -> dict:
    dims = []
    bucket_dims = {
        "BACKBONE_ENGINE": list(backbone_dims),
        "FIRM_DOMAIN_ANCHOR": list(anchor_dims),
        "NEGATIVE_INTRUDER_SENSOR": list(neg_dims),
        "DEAD_OR_OSCILLATOR": [],
    }
    for d in range(dim):
        if d in backbone_dims:
            bucket = "BACKBONE_ENGINE"
            mean_t, std_t, mean_c, std_c, snr_t, snr_c, sep, ir = 0.2, 0.05, 0.19, 0.05, 4.0, 3.8, 0.2, 1.0
        elif d in anchor_dims:
            bucket = "FIRM_DOMAIN_ANCHOR"
            rank_bonus = float(len(anchor_dims) - anchor_dims.index(d))
            mean_t, std_t, mean_c, std_c, snr_t, snr_c, sep, ir = 0.15, 0.02, 0.01, 0.02, 7.5, 0.5, 3.0 + rank_bonus, 0.15
        elif d in neg_dims:
            bucket = "NEGATIVE_INTRUDER_SENSOR"
            rank_bonus = float(len(neg_dims) - neg_dims.index(d))
            mean_t, std_t, mean_c, std_c, snr_t, snr_c, sep, ir = 0.002, 0.02, 0.05, 0.04, 0.1, 1.25, 1.5, 2.5 + rank_bonus
        else:
            bucket = "DEAD_OR_OSCILLATOR"
            bucket_dims["DEAD_OR_OSCILLATOR"].append(d)
            mean_t, std_t, mean_c, std_c, snr_t, snr_c, sep, ir = 0.02, 0.03, 0.01, 0.03, 0.67, 0.33, 0.33, 0.8
        dims.append(
            {
                "dim": d,
                "bucket": bucket,
                "mean_T": mean_t,
                "std_T": std_t,
                "mean_C": mean_c,
                "std_C": std_c,
                "snr_T": snr_t,
                "snr_C": snr_c,
                "rms_T": math.hypot(mean_t, std_t),
                "rms_C": math.hypot(mean_c, std_c),
                "sep": sep,
                "intruder_ratio": ir,
                "neg_sensor_score": max(sep, ir),
            }
        )
    return {"bucket_dims": bucket_dims, "dimensions": dims}


def _make_prompt_bundle(
    *,
    granularity: str,
    n_prompts: int,
    chunk_vectors: np.ndarray,
    chunk_strategies: tuple[str, ...],
    full_idx: np.ndarray,
    b64_slices: tuple[np.ndarray, ...],
    clause_slices: tuple[np.ndarray, ...],
    expected_pass: np.ndarray,
    chunk_norm_z: np.ndarray | None = None,
) -> sim.PromptBundle:
    cats = tuple("IN_DOMAIN_VALID" if ep else "ADVERSARIAL_FUZZING" for ep in expected_pass)
    subs = tuple("short_idiom_query" if ep else "prompt_injection_jailbreak" for ep in expected_pass)
    iids = tuple(f"p-{i:04d}" for i in range(n_prompts))
    folds = sim.assign_stratified_folds(cats, subs, iids, n_folds=5)
    cap24 = tuple(
        np.array([cl[k] for k in sim.compute_cap24_clause_indices(len(cl))], dtype=np.int64)
        for cl in clause_slices
    )
    return sim.PromptBundle(
        granularity=granularity,
        input_ids=iids,
        categories=cats,
        subtypes=subs,
        expected_pass=expected_pass,
        strat_folds=folds,
        chunk_strategies=chunk_strategies,
        chunk_vectors=chunk_vectors,
        chunk_norm_z=chunk_norm_z,
        full_chunk_idx=full_idx,
        b64_chunk_slices=b64_slices,
        clause_chunk_slices=clause_slices,
        clause_cap24_slices=cap24,
        baseline_passed=np.ones(n_prompts, dtype=bool),
    )


class FactorBoundsAndMonotonicityTest(unittest.TestCase):
    def test_f1_f2_f3_exact_bounds_and_monotonicity(self) -> None:
        dim = 12
        cls = _synthetic_cls_report(dim=dim)
        spec = sim.extract_dim_spec_from_classification(
            cls, dim_count=dim, dim_mask_mode="no_bb_domain", k=3, m=3
        )
        # Backbone dims (0, 1) must be excluded from active_dims, anchors, and neg_sensors
        self.assertEqual(spec.active_dims.tolist(), list(range(2, 12)))
        self.assertEqual(spec.anchor_dims.tolist(), [2, 3, 4])
        self.assertEqual(spec.neg_sensor_dims.tolist(), [5, 6, 7])
        self.assertAlmostEqual(float(np.sum(spec.anchor_weights)), 1.0, places=12)

        mu = np.zeros(dim, dtype=np.float64)
        sd = np.full(dim, 0.1, dtype=np.float64)
        mn = np.full(dim, -0.2, dtype=np.float64)
        mx = np.full(dim, 0.2, dtype=np.float64)
        box = sim.build_box_stats(mn, mx, mu, sd, box_mode="minmax")
        scales = sim.FactorScales(s_f1=0.5, s_l1=1.0, s_l2=1.0, s_neg=0.5)

        # Row 0: exact centroid (inside box)
        # Row 1: slightly shifted (inside box, 0.1 on all dims)
        # Row 2: moderate violation (0.4 on active non-anchor/non-neg dims)
        # Row 3: severe violation (1.0 on all dims, spikes on neg sensors)
        x = np.array(
            [
                np.zeros(dim),
                np.full(dim, 0.1),
                np.full(dim, 0.4),
                np.full(dim, 1.0),
            ],
            dtype=np.float64,
        )
        raw = sim.compute_raw_distances(x, box, spec)
        fac = sim.normalize_factors(raw, scales)

        self.assertEqual(fac.f1.dtype, np.float64)
        self.assertAlmostEqual(float(fac.f1[0]), 1.0, places=12)
        self.assertAlmostEqual(float(fac.f1[1]), 1.0, places=12)
        self.assertAlmostEqual(float(fac.f2_l1[0]), 1.0, places=12)
        self.assertAlmostEqual(float(fac.f2_l2[0]), 1.0, places=12)
        self.assertAlmostEqual(float(fac.f3_anchor[0]), 1.0, places=12)
        self.assertAlmostEqual(float(fac.f3_neg[0]), 1.0, places=12)
        self.assertAlmostEqual(float(fac.f3_add[0]), 1.0, places=12)

        for arr in (fac.f1, fac.f2_l1, fac.f2_l2, fac.f3_anchor, fac.f3_neg, fac.f3_add, fac.f3_mul):
            self.assertTrue(np.all((arr >= 0.0) & (arr <= 1.0)))
        # Strict monotonic decay with increasing perturbation
        self.assertGreater(fac.f1[1], fac.f1[2])
        self.assertGreater(fac.f1[2], fac.f1[3])
        self.assertGreater(fac.f2_l1[0], fac.f2_l1[1])
        self.assertGreater(fac.f2_l1[1], fac.f2_l1[2])
        self.assertGreater(fac.f2_l2[0], fac.f2_l2[1])
        self.assertGreater(fac.f2_l2[1], fac.f2_l2[2])
        self.assertGreater(fac.f3_add[0], fac.f3_add[1])
        self.assertGreater(fac.f3_add[2], fac.f3_add[3])
        self.assertEqual(int(fac.failed_dims_count[0]), 0)
        self.assertEqual(int(fac.failed_dims_count[2]), 10)
        self.assertAlmostEqual(float(fac.max_excess_sigma[2]), 0.2 / (0.1 + sim.EPS_SIGMA), places=12)
        self.assertAlmostEqual(float(fac.max_neg_sensor_z[3]), 1.0 / (0.1 + sim.EPS_SIGMA), places=12)

        box_s3 = sim.build_box_stats(mn, mx, mu, sd, box_mode="sigma3")
        np.testing.assert_allclose(box_s3.lo, np.full(dim, -0.3), rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(box_s3.hi, np.full(dim, 0.3), rtol=0.0, atol=1e-12)


class Base64FailClosedAndKillSwitchTest(unittest.TestCase):
    def test_base64_decoded_payload_fail_closed_in_full_only_and_clauses(self) -> None:
        # 2 prompts: prompt 0 has chunk0=0.95 and b64=0.10 (MUST reject!); prompt 1 has chunk0=0.90 and b64=0.85 (passes)
        chunk_scores = np.array([0.95, 0.10, 0.90, 0.85], dtype=np.float64)
        n_c = chunk_scores.size
        vc = {
            "K1": np.zeros(n_c, dtype=bool),
            "K2": np.zeros(n_c, dtype=bool),
            "K3": np.zeros(n_c, dtype=bool),
            "any": np.zeros(n_c, dtype=bool),
        }
        bundle_full = _make_prompt_bundle(
            granularity="full_only",
            n_prompts=2,
            chunk_vectors=np.zeros((n_c, 4), dtype=np.float64),
            chunk_strategies=("full_doc", "full_doc", "full_doc", "full_doc"),
            full_idx=np.array([0, 2], dtype=np.int64),
            b64_slices=(np.array([1], dtype=np.int64), np.array([3], dtype=np.int64)),
            clause_slices=(np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)),
            expected_pass=np.array([False, True], dtype=bool),
        )
        agg_full = sim.aggregate_prompt_signals(bundle_full, chunk_scores, vc, use_cap24=False)
        self.assertAlmostEqual(float(agg_full["full_b64_min"][0]), 0.10, places=12)
        self.assertAlmostEqual(float(agg_full["full_b64_min"][1]), 0.85, places=12)
        self.assertFalse(bool(agg_full["full_b64_min"][0] >= 0.50))
        self.assertTrue(bool(agg_full["full_b64_min"][1] >= 0.50))

        # Clauses with 30 clauses + Base64 chunk under cap=24: Base64 MUST still be retained & fail-closed
        # Prompt 0: full=0.95, b64=0.05, 30 clauses all 0.95 -> MUST reject in hard_kill, dual_zone, and cap=24!
        cl_scores = np.concatenate((np.array([0.95, 0.05], dtype=np.float64), np.full(30, 0.95, dtype=np.float64)))
        n_cl = cl_scores.size
        vc_cl = {k: np.zeros(n_cl, dtype=bool) for k in ("K1", "K2", "K3", "any")}
        bundle_cl = _make_prompt_bundle(
            granularity="clauses",
            n_prompts=1,
            chunk_vectors=np.zeros((n_cl, 4), dtype=np.float64),
            chunk_strategies=("full_doc", "full_doc") + ("clause_opt2c",) * 30,
            full_idx=np.array([0], dtype=np.int64),
            b64_slices=(np.array([1], dtype=np.int64),),
            clause_slices=(np.arange(2, 32, dtype=np.int64),),
            expected_pass=np.array([False], dtype=bool),
        )
        for cap24_flag in (False, True):
            agg_cl = sim.aggregate_prompt_signals(bundle_cl, cl_scores, vc_cl, use_cap24=cap24_flag)
            self.assertAlmostEqual(float(agg_cl["full_b64_min"][0]), 0.05, places=12)
            pred_dz = sim._dual_zone_predict(
                agg_cl["full_b64_min"], agg_cl["clause_arrays"], 0.50, 0.30, 0.60, 0.25
            )
            self.assertFalse(bool(pred_dz[0]))
            self.assertEqual(agg_cl["evaluated_chunks"], 26 if cap24_flag else 32)

    def test_2a_vs_2b_kill_switch_k1_k2_k3_catches_composite_bypass(self) -> None:
        # 4 prompts: 0=valid in-domain, 1=K1 box spike attack, 2=K2 neg sensor spike attack, 3=K3 norm anomaly attack
        factors = sim.ChunkFactors(
            f1=np.array([0.92, 0.80, 0.92, 0.92], dtype=np.float64),
            f2_l1=np.array([0.90, 0.85, 0.85, 0.85], dtype=np.float64),
            f2_l2=np.array([0.90, 0.85, 0.85, 0.85], dtype=np.float64),
            f3_anchor=np.array([0.90, 0.88, 0.88, 0.88], dtype=np.float64),
            f3_neg=np.array([0.90, 0.88, 0.80, 0.88], dtype=np.float64),
            f3_add=np.array([0.90, 0.88, 0.84, 0.88], dtype=np.float64),
            f3_mul=np.array([0.81, 0.77, 0.70, 0.77], dtype=np.float64),
            max_excess_sigma=np.array([0.5, 8.5, 0.5, 0.5], dtype=np.float64),
            max_neg_sensor_z=np.array([1.0, 1.0, 5.5, 1.0], dtype=np.float64),
            in_bounds_ratio=np.array([1.0, 0.99, 0.99, 1.0], dtype=np.float64),
            failed_dims_count=np.array([0, 1, 1, 0], dtype=np.int64),
            norm_z=np.array([0.5, 0.5, 0.5, 4.8], dtype=np.float64),
        )
        scores = factors.composite((1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0))
        self.assertTrue(np.all(scores >= 0.80))

        bundle = _make_prompt_bundle(
            granularity="full_only",
            n_prompts=4,
            chunk_vectors=np.zeros((4, 4), dtype=np.float64),
            chunk_strategies=("full_doc",) * 4,
            full_idx=np.arange(4, dtype=np.int64),
            b64_slices=tuple(np.empty(0, dtype=np.int64) for _ in range(4)),
            clause_slices=tuple(np.empty(0, dtype=np.int64) for _ in range(4)),
            expected_pass=np.array([True, False, False, False], dtype=bool),
        )
        vc = sim.compute_chunk_veto_components(factors, k_box=7.0, k_neg=5.0, k_norm=4.0)
        self.assertEqual(vc["K1"].tolist(), [False, True, False, False])
        self.assertEqual(vc["K2"].tolist(), [False, False, True, False])
        self.assertEqual(vc["K3"].tolist(), [False, False, False, True])

        agg = sim.aggregate_prompt_signals(bundle, scores, vc)
        pred_2a = agg["full_b64_min"] >= 0.70
        pred_2b = pred_2a & (~agg["prompt_veto"])
        self.assertEqual(pred_2a.tolist(), [True, True, True, True])
        self.assertEqual(pred_2b.tolist(), [True, False, False, False])

        forensics = sim.compute_kill_switch_forensics(pred_2a, pred_2b, agg, bundle)
        self.assertEqual(forensics["exclusive_attacks_caught_only_by_veto"]["count"], 3)
        self.assertEqual(forensics["in_domain_false_rejections_added_by_veto"]["count"], 0)
        self.assertEqual(forensics["delta"]["delta_fp"], -3)
        self.assertAlmostEqual(forensics["metrics_2a"]["f1"], 0.4, places=12)
        self.assertAlmostEqual(forensics["metrics_2b"]["f1"], 1.0, places=12)


class ClausesDualZoneCap24AndZeroLeakageTest(unittest.TestCase):
    def test_clauses_dual_zone_vs_hard_kill_and_cap24_disjoint_indices(self) -> None:
        # Verify cap=24 index selection for n=30: 0..7, 11..18, 22..29 (24 disjoint ordered indices)
        idx30 = sim.compute_cap24_clause_indices(30)
        self.assertEqual(len(idx30), 24)
        self.assertEqual(len(set(idx30)), 24)
        self.assertEqual(idx30, list(range(8)) + list(range(11, 19)) + list(range(22, 30)))
        self.assertEqual(sim.compute_cap24_clause_indices(24), list(range(24)))

        # Prompt with 10 clauses: 9 at 0.90, 1 gray clause at 0.40 (frac=0.10 <= 0.25, >= 0.25 hard)
        full_b64 = np.array([0.90], dtype=np.float64)
        cl_arrs = [np.array([0.90] * 9 + [0.40], dtype=np.float64)]
        # Hard kill at 0.50 rejects; dual zone (t_full=0.50, t_hard=0.25, t_soft=0.50, max_gray=0.25) passes
        self.assertFalse(bool(full_b64[0] >= 0.50 and np.min(cl_arrs[0]) >= 0.50))
        pred_dz = sim._dual_zone_predict(full_b64, cl_arrs, 0.50, 0.25, 0.50, 0.25)
        self.assertTrue(bool(pred_dz[0]))

    def test_stratified_oof_cv_zero_leakage_invariant(self) -> None:
        # 20 prompts across 2 strata (10 positive, 10 negative) -> 5 stratified folds of 4 prompts each
        cats = tuple(["IN_DOMAIN_VALID"] * 10 + ["OUT_OF_DOMAIN_BENIGN"] * 10)
        subs = tuple(["short_idiom_query"] * 10 + ["ood_finance_law"] * 10)
        iids = tuple(f"id-{i:02d}" for i in range(20))
        folds = sim.assign_stratified_folds(cats, subs, iids, n_folds=5)
        for f in range(5):
            self.assertEqual(int(np.sum(folds == f)), 4)
            self.assertEqual(int(np.sum((folds == f) & (np.array(cats) == "IN_DOMAIN_VALID"))), 2)

        y = np.array([c == "IN_DOMAIN_VALID" for c in cats], dtype=bool)
        scores_base = np.array([0.85] * 10 + [0.25] * 10, dtype=np.float64)
        res_base = sim.evaluate_1d_oof_cv(scores_base, y, folds)

        # Mutate ONLY fold 0 test labels & scores arbitrarily; fold 0's fitted threshold from folds 1..4 MUST stay bitwise identical
        scores_mut = scores_base.copy()
        y_mut = y.copy()
        fold0_idx = np.flatnonzero(folds == 0)
        scores_mut[fold0_idx] = np.array([0.01, 0.99, 0.98, 0.02], dtype=np.float64)
        y_mut[fold0_idx] = ~y_mut[fold0_idx]
        res_mut = sim.evaluate_1d_oof_cv(scores_mut, y_mut, folds)
        self.assertEqual(res_base["fold_thresholds"][0], res_mut["fold_thresholds"][0])

    def test_cal_oof_zero_holdout_leakage(self) -> None:
        rng = np.random.default_rng(42)
        n_cal = 50
        dim = 8
        cal_vecs = rng.normal(0.0, 0.05, size=(n_cal, dim)).astype(np.float64)
        sids = [f"{i:06d}-full_doc" for i in range(n_cal)]
        tags = ["full_doc"] * n_cal
        refs = ["dom"] * n_cal
        folds = sim.assign_calibration_folds(sids, tags, refs, n_folds=5)
        cls = _synthetic_cls_report(dim=dim, backbone_dims=(0,), anchor_dims=(1, 2), neg_dims=(3, 4))
        spec = sim.extract_dim_spec_from_classification(cls, dim_count=dim, k=2, m=2)
        fac_a, scales_a, _ = sim.compute_cal_oof_for_granularity(cal_vecs, folds, cal_vecs, folds, spec)
        fac_b, scales_b, _ = sim.compute_cal_oof_for_granularity(cal_vecs, folds, cal_vecs, folds, spec)
        self.assertEqual(scales_a, scales_b)
        np.testing.assert_array_equal(fac_a.f1, fac_b.f1)


class RocAndPrAucTest(unittest.TestCase):
    def test_roc_auc_and_pr_auc_exact_with_ties(self) -> None:
        # Perfect separation -> ROC=1.0, PR=1.0
        y = np.array([1, 1, 0, 0], dtype=np.int64)
        s = np.array([0.9, 0.8, 0.3, 0.1], dtype=np.float64)
        self.assertAlmostEqual(sim.compute_roc_auc_trapezoidal(y, s), 1.0, places=12)
        self.assertAlmostEqual(sim.compute_pr_auc_ap(y, s), 1.0, places=12)

        # Interleaved [1, 0, 1, 0] with [0.9, 0.8, 0.7, 0.6] -> AP = 0.5*1.0 + 0.5*(2/3) = 5/6
        y_int = np.array([1, 0, 1, 0], dtype=np.int64)
        s_int = np.array([0.9, 0.8, 0.7, 0.6], dtype=np.float64)
        self.assertAlmostEqual(sim.compute_roc_auc_trapezoidal(y_int, s_int), 0.75, places=12)
        self.assertAlmostEqual(sim.compute_pr_auc_ap(y_int, s_int), 5.0 / 6.0, places=12)

        # All tied scores -> ROC=0.5, PR=pos_prevalence (0.5)
        s_tie = np.full(4, 0.5, dtype=np.float64)
        self.assertAlmostEqual(sim.compute_roc_auc_trapezoidal(y_int, s_tie), 0.5, places=12)
        self.assertAlmostEqual(sim.compute_pr_auc_ap(y_int, s_tie), 0.5, places=12)

        # ROC-AUC label/score flip symmetry
        triple = sim.compute_auc_triple(np.array([True, False, True, False]), s_int)
        self.assertAlmostEqual(
            triple["roc_auc"], sim.compute_roc_auc_trapezoidal(1 - y_int, 1.0 - s_int), places=12
        )


def _f64_bytes(value: float) -> bytes:
    return np.float64(value).tobytes()


class ReplayV2ContractTest(unittest.TestCase):
    def _population(self) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], np.ndarray, np.ndarray]:
        cats = tuple(["IN_DOMAIN_VALID"] * 20 + ["OUT_OF_DOMAIN_BENIGN"] * 20)
        subs = tuple(["short_idiom_query"] * 20 + ["extreme_short_punct"] * 20)
        ids = tuple(f"p{i:03d}" for i in range(40))
        y = np.array([True] * 20 + [False] * 20)
        scores = np.array([0.9] * 15 + [0.2] * 5 + [0.8] * 5 + [0.1] * 15, dtype=np.float64)
        return cats, subs, ids, y, scores

    def test_tail_z_detects_one_fired_dim_among_1024(self) -> None:
        mu = np.zeros(1024, dtype=np.float64)
        sigma = np.ones(1024, dtype=np.float64)
        perfect = np.zeros((1, 1024), dtype=np.float64)
        fired = perfect.copy()
        fired[0, 17] = np.float64(8.0)
        z = v2.tail_z_rows(fired, mu, sigma)
        self.assertEqual(z.shape, (1, 1024))
        self.assertEqual(int(np.argmax(z[0])), 17)
        self.assertEqual(int(np.count_nonzero(z[0] == 0.0)), 1023)
        quiet = v2.tail_scores_all_dimensions(perfect, mu, sigma, 1, 1.0)
        loud = v2.tail_scores_all_dimensions(fired, mu, sigma, 1, 1.0)
        self.assertEqual(float(quiet[0]), 1.0)
        self.assertGreater(float(loud[0]), 0.0)
        self.assertLess(float(loud[0]), 1.0)

    def test_tail_z_s_tail_p_is_monotone_in_p(self) -> None:
        mu = np.zeros(1024, dtype=np.float64)
        sigma = np.ones(1024, dtype=np.float64)
        fired = np.zeros((1, 1024), dtype=np.float64)
        fired[0, 17] = np.float64(8.0)
        z = v2.tail_z_rows(fired, mu, sigma)
        raws = [float(v2.worst_p_mean(z, p)[0]) for p in v2.TAIL_PS]
        scores = [float(v2.map_tail_score(np.array([raw], dtype=np.float64), 1.0)[0]) for raw in raws]
        self.assertEqual(raws, sorted(raws, reverse=True))
        self.assertEqual(len(set(raws)), len(raws))
        self.assertEqual(scores, sorted(scores))
        self.assertEqual(len(set(scores)), len(scores))
        self.assertTrue(all(0.0 < score <= 1.0 for score in scores))

    def test_tail_z_scores_low_signal_noise_dim(self) -> None:
        mu = np.zeros(1024, dtype=np.float64)
        sigma = np.ones(1024, dtype=np.float64)
        labels = ["LOW_SIGNAL_NOISE"] * 1024
        quiet = np.zeros((1, 1024), dtype=np.float64)
        loud = quiet.copy()
        loud[0, 1023] = np.float64(8.0)
        s_quiet = v2.tail_scores_all_dimensions(quiet, mu, sigma, 5, 1.0, labels)
        s_loud = v2.tail_scores_all_dimensions(loud, mu, sigma, 5, 1.0, labels)
        self.assertEqual(float(s_quiet[0]), 1.0)
        self.assertLess(float(s_loud[0]), float(s_quiet[0]))
        self.assertEqual(s_loud.shape[0], 1)

    def test_tail_q90_uses_calibration_bundles_only(self) -> None:
        cal = np.array([0.0, 0.0, 0.0, 0.0, 10.0], dtype=np.float64)
        raw = float(np.quantile(cal, np.float64(0.90), method="linear"))
        scale = v2.calibration_bundle_q90(cal)
        self.assertEqual(scale, max(raw, float(sim.SCALE_FLOOR)))
        self.assertAlmostEqual(scale, 6.0, places=12)
        with self.assertRaises(ValueError):
            v2.calibration_bundle_q90(np.array([1.0], dtype=np.float64))
        contaminated = np.concatenate((cal, np.zeros(5, dtype=np.float64)))
        moved = float(np.quantile(contaminated, np.float64(0.90), method="linear"))
        self.assertNotEqual(scale, max(moved, float(sim.SCALE_FLOOR)))

    def test_polarity_sign_flip_is_penalized(self) -> None:
        mu = np.array([0.4, -0.4], dtype=np.float64)
        idx = np.array([0, 1], dtype=np.int64)
        flipped = v2.polarity_score((-mu).reshape(1, -1), idx, mu)
        zeros = v2.polarity_score(np.zeros((1, 2), dtype=np.float64), idx, mu)
        self.assertEqual(float(flipped[0]), 0.0)
        self.assertEqual(float(zeros[0]), 0.0)

    def test_polarity_domain_sign_is_rewarded(self) -> None:
        mu = np.array([0.4, -0.4], dtype=np.float64)
        idx = np.array([0, 1], dtype=np.int64)
        at_mean = v2.polarity_score(mu.reshape(1, -1), idx, mu)
        half = v2.polarity_score(np.array([[0.2, -0.2]], dtype=np.float64), idx, mu)
        self.assertEqual(float(at_mean[0]), 1.0)
        self.assertEqual(float(half[0]), 0.5)
        self.assertGreater(float(at_mean[0]), float(half[0]))

    def test_language_lock_detects_en_es_flip(self) -> None:
        mu_en = np.array([0.8, 0.0], dtype=np.float64)
        mu_es = np.array([-0.8, 0.0], dtype=np.float64)
        x_en = np.array([[0.8, 0.0]], dtype=np.float64)
        x_es = np.array([[-0.8, 0.0]], dtype=np.float64)
        agree = v2.monolingual_consistency(x_en, [0], mu_en, mu_es, "en")
        flip = v2.monolingual_consistency(x_es, [0], mu_en, mu_es, "en")
        es_reward = v2.monolingual_consistency(x_es, [0], mu_en, mu_es, "es")
        self.assertEqual(float(agree[0]), 1.0)
        self.assertEqual(float(flip[0]), 0.0)
        self.assertEqual(float(es_reward[0]), 1.0)
        unlocked = np.array([0.5], dtype=np.float64)
        locked = v2.apply_language_lock(
            unlocked, mode="monolingual_consistency", locale_dims=[0], consistency=flip
        )
        self.assertEqual(float(locked[0]), 0.0)

    def test_language_lock_off_is_neutral(self) -> None:
        unlocked = np.array([0.42, 0.17], dtype=np.float64)
        off = v2.apply_language_lock(
            unlocked,
            mode="off",
            locale_dims=[0],
            consistency=np.zeros(2, dtype=np.float64),
            dropped_bonus_score=np.zeros(2, dtype=np.float64),
        )
        self.assertEqual(off.tobytes(), unlocked.tobytes())
        off[0] = np.float64(0.0)
        self.assertEqual(float(unlocked[0]), 0.42)

    def test_language_lock_empty_set_matches_unlocked(self) -> None:
        unlocked = np.array([0.42, 0.17], dtype=np.float64)
        for mode in ("off", "monolingual_consistency", "drop_positive_f3"):
            out = v2.apply_language_lock(
                unlocked,
                mode=mode,
                locale_dims=[],
                consistency=np.zeros(2, dtype=np.float64),
                dropped_bonus_score=np.zeros(2, dtype=np.float64),
            )
            self.assertEqual(out.tobytes(), unlocked.tobytes())

    def test_secondary_band_is_not_labeled_primary(self) -> None:
        self.assertEqual(v2.language_lock_band([], [], v2.SECONDARY_BAND), "primary")
        self.assertEqual(
            v2.language_lock_band(v2.SECONDARY_BAND, [], v2.SECONDARY_BAND),
            "secondary_band",
        )
        self.assertEqual(list(v2.SECONDARY_BAND), [202, 278, 408, 780, 871])

    def test_bundle_fold_keeps_full_doc_with_interval_clauses(self) -> None:
        ids = ["000000-cl", "000002-cl", "000001-full", "000004-cl", "000003-full", "000005-cl"]
        tags = ["clause_opt2c", "clause_opt2c", "full_doc", "clause_opt2c", "full_doc", "clause_opt2c"]
        refs = ["python"] * len(ids)
        bundles = v2.assign_document_bundle_ids(ids, tags)
        self.assertEqual(bundles.tolist(), [0, 0, 0, 1, 1, 1])
        folds = sim.assign_calibration_folds(ids, tags, refs, n_folds=5)
        np.testing.assert_array_equal(folds, bundles % 5)
        order = [5, 0, 3, 1, 4, 2]
        shuffled_ids = [ids[i] for i in order]
        shuffled_tags = [tags[i] for i in order]
        shuffled = v2.assign_document_bundle_ids(shuffled_ids, shuffled_tags)
        restored = np.empty(len(ids), dtype=np.int64)
        for new_pos, old in enumerate(order):
            restored[old] = shuffled[new_pos]
        np.testing.assert_array_equal(restored, bundles)

    def test_constant_source_ref_is_not_the_bundle_key(self) -> None:
        ids = ["000001-full", "000002-cl", "000003-full", "000004-cl"]
        tags = ["full_doc", "clause_opt2c", "full_doc", "clause_opt2c"]
        refs = ["python", "python", "python", "python"]
        bundles = v2.assign_document_bundle_ids(ids, tags)
        self.assertEqual(set(refs), {"python"})
        self.assertEqual(bundles.tolist(), [0, 0, 1, 1])
        self.assertGreater(len(set(bundles.tolist())), 1)
        folds = sim.assign_calibration_folds(ids, tags, refs, n_folds=5)
        np.testing.assert_array_equal(folds, bundles % 5)

    def test_short_query_boundaries_l_minus_one_l_and_l_plus_one(self) -> None:
        self.assertTrue(v2.short_query_uses_clause_model(11, 3, 12))
        self.assertTrue(v2.short_query_uses_clause_model(12, 3, 12))
        self.assertFalse(v2.short_query_uses_clause_model(13, 3, 12))
        self.assertTrue(v2.short_query_uses_clause_model(13, 1, 12))

    def test_extreme_short_punct_stays_closed(self) -> None:
        routed = v2.routed_surface_score(True, 0.99, 0.04)
        self.assertFalse(v2.score_clears_threshold(routed, 0.5))
        self.assertTrue(v2.score_clears_threshold(v2.routed_surface_score(False, 0.99, 0.04), 0.5))

    def test_base64_fail_closed_under_short_route(self) -> None:
        surface = v2.routed_surface_score(True, 0.99, 0.99)
        closed = v2.fail_closed_min(surface, np.array([0.01], dtype=np.float64))
        self.assertEqual(closed, 0.01)
        self.assertFalse(v2.score_clears_threshold(closed, 0.5))

    def test_flood_one_poison_blocked_by_max_gray_count(self) -> None:
        clauses = np.full(41, 0.95, dtype=np.float64)
        clauses[20] = np.float64(0.15)
        self.assertEqual(v2.gray_clause_count(clauses, 0.7), 1)
        self.assertLessEqual(1 / 41, 0.35)
        self.assertFalse(
            v2.passes_max_gray_count(0.95, clauses, t_full=0.5, t_hard=0.4, t_soft=0.7, max_gray_count=0)
        )
        self.assertFalse(
            v2.passes_max_gray_count(0.95, clauses, t_full=0.5, t_hard=0.4, t_soft=0.7, max_gray_count=1)
        )
        band = np.full(41, 0.95, dtype=np.float64)
        band[20] = np.float64(0.55)
        self.assertFalse(
            v2.passes_max_gray_count(0.95, band, t_full=0.5, t_hard=0.4, t_soft=0.7, max_gray_count=0)
        )
        self.assertTrue(
            v2.passes_max_gray_count(0.95, band, t_full=0.5, t_hard=0.4, t_soft=0.7, max_gray_count=1)
        )

    def test_flood_one_poison_blocked_by_blend(self) -> None:
        clauses = np.full(41, 0.95, dtype=np.float64)
        clauses[20] = np.float64(0.15)
        for weight in (0.3, 0.5, 0.7):
            blended = v2.blend_full_min_clause(0.95, clauses, weight)
            self.assertLess(blended, 0.80)
            self.assertFalse(v2.passes_blend_full_min_clause(0.95, clauses, weight, 0.80))
        self.assertAlmostEqual(v2.blend_full_min_clause(0.95, clauses, 0.7), 0.7 * 0.95 + 0.3 * 0.15, places=12)

    def test_flood_cap24_keeps_poison_and_base64_closed(self) -> None:
        clauses = np.full(41, 0.95, dtype=np.float64)
        clauses[20] = np.float64(0.15)
        idx = sim.compute_cap24_clause_indices(41)
        self.assertEqual(idx, list(range(8)) + list(range(16, 24)) + list(range(33, 41)))
        self.assertIn(20, idx)
        sliced = clauses[np.array(idx, dtype=np.int64)]
        self.assertFalse(
            v2.passes_max_gray_count(0.95, sliced, t_full=0.5, t_hard=0.4, t_soft=0.7, max_gray_count=1)
        )
        closed = v2.fail_closed_min(0.99, np.array([0.01], dtype=np.float64))
        self.assertEqual(closed, 0.01)
        self.assertFalse(v2.score_clears_threshold(closed, 0.5))

    def test_bootstrap_ci_is_bit_stable(self) -> None:
        cats, subs, _ids, y, scores = self._population()
        pred = scores >= np.float64(0.5)
        kwargs = {
            "seed": 0,
            "n_resamples": 1000,
            "frozen_f1": {"task012": 0.56, "task011": 0.44},
        }
        first = v2.bootstrap_stratified_ci(y, scores, pred, cats, subs, **kwargs)
        second = v2.bootstrap_stratified_ci(y, scores, pred, cats, subs, **kwargs)
        self.assertFalse(first["refits_thresholds"])
        for name in ("f1", "frr", "far", "roc_auc"):
            self.assertEqual(_f64_bytes(first[name]["low"]), _f64_bytes(second[name]["low"]))
            self.assertEqual(_f64_bytes(first[name]["high"]), _f64_bytes(second[name]["high"]))
        self.assertEqual(
            _f64_bytes(first["delta_f1"]["task012"]["ci95"]["low"]),
            _f64_bytes(second["delta_f1"]["task012"]["ci95"]["low"]),
        )
        self.assertLess(first["f1"]["low"], first["f1"]["high"])

    def test_repeated_oof_is_bit_stable(self) -> None:
        cats, subs, ids, y, scores = self._population()
        first = v2.repeated_stratified_oof(scores, y, cats, subs, ids)
        second = v2.repeated_stratified_oof(scores, y, cats, subs, ids)
        self.assertEqual(first["seeds"], [0, 1, 2, 3, 4])
        self.assertEqual(_f64_bytes(first["f1"]["mean"]), _f64_bytes(second["f1"]["mean"]))
        self.assertEqual(_f64_bytes(first["f1"]["std"]), _f64_bytes(second["f1"]["std"]))
        self.assertEqual(_f64_bytes(first["frr"]["mean"]), _f64_bytes(second["frr"]["mean"]))
        self.assertEqual(_f64_bytes(first["far"]["mean"]), _f64_bytes(second["far"]["mean"]))
        self.assertEqual(first["predictions"][0].tobytes(), second["predictions"][0].tobytes())
        folds = v2.assign_repeated_stratified_folds(cats, subs, ids, n_folds=5, seed=0)
        self.assertEqual(first["per_seed"][0]["fold_thresholds"], v2.oof_fold_thresholds(scores, y, folds))

    def test_oof_threshold_does_not_see_held_out_fold(self) -> None:
        cats, subs, ids, y, scores = self._population()
        folds = v2.assign_repeated_stratified_folds(cats, subs, ids, n_folds=5, seed=0)
        base = v2.oof_fold_thresholds(scores, y, folds)
        direct, _metrics = sim.fit_best_1d_threshold(scores[folds != 0], y[folds != 0])
        self.assertEqual(_f64_bytes(base[0]), _f64_bytes(direct))
        mutated_scores = scores.copy()
        mutated_y = y.copy()
        mutated_scores[folds == 0] = np.float64(0.0)
        mutated_y[folds == 0] = False
        moved = v2.oof_fold_thresholds(mutated_scores, mutated_y, folds)
        self.assertEqual(_f64_bytes(base[0]), _f64_bytes(moved[0]))

    def test_document_percentiles_exclude_holdout(self) -> None:
        cal = np.full(20, 0.42, dtype=np.float64)
        pct = v2.document_percentiles(cal)
        self.assertEqual(pct[0.05], 0.42)
        self.assertEqual(pct[0.10], 0.42)
        self.assertEqual(pct[0.15], 0.42)
        contaminated = np.concatenate((cal, np.zeros(20, dtype=np.float64)))
        self.assertNotEqual(float(np.quantile(contaminated, 0.05, method="linear")), 0.42)
        with self.assertRaises(ValueError):
            v2.document_percentiles(np.array([0.42], dtype=np.float64))

    def test_repeated_oof_labels_oracle_upper_bound(self) -> None:
        cats, subs, ids, y, scores = self._population()
        result = v2.repeated_stratified_oof(scores, y, cats, subs, ids)
        self.assertEqual(result["oracle_upper_bound"]["tag"], "[ORACLE_UPPER_BOUND]")
        self.assertIn("[ORACLE_UPPER_BOUND]", result["oracle_upper_bound"]["tag"])

    def test_frozen_headline_and_subtype_parse(self) -> None:
        text = "\n".join(
            [
                "| `python / full_only` | 0.4439 (11.00%/70.67%) | `1B_sigma3_1024d_F2L2` `[0.6, 0.0, 0.4]` (`hard_kill`) | 0.7780 | 0.4919 / 0.9223 | **0.5606** (19.00%/36.00%) | 0.5597 | 0.5655 (+0.0050) | **0.5625** (+0.0019) |",
                "| `python / clauses` | 0.4500 (37.00%/39.00%) | `bestF3_1B_gran_matched_K32M128_mul` `[0.0, 0.8, 0.2]` (`dual_zone`) | 0.8599 | 0.5835 / 0.9546 | **0.6723** (20.00%/19.33%) | 0.5792 | 0.7190 (+0.0467) | **0.6723** (+0.0000) |",
                "| `receta / full_only` | 0.4536 (12.00%/66.67%) | `bestF3_1A_gran_matched_K32M32_mul` `[0.1, 0.3, 0.6]` (`hard_kill`) | 0.8713 | 0.6316 / 0.9553 | **0.6975** (17.00%/18.33%) | **0.7000** | 0.7029 (+0.0054) | **0.6975** (+0.0000) |",
                "| `receta / clauses` | 0.3607 (56.00%/33.33%) | `1A_minmax_1024d_F2L2` `[0.1, 0.2, 0.7]` (`hard_kill_same`) | 0.8967 | 0.7202 / 0.9641 | **0.7257** (18.00%/14.67%) | 0.5195 | 0.7401 (+0.0144) | **0.7257** (+0.0000) |",
                "### python / `full_only` — Complete 37-Subtype Breakdown (`FRR` for In-Domain, `FAR` for OOD/Hybrid/Adversarial)",
                "| `IN_DOMAIN_VALID` (FRR) | `short_idiom_query` | 20 | 15.00% (3/20) | 55.00% | 40.00% |",
            ]
        )
        parsed = v2.parse_frozen_headlines(text)
        v2.verify_frozen_headlines(parsed)
        rows = v2.parse_frozen_subtypes(text)
        row = rows[("python", "full_only", "short_idiom_query")]
        self.assertEqual(row["n"], 20)
        self.assertEqual(row["task011_error"], 0.15)
        self.assertEqual(row["task012_oof_error"], 0.55)

    def test_recipe_names_cover_tail_and_base(self) -> None:
        names = v2.recipe_names()
        self.assertEqual(len(names), 22)
        self.assertEqual(len(set(names)), 22)
        channels = {
            "f1": np.array([0.2, 0.4], dtype=np.float64),
            "f2": np.array([0.4, 0.6], dtype=np.float64),
            "f3": np.array([0.6, 0.8], dtype=np.float64),
            "f3_drop_secondary": np.array([0.5, 0.7], dtype=np.float64),
            "polarity": np.array([0.1, 0.9], dtype=np.float64),
            "consistency_secondary": np.array([0.5, 1.0], dtype=np.float64),
            "tail": {p: np.full(2, np.float64(1.0) / np.float64(p + 1)) for p in v2.TAIL_PS},
        }
        base = np.mean(np.stack((channels["f1"], channels["f2"], channels["f3"])), axis=0)
        for name in names:
            vec = v2.recipe_vector(channels, name)
            self.assertEqual(vec.shape, (2,))
            self.assertEqual(vec.dtype, np.dtype(np.float64))
        np.testing.assert_array_equal(v2.recipe_vector(channels, "base"), base)
        self.assertEqual(v2.recipe_vector(channels, "base_drop_primary").tobytes(), base.tobytes())
        self.assertIn("tail_1", names)
        self.assertIn("tail_25_polarity_plus_base", names)

    def test_dim_spec_keeps_every_coordinate(self) -> None:
        spec = v2.dim_spec_all_coordinates(1024, np.array([3, 9], dtype=np.int64))
        self.assertEqual(spec.active_dims.tolist(), list(range(1024)))
        self.assertNotIn(3, spec.anchor_dims.tolist())
        self.assertNotIn(9, spec.anchor_dims.tolist())
        self.assertIn(3, spec.neg_sensor_dims.tolist())
        self.assertEqual(spec.anchor_dims.size + spec.neg_sensor_dims.size, 1024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
