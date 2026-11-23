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

import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import fhv1_1_lexical_profile as lex
import fhv1_1_replay_sim as sim
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

    def test_clauses_catalog_multiplies_by_three_weights(self) -> None:
        specs = replay.compact_recipe_catalog("clauses")
        self.assertEqual(len(specs), 36)
        self.assertEqual(sorted({spec.w_f for spec in specs}), [0.20, 0.35, 0.50])

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

    def test_freeze_winning_recipe_returns_one_spec(self) -> None:
        specs = replay.compact_recipe_catalog("full_only")
        rng = np.random.default_rng(4)
        y, categories, subtypes, input_ids = _strata(20, 20)
        g = rng.random(40)
        n = rng.random(40)
        s = np.clip(rng.random(40), 0.2, 1.0)
        g[:20] += 0.35
        cal_g = rng.random(50)
        cal_n = rng.random(50)
        cal_s = np.clip(rng.random(50), 0.2, 1.0)
        cal_matrix = replay.materialize_recipe_matrix(specs, cal_g, cal_n, cal_s)
        hold_matrix = replay.materialize_recipe_matrix(specs, g, n, s)
        frozen = replay.freeze_winning_recipe(
            specs, cal_matrix, hold_matrix, y, categories, subtypes, input_ids
        )
        self.assertIn("recipe", frozen)
        self.assertEqual(frozen["oracle_upper_bound"]["tag"], "[ORACLE_UPPER_BOUND]")
        self.assertIn("p10", frozen["cal_only"])

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

    def test_ports_closed_helper_is_boolean(self) -> None:
        self.assertIsInstance(replay.ports_8080_8088_closed(), bool)

    def test_measure_flooding_latency_without_server(self) -> None:
        texts = ["a" * 100, "b" * 100]

        def embed_fn(batch: list[str]) -> list[list[float]]:
            return [[0.0] * 8 for _ in batch]

        block = replay.measure_flooding_latency_ms(texts, embed_fn, repeats=3)
        self.assertEqual(block["n_texts"], 2)
        self.assertTrue(np.isfinite(block["p50_ms"]))
        self.assertTrue(np.isfinite(block["p99_ms"]))

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
        self.assertTrue(np.isfinite(block["p50_ms"]))

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
        self.assertEqual(cell["eje1_preset"], "1B_base_tech")
        self.assertEqual(cell["eje2_stratum"], "near_ood_neighbor")
        self.assertTrue(np.isfinite(cell["frozen"]["cal_only"]["p10"]["f1"]))
        self.assertTrue(np.isfinite(cell["auc"]["roc_auc"]))

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


if __name__ == "__main__":
    unittest.main()
