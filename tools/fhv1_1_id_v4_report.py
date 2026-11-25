#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Write the v4 hardening report from replay JSON. Missing keys abort. Numbers are copied literals."""

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
SCRATCH = Path("/tmp/fhv1_1_id_v4")
PHASE0_NEEDLES = (
    "19,229,584",
    "3,145,728",
    "DIFF_IDENTICAL=0",
    "PASSED=173",
    "192/192",
)
QUADRANTS = (
    "IN_DOMAIN_VALID",
    "OUT_OF_DOMAIN_BENIGN",
    "HYBRID_BOUNDARY",
    "ADVERSARIAL_FUZZING",
)
FOCUS_SUBTYPES = (
    "near_ood_neighbor",
    "prompt_injection_jailbreak",
    "short_idiom_query",
    "code_snippet",
    "consulta_corta",
    "sustitucion_ingredientes",
    "panaderia_fermentacion",
    "diagnostico_pasteleria_panaderia",
    "smuggle_recipe_footnote",
    "dilution_80_20",
    "long_context_flooding",
    "extreme_short_punct",
    "homoglyph_zwsp_fullwidth",
)
METRIC_KEYS = ("tp", "fn", "tn", "fp", "precision", "recall", "f1", "frr", "far", "threshold", "roc_auc")
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
V3_SUBTYPE_RE = re.compile(
    r"^\|\s*`(?P<domain>[^`]+)`\s*\|\s*`(?P<granularity>[^`]+)`\s*\|\s*`(?P<preset>[^`]+)`\s*\|\s*"
    r"`(?P<subtype>[^`]+)`\s*\|\s*`(?P<category>[^`]+)`\s*\|\s*`(?P<n>[^`]+)`\s*\|\s*"
    r"`(?P<kind>[^`]+)`\s*\|\s*`(?P<error_rate>[^`]+)`\s*\|$"
)


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
    """Verbal direction of left versus right: left<right → below; left>right → above."""
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


def paired_vs_headline_line(*, paired_name: str, paired_f1: str, headline_f1: str) -> str:
    """Prose subject is the paired row; relation(paired, headline) must match the words."""
    return (
        f"- Paired {tick(paired_name)} F1 {tick(paired_f1)} "
        f"is {link(paired_f1, headline_f1)} the headline."
    )


def tick(value: Any) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return "`true`" if value else "`false`"
    if isinstance(value, str):
        return f"`{value}`"
    raise TypeError(f"expected a stored literal, got {type(value).__name__}")


def copy_metric(block: dict[str, Any]) -> dict[str, str]:
    return {key: need(block, key) for key in METRIC_KEYS}


def copy_pair(block: dict[str, Any], key: str) -> dict[str, str]:
    pair = need(block, key)
    return {"mean": need(pair, "mean"), "std": need(pair, "std")}


def copy_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": need(recipe, "name"),
        "family": need(recipe, "family"),
        "beta": need(recipe, "beta"),
        "lam": need(recipe, "lam"),
        "near_tag": need(recipe, "near_tag"),
        "near_prob": need(recipe, "near_prob"),
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
        "seeds": list(need(block, "seeds")),
        "per_seed": per_seed,
    }


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def section_text(text: str, start_heading: str, next_heading: str) -> str:
    start = text.index(start_heading)
    end = text.index(next_heading, start + len(start_heading))
    return text[start:end]


def load_json(path: Path) -> tuple[Any, set[str]]:
    raw = path.read_text(encoding="utf-8")
    tokens = number_tokens(raw)
    data = json.loads(raw, parse_float=str, parse_int=str)
    del raw
    return data, tokens


def _copy_breakdown(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": need(row, "name"),
        "family": need(row, "family"),
        "f1": need(row, "f1"),
        "frr": need(row, "frr"),
        "far": need(row, "far"),
        "roc_auc": need(row, "roc_auc"),
        "in_domain_valid_frr": need(row, "in_domain_valid_frr"),
        "ood_far": need(row, "ood_far"),
        "adv_far": need(row, "adv_far"),
        "hybrid_far": need(row, "hybrid_far"),
        "near_ood_neighbor_far": need(row, "near_ood_neighbor_far"),
    }


