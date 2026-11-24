#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""The v4 report generator copies JSON literals and keeps above/below prose consistent."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import fhv1_1_id_v4_report as report


FIXTURE_F1 = "0.7022222222222222"


def _metric(f1: float) -> dict[str, float]:
    return {
        "tp": 79,
        "fn": 21,
        "tn": 254,
        "fp": 46,
        "precision": 0.632,
        "recall": 0.79,
        "f1": f1,
        "frr": 0.21,
        "far": 0.15333333333333332,
        "threshold": 0.5272183609200629,
        "roc_auc": 0.9162999999999999,
    }


def _recipe(*, name: str = "eje1_plus_struct|b=0.10|l=-|n=-|w=-", family: str = "eje1_plus_struct", beta: float = 0.1) -> dict[str, object]:
    return {
        "name": name,
        "family": family,
        "beta": beta,
        "lam": None,
        "near_tag": None,
        "near_prob": None,
        "w_f": None,
    }


def _dual_axis_cell(f1: float = 0.7022222222222222) -> dict[str, object]:
    recipe = _recipe()
    metric = _metric(f1)
    return {
        "domain": "python",
        "granularity": "full_only",
        "catalog_size": 12,
        "recipes": [_recipe(name="eje1_only|b=0.00|l=-|n=-|w=-", family="eje1_only", beta=0.0), recipe],
        "frozen": {
            "recipe": recipe,
            "modal_column": 1,
            "nested_oof": {
                "seeds": [0, 1, 2, 3, 4],
                "f1": {"mean": 0.7189992166038128, "std": 0.002795922874350561},
                "frr": {"mean": 0.258, "std": 0.008366600265340763},
                "far": {"mean": 0.10733333333333332, "std": 0.005477225575051658},
                "roc_auc": {"mean": 0.9155266666666666, "std": 0.0012044823692265378},
                "per_seed": [
                    {
                        "seed": 0,
                        "f1": 0.7192118226600985,
                        "frr": 0.27,
                        "far": 0.1,
                        "roc_auc": 0.9162999999999999,
                    }
                ],
            },
            "oracle_upper_bound": {
                "tag": "[ORACLE_UPPER_BOUND]",
                "f1": 0.7428571428571429,
                "frr": 0.22,
                "far": 0.10666666666666667,
                "threshold": 0.5344316856798338,
                "source": "seed0_mixed_scores_fit_on_all_holdout_labels",
            },
            "cal_only": {"p05": dict(metric), "p10": dict(metric), "p15": dict(metric)},
        },
        "dual_axis_and_cal_only": [
            {
                "near_tag": "p10",
                "near_prob": 0.1,
                "t_gen_p10": 0.5,
                "t_near": 0.4,
                "tp": 1,
                "fn": 1,
                "tn": 1,
                "fp": 1,
                "precision": 0.5,
                "recall": 0.5,
                "f1": 0.6755555555555556,
                "frr": 0.24,
                "far": 0.16333333333333333,
                "roc_auc": 0.8785333333333333,
                "pr_auc_in_domain": 0.7,
                "pr_auc_reject": 0.9,
            }
        ],
        "auc": {"roc_auc": 0.9162999999999999, "pr_auc_in_domain": 0.7, "pr_auc_reject": 0.9},
        "subgroups": {
            "quadrants": {
                "IN_DOMAIN_VALID": {"n": 100, "kind": "frr", "error_rate": 0.21},
                "OUT_OF_DOMAIN_BENIGN": {"n": 100, "kind": "far", "error_rate": 0.0},
                "HYBRID_BOUNDARY": {"n": 100, "kind": "far", "error_rate": 0.34},
                "ADVERSARIAL_FUZZING": {"n": 100, "kind": "far", "error_rate": 0.12},
            },
            "subtypes": [
                {
                    "subtype": "near_ood_neighbor",
                    "category": "HYBRID_BOUNDARY",
                    "n": 12,
                    "kind": "far",
                    "error_rate": 0.5833333333333334,
                },
                {
                    "subtype": "dilution_80_20",
                    "category": "HYBRID_BOUNDARY",
                    "n": 10,
                    "kind": "far",
                    "error_rate": 0.7,
                },
                {
                    "subtype": "short_idiom_query",
                    "category": "IN_DOMAIN_VALID",
                    "n": 20,
                    "kind": "frr",
                    "error_rate": 0.5,
                },
            ],
        },
        "canary": {
            "pattern": r"\b(?:sqlite3|subprocess|json)\b",
            "kinds": {
                "sqlite3": {
                    "kind": "sqlite3",
                    "n_marker": 4,
                    "n_marker_in_domain_valid": 1,
                    "all_marker": {"n": 4, "kind": "f1", "error_rate": 0.6666666666666666},
                    "in_domain_valid_marker": {"n": 1, "kind": "frr", "error_rate": 0.0},
                    "f1": None,
                    "frr": None,
                },
                "subprocess": {
                    "kind": "subprocess",
                    "n_marker": 4,
                    "n_marker_in_domain_valid": 3,
                    "all_marker": {"n": 4, "kind": "f1", "error_rate": 0.8571428571428571},
                    "in_domain_valid_marker": {"n": 3, "kind": "frr", "error_rate": 0.0},
                    "f1": None,
                    "frr": None,
                },
                "json": {
                    "kind": "json",
                    "n_marker": 12,
                    "n_marker_in_domain_valid": 9,
                    "all_marker": {"n": 12, "kind": "f1", "error_rate": 0.9},
                    "in_domain_valid_marker": {"n": 9, "kind": "frr", "error_rate": 0.0},
                    "f1": None,
                    "frr": None,
                },
            },
            "any_kind": {
                "n_marker": 17,
                "all_marker": {"n": 17, "kind": "f1", "error_rate": 0.88},
            },
        },
        "struct_latency_us": {
            "definition": "microseconds per score() call on holdout strings",
            "p50_us": 25.6045,
            "p99_us": 272.75013999999936,
            "full_doc": {"n": 400, "p50_us": 58.625, "p99_us": 1311.0751699999998},
            "clause_opt2c": {"n": 1968, "p50_us": 23.541, "p99_us": 50.13760999999997},
        },
        "clause_caps": [None, 16, 24, 32],
        "dtype": "float64",
        "normalize": True,
        "dir_variant": "dir1024_sig_sep",
        "eje1_preset": "1B_base_tech",
        "eje2_stratum": "near_ood_neighbor",
        "cal_oof": True,
    }


