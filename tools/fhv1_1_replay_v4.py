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
"""v4 dual-axis replay: S_general vs 1B_base_tech, S_near vs near_ood_neighbor.

Calibration scores for both axes and S_struct are 5-fold OOF over document
bundles. The recipe catalog is a fixed compact list (<= 12). clause_cap uses
deterministic edge_plus_struct selection. JSON is written only under the
caller-supplied directory (dispatch defaults to /tmp/fhv1_1_id_v4).
"""

from __future__ import annotations

import atexit
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

import fhv1_1_lexical_profile as lex
import fhv1_1_replay_sim as sim
import fhv1_1_replay_v2 as v2
import fhv1_1_replay_v3 as v3
import fhv1_1_xray as xray

DIR_VARIANT = "dir1024_sig_sep"
EJE1_PRESET = "1B_base_tech"
NEAR_STRATUM = "near_ood_neighbor"
CLAUSE_CAPS: tuple[int | None, ...] = (None, 16, 24, 32)
W_F: tuple[float, ...] = (0.20, 0.35, 0.50)
BLEND_LAMBDAS: tuple[float, ...] = (0.20, 0.35)
AND_NEAR_PROBS: tuple[tuple[float, str], ...] = ((0.02, "p02"), (0.05, "p05"), (0.10, "p10"))
GEN_GATE_PROB = 0.10
PROB_TAGS: tuple[tuple[float, str], ...] = ((0.05, "p05"), (0.10, "p10"), (0.15, "p15"))
BOOTSTRAP_RESAMPLES = v2.BOOTSTRAP_RESAMPLES
CANARY_KINDS: tuple[str, ...] = ("sqlite3", "subprocess", "json")
CANARY_RE = re.compile(r"\b(sqlite3|subprocess|json)\b", re.IGNORECASE)
FOCUS_SUBTYPES: tuple[str, ...] = (
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
)
QUADRANT_NAMES: tuple[str, ...] = (
    "IN_DOMAIN_VALID",
    "OUT_OF_DOMAIN_BENIGN",
    "HYBRID_BOUNDARY",
    "ADVERSARIAL_FUZZING",
)
DEFAULT_OUT_DIR = Path("/tmp/fhv1_1_id_v4")
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080
SERVER_SCRIPT = Path(__file__).resolve().parent / "bge_m3_mps_server.py"


def _log(message: str) -> None:
    print(f"[fhv1_1_replay_v4] {message}", flush=True)


