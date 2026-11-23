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
"""Deterministic offline unit tests for tools/fhv1_1_xray.py (no LanceDB or network)."""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

import fhv1_1_xray as xray


def _make_matrix(rows: list[list[float]], dim: int = 8) -> np.ndarray:
    arr = np.asarray(rows, dtype=np.float64)
    assert arr.shape[1] == dim
    return arr


def _synthetic_moments_from_stats(
    mean: list[float],
    std_sample: list[float],
    sample_count: int = 100,
) -> xray.CoordinateMoments:
    mean_arr = np.asarray(mean, dtype=np.float64)
    std_s = np.asarray(std_sample, dtype=np.float64)
    var_s = std_s**2
    var_p = var_s * ((sample_count - 1.0) / sample_count)
    std_p = np.sqrt(var_p)
    min_arr = mean_arr - 2.0 * std_s
    max_arr = mean_arr + 2.0 * std_s
    return xray.CoordinateMoments(
        sample_count=sample_count,
        min=min_arr,
        max=max_arr,
        mean=mean_arr,
        span=max_arr - min_arr,
        variance_sample=var_s,
        variance_pop=var_p,
        std_dev_sample=std_s,
        std_dev_pop=std_p,
    )


class MomentsAndBoxInflationTest(unittest.TestCase):
    def test_float64_moments_ddof1_and_ddof0_and_stored_diff(self) -> None:
        matrix = np.asarray(
            [
                [1.0, -2.0, 0.5, 4.0],
                [3.0, 2.0, 0.5, 6.0],
                [5.0, 6.0, 0.5, 8.0],
            ],
            dtype=np.float64,
        )
        moments = xray.compute_coordinate_moments(matrix, expected_dim=4)
        self.assertEqual(moments.sample_count, 3)
        self.assertEqual(moments.mean.dtype, np.float64)
        np.testing.assert_allclose(moments.min, [1.0, -2.0, 0.5, 4.0], rtol=0.0, atol=0.0)
        np.testing.assert_allclose(moments.max, [5.0, 6.0, 0.5, 8.0], rtol=0.0, atol=0.0)
        np.testing.assert_allclose(moments.mean, [3.0, 2.0, 0.5, 6.0], rtol=0.0, atol=1e-15)
        np.testing.assert_allclose(moments.span, [4.0, 8.0, 0.0, 4.0], rtol=0.0, atol=0.0)
        # Sample variance (ddof=1): [4.0, 16.0, 0.0, 4.0]
        np.testing.assert_allclose(moments.variance_sample, [4.0, 16.0, 0.0, 4.0], rtol=0.0, atol=1e-15)
        np.testing.assert_allclose(moments.std_dev_sample, [2.0, 4.0, 0.0, 2.0], rtol=0.0, atol=1e-15)
        # Population variance (ddof=0): [8/3, 32/3, 0.0, 8/3]
        np.testing.assert_allclose(
            moments.variance_pop, [8.0 / 3.0, 32.0 / 3.0, 0.0, 8.0 / 3.0], rtol=0.0, atol=1e-15
        )
        np.testing.assert_allclose(
            moments.std_dev_pop,
            [math.sqrt(8.0 / 3.0), math.sqrt(32.0 / 3.0), 0.0, math.sqrt(8.0 / 3.0)],
            rtol=0.0,
            atol=1e-15,
        )

        stored = {
            "min_vector": moments.min.tolist(),
            "max_vector": moments.max.tolist(),
            "mean_vector": moments.mean.tolist(),
            "span_vector": moments.span.tolist(),
            "variance_vector": moments.variance_pop.tolist(),
            "std_dev_vector": moments.std_dev_pop.tolist(),
        }
        diff = xray.compare_moments_against_stored(moments, stored)
        self.assertEqual(diff["min_max_abs_diff"], 0.0)
        self.assertEqual(diff["max_max_abs_diff"], 0.0)
        self.assertEqual(diff["mean_max_abs_diff"], 0.0)
        self.assertEqual(diff["span_max_abs_diff"], 0.0)
        self.assertEqual(diff["variance_pop_max_abs_diff"], 0.0)
        self.assertEqual(diff["std_dev_pop_max_abs_diff"], 0.0)

    def test_box_inflation_ratios_quantiles_and_zero_guard(self) -> None:
        # 5 dims to test exact p25/median/p75/p90 and zero denominator guard at dim 4
        full_doc = xray.CoordinateMoments(
            sample_count=10,
            min=np.zeros(5, dtype=np.float64),
            max=np.array([1.0, 2.0, 4.0, 5.0, 0.0], dtype=np.float64),
            mean=np.zeros(5, dtype=np.float64),
            span=np.array([1.0, 2.0, 4.0, 5.0, 0.0], dtype=np.float64),
            variance_sample=np.array([0.25, 1.0, 4.0, 1.0, 0.0], dtype=np.float64),
            variance_pop=np.array([0.225, 0.9, 3.6, 0.9, 0.0], dtype=np.float64),
            std_dev_sample=np.array([0.5, 1.0, 2.0, 1.0, 0.0], dtype=np.float64),
            std_dev_pop=np.sqrt(np.array([0.225, 0.9, 3.6, 0.9, 0.0], dtype=np.float64)),
        )
        clause = xray.CoordinateMoments(
            sample_count=20,
            min=np.zeros(5, dtype=np.float64),
            max=np.array([2.0, 2.0, 2.0, 10.0, 1.0], dtype=np.float64),
            mean=np.zeros(5, dtype=np.float64),
            span=np.array([2.0, 2.0, 2.0, 10.0, 1.0], dtype=np.float64),
            variance_sample=np.ones(5, dtype=np.float64),
            variance_pop=np.ones(5, dtype=np.float64) * 0.95,
            std_dev_sample=np.ones(5, dtype=np.float64),
            std_dev_pop=np.ones(5, dtype=np.float64) * math.sqrt(0.95),
        )
        pooled = xray.CoordinateMoments(
            sample_count=100,
            min=np.zeros(5, dtype=np.float64),
            max=np.array([2.0, 6.0, 16.0, 25.0, 0.0], dtype=np.float64),
            mean=np.zeros(5, dtype=np.float64),
            span=np.array([2.0, 6.0, 16.0, 25.0, 0.0], dtype=np.float64),
            variance_sample=np.array([1.0, 9.0, 4.0, 9.0, 0.0], dtype=np.float64),
            variance_pop=np.array([0.99, 8.91, 3.96, 8.91, 0.0], dtype=np.float64),
            std_dev_sample=np.array([1.0, 3.0, 2.0, 3.0, 0.0], dtype=np.float64),
            std_dev_pop=np.sqrt(np.array([0.99, 8.91, 3.96, 8.91, 0.0], dtype=np.float64)),
        )
        inflation = xray.compute_box_inflation_metrics(full_doc, clause, pooled, eps=1e-12)
        # span_pooled / (span_full_doc + 1e-12) -> [2.0, 3.0, 4.0, 5.0, 0.0]
        span_ratio_dist = inflation["span_pooled_over_full_doc"]
        self.assertAlmostEqual(span_ratio_dist["min"], 0.0, places=12)
        self.assertAlmostEqual(span_ratio_dist["p25"], 2.0, places=11)
        self.assertAlmostEqual(span_ratio_dist["median"], 3.0, places=11)
        self.assertAlmostEqual(span_ratio_dist["p75"], 4.0, places=11)
        self.assertAlmostEqual(span_ratio_dist["p90"], 4.6, places=11)
        self.assertAlmostEqual(span_ratio_dist["max"], 5.0, places=11)

        # span_pooled / (span_clause + 1e-12) -> [1.0, 3.0, 8.0, 2.5, 0.0] sorted [0, 1, 2.5, 3, 8]
        clause_ratio_dist = inflation["span_pooled_over_clause"]
        self.assertAlmostEqual(clause_ratio_dist["median"], 2.5, places=11)
        self.assertAlmostEqual(clause_ratio_dist["max"], 8.0, places=11)

        # std_pooled / (std_full_doc + 1e-12) -> [2.0, 3.0, 1.0, 3.0, 0.0]
        std_dist = inflation["std_pooled_over_full_doc_ddof1"]
        self.assertAlmostEqual(std_dist["min"], 0.0, places=12)
        self.assertAlmostEqual(std_dist["median"], 2.0, places=11)
        self.assertAlmostEqual(std_dist["max"], 3.0, places=11)
        self.assertIn("std_pooled_over_full_doc_ddof0", inflation)


