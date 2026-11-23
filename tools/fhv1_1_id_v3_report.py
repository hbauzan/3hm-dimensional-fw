#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Write the v3 report from replay JSON. Missing keys abort. Numbers are copied literals."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

FLOOR_KIB = 3_145_728
PHASE0_NEEDLES = (
    "12,074,392",
    "12,074,264",
    "3,145,728",
    "DIFF_IDENTICAL=0",
    "103/103",
    "PASSED=173",
)
QUADRANTS = (
    "IN_DOMAIN_VALID",
    "OUT_OF_DOMAIN_BENIGN",
    "HYBRID_BOUNDARY",
    "ADVERSARIAL_FUZZING",
)
FOCUS_SUBTYPES = (
    "extreme_short_punct",
    "homoglyph_zwsp_fullwidth",
    "near_ood_neighbor",
    "panaderia_fermentacion",
    "diagnostico_pasteleria_panaderia",
    "long_debugging_walkthrough",
    "smuggle_recipe_footnote",
    "dilution_80_20",
)
PRESETS = ("1B_base_tech", "1B_base_tech_noise", "1B_full", "1B_full_v3")
METRIC_KEYS = ("tp", "fn", "tn", "fp", "precision", "recall", "f1", "frr", "far", "threshold", "roc_auc")
COUNT_WORDS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
)
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
SCRATCH = Path("/tmp/fhv1_1_id_v3")


def need(obj: Any, *path: str) -> Any:
    current = obj
    walked: list[str] = []
    for key in path:
        walked.append(key)
        if not isinstance(current, dict) or key not in current:
            raise KeyError("missing " + ".".join(walked))
        current = current[key]
    return current


def number_tokens(raw: str) -> set[str]:
    return {match.group(0) for match in NUMBER_RE.finditer(raw)}


def relation(left: str, right: str) -> str:
    a = float(left)
    b = float(right)
    if a < b:
        return "below"
    if a > b:
        return "above"
    return "equal"


def link(left: str, right: str) -> str:
    rel = relation(left, right)
    if rel == "equal":
        return "tied with"
    return rel


def same_w(left: Any, right: Any) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return float(left) == float(right)


def tick(value: Any) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return "`true`" if value else "`false`"
    if isinstance(value, str):
        return f"`{value}`"
    raise TypeError(f"expected a stored literal, got {type(value).__name__}")


def count_word(count: int) -> str:
    if 0 <= count < len(COUNT_WORDS):
        return COUNT_WORDS[count]
    return str(count)


def copy_metric(block: dict[str, Any]) -> dict[str, str]:
    return {key: need(block, key) for key in METRIC_KEYS}


def copy_pair(block: dict[str, Any], key: str) -> dict[str, str]:
    pair = need(block, key)
    return {"mean": need(pair, "mean"), "std": need(pair, "std")}


def copy_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": need(recipe, "name"),
        "family": need(recipe, "family"),
        "coupling": need(recipe, "coupling"),
        "alpha": need(recipe, "alpha"),
        "guard": need(recipe, "guard"),
        "struct_hook": need(recipe, "struct_hook"),
        "beta": need(recipe, "beta"),
        "gamma": need(recipe, "gamma"),
        "struct_reduction": need(recipe, "struct_reduction"),
        "w_f": need(recipe, "w_f"),
    }


def copy_error(block: dict[str, Any]) -> dict[str, Any]:
    return {"n": need(block, "n"), "kind": need(block, "kind"), "error_rate": need(block, "error_rate")}


def copy_repeated(block: dict[str, Any]) -> dict[str, Any]:
    per_seed = []
    for row in need(block, "per_seed"):
        per_seed.append(
            {
                "seed": need(row, "seed"),
                "f1": need(row, "f1"),
                "frr": need(row, "frr"),
                "far": need(row, "far"),
                "roc_auc": need(row, "roc_auc"),
            }
        )
    return {
        "f1": copy_pair(block, "f1"),
        "frr": copy_pair(block, "frr"),
        "far": copy_pair(block, "far"),
        "roc_auc": copy_pair(block, "roc_auc"),
        "per_seed": per_seed,
    }


def copy_bootstrap_method(block: dict[str, Any]) -> dict[str, Any]:
    delta = need(block, "delta_f1")
    copied_delta = {}
    for key in ("task012_f1", "task013_cal_p10_f1", "task013_repeated_f1"):
        item = need(delta, key)
        ci = need(item, "ci95")
        copied_delta[key] = {
            "point": need(item, "point_bootstrap_mean_minus_frozen"),
            "low": need(ci, "low"),
            "high": need(ci, "high"),
        }
    return {
        "f1": {"low": need(block, "f1", "low"), "high": need(block, "f1", "high")},
        "frr": {"low": need(block, "frr", "low"), "high": need(block, "frr", "high")},
        "far": {"low": need(block, "far", "low"), "high": need(block, "far", "high")},
        "roc_auc": {"low": need(block, "roc_auc", "low"), "high": need(block, "roc_auc", "high")},
        "delta_f1": copied_delta,
    }


def copy_primary_row(row: dict[str, Any]) -> dict[str, Any]:
    recipe = copy_recipe(need(row, "recipe"))
    return {
        "recipe": recipe,
        "p10": copy_metric(need(row, "cal_only", "p10")),
        "oof": copy_repeated(need(row, "repeated_oof_5x5")),
        "bootstrap": copy_bootstrap_method(need(row, "bootstrap_95ci")),
    }


def _better(current: dict[str, str] | None, name: str, f1: str) -> dict[str, str]:
    if current is None or float(f1) > float(current["f1"]):
        return {"name": name, "f1": f1}
    return current


def ablation(grid: list[Any], recipe: dict[str, Any], frozen_f1: str) -> dict[str, Any]:
    if not grid:
        raise KeyError("missing grid_cal_only rows")
    family = recipe["family"]
    w_f = recipe["w_f"]
    reduction = recipe["struct_reduction"]
    best_guard = None
    best_struct = None
    best_any = None
    below = 0
    for row in grid:
        rec = copy_recipe(need(row, "recipe"))
        f1 = need(row, "p10", "f1")
        if float(f1) < float(frozen_f1):
            below += 1
        best_any = _better(best_any, rec["name"], f1)
        if rec["family"] != family or not same_w(rec["w_f"], w_f) or rec["struct_reduction"] != reduction:
            continue
        guard_only = (
            rec["coupling"] in ("additive", "multiplicative")
            and float(rec["alpha"]) > 0.0
            and float(rec["beta"]) == 0.0
            and rec["gamma"] is None
        )
        struct_only = (
            rec["coupling"] == "identity"
            and rec["guard"] is None
            and float(rec["alpha"]) == 0.0
            and (float(rec["beta"]) > 0.0 or rec["gamma"] is not None)
        )
        if guard_only:
            best_guard = _better(best_guard, rec["name"], f1)
        if struct_only:
            best_struct = _better(best_struct, rec["name"], f1)
    return {
        "n_grid": len(grid),
        "n_below_frozen_cal": below,
        "grid_max": best_any,
        "paired_guard": best_guard,
        "paired_struct": best_struct,
    }


