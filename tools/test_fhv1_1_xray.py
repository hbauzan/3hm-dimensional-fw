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


if __name__ == "__main__":
    unittest.main(verbosity=2)