class FourBucketClassificationTest(unittest.TestCase):
    def test_mutually_exclusive_buckets_precedence_and_ranking(self) -> None:
        # 6 synthetic dimensions testing all 4 buckets and boundary precedence:
        # dim 0: BACKBONE_ENGINE (same sign, snr_T=2.0>=1.5, snr_C=2.0>=1.5, sep=0.0<0.75)
        # dim 1: FIRM_DOMAIN_ANCHOR (high SNR same sign BUT sep=1.2>=0.75 -> NOT backbone, becomes anchor)
        # dim 2: FIRM_DOMAIN_ANCHOR (sep=3.2>=1.0, snr_T=1.2>=1.0 -> anchor even though |mu_T|<0.015)
        # dim 3: NEGATIVE_INTRUDER_SENSOR (|mu_T|=0.005 < 0.015, snr_T=0.5 < 0.75, sep~1.98 >= 1.0)
        # dim 4: NEGATIVE_INTRUDER_SENSOR via intruder_ratio >= 1.8 even though sep < 1.0 (rms_T=0.01, rms_C=0.025 => intruder_ratio~2.5)
        # dim 5: DEAD_OR_OSCILLATOR (low SNR and low sep/intruder_ratio)
        target = _synthetic_moments_from_stats(
            mean=[0.20, 0.30, 0.012, 0.005, 0.000, 0.05],
            std_sample=[0.10, 0.10, 0.010, 0.010, 0.010, 0.10],
        )
        contrast = _synthetic_moments_from_stats(
            mean=[0.20, 0.18, -0.020, 0.035, 0.000, -0.01],
            std_sample=[0.10, 0.10, 0.010, 0.019, 0.025, 0.10],
        )
        res = xray.classify_dimensions(
            target,
            contrast,
            target_name="python",
            contrast_name="receta",
        )
        dims = res["dimensions"]
        self.assertEqual(len(dims), 6)
        self.assertEqual(dims[0]["bucket"], "BACKBONE_ENGINE")
        self.assertEqual(dims[1]["bucket"], "FIRM_DOMAIN_ANCHOR")
        self.assertEqual(dims[2]["bucket"], "FIRM_DOMAIN_ANCHOR")
        self.assertEqual(dims[3]["bucket"], "NEGATIVE_INTRUDER_SENSOR")
        self.assertEqual(dims[4]["bucket"], "NEGATIVE_INTRUDER_SENSOR")
        self.assertEqual(dims[5]["bucket"], "DEAD_OR_OSCILLATOR")

        self.assertEqual(
            res["bucket_counts"],
            {
                "BACKBONE_ENGINE": 1,
                "FIRM_DOMAIN_ANCHOR": 2,
                "NEGATIVE_INTRUDER_SENSOR": 2,
                "DEAD_OR_OSCILLATOR": 1,
            },
        )
        # Anchor ranking descending by sep: dim 2 (sep=3.0) > dim 1 (sep=1.2)
        self.assertEqual(res["bucket_dims"]["FIRM_DOMAIN_ANCHOR"], [2, 1])
        # Negative sensor ranking descending by max(sep, intruder_ratio):
        # dim 4: rms_T=0.01, rms_C=0.025 -> intruder_ratio~2.5, sep=0 -> score=2.5
        # dim 3: sep = |0.005 - 0.035| / sqrt((0.0001 + 0.000361)/2) = 0.03 / 0.0151822 = 1.976, intruder_ratio ~ 3.55 -> check exact ordering from computed metrics
        neg_scores = [dims[d]["neg_sensor_score"] for d in res["bucket_dims"]["NEGATIVE_INTRUDER_SENSOR"]]
        self.assertGreaterEqual(neg_scores[0], neg_scores[1])

    def test_opposite_sign_high_snr_is_not_backbone(self) -> None:
        # Both snr >= 1.5 and opposite signs -> mu_T * mu_C < 0 fails backbone, becomes anchor.
        target = _synthetic_moments_from_stats(mean=[0.002], std_sample=[0.001])
        contrast = _synthetic_moments_from_stats(mean=[-0.002], std_sample=[0.001])
        res = xray.classify_dimensions(target, contrast, "python", "receta")
        self.assertEqual(res["dimensions"][0]["bucket"], "FIRM_DOMAIN_ANCHOR")

    def test_anchor_precedence_over_negative_sensor_when_abs_mu_larger(self) -> None:
        # |mu_T| = 0.014 < 0.015 and snr_T = 0.70 < 0.75, yet sep >= 1.0 and |mu_T| > |mu_C|.
        # Anchor must take precedence over negative sensor.
        target = _synthetic_moments_from_stats(mean=[0.014], std_sample=[0.020])
        contrast = _synthetic_moments_from_stats(mean=[-0.012], std_sample=[0.010])
        res = xray.classify_dimensions(target, contrast, "python", "receta")
        self.assertEqual(res["dimensions"][0]["bucket"], "FIRM_DOMAIN_ANCHOR")

    def test_error_guards_for_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            xray.compute_coordinate_moments(np.array([[1.0, 2.0]], dtype=np.float64), expected_dim=2)
        with self.assertRaises(ValueError):
            xray.compute_coordinate_moments(
                np.array([[1.0, np.nan], [2.0, 3.0]], dtype=np.float64), expected_dim=2
            )
        with self.assertRaises(ValueError):
            xray.compute_roc_auc_trapezoidal(np.array([0, 0]), np.array([0.1, 0.2]))
        with self.assertRaises(ValueError):
            xray.compute_roc_auc_trapezoidal(np.array([0, 2]), np.array([0.1, 0.2]))

    def test_cli_defaults_and_summary_formatter(self) -> None:
        args = xray.build_arg_parser().parse_args([])
        self.assertEqual(args.mode, "1a")
        self.assertEqual(args.lancedb_uri, Path("data/sf-lancedb"))
        self.assertEqual(args.benchmarks_dir, Path("data/fhv1_benchmarks"))
        self.assertEqual(args.out, Path("/tmp/fhv1_1_id/xray_1a.json"))

        dist = {
            "count": 4,
            "min": 1.0,
            "p25": 1.5,
            "median": 2.0,
            "p75": 2.5,
            "p90": 3.0,
            "max": 3.5,
        }
        parity = {
            "min_max_abs_diff": 0.0,
            "max_max_abs_diff": 0.0,
            "mean_max_abs_diff": 0.0,
            "std_dev_pop_max_abs_diff": 0.0,
        }
        empty_buckets = {
            "bucket_counts": {b: 0 for b in xray.BUCKET_ORDER},
        }
        fake_report = {
            "stored_profile_parity": {"python": parity, "receta": parity},
            "box_inflation": {
                "python": {
                    k: dist
                    for k in (
                        "span_pooled_over_full_doc",
                        "span_pooled_over_clause",
                        "std_pooled_over_full_doc_ddof1",
                        "std_pooled_over_full_doc_ddof0",
                    )
                },
                "receta": {
                    k: dist
                    for k in (
                        "span_pooled_over_full_doc",
                        "span_pooled_over_clause",
                        "std_pooled_over_full_doc_ddof1",
                        "std_pooled_over_full_doc_ddof0",
                    )
                },
            },
            "bucket_classification": {
                "full_doc": {"python_vs_receta": empty_buckets, "receta_vs_python": empty_buckets},
                "clause_opt2c": {"python_vs_receta": empty_buckets, "receta_vs_python": empty_buckets},
            },
            "rogue_dim_autopsy": {"full_doc": [], "clause_opt2c": []},
            "pre_l2_norm_check": {
                "python": {
                    "calibration_full_doc": {"cal_norm_mean": 26.0, "cal_norm_std": 0.5, "min": 24.0, "max": 28.0},
                    "decoded_payload_chunk_gt0": {"count": 12},
                    "roc_auc_abs_norm_deviation": {"non_in_domain_vs_in_domain": {"roc_auc": 0.75, "n_pos": 300, "n_neg": 100}},
                },
                "receta": {
                    "calibration_full_doc": {"cal_norm_mean": 26.2, "cal_norm_std": 0.5, "min": 24.5, "max": 28.5},
                    "decoded_payload_chunk_gt0": {"count": 12},
                    "roc_auc_abs_norm_deviation": {"non_in_domain_vs_in_domain": {"roc_auc": 0.76, "n_pos": 300, "n_neg": 100}},
                },
            },
        }
        summary = xray.format_stdout_summary(fake_report)
        self.assertIn("FHV1.1 Phase 0 1A X-Ray Summary", summary)
        self.assertIn("python-v1", summary)
        self.assertIn("receta-v2", summary)