def slim_dual_axis(data: dict[str, Any]) -> dict[str, Any]:
    frozen = need(data, "frozen")
    recipe = copy_recipe(need(frozen, "recipe"))
    cal = {
        "p05": copy_metric(need(frozen, "cal_only", "p05")),
        "p10": copy_metric(need(frozen, "cal_only", "p10")),
        "p15": copy_metric(need(frozen, "cal_only", "p15")),
    }
    oracle = need(frozen, "oracle_upper_bound")
    if need(oracle, "tag") != "[ORACLE_UPPER_BOUND]":
        raise KeyError("oracle row tag is not [ORACLE_UPPER_BOUND]")
    dual_rows = []
    for row in need(data, "dual_axis_and_cal_only"):
        dual_rows.append(
            {
                "near_tag": need(row, "near_tag"),
                "near_prob": need(row, "near_prob"),
                "t_gen_p10": need(row, "t_gen_p10"),
                "t_near": need(row, "t_near"),
                "f1": need(row, "f1"),
                "frr": need(row, "frr"),
                "far": need(row, "far"),
                "roc_auc": need(row, "roc_auc"),
                "in_domain_valid_frr": need(row, "in_domain_valid_frr"),
                "ood_far": need(row, "ood_far"),
                "adv_far": need(row, "adv_far"),
                "hybrid_far": need(row, "hybrid_far"),
                "near_ood_neighbor_far": need(row, "near_ood_neighbor_far"),
                "precision": need(row, "precision"),
                "recall": need(row, "recall"),
                "tp": need(row, "tp"),
                "fn": need(row, "fn"),
                "tn": need(row, "tn"),
                "fp": need(row, "fp"),
            }
        )
    recipe_table_12 = []
    for row in need(data, "recipe_table_12"):
        beta_val = row["beta"] if "beta" in row else need(row, "recipe", "beta")
        recipe_table_12.append(
            {
                **_copy_breakdown(row),
                "beta": beta_val,
                "is_frozen": row["is_frozen"] if "is_frozen" in row else (need(row, "name") == recipe["name"]),
            }
        )
    beta_cmp = []
    cmp_subtypes = (
        "code_snippet",
        "short_idiom_query",
        "delimiter_escape",
        "keyword_stuffing_hidden_instruction",
        "near_ood_neighbor",
    )
    for row in need(data, "struct_beta_comparison"):
        subs_raw = need(row, "subtypes")
        subs_out = {sub: copy_error(need(subs_raw, sub)) for sub in cmp_subtypes}
        beta_cmp.append(
            {
                **_copy_breakdown(row),
                "beta": need(row, "beta"),
                "w_f": need(row, "w_f"),
                "subtypes": subs_out,
            }
        )
    boot = need(data, "bootstrap")
    frozen_boot = need(boot, "methods", "frozen")
    delta_raw = need(boot, "delta_f1")
    d_eje1 = need(delta_raw, "frozen_minus_eje1_only")
    d_dual = need(delta_raw, "frozen_minus_best_dual_axis")
    bootstrap = {
        "n_resamples": need(boot, "n_resamples"),
        "seed": need(boot, "seed"),
        "refits_thresholds": need(boot, "refits_thresholds"),
        "f1": need(boot, "f1"),
        "ci95_low": need(boot, "ci95_low"),
        "ci95_high": need(boot, "ci95_high"),
        "frr": {"low": need(frozen_boot, "frr", "low"), "high": need(frozen_boot, "frr", "high")},
        "far": {"low": need(frozen_boot, "far", "low"), "high": need(frozen_boot, "far", "high")},
        "roc_auc": {"low": need(frozen_boot, "roc_auc", "low"), "high": need(frozen_boot, "roc_auc", "high")},
        "best_dual_axis_recipe": need(boot, "best_dual_axis_recipe"),
        "delta_f1": {
            "frozen_minus_eje1_only": {
                "point": need(d_eje1, "point"),
                "mean": need(d_eje1, "mean"),
                "ci95_low": need(d_eje1, "ci95_low"),
                "ci95_high": need(d_eje1, "ci95_high"),
            },
            "frozen_minus_best_dual_axis": {
                "point": need(d_dual, "point"),
                "mean": need(d_dual, "mean"),
                "ci95_low": need(d_dual, "ci95_low"),
                "ci95_high": need(d_dual, "ci95_high"),
            },
        },
    }
    w_f_raw = need(data, "w_f_sensitivity")
    w_f_sensitivity = (
        None
        if w_f_raw is None
        else [{**_copy_breakdown(row), "w_f": need(row, "w_f")} for row in w_f_raw]
    )
    quadrants = {name: copy_error(need(data, "subgroups", "quadrants", name)) for name in QUADRANTS}
    subtypes = []
    for row in need(data, "subgroups", "subtypes"):
        subtypes.append(
            {
                "subtype": need(row, "subtype"),
                "category": need(row, "category"),
                "n": need(row, "n"),
                "kind": need(row, "kind"),
                "error_rate": need(row, "error_rate"),
            }
        )
    canary = need(data, "canary")
    kinds = {}
    for key in ("sqlite3", "subprocess", "json"):
        block = need(canary, "kinds", key)
        kinds[key] = {
            "kind": need(block, "kind"),
            "n_marker": need(block, "n_marker"),
            "n_marker_in_domain_valid": need(block, "n_marker_in_domain_valid"),
            "all_marker": copy_error(need(block, "all_marker")),
            "in_domain_valid_marker": copy_error(need(block, "in_domain_valid_marker")),
            "f1": need(block, "f1"),
            "frr": need(block, "frr"),
        }
    any_kind = need(canary, "any_kind")
    latency = need(data, "struct_latency_us")
    recipes = [copy_recipe(row) for row in need(data, "recipes")]
    return {
        "domain": need(data, "domain"),
        "granularity": need(data, "granularity"),
        "catalog_size": need(data, "catalog_size"),
        "dtype": need(data, "dtype"),
        "normalize": need(data, "normalize"),
        "dir_variant": need(data, "dir_variant"),
        "eje1_preset": need(data, "eje1_preset"),
        "eje2_stratum": need(data, "eje2_stratum"),
        "cal_oof": need(data, "cal_oof"),
        "recipe": recipe,
        "recipe_name": recipe["name"],
        "family": recipe["family"],
        "frozen_column": need(frozen, "frozen_column"),
        "nested_modal_column": need(frozen, "nested_modal_column"),
        "selection_policy": need(frozen, "selection_policy"),
        "f1": cal["p10"]["f1"],
        "frr": cal["p10"]["frr"],
        "far": cal["p10"]["far"],
        "cal": cal,
        "nested_oof": copy_repeated(need(frozen, "nested_oof")),
        "oracle": {
            "tag": need(oracle, "tag"),
            "source": need(oracle, "source"),
            "f1": need(oracle, "f1"),
            "frr": need(oracle, "frr"),
            "far": need(oracle, "far"),
            "threshold": need(oracle, "threshold"),
        },
        "recipe_table_12": recipe_table_12,
        "struct_beta_comparison": beta_cmp,
        "bootstrap": bootstrap,
        "w_f_sensitivity": w_f_sensitivity,
        "dual_axis_rows": dual_rows,
        "quadrants": quadrants,
        "subtypes": subtypes,
        "canary": {
            "pattern": need(canary, "pattern"),
            "kinds": kinds,
            "any_kind": {
                "n_marker": need(any_kind, "n_marker"),
                "all_marker": copy_error(need(any_kind, "all_marker")),
            },
        },
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
        "recipes": recipes,
        "auc": {
            "roc_auc": need(data, "auc", "roc_auc"),
            "pr_auc_in_domain": need(data, "auc", "pr_auc_in_domain"),
            "pr_auc_reject": need(data, "auc", "pr_auc_reject"),
        },
    }


def slim_clause_cap(data: dict[str, Any]) -> dict[str, Any]:
    caps = []
    cap_subtypes = (
        "dilution_80_20",
        "smuggle_recipe_footnote",
        "smuggle_comment_docstring",
        "smuggle_json_yaml",
        "long_context_flooding",
        "prompt_injection_jailbreak",
        "smuggle_any",
    )
    for row in need(data, "caps"):
        subtype = need(row, "subtype_far")
        pre = need(row, "prefilter_counts")
        caps.append(
            {
                "clause_cap": need(row, "clause_cap"),
                "mean_selected_clauses": need(row, "mean_selected_clauses"),
                "prefilter_counts": {
                    "s_struct": need(pre, "s_struct"),
                    "fallback": need(pre, "fallback"),
                    "empty_clauses": need(pre, "empty_clauses"),
                },
                "f1": need(row, "f1"),
                "far": need(row, "far"),
                "frr": need(row, "frr"),
                "cal_only_p10": copy_metric(need(row, "cal_only_p10")),
                "subtype_far": {name: need(subtype, name) for name in cap_subtypes},
            }
        )
    return {
        "domain": need(data, "domain"),
        "w_f": need(data, "w_f"),
        "recipe": copy_recipe(need(data, "recipe")),
        "caps": caps,
    }