def slim_cell(data: dict[str, Any]) -> dict[str, Any]:
    headline = need(data, "headline")
    nested = need(data, "primary", "nested_selected")
    recipe = copy_recipe(need(nested, "recipe"))
    frozen = {
        "task012_f1": need(data, "bootstrap", "frozen_f1", "task012_f1"),
        "task013_cal_p10_f1": need(data, "bootstrap", "frozen_f1", "task013_cal_p10_f1"),
        "task013_repeated_f1": need(data, "bootstrap", "frozen_f1", "task013_repeated_f1"),
    }
    if need(headline, "f1") != need(nested, "cal_only", "p10", "f1"):
        raise KeyError("headline.f1 differs from nested cal_only p10 f1")
    if need(headline, "recipe") != recipe["name"]:
        raise KeyError("headline.recipe differs from nested recipe name")
    quadrants = {name: copy_error(need(data, "quadrants", name)) for name in QUADRANTS}
    subtypes = []
    for row in need(data, "subtypes"):
        subtypes.append(
            {
                "subtype": need(row, "subtype"),
                "category": need(row, "category"),
                "n": need(row, "n"),
                "kind": need(row, "kind"),
                "error_rate": need(row, "error_rate"),
            }
        )
    firing = []
    for row in need(data, "struct_firing", "rows"):
        levels = {}
        for level in ("full_doc", "min_full_clause"):
            block = need(row, level)
            levels[level] = {
                "mean": need(block, "mean"),
                "n_below_1": need(block, "n_below_1"),
                "feature_counts": dict(need(block, "feature_counts")),
            }
        firing.append(
            {
                "subtype": need(row, "subtype"),
                "category": need(row, "category"),
                "n": need(row, "n"),
                **levels,
            }
        )
    w_effect = []
    for row in need(data, "w_f_effect"):
        w_effect.append(
            {
                "family": need(row, "family"),
                "w_f": need(row, "w_f"),
                "alpha": need(row, "alpha"),
                "beta": need(row, "beta"),
                "threshold_p10": need(row, "threshold_p10"),
                "in_domain_valid": copy_error(need(row, "in_domain_valid")),
                "smuggle_recipe_footnote": copy_error(need(row, "smuggle_recipe_footnote")),
                "dilution_80_20": copy_error(need(row, "dilution_80_20")),
            }
        )
    oracles = []
    for row in need(data, "oracle_upper_bound"):
        tag = need(row, "tag")
        if tag != "[ORACLE_UPPER_BOUND]":
            raise KeyError("oracle row tag is not [ORACLE_UPPER_BOUND]")
        oracles.append(
            {
                "source": need(row, "source"),
                "tag": tag,
                "f1": need(row, "f1"),
                "frr": need(row, "frr"),
                "far": need(row, "far"),
                "threshold": need(row, "threshold"),
            }
        )
    if not oracles:
        raise KeyError("missing oracle_upper_bound rows")
    anchors = {}
    for level in ("full_doc", "clause_opt2c"):
        block = need(data, "directional_tie_and_anchors", level)
        anchors[level] = {
            "sep_ge_1": need(block, "sep_ge_1"),
            "sep_ge_1_and_sign_flip": need(block, "sep_ge_1_and_sign_flip"),
            "polarity_dials": need(block, "polarity_dials"),
            "tie_count": need(block, "tie_count"),
        }
    latency = need(data, "struct_latency_us")
    refits = need(data, "bootstrap", "refits_thresholds")
    composition_refits = need(data, "composition", "bootstrap_refits_thresholds")
    if not isinstance(refits, bool) or refits is not composition_refits:
        raise KeyError("bootstrap.refits_thresholds disagrees with composition.bootstrap_refits_thresholds")
    canary = need(data, "canary_sqlite_subprocess_json")
    tokens = need(canary, "token_hit_counts")
    return {
        "domain": need(data, "domain"),
        "granularity": need(data, "granularity"),
        "preset": need(data, "preset"),
        "n_prompts": need(data, "n_prompts"),
        "n_calibration_bundles": need(data, "n_calibration_bundles"),
        "dtype": need(data, "dtype"),
        "normalize": need(data, "normalize"),
        "label": need(headline, "label"),
        "recipe_name": recipe["name"],
        "family": recipe["family"],
        "recipe": recipe,
        "f1": need(headline, "f1"),
        "frr": need(headline, "frr"),
        "far": need(headline, "far"),
        "wins": need(nested, "wins"),
        "selection": need(nested, "selection"),
        "holdout_labels_in_threshold": need(data, "primary", "holdout_labels_in_threshold"),
        "rule": need(data, "primary", "rule"),
        "cal": {
            "p05": copy_metric(need(nested, "cal_only", "p05")),
            "p10": copy_metric(need(nested, "cal_only", "p10")),
            "p15": copy_metric(need(nested, "cal_only", "p15")),
        },
        "nested_oof": copy_repeated(need(data, "secondary_repeated_oof_5x5", "nested_mixed")),
        "fixed_oof": copy_repeated(need(data, "secondary_repeated_oof_5x5", "modal_recipe_fixed")),
        "frozen": frozen,
        "boot": {
            "n_resamples": need(data, "bootstrap", "n_resamples"),
            "seed": need(data, "bootstrap", "seed"),
            "refits_thresholds": refits,
            "threshold_policy": need(data, "bootstrap", "threshold_policy"),
            "probability": need(data, "bootstrap", "probability"),
            "nested": copy_bootstrap_method(need(data, "bootstrap", "nested_selected")),
        },
        "quadrants": quadrants,
        "subtypes": subtypes,
        "canary": {
            "pattern": need(canary, "pattern"),
            "n_marker": need(canary, "n_marker"),
            "n_marker_in_domain_valid": need(canary, "n_marker_in_domain_valid"),
            "token_hit_counts": {
                "sqlite3": need(tokens, "sqlite3"),
                "subprocess": need(tokens, "subprocess"),
                "json": need(tokens, "json"),
            },
            "in_domain_valid_marker": copy_error(need(canary, "in_domain_valid_marker")),
            "all_marker": copy_error(need(canary, "all_marker")),
        },
        "firing": firing,
        "latency": {
            "definition": need(latency, "definition"),
            "p50_us": need(latency, "p50_us"),
            "p99_us": need(latency, "p99_us"),
            "full_doc": {
                "n": need(latency, "full_doc", "n"),
                "p50_us": need(latency, "full_doc", "p50_us"),
                "p99_us": need(latency, "full_doc", "p99_us"),
            },
            "clause_opt2c": {
                "n": need(latency, "clause_opt2c", "n"),
                "p50_us": need(latency, "clause_opt2c", "p50_us"),
                "p99_us": need(latency, "clause_opt2c", "p99_us"),
            },
        },
        "anchors": anchors,
        "primary_rows": [copy_primary_row(row) for row in need(data, "primary", "dir1024_alpha0_beta0")]
        + [copy_primary_row(row) for row in need(data, "primary", "baselines_alpha0_beta0")],
        "w_effect": w_effect,
        "ablation": ablation(need(data, "grid_cal_only"), recipe, frozen["task013_cal_p10_f1"]),
        "oracles": oracles,
    }