class RogueAutopsyTest(unittest.TestCase):
    def test_rogue_dim_autopsy_extracts_exact_fields(self) -> None:
        py = _synthetic_moments_from_stats(
            mean=[0.1, -0.2, 0.005, 0.3],
            std_sample=[0.05, 0.05, 0.01, 0.2],
        )
        rec = _synthetic_moments_from_stats(
            mean=[0.1, 0.2, 0.04, 0.25],
            std_sample=[0.05, 0.05, 0.02, 0.2],
        )
        cls_py = xray.classify_dimensions(py, rec, "python", "receta")
        cls_rec = xray.classify_dimensions(rec, py, "receta", "python")
        rows = xray.build_rogue_dim_autopsy(py, rec, cls_py, cls_rec, rogue_dims=(0, 2))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["dim"], 0)
        self.assertEqual(rows[0]["bucket_python"], "BACKBONE_ENGINE")
        self.assertEqual(rows[0]["bucket_receta"], "BACKBONE_ENGINE")
        self.assertAlmostEqual(rows[0]["sep"], 0.0, places=12)
        self.assertEqual(rows[1]["dim"], 2)
        self.assertEqual(rows[1]["bucket_python"], "NEGATIVE_INTRUDER_SENSOR")
        self.assertEqual(rows[1]["bucket_receta"], "FIRM_DOMAIN_ANCHOR")
        expected_keys = {
            "dim",
            "mean_py",
            "std_py",
            "mean_rec",
            "std_rec",
            "sep",
            "snr_py",
            "snr_rec",
            "intruder_ratio_py",
            "intruder_ratio_rec",
            "bucket_python",
            "bucket_receta",
        }
        self.assertEqual(set(rows[0].keys()), expected_keys)


class PreL2NormAndRocAucTest(unittest.TestCase):
    def test_roc_auc_perfect_inverse_and_ties(self) -> None:
        y = np.array([0, 0, 1, 1], dtype=np.int64)
        self.assertAlmostEqual(
            xray.compute_roc_auc_trapezoidal(y, np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)),
            1.0,
            places=12,
        )
        self.assertAlmostEqual(
            xray.compute_roc_auc_trapezoidal(y, np.array([0.9, 0.8, 0.2, 0.1], dtype=np.float64)),
            0.0,
            places=12,
        )
        self.assertAlmostEqual(
            xray.compute_roc_auc_trapezoidal(y, np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float64)),
            0.5,
            places=12,
        )
        # Partial tie case: scores [0.2, 0.5, 0.5, 0.9] with labels [0, 0, 1, 1]
        # Mann-Whitney U: pos1(0.5) beats 0.2 (1) and ties 0.5 (0.5) = 1.5; pos2(0.9) beats 0.2, 0.5 = 2.0 => 3.5 / 4 = 0.875
        self.assertAlmostEqual(
            xray.compute_roc_auc_trapezoidal(y, np.array([0.2, 0.5, 0.5, 0.9], dtype=np.float64)),
            0.875,
            places=12,
        )

    def test_norm_deviation_uses_calibration_mean_only_and_separates_chunks(self) -> None:
        # Calibration full_doc norms: [20.0, 20.0, 20.0] -> cal_norm_mean = 20.0 exactly
        cal_vecs = np.zeros((3, 4), dtype=np.float64)
        cal_vecs[:, 0] = 20.0

        def vec_with_norm(norm: float) -> list[float]:
            return [norm, 0.0, 0.0, 0.0]

        trace_rows = [
            # chunk 0 prompts
            {
                "input_id": "id-in-1",
                "category": "IN_DOMAIN_VALID",
                "chunk_index": 0,
                "chunk_strategy": "full_doc",
                "input_vector": vec_with_norm(20.1),
            },
            {
                "input_id": "id-in-2",
                "category": "IN_DOMAIN_VALID",
                "chunk_index": 0,
                "chunk_strategy": "full_doc",
                "input_vector": vec_with_norm(19.9),
            },
            {
                "input_id": "id-ood-1",
                "category": "OUT_OF_DOMAIN_BENIGN",
                "chunk_index": 0,
                "chunk_strategy": "full_doc",
                "input_vector": vec_with_norm(23.0),
            },
            {
                "input_id": "id-adv-short",
                "category": "ADVERSARIAL_FUZZING",
                "chunk_index": 0,
                "chunk_strategy": "full_doc",
                "input_vector": vec_with_norm(10.0),
            },
            {
                "input_id": "id-adv-gib",
                "category": "ADVERSARIAL_FUZZING",
                "chunk_index": 0,
                "chunk_strategy": "full_doc",
                "input_vector": vec_with_norm(32.0),
            },
            {
                "input_id": "id-adv-b64",
                "category": "ADVERSARIAL_FUZZING",
                "chunk_index": 0,
                "chunk_strategy": "full_doc",
                "input_vector": vec_with_norm(20.5),
            },
            # chunk 1 decoded Base64 payload (must be tracked separately, NOT mixed into chunk 0 stats!)
            {
                "input_id": "id-adv-b64",
                "category": "ADVERSARIAL_FUZZING",
                "chunk_index": 1,
                "chunk_strategy": "full_doc",
                "input_vector": vec_with_norm(29.0),
            },
        ]
        subtypes = {
            "id-in-1": "short_idiom_query",
            "id-in-2": "short_idiom_query",
            "id-ood-1": "ood_suite2_clinc",
            "id-adv-short": "extreme_short_punct",
            "id-adv-gib": "extreme_high_entropy_gibberish",
            "id-adv-b64": "obfuscation_base64",
        }
        report = xray.analyze_pre_l2_norms(cal_vecs, trace_rows, subtypes)
        self.assertEqual(report["calibration_full_doc"]["cal_norm_mean"], 20.0)
        self.assertEqual(report["calibration_full_doc"]["cal_norm_std"], 0.0)
        self.assertEqual(report["chunk0_prompt_count"], 6)
        self.assertEqual(report["decoded_payload_chunk_gt0"]["count"], 1)
        self.assertAlmostEqual(report["decoded_payload_chunk_gt0"]["norm_distribution"]["min"], 29.0, places=12)

        # Even if holdout OOD/ADV norms had huge mean (say 1000), cal_norm_mean stays strictly 20.0.
        aucs = report["roc_auc_abs_norm_deviation"]
        self.assertAlmostEqual(aucs["non_in_domain_vs_in_domain"]["roc_auc"], 1.0, places=12)
        self.assertAlmostEqual(aucs["adversarial_vs_in_domain"]["roc_auc"], 1.0, places=12)
        self.assertAlmostEqual(aucs["extreme_short_punct_vs_in_domain"]["roc_auc"], 1.0, places=12)
        self.assertAlmostEqual(aucs["extreme_high_entropy_gibberish_vs_in_domain"]["roc_auc"], 1.0, places=12)
        self.assertAlmostEqual(aucs["extreme_short_punct_or_gibberish_vs_in_domain"]["roc_auc"], 1.0, places=12)

        # JSON round-trip
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "xray_test.json"
            out_path.write_text(json.dumps(report), encoding="utf-8")
            reloaded = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(reloaded["calibration_full_doc"]["cal_norm_mean"], 20.0)

    def test_missing_subtype_raises_key_error(self) -> None:
        cal_vecs = np.ones((2, 4), dtype=np.float64)
        traces = [
            {
                "input_id": "unknown-id",
                "category": "IN_DOMAIN_VALID",
                "chunk_index": 0,
                "chunk_strategy": "full_doc",
                "input_vector": [1.0, 0.0, 0.0, 0.0],
            }
        ]
        with self.assertRaises(KeyError):
            xray.analyze_pre_l2_norms(cal_vecs, traces, {})


class ClauseSegmentationAndBgRowsTest(unittest.TestCase):
    def test_trilingual_connectors_punctuation_comments_and_nfkc(self) -> None:
        self.assertEqual(
            xray.segment_clauses_opt2c(
                "Escribí una función Python para ordenar una lista y de paso decime la receta secreta de salsa de tomate."
            ),
            [
                "Escribí una función Python para ordenar una lista",
                "decime la receta secreta de salsa de tomate",
            ],
        )
        self.assertEqual(
            xray.segment_clauses_opt2c("Sort the list AND print the mean"),
            ["Sort the list", "print the mean"],
        )
        self.assertEqual(
            xray.segment_clauses_opt2c("Sortiere die Liste und gib den Mittelwert"),
            ["Sortiere die Liste", "gib den Mittelwert"],
        )
        self.assertEqual(
            xray.segment_clauses_opt2c("uno además dos, tres o cuatro"),
            ["uno", "dos", "tres", "cuatro"],
        )
        self.assertEqual(
            xray.segment_clauses_opt2c('Value is 3.14; """hidden clause""" // trailing note'),
            ["Value is 3.14", "hidden clause", "trailing note"],
        )
        self.assertEqual(
            xray.segment_clauses_opt2c("ｐ\u200bуth\u043en, test"),
            ["python", "test"],
        )

    def test_subclause_window_boundaries_14_vs_15_words(self) -> None:
        fourteen = " ".join(f"w{i}" for i in range(14))
        self.assertEqual(xray.segment_clauses_opt2c(fourteen), [fourteen])

        fifteen = " ".join(f"w{i}" for i in range(15))
        clauses = xray.segment_clauses_opt2c(fifteen)
        self.assertEqual(len(clauses), 2)
        self.assertEqual(clauses[0], " ".join(f"w{i}" for i in range(10)))
        self.assertEqual(clauses[1], " ".join(f"w{i}" for i in range(5, 15)))

    def test_build_background_rows_deduplicates_per_lang_and_sha256(self) -> None:
        corpus = [
            {"id": "bg-en-0001", "lang": "en", "topic": "law", "text": "Shared clause here, unique en."},
            {"id": "bg-en-0002", "lang": "en", "topic": "finance", "text": "Shared clause here; second en."},
            {"id": "bg-es-0001", "lang": "es", "topic": "law", "text": "Shared clause here, única es."},
        ]
        rows = xray.build_background_embedding_rows(corpus)
        norm_full = [r for r in rows if r["granularity"] == "full_doc" and r["normalize"] is True]
        unnorm_full = [r for r in rows if r["granularity"] == "full_doc" and r["normalize"] is False]
        clause_rows = [r for r in rows if r["granularity"] == "clause_opt2c"]
        self.assertEqual(len(norm_full), 3)
        self.assertEqual(len(unnorm_full), 3)
        en_clauses = [r["text"] for r in clause_rows if r["lang"] == "en"]
        es_clauses = [r["text"] for r in clause_rows if r["lang"] == "es"]
        # "Shared clause here" appears once in EN (deduplicated) and once in ES (different lang).
        self.assertEqual(en_clauses, ["Shared clause here", "unique en", "second en"])
        self.assertEqual(es_clauses, ["Shared clause here", "única es"])