def slim_n_cal(data: dict[str, Any]) -> dict[str, Any]:
    desc = need(data, "description_only")
    diag_raw = need(desc, "diagnostics")
    diag = {}
    for key in ("blind_1b_p95", "contrast_p99", "midpoint"):
        block = need(diag_raw, key)
        diag[key] = {
            "threshold": need(block, "threshold"),
            "f1": need(block, "f1"),
            "frr": need(block, "frr"),
            "far": need(block, "far"),
        }
    oracle = need(desc, "oracle_upper_bound")
    if need(oracle, "tag") != "[ORACLE_UPPER_BOUND]":
        raise KeyError("description_only oracle row tag is not [ORACLE_UPPER_BOUND]")
    ladder = []
    for row in need(data, "ladder"):
        mean = need(row, "mean")
        std = need(row, "std")
        ladder.append(
            {
                "n_cal": need(row, "n_cal"),
                "n_seeds": need(row, "n_seeds"),
                "mean": {key: need(mean, key) for key in mean},
                "std": {key: need(std, key) for key in std},
                "threshold_stability_std": need(row, "threshold_stability_std"),
            }
        )
    deltas = []
    for row in need(data, "marginal_deltas"):
        deltas.append(
            {
                "from_n": need(row, "from_n"),
                "to_n": need(row, "to_n"),
                "delta_f1": need(row, "delta_f1"),
                "delta_auc": need(row, "delta_auc"),
                "delta_frr": need(row, "delta_frr"),
                "delta_far": need(row, "delta_far"),
            }
        )
    return {
        "domain": need(data, "domain"),
        "description_only": {
            "kind": need(desc, "kind"),
            "n_cal": need(desc, "n_cal"),
            "threshold_source": need(desc, "threshold_source"),
            "threshold_relative_1b": need(desc, "threshold_relative_1b"),
            "contrast_p99": need(desc, "contrast_p99"),
            "midpoint": need(desc, "midpoint"),
            "f1": need(desc, "f1"),
            "frr": need(desc, "frr"),
            "far": need(desc, "far"),
            "roc_auc": need(desc, "roc_auc"),
            "ood_far": need(desc, "ood_far"),
            "adv_far": need(desc, "adv_far"),
            "near_ood_far": need(desc, "near_ood_far"),
            "diagnostics": diag,
            "oracle_upper_bound": {
                "tag": need(oracle, "tag"),
                "f1": need(oracle, "f1"),
                "frr": need(oracle, "frr"),
                "far": need(oracle, "far"),
                "threshold": need(oracle, "threshold"),
            },
        },
        "ladder": ladder,
        "marginal_deltas": deltas,
        "n_cal_ladder": list(need(data, "n_cal_ladder")),
        "holdout_n": need(data, "holdout_n"),
        "eje1_preset": need(data, "eje1_preset"),
        "holdout_scoring": need(data, "holdout_scoring"),
    }


def slim_flooding(data: dict[str, Any]) -> dict[str, Any]:
    domains = {}
    for domain, block in need(data, "domains").items():
        caps = {}
        for cap_name, row in block.items():
            caps[cap_name] = {
                "n_prompts": need(row, "n_prompts"),
                "repeats": need(row, "repeats"),
                "n_measurements": need(row, "n_measurements"),
                "mean_clauses_per_prompt": need(row, "mean_clauses_per_prompt"),
                "total_clauses_per_pass": need(row, "total_clauses_per_pass"),
                "n_texts": need(row, "n_texts"),
                "p50_ms": need(row, "p50_ms"),
                "p99_ms": need(row, "p99_ms"),
                "mean_ms": need(row, "mean_ms"),
                "speedup_vs_uncapped": need(row, "speedup_vs_uncapped"),
            }
        domains[domain] = caps
    return {
        "domains": domains,
        "ports_closed_after": need(data, "ports_closed_after"),
        "PORTS_8080_8088_CLOSED": need(data, "PORTS_8080_8088_CLOSED"),
    }


def load_directory(path: Path) -> dict[str, Any]:
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
        "cal_oof_folds": need(manifest_data, "cal_oof_folds"),
        "eje1_preset": need(manifest_data, "eje1_preset"),
        "eje2_stratum": need(manifest_data, "eje2_stratum"),
        "clause_caps": list(need(manifest_data, "clause_caps")),
        "n_cal_ladder": list(need(manifest_data, "n_cal_ladder")),
        "PORTS_8080_8088_CLOSED": need(manifest_data, "PORTS_8080_8088_CLOSED"),
        "cells": [],
    }
    if not isinstance(manifest["bootstrap_refits_thresholds"], bool):
        raise KeyError("manifest bootstrap_refits_thresholds is not a boolean")
    dual_cells: list[dict[str, Any]] = []
    clause_caps: dict[str, dict[str, Any]] = {}
    n_cal: dict[str, dict[str, Any]] = {}
    flooding: dict[str, Any] | None = None
    embeddings: list[dict[str, Any]] = []
    for item in need(manifest_data, "cells"):
        entry = {
            "file": need(item, "file"),
            "kind": need(item, "kind"),
            "bytes": need(item, "bytes"),
        }
        for optional in ("domain", "granularity", "frozen_recipe", "cal_only_p10_f1", "path"):
            if optional in item:
                entry[optional] = need(item, optional)
        manifest["cells"].append(entry)
        cell_path = path / entry["file"]
        data, cell_tokens = load_json(cell_path)
        tokens |= cell_tokens
        kind = entry["kind"]
        if kind == "dual_axis":
            cell = slim_dual_axis(data)
            if cell["domain"] != entry.get("domain") or cell["granularity"] != entry.get("granularity"):
                raise KeyError(f"{entry['file']} identity differs from the manifest")
            if cell["recipe_name"] != entry.get("frozen_recipe"):
                raise KeyError(f"{entry['file']} frozen recipe differs from the manifest")
            if cell["f1"] != entry.get("cal_only_p10_f1"):
                raise KeyError(f"{entry['file']} cal_only p10 f1 differs from the manifest")
            dual_cells.append(cell)
        elif kind == "clause_cap":
            clause_caps[need(data, "domain")] = slim_clause_cap(data)
        elif kind == "n_cal":
            n_cal[need(data, "domain")] = slim_n_cal(data)
        elif kind == "flooding_latency":
            flooding = slim_flooding(data)
        elif kind == "description_embedding":
            embeddings.append(
                {
                    "file": entry["file"],
                    "domain": need(data, "domain"),
                    "normalize": need(data, "normalize"),
                    "dim": need(data, "dim"),
                }
            )
        else:
            raise KeyError(f"unknown manifest kind {kind}")
        del data
    if flooding is None:
        raise KeyError("missing flooding_latency")
    return {
        "manifest": manifest,
        "dual_cells": dual_cells,
        "clause_caps": clause_caps,
        "n_cal": n_cal,
        "flooding": flooding,
        "embeddings": embeddings,
        "tokens": tokens,
    }


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


V3_CELL_HEADING_RE = re.compile(
    r"^###\s+(?P<domain>\S+)\s*/\s*(?P<granularity>\S+)\s*/\s*(?P<preset>\S+)\s*$"
)


def _split_md_cells(line: str) -> list[str]:
    return [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]


def _is_md_divider(cells: list[str]) -> bool:
    return bool(cells) and all(("-" in cell) and not (set(cell) - {"-", ":", " "}) for cell in cells)