def load_json(path: Path) -> tuple[Any, set[str]]:
    raw = path.read_text(encoding="utf-8")
    tokens = number_tokens(raw)
    data = json.loads(raw, parse_float=str, parse_int=str)
    del raw
    return data, tokens


def load_directory(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], set[str]]:
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise KeyError("missing manifest.json")
    manifest_data, tokens = load_json(manifest_path)
    manifest = {
        "mode": need(manifest_data, "mode"),
        "dtype": need(manifest_data, "dtype"),
        "dim": need(manifest_data, "dim"),
        "normalize": need(manifest_data, "normalize"),
        "n_cells": need(manifest_data, "n_cells"),
        "bootstrap_resamples": need(manifest_data, "bootstrap_resamples"),
        "bootstrap_seed": need(manifest_data, "bootstrap_seed"),
        "bootstrap_refits_thresholds": need(manifest_data, "bootstrap_refits_thresholds"),
        "primary": need(manifest_data, "primary"),
        "cells": [],
    }
    if not isinstance(manifest["bootstrap_refits_thresholds"], bool):
        raise KeyError("manifest bootstrap_refits_thresholds is not a boolean")
    listed = need(manifest_data, "cells")
    if str(len(listed)) != str(manifest["n_cells"]) and int(manifest["n_cells"]) != len(listed):
        raise KeyError("manifest n_cells differs from cells length")
    cells: list[dict[str, Any]] = []
    for item in listed:
        entry = {
            "file": need(item, "file"),
            "domain": need(item, "domain"),
            "granularity": need(item, "granularity"),
            "preset": need(item, "preset"),
            "headline_label": need(item, "headline_label"),
            "headline_recipe": need(item, "headline_recipe"),
            "cal_only_p10_f1": need(item, "cal_only_p10_f1"),
        }
        manifest["cells"].append(entry)
        cell_path = path / entry["file"]
        data, cell_tokens = load_json(cell_path)
        tokens |= cell_tokens
        cell = slim_cell(data)
        del data
        if cell["domain"] != entry["domain"] or cell["granularity"] != entry["granularity"] or cell["preset"] != entry["preset"]:
            raise KeyError(f"{entry['file']} identity differs from the manifest")
        if cell["label"] != entry["headline_label"] or cell["recipe_name"] != entry["headline_recipe"]:
            raise KeyError(f"{entry['file']} headline differs from the manifest")
        if cell["f1"] != entry["cal_only_p10_f1"]:
            raise KeyError(f"{entry['file']} cal_only p10 f1 differs from the manifest")
        if cell["boot"]["refits_thresholds"] is not manifest["bootstrap_refits_thresholds"]:
            raise KeyError(f"{entry['file']} refits_thresholds differs from the manifest")
        cells.append(cell)
    return manifest, cells, tokens


def quote_phase0(roadmap_text: str) -> str:
    start = roadmap_text.find("## 1. Phase-0")
    end = roadmap_text.find("\n## 2. ")
    if start < 0 or end < 0:
        raise KeyError("roadmap section 1 is missing")
    quote = roadmap_text[start:end].strip()
    for needle in PHASE0_NEEDLES:
        if needle not in quote:
            raise KeyError(f"phase-0 quote missing {needle}")
    return quote


def section_text(text: str, start_heading: str, next_heading: str) -> str:
    start = text.index(start_heading)
    end = text.index(next_heading, start + len(start_heading))
    return text[start:end]


def assert_executive_f1(markdown: str, manifest: dict[str, Any]) -> None:
    section = section_text(markdown, "## 0. Executive", "## 1. Phase-0 and disk")
    for cell in manifest["cells"]:
        literal = cell["cal_only_p10_f1"]
        if f"`{literal}`" not in section:
            raise KeyError(f"executive table missing manifest f1 {literal}")


def assert_section0_numbers(markdown: str, tokens: set[str]) -> None:
    section = section_text(markdown, "## 0. Executive", "## 1. Phase-0 and disk")
    missing = []
    for token in re.findall(r"`([^`]+)`", section):
        if NUMBER_RE.fullmatch(token) and token not in tokens:
            missing.append(token)
    if missing:
        raise KeyError("executive number absent from JSON: " + ", ".join(missing[:8]))


def subtype_map(cell: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["subtype"]: row for row in cell["subtypes"]}


def find_cell(cells: list[dict[str, Any]], domain: str, granularity: str, preset: str) -> dict[str, Any] | None:
    for cell in cells:
        if cell["domain"] == domain and cell["granularity"] == granularity and cell["preset"] == preset:
            return cell
    return None


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def rate_cell(block: dict[str, Any]) -> str:
    if block["error_rate"] is None:
        return "`null`"
    return tick(block["error_rate"])


