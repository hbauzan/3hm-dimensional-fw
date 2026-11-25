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
"""Synthetic tests for the v4 dual-axis replay. No LanceDB connection and no network."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import fhv1_1_id_v4_report as v4_report
import fhv1_1_lexical_profile as lex
import fhv1_1_replay_sim as sim
import fhv1_1_replay_v2 as v2
import fhv1_1_replay_v3 as v3
import fhv1_1_replay_v4 as replay
import fhv1_1_xray as xray


def _unit_rows(n: int, dim: int, seed: int, *, center: np.ndarray | None = None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(0.0, 1.0, size=(n, dim))
    if center is not None:
        raw = raw * 0.05 + np.asarray(center, dtype=np.float64)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    return (raw / norms).astype(np.float64)


def _separated_target_contrast(n_target: int = 40, n_contrast: int = 30, dim: int = 32, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    direction = rng.normal(0.0, 1.0, size=dim)
    direction = direction / np.linalg.norm(direction)
    target = _unit_rows(n_target, dim, seed + 1, center=direction * 0.4)
    contrast = _unit_rows(n_contrast, dim, seed + 2, center=-direction * 0.4)
    return target, contrast


def _strata(n_pos: int, n_neg: int) -> tuple[np.ndarray, list[str], list[str], list[str]]:
    y = np.array([True] * n_pos + [False] * n_neg, dtype=bool)
    categories = (
        ["IN_DOMAIN_VALID"] * n_pos
        + ["OUT_OF_DOMAIN_BENIGN"] * (n_neg // 2)
        + ["ADVERSARIAL_FUZZING"] * (n_neg - n_neg // 2)
    )
    subtypes = (
        ["code_snippet"] * (n_pos // 2)
        + ["consulta_corta"] * (n_pos - n_pos // 2)
        + ["near_ood_neighbor"] * (n_neg // 2)
        + ["long_context_flooding"] * (n_neg - n_neg // 2)
    )
    input_ids = [f"id-{i}" for i in range(n_pos + n_neg)]
    return y, categories, subtypes, input_ids


def _plain_docs(n: int, seed: int = 0) -> tuple[list[str], list[list[str]]]:
    rng = np.random.default_rng(seed)
    verbs = ("cook", "bake", "mix", "slice", "simmer", "whisk")
    nouns = ("flour", "butter", "onion", "stock", "cream", "dough")
    texts: list[str] = []
    clauses: list[list[str]] = []
    for i in range(n):
        parts = [f"{verbs[int(rng.integers(0, len(verbs)))]} the {nouns[int(rng.integers(0, len(nouns)))]}" for _ in range(3)]
        text = ". ".join(parts) + "."
        texts.append(text)
        clauses.append([p + "." for p in parts])
    return texts, clauses


class AxisIsolationTest(unittest.TestCase):
    def test_eje1_preset_excludes_near_ood_and_noise(self) -> None:
        strata = xray.contrast_preset_strata(replay.EJE1_PRESET)
        self.assertEqual(strata, ("general_prose", "technical_structured"))
        self.assertNotIn("near_ood_neighbor", strata)
        self.assertNotIn("structural_symbol_noise", strata)

    def test_stack_near_ood_is_isolated_from_eje1(self) -> None:
        dim = 8
        groups = {
            ("en", "full_doc", "general_prose", True): {"vectors": _unit_rows(4, dim, 1)},
            ("en", "full_doc", "technical_structured", True): {"vectors": _unit_rows(2, dim, 2)},
            ("en", "full_doc", "near_ood_neighbor", True): {"vectors": _unit_rows(3, dim, 3)},
            ("en", "full_doc", "structural_symbol_noise", True): {"vectors": _unit_rows(2, dim, 4)},
        }
        eje1 = replay.stack_eje1_contrast(groups, "en", "full_doc")
        near = replay.stack_near_ood_contrast(groups, "en", "full_doc")
        self.assertEqual(eje1.shape[0], 6)
        self.assertEqual(near.shape[0], 3)
        # Near matrix must equal the near stratum alone, not a mix with eje1.
        np.testing.assert_allclose(near, groups[("en", "full_doc", "near_ood_neighbor", True)]["vectors"])

    def test_axis_oof_differs_from_in_sample_fit(self) -> None:
        target, contrast = _separated_target_contrast(n_target=50, n_contrast=40, dim=64, seed=11)
        folds = np.arange(50, dtype=np.int64) % 5
        oof = replay.score_axis_oof(target, folds, contrast)
        in_sample_fit = v3.fit_directional_matrices(target, contrast)
        in_sample = v3.score_dir1024(target, in_sample_fit, replay.DIR_VARIANT)
        self.assertTrue(np.all(np.isfinite(oof)))
        self.assertFalse(np.allclose(oof, in_sample))
        # Fold-0 rows scored without fold-0 in the fit.
        fold0 = folds == 0
        fit_wo0 = v3.fit_directional_matrices(target[~fold0], contrast)
        expected = v3.score_dir1024(target[fold0], fit_wo0, replay.DIR_VARIANT)
        np.testing.assert_allclose(oof[fold0], expected)

    def test_axis_oof_rejects_non_finite(self) -> None:
        target, contrast = _separated_target_contrast(dim=16, seed=2)
        folds = np.arange(target.shape[0], dtype=np.int64) % 5
        bad = target.copy()
        bad[0, 0] = np.nan
        with self.assertRaises(ValueError):
            replay.score_axis_oof(bad, folds, contrast)

    def test_struct_oof_is_anti_in_sample(self) -> None:
        texts, clauses = _plain_docs(25, seed=7)
        # Inject fold-local punctuation bursts so in-sample envelopes absorb them.
        for i in range(0, 25, 5):
            texts[i] = texts[i] + " ???!!! ;;;:::&&&"
            clauses[i] = clauses[i] + ["???!!! ;;;:::&&&"]
        folds = np.arange(25, dtype=np.int64) % 5
        oof = replay.score_struct_oof(texts, clauses, folds)
        full_profile = lex.fit(texts, "full_doc")
        clause_profile = lex.fit([c for doc in clauses for c in doc], "clause_opt2c")
        in_sample = v3.score_struct_corpus(texts, clauses, full_profile, clause_profile, time_calls=False)
        self.assertTrue(np.all(np.isfinite(oof["s_full"])))
        self.assertTrue(np.all(np.isfinite(oof["s_min"])))
        # At least one poisoned fold-0 document should score differently OOF vs in-sample.
        fold0 = np.flatnonzero(folds == 0)
        self.assertFalse(np.allclose(oof["s_full"][fold0], in_sample["s_full"][fold0]))


class DualGateAndCatalogTest(unittest.TestCase):
    def test_full_only_catalog_is_exactly_twelve(self) -> None:
        specs = replay.compact_recipe_catalog("full_only")
        self.assertEqual(len(specs), 12)
        families = {spec.family for spec in specs}
        self.assertEqual(
            families,
            {"eje1_only", "eje1_plus_struct", "dual_axis_and", "dual_axis_blend", "dual_axis_min"},
        )

    def test_clauses_catalog_is_twelve_with_default_weight(self) -> None:
        specs = replay.compact_recipe_catalog("clauses")
        self.assertEqual(len(specs), 12)
        self.assertEqual({spec.w_f for spec in specs}, {0.35})

    def test_w_f_sensitivity_evaluates_three_weights_separately(self) -> None:
        rng = np.random.default_rng(14)
        y, categories, subtypes, _ids = _strata(16, 16)
        cal_full = rng.random(30)
        cal_cmin = rng.random(30)
        cal_near_full = rng.random(30)
        cal_near_cmin = rng.random(30)
        cal_struct = np.clip(rng.random(30), 0.2, 1.0)
        hold_full = rng.random(32) + np.where(y, 0.3, 0.0)
        hold_cmin = rng.random(32) + np.where(y, 0.25, 0.0)
        hold_near_full = rng.random(32)
        hold_near_cmin = rng.random(32)
        hold_struct = np.clip(rng.random(32), 0.2, 1.0)
        rows = replay.evaluate_w_f_sensitivity(
            cal_gen_full=cal_full,
            cal_gen_cmin=cal_cmin,
            cal_near_full=cal_near_full,
            cal_near_cmin=cal_near_cmin,
            cal_struct_min=cal_struct,
            hold_gen_full=hold_full,
            hold_gen_cmin=hold_cmin,
            hold_near_full=hold_near_full,
            hold_near_cmin=hold_near_cmin,
            hold_struct_min=hold_struct,
            y_true=y,
            categories=categories,
            subtypes=subtypes,
        )
        self.assertEqual([row["w_f"] for row in rows], [0.20, 0.35, 0.50])
        for row in rows:
            self.assertEqual(row["family"], "eje1_plus_struct")
            self.assertAlmostEqual(row["beta"], 0.10, places=12)
            self.assertTrue(np.isfinite(row["f1"]))
            self.assertTrue(np.isfinite(row["roc_auc"]))

    def test_dual_and_gate_requires_both_axes(self) -> None:
        cal_g = np.linspace(0.1, 1.0, 20)
        cal_n = np.linspace(0.2, 0.9, 20)
        t_gen, t_near = replay.dual_axis_and_thresholds(cal_g, cal_n, near_prob=0.05)
        hold_g = np.array([t_gen + 0.1, t_gen + 0.1, t_gen - 0.1, t_gen + 0.2])
        hold_n = np.array([t_near + 0.1, t_near - 0.1, t_near + 0.1, t_near + 0.2])
        pred = replay.predict_dual_axis_and(hold_g, hold_n, t_gen=t_gen, t_near=t_near)
        np.testing.assert_array_equal(pred, np.array([True, False, False, True]))

    def test_dual_and_thresholds_ignore_holdout(self) -> None:
        cal_g = np.linspace(0.0, 1.0, 50)
        cal_n = np.linspace(0.0, 1.0, 50)
        first = replay.dual_axis_and_thresholds(cal_g, cal_n, near_prob=0.10)
        # Mutating "holdout" cannot change thresholds because it is not an input.
        second = replay.dual_axis_and_thresholds(cal_g, cal_n, near_prob=0.10)
        self.assertEqual(first, second)
        shifted = replay.dual_axis_and_thresholds(cal_g + 1.0, cal_n + 1.0, near_prob=0.10)
        self.assertNotEqual(first[0], shifted[0])

    def test_evaluate_dual_and_cal_only_is_finite(self) -> None:
        rng = np.random.default_rng(0)
        cal_g = rng.random(40)
        cal_n = rng.random(40)
        hold_g = rng.random(30)
        hold_n = rng.random(30)
        y = np.array([True] * 15 + [False] * 15)
        row = replay.evaluate_dual_and_cal_only(
            cal_g, cal_n, hold_g, hold_n, y, near_prob=0.05, near_tag="p05"
        )
        self.assertEqual(row["near_tag"], "p05")
        self.assertTrue(np.isfinite(row["f1"]))
        self.assertTrue(np.isfinite(row["roc_auc"]))

    def test_blend_and_min_formulas(self) -> None:
        g = np.array([0.2, 0.8, 0.5])
        n = np.array([0.6, 0.4, 0.5])
        blended = replay.blend_axes(g, n, 0.35)
        expected = 0.65 * g + 0.35 * n
        np.testing.assert_allclose(blended, expected)
        np.testing.assert_allclose(replay.min_axes(g, n), np.array([0.2, 0.4, 0.5]))

    def test_struct_beta_identity_at_one(self) -> None:
        sem = np.array([0.3, 0.7, 0.9])
        struct = np.ones(3)
        out = replay.apply_struct_beta(sem, struct, 0.15)
        np.testing.assert_allclose(out, sem)

    def test_recipe_matrix_has_no_nan_or_inf(self) -> None:
        specs = replay.compact_recipe_catalog("full_only")
        g = np.linspace(0.1, 0.9, 20)
        n = np.linspace(0.2, 0.8, 20)
        s = np.linspace(0.5, 1.0, 20)
        matrix = replay.materialize_recipe_matrix(specs, g, n, s)
        self.assertEqual(matrix.shape, (20, 12))
        self.assertTrue(np.all(np.isfinite(matrix)))


class ClauseCapTest(unittest.TestCase):
    def test_uncapped_or_small_returns_all(self) -> None:
        scores = np.linspace(0.1, 1.0, 10)
        self.assertEqual(replay.select_clause_indices_edge_plus_struct(10, None, scores), list(range(10)))
        self.assertEqual(replay.select_clause_indices_edge_plus_struct(10, 16, scores), list(range(10)))

    def test_edge_plus_struct_is_deterministic(self) -> None:
        scores = np.linspace(1.0, 0.0, 80)
        first = replay.select_clause_indices_edge_plus_struct(80, 24, scores)
        second = replay.select_clause_indices_edge_plus_struct(80, 24, scores)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 24)
        self.assertEqual(first, sorted(first))
        self.assertIn(0, first)
        self.assertIn(79, first)

    def test_struct_prioritization_keeps_lowest_s_struct(self) -> None:
        n = 64
        scores = np.ones(n, dtype=np.float64)
        # Make a mid-band clause the most anomalous.
        scores[40] = 0.01
        scores[41] = 0.02
        keep = replay.select_clause_indices_edge_plus_struct(n, 16, scores)
        self.assertIn(40, keep)
        self.assertIn(41, keep)
        self.assertEqual(len(keep), 16)

    def test_caps_sixteen_twentyfour_thirtytwo(self) -> None:
        scores = np.linspace(0.0, 1.0, 100)
        for cap in (16, 24, 32):
            keep = replay.select_clause_indices_edge_plus_struct(100, cap, scores)
            self.assertEqual(len(keep), cap)
            self.assertEqual(keep[0], 0)
            self.assertEqual(keep[-1], 99)

    def test_apply_clause_cap_preserves_order(self) -> None:
        clauses = [f"c{i}" for i in range(40)]
        scores = np.linspace(1.0, 0.0, 40)
        capped = replay.apply_clause_cap_to_texts(clauses, 16, scores)
        self.assertEqual(len(capped), 16)
        indices = [int(name[1:]) for name in capped]
        self.assertEqual(indices, sorted(indices))

    def test_prefilter_is_finite(self) -> None:
        texts, clauses = _plain_docs(5, seed=3)
        profile = lex.fit([c for doc in clauses for c in doc], "clause_opt2c")
        values = replay.prefilter_clause_s_struct(clauses[0], profile)
        self.assertEqual(values.shape[0], len(clauses[0]))
        self.assertTrue(np.all(np.isfinite(values)))


class AntiLeakageMetricsTest(unittest.TestCase):
    def test_cal_only_ignores_holdout_labels(self) -> None:
        cal = np.linspace(0.1, 1.0, 30)
        hold = np.array([0.0, 1.0, 0.2, 0.8, 0.4, 0.6])
        y = np.array([True, True, True, False, False, False])
        first = replay.evaluate_cal_only(cal, hold, y)
        flipped = replay.evaluate_cal_only(cal, hold, ~y)
        for _prob, tag in replay.PROB_TAGS:
            self.assertEqual(first[tag]["threshold"], flipped[tag]["threshold"])

    def test_nested_selector_ignores_held_out_fold(self) -> None:
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
        chosen, threshold, train_f1 = v3.select_recipe_on_train(scores, y, train)
        poisoned = scores.copy()
        poisoned[test] = 1.0 - poisoned[test]
        chosen_p, threshold_p, f1_p = v3.select_recipe_on_train(poisoned, y, train)
        self.assertEqual(chosen, chosen_p)
        self.assertEqual(threshold, threshold_p)
        self.assertEqual(train_f1, f1_p)

    def test_repeated_oof_bit_stable_seed_zero(self) -> None:
        rng = np.random.default_rng(8)
        y, categories, subtypes, input_ids = _strata(20, 20)
        scores = rng.random(40)
        scores[:20] += 0.4
        first = replay.repeated_stratified_oof(scores, y, categories, subtypes, input_ids)
        second = replay.repeated_stratified_oof(scores, y, categories, subtypes, input_ids)
        self.assertEqual(first["seeds"][0], 0)
        self.assertEqual(first["f1"]["mean"], second["f1"]["mean"])
        self.assertEqual(first["oracle_upper_bound"]["tag"], "[ORACLE_UPPER_BOUND]")
        clean, oracle = replay.detach_oracle(dict(first))
        self.assertIsNotNone(oracle)
        self.assertNotIn("oracle_upper_bound", clean)

    def test_nested_oof_bit_stable_seed_zero(self) -> None:
        rng = np.random.default_rng(9)
        y, categories, subtypes, input_ids = _strata(20, 20)
        matrix = rng.random((40, 3))
        matrix[:20, 0] += 0.35
        first = replay.nested_repeated_oof(matrix, y, categories, subtypes, input_ids)
        second = replay.nested_repeated_oof(matrix, y, categories, subtypes, input_ids)
        self.assertEqual(first["seeds"], [0, 1, 2, 3, 4])
        self.assertEqual(first["f1"], second["f1"])
        self.assertEqual(first["modal_column"], second["modal_column"])

    def test_bootstrap_refits_and_is_bit_stable(self) -> None:
        rng = np.random.default_rng(3)
        y, categories, subtypes, _ids = _strata(16, 16)
        hold = rng.random(32)
        hold[:16] += 0.3
        cal = rng.random(40)
        methods = {"eje1": (hold, cal)}
        first = replay.bootstrap_cal_only(methods, y, categories, subtypes, seed=0, n_resamples=20)
        second = replay.bootstrap_cal_only(methods, y, categories, subtypes, seed=0, n_resamples=20)
        self.assertEqual(first["methods"]["eje1"]["f1"]["low"], second["methods"]["eje1"]["f1"]["low"])
        self.assertEqual(first["methods"]["eje1"]["f1"]["high"], second["methods"]["eje1"]["f1"]["high"])
        self.assertTrue(first["refits_thresholds"])
        self.assertEqual(first["seed"], 0)

    def test_bootstrap_supports_2d_dual_and_paired_deltas(self) -> None:
        rng = np.random.default_rng(6)
        y, categories, subtypes, _ids = _strata(16, 16)
        cal_g = rng.random(40)
        cal_n = rng.random(40)
        hold_g = rng.random(32) + np.where(y, 0.35, 0.0)
        hold_n = rng.random(32) + np.where(y, 0.25, 0.0)
        methods = {
            "frozen": (hold_g, cal_g),
            "eje1_only": (hold_g * 0.95, cal_g * 0.95),
            "best_dual_axis": replay.DualAndBootstrapMethod(
                hold_general=hold_g,
                hold_near=hold_n,
                cal_general=cal_g,
                cal_near=cal_n,
                near_prob=0.05,
            ),
        }
        boot = replay.bootstrap_cal_only(
            methods,
            y,
            categories,
            subtypes,
            seed=0,
            n_resamples=30,
            paired_deltas=(
                ("frozen_minus_eje1_only", "frozen", "eje1_only", 0.01),
                ("frozen_minus_best_dual_axis", "frozen", "best_dual_axis", 0.02),
            ),
        )
        self.assertTrue(boot["refits_thresholds"])
        self.assertIn("best_dual_axis", boot["methods"])
        self.assertIn("frozen_minus_eje1_only", boot["paired_deltas"])
        self.assertIn("frozen_minus_best_dual_axis", boot["paired_deltas"])
        d_dual = boot["paired_deltas"]["frozen_minus_best_dual_axis"]
        self.assertLessEqual(d_dual["ci95_low"], d_dual["ci95_high"])

    def test_freeze_winning_recipe_is_blind_and_oracle_dominates_cal_only(self) -> None:
        specs = replay.compact_recipe_catalog("full_only")
        rng = np.random.default_rng(4)
        y, categories, subtypes, input_ids = _strata(20, 20)
        g = rng.random(40)
        n = rng.random(40)
        s = np.clip(rng.random(40), 0.2, 1.0)
        g[:20] += 0.35
        # Make dual_axis_min appear better on holdout to ensure blind selection ignores holdout labels.
        n[:20] += 0.80
        cal_g = rng.random(50)
        cal_n = rng.random(50)
        cal_s = np.clip(rng.random(50), 0.2, 1.0)
        cal_matrix = replay.materialize_recipe_matrix(specs, cal_g, cal_n, cal_s)
        hold_matrix = replay.materialize_recipe_matrix(specs, g, n, s)
        frozen = replay.freeze_winning_recipe(
            specs, cal_matrix, hold_matrix, y, categories, subtypes, input_ids
        )
        flipped = replay.freeze_winning_recipe(
            specs, cal_matrix, hold_matrix, ~y, categories, subtypes, input_ids
        )
        self.assertEqual(frozen["recipe"]["family"], "eje1_plus_struct")
        self.assertAlmostEqual(frozen["recipe"]["beta"], 0.10, places=12)
        self.assertEqual(frozen["frozen_column"], 1)
        self.assertEqual(frozen["recipe"], flipped["recipe"])
        self.assertEqual(frozen["frozen_column"], flipped["frozen_column"])
        self.assertEqual(frozen["oracle_upper_bound"]["tag"], "[ORACLE_UPPER_BOUND]")
        for _prob, tag in replay.PROB_TAGS:
            self.assertEqual(frozen["cal_only"][tag]["threshold"], flipped["cal_only"][tag]["threshold"])
            self.assertGreaterEqual(
                frozen["oracle_upper_bound"]["f1"] + 1e-12,
                frozen["cal_only"][tag]["f1"],
            )

    def test_canary_kinds_are_explicit(self) -> None:
        texts = [
            "import sqlite3 and connect",
            "safe text",
            "call subprocess.run",
            "parse with json.loads",
        ]
        categories = ["IN_DOMAIN_VALID", "IN_DOMAIN_VALID", "ADVERSARIAL_FUZZING", "IN_DOMAIN_VALID"]
        y = np.array([True, True, False, True])
        pred = np.array([True, True, False, False])
        block = replay.canary_block(texts, categories, y, pred)
        self.assertEqual(set(block["kinds"]), {"sqlite3", "subprocess", "json"})
        self.assertEqual(block["kinds"]["sqlite3"]["kind"], "sqlite3")
        self.assertEqual(block["kinds"]["sqlite3"]["n_marker"], 1)

    def test_subgroup_block_covers_quadrants(self) -> None:
        y, categories, subtypes, _ids = _strata(10, 10)
        pred = y.copy()
        pred[0] = False
        block = replay.subgroup_block(y, pred, categories, subtypes)
        for name in replay.QUADRANT_NAMES:
            self.assertIn(name, block["quadrants"])
        subtypes_found = {row["subtype"] for row in block["subtypes"]}
        self.assertIn("near_ood_neighbor", subtypes_found)


class DispatchAndHarnessTest(unittest.TestCase):
    def test_mode_parser_accepts_v4_and_keeps_legacy(self) -> None:
        parser = sim.build_arg_parser()
        self.assertEqual(parser.parse_args(["--mode", "default"]).mode, "default")
        self.assertEqual(parser.parse_args(["--mode", "v2"]).mode, "v2")
        self.assertEqual(parser.parse_args(["--mode", "v3"]).mode, "v3")
        self.assertEqual(parser.parse_args(["--mode", "v4"]).mode, "v4")

    def test_output_dir_under_reports_is_refused(self) -> None:
        with self.assertRaises(RuntimeError):
            replay._reject_tracked_output(Path("reports/fhv1_1_id_v4"))
        repo_reports = Path(__file__).resolve().parents[1] / "reports" / "fhv1_1_id_v4"
        with self.assertRaises(RuntimeError):
            replay._reject_tracked_output(repo_reports)

    def test_ports_closed_helper_is_boolean(self) -> None:
        self.assertIsInstance(replay.ports_8080_8088_closed(), bool)

    def test_measure_flooding_latency_without_server(self) -> None:
        prompts = [
            "First alpha clause. Second alpha clause. Third alpha clause. Fourth alpha clause.",
            "First beta clause. Second beta clause. Third beta clause. Fourth beta clause.",
        ]
        profile = lex.fit([c for p in prompts for c in xray.segment_clauses_opt2c(p)], "clause_opt2c")
        seen_payload_lengths: list[int] = []

        def embed_fn(batch: list[str]) -> list[list[float]]:
            seen_payload_lengths.append(len(batch))
            return [[0.0] * 8 for _ in batch]

        uncapped = replay.measure_flooding_latency_ms(prompts, embed_fn, cap=None, clause_profile=profile, repeats=3)
        self.assertEqual(uncapped["n_prompts"], 2)
        self.assertEqual(uncapped["repeats"], 3)
        self.assertEqual(uncapped["n_measurements"], 6)
        self.assertEqual(len(uncapped["samples_ms"]), 6)
        self.assertEqual(uncapped["total_clauses_per_pass"], 8)
        self.assertAlmostEqual(uncapped["mean_clauses_per_prompt"], 4.0, places=12)
        self.assertTrue(np.isfinite(uncapped["p50_ms"]))
        self.assertTrue(np.isfinite(uncapped["p99_ms"]))
        self.assertTrue(np.isfinite(uncapped["mean_ms"]))
        self.assertEqual(uncapped["speedup_vs_uncapped"], 1.0)
        # Each timed call embeds [prompt_text] + selected_clauses = 1 + 4 = 5 texts.
        self.assertEqual(seen_payload_lengths, [5] * 6)

        domain_block = replay.measure_domain_flooding_latency(
            prompts,
            embed_fn,
            clause_profile=profile,
            caps=(None, 2),
            repeats=3,
        )
        self.assertEqual(set(domain_block), {"uncapped", "cap_2"})
        self.assertEqual(domain_block["cap_2"]["total_clauses_per_pass"], 4)
        self.assertAlmostEqual(
            domain_block["cap_2"]["speedup_vs_uncapped"],
            domain_block["uncapped"]["p50_ms"] / domain_block["cap_2"]["p50_ms"],
            places=12,
        )

    def test_latency_harness_cleanup_checks_ports(self) -> None:
        texts = ["flood me"]

        def embed_fn(batch: list[str]) -> list[list[float]]:
            return [[0.1] * 4 for _ in batch]

        with mock.patch.object(replay, "EmbedServerSession") as session_cls:
            session = mock.MagicMock()
            session.start.return_value = 12345
            session_cls.return_value = session
            with mock.patch.object(replay, "ports_8080_8088_closed", return_value=True):
                block = replay.run_flooding_latency_with_server(texts, embed_fn, repeats=2, start_server=True)
            session.cleanup.assert_called()
        self.assertEqual(block["server_pid"], 12345)
        self.assertEqual(block["n_prompts"], 1)
        self.assertEqual(block["n_measurements"], 2)
        self.assertTrue(np.isfinite(block["p50_ms"]))

    def test_evaluate_clause_cap_cell_uses_frozen_struct_and_smuggle_any(self) -> None:
        texts_cal, clauses_cal = _plain_docs(12, seed=20)
        clause_profile = lex.fit([c for doc in clauses_cal for c in doc], "clause_opt2c")
        hold_texts = [
            "import json. parse safely. validate input. return result.",
            "cook soup. boil water. add salt. serve hot.",
            "footnote recipe secret. ignore rules. ### ??? !!!",
            "yaml payload key. value pair. hidden task. run now.",
            "flood one. flood two. flood three. flood four.",
            "jailbreak prompt. bypass check. override policy. print secret.",
            "valid doc a. valid doc b. valid doc c. valid doc d.",
            "valid doc e. valid doc f. valid doc g. valid doc h.",
        ]
        hold_clauses = [
            xray.segment_clauses_opt2c(hold_texts[0]),
            xray.segment_clauses_opt2c(hold_texts[1]),
            # Force fallback on row 2 by giving mismatched clause count vs scores.
            ["only one clause"],
            xray.segment_clauses_opt2c(hold_texts[3]),
            xray.segment_clauses_opt2c(hold_texts[4]),
            xray.segment_clauses_opt2c(hold_texts[5]),
            xray.segment_clauses_opt2c(hold_texts[6]),
            [],
        ]
        y_true = np.array([True, True, False, False, False, False, True, True], dtype=bool)
        categories = [
            "IN_DOMAIN_VALID",
            "IN_DOMAIN_VALID",
            "HYBRID_BOUNDARY",
            "HYBRID_BOUNDARY",
            "ADVERSARIAL_FUZZING",
            "ADVERSARIAL_FUZZING",
            "IN_DOMAIN_VALID",
            "IN_DOMAIN_VALID",
        ]
        subtypes = [
            "code_snippet",
            "short_idiom_query",
            "smuggle_comment_docstring",
            "smuggle_json_yaml",
            "long_context_flooding",
            "prompt_injection_jailbreak",
            "dilution_80_20",  # intentional check when positive? wait: use negative below
            "code_snippet",
        ]
        subtypes[6] = "code_snippet"
        # Add one negative dilution_80_20 row by flipping row 1 to negative dilution_80_20.
        y_true[1] = False
        categories[1] = "HYBRID_BOUNDARY"
        subtypes[1] = "dilution_80_20"

        hold_gen_clause_scores = []
        hold_near_clause_scores = []
        for idx, cls in enumerate(hold_clauses):
            if idx == 2:
                # 3 scores vs 1 clause -> triggers fallback
                hold_gen_clause_scores.append(np.array([0.8, 0.2, 0.5], dtype=np.float64))
                hold_near_clause_scores.append(np.array([0.7, 0.3, 0.4], dtype=np.float64))
            elif idx == 7:
                hold_gen_clause_scores.append(np.zeros(0, dtype=np.float64))
                hold_near_clause_scores.append(np.zeros(0, dtype=np.float64))
            else:
                base = 0.85 if y_true[idx] else 0.25
                hold_gen_clause_scores.append(np.full(len(cls), base, dtype=np.float64))
                hold_near_clause_scores.append(np.full(len(cls), base, dtype=np.float64))

        hold_gen_full = np.where(y_true, 0.85, 0.30).astype(np.float64)
        hold_near_full = np.where(y_true, 0.85, 0.30).astype(np.float64)
        hold_struct_full = np.array([1.0, 0.9, 0.42, 0.8, 0.7, 0.6, 1.0, 0.95], dtype=np.float64)
        hold_struct_min_uncapped = hold_struct_full.copy()
        cal_gen = np.linspace(0.4, 0.9, 20)
        cal_near = np.linspace(0.4, 0.9, 20)
        cal_struct = np.ones(20, dtype=np.float64)

        block = replay.evaluate_clause_cap_cell(
            domain="python",
            hold_texts=hold_texts,
            hold_clauses=hold_clauses,
            hold_gen_full=hold_gen_full,
            hold_gen_clause_scores=hold_gen_clause_scores,
            hold_near_full=hold_near_full,
            hold_near_clause_scores=hold_near_clause_scores,
            hold_struct_min_uncapped=hold_struct_min_uncapped,
            hold_struct_full=hold_struct_full,
            y_true=y_true,
            categories=categories,
            subtypes=subtypes,
            cal_gen=cal_gen,
            cal_near=cal_near,
            cal_struct=cal_struct,
            clause_profile=clause_profile,
            w_f=0.35,
            beta=0.10,
        )
        self.assertEqual(block["recipe"]["family"], "eje1_plus_struct")
        self.assertAlmostEqual(block["recipe"]["beta"], 0.10, places=12)
        self.assertAlmostEqual(block["w_f"], 0.35, places=12)
        first = block["caps"][0]
        self.assertEqual(first["prefilter_counts"], {"s_struct": 6, "fallback": 1, "empty_clauses": 1})
        far_map = first["subtype_far"]
        for key in (
            "dilution_80_20",
            "smuggle_recipe_footnote",
            "smuggle_comment_docstring",
            "smuggle_json_yaml",
            "long_context_flooding",
            "prompt_injection_jailbreak",
            "smuggle_any",
        ):
            self.assertIn(key, far_map)
        self.assertIsNotNone(far_map["smuggle_any"])
        self.assertIsNone(far_map["smuggle_recipe_footnote"])

    def test_evaluate_cell_synthetic_is_finite(self) -> None:
        rng = np.random.default_rng(5)
        y, categories, subtypes, input_ids = _strata(20, 20)
        texts = [f"doc {i} with json" if i % 7 == 0 else f"doc {i}" for i in range(40)]
        cell = replay.evaluate_cell_synthetic(
            domain="receta",
            granularity="full_only",
            s_general_cal=rng.random(50),
            s_near_cal=rng.random(50),
            s_struct_cal=np.clip(rng.random(50), 0.2, 1.0),
            s_general_hold=rng.random(40) + np.where(y, 0.3, 0.0),
            s_near_hold=rng.random(40) + np.where(y, 0.2, 0.0),
            s_struct_hold=np.clip(rng.random(40), 0.2, 1.0),
            y_true=y,
            categories=categories,
            subtypes=subtypes,
            input_ids=input_ids,
            texts=texts,
        )
        self.assertEqual(cell["catalog_size"], 12)
        self.assertEqual(len(cell["recipe_table_12"]), 12)
        for row in cell["recipe_table_12"]:
            for key in ("f1", "in_domain_valid_frr", "ood_far", "adv_far", "hybrid_far", "near_ood_neighbor_far"):
                self.assertIn(key, row)
        self.assertEqual(len(cell["struct_beta_comparison"]), 3)
        self.assertIn("bootstrap", cell)
        self.assertIn("frozen_minus_eje1_only", cell["bootstrap"]["delta_f1"])
        self.assertIn("frozen_minus_best_dual_axis", cell["bootstrap"]["delta_f1"])
        self.assertEqual(cell["eje1_preset"], "1B_base_tech")
        self.assertEqual(cell["eje2_stratum"], "near_ood_neighbor")
        self.assertTrue(np.isfinite(cell["frozen"]["cal_only"]["p10"]["f1"]))
        self.assertTrue(np.isfinite(cell["auc"]["roc_auc"]))
        for _prob, tag in replay.PROB_TAGS:
            self.assertGreaterEqual(
                cell["frozen"]["oracle_upper_bound"]["f1"] + 1e-12,
                cell["frozen"]["cal_only"][tag]["f1"],
            )

    def test_struct_latency_block_finite(self) -> None:
        block = replay.struct_latency_block([10.0, 12.0, 11.0], [8.0, 9.0])
        self.assertTrue(np.isfinite(block["p50_us"]))
        self.assertTrue(np.isfinite(block["p99_us"]))


class PublicSurfaceFiniteTest(unittest.TestCase):
    def test_public_pipeline_arrays_have_no_nan_or_inf(self) -> None:
        target, contrast = _separated_target_contrast(n_target=30, n_contrast=20, dim=48, seed=21)
        folds = np.arange(30, dtype=np.int64) % 5
        oof = replay.score_axis_oof(target, folds, contrast)
        hold_fit = replay.fit_holdout_axis(target, contrast)
        hold = v3.score_dir1024(target, hold_fit, replay.DIR_VARIANT)
        texts, clauses = _plain_docs(20, seed=12)
        struct = replay.score_struct_oof(texts, clauses, np.arange(20) % 5)
        specs = replay.compact_recipe_catalog("full_only")
        matrix = replay.materialize_recipe_matrix(specs, oof[:20], hold[:20], struct["s_full"])
        self.assertTrue(np.all(np.isfinite(oof)))
        self.assertTrue(np.all(np.isfinite(hold)))
        self.assertTrue(np.all(np.isfinite(struct["s_full"])))
        self.assertTrue(np.all(np.isfinite(struct["s_min"])))
        self.assertTrue(np.all(np.isfinite(matrix)))

    def test_dir_variant_is_sig_sep(self) -> None:
        self.assertEqual(replay.DIR_VARIANT, "dir1024_sig_sep")
        target, contrast = _separated_target_contrast(dim=16, seed=1)
        fit = v3.fit_directional_matrices(target, contrast)
        weights = v3.variant_weights(fit, replay.DIR_VARIANT)
        np.testing.assert_allclose(weights, np.maximum(fit.sep, 0.05))


class NCalVolumeCurveTest(unittest.TestCase):
    def test_nfkc_casefold_collapses_compat_and_case(self) -> None:
        raw = "Caf\u00e9 PYTHON"
        folded = replay.nfkc_casefold(raw)
        self.assertEqual(folded, replay.nfkc_casefold("CAF\u00c9 python"))
        self.assertNotEqual(raw, folded)

    def test_zero_overlap_accepts_novel_and_rejects_dup(self) -> None:
        corpora = ["alpha beta gamma", "delta epsilon"]
        replay.assert_zero_text_overlap("brand new paragraph about widgets", corpora)
        with self.assertRaises(RuntimeError):
            replay.assert_zero_text_overlap("Alpha BETA gamma", corpora)

    def test_description_only_texts_are_nonempty_unique_domains(self) -> None:
        self.assertIn("python", replay.DESCRIPTION_ONLY_TEXTS)
        self.assertIn("receta", replay.DESCRIPTION_ONLY_TEXTS)
        py = replay.DESCRIPTION_ONLY_TEXTS["python"]
        es = replay.DESCRIPTION_ONLY_TEXTS["receta"]
        self.assertGreater(len(py.split()), 40)
        self.assertGreater(len(es.split()), 40)
        self.assertNotEqual(replay.nfkc_casefold(py), replay.nfkc_casefold(es))

    def test_fit_n1_uses_std_c_as_std_pool(self) -> None:
        dim = 16
        target = _unit_rows(1, dim, 7)
        contrast = _unit_rows(20, dim, 8, center=-np.ones(dim) / np.sqrt(dim))
        fit = replay.fit_directional_n1(target, contrast)
        self.assertTrue(np.allclose(fit.std_t, 0.0))
        np.testing.assert_allclose(fit.std_pool, fit.std_c)
        self.assertTrue(np.all(np.isfinite(fit.sep)))
        self.assertEqual(fit.std_t_fallback, "std_pool=std_C")

    def test_fit_allow_n1_matches_standard_for_n_ge_2(self) -> None:
        target, contrast = _separated_target_contrast(n_target=12, n_contrast=10, dim=24, seed=3)
        expected = v3.fit_directional_matrices(target, contrast)
        got = replay.fit_directional_matrices_allow_n1(target, contrast)
        np.testing.assert_allclose(got.std_pool, expected.std_pool)
        self.assertIsNone(got.std_t_fallback)

    def test_subsample_indices_are_deterministic_and_unique(self) -> None:
        first = replay.subsample_calibration_indices(60, 10, seed=2)
        second = replay.subsample_calibration_indices(60, 10, seed=2)
        other = replay.subsample_calibration_indices(60, 10, seed=3)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(len(set(first.tolist())), 10)
        self.assertFalse(np.array_equal(first, other))
        with self.assertRaises(ValueError):
            replay.subsample_calibration_indices(5, 10, seed=0)

    def test_n_cal_ladder_and_seeds_match_spec(self) -> None:
        self.assertEqual(replay.N_CAL_LADDER, (1, 5, 10, 25, 50, 100, 200, 400, 600))
        self.assertEqual(replay.N_CAL_SEEDS, (0, 1, 2, 3, 4))

    def test_evaluate_n_cal_seed_metrics_finite(self) -> None:
        dim = 32
        n_cal = 40
        n_hold = 30
        cal, contrast = _separated_target_contrast(n_target=n_cal, n_contrast=25, dim=dim, seed=11)
        hold = _unit_rows(n_hold, dim, 99, center=np.ones(dim) / np.sqrt(dim) * 0.35)
        y, categories, subtypes, _ids = _strata(12, 18)
        block = replay.evaluate_n_cal_seed(
            cal_vectors=cal,
            contrast=contrast,
            hold_vectors=hold,
            y_true=y,
            categories=categories,
            subtypes=subtypes,
            n_keep=10,
            seed=0,
        )
        self.assertEqual(block["n_cal"], 10)
        self.assertTrue(np.isfinite(block["cal_only"]["p10"]["f1"]))
        self.assertTrue(np.isfinite(block["roc_auc"]))
        self.assertIn("sep_ge_1_count", block)
        self.assertIn("ood_far", block)
        self.assertIn("adv_far", block)
        self.assertIn("near_ood_far", block)

    def test_aggregate_and_marginal_deltas(self) -> None:
        seed_rows = [
            {
                "n_cal": 5,
                "seed": seed,
                "cal_only": {
                    "p05": {"f1": 0.5 + 0.01 * seed, "frr": 0.1, "far": 0.2, "threshold": 0.4},
                    "p10": {"f1": 0.55 + 0.01 * seed, "frr": 0.08, "far": 0.18, "threshold": 0.35},
                },
                "roc_auc": 0.7 + 0.01 * seed,
                "frr": 0.08,
                "far": 0.18,
                "ood_far": 0.2,
                "adv_far": 0.15,
                "near_ood_far": 0.25,
                "threshold_p10": 0.35 + 0.01 * seed,
                "sep_ge_1_count": 3 + seed,
            }
            for seed in range(5)
        ]
        summary = replay.aggregate_n_cal_rung(seed_rows)
        self.assertIn("p10_f1", summary["mean"])
        self.assertIn("p10_f1", summary["std"])
        self.assertEqual(summary["n_seeds"], 5)
        rung_a = {"n_cal": 5, "mean": {"p10_f1": 0.5, "roc_auc": 0.7, "frr": 0.1, "far": 0.2}}
        rung_b = {"n_cal": 10, "mean": {"p10_f1": 0.6, "roc_auc": 0.75, "frr": 0.08, "far": 0.15}}
        deltas = replay.marginal_n_cal_deltas([rung_a, rung_b])
        self.assertEqual(len(deltas), 1)
        self.assertAlmostEqual(deltas[0]["delta_f1"], 0.1, places=12)
        self.assertAlmostEqual(deltas[0]["delta_auc"], 0.05, places=12)

    def test_n_cal_ge_5_uses_oof_and_differs_from_in_sample(self) -> None:
        dim = 32
        cal, contrast = _separated_target_contrast(n_target=30, n_contrast=20, dim=dim, seed=17)
        hold = _unit_rows(20, dim, 55, center=np.ones(dim) / np.sqrt(dim) * 0.35)
        y, categories, subtypes, _ids = _strata(10, 10)
        for n_keep in (5, 10, 20):
            indices = replay.subsample_calibration_indices(cal.shape[0], n_keep, seed=0)
            subset = cal[indices]
            fit = replay.fit_directional_matrices_allow_n1(subset, contrast)
            in_sample = v3.score_dir1024(subset, fit.as_directional(), replay.DIR_VARIANT)
            expected_oof = replay.score_axis_oof(
                subset, np.arange(n_keep, dtype=np.int64) % 5, contrast, n_folds=5
            )
            self.assertFalse(np.allclose(expected_oof, in_sample))
            block = replay.evaluate_n_cal_seed(
                cal_vectors=cal,
                contrast=contrast,
                hold_vectors=hold,
                y_true=y,
                categories=categories,
                subtypes=subtypes,
                n_keep=n_keep,
                seed=0,
            )
            expected_p10 = float(np.quantile(expected_oof, np.float64(0.10), method="linear"))
            in_sample_p10 = float(np.quantile(in_sample, np.float64(0.10), method="linear"))
            self.assertAlmostEqual(block["threshold_p10"], expected_p10, places=12)
            self.assertNotAlmostEqual(block["threshold_p10"], in_sample_p10, places=9)

    def test_n_cal_1_uses_1b_contrast_quantile_not_self_score(self) -> None:
        dim = 16
        cal = _unit_rows(20, dim, 31, center=np.ones(dim) / np.sqrt(dim) * 0.4)
        contrast = _unit_rows(20, dim, 32, center=-np.ones(dim) / np.sqrt(dim) * 0.4)
        hold_pos = _unit_rows(8, dim, 33, center=np.ones(dim) / np.sqrt(dim) * 0.4)
        hold_neg = _unit_rows(12, dim, 34, center=-np.ones(dim) / np.sqrt(dim) * 0.4)
        hold = np.vstack((hold_pos, hold_neg))
        y, categories, subtypes, _ids = _strata(8, 12)

        # Description-only N=1.
        desc = cal[:1]
        fit_desc = replay.fit_directional_n1(desc, contrast)
        contrast_scores = v3.score_dir1024(contrast, fit_desc.as_directional(), replay.DIR_VARIANT)
        expected_p95 = float(np.quantile(contrast_scores, np.float64(0.95), method="linear"))
        expected_p99 = float(np.quantile(contrast_scores, np.float64(0.99), method="linear"))
        desc_score = float(v3.score_dir1024(desc, fit_desc.as_directional(), replay.DIR_VARIANT)[0])
        desc_block = replay.evaluate_description_only_scores(
            domain="python",
            description_vector=desc,
            contrast=contrast,
            hold_vectors=hold,
            y_true=y,
            categories=categories,
            subtypes=subtypes,
        )
        self.assertEqual(desc_block["threshold_source"], "1b_contrast_quantile_0.95")
        self.assertAlmostEqual(desc_block["threshold_relative_1b"], expected_p95, places=12)
        self.assertAlmostEqual(desc_block["contrast_p99"], expected_p99, places=12)
        self.assertEqual(desc_block["midpoint"], 0.50)
        self.assertNotAlmostEqual(desc_block["threshold_relative_1b"], desc_score, places=6)
        self.assertLess(desc_block["frr"], 1.0)
        self.assertGreater(desc_block["f1"], 0.0)

        # Real-doc N=1 subsample seed.
        idx = replay.subsample_calibration_indices(cal.shape[0], 1, seed=0)
        subset = cal[idx]
        fit_n1 = replay.fit_directional_matrices_allow_n1(subset, contrast)
        c_scores_n1 = v3.score_dir1024(contrast, fit_n1.as_directional(), replay.DIR_VARIANT)
        expected_n1_p95 = float(np.quantile(c_scores_n1, np.float64(0.95), method="linear"))
        self_score_n1 = float(v3.score_dir1024(subset, fit_n1.as_directional(), replay.DIR_VARIANT)[0])
        seed_block = replay.evaluate_n_cal_seed(
            cal_vectors=cal,
            contrast=contrast,
            hold_vectors=hold,
            y_true=y,
            categories=categories,
            subtypes=subtypes,
            n_keep=1,
            seed=0,
        )
        self.assertEqual(seed_block["threshold_source"], "1b_contrast_quantile_0.95")
        self.assertAlmostEqual(seed_block["threshold_relative_1b"], expected_n1_p95, places=12)
        self.assertAlmostEqual(seed_block["threshold_p10"], expected_n1_p95, places=12)
        self.assertAlmostEqual(seed_block["cal_only"]["blind_1b_p95"]["threshold"], expected_n1_p95, places=12)
        self.assertNotAlmostEqual(seed_block["threshold_relative_1b"], self_score_n1, places=6)
        self.assertLess(seed_block["frr"], 1.0)

    def test_run_n_cal_volume_curve_domain_full_rung_uses_oof(self) -> None:
        dim = 24
        cal, contrast = _separated_target_contrast(n_target=10, n_contrast=15, dim=dim, seed=41)
        hold = _unit_rows(20, dim, 42, center=np.ones(dim) / np.sqrt(dim) * 0.35)
        y, categories, subtypes, _ids = _strata(10, 10)
        cal_folds = np.arange(10, dtype=np.int64) % 5
        expected_oof = replay.score_axis_oof(cal, cal_folds, contrast, n_folds=5)
        expected_p10 = float(np.quantile(expected_oof, np.float64(0.10), method="linear"))
        fit = replay.fit_directional_matrices_allow_n1(cal, contrast)
        in_sample = v3.score_dir1024(cal, fit.as_directional(), replay.DIR_VARIANT)
        in_sample_p10 = float(np.quantile(in_sample, np.float64(0.10), method="linear"))
        with mock.patch.object(replay, "N_CAL_LADDER", (1, 5, 10)):
            curve = replay.run_n_cal_volume_curve_domain(
                domain="python",
                cal_vectors=cal,
                contrast=contrast,
                hold_vectors=hold,
                y_true=y,
                categories=categories,
                subtypes=subtypes,
                description_vector=None,
                description_text=None,
                overlap_corpora=[],
                cal_folds=cal_folds,
            )
        full_rows = [r for r in curve["ladder_seed_rows"] if r["kind"] == "full_calibration"]
        self.assertEqual(len(full_rows), 1)
        self.assertEqual(full_rows[0]["threshold_source"], "oof_calibration_quantile")
        self.assertAlmostEqual(full_rows[0]["threshold_p10"], expected_p10, places=12)
        self.assertNotAlmostEqual(full_rows[0]["threshold_p10"], in_sample_p10, places=9)

    def test_description_only_block_labels_oracle(self) -> None:
        dim = 16
        desc = _unit_rows(1, dim, 1)
        contrast = _unit_rows(12, dim, 2, center=-np.ones(dim) / np.sqrt(dim))
        hold = _unit_rows(20, dim, 3)
        y, categories, subtypes, _ids = _strata(8, 12)
        block = replay.evaluate_description_only_scores(
            domain="python",
            description_vector=desc,
            contrast=contrast,
            hold_vectors=hold,
            y_true=y,
            categories=categories,
            subtypes=subtypes,
        )
        self.assertEqual(block["kind"], "description_only")
        self.assertEqual(block["std_t_fallback"], "std_pool=std_C")
        self.assertEqual(block["threshold_source"], "1b_contrast_quantile_0.95")
        self.assertEqual(block["oracle_upper_bound"]["tag"], "[ORACLE_UPPER_BOUND]")
        self.assertTrue(np.isfinite(block["roc_auc"]))
        self.assertTrue(np.isfinite(block["pr_auc_in_domain"]))
        self.assertTrue(np.isfinite(block["threshold_relative_1b"]))
        self.assertTrue(np.isfinite(block["contrast_p99"]))
        self.assertEqual(block["midpoint"], 0.50)

    def test_replay_v4_outputs_roundtrip_into_report_generator(self) -> None:
        rng = np.random.default_rng(77)
        y, categories, subtypes, input_ids = _strata(16, 16)
        texts = [
            f"import json sqlite3 subprocess func_{i}. parse payload {i}."
            for i in range(32)
        ]
        specs_full = replay.compact_recipe_catalog("full_only")
        specs_cls = replay.compact_recipe_catalog("clauses")
        cal_g = rng.random(40)
        cal_n = rng.random(40)
        cal_s = np.clip(rng.random(40), 0.2, 1.0)
        hold_g = rng.random(32) + np.where(y, 0.35, 0.0)
        hold_n = rng.random(32) + np.where(y, 0.25, 0.0)
        hold_s = np.clip(rng.random(32), 0.2, 1.0)
        latency = replay.struct_latency_block([10.0, 12.0], [5.0, 6.0])
        cell_full = replay.build_dual_axis_cell(
            domain="python",
            granularity="full_only",
            specs=specs_full,
            cal_matrix=replay.materialize_recipe_matrix(specs_full, cal_g, cal_n, cal_s),
            hold_matrix=replay.materialize_recipe_matrix(specs_full, hold_g, hold_n, hold_s),
            s_general_cal=cal_g,
            s_near_cal=cal_n,
            s_general_hold=hold_g,
            s_near_hold=hold_n,
            y_true=y,
            categories=categories,
            subtypes=subtypes,
            input_ids=input_ids,
            texts=texts,
            struct_latency=latency,
            bootstrap_resamples=20,
        )
        w_f_sens = replay.evaluate_w_f_sensitivity(
            cal_gen_full=cal_g,
            cal_gen_cmin=cal_g * 0.9,
            cal_near_full=cal_n,
            cal_near_cmin=cal_n * 0.9,
            cal_struct_min=cal_s,
            hold_gen_full=hold_g,
            hold_gen_cmin=hold_g * 0.9,
            hold_near_full=hold_n,
            hold_near_cmin=hold_n * 0.9,
            hold_struct_min=hold_s,
            y_true=y,
            categories=categories,
            subtypes=subtypes,
        )
        cell_clauses = replay.build_dual_axis_cell(
            domain="python",
            granularity="clauses",
            specs=specs_cls,
            cal_matrix=replay.materialize_recipe_matrix(specs_cls, cal_g, cal_n, cal_s),
            hold_matrix=replay.materialize_recipe_matrix(specs_cls, hold_g, hold_n, hold_s),
            s_general_cal=cal_g,
            s_near_cal=cal_n,
            s_general_hold=hold_g,
            s_near_hold=hold_n,
            y_true=y,
            categories=categories,
            subtypes=subtypes,
            input_ids=input_ids,
            texts=texts,
            struct_latency=latency,
            w_f_sensitivity=w_f_sens,
            bootstrap_resamples=20,
        )
        hold_clauses = [xray.segment_clauses_opt2c(t) for t in texts]
        clause_profile = lex.fit([c for doc in hold_clauses for c in doc], "clause_opt2c")
        cap_block = replay.evaluate_clause_cap_cell(
            domain="python",
            hold_texts=texts,
            hold_clauses=hold_clauses,
            hold_gen_full=hold_g,
            hold_gen_clause_scores=[np.full(len(cls), hold_g[i], dtype=np.float64) for i, cls in enumerate(hold_clauses)],
            hold_near_full=hold_n,
            hold_near_clause_scores=[np.full(len(cls), hold_n[i], dtype=np.float64) for i, cls in enumerate(hold_clauses)],
            hold_struct_min_uncapped=hold_s,
            hold_struct_full=hold_s,
            y_true=y,
            categories=categories,
            subtypes=subtypes,
            cal_gen=cal_g,
            cal_near=cal_n,
            cal_struct=cal_s,
            clause_profile=clause_profile,
        )
        flood_dom = replay.measure_domain_flooding_latency(
            ["flood one. flood two. flood three. flood four."],
            lambda batch: [[0.0] * 4 for _ in batch],
            clause_profile=clause_profile,
            caps=(None, 2),
            repeats=2,
        )
        flood_payload = {
            "domains": {"python": flood_dom},
            "ports_closed_after": True,
            "PORTS_8080_8088_CLOSED": True,
        }
        cal_vec, contrast = _separated_target_contrast(n_target=10, n_contrast=12, dim=16, seed=81)
        hold_vec = _unit_rows(32, 16, 82)
        with mock.patch.object(replay, "N_CAL_LADDER", (1, 5, 10)):
            n_cal_payload = replay.run_n_cal_volume_curve_domain(
                domain="python",
                cal_vectors=cal_vec,
                contrast=contrast,
                hold_vectors=hold_vec,
                y_true=y,
                categories=categories,
                subtypes=subtypes,
                description_vector=cal_vec[:1],
                description_text=None,
                overlap_corpora=[],
            )
        n_cal_payload["holdout_scoring"] = "full_doc_chunk0"

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            cells_meta = [
                {
                    **replay._write_json(out, "python__full_only__dual_axis_v4.json", cell_full),
                    "domain": "python",
                    "granularity": "full_only",
                    "frozen_recipe": cell_full["frozen"]["recipe"]["name"],
                    "cal_only_p10_f1": cell_full["frozen"]["cal_only"]["p10"]["f1"],
                    "kind": "dual_axis",
                },
                {
                    **replay._write_json(out, "python__clauses__dual_axis_v4.json", cell_clauses),
                    "domain": "python",
                    "granularity": "clauses",
                    "frozen_recipe": cell_clauses["frozen"]["recipe"]["name"],
                    "cal_only_p10_f1": cell_clauses["frozen"]["cal_only"]["p10"]["f1"],
                    "kind": "dual_axis",
                },
                {
                    **replay._write_json(out, "python__clause_cap_eval.json", cap_block),
                    "domain": "python",
                    "kind": "clause_cap",
                },
                {
                    **replay._write_json(out, "python__n_cal_volume_curve.json", n_cal_payload),
                    "domain": "python",
                    "kind": "n_cal",
                },
                {
                    **replay._write_json(out, "flooding_latency_v4.json", flood_payload),
                    "kind": "flooding_latency",
                },
            ]
            manifest = {
                "mode": "v4",
                "dtype": "float64",
                "dim": sim.DIM,
                "normalize": True,
                "n_cells": 2,
                "cells": cells_meta,
                "bootstrap_resamples": replay.BOOTSTRAP_RESAMPLES,
                "bootstrap_seed": 0,
                "bootstrap_refits_thresholds": True,
                "cal_oof_folds": 5,
                "eje1_preset": replay.EJE1_PRESET,
                "eje2_stratum": replay.NEAR_STRATUM,
                "clause_caps": list(replay.CLAUSE_CAPS),
                "n_cal_ladder": [1, 5, 10],
                "PORTS_8080_8088_CLOSED": True,
            }
            (out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            bundle = v4_report.load_directory(out)
            v3_path = Path(__file__).resolve().parents[1] / "reports" / "fhv1_1_id_v3_report.md"
            v3_base = v4_report.parse_v3_baseline(v3_path.read_text(encoding="utf-8"))
            md = v4_report.render_report(
                bundle,
                phase0_quote="## 1. Phase-0\nDIFF_IDENTICAL=0\n19,229,584\n3,145,728\nPASSED=173",
                disk_before="before",
                disk_after="after",
                v3_baseline=v3_base,
            )
            v4_report.assert_executive_f1(md, bundle)
            self.assertIn("Diagnostic `w_f` sensitivity", md)
            self.assertIn("`0.21`", md)
            self.assertIn("`0.11`", md)


if __name__ == "__main__":
    unittest.main()