def _as_f64_matrix(values: np.ndarray, *, name: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError(f"{name} must be a non-empty 2D matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"non-finite values in {name}")
    return matrix


def _as_f64_vector(values: np.ndarray, *, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.size == 0:
        raise ValueError(f"{name} must be non-empty")
    if not np.all(np.isfinite(vector)):
        raise ValueError(f"non-finite values in {name}")
    return vector


def stack_eje1_contrast(
    groups: Mapping[tuple[str, str, str, bool], Mapping[str, Any]],
    lang: str,
    granularity: str,
    *,
    normalize: bool = True,
) -> np.ndarray:
    """Stack ``1B_base_tech`` only. Never mixes near-OOD or structural noise."""
    strata = xray.contrast_preset_strata(EJE1_PRESET)
    if NEAR_STRATUM in strata or xray.V2_NOISE_STRATUM in strata:
        raise RuntimeError("Eje 1 contrast leaked near-OOD or structural noise")
    return xray.stack_contrast_preset(groups, lang, granularity, EJE1_PRESET, normalize=normalize)


def stack_near_ood_contrast(
    groups: Mapping[tuple[str, str, str, bool], Mapping[str, Any]],
    lang: str,
    granularity: str,
    *,
    normalize: bool = True,
) -> np.ndarray:
    """Stack pure ``near_ood_neighbor`` for Eje 2. Axes stay separated."""
    key = (lang, granularity, NEAR_STRATUM, normalize)
    if key not in groups:
        raise KeyError(f"missing embedding slice {key}")
    matrix = np.asarray(groups[key]["vectors"], dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        raise ValueError("near_ood_neighbor contrast is empty")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("non-finite near_ood_neighbor contrast")
    return matrix


def fit_holdout_axis(target: np.ndarray, contrast: np.ndarray) -> v3.DirectionalFit:
    """Full-calibration dial used only to score holdout rows."""
    return v3.fit_directional_matrices(target, contrast)


def score_axis_oof(
    cal_vectors: np.ndarray,
    folds: np.ndarray,
    contrast: np.ndarray,
    *,
    n_folds: int = 5,
    variant: str = DIR_VARIANT,
) -> np.ndarray:
    """Score each calibration row with params fit on the other folds only.

    Same fold scheme as ``fit_geometry_level``: a held-out fold never enters
    ``mu_T`` / ``std_T`` for its own score. Contrast moments are fixed.
    """
    matrix = _as_f64_matrix(cal_vectors, name="calibration")
    fold_ids = np.asarray(folds, dtype=np.int64).reshape(-1)
    if fold_ids.shape[0] != matrix.shape[0]:
        raise ValueError("folds do not align with calibration rows")
    contrast_m = _as_f64_matrix(contrast, name="contrast")
    if contrast_m.shape[1] != matrix.shape[1]:
        raise ValueError("contrast dim differs from calibration")
    scores = np.empty(matrix.shape[0], dtype=np.float64)
    seen = np.zeros(matrix.shape[0], dtype=bool)
    for fold in range(n_folds):
        train = fold_ids != fold
        val = np.flatnonzero(fold_ids == fold)
        if val.size == 0:
            continue
        if int(np.sum(train)) < 2:
            raise RuntimeError("calibration fold has fewer than 2 target rows")
        fit = v3.fit_directional_matrices(matrix[train], contrast_m)
        scores[val] = v3.score_dir1024(matrix[val], fit, variant)
        seen[val] = True
    if not np.all(seen):
        raise RuntimeError("axis OOF left a calibration row unscored")
    if not np.all(np.isfinite(scores)):
        raise RuntimeError("non-finite axis OOF scores")
    return scores


def score_struct_oof(
    texts: Sequence[str],
    clauses: Sequence[Sequence[str]],
    folds: np.ndarray,
    *,
    n_folds: int = 5,
    time_calls: bool = False,
) -> dict[str, Any]:
    """5-fold OOF ``S_struct``. Each bundle is scored with a profile fit on 4 folds."""
    n_docs = len(texts)
    if n_docs == 0:
        raise ValueError("struct OOF needs at least one document")
    if len(clauses) != n_docs:
        raise ValueError("struct texts and clause lists differ in length")
    fold_ids = np.asarray(folds, dtype=np.int64).reshape(-1)
    if fold_ids.shape[0] != n_docs:
        raise ValueError("struct folds do not align with documents")
    s_full = np.empty(n_docs, dtype=np.float64)
    s_min = np.empty(n_docs, dtype=np.float64)
    full_features: list[tuple[str, ...] | None] = [None] * n_docs
    min_features: list[tuple[str, ...] | None] = [None] * n_docs
    full_us: list[float] = []
    clause_us: list[float] = []
    seen = np.zeros(n_docs, dtype=bool)
    for fold in range(n_folds):
        train_idx = np.flatnonzero(fold_ids != fold)
        val_idx = np.flatnonzero(fold_ids == fold)
        if val_idx.size == 0:
            continue
        if train_idx.size == 0:
            raise RuntimeError("struct OOF fold has an empty train set")
        train_texts = [texts[int(i)] for i in train_idx]
        train_clauses = [clause for i in train_idx for clause in clauses[int(i)]]
        if not train_clauses:
            raise RuntimeError("struct OOF train fold produced no clauses")
        full_profile = lex.fit(train_texts, "full_doc")
        clause_profile = lex.fit(train_clauses, "clause_opt2c")
        for i in val_idx:
            doc_i = int(i)
            started = time.perf_counter_ns()
            full = lex.score(texts[doc_i], full_profile)
            if time_calls:
                full_us.append(float(time.perf_counter_ns() - started) / 1000.0)
            clause_values: list[float] = []
            clause_names: set[str] = set()
            for clause in clauses[doc_i]:
                started = time.perf_counter_ns()
                scored = lex.score(clause, clause_profile)
                if time_calls:
                    clause_us.append(float(time.perf_counter_ns() - started) / 1000.0)
                clause_values.append(float(scored.s_struct))
                clause_names.update(feature.name for feature in scored.top_triggered_features)
            full_value, reduced = v3.struct_reductions(full.s_struct, clause_values)
            s_full[doc_i] = full_value
            s_min[doc_i] = reduced
            full_names = tuple(feature.name for feature in full.top_triggered_features)
            full_features[doc_i] = full_names
            min_features[doc_i] = tuple(sorted(set(full_names) | clause_names))
            seen[doc_i] = True
    if not np.all(seen):
        raise RuntimeError("struct OOF left a calibration document unscored")
    if not np.all(np.isfinite(s_full)) or not np.all(np.isfinite(s_min)):
        raise RuntimeError("non-finite S_struct OOF")
    if any(item is None for item in full_features) or any(item is None for item in min_features):
        raise RuntimeError("struct OOF left feature rows empty")
    return {
        "s_full": s_full,
        "s_min": s_min,
        "full_features": [item if item is not None else () for item in full_features],
        "min_features": [item if item is not None else () for item in min_features],
        "full_us": full_us,
        "clause_us": clause_us,
    }


@dataclass(frozen=True)
class V4RecipeSpec:
    """One compact dual-axis candidate. Catalog size is fixed and auditable."""

    family: str
    beta: float
    lam: float | None
    near_tag: str | None
    near_prob: float | None
    w_f: float | None

    def name(self) -> str:
        lam = "-" if self.lam is None else f"{self.lam:.2f}"
        near = "-" if self.near_tag is None else self.near_tag
        weight = "-" if self.w_f is None else f"{self.w_f:.2f}"
        return f"{self.family}|b={self.beta:.2f}|l={lam}|n={near}|w={weight}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name(),
            "family": self.family,
            "beta": float(self.beta),
            "lam": None if self.lam is None else float(self.lam),
            "near_tag": self.near_tag,
            "near_prob": None if self.near_prob is None else float(self.near_prob),
            "w_f": None if self.w_f is None else float(self.w_f),
        }


def compact_recipe_catalog(granularity: str) -> tuple[V4RecipeSpec, ...]:
    """Fixed catalog. ``full_only`` has exactly 12 recipes; clauses multiply by ``w_f``."""
    if granularity not in ("full_only", "clauses"):
        raise ValueError(f"unsupported granularity {granularity}")
    weights: tuple[float | None, ...]
    if granularity == "full_only":
        weights = (None,)
    else:
        weights = tuple(float(w) for w in W_F)
    specs: list[V4RecipeSpec] = []
    for weight in weights:
        specs.append(V4RecipeSpec("eje1_only", 0.0, None, None, None, weight))
        for beta in (0.10, 0.20):
            specs.append(V4RecipeSpec("eje1_plus_struct", float(beta), None, None, None, weight))
        for prob, tag in AND_NEAR_PROBS:
            specs.append(V4RecipeSpec("dual_axis_and", 0.0, None, tag, float(prob), weight))
        for lam in BLEND_LAMBDAS:
            specs.append(V4RecipeSpec("dual_axis_blend", 0.0, float(lam), None, None, weight))
            specs.append(V4RecipeSpec("dual_axis_blend", 0.15, float(lam), None, None, weight))
        specs.append(V4RecipeSpec("dual_axis_min", 0.0, None, None, None, weight))
        specs.append(V4RecipeSpec("dual_axis_min", 0.15, None, None, None, weight))
    catalog = tuple(specs)
    if granularity == "full_only" and len(catalog) > 12:
        raise RuntimeError(f"full_only catalog exceeded 12 recipes: {len(catalog)}")
    if granularity == "full_only" and len(catalog) != 12:
        raise RuntimeError(f"full_only catalog must be exactly 12, got {len(catalog)}")
    return catalog


def blend_axes(s_general: np.ndarray, s_near: np.ndarray, lam: float) -> np.ndarray:
    """``(1 - lambda) * S_general + lambda * S_near``."""
    left = _as_f64_vector(s_general, name="S_general")
    right = _as_f64_vector(s_near, name="S_near")
    if left.shape != right.shape:
        raise ValueError("axis blend shapes differ")
    weight = np.float64(lam)
    if weight < 0.0 or weight > 1.0:
        raise ValueError("lambda must be in [0, 1]")
    return (np.float64(1.0) - weight) * left + weight * right


def min_axes(s_general: np.ndarray, s_near: np.ndarray) -> np.ndarray:
    left = _as_f64_vector(s_general, name="S_general")
    right = _as_f64_vector(s_near, name="S_near")
    if left.shape != right.shape:
        raise ValueError("axis min shapes differ")
    return np.minimum(left, right)


def apply_struct_beta(s_sem: np.ndarray, s_struct: np.ndarray, beta: float) -> np.ndarray:
    return v3.apply_beta_struct(s_sem, s_struct, beta)


def score_recipe_continuous(
    spec: V4RecipeSpec,
    s_general: np.ndarray,
    s_near: np.ndarray,
    s_struct: np.ndarray,
) -> np.ndarray:
    """Continuous score for ranking / single-threshold recipes.

    ``dual_axis_and`` uses ``min(S_general, S_near)`` as a continuous proxy; hard
    CAL_ONLY predictions for that family use ``predict_dual_axis_and``.
    """
    general = _as_f64_vector(s_general, name="S_general")
    near = _as_f64_vector(s_near, name="S_near")
    struct = _as_f64_vector(s_struct, name="S_struct")
    if general.shape != near.shape or general.shape != struct.shape:
        raise ValueError("recipe score shapes differ")
    if spec.family == "eje1_only":
        semantic = general
    elif spec.family == "eje1_plus_struct":
        semantic = general
    elif spec.family == "dual_axis_and":
        semantic = min_axes(general, near)
    elif spec.family == "dual_axis_blend":
        if spec.lam is None:
            raise ValueError("dual_axis_blend requires lambda")
        semantic = blend_axes(general, near, spec.lam)
    elif spec.family == "dual_axis_min":
        semantic = min_axes(general, near)
    else:
        raise ValueError(f"unknown recipe family {spec.family}")
    if spec.beta == 0.0:
        return np.array(semantic, dtype=np.float64, copy=True)
    return apply_struct_beta(semantic, struct, spec.beta)


def dual_axis_and_thresholds(
    cal_general: np.ndarray,
    cal_near: np.ndarray,
    *,
    gen_prob: float = GEN_GATE_PROB,
    near_prob: float,
) -> tuple[float, float]:
    """Independent CAL_ONLY percentiles. Holdout labels are not an input."""
    general = _as_f64_vector(cal_general, name="cal_S_general")
    near = _as_f64_vector(cal_near, name="cal_S_near")
    t_gen = float(np.quantile(general, np.float64(gen_prob), method="linear"))
    t_near = float(np.quantile(near, np.float64(near_prob), method="linear"))
    return t_gen, t_near


def predict_dual_axis_and(
    hold_general: np.ndarray,
    hold_near: np.ndarray,
    *,
    t_gen: float,
    t_near: float,
) -> np.ndarray:
    """Hard dual gate: ``S_general >= T_gen AND S_near >= T_near``."""
    general = _as_f64_vector(hold_general, name="hold_S_general")
    near = _as_f64_vector(hold_near, name="hold_S_near")
    if general.shape != near.shape:
        raise ValueError("dual-and holdout shapes differ")
    return (general >= np.float64(t_gen)) & (near >= np.float64(t_near))


def materialize_recipe_matrix(
    specs: Sequence[V4RecipeSpec],
    s_general: np.ndarray,
    s_near: np.ndarray,
    s_struct: np.ndarray,
) -> np.ndarray:
    columns = [score_recipe_continuous(spec, s_general, s_near, s_struct) for spec in specs]
    matrix = np.column_stack(columns)
    if not np.all(np.isfinite(matrix)):
        raise RuntimeError("non-finite recipe matrix")
    return matrix


def evaluate_cal_only(
    cal_scores: np.ndarray,
    hold_scores: np.ndarray,
    y_true: np.ndarray,
) -> dict[str, Any]:
    """CAL_ONLY p05/p10/p15. Thresholds read calibration only."""
    return v3.evaluate_cal_only(cal_scores, hold_scores, y_true)


def evaluate_dual_and_cal_only(
    cal_general: np.ndarray,
    cal_near: np.ndarray,
    hold_general: np.ndarray,
    hold_near: np.ndarray,
    y_true: np.ndarray,
    *,
    near_prob: float,
    near_tag: str,
) -> dict[str, Any]:
    """Dual CAL_ONLY gate with fixed general p10 and configurable near percentile."""
    t_gen, t_near = dual_axis_and_thresholds(cal_general, cal_near, near_prob=near_prob)
    pred = predict_dual_axis_and(hold_general, hold_near, t_gen=t_gen, t_near=t_near)
    metrics = sim.compute_confusion_metrics(np.asarray(y_true, dtype=bool), pred)
    proxy = min_axes(hold_general, hold_near)
    auc = sim.compute_auc_triple(np.asarray(y_true, dtype=bool), proxy)
    return {
        "near_tag": near_tag,
        "near_prob": float(near_prob),
        "t_gen_p10": float(t_gen),
        "t_near": float(t_near),
        "tp": int(metrics["tp"]),
        "fn": int(metrics["fn"]),
        "tn": int(metrics["tn"]),
        "fp": int(metrics["fp"]),
        "precision": float(metrics["precision"]),
        "recall": None if metrics["recall"] is None else float(metrics["recall"]),
        "f1": float(metrics["f1"]),
        "frr": None if metrics["frr"] is None else float(metrics["frr"]),
        "far": None if metrics["far"] is None else float(metrics["far"]),
        "roc_auc": float(auc["roc_auc"]),
        "pr_auc_in_domain": float(auc["pr_auc_in_domain"]),
        "pr_auc_reject": float(auc["pr_auc_reject"]),
    }


def repeated_stratified_oof(
    scores: np.ndarray,
    y_true: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    input_ids: Sequence[str],
) -> dict[str, Any]:
    return v3.repeated_stratified_oof(scores, y_true, categories, subtypes, input_ids)


def nested_repeated_oof(
    scores: np.ndarray,
    y_true: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    input_ids: Sequence[str],
) -> dict[str, Any]:
    return v3.nested_repeated_oof(scores, y_true, categories, subtypes, input_ids)


BOOTSTRAP_PROBABILITY = 0.10


def bootstrap_cal_only(
    methods: Mapping[str, tuple[np.ndarray, np.ndarray]],
    y_true: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    *,
    seed: int = 0,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    probability: float = BOOTSTRAP_PROBABILITY,
) -> dict[str, Any]:
    """Bootstrap 1000, seed=0, ``refits_thresholds=True`` (via v3 paired path)."""
    return v3.bootstrap_cal_only_paired(
        methods,
        y_true,
        categories,
        subtypes,
        seed=seed,
        n_resamples=n_resamples,
        probability=probability,
    )


def detach_oracle(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    return v3.detach_oracle(row)


def freeze_winning_recipe(
    specs: Sequence[V4RecipeSpec],
    cal_matrix: np.ndarray,
    hold_matrix: np.ndarray,
    y_true: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    input_ids: Sequence[str],
) -> dict[str, Any]:
    """Select one recipe via nested 5x5 OOF. Holdout labels never set the CAL_ONLY threshold."""
    nested = nested_repeated_oof(hold_matrix, y_true, categories, subtypes, input_ids)
    clean, oracle = detach_oracle(dict(nested))
    modal = int(clean["modal_column"])
    winner = specs[modal]
    cal_scores = cal_matrix[:, modal]
    hold_scores = hold_matrix[:, modal]
    cal_only = evaluate_cal_only(cal_scores, hold_scores, y_true)
    return {
        "recipe": winner.as_dict(),
        "modal_column": modal,
        "nested_oof": v3._pack_repeated(clean),
        "oracle_upper_bound": oracle,
        "cal_only": cal_only,
    }


def select_clause_indices_edge_plus_struct(
    n_clauses: int,
    cap: int | None,
    s_struct: Sequence[float] | np.ndarray,
) -> list[int]:
    """Deterministic ``edge_plus_struct`` clause budget.

    When ``n_clauses > cap``:
    1. Reserve start and end edges (``e = max(1, cap // 8)`` each side).
    2. Reserve ``m = max(1, (cap - 2*e) // 2)`` evenly spaced mid samples.
    3. Fill remaining slots with the lowest ``S_struct`` (stable by index).
    CPU pre-filter before embedding.
    """
    if isinstance(cap, bool) or (cap is not None and (not isinstance(cap, int) or cap < 1)):
        raise ValueError("clause_cap must be None or a positive int")
    if n_clauses < 0:
        raise ValueError("n_clauses must be non-negative")
    scores = np.asarray(s_struct, dtype=np.float64).reshape(-1)
    if scores.shape[0] != n_clauses:
        raise ValueError("s_struct length must equal n_clauses")
    if not np.all(np.isfinite(scores)):
        raise ValueError("non-finite S_struct in clause_cap selection")
    if cap is None or n_clauses <= cap:
        return list(range(n_clauses))
    edge_each = max(1, cap // 8)
    if 2 * edge_each >= cap:
        edge_each = max(1, cap // 4)
    edge_total = 2 * edge_each
    remaining_after_edges = cap - edge_total
    mid_n = max(1, remaining_after_edges // 2) if remaining_after_edges > 1 else 0
    struct_k = cap - edge_total - mid_n
    selected: set[int] = set()
    start = list(range(0, min(edge_each, n_clauses)))
    end = list(range(max(0, n_clauses - edge_each), n_clauses))
    for idx in start + end:
        selected.add(idx)
    middle_pool = [i for i in range(n_clauses) if i not in selected]
    if mid_n > 0 and middle_pool:
        if len(middle_pool) <= mid_n:
            chosen_mid = middle_pool
        else:
            # Evenly spaced samples across the middle band.
            positions = np.linspace(0, len(middle_pool) - 1, num=mid_n)
            chosen_mid = [middle_pool[int(round(float(p)))] for p in positions]
        for idx in chosen_mid:
            selected.add(int(idx))
    remaining = [i for i in range(n_clauses) if i not in selected]
    if struct_k > 0 and remaining:
        order = sorted(remaining, key=lambda i: (float(scores[i]), i))
        for idx in order[:struct_k]:
            selected.add(idx)
    # If still short (edge overlap on tiny n), fill by lowest S_struct then index.
    if len(selected) < cap:
        fillers = sorted(range(n_clauses), key=lambda i: (float(scores[i]), i))
        for idx in fillers:
            selected.add(idx)
            if len(selected) >= cap:
                break
    # If over (mid duplicates), trim by dropping highest S_struct among non-edges.
    if len(selected) > cap:
        protected = set(start + end)
        extras = sorted((i for i in selected if i not in protected), key=lambda i: (-float(scores[i]), -i))
        for idx in extras:
            if len(selected) <= cap:
                break
            selected.discard(idx)
    return sorted(selected)


def apply_clause_cap_to_texts(
    clauses: Sequence[str],
    cap: int | None,
    s_struct: Sequence[float] | np.ndarray,
) -> list[str]:
    """Return the capped clause strings in index order."""
    keep = select_clause_indices_edge_plus_struct(len(clauses), cap, s_struct)
    return [clauses[i] for i in keep]


def prefilter_clause_s_struct(
    clauses: Sequence[str],
    profile: lex.LexicalProfile,
) -> np.ndarray:
    """CPU ``S_struct`` per clause before any embedding call."""
    if not clauses:
        return np.zeros(0, dtype=np.float64)
    values = np.empty(len(clauses), dtype=np.float64)
    for i, clause in enumerate(clauses):
        values[i] = float(lex.score(clause, profile).s_struct)
    if not np.all(np.isfinite(values)):
        raise RuntimeError("non-finite prefilter S_struct")
    return values


def subgroup_block(
    y_true: np.ndarray,
    pred: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
) -> dict[str, Any]:
    labels = np.asarray(y_true, dtype=bool)
    cats = np.asarray(list(categories), dtype=object)
    subs = np.asarray(list(subtypes), dtype=object)
    quadrants = {name: v2.subgroup_error(labels, pred, cats == name) for name in QUADRANT_NAMES}
    subtype_rows = []
    wanted = set(FOCUS_SUBTYPES) | set(subs.tolist())
    for subtype in sorted(wanted):
        mask = subs == subtype
        if not np.any(mask):
            continue
        row = v2.subgroup_error(labels, pred, mask)
        present = cats[mask]
        category = str(present[0]) if present.size else None
        subtype_rows.append({"subtype": str(subtype), "category": category, **row})
    return {"quadrants": quadrants, "subtypes": subtype_rows}


def canary_block(
    texts: Sequence[str],
    categories: Sequence[str],
    y_true: np.ndarray,
    pred: np.ndarray,
) -> dict[str, Any]:
    """Canary tokens with explicit ``kind`` and F1 vs FRR."""
    cats = np.asarray(list(categories), dtype=object)
    labels = np.asarray(y_true, dtype=bool)
    predictions = np.asarray(pred, dtype=bool)
    kinds: dict[str, dict[str, Any]] = {}
    for kind in CANARY_KINDS:
        pattern = re.compile(rf"\b{re.escape(kind)}\b", re.IGNORECASE)
        mask = np.array([bool(pattern.search(text)) for text in texts], dtype=bool)
        in_domain = mask & (cats == "IN_DOMAIN_VALID")
        metrics_all = v2.subgroup_error(labels, predictions, mask)
        metrics_in = v2.subgroup_error(labels, predictions, in_domain)
        kinds[kind] = {
            "kind": kind,
            "n_marker": int(np.sum(mask)),
            "n_marker_in_domain_valid": int(np.sum(in_domain)),
            "all_marker": metrics_all,
            "in_domain_valid_marker": metrics_in,
            "f1": metrics_all.get("f1"),
            "frr": metrics_in.get("frr"),
        }
    any_mask = np.array([bool(CANARY_RE.search(text)) for text in texts], dtype=bool)
    return {
        "pattern": r"\b(?:sqlite3|subprocess|json)\b",
        "kinds": kinds,
        "any_kind": {
            "n_marker": int(np.sum(any_mask)),
            "all_marker": v2.subgroup_error(labels, predictions, any_mask),
        },
    }


def struct_latency_block(full_us: Sequence[float], clause_us: Sequence[float]) -> dict[str, Any]:
    return v3._latency_block(full_us, clause_us)


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def ports_8080_8088_closed(*, host: str = SERVER_HOST) -> bool:
    """True when neither 8080 nor 8088 accepts TCP connections."""
    return (not _port_is_open(host, 8080)) and (not _port_is_open(host, 8088))


def _kill_exact_pid(pid: int) -> None:
    if pid <= 0:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.time() + 5.0
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


class EmbedServerSession:
    """Start ``bge_m3_mps_server.py`` on loopback with offline hub and exact-PID cleanup."""

    def __init__(
        self,
        *,
        script: Path = SERVER_SCRIPT,
        host: str = SERVER_HOST,
        port: int = SERVER_PORT,
        ready_timeout_s: float = 120.0,
    ) -> None:
        self.script = Path(script)
        self.host = host
        self.port = port
        self.ready_timeout_s = ready_timeout_s
        self.proc: subprocess.Popen[str] | None = None
        self._registered = False

    def start(self) -> int:
        if self.proc is not None:
            raise RuntimeError("embed server already started")
        if _port_is_open(self.host, self.port):
            raise RuntimeError(f"{self.host}:{self.port} is already open")
        env = os.environ.copy()
        env["HF_HUB_OFFLINE"] = "1"
        env["TEI_PORT"] = str(self.port)
        self.proc = subprocess.Popen(
            [sys.executable, str(self.script)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        atexit.register(self.cleanup)
        self._registered = True
        deadline = time.time() + self.ready_timeout_s
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"embed server exited early with code {self.proc.returncode}")
            if _port_is_open(self.host, self.port):
                return int(self.proc.pid)
            time.sleep(0.1)
        self.cleanup()
        raise TimeoutError(f"embed server did not open {self.host}:{self.port}")

    def cleanup(self) -> None:
        if self.proc is None:
            return
        pid = int(self.proc.pid)
        _kill_exact_pid(pid)
        try:
            self.proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            _kill_exact_pid(pid)
        self.proc = None

    def __enter__(self) -> EmbedServerSession:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.cleanup()


def measure_flooding_latency_ms(
    texts: Sequence[str],
    embed_fn: Callable[[Sequence[str]], Sequence[Sequence[float]]],
    *,
    repeats: int = 3,
) -> dict[str, Any]:
    """End-to-end flooding latency in ms via a caller-supplied embed callable."""
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    if not texts:
        raise ValueError("flooding latency needs at least one text")
    samples: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        vectors = embed_fn(list(texts))
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if len(vectors) != len(texts):
            raise RuntimeError("embed_fn returned the wrong number of vectors")
        samples.append(float(elapsed_ms))
    arr = np.asarray(samples, dtype=np.float64)
    return {
        "n_texts": len(texts),
        "repeats": repeats,
        "p50_ms": float(np.quantile(arr, 0.50, method="linear")),
        "p99_ms": float(np.quantile(arr, 0.99, method="linear")),
        "samples_ms": [float(x) for x in samples],
    }


def run_flooding_latency_with_server(
    texts: Sequence[str],
    embed_fn: Callable[[Sequence[str]], Sequence[Sequence[float]]],
    *,
    repeats: int = 3,
    start_server: bool = True,
) -> dict[str, Any]:
    """Optional real-server harness. Always cleans up the exact PID it started."""
    session: EmbedServerSession | None = None
    try:
        if start_server:
            session = EmbedServerSession()
            pid = session.start()
        else:
            pid = None
        block = measure_flooding_latency_ms(texts, embed_fn, repeats=repeats)
        block["server_pid"] = pid
        return block
    finally:
        if session is not None:
            session.cleanup()
        if not ports_8080_8088_closed():
            raise RuntimeError("PORTS_8080_8088_CLOSED failed after latency harness")


def _reject_tracked_output(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    repo = Path(__file__).resolve().parents[1]
    for banned in (repo / "reports", repo / "data"):
        banned_resolved = banned.resolve()
        if resolved == banned_resolved or banned_resolved in resolved.parents:
            raise RuntimeError(f"refusing to write v4 JSON under {banned_resolved}")


def evaluate_cell_synthetic(
    *,
    domain: str,
    granularity: str,
    s_general_cal: np.ndarray,
    s_near_cal: np.ndarray,
    s_struct_cal: np.ndarray,
    s_general_hold: np.ndarray,
    s_near_hold: np.ndarray,
    s_struct_hold: np.ndarray,
    y_true: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    input_ids: Sequence[str],
    texts: Sequence[str],
    struct_latency: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Score one regime cell from already-materialized axis scores (unit-test path)."""
    specs = compact_recipe_catalog(granularity if granularity == "full_only" else "full_only")
    # For synthetic clauses tests the caller already blended w_f into the vectors;
    # use the 12-recipe full_only catalog shape unless clauses + per-w_f matrices are supplied.
    if granularity == "clauses":
        # Expand catalog across w_f by treating input scores as already blended once;
        # callers that need per-w_f grids should call compact_recipe_catalog("clauses").
        specs = compact_recipe_catalog("full_only")
    cal_matrix = materialize_recipe_matrix(specs, s_general_cal, s_near_cal, s_struct_cal)
    hold_matrix = materialize_recipe_matrix(specs, s_general_hold, s_near_hold, s_struct_hold)
    frozen = freeze_winning_recipe(
        specs, cal_matrix, hold_matrix, y_true, categories, subtypes, input_ids
    )
    and_rows = []
    for prob, tag in AND_NEAR_PROBS:
        and_rows.append(
            evaluate_dual_and_cal_only(
                s_general_cal,
                s_near_cal,
                s_general_hold,
                s_near_hold,
                y_true,
                near_prob=prob,
                near_tag=tag,
            )
        )
    winner_col = int(frozen["modal_column"])
    threshold = float(frozen["cal_only"]["p10"]["threshold"])
    pred = hold_matrix[:, winner_col] >= np.float64(threshold)
    auc = sim.compute_auc_triple(np.asarray(y_true, dtype=bool), hold_matrix[:, winner_col])
    return {
        "domain": domain,
        "granularity": granularity,
        "catalog_size": len(specs),
        "recipes": [spec.as_dict() for spec in specs],
        "frozen": frozen,
        "dual_axis_and_cal_only": and_rows,
        "auc": auc,
        "subgroups": subgroup_block(y_true, pred, categories, subtypes),
        "canary": canary_block(texts, categories, y_true, pred),
        "struct_latency_us": struct_latency,
        "dtype": "float64",
        "normalize": True,
        "dir_variant": DIR_VARIANT,
        "eje1_preset": EJE1_PRESET,
        "eje2_stratum": NEAR_STRATUM,
    }


def run_replay_v4(
    *,
    lancedb_uri: Path,
    benchmarks_dir: Path,
    bg_parquet: Path,
    augmented_dir: Path,
    out_dir: Path,
) -> str:
    """Full dual-axis sweep. Intended for Slice 3 execution against LanceDB."""
    import lancedb

    _reject_tracked_output(Path(out_dir))
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    _log(f"loading background embeddings {bg_parquet}")
    groups = xray.load_embedding_groups(Path(bg_parquet), expected_dim=sim.DIM)
    db = lancedb.connect(str(lancedb_uri))
    runs = sim.load_lancedb_benchmark_runs(db)
    written: list[dict[str, Any]] = []
    headlines: list[str] = []
    for domain in ("python", "receta"):
        lang = xray.V2_DOMAIN_LANG[domain]
        profile_id = sim.V1_PROFILES[domain]
        index = v3.load_augmented_hash_index(v3.augmented_jsonl(Path(augmented_dir), domain))
        calibration = v3.load_calibration_with_hashes(db, profile_id, domain)
        raw_texts = v3.join_full_doc_texts(calibration["full_doc_sha256"], index)
        if len(raw_texts) != 600:
            raise RuntimeError(f"{domain} joined {len(raw_texts)} full documents, expected 600")
        cal_clauses = [xray.segment_clauses_opt2c(text) for text in raw_texts]
        folds = np.asarray(calibration["full_folds"], dtype=np.int64)
        _log(f"OOF S_struct {domain}")
        cal_struct_oof = score_struct_oof(raw_texts, cal_clauses, folds, time_calls=False)
        eje1_full = stack_eje1_contrast(groups, lang, "full_doc", normalize=True)
        eje1_clause = stack_eje1_contrast(groups, lang, "clause_opt2c", normalize=True)
        near_full = stack_near_ood_contrast(groups, lang, "full_doc", normalize=True)
        near_clause = stack_near_ood_contrast(groups, lang, "clause_opt2c", normalize=True)
        if near_full.shape[0] != 100:
            raise RuntimeError(f"{domain} near_ood full_doc count is {near_full.shape[0]}, expected 100")
        s_gen_cal_full = score_axis_oof(calibration["full_vectors"], folds, eje1_full)
        s_near_cal_full = score_axis_oof(calibration["full_vectors"], folds, near_full)
        s_gen_cal_clause = score_axis_oof(
            calibration["clause_vectors"],
            calibration["clause_folds"],
            eje1_clause,
        )
        s_near_cal_clause = score_axis_oof(
            calibration["clause_vectors"],
            calibration["clause_folds"],
            near_clause,
        )
        fit_gen_full = fit_holdout_axis(calibration["full_vectors"], eje1_full)
        fit_near_full = fit_holdout_axis(calibration["full_vectors"], near_full)
        fit_gen_clause = fit_holdout_axis(calibration["clause_vectors"], eje1_clause)
        fit_near_clause = fit_holdout_axis(calibration["clause_vectors"], near_clause)
        # Full profiles for holdout S_struct (cal thresholds already OOF).
        flat_clauses = [clause for doc in cal_clauses for clause in doc]
        full_profile = lex.fit(raw_texts, "full_doc")
        clause_profile = lex.fit(flat_clauses, "clause_opt2c")
        rows = v2.load_benchmark_table(Path(benchmarks_dir) / f"{domain}.jsonl")
        text_map = {str(row["input_id"]): str(row["text"]) for row in rows}
        subtypes_map = {str(row["input_id"]): str(row["subtype"]) for row in rows}
        categories_map = {str(row["input_id"]): str(row["category"]) for row in rows}
        expected_map = {str(row["input_id"]): bool(row["expected_pass"]) for row in rows}
        for granularity in ("full_only", "clauses"):
            run = runs[(profile_id, granularity, "m0")]
            bundle = sim.load_prompt_bundle(db, run["run_id"], granularity, subtypes_map, categories_map, expected_map)
            texts = [text_map[iid] for iid in bundle.input_ids]
            hold_clauses = [xray.segment_clauses_opt2c(text) for text in texts]
            hold_struct = v3.score_struct_corpus(
                texts, hold_clauses, full_profile, clause_profile, time_calls=True
            )
            hold_gen_chunks = v3.score_dir1024(bundle.chunk_vectors, fit_gen_full, DIR_VARIANT)
            hold_near_chunks = v3.score_dir1024(bundle.chunk_vectors, fit_near_full, DIR_VARIANT)
            if granularity == "full_only":
                hold_gen, _ = v3.holdout_parts(hold_gen_chunks, bundle)
                hold_near, _ = v3.holdout_parts(hold_near_chunks, bundle)
                cal_gen = s_gen_cal_full
                cal_near = s_near_cal_full
                cal_struct_vec = cal_struct_oof["s_full"]
                hold_struct_vec = hold_struct["s_full"]
                specs = compact_recipe_catalog("full_only")
                cal_matrix = materialize_recipe_matrix(specs, cal_gen, cal_near, cal_struct_vec)
                hold_matrix = materialize_recipe_matrix(specs, hold_gen, hold_near, hold_struct_vec)
            else:
                # Clause-aware blends across fixed w_f; freeze one winner.
                hold_gen_surface, hold_gen_cmin = v3.holdout_parts(
                    v3._matched_chunks(
                        hold_gen_chunks,
                        v3.score_dir1024(bundle.chunk_vectors, fit_gen_clause, DIR_VARIANT),
                        bundle.chunk_strategies,
                    ),
                    bundle,
                )
                hold_near_surface, hold_near_cmin = v3.holdout_parts(
                    v3._matched_chunks(
                        hold_near_chunks,
                        v3.score_dir1024(bundle.chunk_vectors, fit_near_clause, DIR_VARIANT),
                        bundle.chunk_strategies,
                    ),
                    bundle,
                )
                cal_gen_cmin = v3.calibration_clause_min(
                    s_gen_cal_full,
                    s_gen_cal_clause,
                    calibration["clause_bundle_ids"],
                    int(calibration["n_bundles"]),
                )
                cal_near_cmin = v3.calibration_clause_min(
                    s_near_cal_full,
                    s_near_cal_clause,
                    calibration["clause_bundle_ids"],
                    int(calibration["n_bundles"]),
                )
                specs = compact_recipe_catalog("clauses")
                cal_cols: list[np.ndarray] = []
                hold_cols: list[np.ndarray] = []
                for spec in specs:
                    if spec.w_f is None:
                        raise RuntimeError("clauses catalog requires w_f")
                    cal_g = v3.blend_documents(s_gen_cal_full, cal_gen_cmin, spec.w_f)
                    cal_n = v3.blend_documents(s_near_cal_full, cal_near_cmin, spec.w_f)
                    hold_g = v3.blend_documents(hold_gen_surface, hold_gen_cmin, spec.w_f)
                    hold_n = v3.blend_documents(hold_near_surface, hold_near_cmin, spec.w_f)
                    cal_cols.append(
                        score_recipe_continuous(spec, cal_g, cal_n, cal_struct_oof["s_min"])
                    )
                    hold_cols.append(
                        score_recipe_continuous(spec, hold_g, hold_n, hold_struct["s_min"])
                    )
                cal_matrix = np.column_stack(cal_cols)
                hold_matrix = np.column_stack(hold_cols)
                cal_gen = v3.blend_documents(s_gen_cal_full, cal_gen_cmin, 0.35)
                cal_near = v3.blend_documents(s_near_cal_full, cal_near_cmin, 0.35)
                hold_gen = v3.blend_documents(hold_gen_surface, hold_gen_cmin, 0.35)
                hold_near = v3.blend_documents(hold_near_surface, hold_near_cmin, 0.35)
            y = np.asarray(bundle.expected_pass, dtype=bool)
            frozen = freeze_winning_recipe(
                specs,
                cal_matrix,
                hold_matrix,
                y,
                bundle.categories,
                bundle.subtypes,
                bundle.input_ids,
            )
            and_rows = [
                evaluate_dual_and_cal_only(
                    cal_gen,
                    cal_near,
                    hold_gen,
                    hold_near,
                    y,
                    near_prob=prob,
                    near_tag=tag,
                )
                for prob, tag in AND_NEAR_PROBS
            ]
            winner_col = int(frozen["modal_column"])
            threshold = float(frozen["cal_only"]["p10"]["threshold"])
            pred = hold_matrix[:, winner_col] >= np.float64(threshold)
            cell = {
                "domain": domain,
                "granularity": granularity,
                "catalog_size": len(specs),
                "recipes": [spec.as_dict() for spec in specs],
                "frozen": frozen,
                "dual_axis_and_cal_only": and_rows,
                "auc": sim.compute_auc_triple(y, hold_matrix[:, winner_col]),
                "subgroups": subgroup_block(y, pred, bundle.categories, bundle.subtypes),
                "canary": canary_block(texts, bundle.categories, y, pred),
                "struct_latency_us": struct_latency_block(hold_struct["full_us"], hold_struct["clause_us"]),
                "clause_caps": list(CLAUSE_CAPS),
                "dtype": "float64",
                "normalize": True,
                "dir_variant": DIR_VARIANT,
                "eje1_preset": EJE1_PRESET,
                "eje2_stratum": NEAR_STRATUM,
                "cal_oof": True,
            }
            payload = v2.to_jsonable(cell)
            filename = f"{domain}__{granularity}__dual_axis_v4.json"
            destination = out_path / filename
            destination.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
            written.append(
                {
                    "file": filename,
                    "domain": domain,
                    "granularity": granularity,
                    "bytes": int(destination.stat().st_size),
                    "frozen_recipe": cell["frozen"]["recipe"]["name"],
                    "cal_only_p10_f1": cell["frozen"]["cal_only"]["p10"]["f1"],
                }
            )
            headlines.append(
                f"{domain}/{granularity} {cell['frozen']['recipe']['name']} "
                f"p10_f1={cell['frozen']['cal_only']['p10']['f1']:.6f}"
            )
            _log(headlines[-1])
    manifest = {
        "mode": "v4",
        "dtype": "float64",
        "dim": sim.DIM,
        "normalize": True,
        "n_cells": len(written),
        "cells": written,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": 0,
        "bootstrap_refits_thresholds": True,
        "cal_oof_folds": 5,
        "eje1_preset": EJE1_PRESET,
        "eje2_stratum": NEAR_STRATUM,
        "clause_caps": list(CLAUSE_CAPS),
        "output_dir": str(out_path),
    }
    manifest_path = out_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    lines = [
        "fhv1_1 replay v4",
        f"cells={len(written)} dir={out_path}",
        *headlines,
        f"manifest={manifest_path} bytes={manifest_path.stat().st_size}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(
        "dispatch via tools/fhv1_1_replay_sim.py --mode v4"
    )