def executive_lines(manifest: dict[str, Any], cells: list[dict[str, Any]]) -> list[str]:
    labels = {cell["label"] for cell in cells}
    lines = [
        "Headline label on every cell is "
        + ", ".join(tick(label) for label in sorted(labels))
        + ". The manifest field is `nested_modal_recipe_cal_only_p10` when that is the stored label.",
        f"Primary rule `{manifest['primary']}`. `bootstrap.refits_thresholds` is {tick(manifest['bootstrap_refits_thresholds'])}. "
        f"Resamples {tick(manifest['bootstrap_resamples'])}, seed {tick(manifest['bootstrap_seed'])}, dim {tick(manifest['dim'])}.",
        "TASK-011 m0 F1 is the published column in `reports/fhv1_1_xray_and_replay_report.md`. It is not a field of this JSON, so the table does not repeat it. "
        "TASK-012 and TASK-013 F1 values below are the `bootstrap.frozen_f1` literals stored in each cell.",
        "Upper-bound rows that were fit on holdout labels are outside this table. They are not columns here.",
    ]
    rows = []
    for cell in cells:
        near = subtype_map(cell).get("near_ood_neighbor")
        near_far = tick(near["error_rate"]) if near is not None else "`absent`"
        rows.append(
            [
                tick(cell["domain"]),
                tick(cell["granularity"]),
                tick(cell["preset"]),
                tick(cell["family"]),
                tick(cell["f1"]),
                tick(cell["nested_oof"]["f1"]["mean"]),
                tick(cell["nested_oof"]["f1"]["std"]),
                tick(cell["cal"]["p10"]["roc_auc"]),
                tick(cell["quadrants"]["OUT_OF_DOMAIN_BENIGN"]["error_rate"]),
                tick(cell["quadrants"]["ADVERSARIAL_FUZZING"]["error_rate"]),
                tick(cell["quadrants"]["HYBRID_BOUNDARY"]["error_rate"]),
                near_far,
                tick(cell["latency"]["p50_us"]),
                tick(cell["latency"]["p99_us"]),
                tick(cell["frozen"]["task012_f1"]),
                tick(cell["frozen"]["task013_cal_p10_f1"]),
                tick(cell["frozen"]["task013_repeated_f1"]),
            ]
        )
    lines.append(
        md_table(
            [
                "domain",
                "granularity",
                "preset",
                "family",
                "CAL_ONLY p10 F1",
                "5x5 F1 mean",
                "5x5 F1 std",
                "ROC-AUC",
                "OOD FAR",
                "adversarial FAR",
                "hybrid FAR",
                "near-OOD FAR",
                "S_struct p50 us",
                "S_struct p99 us",
                "TASK-012 F1",
                "TASK-013 CAL_ONLY p10 F1",
                "TASK-013 5x5 F1",
            ],
            rows,
        )
    )
    lines.append("Stored headline recipes:")
    for cell in cells:
        lines.append(
            f"- {tick(cell['domain'])} {tick(cell['granularity'])} {tick(cell['preset'])} {tick(cell['recipe_name'])} "
            f"CAL_ONLY p10 F1 {tick(cell['f1'])} is {link(cell['f1'], cell['frozen']['task013_cal_p10_f1'])} "
            f"the frozen TASK-013 F_polarity CAL_ONLY p10 {tick(cell['frozen']['task013_cal_p10_f1'])}. "
            f"5x5 F1 {tick(cell['nested_oof']['f1']['mean'])} is {link(cell['nested_oof']['f1']['mean'], cell['frozen']['task013_repeated_f1'])} "
            f"the frozen TASK-013 5x5 F1 {tick(cell['frozen']['task013_repeated_f1'])}."
        )
    lines.extend(verdict_lines(cells))
    return lines


def verdict_lines(cells: list[dict[str, Any]]) -> list[str]:
    lines = ["What moved, using only stored literals:"]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for cell in cells:
        grouped.setdefault((cell["domain"], cell["granularity"]), []).append(cell)
    for (domain, granularity), group in grouped.items():
        for word, rel in (("above", "above"), ("equal", "equal"), ("below", "below")):
            picked = [cell for cell in group if relation(cell["f1"], cell["frozen"]["task013_cal_p10_f1"]) == rel]
            if not picked:
                continue
            presets = ", ".join(tick(cell["preset"]) for cell in picked)
            lines.append(
                f"{count_word(len(picked))} {domain}/{granularity} headline(s) {word} the frozen TASK-013 F_polarity CAL_ONLY p10: {presets}."
            )
    polarity = [
        cell
        for cell in cells
        if cell["domain"] == "receta" and cell["granularity"] == "full_only" and cell["family"] == "polarity_v2_subset"
    ]
    if polarity:
        presets = ", ".join(tick(cell["preset"]) for cell in polarity)
        lines.append(
            f"{count_word(len(polarity))} receta/full_only cell(s) selected `polarity_v2_subset` rather than a dir1024 family: {presets}."
        )
    else:
        lines.append("No receta/full_only cell selected `polarity_v2_subset`.")
    below_rows = []
    for cell in cells:
        if cell["domain"] != "python" or cell["granularity"] != "full_only":
            continue
        for row in cell["primary_rows"]:
            if row["recipe"]["family"] not in ("polarity_v2_subset", "base_repaired") and not str(row["recipe"]["family"]).startswith("dir1024_"):
                continue
            if relation(row["p10"]["f1"], cell["frozen"]["task013_cal_p10_f1"]) == "below":
                below_rows.append((cell, row))
    if below_rows:
        lines.append(
            f"{count_word(len(below_rows))} python/full_only alpha=0 rows are below the frozen TASK-013 F_polarity CAL_ONLY p10. "
            "That set includes `base_repaired` and, where the stored row is below, `polarity_v2_subset`. "
            "A nested headline that is above that frozen value stays above it; the alpha=0 row is a different stored score."
        )
        for cell, row in below_rows:
            if row["recipe"]["family"] in ("base_repaired", "polarity_v2_subset"):
                lines.append(
                    f"- {tick(cell['preset'])} {tick(row['recipe']['family'])} w_f {tick(row['recipe']['w_f'])} "
                    f"CAL_ONLY p10 F1 {tick(row['p10']['f1'])} is below {tick(cell['frozen']['task013_cal_p10_f1'])}."
                )
    dir_losses = [
        cell
        for cell in cells
        if cell["granularity"] == "full_only" and cell["domain"] == "receta" and not str(cell["family"]).startswith("dir1024_")
    ]
    if dir_losses:
        lines.append(
            "On those receta/full_only cells the nested selector did not pick a dir1024 family. "
            "The stored headline is the polarity subset score, so a dir1024 gain is not what this run selected."
        )
    return lines


