#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""The report generator copies stored JSON literals and refuses a missing key."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import fhv1_1_id_v3_report as report


FIXTURE_F1 = "0.123456789012345"


def _metric(f1: float) -> dict[str, float]:
    return {
        "tp": 1,
        "fn": 1,
        "tn": 1,
        "fp": 1,
        "precision": f1,
        "recall": f1,
        "f1": f1,
        "frr": 0.25,
        "far": 0.5,
        "threshold": 0.4,
        "roc_auc": 0.9,
    }


def _recipe() -> dict[str, object]:
    return {
        "name": "dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-",
        "family": "dir1024_sig_sep",
        "coupling": "identity",
        "alpha": 0.0,
        "guard": None,
        "struct_hook": "beta",
        "beta": 0.0,
        "gamma": None,
        "struct_reduction": "full_doc",
        "w_f": None,
    }


def _primary_row(f1: float) -> dict[str, object]:
    block = _metric(f1)
    return {
        "recipe": _recipe(),
        "cal_only": {"p05": dict(block), "p10": dict(block), "p15": dict(block)},
        "repeated_oof_5x5": {
            "seeds": [0],
            "f1": {"mean": f1, "std": 0.01},
            "frr": {"mean": 0.25, "std": 0.0},
            "far": {"mean": 0.5, "std": 0.0},
            "roc_auc": {"mean": 0.9, "std": 0.0},
            "per_seed": [{"seed": 0, "f1": f1, "frr": 0.25, "far": 0.5, "roc_auc": 0.9}],
        },
        "bootstrap_95ci": {
            "f1": {"low": 0.1, "high": 0.2},
            "frr": {"low": 0.2, "high": 0.3},
            "far": {"low": 0.4, "high": 0.6},
            "roc_auc": {"low": 0.8, "high": 0.95},
            "delta_f1": {
                "task012_f1": {"point_bootstrap_mean_minus_frozen": 0.01, "ci95": {"low": 0.0, "high": 0.02}},
                "task013_cal_p10_f1": {"point_bootstrap_mean_minus_frozen": 0.01, "ci95": {"low": 0.0, "high": 0.02}},
                "task013_repeated_f1": {"point_bootstrap_mean_minus_frozen": 0.01, "ci95": {"low": 0.0, "high": 0.02}},
            },
        },
    }