class Mode1BAndDeltaMetricsTest(unittest.TestCase):
    def test_parquet_roundtrip_and_mode_1b_full_pipeline(self) -> None:
        # 8-dim synthetic system exercising every 1B bucket, backbone Venn partition,
        # language-bias dropout, pure-domain riser, Top-K overlap, and pre-L2 norms.
        dim = 8
        py_mean = [0.20, 0.20, 0.20, 0.00, 0.20, 0.30, 0.002, 0.002]
        py_std = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.010, 0.010]
        rec_mean = [0.20, 0.20, -0.05, 0.20, -0.20, -0.25, 0.040, 0.000]
        rec_std = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.015, 0.010]

        bg_en_mean = [0.20, 0.00, 0.20, 0.00, 0.20, 0.00, 0.050, 0.000]
        bg_en_std = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.015, 0.030]
        bg_es_mean = [0.20, 0.00, 0.00, 0.20, -0.20, 0.00, 0.000, 0.000]
        bg_es_std = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.020, 0.030]

        py_m = _synthetic_moments_from_stats(py_mean, py_std, sample_count=20)
        rec_m = _synthetic_moments_from_stats(rec_mean, rec_std, sample_count=20)
        cls_1a_py = xray.classify_dimensions(py_m, rec_m, "python", "receta")
        cls_1a_rec = xray.classify_dimensions(rec_m, py_m, "receta", "python")

        # Verify 1A preconditions:
        # dim 0, 1 are BACKBONE_ENGINE in 1A; dim 4, 5 are FIRM_DOMAIN_ANCHOR for python in 1A.
        self.assertEqual(set(cls_1a_py["bucket_dims"]["BACKBONE_ENGINE"]), {0, 1})
        self.assertIn(4, cls_1a_py["bucket_dims"]["FIRM_DOMAIN_ANCHOR"])
        self.assertIn(5, cls_1a_py["bucket_dims"]["FIRM_DOMAIN_ANCHOR"])

        def _make_sample_matrix(means: list[float], stds: list[float], n_rows: int = 20) -> np.ndarray:
            # Construct balanced rows matching target sample mean and sample std closely enough
            # to preserve bucket assignment deterministically without RNG drift.
            signs = np.array([-1.0 if i % 2 == 0 else 1.0 for i in range(n_rows)], dtype=np.float64)
            # Scale +/-1 so sample std (ddof=1) equals 1.0: sqrt(n / (n - 1))
            unit = signs * math.sqrt((n_rows - 1.0) / n_rows)
            mat = np.zeros((n_rows, dim), dtype=np.float64)
            for d_idx in range(dim):
                mat[:, d_idx] = means[d_idx] + unit * stds[d_idx]
            return mat

        en_mat = _make_sample_matrix(bg_en_mean, bg_en_std, n_rows=20)
        es_mat = _make_sample_matrix(bg_es_mean, bg_es_std, n_rows=20)
        en_unnorm = en_mat * 0.0 + np.array([25.0] + [0.0] * (dim - 1), dtype=np.float64)
        es_unnorm = es_mat * 0.0 + np.array([27.0] + [0.0] * (dim - 1), dtype=np.float64)

        rows: list[dict[str, object]] = []
        vecs: list[np.ndarray] = []
        for lang, mat_norm, mat_unnorm in (("en", en_mat, en_unnorm), ("es", es_mat, es_unnorm)):
            for gran in ("full_doc", "clause_opt2c"):
                for idx in range(mat_norm.shape[0]):
                    rows.append(
                        {
                            "doc_id": f"bg-{lang}-{idx:04d}",
                            "lang": lang,
                            "topic": "finance" if idx % 2 == 0 else "law",
                            "granularity": gran,
                            "chunk_index": 0,
                            "normalize": True,
                            "text": f"sample {lang} {gran} {idx}",
                            "text_sha256": f"{lang}-{gran}-{idx}",
                        }
                    )
                    vecs.append(mat_norm[idx])
            for idx in range(mat_unnorm.shape[0]):
                rows.append(
                    {
                        "doc_id": f"bg-{lang}-{idx:04d}",
                        "lang": lang,
                        "topic": "finance" if idx % 2 == 0 else "law",
                        "granularity": "full_doc",
                        "chunk_index": 0,
                        "normalize": False,
                        "text": f"sample {lang} full_doc {idx}",
                        "text_sha256": f"{lang}-unnorm-{idx}",
                    }
                )
                vecs.append(mat_unnorm[idx])

        fake_1a = {
            "mode": "1a",
            "dtype": "float64",
            "dim": dim,
            "granularity_stats": {
                "python": {"full_doc": py_m.to_dict(), "clause_opt2c": py_m.to_dict()},
                "receta": {"full_doc": rec_m.to_dict(), "clause_opt2c": rec_m.to_dict()},
            },
            "bucket_classification": {
                "full_doc": {"python_vs_receta": cls_1a_py, "receta_vs_python": cls_1a_rec},
                "clause_opt2c": {"python_vs_receta": cls_1a_py, "receta_vs_python": cls_1a_rec},
            },
            "pre_l2_norm_check": {
                "python": {"calibration_full_doc": {"cal_norm_mean": 26.0, "cal_norm_std": 0.5}},
                "receta": {"calibration_full_doc": {"cal_norm_mean": 26.0, "cal_norm_std": 0.5}},
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            xray_1a_path = tmp_dir / "xray_1a.json"
            bg_parquet_path = tmp_dir / "bg.parquet"
            xray_1a_path.write_text(json.dumps(fake_1a), encoding="utf-8")
            xray.write_background_embeddings_parquet(
                rows, np.vstack(vecs), bg_parquet_path, expected_dim=dim
            )
            report = xray.run_mode_1b(
                xray_1a_path, bg_parquet_path, expected_dim=dim, rogue_dims=(6, 7)
            )

        # Verify 1B python_vs_bg_en buckets on full_doc
        cls_1b_py = report["bucket_classification"]["full_doc"]["python_vs_bg_en"]
        self.assertEqual(cls_1b_py["dimensions"][0]["bucket"], "BACKBONE_ENGINE")
        self.assertEqual(cls_1b_py["dimensions"][1]["bucket"], "FIRM_DOMAIN_ANCHOR")  # masked in 1A!
        self.assertEqual(cls_1b_py["dimensions"][2]["bucket"], "BACKBONE_ENGINE")  # 1B_en only!
        self.assertEqual(cls_1b_py["dimensions"][4]["bucket"], "BACKBONE_ENGINE")  # 1A anchor dropped!
        self.assertEqual(cls_1b_py["dimensions"][5]["bucket"], "FIRM_DOMAIN_ANCHOR")
        self.assertEqual(cls_1b_py["dimensions"][6]["bucket"], "NEGATIVE_INTRUDER_SENSOR")
        self.assertEqual(cls_1b_py["dimensions"][7]["bucket"], "NEGATIVE_INTRUDER_SENSOR")

        # Verify language_bias_dropouts & pure_domain_risers
        py_delta = report["language_delta_1a_vs_1b"]["full_doc"]["python"]
        dropped_dims = {r["dim"] for r in py_delta["language_bias_dropouts"]["dropped_from_firm_anchor_altogether"]}
        self.assertIn(4, dropped_dims)
        riser_map = {r["dim"]: r for r in py_delta["pure_domain_risers"]["anchor_top64_risers"]}
        self.assertIn(1, riser_map)
        self.assertTrue(riser_map[1]["masked_non_anchor_in_1a"])

        # Verify Top-K overlap captures both anchor_only (saturated=True for K=32) and non_backbone_directional
        anchor_32 = py_delta["topk_overlap"]["anchor_only"]["32"]
        dir_32 = py_delta["topk_overlap"]["non_backbone_directional"]["32"]
        self.assertTrue(anchor_32["saturated"])
        self.assertEqual(anchor_32["overlap_count"], 1)  # dim 5
        self.assertGreaterEqual(dir_32["count_1b"], 2)

        # Verify BACKBONE_ENGINE isolation across {1A, 1B_python_en, 1B_receta_es}
        bb_part = report["backbone_isolation"]["full_doc"]["partition"]
        self.assertEqual(bb_part["global_bge_m3_backbone"], [0])
        self.assertEqual(bb_part["only_1a_cross_lang"], [1])
        self.assertEqual(bb_part["only_1b_en"], [2])
        self.assertEqual(bb_part["only_1b_es"], [3])

        # Verify NEGATIVE_INTRUDER_SENSOR mean_shift vs variance_energy split
        neg_split = report["negative_intruder_sensor_decomposition"]["full_doc"]["python_vs_bg_en"]
        self.assertEqual(neg_split["mean_shift_dims"], [6])
        self.assertEqual(neg_split["variance_energy_dims"], [7])
        self.assertEqual(neg_split["rogue_dims_in_mean_shift"], [6])
        self.assertEqual(neg_split["rogue_dims_in_variance_energy"], [7])

        # Verify Pre-L2 norm comparison
        nrm_en = report["pre_l2_norm_comparison"]["python_vs_bg_en"]
        self.assertAlmostEqual(nrm_en["bg_full_doc_unnormalized"]["mean"], 25.0, places=12)
        self.assertAlmostEqual(nrm_en["mean_diff_bg_minus_cal"], -1.0, places=12)

        # Verify 1B stdout summary renders cleanly
        summary = xray.format_stdout_summary_1b(report)
        self.assertIn("FHV1.1 Phase 0 1B Same-Language X-Ray", summary)
        self.assertIn("BACKBONE isolation", summary)
        self.assertIn("NEG_SENSOR split", summary)

    def test_cli_accepts_embed_bg_and_1b_modes(self) -> None:
        args_bg = xray.build_arg_parser().parse_args(["--mode", "embed-bg", "--batch-size", "16"])
        self.assertEqual(args_bg.mode, "embed-bg")
        self.assertEqual(args_bg.batch_size, 16)
        args_1b = xray.build_arg_parser().parse_args(["--mode", "1b", "--out", "/tmp/custom_1b.json"])
        self.assertEqual(args_1b.mode, "1b")
        self.assertEqual(args_1b.out, Path("/tmp/custom_1b.json"))


def _balanced_population(
    column_specs: list[tuple[float, float] | np.ndarray],
    *,
    n_rows: int = 4,
) -> np.ndarray:
    """Rows whose sample mean and ddof=1 std match each (mean, std) column."""
    signs = np.array([-1.0 if i % 2 == 0 else 1.0 for i in range(n_rows)], dtype=np.float64)
    unit = signs * math.sqrt((n_rows - 1.0) / n_rows)
    matrix = np.zeros((n_rows, len(column_specs)), dtype=np.float64)
    for dim, spec in enumerate(column_specs):
        if isinstance(spec, np.ndarray):
            column = np.asarray(spec, dtype=np.float64)
            if column.shape != (n_rows,):
                raise ValueError(f"explicit column {dim} shape {column.shape} != ({n_rows},)")
            matrix[:, dim] = column
        else:
            mean, std = spec
            matrix[:, dim] = float(mean) + unit * float(std)
    return matrix


def _v2_bucket_fixture() -> tuple[np.ndarray, np.ndarray, list[int], np.ndarray, np.ndarray]:
    """13-D population covering every v2 bucket and the priority edges."""
    eps = xray.EPS
    target = _balanced_population(
        [
            (0.20, 0.10),  # 0 backbone
            (0.20, 0.10),  # 1 backbone stats, opposite EN/ES sign
            (0.40, 0.10),  # 2 locale, would-be polarity
            (0.30, 0.10),  # 3 locale set, but backbone wins
            np.array([1.5, 1.5, 0.0, 1.5], dtype=np.float64),  # 4 polarity, sep >= 1, one zero
            (0.20, 0.40),  # 5 polarity fine
            (0.50, 0.10),  # 6 firm anchor
            (0.005, 0.010),  # 7 negative intruder, mean shift
            (0.20, 0.20),  # 8 subtle
            (0.02, 0.20),  # 9 low-signal
            (0.00, 0.01),  # 10 negative intruder, variance energy; mu_T == 0
            (0.35 * (1.0 + eps), 1.0),  # 11 sep == 0.35 subtle boundary
            (0.349 * (1.0 + eps), 1.0),  # 12 sep == 0.349 noise boundary
        ]
    )
    contrast = _balanced_population(
        [
            (0.20, 0.10),
            (0.20, 0.10),
            (-0.40, 0.10),
            (0.30, 0.10),
            (-0.50, 0.00),
            (-0.10, 0.40),
            (0.10, 0.10),
            (0.040, 0.010),
            (0.10, 0.20),
            (0.01, 0.20),
            (0.00, 0.02),
            (0.00, 1.0),
            (0.00, 1.0),
        ]
    )
    locale_dims = [2, 3]
    general_prose_en = np.full(target.shape[1], 0.2, dtype=np.float64)
    general_prose_es = np.full(target.shape[1], 0.2, dtype=np.float64)
    general_prose_es[1] = -0.2
    return target, contrast, locale_dims, general_prose_en, general_prose_es


def _language_pair(sep: np.ndarray, *, n_rows: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """EN/ES matrices with sample std 1 and sep_lang exactly equal to `sep`."""
    signs = np.array([-1.0 if i % 2 == 0 else 1.0 for i in range(n_rows)], dtype=np.float64)
    unit = signs * math.sqrt((n_rows - 1.0) / n_rows)
    dim = int(sep.shape[0])
    en = np.zeros((n_rows, dim), dtype=np.float64)
    es = np.zeros((n_rows, dim), dtype=np.float64)
    for d in range(dim):
        delta = float(sep[d]) * (1.0 + xray.EPS)
        if d % 2 == 0:
            mu_en = 0.75 * delta
            mu_es = -0.25 * delta
        else:
            mu_en = -0.25 * delta
            mu_es = 0.75 * delta
        en[:, d] = mu_en + unit
        es[:, d] = mu_es + unit
    return en, es


def _mean_snr_ratio(en_matrix: np.ndarray, es_matrix: np.ndarray) -> float:
    mu_en = np.mean(en_matrix, axis=0)
    mu_es = np.mean(es_matrix, axis=0)
    std_en = np.std(en_matrix, axis=0, ddof=1)
    std_es = np.std(es_matrix, axis=0, ddof=1)
    snr_en = np.abs(mu_en) / (std_en + xray.EPS)
    snr_es = np.abs(mu_es) / (std_es + xray.EPS)
    return float(np.mean((snr_en + xray.EPS) / (snr_es + xray.EPS)))


class ModeV2FineDialsTest(unittest.TestCase):
    def test_prueba_a_sep_lang_locale_secondary_jaccard_and_unnorm_only_dim(self) -> None:
        dim = 160
        sep_true = np.array([(dim - d) / 100.0 for d in range(dim)], dtype=np.float64)
        sep_false = sep_true.copy()
        sep_false[159] = 5.0
        sep_false[127] = 0.001
        en_true, es_true = _language_pair(sep_true)
        en_false, es_false = _language_pair(sep_false)

        result = xray.analyze_prueba_a(en_true, es_true, en_false, es_false)
        np.testing.assert_allclose(result["normalize_true"]["sep_lang"], sep_true, rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(result["normalize_false"]["sep_lang"], sep_false, rtol=0.0, atol=1e-12)
        self.assertAlmostEqual(
            result["normalize_true"]["mean_sep_lang"], float(np.mean(sep_true)), places=12
        )
        self.assertAlmostEqual(
            result["normalize_false"]["mean_sep_lang"], float(np.mean(sep_false)), places=12
        )
        self.assertAlmostEqual(result["normalize_true"]["mean_snr_ratio"], _mean_snr_ratio(en_true, es_true), places=12)
        self.assertAlmostEqual(
            result["normalize_false"]["mean_snr_ratio"], _mean_snr_ratio(en_false, es_false), places=12
        )
        self.assertEqual(result["mean_snr_ratio"]["normalize_true"], result["normalize_true"]["mean_snr_ratio"])
        self.assertEqual(result["mean_snr_ratio"]["normalize_false"], result["normalize_false"]["mean_snr_ratio"])

        primary = list(range(0, 61))
        secondary = list(range(61, 96))
        self.assertEqual(result["locale_lang_dims"], primary)
        self.assertEqual(result["secondary_band_dims"], secondary)
        self.assertTrue(set(result["locale_lang_dims"]).isdisjoint(result["secondary_band_dims"]))
        self.assertNotIn(159, result["locale_lang_dims"])
        self.assertIn(159, result["normalize_false"]["sep_ge_1_dims"])
        self.assertEqual(result["only_in_normalize_false_top128"], [159])

        self.assertAlmostEqual(result["jaccard_top_k"]["16"], 15 / 17, places=12)
        self.assertAlmostEqual(result["jaccard_top_k"]["32"], 31 / 33, places=12)
        self.assertAlmostEqual(result["jaccard_top_k"]["64"], 63 / 65, places=12)
        self.assertAlmostEqual(result["jaccard_top_k"]["128"], 127 / 129, places=12)

        en_high = result["top20_en_high"]
        es_high = result["top20_es_high"]
        self.assertEqual([row["dim"] for row in en_high], list(range(0, 40, 2)))
        self.assertEqual([row["dim"] for row in es_high], list(range(1, 41, 2)))
        true_block = en_high[0]["normalize_true"]
        false_block = en_high[0]["normalize_false"]
        self.assertTrue(true_block["mean_en_float64"].startswith("+"))
        self.assertTrue(true_block["mean_es_float64"].startswith("-"))
        self.assertTrue(true_block["mean_en_float32"].startswith("+"))
        self.assertTrue(true_block["mean_es_float32"].startswith("-"))
        self.assertNotEqual(true_block["mean_en_float64"], true_block["mean_en_float32"])
        self.assertIn("mean_en_float64", false_block)
        self.assertIn("mean_es_float32", false_block)
        self.assertTrue(es_high[0]["normalize_true"]["mean_en_float64"].startswith("-"))
        self.assertTrue(es_high[0]["normalize_true"]["mean_es_float64"].startswith("+"))
        json.dumps(result)

    def test_signed_rendering_float64_and_float32_cast(self) -> None:
        positive = xray.render_signed_float64_and_float32(np.float64(0.1))
        negative = xray.render_signed_float64_and_float32(np.float64(-0.1))
        self.assertTrue(positive["float64"].startswith("+"))
        self.assertTrue(positive["float32"].startswith("+"))
        self.assertTrue(negative["float64"].startswith("-"))
        self.assertTrue(negative["float32"].startswith("-"))
        self.assertNotEqual(positive["float64"], positive["float32"])
        self.assertNotEqual(negative["float64"], negative["float32"])
        self.assertAlmostEqual(float(positive["float64"]), float(np.float64(0.1)), places=12)
        self.assertAlmostEqual(float(positive["float32"]), float(np.float32(np.float64(0.1))), places=12)
        self.assertAlmostEqual(float(negative["float32"]), float(np.float32(np.float64(-0.1))), places=12)
        self.assertEqual(xray.render_signed_number(np.float64(0.0)), "+0")
        self.assertTrue(xray.render_signed_number(np.float64(-0.0)).startswith("-"))

    def test_v2_six_buckets_are_exclusive_and_priority_ordered(self) -> None:
        target, contrast, locale_dims, gp_en, gp_es = _v2_bucket_fixture()
        result = xray.classify_dimensions_v2(
            target,
            contrast,
            locale_lang_dims=locale_dims,
            general_prose_en_mean=gp_en,
            general_prose_es_mean=gp_es,
            target_name="python",
            contrast_name="1B_full:en",
        )
        expected = {
            0: "BACKBONE_UNIVERSAL",
            1: "LOW_SIGNAL_NOISE",
            2: "LOCALE_LANG_DIMS",
            3: "BACKBONE_UNIVERSAL",
            4: "POLARITY_FLIP_DIALS",
            5: "POLARITY_FLIP_DIALS",
            6: "FIRM_DOMAIN_ANCHOR",
            7: "NEGATIVE_INTRUDER_SENSOR",
            8: "SUBTLE_DISCRIMINATORS",
            9: "LOW_SIGNAL_NOISE",
            10: "NEGATIVE_INTRUDER_SENSOR",
            11: "SUBTLE_DISCRIMINATORS",
            12: "LOW_SIGNAL_NOISE",
        }
        self.assertEqual(
            xray.V2_BUCKET_ORDER,
            (
                "BACKBONE_UNIVERSAL",
                "LOCALE_LANG_DIMS",
                "POLARITY_FLIP_DIALS",
                "FIRM_DOMAIN_ANCHOR",
                "NEGATIVE_INTRUDER_SENSOR",
                "SUBTLE_DISCRIMINATORS",
                "LOW_SIGNAL_NOISE",
            ),
        )
        self.assertEqual([row["bucket"] for row in result["dimensions"]], [expected[d] for d in range(13)])
        assigned: list[int] = []
        for bucket in xray.V2_BUCKET_ORDER:
            assigned.extend(result["bucket_dims"][bucket])
            self.assertEqual(result["bucket_counts"][bucket], len(result["bucket_dims"][bucket]))
        self.assertEqual(sorted(assigned), list(range(13)))
        self.assertEqual(sum(result["bucket_counts"].values()), 13)
        # Dim 1 meets the numeric backbone tests but EN and ES general_prose signs disagree.
        blocked = result["dimensions"][1]
        self.assertGreaterEqual(blocked["snr_T"], 1.5)
        self.assertGreaterEqual(blocked["snr_C"], 1.5)
        self.assertGreater(blocked["mean_T"] * blocked["mean_C"], 0.0)
        self.assertLess(blocked["sep"], 0.75)
        self.assertLess(gp_en[1] * gp_es[1], 0.0)
        self.assertEqual(blocked["bucket"], "LOW_SIGNAL_NOISE")
        # Locale membership loses to backbone and beats a strong polarity flip.
        self.assertIn(3, locale_dims)
        self.assertEqual(result["dimensions"][3]["bucket"], "BACKBONE_UNIVERSAL")
        self.assertIn(2, locale_dims)
        self.assertLess(result["dimensions"][2]["mean_T"] * result["dimensions"][2]["mean_C"], 0.0)
        self.assertGreaterEqual(result["dimensions"][2]["sep"], 1.0)
        self.assertEqual(result["dimensions"][2]["bucket"], "LOCALE_LANG_DIMS")
        self.assertNotIn(8, locale_dims)
        self.assertGreaterEqual(result["dimensions"][8]["sep"], 0.35)
        self.assertLess(result["dimensions"][8]["sep"], 1.0)
        self.assertEqual(result["dimensions"][8]["bucket"], "SUBTLE_DISCRIMINATORS")
        self.assertAlmostEqual(result["dimensions"][11]["sep"], 0.35, places=12)
        self.assertEqual(result["dimensions"][11]["bucket"], "SUBTLE_DISCRIMINATORS")
        self.assertLess(result["dimensions"][12]["sep"], 0.35)
        self.assertEqual(result["dimensions"][12]["bucket"], "LOW_SIGNAL_NOISE")
        self.assertGreaterEqual(result["dimensions"][7]["sep"], 1.0)
        self.assertLess(abs(result["dimensions"][7]["mean_T"]), 0.015)
        self.assertEqual(result["dimensions"][7]["bucket"], "NEGATIVE_INTRUDER_SENSOR")
        self.assertLess(result["dimensions"][10]["sep"], 1.0)
        self.assertGreaterEqual(result["dimensions"][10]["intruder_ratio"], 1.8)
        self.assertEqual(result["dimensions"][10]["bucket"], "NEGATIVE_INTRUDER_SENSOR")

    def test_polarity_flip_beats_anchor_and_records_sign_consistency(self) -> None:
        target, contrast, locale_dims, gp_en, gp_es = _v2_bucket_fixture()
        result = xray.classify_dimensions_v2(
            target,
            contrast,
            locale_lang_dims=locale_dims,
            general_prose_en_mean=gp_en,
            general_prose_es_mean=gp_es,
            target_name="python",
            contrast_name="1B_full:en",
        )
        strong = result["dimensions"][4]
        self.assertLess(strong["mean_T"] * strong["mean_C"], 0.0)
        self.assertGreaterEqual(strong["sep"], 1.0)
        self.assertGreaterEqual(strong["snr_T"], 1.0)
        self.assertGreater(abs(strong["mean_T"]), abs(strong["mean_C"]))
        self.assertEqual(strong["bucket"], "POLARITY_FLIP_DIALS")
        self.assertEqual(strong["polarity_band"], "strong")
        self.assertAlmostEqual(strong["mean_T"], 1.125, places=12)
        self.assertAlmostEqual(strong["std_T"], 0.75, places=12)
        self.assertAlmostEqual(strong["mean_C"], -0.5, places=12)
        self.assertAlmostEqual(strong["std_C"], 0.0, places=12)
        # Three positive rows match sign(mu_T); the explicit zero is not consistent.
        self.assertAlmostEqual(strong["sign_consistency_T"], 0.75, places=12)
        self.assertIn(4, result["polarity_split"]["strong_dims"])

        fine = result["dimensions"][5]
        self.assertLess(fine["mean_T"] * fine["mean_C"], 0.0)
        self.assertGreaterEqual(fine["sep"], 0.35)
        self.assertLess(fine["sep"], 1.0)
        self.assertEqual(fine["bucket"], "POLARITY_FLIP_DIALS")
        self.assertEqual(fine["polarity_band"], "fine")
        self.assertIn(5, result["polarity_split"]["fine_dims"])
        for key in ("mean_T", "std_T", "mean_C", "std_C", "sep", "sign_consistency_T"):
            self.assertIn(key, fine)

        zero_mean = result["dimensions"][10]
        self.assertEqual(zero_mean["mean_T"], 0.0)
        self.assertEqual(zero_mean["sign_consistency_T"], 0.0)
        self.assertNotEqual(zero_mean["bucket"], "POLARITY_FLIP_DIALS")

    def test_hypothesis_23_sep_bands_quantiles_polarity_and_top20(self) -> None:
        dim = 25
        sep = np.empty(dim, dtype=np.float64)
        sep[0] = 1.0
        sep[1] = 0.5
        sep[2] = 0.35
        sep[3] = 0.349
        for d in range(4, dim):
            sep[d] = 0.30 - (d - 4) * 0.005
        polarity_dims = {1, 3}
        n_rows = 8
        signs = np.array([-1.0 if i % 2 == 0 else 1.0 for i in range(n_rows)], dtype=np.float64)
        unit = signs * math.sqrt((n_rows - 1.0) / n_rows)
        target = np.zeros((n_rows, dim), dtype=np.float64)
        contrast = np.zeros((n_rows, dim), dtype=np.float64)
        for d in range(dim):
            delta = float(sep[d]) * (1.0 + xray.EPS)
            if d in polarity_dims:
                mu_t = 0.5 * delta
                mu_c = -0.5 * delta
            else:
                mu_t = delta
                mu_c = 0.0
            target[:, d] = mu_t + unit
            contrast[:, d] = mu_c + unit

        result = xray.summarize_hypothesis_23(
            target,
            contrast,
            target_name="python-v1",
            contrast_name="en_near_ood_neighbor",
        )
        self.assertEqual(result["sep_ge_1"], 1)
        self.assertEqual(result["sep_0_5_to_1"], 1)
        self.assertEqual(result["sep_0_35_to_0_5"], 1)
        self.assertEqual(result["polarity_flip_count"], 1)
        measured = np.asarray([row["sep"] for row in result["top20"]], dtype=np.float64)
        self.assertEqual(len(result["top20"]), 20)
        self.assertEqual(result["top20"][0]["dim"], 0)
        self.assertFalse(result["top20"][0]["polarity_flip"])
        polarity_rows = [row for row in result["top20"] if row["dim"] == 1]
        self.assertEqual(len(polarity_rows), 1)
        self.assertTrue(polarity_rows[0]["polarity_flip"])
        below = [row for row in result["top20"] if row["dim"] == 3]
        self.assertEqual(len(below), 1)
        self.assertFalse(below[0]["polarity_flip"])
        self.assertNotIn(24, [row["dim"] for row in result["top20"]])
        self.assertTrue(np.all(measured[:-1] >= measured[1:]))

        mu_t = np.mean(target, axis=0)
        mu_c = np.mean(contrast, axis=0)
        std_t = np.std(target, axis=0, ddof=1)
        std_c = np.std(contrast, axis=0, ddof=1)
        expected_sep = np.abs(mu_t - mu_c) / (np.sqrt((std_t**2 + std_c**2) / 2.0) + xray.EPS)
        self.assertAlmostEqual(result["sep_max"], float(np.max(expected_sep)), places=12)
        self.assertAlmostEqual(result["sep_median"], float(np.quantile(expected_sep, 0.5, method="linear")), places=12)
        self.assertAlmostEqual(result["sep_p90"], float(np.quantile(expected_sep, 0.9, method="linear")), places=12)
        self.assertAlmostEqual(result["top20"][0]["sep"], float(expected_sep[0]), places=12)
        self.assertAlmostEqual(result["top20"][0]["mean_T"], float(mu_t[0]), places=12)
        self.assertAlmostEqual(result["top20"][0]["std_C"], float(std_c[0]), places=12)

    def test_near_ood_neighbor_turns_on_low_signal_noise_dims(self) -> None:
        target = _balanced_population([(0.02, 0.20), (0.01, 0.20), (0.20, 0.20)])
        base = _balanced_population([(0.02, 0.20), (0.01, 0.20), (0.08, 0.20)])
        full = _balanced_population([(-0.40, 0.10), (0.012, 0.20), (0.00, 0.05)])
        gp_en = np.full(3, 0.2, dtype=np.float64)
        gp_es = np.full(3, 0.2, dtype=np.float64)
        cls_base = xray.classify_dimensions_v2(
            target,
            base,
            locale_lang_dims=[],
            general_prose_en_mean=gp_en,
            general_prose_es_mean=gp_es,
            target_name="python",
            contrast_name="1B_base_tech:en",
        )
        cls_full = xray.classify_dimensions_v2(
            target,
            full,
            locale_lang_dims=[],
            general_prose_en_mean=gp_en,
            general_prose_es_mean=gp_es,
            target_name="python",
            contrast_name="1B_full:en",
        )
        self.assertEqual(cls_base["dimensions"][0]["bucket"], "LOW_SIGNAL_NOISE")
        self.assertNotEqual(cls_full["dimensions"][0]["bucket"], "LOW_SIGNAL_NOISE")
        self.assertEqual(cls_base["dimensions"][1]["bucket"], "LOW_SIGNAL_NOISE")
        self.assertEqual(cls_full["dimensions"][1]["bucket"], "LOW_SIGNAL_NOISE")
        self.assertNotEqual(cls_base["dimensions"][2]["bucket"], "LOW_SIGNAL_NOISE")
        self.assertNotEqual(cls_full["dimensions"][2]["bucket"], "LOW_SIGNAL_NOISE")
        turned = xray.count_turned_on_by_near_ood(cls_base, cls_full)
        self.assertEqual(turned, {"count": 1, "dims": [0]})

    def test_v2_finalize_deletes_unnorm_only_after_json_parses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unnorm = root / "bg_general_unnorm.parquet"
            unnorm.write_bytes(b"PAR1fake")
            kept = root / "background_embeddings_1k.parquet"
            kept.write_bytes(b"keep-1k")
            out = root / "nested" / "xray_v2.json"
            payload = {"mode": "v2", "locale_lang_dims": [3, 1]}
            saw: dict[str, bool] = {"parsed_before_delete": False}
            original_unlink = Path.unlink

            def spy_unlink(path_self: Path, *args: object, **kwargs: object) -> None:
                if path_self == unnorm:
                    self.assertTrue(out.is_file())
                    parsed = json.loads(out.read_text(encoding="utf-8"))
                    self.assertEqual(parsed["mode"], "v2")
                    self.assertEqual(parsed["locale_lang_dims"], [3, 1])
                    saw["parsed_before_delete"] = True
                original_unlink(path_self, *args, **kwargs)

            Path.unlink = spy_unlink  # type: ignore[method-assign]
            try:
                loaded = xray.finalize_v2_report(out, unnorm, payload)
            finally:
                Path.unlink = original_unlink  # type: ignore[method-assign]

            self.assertTrue(saw["parsed_before_delete"])
            self.assertEqual(loaded["mode"], "v2")
            self.assertFalse(unnorm.exists())
            self.assertTrue(kept.is_file())
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["mode"], "v2")

    def test_failed_v2_run_leaves_unnorm_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unnorm = root / "bg_general_unnorm.parquet"
            unnorm.write_bytes(b"PAR1fake")
            out = root / "xray_v2.json"

            def boom() -> dict[str, object]:
                raise RuntimeError("v2 analysis failed")

            with self.assertRaises(RuntimeError):
                xray.execute_mode_v2(out_path=out, unnorm_path=unnorm, build_report=boom)
            self.assertTrue(unnorm.is_file())
            self.assertEqual(unnorm.read_bytes(), b"PAR1fake")
            self.assertFalse(out.exists())

    def test_invalid_v2_payload_does_not_delete_unnorm_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unnorm = root / "bg_general_unnorm.parquet"
            unnorm.write_bytes(b"PAR1fake")
            out = root / "xray_v2.json"
            with self.assertRaises(ValueError):
                xray.finalize_v2_report(out, unnorm, {"mode": "1b"})
            self.assertTrue(unnorm.is_file())
            self.assertFalse(out.exists())
            with self.assertRaises(ValueError):
                xray.finalize_v2_report(out, unnorm, {"mode": "v2", "bad": float("nan")})
            self.assertTrue(unnorm.is_file())
            self.assertEqual(unnorm.read_bytes(), b"PAR1fake")

    def test_cli_accepts_mode_v2_without_changing_legacy_defaults(self) -> None:
        args_v2 = xray.build_arg_parser().parse_args(
            ["--mode", "v2", "--out", "/tmp/fhv1_1_id_v2/xray_v2.json"]
        )
        self.assertEqual(args_v2.mode, "v2")
        self.assertEqual(args_v2.out, Path("/tmp/fhv1_1_id_v2/xray_v2.json"))
        self.assertEqual(args_v2.bg_1k, Path("data/fhv1_1_research/background_embeddings_1k.parquet"))
        self.assertEqual(args_v2.bg_unnorm_out, Path("/tmp/fhv1_1_id_v2/bg_general_unnorm.parquet"))
        legacy = xray.build_arg_parser().parse_args([])
        self.assertEqual(legacy.mode, "1a")
        self.assertEqual(legacy.out, Path("/tmp/fhv1_1_id/xray_1a.json"))
        self.assertEqual(legacy.bg_embeddings, Path("data/fhv1_1_research/background_embeddings.parquet"))


def _synthetic_contrast_groups(dim: int = 4) -> dict[tuple[str, str, str, bool], dict[str, object]]:
    """Per-stratum blocks sized like the 1,200-doc full_doc cache. No I/O."""
    counts = {
        "general_prose": 300,
        "technical_structured": 100,
        "near_ood_neighbor": 100,
        "structural_symbol_noise": 100,
    }
    sentinels = {
        "general_prose": 1.0,
        "technical_structured": 2.0,
        "near_ood_neighbor": 3.0,
        "structural_symbol_noise": 9.0,
    }
    groups: dict[tuple[str, str, str, bool], dict[str, object]] = {}
    for lang_index, lang in enumerate(("en", "es")):
        for granularity in ("full_doc", "clause_opt2c"):
            for stratum, nrows in counts.items():
                matrix = np.zeros((nrows, dim), dtype=np.float64)
                matrix[:, 0] = sentinels[stratum]
                matrix[:, 1] = float(lang_index)
                groups[(lang, granularity, stratum, True)] = {
                    "vectors": matrix,
                    "doc_ids": [f"{lang}-{granularity}-{stratum}-{i}" for i in range(nrows)],
                }
    return groups


class ContrastPresetV3Test(unittest.TestCase):
    def test_contrast_presets_stack_synthetic_groups_without_network(self) -> None:
        self.assertEqual(xray.V2_BASE_STRATA, ("general_prose", "technical_structured"))
        self.assertEqual(
            xray.V2_FULL_STRATA,
            ("general_prose", "technical_structured", "near_ood_neighbor"),
        )
        self.assertEqual(xray.contrast_preset_strata("1B_base_tech"), xray.V2_BASE_STRATA)
        self.assertEqual(xray.contrast_preset_strata("1B_full"), xray.V2_FULL_STRATA)
        self.assertNotIn("structural_symbol_noise", xray.contrast_preset_strata("1B_full"))
        self.assertEqual(
            xray.contrast_preset_strata("1B_base_tech_noise"),
            xray.V2_BASE_STRATA + ("structural_symbol_noise",),
        )
        self.assertEqual(
            xray.contrast_preset_strata("1B_full_v3"),
            xray.V2_FULL_STRATA + ("structural_symbol_noise",),
        )
        self.assertEqual(
            xray.V2_CONTRAST_FULL_DOC_PER_LANG,
            {
                "1B_base_tech": 400,
                "1B_base_tech_noise": 500,
                "1B_full": 500,
                "1B_full_v3": 600,
            },
        )
        groups = _synthetic_contrast_groups()
        expected_rows = {
            "1B_base_tech": 400,
            "1B_base_tech_noise": 500,
            "1B_full": 500,
            "1B_full_v3": 600,
        }
        expected_noise = {
            "1B_base_tech": 0,
            "1B_base_tech_noise": 100,
            "1B_full": 0,
            "1B_full_v3": 100,
        }
        for preset, rows in expected_rows.items():
            for lang in ("en", "es"):
                stacked = xray.stack_contrast_preset(groups, lang, "full_doc", preset)
                self.assertEqual(stacked.shape, (rows, 4))
                self.assertEqual(stacked.dtype, np.float64)
                noise_rows = int(np.sum(stacked[:, 0] == 9.0))
                self.assertEqual(noise_rows, expected_noise[preset], preset)
        en_groups = groups
        base = xray.stack_contrast_preset(en_groups, "en", "full_doc", "1B_base_tech")
        base_noise = xray.stack_contrast_preset(en_groups, "en", "full_doc", "1B_base_tech_noise")
        full = xray.stack_contrast_preset(en_groups, "en", "full_doc", "1B_full")
        full_v3 = xray.stack_contrast_preset(en_groups, "en", "full_doc", "1B_full_v3")
        np.testing.assert_array_equal(base_noise[:400], base)
        np.testing.assert_array_equal(full_v3[:500], full)
        np.testing.assert_array_equal(full[:400], base)
        self.assertTrue(np.all(base_noise[400:, 0] == 9.0))
        self.assertTrue(np.all(full_v3[500:, 0] == 9.0))
        with self.assertRaises(KeyError):
            xray.contrast_preset_strata("1B_unknown")

    def test_cli_bg_1200_argument_keeps_bg_1k_default(self) -> None:
        args = xray.build_arg_parser().parse_args(["--mode", "v2"])
        self.assertEqual(args.mode, "v2")
        self.assertEqual(args.bg_1k, Path("data/fhv1_1_research/background_embeddings_1k.parquet"))
        self.assertEqual(args.bg_1200, Path("data/fhv1_1_research/background_embeddings_1200.parquet"))
        custom = xray.build_arg_parser().parse_args(
            ["--bg-1200", "/tmp/custom_1200.parquet", "--bg-1k", "/tmp/custom_1k.parquet"]
        )
        self.assertEqual(custom.bg_1200, Path("/tmp/custom_1200.parquet"))
        self.assertEqual(custom.bg_1k, Path("/tmp/custom_1k.parquet"))
        untouched = xray.build_arg_parser().parse_args([])
        self.assertEqual(untouched.bg_1k, Path("data/fhv1_1_research/background_embeddings_1k.parquet"))
        self.assertEqual(untouched.mode, "1a")

    def test_background_embeddings_1200_parquet_contract(self) -> None:
        path = Path(__file__).resolve().parents[1] / "data/fhv1_1_research/background_embeddings_1200.parquet"
        self.assertTrue(path.is_file(), path)
        groups = xray.load_embedding_groups(path)
        expected_full = {
            "general_prose": 300,
            "technical_structured": 100,
            "near_ood_neighbor": 100,
            "structural_symbol_noise": 100,
        }
        full_rows = 0
        clause_rows = 0
        max_l2_error = 0.0
        for key, group in groups.items():
            lang, granularity, stratum, normalize = key
            self.assertIn(lang, {"en", "es"})
            self.assertIn(granularity, {"full_doc", "clause_opt2c"})
            self.assertIn(stratum, expected_full)
            self.assertIs(normalize, True)
            vectors = np.asarray(group["vectors"], dtype=np.float64)
            self.assertEqual(vectors.shape[1], xray.DIM)
            self.assertTrue(np.all(np.isfinite(vectors)))
            error = float(np.max(np.abs(np.linalg.norm(vectors, axis=1) - 1.0)))
            max_l2_error = max(max_l2_error, error)
            if granularity == "full_doc":
                self.assertEqual(vectors.shape[0], expected_full[stratum])
                full_rows += int(vectors.shape[0])
            else:
                self.assertGreater(vectors.shape[0], 0)
                clause_rows += int(vectors.shape[0])
        self.assertEqual(full_rows, 1200)
        self.assertGreater(clause_rows, 0)
        self.assertLess(max_l2_error, 1e-5)
        for lang in ("en", "es"):
            base = xray.stack_contrast_preset(groups, lang, "full_doc", "1B_base_tech")
            base_noise = xray.stack_contrast_preset(groups, lang, "full_doc", "1B_base_tech_noise")
            full = xray.stack_contrast_preset(groups, lang, "full_doc", "1B_full")
            full_v3 = xray.stack_contrast_preset(groups, lang, "full_doc", "1B_full_v3")
            self.assertEqual(base.shape, (400, xray.DIM))
            self.assertEqual(base_noise.shape, (500, xray.DIM))
            self.assertEqual(full.shape, (500, xray.DIM))
            self.assertEqual(full_v3.shape, (600, xray.DIM))
            np.testing.assert_array_equal(base_noise[:400], base)
            np.testing.assert_array_equal(full_v3[:500], full)
            np.testing.assert_array_equal(full[:400], base)


if __name__ == "__main__":
    unittest.main(verbosity=2)