def stratum_lines(cells: list[dict[str, Any]]) -> list[str]:
    lines = [
        "Preset definitions stay those in the roadmap: `1B_base_tech_noise` adds `structural_symbol_noise` to `1B_base_tech`, "
        "and `1B_full_v3` adds that stratum to `1B_full`. `1B_full` adds `near_ood_neighbor` and does not include the symbol stratum. "
        "The comparison is the nested CAL_ONLY p10 F1 of each stored cell.",
    ]
    domains = []
    for cell in cells:
        key = (cell["domain"], cell["granularity"])
        if key not in domains:
            domains.append(key)
    pairs = (
        ("1B_base_tech", "1B_base_tech_noise", "symbol stratum against base_tech"),
        ("1B_full", "1B_full_v3", "symbol stratum against 1B_full"),
        ("1B_base_tech", "1B_full", "near_ood_neighbor against base_tech"),
    )
    for domain, granularity in domains:
        lines.append(f"### {domain} / {granularity}")
        for left_name, right_name, title in pairs:
            left = find_cell(cells, domain, granularity, left_name)
            right = find_cell(cells, domain, granularity, right_name)
            if left is None or right is None:
                lines.append(f"- {title}: a preset file is absent.")
                continue
            rel = link(right["f1"], left["f1"])
            lines.append(
                f"- {title}: {tick(right_name)} F1 {tick(right['f1'])} ({tick(right['family'])}) is {rel} "
                f"{tick(left_name)} F1 {tick(left['f1'])} ({tick(left['family'])}). "
                f"OOD FAR {tick(right['quadrants']['OUT_OF_DOMAIN_BENIGN']['error_rate'])} versus {tick(left['quadrants']['OUT_OF_DOMAIN_BENIGN']['error_rate'])}. "
                f"Adversarial FAR {tick(right['quadrants']['ADVERSARIAL_FUZZING']['error_rate'])} versus {tick(left['quadrants']['ADVERSARIAL_FUZZING']['error_rate'])}. "
                f"Hybrid FAR {tick(right['quadrants']['HYBRID_BOUNDARY']['error_rate'])} versus {tick(left['quadrants']['HYBRID_BOUNDARY']['error_rate'])}."
            )
            near_l = subtype_map(left).get("near_ood_neighbor")
            near_r = subtype_map(right).get("near_ood_neighbor")
            if near_l is not None and near_r is not None:
                lines.append(
                    f"  near-OOD FAR {tick(near_r['error_rate'])} on {tick(right_name)} and {tick(near_l['error_rate'])} on {tick(left_name)}."
                )
    return lines


def directional_lines(cells: list[dict[str, Any]]) -> list[str]:
    lines = [
        "Rows here are the stored alpha=0, beta=0 reference scores (`primary.dir1024_alpha0_beta0` and `primary.baselines_alpha0_beta0`). "
        "They are not the nested headline unless the headline recipe is that same alpha=0 beta=0 name.",
    ]
    for cell in cells:
        lines.append(f"### {cell['domain']} / {cell['granularity']} / {cell['preset']}")
        lines.append(
            f"Nested family {tick(cell['family'])}, wins {tick(cell['wins'])}, recipe {tick(cell['recipe_name'])}, "
            f"CAL_ONLY p10 F1 {tick(cell['f1'])}."
        )
        for level, block in cell["anchors"].items():
            lines.append(
                f"- anchors {tick(level)}: sep_ge_1 {tick(block['sep_ge_1'])}, "
                f"sep_ge_1_and_sign_flip {tick(block['sep_ge_1_and_sign_flip'])}, "
                f"polarity_dials {tick(block['polarity_dials'])}, tie_count {tick(block['tie_count'])}."
            )
        rows = []
        for row in cell["primary_rows"]:
            recipe = row["recipe"]
            rows.append(
                [
                    tick(recipe["family"]),
                    tick(recipe["w_f"]),
                    tick(row["p10"]["f1"]),
                    tick(row["p10"]["frr"]),
                    tick(row["p10"]["far"]),
                    tick(row["p10"]["roc_auc"]),
                    tick(row["oof"]["f1"]["mean"]),
                    tick(row["oof"]["f1"]["std"]),
                    relation(row["p10"]["f1"], cell["frozen"]["task013_cal_p10_f1"]),
                ]
            )
        lines.append(
            md_table(
                ["family", "w_f", "CAL_ONLY p10 F1", "FRR", "FAR", "ROC-AUC", "5x5 F1 mean", "5x5 F1 std", "versus TASK-013 CAL p10"],
                rows,
            )
        )
    return lines