def _manifest() -> dict[str, object]:
    return {
        "mode": "v4",
        "dtype": "float64",
        "dim": 1024,
        "normalize": True,
        "n_cells": 4,
        "cells": [
            {
                "file": "description_only__python__embedding.json",
                "bytes": 50,
                "kind": "description_embedding",
            },
            {
                "file": "flooding_latency_v4.json",
                "bytes": 50,
                "path": "/tmp/x/flooding_latency_v4.json",
                "kind": "flooding_latency",
            },
            {
                "file": "python__n_cal_volume_curve.json",
                "bytes": 50,
                "path": "/tmp/x/python__n_cal_volume_curve.json",
                "domain": "python",
                "kind": "n_cal",
            },
            {
                "file": "python__full_only__dual_axis_v4.json",
                "bytes": 100,
                "path": "/tmp/x/python__full_only__dual_axis_v4.json",
                "domain": "python",
                "granularity": "full_only",
                "frozen_recipe": "eje1_plus_struct|b=0.10|l=-|n=-|w=-",
                "cal_only_p10_f1": 0.7022222222222222,
                "kind": "dual_axis",
            },
            {
                "file": "python__clause_cap_eval.json",
                "bytes": 50,
                "path": "/tmp/x/python__clause_cap_eval.json",
                "domain": "python",
                "kind": "clause_cap",
            },
        ],
        "n_cal_files": [],
        "clause_cap_files": [],
        "bootstrap_resamples": 1000,
        "bootstrap_seed": 0,
        "bootstrap_refits_thresholds": True,
        "cal_oof_folds": 5,
        "eje1_preset": "1B_base_tech",
        "eje2_stratum": "near_ood_neighbor",
        "clause_caps": [None, 16, 24, 32],
        "n_cal_ladder": [1, 5, 10, 25, 50, 100, 200, 400, 600],
        "PORTS_8080_8088_CLOSED": True,
        "output_dir": "/tmp/fhv1_1_id_v4",
    }


