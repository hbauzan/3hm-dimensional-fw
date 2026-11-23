#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "lancedb>=0.20.0",
#     "numpy>=2.0.0",
#     "pyarrow>=18.0.0",
# ]
# ///
"""Synthetic tests for the v3 directional replay. No LanceDB connection and no network."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import numpy as np

import fhv1_1_lexical_profile as lex
import fhv1_1_replay_sim as sim
import fhv1_1_replay_v2 as v2
import fhv1_1_replay_v3 as replay
import fhv1_1_xray as xray


def _no_tie_fit(dim: int = 1024, seed: int = 0) -> replay.DirectionalFit:
    rng = np.random.default_rng(seed)
    mu_t = rng.normal(0.0, 0.02, size=dim)
    gap = rng.uniform(0.02, 0.08, size=dim)
    sign = np.where(rng.random(dim) < 0.5, np.float64(-1.0), np.float64(1.0))
    mu_c = mu_t - sign * gap
    std = np.full(dim, np.float64(0.1))
    fit = replay.fit_directional(mu_t, std, mu_c, std)
    if fit.tie_count != 0 or np.any(fit.direction == 0.0):
        raise RuntimeError("no-tie fixture produced a tie")
    return fit


def _strata(n_pos: int = 10, n_neg: int = 10) -> tuple[np.ndarray, list[str], list[str], list[str]]:
    y = np.array([True] * n_pos + [False] * n_neg)
    categories = ["IN_DOMAIN_VALID"] * n_pos + ["ADVERSARIAL_FUZZING"] * n_neg
    subtypes = ["valid_impl"] * n_pos + ["payload"] * n_neg
    input_ids = [f"{i:04d}" for i in range(n_pos + n_neg)]
    return y, categories, subtypes, input_ids


def _prompt_bundle() -> sim.PromptBundle:
    vectors = np.zeros((4, 2), dtype=np.float64)
    return sim.PromptBundle(
        granularity="clauses",
        input_ids=("p0", "p1"),
        categories=("IN_DOMAIN_VALID", "ADVERSARIAL_FUZZING"),
        subtypes=("valid_impl", "payload"),
        expected_pass=np.array([True, False]),
        strat_folds=np.array([0, 1], dtype=np.int64),
        chunk_strategies=("full_doc", "full_doc", "full_doc", "clause_opt2c"),
        chunk_vectors=vectors,
        chunk_norm_z=None,
        full_chunk_idx=np.array([0, 2], dtype=np.int64),
        b64_chunk_slices=(np.array([1], dtype=np.int64), np.zeros(0, dtype=np.int64)),
        clause_chunk_slices=(np.zeros(0, dtype=np.int64), np.array([3], dtype=np.int64)),
        clause_cap24_slices=(np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)),
        baseline_passed=np.array([True, False]),
    )


class DirectionalContractTest(unittest.TestCase):
    def test_eps_sigma_is_the_margin_denominator(self) -> None:
        self.assertEqual(float(sim.EPS_SIGMA), 1e-9)
        fit = replay.fit_directional(
            np.array([1.0]),
            np.array([0.2]),
            np.array([-1.0]),
            np.array([0.2]),
        )
        row = np.array([[fit.std_pool[0] + np.float64(sim.EPS_SIGMA)]])
        margin = replay.directional_margin(row, fit)
        self.assertEqual(float(margin[0, 0]), 1.0)

    def test_std_pool_matches_coordinate_contrast_stats(self) -> None:
        target = np.array([[0.0, 1.0], [2.0, 3.0], [4.0, 5.0]], dtype=np.float64)
        contrast = np.array([[1.0, 0.0], [1.5, 2.0], [0.5, 4.0]], dtype=np.float64)
        fit = replay.fit_directional_matrices(target, contrast)
        moments_t = xray.compute_coordinate_moments(target, expected_dim=2)
        moments_c = xray.compute_coordinate_moments(contrast, expected_dim=2)
        expected_pool = np.sqrt((moments_t.std_dev_sample**2 + moments_c.std_dev_sample**2) / np.float64(2.0))
        _snr_t, _snr_c, _rms_t, _rms_c, sep, _ratio = xray.coordinate_contrast_stats(
            moments_t.mean,
            moments_t.std_dev_sample,
            moments_c.mean,
            moments_c.std_dev_sample,
        )
        np.testing.assert_array_equal(fit.std_t, moments_t.std_dev_sample)
        np.testing.assert_array_equal(fit.std_c, moments_c.std_dev_sample)
        np.testing.assert_array_equal(fit.std_pool, expected_pool)
        np.testing.assert_array_equal(fit.sep, sep)
        np.testing.assert_array_equal(fit.direction, np.sign(moments_t.mean - moments_c.mean))

    def test_direction_is_zero_only_on_exact_equality(self) -> None:
        fit = replay.fit_directional(
            np.array([0.2, 0.06, -0.2]),
            np.array([0.1, 0.1, 0.1]),
            np.array([0.2, 0.01, 0.2]),
            np.array([0.1, 0.1, 0.1]),
        )
        self.assertEqual(float(fit.direction[0]), 0.0)
        self.assertEqual(int(fit.tie_count), 1)
        self.assertEqual(float(fit.direction[1]), 1.0)
        self.assertEqual(float(fit.direction[2]), -1.0)
        self.assertGreater(float(fit.mu_t[1] * fit.mu_c[1]), 0.0)

    def test_tie_coordinate_does_not_move_the_score(self) -> None:
        fit = replay.fit_directional(
            np.array([0.2, 0.4]),
            np.array([0.1, 0.1]),
            np.array([0.2, -0.3]),
            np.array([0.1, 0.1]),
        )
        base = fit.midpoint.reshape(1, -1).copy()
        moved = base.copy()
        moved[0, 0] += np.float64(5.0)
        for variant in replay.DIR_VARIANTS:
            left = replay.score_dir1024(base, fit, variant)
            right = replay.score_dir1024(moved, fit, variant)
            np.testing.assert_array_equal(left, right)

    def test_weights_stay_positive_when_separation_is_zero(self) -> None:
        fit = replay.fit_directional(
            np.array([0.2, 0.0]),
            np.array([0.1, 0.1]),
            np.array([-0.2, 0.0]),
            np.array([0.1, 0.1]),
        )
        self.assertEqual(float(fit.sep[1]), 0.0)
        for variant in replay.DIR_VARIANTS:
            weights = replay.variant_weights(fit, variant)
            self.assertEqual(weights.shape, (2,))
            self.assertTrue(np.all(weights > 0.0))
            self.assertTrue(np.all(np.isfinite(weights)))

    def test_1024_mutation_changes_every_variant(self) -> None:
        fit = _no_tie_fit(1024)
        self.assertEqual(fit.dim, 1024)
        self.assertEqual(fit.tie_count, 0)
        base = fit.midpoint.reshape(1, -1)
        mutated = np.repeat(base, 1024, axis=0)
        mutated[np.arange(1024), np.arange(1024)] += np.float64(1.0)
        for variant in replay.DIR_VARIANTS:
            weights = replay.variant_weights(fit, variant)
            self.assertEqual(weights.shape, (1024,))
            self.assertTrue(np.all(weights > 0.0))
            base_score = replay.score_dir1024(base, fit, variant)
            moved = replay.score_dir1024(mutated, fit, variant)
            self.assertEqual(moved.shape, (1024,))
            self.assertTrue(np.all(np.isfinite(moved)))
            self.assertTrue(np.all(moved != base_score[0]))

    def test_same_sign_coordinate_changes_the_score(self) -> None:
        mu_t = np.array([0.06, 0.20, -0.20])
        mu_c = np.array([0.01, -0.20, 0.20])
        std = np.full(3, np.float64(0.05))
        fit = replay.fit_directional(mu_t, std, mu_c, std)
        self.assertEqual(float(fit.direction[0]), 1.0)
        self.assertGreater(float(fit.mu_t[0] * fit.mu_c[0]), 0.0)
        self.assertEqual(fit.tie_count, 0)
        base = fit.midpoint.reshape(1, -1).copy()
        moved = base.copy()
        moved[0, 0] += np.float64(0.5)
        for variant in replay.DIR_VARIANTS:
            self.assertGreater(float(replay.variant_weights(fit, variant)[0]), 0.0)
            before = replay.score_dir1024(base, fit, variant)
            after = replay.score_dir1024(moved, fit, variant)
            self.assertNotEqual(float(before[0]), float(after[0]))
            self.assertTrue(np.isfinite(before[0]) and np.isfinite(after[0]))

    def test_dir_variants_match_the_weighted_formulas(self) -> None:
        fit = _no_tie_fit(8, seed=3)
        rng = np.random.default_rng(4)
        rows = rng.normal(size=(5, 8))
        margin = replay.directional_margin(rows, fit)
        sigmoid = np.float64(1.0) / (np.float64(1.0) + np.exp(-np.clip(margin, -60.0, 60.0)))
        clipped = np.clip(np.float64(0.5) + np.float64(0.5) * margin, 0.0, 1.0)
        boost = np.where(fit.mu_t * fit.mu_c < 0.0, np.float64(1.5), np.float64(1.0))
        formulas = {
            "dir1024_sig_sep": (sigmoid, np.maximum(fit.sep, np.float64(0.05))),
            "dir1024_sig_sep2": (sigmoid, np.maximum(fit.sep * fit.sep, np.float64(0.01))),
            "dir1024_clip_polboost": (clipped, np.maximum(fit.sep, np.float64(0.05)) * boost),
        }
        for variant, (atom, weights) in formulas.items():
            expected = (atom * weights).sum(axis=1) / np.sum(weights)
            np.testing.assert_array_equal(replay.score_dir1024(rows, fit, variant), expected)

    def test_unknown_variant_and_bad_shapes_raise(self) -> None:
        fit = _no_tie_fit(4, seed=5)
        with self.assertRaises(ValueError):
            replay.variant_weights(fit, "dir_missing")
        with self.assertRaises(ValueError):
            replay.directional_margin(np.zeros((2, 3)), fit)
        with self.assertRaises(ValueError):
            replay.fit_directional_matrices(np.zeros((0, 4)), np.ones((3, 4)))
        with self.assertRaises(ValueError):
            replay.fit_directional_matrices(np.ones((3, 4)), np.array([[np.nan, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]]))


class GuardAndRepairTest(unittest.TestCase):
    def test_base_repaired_keeps_sign_flip_anchor(self) -> None:
        sep = np.array([1.5, 0.4, 0.9])
        drop = replay.anchor_drop_dims(sep, [0, 1])
        self.assertNotIn(0, drop.tolist())
        self.assertIn(1, drop.tolist())
        self.assertIn(2, drop.tolist())
        mu = np.array([1.0, 0.0, 0.0])
        sigma = np.array([0.1, 0.1, 0.1])
        far = np.array([[8.0, 0.0, 0.0]])
        kept = v2.positive_f3_bonus(far, mu, sigma, drop)
        starved = v2.positive_f3_bonus(far, mu, sigma, np.array([0, 1, 2], dtype=np.int64))
        self.assertLess(float(kept[0]), 1.0)
        self.assertEqual(float(starved[0]), 1.0)
        f1 = np.array([0.4])
        f2 = np.array([0.6])
        repaired = replay.base_repaired_from_factors(f1, f2, kept)
        wrong = replay.base_repaired_from_factors(f1, f2, starved)
        np.testing.assert_array_equal(repaired, np.mean(np.stack([f1, f2, kept]), axis=0))
        self.assertNotEqual(float(repaired[0]), float(wrong[0]))

    def test_polarity_v2_subset_calls_polarity_score(self) -> None:
        classification = {
            "dimensions": [
                {"bucket": "POLARITY_FLIP_DIALS", "sep": 0.8, "mean_T": 0.4, "mean_C": -0.2, "dim": 1},
                {"bucket": "FIRM_DOMAIN_ANCHOR", "sep": 2.0, "mean_T": 0.5, "mean_C": 0.1, "dim": 0},
                {"bucket": "POLARITY_FLIP_DIALS", "sep": 0.2, "mean_T": -0.4, "mean_C": 0.3, "dim": 2},
            ]
        }
        vectors = np.array(
            [[0.5, -0.2, 0.1], [0.0, 0.3, -0.4], [-0.1, 0.0, 0.2]],
            dtype=np.float64,
        )
        idx, mu = v2.dials_from_classification(classification)
        expected = v2.polarity_score(vectors, idx, mu)
        np.testing.assert_array_equal(replay.polarity_v2_subset(vectors, classification), expected)
        self.assertEqual(idx.tolist(), [1])

    def test_tail_channel_delegates(self) -> None:
        rng = np.random.default_rng(6)
        vectors = rng.normal(size=(7, 5))
        mu = np.mean(vectors, axis=0)
        sigma = np.std(vectors, axis=0, ddof=1)
        got = replay.tail_channel(vectors, mu, sigma, 5, 1.25)
        expected = v2.tail_scores_all_dimensions(vectors, mu, sigma, 5, 1.25)
        np.testing.assert_array_equal(got, expected)

    def test_additive_and_multiplicative_guard_numerics(self) -> None:
        s_dir = np.array([0.8, 0.2, 0.5], dtype=np.float64)
        s_guard = np.array([0.4, 0.9, 0.1], dtype=np.float64)
        alpha = np.float64(0.20)
        added = replay.couple_additive(s_dir, s_guard, float(alpha))
        multiplied = replay.couple_multiplicative(s_dir, s_guard, float(alpha))
        np.testing.assert_array_equal(added, (np.float64(1.0) - alpha) * s_dir + alpha * s_guard)
        np.testing.assert_array_equal(multiplied, np.power(s_dir, np.float64(1.0) - alpha) * np.power(s_guard, alpha))
        self.assertFalse(np.allclose(added, multiplied))

    def test_alpha_zero_is_exactly_the_directional_score(self) -> None:
        s_dir = np.array([0.2, 0.7], dtype=np.float64)
        s_guard = np.array([0.9, 0.1], dtype=np.float64)
        np.testing.assert_array_equal(replay.couple_additive(s_dir, s_guard, 0.0), s_dir)
        np.testing.assert_array_equal(replay.couple_multiplicative(s_dir, s_guard, 0.0), s_dir)

    def test_struct_one_is_the_identity_for_both_hooks(self) -> None:
        semantic = np.array([0.25, 0.8, 0.1], dtype=np.float64)
        ones = np.ones(3, dtype=np.float64)
        for beta in replay.BETAS:
            np.testing.assert_array_equal(replay.apply_beta_struct(semantic, ones, beta), semantic)
        for gamma in replay.GAMMAS:
            np.testing.assert_array_equal(replay.apply_gamma_struct(semantic, ones, gamma), semantic)
        partial = np.array([1.0, 0.5, 1.0])
        beta = replay.apply_beta_struct(semantic, partial, 0.30)
        self.assertEqual(float(beta[0]), float(semantic[0]))
        self.assertEqual(float(beta[2]), float(semantic[2]))
        self.assertNotEqual(float(beta[1]), float(semantic[1]))

    def test_beta_and_gamma_match_the_written_formulas(self) -> None:
        semantic = np.array([0.6, 0.4], dtype=np.float64)
        struct = np.array([0.5, 0.8], dtype=np.float64)
        np.testing.assert_array_equal(
            replay.apply_beta_struct(semantic, struct, 0.15),
            semantic * (np.float64(1.0) - np.float64(0.15) * (np.float64(1.0) - struct)),
        )
        np.testing.assert_array_equal(
            replay.apply_gamma_struct(semantic, struct, 0.25),
            semantic * np.power(struct, np.float64(0.25)),
        )

    def test_poisoned_clause_moves_only_the_min_hook(self) -> None:
        prose = "The function returns the sum of two integers and checks the sign."
        docs = [prose for _ in range(12)]
        clean = [prose for _ in range(4)]
        poison = "@" * 160
        full_profile = lex.fit(docs, "full_doc")
        clause_profile = lex.fit(clean, "clause_opt2c")
        poison_score = lex.score(poison, clause_profile).s_struct
        self.assertLess(poison_score, 1.0)
        clean_scored = replay.score_struct_corpus([prose], [clean], full_profile, clause_profile, time_calls=False)
        poison_scored = replay.score_struct_corpus(
            [prose],
            [clean[:2] + [poison]],
            full_profile,
            clause_profile,
            time_calls=False,
        )
        self.assertEqual(float(clean_scored["s_full"][0]), float(poison_scored["s_full"][0]))
        self.assertLess(float(poison_scored["s_min"][0]), float(clean_scored["s_min"][0]))
        reference = lex.score_clauses(prose, clean[:2] + [poison], full_profile, clause_profile)
        self.assertEqual(float(poison_scored["s_full"][0]), reference.full_doc.s_struct)
        self.assertEqual(float(poison_scored["s_min"][0]), reference.s_struct)
        full_only, reduced = replay.struct_reductions(0.9, [1.0, 0.2, 1.0])
        untouched, still = replay.struct_reductions(0.9, [1.0, 1.0, 1.0])
        self.assertEqual(full_only, untouched)
        self.assertEqual(reduced, 0.2)
        self.assertEqual(still, 0.9)

    def test_empty_clause_list_matches_score_clauses(self) -> None:
        text = "Return the absolute value of the integer argument."
        profile = lex.fit([text, text + " Also return zero."], "full_doc")
        clause_profile = lex.fit([text], "clause_opt2c")
        reference = lex.score_clauses(text, [], profile, clause_profile)
        _full, reduced = replay.struct_reductions(reference.full_doc.s_struct, [])
        self.assertEqual(reduced, reference.s_struct)

    def test_non_finite_hooks_raise(self) -> None:
        good = np.array([0.2, 0.4])
        bad = np.array([0.2, np.nan])
        with self.assertRaises(ValueError):
            replay.couple_additive(good, bad, 0.1)
        with self.assertRaises(ValueError):
            replay.couple_multiplicative(good, np.array([0.2, np.inf]), 0.1)
        with self.assertRaises(ValueError):
            replay.apply_beta_struct(good, bad, 0.1)
        with self.assertRaises(ValueError):
            replay.apply_gamma_struct(bad, good, 0.1)
        with self.assertRaises(ValueError):
            replay.struct_reductions(float("nan"), [0.2])
        with self.assertRaises(ValueError):
            replay.base_repaired_from_factors(good, good, bad)


class SelectionAndAggregationTest(unittest.TestCase):
    def test_threshold_matrix_matches_scalar_including_ties(self) -> None:
        rng = np.random.default_rng(7)
        scores = rng.random((36, 5))
        scores[8:14, 1] = scores[8, 1]
        scores[:, 2] = np.float64(0.5)
        scores[0, 3] = scores[1, 3]
        y = np.array([index % 2 == 0 for index in range(36)])
        thresholds, f1, _err = replay.fit_best_thresholds_matrix(scores, y)
        for col in range(scores.shape[1]):
            threshold, metrics = sim.fit_best_1d_threshold(scores[:, col], y)
            self.assertEqual(float(thresholds[col]), float(threshold))
            self.assertEqual(float(f1[col]), float(metrics["f1"]))

    def test_nested_selector_ignores_the_held_out_fold(self) -> None:
        scores = np.zeros((12, 2), dtype=np.float64)
        y = np.array([True, True, True, True, False, False, False, False, True, True, False, False])
        train = np.arange(8, dtype=np.int64)
        test = np.arange(8, 12, dtype=np.int64)
        scores[0:4, 0] = 0.9
        scores[4:8, 0] = 0.1
        scores[8:10, 0] = 0.0
        scores[10:12, 0] = 1.0
        scores[0:8, 1] = 0.5
        scores[8:10, 1] = 1.0
        scores[10:12, 1] = 0.0
        chosen, threshold, train_f1 = replay.select_recipe_on_train(scores, y, train)
        poisoned = scores.copy()
        poisoned[test] = 1.0 - poisoned[test]
        chosen_poison, threshold_poison, f1_poison = replay.select_recipe_on_train(poisoned, y, train)
        chosen_all, _threshold_all, _f1_all = replay.select_recipe_on_train(scores, y, np.arange(12))
        self.assertEqual(chosen, 0)
        self.assertEqual(chosen_poison, chosen)
        self.assertEqual(threshold_poison, threshold)
        self.assertEqual(f1_poison, train_f1)
        self.assertEqual(chosen_all, 1)
        with self.assertRaises(ValueError):
            replay.select_recipe_on_train(scores, y, np.zeros(0, dtype=np.int64))

    def test_cal_only_percentile_ignores_holdout_scores_and_labels(self) -> None:
        cal = np.linspace(0.1, 1.0, 10)
        hold_a = np.array([0.0, 1.0, 0.2, 0.8])
        hold_b = np.array([0.95, 0.05, 0.4, 0.6])
        y = np.array([True, True, False, False])
        first = replay.evaluate_cal_only(cal, hold_a, y)
        second = replay.evaluate_cal_only(cal, hold_b, y)
        flipped = replay.evaluate_cal_only(cal, hold_a, ~y)
        shifted = replay.evaluate_cal_only(cal + np.float64(3.0), hold_a, y)
        for probability, tag in replay.PROB_TAGS:
            expected = float(np.quantile(cal, np.float64(probability), method="linear"))
            self.assertEqual(first[tag]["threshold"], expected)
            self.assertEqual(second[tag]["threshold"], expected)
            self.assertEqual(flipped[tag]["threshold"], expected)
        self.assertNotEqual(first["p10"]["threshold"], shifted["p10"]["threshold"])
        self.assertTrue(all(np.isfinite(first[tag]["f1"]) for _prob, tag in replay.PROB_TAGS))

    def test_base64_fail_closed_min_is_preserved(self) -> None:
        bundle = _prompt_bundle()
        scores = np.array([0.9, 0.2, 0.8, 0.4], dtype=np.float64)
        surface, clause_min = replay.holdout_parts(scores, bundle)
        self.assertEqual(float(surface[0]), v2.fail_closed_min(0.9, np.array([0.2])))
        self.assertEqual(float(surface[1]), v2.fail_closed_min(0.8, np.zeros(0, dtype=np.float64)))
        self.assertEqual(float(clause_min[0]), 0.9)
        self.assertEqual(float(clause_min[1]), 0.4)
        self.assertLess(float(surface[0]), 0.9)
        blended = replay.blend_documents(surface, clause_min, 0.35)
        for index in range(2):
            self.assertEqual(
                float(blended[index]),
                v2.blend_full_min_clause(float(surface[index]), np.array([clause_min[index]]), 0.35),
            )

    def test_calibration_clause_min_keeps_an_empty_bundle(self) -> None:
        full = np.array([0.8, 0.4, 0.6])
        clause_min = replay.calibration_clause_min(
            full,
            np.array([0.2, 0.5]),
            np.array([0, 0], dtype=np.int64),
            3,
        )
        np.testing.assert_array_equal(clause_min, np.array([0.2, 0.4, 0.6]))

    def test_repeated_oof_is_bit_stable_at_seed_zero(self) -> None:
        rng = np.random.default_rng(8)
        y, categories, subtypes, input_ids = _strata(20, 20)
        scores = rng.random(40)
        scores[:20] += 0.4
        first = replay.repeated_stratified_oof(scores, y, categories, subtypes, input_ids)
        second = replay.repeated_stratified_oof(scores, y, categories, subtypes, input_ids)
        self.assertEqual(first["seeds"][0], 0)
        self.assertEqual(first["f1"]["mean"], second["f1"]["mean"])
        self.assertEqual(first["f1"]["std"], second["f1"]["std"])
        self.assertEqual(first["oracle_upper_bound"]["tag"], "[ORACLE_UPPER_BOUND]")
        for left, right in zip(first["predictions"], second["predictions"]):
            np.testing.assert_array_equal(left, right)
        for left, right in zip(first["per_seed"], second["per_seed"]):
            self.assertEqual(left["fold_thresholds"], right["fold_thresholds"])

    def test_nested_oof_is_bit_stable_at_seed_zero(self) -> None:
        rng = np.random.default_rng(9)
        y, categories, subtypes, input_ids = _strata(20, 20)
        matrix = rng.random((40, 3))
        matrix[:20, 0] += 0.35
        first = replay.nested_repeated_oof(matrix, y, categories, subtypes, input_ids)
        second = replay.nested_repeated_oof(matrix, y, categories, subtypes, input_ids)
        self.assertEqual(first["seeds"], [0, 1, 2, 3, 4])
        self.assertEqual(first["f1"], second["f1"])
        self.assertEqual(first["modal_column"], second["modal_column"])
        self.assertEqual(first["oracle_upper_bound"]["tag"], "[ORACLE_UPPER_BOUND]")
        for left, right in zip(first["predictions"], second["predictions"]):
            np.testing.assert_array_equal(left, right)
        clean, oracle = replay.detach_oracle(dict(first))
        self.assertNotIn("oracle_upper_bound", clean)
        self.assertEqual(oracle["tag"], "[ORACLE_UPPER_BOUND]")
        self.assertNotIn("[ORACLE_UPPER_BOUND]", str(clean))

    def test_bootstrap_is_bit_stable_and_refits_thresholds(self) -> None:
        y, categories, subtypes, _ids = _strata(12, 12)
        hold = np.concatenate([np.full(12, 0.85), np.full(12, 0.15)])
        cal = np.array([0.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float64)
        methods = {"a": (hold, cal), "b": (1.0 - hold, cal + np.float64(0.05))}
        draws_cal, draws_hold = replay.bootstrap_resample_indices(cal.shape[0], categories, subtypes, seed=0, n_resamples=24)
        manual = []
        thresholds = []
        for cal_idx, hold_idx in zip(draws_cal, draws_hold):
            threshold = float(np.quantile(cal[cal_idx], np.float64(0.10), method="linear"))
            thresholds.append(threshold)
            pred = hold[hold_idx] >= np.float64(threshold)
            manual.append(float(sim.compute_confusion_metrics(y[hold_idx], pred)["f1"]))
        self.assertGreater(len(set(np.round(thresholds, 12))), 1)
        self.assertGreater(len(set(np.round(manual, 12))), 1)
        first = replay.bootstrap_cal_only_paired(methods, y, categories, subtypes, seed=0, n_resamples=24)
        second = replay.bootstrap_cal_only_paired(methods, y, categories, subtypes, seed=0, n_resamples=24)
        self.assertTrue(first["refits_thresholds"])
        self.assertEqual(first["seed"], 0)
        self.assertEqual(first["methods"]["a"]["f1"], second["methods"]["a"]["f1"])
        self.assertEqual(first["methods"]["b"]["roc_auc"], second["methods"]["b"]["roc_auc"])
        manual_arr = np.array(manual, dtype=np.float64)
        self.assertEqual(first["methods"]["a"]["f1"]["low"], float(np.quantile(manual_arr, 0.025, method="linear")))
        self.assertEqual(first["methods"]["a"]["f1"]["high"], float(np.quantile(manual_arr, 0.975, method="linear")))
        self.assertTrue(np.isfinite(first["methods"]["a"]["f1"]["low"]))
        with self.assertRaises(ValueError):
            replay.bootstrap_cal_only_paired(methods, y, categories, subtypes, seed=0, n_resamples=1)

    def test_detach_oracle_rejects_a_missing_tag(self) -> None:
        with self.assertRaises(RuntimeError):
            replay.detach_oracle({"oracle_upper_bound": {"f1": 1.0}})
        untouched, missing = replay.detach_oracle({"f1": 0.5})
        self.assertIsNone(missing)
        self.assertEqual(untouched["f1"], 0.5)

    def test_public_pipeline_arrays_have_no_nan_or_inf(self) -> None:
        fit = _no_tie_fit(6, seed=11)
        rows = np.random.default_rng(12).normal(size=(9, 6))
        directional = replay.score_dir1024(rows, fit, "dir1024_sig_sep")
        guard = replay.score_dir1024(rows, fit, "dir1024_clip_polboost")
        struct = np.linspace(0.4, 1.0, 9)
        pieces = [
            directional,
            replay.couple_additive(directional, guard, 0.1),
            replay.couple_multiplicative(directional, guard, 0.1),
            replay.apply_beta_struct(directional, struct, 0.2),
            replay.apply_gamma_struct(directional, struct, 0.5),
        ]
        for piece in pieces:
            self.assertTrue(np.all(np.isfinite(piece)))
            self.assertFalse(np.any(np.isnan(piece)))
            self.assertFalse(np.any(np.isinf(piece)))


class SweepAndJoinTest(unittest.TestCase):
    def test_mode_parser_keeps_default_and_accepts_v2_v3(self) -> None:
        parser = sim.build_arg_parser()
        self.assertEqual(parser.parse_args([]).mode, "default")
        self.assertEqual(parser.parse_args(["--mode", "v2"]).mode, "v2")
        self.assertEqual(parser.parse_args(["--mode", "v3"]).mode, "v3")
        self.assertEqual(parser.parse_args([]).bg_parquet, Path("data/fhv1_1_research/background_embeddings_1k.parquet"))

    def test_sweep_has_no_hardcoded_quarter_blend(self) -> None:
        self.assertEqual(replay.ALPHAS, (0.00, 0.05, 0.10, 0.15, 0.20, 0.30))
        self.assertEqual(replay.BETAS, (0.00, 0.05, 0.10, 0.15, 0.20, 0.30))
        self.assertEqual(replay.GAMMAS, (0.10, 0.25, 0.50))
        self.assertEqual(replay.W_F, (0.20, 0.35, 0.50, 0.70))
        self.assertNotIn(0.25, replay.ALPHAS)
        self.assertEqual(replay.GUARDS, ("f2_l2", "tail_p5", "tail_p10", "tail_p25"))
        self.assertEqual(replay.TAIL_P, (3, 5, 10, 25))

    def test_alpha_zero_is_one_identity_column(self) -> None:
        specs = replay.iter_recipe_specs("full_only")
        family = replay.DIR_VARIANTS[0]
        alpha_zero = [spec for spec in specs if spec.family == family and spec.alpha == 0.0]
        self.assertEqual(len(alpha_zero), len(replay.BETAS) + len(replay.GAMMAS))
        self.assertTrue(all(spec.coupling == "identity" and spec.guard is None for spec in alpha_zero))
        alpha_open = [spec for spec in specs if spec.family == family and spec.alpha == 0.10]
        self.assertEqual({spec.coupling for spec in alpha_open}, {"additive", "multiplicative"})
        self.assertEqual({spec.guard for spec in alpha_open}, set(replay.GUARDS))

    def test_grid_catalog_counts(self) -> None:
        n_semantic = 1 + (len(replay.ALPHAS) - 1) * 2 * len(replay.GUARDS)
        n_struct = len(replay.BETAS) + len(replay.GAMMAS)
        per_family = n_semantic * n_struct
        full = replay.iter_recipe_specs("full_only")
        clauses = replay.iter_recipe_specs("clauses")
        self.assertEqual(len(full), len(replay.DIR_VARIANTS) * per_family + len(replay.BASELINES) * n_struct)
        self.assertEqual(len(clauses), len(full) * len(replay.W_F) * 2)
        self.assertEqual(len({spec.name() for spec in clauses}), len(clauses))
        self.assertTrue(all(spec.alpha == 0.0 and spec.guard is None for spec in full if spec.family in replay.BASELINES))
        self.assertGreaterEqual(len(full), 30)

    def test_struct_identity_survives_recipe_application(self) -> None:
        semantic = np.array([0.3, 0.7], dtype=np.float64)
        channels = {name: semantic for name in (*replay.DIR_VARIANTS, *replay.BASELINES, *replay.GUARDS)}
        struct = {"full_doc": np.ones(2), "min_full_clause": np.ones(2)}
        spec = replay.RecipeSpec(
            family="dir1024_sig_sep",
            coupling="identity",
            alpha=0.0,
            guard=None,
            struct_hook="gamma",
            beta=0.0,
            gamma=0.50,
            struct_reduction="full_doc",
            w_f=None,
        )
        np.testing.assert_array_equal(replay._apply_spec(spec, channels, struct), semantic)

    def test_candidate_hash_finds_a_homoglyph_after_normalization(self) -> None:
        text = "keep \u03bfnly this line"
        stripped = text.strip()
        normalized = xray.normalize_input_text(stripped)
        self.assertNotEqual(stripped, normalized)
        digests = replay.candidate_hashes(text)
        strip_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
        norm_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        self.assertIn(strip_hash, digests)
        self.assertIn(norm_hash, digests)
        self.assertNotEqual(strip_hash, norm_hash)
        joined = replay.join_full_doc_texts([norm_hash], {norm_hash: text})
        self.assertEqual(joined, [text])

    def test_hash_join_stops_and_reports_the_miss_count(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            replay.join_full_doc_texts(["aa", "bb", "cc"], {"aa": "one"})
        self.assertIn("miss_count=2", str(caught.exception))
        with self.assertRaises(TypeError):
            replay.candidate_hashes(None)  # type: ignore[arg-type]

    def test_geometry_oof_is_finite_and_rejects_non_finite_input(self) -> None:
        rng = np.random.default_rng(13)
        cal = rng.normal(size=(10, 25))
        folds = np.arange(10) % 5
        bundles = np.arange(10, dtype=np.int64)
        level = replay.fit_geometry_level(cal, folds, bundles, 10)
        self.assertTrue(np.all(np.isfinite(level.cal_f1)))
        self.assertTrue(np.all(np.isfinite(level.cal_f2)))
        for values in level.cal_tail.values():
            self.assertTrue(np.all(np.isfinite(values)))
        hold_f1, hold_f2, hold_tail = replay.score_geometry_holdout(level, rng.normal(size=(3, 25)))
        self.assertTrue(np.all(np.isfinite(hold_f1)))
        self.assertTrue(np.all(np.isfinite(hold_f2)))
        self.assertTrue(all(np.all(np.isfinite(values)) for values in hold_tail.values()))
        broken = cal.copy()
        broken[0, 0] = np.nan
        with self.assertRaises(ValueError):
            replay.fit_geometry_level(broken, folds, bundles, 10)

    def test_output_dir_under_reports_or_data_is_refused(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with self.assertRaises(RuntimeError):
            replay._reject_tracked_output(repo / "reports")
        with self.assertRaises(RuntimeError):
            replay._reject_tracked_output(repo / "data" / "fhv1_1_id_v3")

    def test_published_task013_headlines_parse(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        text = (repo / "reports" / "fhv1_1_id_v2_report.md").read_text(encoding="utf-8")
        parsed = replay.parse_task013_headlines(text)
        replay.verify_task013_headlines(parsed)
        task012 = v2.parse_frozen_headlines((repo / "reports" / "fhv1_1_xray_and_replay_report.md").read_text(encoding="utf-8"))
        v2.verify_frozen_headlines(task012)
        rates = {f"{domain}/{gran}": v2.frozen_rates(row) for (domain, gran), row in task012.items()}
        frozen = replay.frozen_f1_for_cell("python", "full_only", rates, parsed)
        self.assertEqual(frozen["task013_cal_p10_f1"], float(np.float64("0.6338028169014085")))
        self.assertEqual(frozen["task012_f1"], float(np.float64(rates["python/full_only"]["task012_f1"])))


if __name__ == "__main__":
    unittest.main()