def guard_lines(cells: list[dict[str, Any]]) -> list[str]:
    lines = [
        "Guard-only keeps the headline family, w_f, and struct reduction, with alpha above zero, beta at zero, and gamma null. "
        "Struct-only keeps that same pairing with identity coupling, a null guard, alpha at zero, and either beta above zero or a gamma value. "
        "`[HOLDOUT_MAX_SCAN]` is the maximum stored CAL_ONLY p10 F1 in `grid_cal_only`. Choosing it uses holdout F1, so it is not the nested headline and it is not `[ORACLE_UPPER_BOUND]`.",
    ]
    for cell in cells:
        scan = cell["ablation"]["grid_max"]
        lines.append(f"### {cell['domain']} / {cell['granularity']} / {cell['preset']}")
        lines.append(
            f"Grid rows {cell['ablation']['n_grid']}. "
            f"Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: {cell['ablation']['n_below_frozen_cal']}. "
            f"Both counts are computed from the stored grid."
        )
        lines.append(f"- Headline {tick(cell['recipe_name'])} F1 {tick(cell['f1'])}.")
        identity = None
        for row in cell["primary_rows"]:
            if row["recipe"]["family"] == cell["family"] and same_w(row["recipe"]["w_f"], cell["recipe"]["w_f"]):
                identity = row
                break
        if identity is None:
            lines.append("- Paired alpha=0 beta=0 row for the headline family is absent.")
        else:
            lines.append(
                f"- Paired alpha=0 beta=0 {tick(identity['recipe']['name'])} F1 {tick(identity['p10']['f1'])} "
                f"is {link(cell['f1'], identity['p10']['f1'])} the headline when the headline is compared with this row."
            )
        for label, picked in (("guard-only", cell["ablation"]["paired_guard"]), ("struct-only", cell["ablation"]["paired_struct"])):
            if picked is None:
                lines.append(f"- Paired {label} row is absent.")
            else:
                lines.append(f"- Paired {label} {tick(picked['name'])} F1 {tick(picked['f1'])}.")
        if scan is not None:
            lines.append(f"- `[HOLDOUT_MAX_SCAN]` {tick(scan['name'])} F1 {tick(scan['f1'])}.")
        lines.append(
            f"S_struct latency ({cell['latency']['definition']}): combined p50 {tick(cell['latency']['p50_us'])} us, "
            f"p99 {tick(cell['latency']['p99_us'])} us. "
            f"full_doc n {tick(cell['latency']['full_doc']['n'])} p50 {tick(cell['latency']['full_doc']['p50_us'])} "
            f"p99 {tick(cell['latency']['full_doc']['p99_us'])}. "
            f"clause_opt2c n {tick(cell['latency']['clause_opt2c']['n'])} p50 {tick(cell['latency']['clause_opt2c']['p50_us'])} "
            f"p99 {tick(cell['latency']['clause_opt2c']['p99_us'])}."
        )
        lines.append("Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:")
        focus = set(FOCUS_SUBTYPES)
        shown = set()
        for row in cell["firing"]:
            in_domain_hit = row["category"] == "IN_DOMAIN_VALID" and str(row["full_doc"]["n_below_1"]) not in {"0", "0.0"}
            if row["subtype"] not in focus and not in_domain_hit:
                continue
            shown.add(row["subtype"])
            lines.append(
                f"- {tick(row['subtype'])} {tick(row['category'])} n {tick(row['n'])} "
                f"full_doc mean {tick(row['full_doc']['mean'])} n_below_1 {tick(row['full_doc']['n_below_1'])} "
                f"features { _feature_text(row['full_doc']['feature_counts']) }; "
                f"min_full_clause mean {tick(row['min_full_clause']['mean'])} n_below_1 {tick(row['min_full_clause']['n_below_1'])} "
                f"features { _feature_text(row['min_full_clause']['feature_counts']) }."
            )
        for name in FOCUS_SUBTYPES:
            if name not in shown and name not in {row["subtype"] for row in cell["firing"]}:
                lines.append(f"- {tick(name)} is absent from `struct_firing` on this cell.")
    return lines


def _feature_text(counts: dict[str, Any]) -> str:
    if not counts:
        return "`none`"
    parts = [f"{tick(name)} {tick(counts[name])}" for name in sorted(counts)]
    return ", ".join(parts)


def weight_lines(cells: list[dict[str, Any]]) -> list[str]:
    lines = [
        "Each row is a stored `w_f_effect` entry at alpha 0 and beta 0. "
        "`smuggle_recipe_footnote` and `dilution_80_20` rates are the stored error rates. "
        "A null rate means the subtype has n 0 in that block. The roadmap's earlier 80% and 74% figures are not rewritten here; the rates below are the v3 literals.",
    ]
    for cell in cells:
        lines.append(f"### {cell['domain']} / {cell['granularity']} / {cell['preset']}")
        rows = []
        for row in cell["w_effect"]:
            rows.append(
                [
                    tick(row["family"]),
                    tick(row["w_f"]),
                    tick(row["in_domain_valid"]["n"]),
                    rate_cell(row["in_domain_valid"]),
                    tick(row["smuggle_recipe_footnote"]["n"]),
                    rate_cell(row["smuggle_recipe_footnote"]),
                    tick(row["dilution_80_20"]["n"]),
                    rate_cell(row["dilution_80_20"]),
                ]
            )
        lines.append(
            md_table(
                ["family", "w_f", "in-domain n", "in-domain FRR", "smuggle n", "smuggle FAR", "dilution n", "dilution FAR"],
                rows,
            )
        )
    return lines


def master_lines(cells: list[dict[str, Any]]) -> list[str]:
    lines = [
        "Document-level CAL_ONLY uses the calibration percentile only. "
        f"The stored `holdout_labels_in_threshold` value is reported per cell. "
        "5x5 figures are `secondary_repeated_oof_5x5`. Bootstrap intervals are `bootstrap.nested_selected`.",
    ]
    for cell in cells:
        lines.append(f"### {cell['domain']} / {cell['granularity']} / {cell['preset']}")
        lines.append(
            f"n_prompts {tick(cell['n_prompts'])}, n_calibration_bundles {tick(cell['n_calibration_bundles'])}, "
            f"rule {tick(cell['rule'])}, holdout_labels_in_threshold {tick(cell['holdout_labels_in_threshold'])}, "
            f"selection {tick(cell['selection'])}."
        )
        cal_rows = []
        for tag in ("p05", "p10", "p15"):
            block = cell["cal"][tag]
            cal_rows.append(
                [
                    tick(tag),
                    tick(block["f1"]),
                    tick(block["frr"]),
                    tick(block["far"]),
                    tick(block["precision"]),
                    tick(block["recall"]),
                    tick(block["threshold"]),
                    tick(block["roc_auc"]),
                    tick(block["tp"]),
                    tick(block["fn"]),
                    tick(block["tn"]),
                    tick(block["fp"]),
                ]
            )
        lines.append("CAL_ONLY on the nested recipe:")
        lines.append(md_table(["tag", "F1", "FRR", "FAR", "precision", "recall", "threshold", "ROC-AUC", "tp", "fn", "tn", "fp"], cal_rows))
        for title, block in (("nested 5x5", cell["nested_oof"]), ("modal recipe fixed 5x5", cell["fixed_oof"])):
            lines.append(title + ":")
            stat_rows = []
            for metric in ("f1", "frr", "far", "roc_auc"):
                stat_rows.append([tick(metric), tick(block[metric]["mean"]), tick(block[metric]["std"])])
            lines.append(md_table(["metric", "mean", "std"], stat_rows))
            seed_rows = []
            for seed in block["per_seed"]:
                seed_rows.append(
                    [tick(seed["seed"]), tick(seed["f1"]), tick(seed["frr"]), tick(seed["far"]), tick(seed["roc_auc"])]
                )
            lines.append(md_table(["seed", "F1", "FRR", "FAR", "ROC-AUC"], seed_rows))
        boot = cell["boot"]
        lines.append(
            f"Bootstrap n {tick(boot['n_resamples'])}, seed {tick(boot['seed'])}, probability {tick(boot['probability'])}, "
            f"threshold_policy {tick(boot['threshold_policy'])}, refits_thresholds {tick(boot['refits_thresholds'])}."
        )
        nested = boot["nested"]
        ci_rows = []
        for metric in ("f1", "frr", "far", "roc_auc"):
            ci_rows.append([tick(metric), tick(nested[metric]["low"]), tick(nested[metric]["high"])])
        lines.append(md_table(["metric", "ci95 low", "ci95 high"], ci_rows))
        delta_rows = []
        for key, item in nested["delta_f1"].items():
            delta_rows.append([tick(key), tick(item["point"]), tick(item["low"]), tick(item["high"])])
        lines.append("Paired bootstrap delta of the nested score against the frozen F1 literals:")
        lines.append(md_table(["frozen key", "point", "ci95 low", "ci95 high"], delta_rows))
    lines.append("### 6.4 [ORACLE_UPPER_BOUND]")
    lines.append(
        "Every row in this subsection carries the stored tag `[ORACLE_UPPER_BOUND]`. "
        "These F1 values are not CAL_ONLY operating points and they are not the 5x5 means above."
    )
    for cell in cells:
        lines.append(f"#### {cell['domain']} / {cell['granularity']} / {cell['preset']}")
        rows = []
        for row in cell["oracles"]:
            rows.append(
                [tick(row["tag"]), tick(row["source"]), tick(row["f1"]), tick(row["frr"]), tick(row["far"]), tick(row["threshold"])]
            )
        lines.append(md_table(["tag", "source", "F1", "FRR", "FAR", "threshold"], rows))
    return lines