def _write_minimal_bundle(root: Path, *, dual_f1: float = 0.7022222222222222) -> None:
    (root / "manifest.json").write_text(json.dumps(_manifest()), encoding="utf-8")
    (root / "python__full_only__dual_axis_v4.json").write_text(
        json.dumps(_dual_axis_cell(dual_f1)), encoding="utf-8"
    )
    (root / "python__clause_cap_eval.json").write_text(
        json.dumps(
            {
                "domain": "python",
                "w_f": 0.35,
                "recipe": _recipe(name="eje1_only|b=0.00|l=-|n=-|w=-", family="eje1_only", beta=0.0),
                "caps": [
                    {
                        "clause_cap": None,
                        "mean_selected_clauses": 4.3925,
                        "cal_only_p10": _metric(0.7125506072874493),
                        "f1": 0.7125506072874493,
                        "far": 0.19666666666666666,
                        "frr": 0.12,
                        "subtype_far": {
                            "dilution_80_20": 0.0,
                            "smuggle_recipe_footnote": None,
                            "long_context_flooding": 0.0,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "python__n_cal_volume_curve.json").write_text(
        json.dumps(
            {
                "domain": "python",
                "description_only": {
                    "kind": "description_only",
                    "domain": "python",
                    "n_cal": 1,
                    "std_t_fallback": "std_pool=std_C",
                    "threshold_relative_1b": 0.6353441865160234,
                    "roc_auc": 0.8234,
                    "pr_auc_in_domain": 0.6,
                    "pr_auc_reject": 0.9,
                    "f1": 0.0,
                    "frr": 1.0,
                    "far": 0.0,
                    "ood_far": 0.0,
                    "adv_far": 0.0,
                    "near_ood_far": 0.0,
                    "sep_ge_1_count": 451,
                    "oracle_upper_bound": {
                        "tag": "[ORACLE_UPPER_BOUND]",
                        "f1": 0.5,
                        "frr": 0.5,
                        "far": 0.5,
                        "threshold": 0.5,
                    },
                    "eje1_preset": "1B_base_tech",
                },
                "ladder": [
                    {
                        "n_cal": 1,
                        "n_seeds": 5,
                        "mean": {
                            "p05_f1": 0.0,
                            "p10_f1": 0.0,
                            "frr": 1.0,
                            "far": 0.0,
                            "roc_auc": 0.77456,
                            "ood_far": 0.0,
                            "adv_far": 0.0,
                            "near_ood_far": 0.0,
                            "threshold_p10": 0.65,
                            "sep_ge_1_count": 493.4,
                        },
                        "std": {
                            "p05_f1": 0.0,
                            "p10_f1": 0.0,
                            "frr": 0.0,
                            "far": 0.0,
                            "roc_auc": 0.05,
                            "ood_far": 0.0,
                            "adv_far": 0.0,
                            "near_ood_far": 0.0,
                            "threshold_p10": 0.01,
                            "sep_ge_1_count": 1.0,
                        },
                        "threshold_stability_std": 0.01,
                        "seeds": [0, 1, 2, 3, 4],
                    },
                    {
                        "n_cal": 600,
                        "n_seeds": 1,
                        "mean": {
                            "p05_f1": 0.65,
                            "p10_f1": 0.6810344827586207,
                            "frr": 0.21,
                            "far": 0.17666666666666667,
                            "roc_auc": 0.8993666666666668,
                            "ood_far": 0.0,
                            "adv_far": 0.24,
                            "near_ood_far": 0.5,
                            "threshold_p10": 0.5288744098263051,
                            "sep_ge_1_count": 23.0,
                        },
                        "std": {
                            "p05_f1": 0.0,
                            "p10_f1": 0.0,
                            "frr": 0.0,
                            "far": 0.0,
                            "roc_auc": 0.0,
                            "ood_far": 0.0,
                            "adv_far": 0.0,
                            "near_ood_far": 0.0,
                            "threshold_p10": 0.0,
                            "sep_ge_1_count": 0.0,
                        },
                        "threshold_stability_std": 0.0,
                        "seeds": [],
                    },
                ],
                "ladder_seed_rows": [],
                "marginal_deltas": [
                    {
                        "from_n": 400,
                        "to_n": 600,
                        "delta_f1": -0.0038524488883313612,
                        "delta_auc": 0.00039333333333335663,
                        "delta_frr": 0.011999999999999983,
                        "delta_far": -0.003333333333333327,
                    }
                ],
                "n_cal_ladder": [1, 600],
                "n_cal_seeds": [0, 1, 2, 3, 4],
                "holdout_n": 400,
                "eje1_preset": "1B_base_tech",
                "holdout_scoring": "full_doc_chunk0",
            }
        ),
        encoding="utf-8",
    )
    (root / "flooding_latency_v4.json").write_text(
        json.dumps(
            {
                "domains": {
                    "python": {
                        "uncapped": {
                            "n_texts": 6,
                            "repeats": 3,
                            "p50_ms": 1553.8348339905497,
                            "p99_ms": 1579.556607833365,
                            "samples_ms": [1.0, 2.0, 3.0],
                        },
                        "cap_16": {
                            "n_texts": 96,
                            "repeats": 3,
                            "p50_ms": 723.8832500006538,
                            "p99_ms": 736.2045450130245,
                            "samples_ms": [1.0, 2.0, 3.0],
                        },
                    }
                },
                "ports_closed_after": True,
                "PORTS_8080_8088_CLOSED": True,
            }
        ),
        encoding="utf-8",
    )
    (root / "description_only__python__embedding.json").write_text(
        json.dumps(
            {
                "domain": "python",
                "normalize": True,
                "dim": 1024,
                "vector": [0.0] * 8,
                "text": "fixture description",
            }
        ),
        encoding="utf-8",
    )


class ReportGeneratorV4Test(unittest.TestCase):
    def test_relation_direction_left_versus_right(self) -> None:
        self.assertEqual(report.relation("0.5", "0.7"), "below")
        self.assertEqual(report.relation("0.7", "0.5"), "above")
        self.assertEqual(report.relation("0.5", "0.5"), "equal")
        self.assertEqual(report.link("0.5", "0.7"), "below")
        self.assertEqual(report.link("0.7", "0.5"), "above")
        self.assertEqual(report.link("0.5", "0.5"), "tied with")

    def test_paired_prose_uses_subject_then_reference(self) -> None:
        # Paired F1 0.5 is below headline 0.7 — not "above".
        line = report.paired_vs_headline_line(
            paired_name="eje1_only|b=0.00|l=-|n=-|w=-",
            paired_f1="0.5",
            headline_f1="0.7",
        )
        self.assertIn("`0.5`", line)
        self.assertIn("below the headline", line)
        self.assertNotIn("above the headline", line)
        inverted = report.paired_vs_headline_line(
            paired_name="row",
            paired_f1="0.9",
            headline_f1="0.7",
        )
        self.assertIn("above the headline", inverted)

    def test_canary_table_includes_kind_and_f1_versus_frr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_bundle(root)
            bundle = report.load_directory(root)
            text = report.render_report(
                bundle,
                phase0_quote="## 1. Phase-0\nDIFF_IDENTICAL=0\n19,229,584\n3,145,728\nPASSED=173",
                disk_before="disk before fixture",
                disk_after="disk after fixture",
                v3_baseline=None,
            )
        section = report.section_text(text, "## 6. Master tables", "## 7. Verdict")
        self.assertIn("`kind`", section)
        self.assertIn("`sqlite3`", section)
        self.assertIn("`f1`", section)
        self.assertIn("`frr`", section)
        self.assertIn("F1", section)
        self.assertIn("FRR", section)
        self.assertIn("`0.6666666666666666`", section)

    def test_fixture_f1_copied_verbatim_and_missing_key_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_bundle(root)
            bundle = report.load_directory(root)
            text = report.render_report(
                bundle,
                phase0_quote="## 1. Phase-0\nDIFF_IDENTICAL=0\n19,229,584\n3,145,728\nPASSED=173",
                disk_before="disk before fixture",
                disk_after="disk after fixture",
                v3_baseline=None,
            )
        self.assertIn(f"`{FIXTURE_F1}`", text)
        report.assert_executive_f1(text, bundle)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_bundle(root)
            broken = _dual_axis_cell()
            del broken["frozen"]
            (root / "python__full_only__dual_axis_v4.json").write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(KeyError):
                report.load_directory(root)


if __name__ == "__main__":
    unittest.main()