def _cell(f1: float = 0.123456789012345) -> dict[str, object]:
    recipe = _recipe()
    metric = _metric(f1)
    repeated = _primary_row(f1)["repeated_oof_5x5"]
    return {
        "mode": "v3",
        "domain": "python",
        "granularity": "full_only",
        "preset": "1B_base_tech",
        "n_prompts": 4,
        "n_calibration_bundles": 6,
        "dtype": "float64",
        "normalize": True,
        "directional_tie_and_anchors": {
            "full_doc": {"sep_ge_1": 1, "sep_ge_1_and_sign_flip": 0, "polarity_dials": 2, "tie_count": 0},
            "clause_opt2c": {"sep_ge_1": 0, "sep_ge_1_and_sign_flip": 0, "polarity_dials": 1, "tie_count": 0},
        },
        "headline": {
            "label": "nested_modal_recipe_cal_only_p10",
            "recipe": recipe["name"],
            "f1": f1,
            "frr": 0.25,
            "far": 0.5,
        },
        "primary": {
            "rule": "document_level_CAL_ONLY",
            "holdout_labels_in_threshold": False,
            "nested_selected": {
                "selection": "modal fold wins",
                "recipe": recipe,
                "wins": 3,
                "cal_only": {"p05": dict(metric), "p10": dict(metric), "p15": dict(metric)},
            },
            "dir1024_alpha0_beta0": [_primary_row(f1)],
            "baselines_alpha0_beta0": [_primary_row(0.11)],
        },
        "secondary_repeated_oof_5x5": {
            "nested_mixed": repeated,
            "modal_recipe_fixed": repeated,
        },
        "bootstrap": {
            "n_resamples": 1000,
            "seed": 0,
            "refits_thresholds": True,
            "threshold_policy": "resampled_calibration_percentile",
            "probability": 0.1,
            "frozen_f1": {
                "task012_f1": 0.5606,
                "task013_cal_p10_f1": 0.2,
                "task013_repeated_f1": 0.19,
            },
            "nested_selected": _primary_row(f1)["bootstrap_95ci"],
        },
        "oracle_upper_bound": [
            {
                "source": "seed0_mixed_scores_fit_on_all_holdout_labels",
                "tag": "[ORACLE_UPPER_BOUND]",
                "f1": 0.99,
                "frr": 0.0,
                "far": 0.0,
                "threshold": 0.3,
            }
        ],
        "grid_cal_only": [
            {
                "recipe": recipe,
                "roc_auc": 0.9,
                "p05": dict(metric),
                "p10": dict(metric),
                "p15": dict(metric),
            }
        ],
        "quadrants": {
            "IN_DOMAIN_VALID": {"n": 1, "kind": "frr", "error_rate": 0.25},
            "OUT_OF_DOMAIN_BENIGN": {"n": 1, "kind": "far", "error_rate": 0.0},
            "HYBRID_BOUNDARY": {"n": 1, "kind": "far", "error_rate": 0.5},
            "ADVERSARIAL_FUZZING": {"n": 1, "kind": "far", "error_rate": 0.5},
        },
        "subtypes": [
            {"subtype": "near_ood_neighbor", "category": "HYBRID_BOUNDARY", "n": 1, "kind": "far", "error_rate": 0.5},
            {"subtype": "dilution_80_20", "category": "HYBRID_BOUNDARY", "n": 1, "kind": "far", "error_rate": 0.5},
        ],
        "canary_sqlite_subprocess_json": {
            "pattern": "marker",
            "n_marker": 2,
            "n_marker_in_domain_valid": 1,
            "token_hit_counts": {"sqlite3": 1, "subprocess": 0, "json": 1},
            "in_domain_valid_marker": {"n": 1, "kind": "frr", "error_rate": 0.0},
            "all_marker": {"n": 2, "kind": "f1", "error_rate": 0.5},
        },
        "struct_firing": {
            "rows": [
                {
                    "subtype": "near_ood_neighbor",
                    "category": "HYBRID_BOUNDARY",
                    "n": 1,
                    "full_doc": {"mean": 0.5, "n_below_1": 1, "feature_counts": {"punct_ratio": 1}},
                    "min_full_clause": {"mean": 0.4, "n_below_1": 1, "feature_counts": {"punct_ratio": 1}},
                }
            ]
        },
        "struct_latency_us": {
            "definition": "microseconds per score() call on holdout strings",
            "p50_us": 19.125,
            "p99_us": 194.5,
            "full_doc": {"n": 4, "p50_us": 20.0, "p99_us": 30.0},
            "clause_opt2c": {"n": 0, "p50_us": None, "p99_us": None},
        },
        "w_f_effect": [
            {
                "family": "dir1024_sig_sep",
                "w_f": None,
                "alpha": 0.0,
                "beta": 0.0,
                "threshold_p10": 0.4,
                "in_domain_valid": {"n": 1, "kind": "frr", "error_rate": 0.25},
                "smuggle_recipe_footnote": {"n": 0, "kind": None, "error_rate": None},
                "dilution_80_20": {"n": 1, "kind": "far", "error_rate": 0.5},
            }
        ],
        "composition": {"bootstrap_refits_thresholds": True},
    }


def _manifest(f1: float = 0.123456789012345) -> dict[str, object]:
    return {
        "mode": "v3",
        "dtype": "float64",
        "dim": 1024,
        "normalize": True,
        "n_cells": 1,
        "cells": [
            {
                "file": "python__full_only__1B_base_tech.json",
                "domain": "python",
                "granularity": "full_only",
                "preset": "1B_base_tech",
                "headline_label": "nested_modal_recipe_cal_only_p10",
                "headline_recipe": _recipe()["name"],
                "cal_only_p10_f1": f1,
            }
        ],
        "bootstrap_resamples": 1000,
        "bootstrap_seed": 0,
        "bootstrap_refits_thresholds": True,
        "primary": "document_level_CAL_ONLY",
    }


class ReportGeneratorTest(unittest.TestCase):
    def test_fixture_field_is_copied_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = _cell()
            (root / "manifest.json").write_text(json.dumps(_manifest()), encoding="utf-8")
            (root / "python__full_only__1B_base_tech.json").write_text(json.dumps(payload), encoding="utf-8")
            manifest, cells, tokens = report.load_directory(root)
            text = report.render_report(
                manifest,
                cells,
                phase0_quote="phase-0 quote fixture",
                disk_before="disk before fixture",
                disk_after="disk after fixture",
            )
        self.assertIn(FIXTURE_F1, json.dumps(payload))
        self.assertIn(f"`{FIXTURE_F1}`", text)
        report.assert_executive_f1(text, manifest)
        report.assert_section0_numbers(text, tokens)
        section0 = report.section_text(text, "## 0. Executive", "## 1. Phase-0 and disk")
        self.assertNotIn("[ORACLE_UPPER_BOUND]", section0)
        self.assertIn("`true`", section0)
        self.assertIn("bootstrap.refits_thresholds", section0)

    def test_missing_required_key_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            broken = _cell()
            del broken["headline"]
            (root / "manifest.json").write_text(json.dumps(_manifest()), encoding="utf-8")
            (root / "python__full_only__1B_base_tech.json").write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(KeyError):
                report.load_directory(root)


if __name__ == "__main__":
    unittest.main()