def subtype_lines(cells: list[dict[str, Any]]) -> list[str]:
    lines = [
        "Focus subtypes first. A name that the benchmark file does not contain on that cell is `absent`. "
        "The full stored subtype list follows.",
    ]
    focus_rows = []
    for cell in cells:
        present = subtype_map(cell)
        for name in FOCUS_SUBTYPES:
            row = present.get(name)
            if row is None:
                focus_rows.append(
                    [tick(cell["domain"]), tick(cell["granularity"]), tick(cell["preset"]), tick(name), "`absent`", "`absent`", "`absent`", "`absent`"]
                )
            else:
                focus_rows.append(
                    [
                        tick(cell["domain"]),
                        tick(cell["granularity"]),
                        tick(cell["preset"]),
                        tick(name),
                        tick(row["category"]),
                        tick(row["n"]),
                        tick(row["kind"]),
                        tick(row["error_rate"]),
                    ]
                )
    lines.append(md_table(["domain", "granularity", "preset", "subtype", "category", "n", "kind", "error_rate"], focus_rows))
    lines.append("Full subtype breakdown:")
    full_rows = []
    for cell in cells:
        for row in cell["subtypes"]:
            full_rows.append(
                [
                    tick(cell["domain"]),
                    tick(cell["granularity"]),
                    tick(cell["preset"]),
                    tick(row["subtype"]),
                    tick(row["category"]),
                    tick(row["n"]),
                    tick(row["kind"]),
                    tick(row["error_rate"]) if row["error_rate"] is not None else "`null`",
                ]
            )
    lines.append(md_table(["domain", "granularity", "preset", "subtype", "category", "n", "kind", "error_rate"], full_rows))
    return lines


def canary_lines(cells: list[dict[str, Any]]) -> list[str]:
    lines = [
        "Marker counts are the stored `canary_sqlite_subprocess_json` object on the nested p10 decision. "
        "Token hit counts can exceed `n_marker` when one text contains more than one of the three tokens.",
    ]
    rows = []
    for cell in cells:
        canary = cell["canary"]
        rows.append(
            [
                tick(cell["domain"]),
                tick(cell["granularity"]),
                tick(cell["preset"]),
                tick(canary["n_marker"]),
                tick(canary["n_marker_in_domain_valid"]),
                tick(canary["token_hit_counts"]["sqlite3"]),
                tick(canary["token_hit_counts"]["subprocess"]),
                tick(canary["token_hit_counts"]["json"]),
                tick(canary["in_domain_valid_marker"]["n"]),
                rate_cell(canary["in_domain_valid_marker"]),
                tick(canary["all_marker"]["n"]),
                rate_cell(canary["all_marker"]),
            ]
        )
    lines.append(
        md_table(
            [
                "domain",
                "granularity",
                "preset",
                "n_marker",
                "n in-domain",
                "sqlite3",
                "subprocess",
                "json",
                "in-domain n",
                "in-domain error",
                "all n",
                "all error",
            ],
            rows,
        )
    )
    return lines


def closed_open_lines(cells: list[dict[str, Any]], manifest: dict[str, Any]) -> list[str]:
    lines = [
        "Closed measurements:",
        f"- `bootstrap.refits_thresholds` is {tick(manifest['bootstrap_refits_thresholds'])} on the manifest and on every cell.",
        f"- Primary statistic `{manifest['primary']}`. Nested selection text is stored per cell in section 6.",
        "- `[ORACLE_UPPER_BOUND]` stays in section 6.4. `[HOLDOUT_MAX_SCAN]` stays in section 4. Neither is the executive F1.",
    ]
    below = [cell for cell in cells if relation(cell["f1"], cell["frozen"]["task013_cal_p10_f1"]) == "below"]
    equal = [cell for cell in cells if relation(cell["f1"], cell["frozen"]["task013_cal_p10_f1"]) == "equal"]
    above = [cell for cell in cells if relation(cell["f1"], cell["frozen"]["task013_cal_p10_f1"]) == "above"]
    lines.append(
        f"- {count_word(len(above))} headlines are above the frozen TASK-013 CAL_ONLY p10, "
        f"{count_word(len(equal))} are equal, and {count_word(len(below))} are below."
    )
    lines.append("Open, and not restated as a gain:")
    if below or equal:
        for cell in below + equal:
            lines.append(
                f"- {tick(cell['domain'])}/{tick(cell['granularity'])}/{tick(cell['preset'])} family {tick(cell['family'])} "
                f"F1 {tick(cell['f1'])} is {link(cell['f1'], cell['frozen']['task013_cal_p10_f1'])} "
                f"{tick(cell['frozen']['task013_cal_p10_f1'])}."
            )
    polarity = [
        cell["preset"]
        for cell in cells
        if cell["domain"] == "receta" and cell["granularity"] == "full_only" and cell["family"] == "polarity_v2_subset"
    ]
    if polarity:
        lines.append(
            "- receta/full_only selected `polarity_v2_subset` on " + ", ".join(tick(preset) for preset in polarity) + "."
        )
    lines.append(
        "- `base_repaired` alpha=0 rows that sit below the frozen TASK-013 CAL_ONLY p10 are listed in section 3. "
        "Repairing F3 anchor retention did not, by itself, pass that frozen F_polarity headline on those rows."
    )
    lines.append(
        "- Adding `structural_symbol_noise` lowers the nested F1 on the pairs in section 2 where the later preset is below the earlier one. "
        "That drop is a loss on the headline F1."
    )
    lines.append(
        "- near-OOD, hybrid, smuggle, and dilution rates that remain away from zero are the stored rates in sections 0, 5, and 7. "
        "A clause-cell improvement does not cancel a full_only cell that kept the higher rate."
    )
    lines.append(
        "- In-domain rows with `n_below_1` above zero in section 4 show `S_struct` firing on valid text. "
        "The latency figures do not say that firing is harmless."
    )
    lines.append(
        "This report does not promote the scorer into the production path. The approval gate is still open."
    )
    return lines