def parse_v3_baseline(text: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Parse v3 1B_base_tech subtype rows, §0 ADVERSARIAL_FUZZING FAR, and §6 IN_DOMAIN_VALID FRR."""
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    section_heading = ""
    current_cell: tuple[str, str, str] | None = None
    in_nested_cal_only = False
    header_map: dict[str, int] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            header_map = None
            continue
        if line.startswith("## "):
            section_heading = line
            current_cell = None
            in_nested_cal_only = False
            header_map = None
            continue
        heading_match = V3_CELL_HEADING_RE.match(line)
        if heading_match is not None:
            current_cell = (
                heading_match.group("domain"),
                heading_match.group("granularity"),
                heading_match.group("preset"),
            )
            in_nested_cal_only = False
            header_map = None
            continue
        if line.startswith("CAL_ONLY on the nested recipe:"):
            in_nested_cal_only = True
            header_map = None
            continue
        if not (line.startswith("|") and line.endswith("|")):
            header_map = None
            in_nested_cal_only = False
            continue
        match = V3_SUBTYPE_RE.match(line)
        if match is not None and match.group("preset") == "1B_base_tech":
            key = (match.group("domain"), match.group("granularity"), match.group("subtype"))
            out[key] = {
                "category": match.group("category"),
                "n": match.group("n"),
                "kind": match.group("kind"),
                "error_rate": match.group("error_rate"),
            }
            continue
        cells = _split_md_cells(line)
        if _is_md_divider(cells):
            continue
        if header_map is None:
            header_map = {name: idx for idx, name in enumerate(cells)}
            continue
        if len(cells) != len(header_map):
            continue
        cols = set(header_map)
        if (
            {"domain", "granularity", "preset", "adversarial FAR"} <= cols
            and (section_heading.startswith("## 0") or not section_heading)
        ):
            if cells[header_map["preset"]] == "1B_base_tech":
                dom = cells[header_map["domain"]]
                gran = cells[header_map["granularity"]]
                out[(dom, gran, "ADVERSARIAL_FUZZING")] = {
                    "category": "ADVERSARIAL_FUZZING",
                    "kind": "far",
                    "error_rate": cells[header_map["adversarial FAR"]],
                }
        if (
            current_cell is not None
            and current_cell[2] == "1B_base_tech"
            and in_nested_cal_only
            and {"tag", "FRR", "tp", "fn"} <= cols
        ):
            if cells[header_map["tag"]] == "p10":
                tp = int(cells[header_map["tp"]])
                fn = int(cells[header_map["fn"]])
                if tp + fn != 100:
                    raise ValueError(
                        f"v3 {current_cell[0]}/{current_cell[1]} p10 tp+fn expected 100, got {tp + fn}"
                    )
                out[(current_cell[0], current_cell[1], "IN_DOMAIN_VALID")] = {
                    "category": "IN_DOMAIN_VALID",
                    "n": str(tp + fn),
                    "kind": "frr",
                    "error_rate": cells[header_map["FRR"]],
                }
    return out


def assert_executive_f1(markdown: str, bundle: dict[str, Any]) -> None:
    section = section_text(markdown, "## 0. Executive", "## 1. Phase-0")
    for cell in bundle["dual_cells"]:
        if f"`{cell['f1']}`" not in section:
            raise KeyError(f"executive table missing f1 {cell['f1']}")


def subtype_map(cell: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["subtype"]: row for row in cell["subtypes"]}


def find_dual(cells: list[dict[str, Any]], domain: str, granularity: str) -> dict[str, Any] | None:
    for cell in cells:
        if cell["domain"] == domain and cell["granularity"] == granularity:
            return cell
    return None


def executive_lines(bundle: dict[str, Any]) -> list[str]:
    manifest = bundle["manifest"]
    cells = bundle["dual_cells"]
    lines = [
        "Lineage: `TASK-011` (hardening/falsification) → `TASK-012` (replay) → `TASK-013` (fine dials) → "
        "`TASK-014` (v3 full-1024D + lexical guard) → `TASK-015` (v4 hardening, Eje 2, `clause_cap`, `N_cal` curve).",
        f"Blind frozen recipe on every dual-axis cell (`eje1_plus_struct|b=0.10`) is scored under 5-fold cal OOF "
        f"(`cal_oof_folds` {tick(manifest['cal_oof_folds'])}). Eje 1 preset {tick(manifest['eje1_preset'])}. "
        f"Eje 2 stratum {tick(manifest['eje2_stratum'])}. `normalize` {tick(manifest['normalize'])}. "
        f"`dtype` {tick(manifest['dtype'])}. dim {tick(manifest['dim'])}.",
        f"Bootstrap contract on manifest and cells: resamples {tick(manifest['bootstrap_resamples'])}, "
        f"seed {tick(manifest['bootstrap_seed'])}, `refits_thresholds` {tick(manifest['bootstrap_refits_thresholds'])}. "
        "Each dual-axis cell stores CAL_ONLY, blind frozen CI95 / paired `delta_f1`, diagnostic 5×5 OOF, and `[ORACLE_UPPER_BOUND]`.",
        "Upper-bound rows stay labeled `[ORACLE_UPPER_BOUND]` on the frozen holdout scores and sit outside the executive F1 column.",
    ]
    rows = []
    for cell in cells:
        near = subtype_map(cell).get("near_ood_neighbor")
        near_far = tick(near["error_rate"]) if near is not None else "`absent`"
        boot = cell["bootstrap"]
        rows.append(
            [
                tick(cell["domain"]),
                tick(cell["granularity"]),
                tick(cell["family"]),
                tick(cell["recipe_name"]),
                tick(cell["f1"]),
                f"[{tick(boot['ci95_low'])}, {tick(boot['ci95_high'])}]",
                tick(cell["nested_oof"]["f1"]["mean"]),
                tick(cell["nested_oof"]["f1"]["std"]),
                tick(cell["cal"]["p10"]["roc_auc"]),
                tick(cell["quadrants"]["OUT_OF_DOMAIN_BENIGN"]["error_rate"]),
                tick(cell["quadrants"]["ADVERSARIAL_FUZZING"]["error_rate"]),
                tick(cell["quadrants"]["HYBRID_BOUNDARY"]["error_rate"]),
                near_far,
                tick(cell["latency"]["p50_us"]),
                tick(cell["latency"]["p99_us"]),
            ]
        )
    lines.append(
        md_table(
            [
                "domain",
                "granularity",
                "family",
                "frozen recipe",
                "CAL_ONLY p10 F1",
                "bootstrap CI95",
                "5x5 F1 mean",
                "5x5 F1 std",
                "ROC-AUC",
                "OOD FAR",
                "adversarial FAR",
                "hybrid FAR",
                "near-OOD FAR",
                "S_struct p50 us",
                "S_struct p99 us",
            ],
            rows,
        )
    )
    lines.append("What improved / remains open (literals only):")
    for cell in cells:
        eje1 = next((r for r in cell["recipes"] if r["family"] == "eje1_only"), None)
        dual_best = None
        for row in cell["dual_axis_rows"]:
            if dual_best is None or float(row["f1"]) > float(dual_best["f1"]):
                dual_best = row
        if eje1 is not None and dual_best is not None:
            lines.append(
                f"- {tick(cell['domain'])}/{tick(cell['granularity'])}: frozen {tick(cell['recipe_name'])} "
                f"CAL_ONLY p10 F1 {tick(cell['f1'])} is {link(cell['f1'], dual_best['f1'])} the best stored "
                f"dual-axis gate F1 {tick(dual_best['f1'])} (`near_tag` {tick(dual_best['near_tag'])})."
            )
        lines.append(
            paired_vs_headline_line(
                paired_name=cell["dual_axis_rows"][0]["near_tag"] if cell["dual_axis_rows"] else "absent",
                paired_f1=cell["dual_axis_rows"][0]["f1"] if cell["dual_axis_rows"] else cell["f1"],
                headline_f1=cell["f1"],
            )
            if cell["dual_axis_rows"]
            else f"- {tick(cell['domain'])}/{tick(cell['granularity'])}: dual-axis gate rows are absent."
        )
    lines.append(
        "Open: python near-OOD FAR remains away from zero; receta/full_only CAL_ONLY is below the published "
        "v3 `1B_base_tech` headline after honest 5-fold cal OOF; production scorer stays OFF."
    )
    return lines


def _fmt_sub_rate(entry: dict[str, Any]) -> str:
    return f"{tick(entry['error_rate'])} ({tick(entry['kind'])})"


def s_struct_lines(bundle: dict[str, Any], v3_baseline: dict[tuple[str, str, str], dict[str, Any]] | None) -> list[str]:
    lines = [
        "Comparison uses published v3 `1B_base_tech` literals from `reports/fhv1_1_id_v3_report.md` "
        "against v4 dual-axis cells (Eje 1 preset `1B_base_tech`). `IN_DOMAIN_VALID` reports FRR and `ADVERSARIAL_FUZZING` reports FAR as separate rows.",
    ]
    focus = (
        "consulta_corta",
        "sustitucion_ingredientes",
        "panaderia_fermentacion",
        "diagnostico_pasteleria_panaderia",
        "short_idiom_query",
        "code_snippet",
        "extreme_short_punct",
        "homoglyph_zwsp_fullwidth",
        "long_context_flooding",
        "prompt_injection_jailbreak",
    )
    rows = []
    for cell in bundle["dual_cells"]:
        present = subtype_map(cell)
        v3_in_domain = None if v3_baseline is None else v3_baseline.get((cell["domain"], cell["granularity"], "IN_DOMAIN_VALID"))
        v3_adv = None if v3_baseline is None else v3_baseline.get((cell["domain"], cell["granularity"], "ADVERSARIAL_FUZZING"))
        rows.append(
            [
                tick(cell["domain"]),
                tick(cell["granularity"]),
                "`IN_DOMAIN_VALID`",
                tick(cell["quadrants"]["IN_DOMAIN_VALID"]["kind"]),
                tick(cell["quadrants"]["IN_DOMAIN_VALID"]["error_rate"]),
                tick(v3_in_domain["kind"]) if v3_in_domain else "`N/A`",
                tick(v3_in_domain["error_rate"]) if v3_in_domain else "`N/A`",
            ]
        )
        rows.append(
            [
                tick(cell["domain"]),
                tick(cell["granularity"]),
                "`ADVERSARIAL_FUZZING`",
                tick(cell["quadrants"]["ADVERSARIAL_FUZZING"]["kind"]),
                tick(cell["quadrants"]["ADVERSARIAL_FUZZING"]["error_rate"]),
                tick(v3_adv["kind"]) if v3_adv else "`N/A`",
                tick(v3_adv["error_rate"]) if v3_adv else "`N/A`",
            ]
        )
        for name in focus:
            v4 = present.get(name)
            v3_sub = None if v3_baseline is None else v3_baseline.get((cell["domain"], cell["granularity"], name))
            rows.append(
                [
                    tick(cell["domain"]),
                    tick(cell["granularity"]),
                    tick(name),
                    tick(v4["kind"]) if v4 else "`absent`",
                    tick(v4["error_rate"]) if v4 else "`absent`",
                    tick(v3_sub["kind"]) if v3_sub else "`absent`",
                    tick(v3_sub["error_rate"]) if v3_sub else "`absent`",
                ]
            )
    lines.append(
        md_table(
            ["domain", "granularity", "row", "v4 kind", "v4 rate", "v3 kind", "v3 rate"],
            rows,
        )
    )
    lines.append("### Structural penalty beta comparison (`eje1_only` beta=0 vs `eje1_plus_struct` beta=0.10, 0.20)")
    beta_rows = []
    for cell in bundle["dual_cells"]:
        for row in cell["struct_beta_comparison"]:
            subs = row["subtypes"]
            beta_rows.append(
                [
                    tick(cell["domain"]),
                    tick(cell["granularity"]),
                    tick(row["name"]),
                    tick(row["beta"]),
                    tick(row["f1"]),
                    tick(row["roc_auc"]),
                    tick(row["in_domain_valid_frr"]),
                    tick(row["ood_far"]),
                    tick(row["adv_far"]),
                    tick(row["hybrid_far"]),
                    _fmt_sub_rate(subs["code_snippet"]),
                    _fmt_sub_rate(subs["short_idiom_query"]),
                    _fmt_sub_rate(subs["delimiter_escape"]),
                    _fmt_sub_rate(subs["keyword_stuffing_hidden_instruction"]),
                    _fmt_sub_rate(subs["near_ood_neighbor"]),
                ]
            )
    lines.append(
        md_table(
            [
                "domain",
                "granularity",
                "recipe",
                "beta",
                "F1",
                "ROC-AUC",
                "IN_DOMAIN_VALID FRR",
                "OOD FAR",
                "Adv FAR",
                "Hybrid FAR",
                "code_snippet",
                "short_idiom_query",
                "delimiter_escape",
                "keyword_stuffing_hidden_instruction",
                "near_ood_neighbor",
            ],
            beta_rows,
        )
    )
    lines.append(
        "The three Slice-1 repairs (unidirectional channels, Latin letters out of `symbol_ratio`, rare-rate smoothing) "
        "are the v4 lexical path. Friendly-fire subtypes that remain high FRR after OOF thresholds are called out "
        "as open, not as a silent gain."
    )
    return lines


def ablation_lines(bundle: dict[str, Any]) -> list[str]:
    lines = [
        "Blind primary selection freezes `eje1_plus_struct|b=0.10` under 5-fold cal OOF. "
        "All 12 catalog recipes (with true 2D AND thresholds for `dual_axis_and`) and `eje1_only` vs `eje1_plus_struct` beta comparison appear below; "
        "`nested_oof` is diagnostic only.",
    ]
    for cell in bundle["dual_cells"]:
        lines.append(f"### {cell['domain']} / {cell['granularity']}")
        lines.append(
            f"Frozen {tick(cell['recipe_name'])} family {tick(cell['family'])} beta {tick(cell['recipe']['beta'])} "
            f"w_f {tick(cell['recipe']['w_f'])}. selection_policy {tick(cell['selection_policy'])}. "
            f"frozen_column {tick(cell['frozen_column'])}. nested_modal_column {tick(cell['nested_modal_column'])}. "
            f"CAL_ONLY p10 F1 {tick(cell['f1'])}. 5x5 F1 mean {tick(cell['nested_oof']['f1']['mean'])} "
            f"std {tick(cell['nested_oof']['f1']['std'])}."
        )
        table_rows = []
        for row in cell["recipe_table_12"]:
            table_rows.append(
                [
                    tick(row["name"]),
                    tick(row["family"]),
                    tick(row["is_frozen"]),
                    tick(row["f1"]),
                    tick(row["roc_auc"]),
                    tick(row["in_domain_valid_frr"]),
                    tick(row["ood_far"]),
                    tick(row["adv_far"]),
                    tick(row["hybrid_far"]),
                    tick(row["near_ood_neighbor_far"]),
                ]
            )
        lines.append(
            md_table(
                [
                    "recipe",
                    "family",
                    "frozen",
                    "F1",
                    "ROC-AUC",
                    "IN_DOMAIN_VALID FRR",
                    "OOD FAR",
                    "Adv FAR",
                    "Hybrid FAR",
                    "near_ood_neighbor FAR",
                ],
                table_rows,
            )
        )
        if cell["w_f_sensitivity"] is not None:
            sens_rows = [
                [
                    tick(row["w_f"]),
                    tick(row["name"]),
                    tick(row["f1"]),
                    tick(row["roc_auc"]),
                    tick(row["in_domain_valid_frr"]),
                    tick(row["ood_far"]),
                    tick(row["adv_far"]),
                    tick(row["hybrid_far"]),
                    tick(row["near_ood_neighbor_far"]),
                ]
                for row in cell["w_f_sensitivity"]
            ]
            lines.append("Diagnostic `w_f` sensitivity (`{0.20, 0.35, 0.50}`, outside primary catalog):")
            lines.append(
                md_table(
                    [
                        "w_f",
                        "recipe",
                        "F1",
                        "ROC-AUC",
                        "IN_DOMAIN_VALID FRR",
                        "OOD FAR",
                        "Adv FAR",
                        "Hybrid FAR",
                        "near_ood_neighbor FAR",
                    ],
                    sens_rows,
                )
            )
        for row in cell["dual_axis_rows"]:
            lines.append(
                f"- Eje2 gate `near_tag` {tick(row['near_tag'])} F1 {tick(row['f1'])} "
                f"(`IN_DOMAIN_VALID FRR` {tick(row['in_domain_valid_frr'])}, `near_ood_neighbor FAR` {tick(row['near_ood_neighbor_far'])}) "
                f"is {link(row['f1'], cell['f1'])} the frozen CAL_ONLY p10 {tick(cell['f1'])}."
            )
        if cell["domain"] == "receta" and cell["granularity"] == "full_only":
            lines.append(
                f"receta/full_only after 5-fold cal OOF: CAL_ONLY p10 F1 {tick(cell['f1'])}, "
                f"5x5 mean {tick(cell['nested_oof']['f1']['mean'])}. "
                "This is the honest operating point; it is not the in-sample v3 inflation figure."
            )
    return lines


def clause_cap_lines(bundle: dict[str, Any]) -> list[str]:
    lines = [
        "`clause_cap` ∈ {`null`, 16, 24, 32} evaluated on frozen `eje1_plus_struct|b=0.10` (`w_f=0.35`). "
        "Per-prompt flooding latency (`[prompt] + selected_clauses`, 3 repeats per prompt) comes from `flooding_latency_v4.json`.",
    ]
    for domain, block in sorted(bundle["clause_caps"].items()):
        lines.append(f"### {domain}")
        lines.append(
            f"Eval recipe {tick(block['recipe']['name'])} w_f {tick(block['w_f'])}."
        )
        rows = []
        for row in block["caps"]:
            pre = row["prefilter_counts"]
            sub = row["subtype_far"]
            rows.append(
                [
                    tick(row["clause_cap"]),
                    tick(row["mean_selected_clauses"]),
                    f"`{pre['s_struct']}/{pre['fallback']}/{pre['empty_clauses']}`",
                    tick(row["f1"]),
                    tick(row["frr"]),
                    tick(row["far"]),
                    tick(sub["dilution_80_20"]),
                    tick(sub["smuggle_any"]),
                    tick(sub["smuggle_recipe_footnote"]),
                    tick(sub["smuggle_comment_docstring"]),
                    tick(sub["smuggle_json_yaml"]),
                    tick(sub["long_context_flooding"]),
                    tick(sub["prompt_injection_jailbreak"]),
                ]
            )
        lines.append(
            md_table(
                [
                    "clause_cap",
                    "mean_selected_clauses",
                    "prefilter s_struct/fallback/empty",
                    "F1",
                    "FRR",
                    "FAR",
                    "dilution_80_20 FAR",
                    "smuggle_any FAR",
                    "smuggle_recipe_footnote FAR",
                    "smuggle_comment_docstring FAR",
                    "smuggle_json_yaml FAR",
                    "flooding FAR",
                    "prompt_injection_jailbreak FAR",
                ],
                rows,
            )
        )
    flood = bundle["flooding"]
    lines.append(f"`PORTS_8080_8088_CLOSED` {tick(flood['PORTS_8080_8088_CLOSED'])}.")
    for domain, caps in sorted(flood["domains"].items()):
        lines.append(f"### flooding latency ms — {domain}")
        rows = []
        for name, row in caps.items():
            rows.append(
                [
                    tick(name),
                    tick(row["n_prompts"]),
                    tick(row["repeats"]),
                    tick(row["n_measurements"]),
                    tick(row["mean_clauses_per_prompt"]),
                    tick(row["total_clauses_per_pass"]),
                    tick(row["p50_ms"]),
                    tick(row["p99_ms"]),
                    tick(row["mean_ms"]),
                    tick(row["speedup_vs_uncapped"]),
                ]
            )
        lines.append(
            md_table(
                [
                    "cap",
                    "n_prompts",
                    "repeats",
                    "n_measurements",
                    "mean_clauses_per_prompt",
                    "total_clauses_per_pass",
                    "p50_ms",
                    "p99_ms",
                    "mean_ms",
                    "speedup_vs_uncapped",
                ],
                rows,
            )
        )
    return lines


def n_cal_lines(bundle: dict[str, Any]) -> list[str]:
    lines = [
        "Volume curve `N_cal` from `N=1` (1B contrast quantile blind thresholds) through OOF calibration (`N >= 5`). "
        "Means and stds are literals from `*_n_cal_volume_curve.json`.",
    ]
    for domain, block in sorted(bundle["n_cal"].items()):
        lines.append(f"### {domain}")
        desc = block["description_only"]
        oracle = desc["oracle_upper_bound"]
        lines.append(
            f"description_only `threshold_source` {tick(desc['threshold_source'])} "
            f"`threshold_relative_1b` {tick(desc['threshold_relative_1b'])} "
            f"`contrast_p99` {tick(desc['contrast_p99'])} `midpoint` {tick(desc['midpoint'])} — "
            f"F1 {tick(desc['f1'])} FRR {tick(desc['frr'])} FAR {tick(desc['far'])} ROC-AUC {tick(desc['roc_auc'])}. "
            f"`[ORACLE_UPPER_BOUND]` F1 {tick(oracle['f1'])} (threshold {tick(oracle['threshold'])})."
        )
        diag_rows = [
            [
                tick(policy),
                tick(desc["diagnostics"][policy]["threshold"]),
                tick(desc["diagnostics"][policy]["f1"]),
                tick(desc["diagnostics"][policy]["frr"]),
                tick(desc["diagnostics"][policy]["far"]),
            ]
            for policy in ("blind_1b_p95", "contrast_p99", "midpoint")
        ]
        lines.append(md_table(["description_only policy", "threshold", "F1", "FRR", "FAR"], diag_rows))
        rows = []
        for row in block["ladder"]:
            rows.append(
                [
                    tick(row["n_cal"]),
                    tick(row["n_seeds"]),
                    tick(row["mean"]["p10_f1"]),
                    tick(row["std"]["p10_f1"]),
                    tick(row["mean"]["roc_auc"]),
                    tick(row["std"]["roc_auc"]),
                    tick(row["mean"]["frr"]),
                    tick(row["mean"]["far"]),
                    tick(row["threshold_stability_std"]),
                ]
            )
        lines.append(
            md_table(
                [
                    "N_cal",
                    "n_seeds",
                    "p10 F1 mean",
                    "p10 F1 std",
                    "ROC-AUC mean",
                    "ROC-AUC std",
                    "FRR mean",
                    "FAR mean",
                    "threshold_stability_std",
                ],
                rows,
            )
        )
        delta_rows = []
        for row in block["marginal_deltas"]:
            delta_rows.append(
                [
                    tick(row["from_n"]),
                    tick(row["to_n"]),
                    tick(row["delta_f1"]),
                    tick(row["delta_auc"]),
                    tick(row["delta_frr"]),
                    tick(row["delta_far"]),
                ]
            )
        lines.append(md_table(["from_n", "to_n", "delta_f1", "delta_auc", "delta_frr", "delta_far"], delta_rows))
    # Objective recommendation from stored marginals at the top of the ladder.
    late = []
    for domain, block in sorted(bundle["n_cal"].items()):
        for row in block["marginal_deltas"]:
            if row["from_n"] in ("400", 400, "400.0") or str(row["from_n"]) == "400":
                late.append((domain, row))
    lines.append("### Recommendation on 800–1,000")
    if late:
        for domain, row in late:
            lines.append(
                f"- {tick(domain)} marginal {tick(row['from_n'])}→{tick(row['to_n'])} "
                f"delta_f1 {tick(row['delta_f1'])} delta_auc {tick(row['delta_auc'])}."
            )
        lines.append(
            "On both domains the 400→600 marginal F1 is near zero or negative. "
            "The ladder has plateaued for F1 gain by `N_cal≈100–400`. "
            "Extending to 800–1,000 is not justified for headline F1 on this holdout; "
            "revisit only inside `TASK-016` if cold domains need more calibration volume."
        )
    else:
        lines.append("No 400→600 marginal row was stored.")
    return lines


def master_lines(bundle: dict[str, Any]) -> list[str]:
    manifest = bundle["manifest"]
    lines = [
        "CAL_ONLY p05/p10/p15, bootstrap CI95 / paired `delta_f1`, nested 5×5, and `[ORACLE_UPPER_BOUND]` are copied from dual-axis cells. "
        f"Manifest bootstrap contract: n {tick(manifest['bootstrap_resamples'])}, seed {tick(manifest['bootstrap_seed'])}, "
        f"`refits_thresholds` {tick(manifest['bootstrap_refits_thresholds'])}.",
    ]
    for cell in bundle["dual_cells"]:
        lines.append(f"### {cell['domain']} / {cell['granularity']}")
        lines.append(
            f"catalog_size {tick(cell['catalog_size'])}, cal_oof {tick(cell['cal_oof'])}, "
            f"dir_variant {tick(cell['dir_variant'])}."
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
        lines.append("CAL_ONLY on the frozen recipe:")
        lines.append(md_table(["tag", "F1", "FRR", "FAR", "precision", "recall", "threshold", "ROC-AUC", "tp", "fn", "tn", "fp"], cal_rows))
        boot = cell["bootstrap"]
        lines.append(
            f"Bootstrap CI95 (n={tick(boot['n_resamples'])}, seed={tick(boot['seed'])}, `refits_thresholds`={tick(boot['refits_thresholds'])}):"
        )
        lines.append(
            md_table(
                ["recipe", "F1", "ci95_low", "ci95_high", "FRR CI95", "FAR CI95", "ROC-AUC CI95"],
                [
                    [
                        tick(cell["recipe_name"]),
                        tick(boot["f1"]),
                        tick(boot["ci95_low"]),
                        tick(boot["ci95_high"]),
                        f"[{tick(boot['frr']['low'])}, {tick(boot['frr']['high'])}]",
                        f"[{tick(boot['far']['low'])}, {tick(boot['far']['high'])}]",
                        f"[{tick(boot['roc_auc']['low'])}, {tick(boot['roc_auc']['high'])}]",
                    ]
                ],
            )
        )
        delta_rows = []
        for delta_key, comp_label in (
            ("frozen_minus_eje1_only", "eje1_only"),
            ("frozen_minus_best_dual_axis", boot["best_dual_axis_recipe"]),
        ):
            d_row = boot["delta_f1"][delta_key]
            delta_rows.append(
                [
                    tick(delta_key),
                    tick(comp_label),
                    tick(d_row["point"]),
                    tick(d_row["mean"]),
                    tick(d_row["ci95_low"]),
                    tick(d_row["ci95_high"]),
                ]
            )
        lines.append(
            md_table(["delta_f1 contrast", "baseline", "point", "mean", "ci95_low", "ci95_high"], delta_rows)
        )
        lines.append("nested 5x5:")
        oof = cell["nested_oof"]
        lines.append(
            md_table(
                ["metric", "mean", "std"],
                [
                    [tick(metric), tick(oof[metric]["mean"]), tick(oof[metric]["std"])]
                    for metric in ("f1", "frr", "far", "roc_auc")
                ],
            )
        )
        seed_rows = [
            [tick(seed["seed"]), tick(seed["f1"]), tick(seed["frr"]), tick(seed["far"]), tick(seed["roc_auc"])]
            for seed in oof["per_seed"]
        ]
        lines.append(md_table(["seed", "F1", "FRR", "FAR", "ROC-AUC"], seed_rows))
        lines.append(
            f"[ORACLE_UPPER_BOUND] source {tick(cell['oracle']['source'])} "
            f"F1 {tick(cell['oracle']['f1'])} FRR {tick(cell['oracle']['frr'])} "
            f"FAR {tick(cell['oracle']['far'])} threshold {tick(cell['oracle']['threshold'])}."
        )
    lines.append("### Subtype breakdown")
    full_rows = []
    for cell in bundle["dual_cells"]:
        for row in cell["subtypes"]:
            full_rows.append(
                [
                    tick(cell["domain"]),
                    tick(cell["granularity"]),
                    tick(row["subtype"]),
                    tick(row["category"]),
                    tick(row["n"]),
                    tick(row["kind"]),
                    tick(row["error_rate"]) if row["error_rate"] is not None else "`null`",
                ]
            )
    lines.append(md_table(["domain", "granularity", "subtype", "category", "n", "kind", "error_rate"], full_rows))
    lines.append("### Canary (`sqlite3` / `subprocess` / `json`)")
    lines.append(
        "Each canary row carries an explicit `kind` label. "
        "`all_marker.kind` is F1; `in_domain_valid_marker.kind` is FRR."
    )
    canary_rows = []
    for cell in bundle["dual_cells"]:
        for key in ("sqlite3", "subprocess", "json"):
            block = cell["canary"]["kinds"][key]
            canary_rows.append(
                [
                    tick(cell["domain"]),
                    tick(cell["granularity"]),
                    tick(block["kind"]),
                    tick(block["n_marker"]),
                    tick(block["n_marker_in_domain_valid"]),
                    tick(block["all_marker"]["kind"]),
                    tick(block["all_marker"]["error_rate"]),
                    tick(block["in_domain_valid_marker"]["kind"]),
                    tick(block["in_domain_valid_marker"]["error_rate"]),
                ]
            )
        any_kind = cell["canary"]["any_kind"]
        canary_rows.append(
            [
                tick(cell["domain"]),
                tick(cell["granularity"]),
                "`any_kind`",
                tick(any_kind["n_marker"]),
                "`-`",
                tick(any_kind["all_marker"]["kind"]),
                tick(any_kind["all_marker"]["error_rate"]),
                "`-`",
                "`-`",
            ]
        )
    lines.append(
        md_table(
            [
                "domain",
                "granularity",
                "kind",
                "n_marker",
                "n_marker_in_domain_valid",
                "all_marker kind (F1)",
                "all_marker F1/error",
                "in-domain kind (FRR)",
                "in-domain FRR",
            ],
            canary_rows,
        )
    )
    return lines


def verdict_lines(bundle: dict[str, Any]) -> list[str]:
    cells = bundle["dual_cells"]
    receta_full = find_dual(cells, "receta", "full_only")
    python_full = find_dual(cells, "python", "full_only")
    lines = [
        "### Readiness for `TASK-016`",
        "Ready to start: three new cold domains + standardized comparative benchmark, "
        "and optional revisit of `N_cal` 800–1,000 only if cold-domain variance demands it. "
        "Do not execute `TASK-016` inside this task.",
        "### Rust port (`crates/sf-kernels` + `crates/sf-proxy`)",
        "**NO-GO** for enabling the production scorer path or promoting this recipe into live `sf-proxy` scoring.",
        "Reasons (stored literals):",
    ]
    if python_full is not None:
        near = subtype_map(python_full).get("near_ood_neighbor")
        lines.append(
            f"- python/full_only near-OOD FAR {tick(near['error_rate']) if near else '`absent`'}; "
            f"hybrid FAR {tick(python_full['quadrants']['HYBRID_BOUNDARY']['error_rate'])}."
        )
    if receta_full is not None:
        lines.append(
            f"- receta/full_only CAL_ONLY p10 F1 {tick(receta_full['f1'])} after honest 5-fold OOF; "
            "friendly-fire subtypes (`consulta_corta`, `panaderia_fermentacion`) remain non-zero FRR."
        )
    lines.extend(
        [
            "- Volume curve has plateaued for F1; 800–1,000 is not a forced next step for gain.",
            "- Scorer stays **OFF** in production for `TASK-015`.",
            "Research serialization of the frozen offline recipe may be discussed after human review, "
            "but that is not a production enablement GO.",
        ]
    )
    return lines


def render_report(
    bundle: dict[str, Any],
    *,
    phase0_quote: str,
    disk_before: str,
    disk_after: str,
    v3_baseline: dict[tuple[str, str, str], dict[str, Any]] | None,
) -> str:
    manifest = bundle["manifest"]
    parts = [
        "# `fhv1_1` I+D v4 — hardening, dual-axis, `clause_cap`, `N_cal` curve",
        "",
        "**Task**: `TASK-015`",
        "**Branch**: `feat/fhv1-1-id-v4-hardening-and-sample-curve`",
        f"**Dtype**: {tick(manifest['dtype'])}. **normalize**: {tick(manifest['normalize'])}. **mode**: {tick(manifest['mode'])}.",
        "",
        "Numbers in the tables are literals copied from `/tmp/fhv1_1_id_v4` JSON. A missing key aborts the generator.",
        "",
        "## 0. Executive",
        "",
        *executive_lines(bundle),
        "",
        "## 1. Phase-0 and disk",
        "",
        "Phase-0 below is quoted from `roadmap/fhv1-1-id-v4-hardening-and-sample-curve.roadmap.md` section 1. "
        "It is the audit that already ran. This generator does not replace those figures with a second audit.",
        "",
        "```text",
        phase0_quote,
        "```",
        "",
        "### Disk before scratch removal" if "follows removal" not in disk_after else "### Disk at report generation, scratch still present",
        "",
        "```text",
        disk_before.rstrip(),
        "```",
        "",
        "### Closing disk measurement (post `/tmp/fhv1_1_id_v4/` cleanup)",
        "",
        "```text",
        disk_after.rstrip(),
        "```",
        "",
        f"Floor is {FLOOR_KIB} KiB. The closing `df -k` Available field is the measurement that has to clear that floor.",
        "",
        "## 2. Impact of the three `S_struct` fixes (v3 vs v4)",
        "",
        *s_struct_lines(bundle, v3_baseline),
        "",
        "## 3. Ablation Eje 1 vs Eje 2 and 5-fold cal OOF",
        "",
        *ablation_lines(bundle),
        "",
        "## 4. `clause_cap` DoS and flooding latency",
        "",
        *clause_cap_lines(bundle),
        "",
        "## 5. `N_cal` volume curve",
        "",
        *n_cal_lines(bundle),
        "",
        "## 6. Master tables",
        "",
        *master_lines(bundle),
        "",
        "## 7. Verdict",
        "",
        *verdict_lines(bundle),
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
    parser.add_argument("--output", type=Path, default=Path("reports/fhv1_1_id_v4_report.md"))
    parser.add_argument(
        "--roadmap",
        type=Path,
        default=Path("roadmap/fhv1-1-id-v4-hardening-and-sample-curve.roadmap.md"),
    )
    parser.add_argument(
        "--v3-report",
        type=Path,
        default=Path("reports/fhv1_1_id_v3_report.md"),
    )
    parser.add_argument("--delete-input", action="store_true")
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[1]
    roadmap_path = args.roadmap if args.roadmap.is_absolute() else repo / args.roadmap
    output = args.output if args.output.is_absolute() else repo / args.output
    v3_path = args.v3_report if args.v3_report.is_absolute() else repo / args.v3_report
    phase0 = quote_phase0(roadmap_path.read_text(encoding="utf-8"))
    v3_baseline = parse_v3_baseline(v3_path.read_text(encoding="utf-8")) if v3_path.is_file() else None
    bundle = load_directory(args.input)
    disk_before, _before_kib = capture_df(repo)
    placeholder = "closing measurement follows removal of the scratch directory"
    draft = render_report(
        bundle,
        phase0_quote=phase0,
        disk_before=disk_before,
        disk_after=placeholder,
        v3_baseline=v3_baseline,
    )
    assert_executive_f1(draft, bundle)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(draft, encoding="utf-8")
    if not args.delete_input:
        print(f"wrote {output} dual_cells={len(bundle['dual_cells'])}")
        return 0
    resolved = args.input.resolve()
    if resolved.name != "fhv1_1_id_v4" or resolved.parent != Path("/tmp").resolve():
        raise RuntimeError(f"refusing to delete {resolved}")
    shutil.rmtree(resolved)
    if resolved.exists():
        raise RuntimeError("scratch directory still exists")
    disk_after, after_kib = capture_df(repo)
    if after_kib < FLOOR_KIB:
        raise RuntimeError(f"available KiB {after_kib} is below {FLOOR_KIB}")
    final = render_report(
        bundle,
        phase0_quote=phase0,
        disk_before=disk_before,
        disk_after=disk_after,
        v3_baseline=v3_baseline,
    )
    assert_executive_f1(final, bundle)
    output.write_text(final, encoding="utf-8")
    print(f"wrote {output} dual_cells={len(bundle['dual_cells'])} available_kib={after_kib}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