def render_report(
    manifest: dict[str, Any],
    cells: list[dict[str, Any]],
    *,
    phase0_quote: str,
    disk_before: str,
    disk_after: str,
) -> str:
    parts = [
        "# `fhv1_1` I+D v3 — full-1024D directional dials and lexical guardrail",
        "",
        "**Task**: `TASK-014`",
        "**Branch**: `feat/fhv1-1-id-v3-full1024d-and-lexical-guard`",
        f"**Dtype**: {tick(manifest['dtype'])}. **normalize**: {tick(manifest['normalize'])}. **mode**: {tick(manifest['mode'])}.",
        "",
        "Numbers in the tables are literals copied from `/tmp/fhv1_1_id_v3` JSON. A missing key aborts the generator.",
        "",
        "## 0. Executive",
        "",
        *executive_lines(manifest, cells),
        "",
        "## 1. Phase-0 and disk",
        "",
        "Phase-0 below is quoted from `roadmap/fhv1-1-id-v3-full1024d-and-lexical-guard.roadmap.md` section 1. "
        "It is the audit that already ran. This generator does not replace those figures with a second audit.",
        "",
        "```text",
        phase0_quote,
        "```",
        "",
        "### Disk at report generation, scratch still present" if "follows removal" in disk_after else "### Disk before scratch removal",
        "",
        "```text",
        disk_before.rstrip(),
        "```",
        "",
        "### Closing disk measurement",
        "",
        "```text",
        disk_after.rstrip(),
        "```",
        "",
        f"Floor is {FLOOR_KIB} KiB. The closing `df -k` Available field is the measurement that has to clear that floor.",
        "",
        "## 2. Stratum 4 preset impact",
        "",
        *stratum_lines(cells),
        "",
        "## 3. F_dir1024 versus polarity_v2_subset versus base_repaired",
        "",
        *directional_lines(cells),
        "",
        "## 4. Guardrail and S_struct ablations",
        "",
        *guard_lines(cells),
        "",
        "## 5. w_f on smuggle_recipe_footnote and dilution_80_20",
        "",
        *weight_lines(cells),
        "",
        "## 6. Master tables",
        "",
        *master_lines(cells),
        "",
        "## 7. Subtype deltas",
        "",
        *subtype_lines(cells),
        "",
        "## 8. sqlite3 subprocess json canary",
        "",
        *canary_lines(cells),
        "",
        "## 9. Closed and open",
        "",
        *closed_open_lines(cells, manifest),
        "",
    ]
    return "\n".join(parts) + "\n"


def parse_available_kib(df_k: str) -> int:
    rows = [line for line in df_k.splitlines() if line.strip()]
    if len(rows) < 2:
        raise RuntimeError("df -k returned no data row")
    parts = rows[-1].split()
    if len(parts) < 4:
        raise RuntimeError("df -k row is short")
    return int(parts[3])


def capture_df(repo: Path) -> tuple[str, int]:
    chunks = []
    availabilities = []
    for label, path in (("repo", repo), ("tmp", Path("/tmp"))):
        df_h = subprocess.check_output(["df", "-h", str(path)], text=True)
        df_k = subprocess.check_output(["df", "-k", str(path)], text=True)
        kib = parse_available_kib(df_k)
        availabilities.append(kib)
        chunks.append(f"# {label} {path}\n{df_h.rstrip()}\n{df_k.rstrip()}\navailable_kib {kib}")
    return "\n\n".join(chunks), min(availabilities)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=SCRATCH)
    parser.add_argument("--output", type=Path, default=Path("reports/fhv1_1_id_v3_report.md"))
    parser.add_argument(
        "--roadmap",
        type=Path,
        default=Path("roadmap/fhv1-1-id-v3-full1024d-and-lexical-guard.roadmap.md"),
    )
    parser.add_argument("--delete-input", action="store_true")
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[1]
    roadmap_path = args.roadmap if args.roadmap.is_absolute() else repo / args.roadmap
    output = args.output if args.output.is_absolute() else repo / args.output
    phase0 = quote_phase0(roadmap_path.read_text(encoding="utf-8"))
    manifest, cells, tokens = load_directory(args.input)
    disk_before, _before_kib = capture_df(repo)
    placeholder = "closing measurement follows removal of the scratch directory"
    draft = render_report(manifest, cells, phase0_quote=phase0, disk_before=disk_before, disk_after=placeholder)
    assert_executive_f1(draft, manifest)
    assert_section0_numbers(draft, tokens)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(draft, encoding="utf-8")
    if not args.delete_input:
        return 0
    resolved = args.input.resolve()
    if resolved.name != "fhv1_1_id_v3" or resolved.parent != Path("/tmp").resolve():
        raise RuntimeError(f"refusing to delete {resolved}")
    shutil.rmtree(resolved)
    if resolved.exists():
        raise RuntimeError("scratch directory still exists")
    disk_after, after_kib = capture_df(repo)
    if after_kib < FLOOR_KIB:
        raise RuntimeError(f"available KiB {after_kib} is below {FLOOR_KIB}")
    final = render_report(manifest, cells, phase0_quote=phase0, disk_before=disk_before, disk_after=disk_after)
    assert_executive_f1(final, manifest)
    assert_section0_numbers(final, tokens)
    output.write_text(final, encoding="utf-8")
    print(f"wrote {output} cells={len(cells)} available_kib={after_kib}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
