"""Offline v2 replay: 1,024-D Tail-Z, polarity, language-lock, document calibration.

Bucket labels select Tail-Z, polarity, and language-lock coordinates. They do not
drop a coordinate from F1, F2_L2, or the unlocked positive F3 bonus.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import fhv1_1_replay_sim as sim

TAIL_PS: tuple[int, ...] = (1, 3, 5, 10, 25)
SHORT_LIMITS: tuple[int, ...] = (0, 8, 12, 16, 20)
DOC_PROBS: tuple[float, ...] = (0.05, 0.10, 0.15)
REPEATED_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
BOOTSTRAP_RESAMPLES = 1000
SECONDARY_BAND: tuple[int, ...] = (202, 278, 408, 780, 871)
BUCKET_ORDER: tuple[str, ...] = (
    "BACKBONE_UNIVERSAL",
    "LOCALE_LANG_DIMS",
    "POLARITY_FLIP_DIALS",
    "FIRM_DOMAIN_ANCHOR",
    "NEGATIVE_INTRUDER_SENSOR",
    "SUBTLE_DISCRIMINATORS",
    "LOW_SIGNAL_NOISE",
)
EXPECTED_FULL_BUCKETS: dict[str, tuple[int, ...]] = {
    "python": (27, 0, 101, 5, 0, 258, 633),
    "receta": (21, 0, 168, 33, 4, 333, 465),
}
EXPECTED_CLAUSE_ROWS: dict[str, int] = {"python": 3579, "receta": 4066}
DOMAIN_LANG: dict[str, str] = {"python": "en", "receta": "es"}
CONTRASTS: tuple[str, ...] = ("1B_base_tech", "1B_full")
XRAY_GRANULARITY: dict[str, str] = {"full_only": "full_doc", "clauses": "clause_opt2c"}

FROZEN_HEADLINE: dict[tuple[str, str], dict[str, str]] = {
    ("python", "full_only"): {
        "task011_f1": "0.4439",
        "task011_frr": "11.00",
        "task011_far": "70.67",
        "task012_f1": "0.5606",
        "task012_frr": "19.00",
        "task012_far": "36.00",
        "task012_roc": "0.7780",
        "task012_pr_in": "0.4919",
        "task012_pr_rej": "0.9223",
        "task012_cal05_f1": "0.5597",
    },
    ("python", "clauses"): {
        "task011_f1": "0.4500",
        "task011_frr": "37.00",
        "task011_far": "39.00",
        "task012_f1": "0.6723",
        "task012_frr": "20.00",
        "task012_far": "19.33",
        "task012_roc": "0.8599",
        "task012_pr_in": "0.5835",
        "task012_pr_rej": "0.9546",
        "task012_cal05_f1": "0.5792",
    },
    ("receta", "full_only"): {
        "task011_f1": "0.4536",
        "task011_frr": "12.00",
        "task011_far": "66.67",
        "task012_f1": "0.6975",
        "task012_frr": "17.00",
        "task012_far": "18.33",
        "task012_roc": "0.8713",
        "task012_pr_in": "0.6316",
        "task012_pr_rej": "0.9553",
        "task012_cal05_f1": "0.7000",
    },
    ("receta", "clauses"): {
        "task011_f1": "0.3607",
        "task011_frr": "56.00",
        "task011_far": "33.33",
        "task012_f1": "0.7257",
        "task012_frr": "18.00",
        "task012_far": "14.67",
        "task012_roc": "0.8967",
        "task012_pr_in": "0.7202",
        "task012_pr_rej": "0.9641",
        "task012_cal05_f1": "0.5195",
    },
}

_HEADLINE_RE = re.compile(
    r"\| `(?P<domain>python|receta) / (?P<granularity>full_only|clauses)` \| "
    r"(?P<task011_f1>\d+\.\d+) \((?P<task011_frr>\d+\.\d+)%/(?P<task011_far>\d+\.\d+)%\) \| "
    r".*?\| (?P<task012_roc>\d+\.\d+) \| (?P<task012_pr_in>\d+\.\d+) / (?P<task012_pr_rej>\d+\.\d+) \| "
    r"\*\*(?P<task012_f1>\d+\.\d+)\*\* \((?P<task012_frr>\d+\.\d+)%/(?P<task012_far>\d+\.\d+)%\) \| "
    r"\*{0,2}(?P<task012_cal05_f1>\d+\.\d+)\*{0,2} \|"
)
_SECTION_RE = re.compile(
    r"^### (?P<domain>python|receta) / `(?P<granularity>full_only|clauses)` — Complete "
)
_SUBTYPE_RE = re.compile(
    r"^\| `(?P<category>[A-Z_]+)` \((?P<kind>FRR|FAR)\) \| `(?P<subtype>[^`]+)` \| (?P<n>\d+) \| "
    r"(?P<task011>\d+\.\d+)% \(\d+/\d+\) \| (?P<task012>\d+\.\d+)% \|"
)
_TOKEN_RE = re.compile(r"\b(?:sqlite3|subprocess|json)\b", re.IGNORECASE)


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def recipe_names() -> tuple[str, ...]:
    return (
        "base",
        "base_drop_primary",
        "base_consistency_primary",
        "base_drop_secondary",
        "base_consistency_secondary",
        "polarity",
        "polarity_plus_base",
        *(f"tail_{p}" for p in TAIL_PS),
        *(f"tail_{p}_plus_base" for p in TAIL_PS),
        *(f"tail_{p}_polarity_plus_base" for p in TAIL_PS),
    )


def signal_label(recipe: str) -> str:
    fixed = {
        "base": "F1+F2_L2+F3",
        "base_drop_primary": "F1+F2_L2+F3 language-lock primary drop",
        "base_consistency_primary": "F1+F2_L2+F3 language-lock primary consistency",
        "base_drop_secondary": "F1+F2_L2+F3 language-lock secondary_band drop",
        "base_consistency_secondary": "F1+F2_L2+F3 language-lock secondary_band consistency",
        "polarity": "F_polarity",
        "polarity_plus_base": "F_polarity+F1+F2_L2+F3",
    }
    if recipe in fixed:
        return fixed[recipe]
    body = recipe[len("tail_") :]
    if body.endswith("_polarity_plus_base"):
        return f"Tail-Z P={body[: -len('_polarity_plus_base')]}+F_polarity+F1+F2_L2+F3"
    if body.endswith("_plus_base"):
        return f"Tail-Z P={body[: -len('_plus_base')]}+F1+F2_L2+F3"
    return f"Tail-Z P={body}"


def language_lock_band(dim_ids: Sequence[int], primary: Sequence[int], secondary: Sequence[int]) -> str:
    dims = {int(d) for d in dim_ids}
    primary_set = {int(d) for d in primary}
    secondary_set = {int(d) for d in secondary}
    if dims == primary_set:
        return "primary"
    if dims == secondary_set and dims != primary_set:
        return "secondary_band"
    raise ValueError("locale set is neither the primary set nor the secondary band")


def tail_z_rows(vectors: np.ndarray, mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    x = np.asarray(vectors, dtype=np.float64)
    center = np.asarray(mu, dtype=np.float64)
    scale = np.asarray(sigma, dtype=np.float64)
    if x.ndim != 2 or center.shape != (x.shape[1],) or scale.shape != (x.shape[1],):
        raise ValueError(f"tail-z shape {x.shape} vs mu {center.shape}")
    return np.abs(x - center) / (scale + sim.EPS_SIGMA)


def worst_p_mean(z: np.ndarray, p: int) -> np.ndarray:
    arr = np.asarray(z, dtype=np.float64)
    if arr.ndim != 2 or p < 1 or p > arr.shape[1]:
        raise ValueError(f"worst-{p} mean is not defined for shape {arr.shape}")
    if p == arr.shape[1]:
        return np.mean(arr, axis=1)
    part = np.partition(arr, arr.shape[1] - p, axis=1)[:, -p:]
    return np.mean(part, axis=1)


def map_tail_score(raw: np.ndarray, q90: float) -> np.ndarray:
    scale = max(np.float64(q90), np.float64(sim.SCALE_FLOOR))
    score = np.exp(-np.asarray(raw, dtype=np.float64) / scale)
    return np.minimum(np.maximum(score, np.finfo(np.float64).tiny), np.float64(1.0))


def tail_scores_all_dimensions(
    vectors: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    p: int,
    q90: float,
    bucket_labels: Sequence[str] | None = None,
) -> np.ndarray:
    if bucket_labels is not None and len(bucket_labels) != int(np.asarray(vectors).shape[1]):
        raise ValueError("bucket labels do not match the coordinate count")
    z = tail_z_rows(vectors, mu, sigma)
    if z.shape[1] != np.asarray(vectors).shape[1]:
        raise RuntimeError("Tail-Z dropped a coordinate")
    return map_tail_score(worst_p_mean(z, p), q90)


def calibration_bundle_q90(bundle_values: np.ndarray) -> float:
    raw = np.asarray(bundle_values, dtype=np.float64)
    if raw.ndim != 1 or raw.size < 2:
        raise ValueError("q90 scale is fit on calibration bundles only")
    scale = float(np.quantile(raw, np.float64(0.90), method="linear"))
    return float(max(np.float64(scale), np.float64(sim.SCALE_FLOOR)))


def polarity_score(vectors: np.ndarray, dial_idx: np.ndarray, dial_mu: np.ndarray) -> np.ndarray:
    x = np.asarray(vectors, dtype=np.float64)
    idx = np.asarray(dial_idx, dtype=np.int64)
    mu = np.asarray(dial_mu, dtype=np.float64)
    if idx.size == 0:
        return np.ones(x.shape[0], dtype=np.float64)
    if idx.shape != mu.shape:
        raise ValueError("polarity dial index and mean differ")
    sign = np.sign(mu)
    if np.any(sign == 0.0):
        raise ValueError("polarity dial mean is zero")
    signed = x[:, idx] * sign
    keep = signed > np.float64(0.0)
    frac = np.mean(keep.astype(np.float64), axis=1)
    margin = np.maximum(signed, np.float64(0.0)) / np.abs(mu)
    margin_unit = np.minimum(margin, np.float64(1.0))
    return frac * np.mean(margin_unit, axis=1)


def positive_f3_bonus(
    vectors: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    drop_dims: Sequence[int],
) -> np.ndarray:
    x = np.asarray(vectors, dtype=np.float64)
    center = np.asarray(mu, dtype=np.float64)
    scale = np.asarray(sigma, dtype=np.float64)
    drop = {int(d) for d in drop_dims}
    keep = np.array([d for d in range(center.shape[0]) if d not in drop], dtype=np.int64)
    if keep.size == 0:
        return np.ones(x.shape[0], dtype=np.float64)
    terms = np.exp(-np.abs(x[:, keep] - center[keep]) / (np.float64(2.0) * scale[keep] + sim.EPS_SIGMA))
    return np.mean(terms, axis=1)


def monolingual_consistency(
    vectors: np.ndarray,
    locale_dims: Sequence[int],
    mu_en: np.ndarray,
    mu_es: np.ndarray,
    domain_lang: str,
) -> np.ndarray:
    x = np.asarray(vectors, dtype=np.float64)
    if len(locale_dims) == 0:
        return np.ones(x.shape[0], dtype=np.float64)
    if domain_lang not in ("en", "es"):
        raise ValueError(f"unsupported domain language {domain_lang}")
    dims = np.array([int(d) for d in locale_dims], dtype=np.int64)
    en = np.asarray(mu_en, dtype=np.float64)
    es = np.asarray(mu_es, dtype=np.float64)
    mu_dom = en if domain_lang == "en" else es
    mu_oth = es if domain_lang == "en" else en
    direction = np.sign(mu_dom[dims] - mu_oth[dims])
    active = direction != 0.0
    if not np.any(active):
        return np.ones(x.shape[0], dtype=np.float64)
    mid = np.float64(0.5) * (mu_dom[dims] + mu_oth[dims])
    signed = (x[:, dims] - mid) * direction
    agree = signed[:, active] > np.float64(0.0)
    return np.mean(agree.astype(np.float64), axis=1)


def apply_language_lock(
    unlocked: np.ndarray,
    *,
    mode: str,
    locale_dims: Sequence[int],
    consistency: np.ndarray | None = None,
    dropped_bonus_score: np.ndarray | None = None,
) -> np.ndarray:
    base = np.array(np.asarray(unlocked, dtype=np.float64), dtype=np.float64, copy=True)
    if mode == "off" or len(tuple(locale_dims)) == 0:
        return base
    if mode == "monolingual_consistency":
        if consistency is None:
            raise ValueError("monolingual consistency requires a consistency vector")
        return base * np.asarray(consistency, dtype=np.float64)
    if mode == "drop_positive_f3":
        if dropped_bonus_score is None:
            raise ValueError("drop_positive_f3 requires the recomputed bonus score")
        return np.array(np.asarray(dropped_bonus_score, dtype=np.float64), dtype=np.float64, copy=True)
    raise ValueError(f"unsupported language-lock mode {mode}")


def assign_document_bundle_ids(sample_ids: Sequence[str], tags: Sequence[str]) -> np.ndarray:
    """Bundle id of each row. A full_doc opens a bundle; later rows stay with it.

    This follows assign_calibration_folds: the numeric sample_id prefix orders the
    rows. The constant source_ref string is not a bundle key.
    """
    n = len(sample_ids)
    if n != len(tags):
        raise ValueError("sample_ids and tags differ in length")
    if n == 0:
        return np.empty(0, dtype=np.int64)
    for sid in sample_ids:
        prefix = sid.split("-", 1)[0]
        if not prefix.isdigit():
            raise ValueError(f"sample_id {sid} has no numeric prefix")
    order = sorted(range(n), key=lambda i: (int(sample_ids[i].split("-", 1)[0]), sample_ids[i]))
    bundle_ids = np.empty(n, dtype=np.int64)
    current = -1
    for idx in order:
        if tags[idx] == "full_doc":
            current += 1
        bundle_ids[idx] = max(current, 0)
    return bundle_ids


def short_query_uses_clause_model(word_count: int, num_clauses: int, length_limit: int) -> bool:
    if word_count < 0 or num_clauses < 1 or length_limit < 0:
        raise ValueError("word_count, num_clauses, and L must be non-negative; num_clauses >= 1")
    return int(word_count) <= int(length_limit) or int(num_clauses) == 1


def routed_surface_score(use_clause: bool, full_score: float, clause_score: float) -> float:
    return float(clause_score if use_clause else full_score)


def fail_closed_min(surface_score: float, payload_scores: np.ndarray | None) -> float:
    score = float(surface_score)
    if payload_scores is None:
        return score
    payload = np.asarray(payload_scores, dtype=np.float64)
    if payload.size == 0:
        return score
    return float(min(score, float(np.min(payload))))


def score_clears_threshold(score: float, threshold: float) -> bool:
    return float(score) >= float(threshold)


def gray_clause_count(clause_scores: np.ndarray, t_soft: float) -> int:
    cl = np.asarray(clause_scores, dtype=np.float64)
    return int(np.sum(cl < np.float64(t_soft)))


def passes_max_gray_count(
    full_score: float,
    clause_scores: np.ndarray,
    *,
    t_full: float,
    t_hard: float,
    t_soft: float,
    max_gray_count: int,
) -> bool:
    cl = np.asarray(clause_scores, dtype=np.float64)
    if cl.size == 0 or float(full_score) < float(t_full) or float(np.min(cl)) < float(t_hard):
        return False
    return gray_clause_count(cl, t_soft) <= int(max_gray_count)


def blend_full_min_clause(full_score: float, clause_scores: np.ndarray, w_f: float) -> float:
    cl = np.asarray(clause_scores, dtype=np.float64)
    w = np.float64(w_f)
    return float(w * np.float64(full_score) + (np.float64(1.0) - w) * np.float64(np.min(cl)))


def passes_blend_full_min_clause(
    full_score: float,
    clause_scores: np.ndarray,
    w_f: float,
    threshold: float,
) -> bool:
    return blend_full_min_clause(full_score, clause_scores, w_f) >= float(threshold)


def document_percentiles(
    cal_scores: np.ndarray,
    probs: Sequence[float] = DOC_PROBS,
) -> dict[float, float]:
    cal = np.asarray(cal_scores, dtype=np.float64)
    if cal.ndim != 1 or cal.size < 2:
        raise ValueError("percentile fit requires the calibration bundles")
    return {float(prob): float(np.quantile(cal, np.float64(prob), method="linear")) for prob in probs}


def document_stat_arrays(
    full_scores: np.ndarray,
    clause_lists: Sequence[np.ndarray],
    *,
    w_f: float = 0.5,
) -> dict[str, np.ndarray]:
    full = np.asarray(full_scores, dtype=np.float64)
    if len(clause_lists) != full.shape[0]:
        raise ValueError("clause lists do not align with full scores")
    n = full.shape[0]
    blend = np.empty(n, dtype=np.float64)
    p10_stat = np.empty(n, dtype=np.float64)
    hard = np.empty(n, dtype=np.float64)
    dual = np.empty(n, dtype=np.float64)
    w = np.float64(w_f)
    for i in range(n):
        cl = np.asarray(clause_lists[i], dtype=np.float64)
        if cl.size == 0:
            cl = np.array([full[i]], dtype=np.float64)
        cmin = np.float64(np.min(cl))
        blend[i] = w * full[i] + (np.float64(1.0) - w) * cmin
        p10_stat[i] = min(np.float64(full[i]), np.float64(np.quantile(cl, np.float64(0.10), method="linear")))
        hard[i] = min(np.float64(full[i]), cmin)
        order = np.sort(cl)
        bind = 1 if order.size > 1 else 0
        dual[i] = min(np.float64(full[i]), np.float64(order[bind]))
    return {
        "blend_full_min_clause": blend,
        "p10_clause_min_full": p10_stat,
        "hard_kill": hard,
        "dual_zone": dual,
    }


def dim_spec_all_coordinates(dim: int, neg_dims: np.ndarray) -> sim.DimSpec:
    neg = np.array([int(d) for d in np.asarray(neg_dims, dtype=np.int64).tolist()], dtype=np.int64)
    neg_set = set(neg.tolist())
    anchor = np.array([d for d in range(dim) if d not in neg_set], dtype=np.int64)
    if anchor.size == 0:
        weights = np.empty(0, dtype=np.float64)
    else:
        weights = np.full(anchor.size, np.float64(1.0) / np.float64(anchor.size), dtype=np.float64)
    if anchor.size + neg.size != dim:
        raise RuntimeError("coordinate partition is not exhaustive")
    return sim.DimSpec(
        active_dims=np.arange(dim, dtype=np.int64),
        anchor_dims=anchor,
        anchor_weights=weights,
        neg_sensor_dims=neg,
    )


def assign_repeated_stratified_folds(
    categories: Sequence[str],
    subtypes: Sequence[str],
    input_ids: Sequence[str],
    *,
    n_folds: int = 5,
    seed: int,
) -> np.ndarray:
    n = len(input_ids)
    if n != len(categories) or n != len(subtypes):
        raise ValueError("stratification fields differ in length")
    rng = np.random.Generator(np.random.PCG64(np.uint64(seed)))
    groups: dict[tuple[str, str], list[int]] = {}
    for i, (cat, sub) in enumerate(zip(categories, subtypes)):
        groups.setdefault((cat, sub), []).append(i)
    folds = np.empty(n, dtype=np.int64)
    for key in sorted(groups):
        idx = np.array(sorted(groups[key], key=lambda i: input_ids[i]), dtype=np.int64)
        shuffled = idx[rng.permutation(idx.size)]
        for pos, row in enumerate(shuffled.tolist()):
            folds[int(row)] = np.int64(pos % n_folds)
    return folds


def oof_fold_thresholds(
    scores: np.ndarray,
    y_true: np.ndarray,
    folds: np.ndarray,
    *,
    n_folds: int = 5,
) -> list[float]:
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(y_true, dtype=bool)
    fold_ids = np.asarray(folds, dtype=np.int64)
    thresholds: list[float] = []
    for fold in range(n_folds):
        train = fold_ids != fold
        if not np.any(train):
            raise RuntimeError("empty training fold")
        threshold, _ = sim.fit_best_1d_threshold(s[train], y[train])
        thresholds.append(float(threshold))
    return thresholds


def repeated_stratified_oof(
    scores: np.ndarray,
    y_true: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    input_ids: Sequence[str],
    *,
    seeds: Sequence[int] = REPEATED_SEEDS,
    n_folds: int = 5,
) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=bool)
    s = np.asarray(scores, dtype=np.float64)
    per_seed: list[dict[str, Any]] = []
    predictions: list[np.ndarray] = []
    f1s: list[float] = []
    frrs: list[float] = []
    fars: list[float] = []
    rocs: list[float] = []
    pr_in: list[float] = []
    pr_rej: list[float] = []
    oracle: dict[str, Any] | None = None
    for seed in seeds:
        folds = assign_repeated_stratified_folds(
            categories, subtypes, input_ids, n_folds=n_folds, seed=int(seed)
        )
        fitted = oof_fold_thresholds(s, y, folds, n_folds=n_folds)
        result = sim.evaluate_1d_oof_cv(s, y, folds)
        if result["fold_thresholds"] != fitted:
            raise RuntimeError("repeated OOF thresholds diverged from the train-only fit")
        metrics = result["oof_cv"]
        auc = sim.compute_auc_triple(y, s)
        if metrics["frr"] is None or metrics["far"] is None:
            raise RuntimeError("OOF metrics are missing a class")
        f1s.append(float(metrics["f1"]))
        frrs.append(float(metrics["frr"]))
        fars.append(float(metrics["far"]))
        rocs.append(float(auc["roc_auc"]))
        pr_in.append(float(auc["pr_auc_in_domain"]))
        pr_rej.append(float(auc["pr_auc_reject"]))
        predictions.append(np.array(result["oof_pred"], dtype=bool, copy=True))
        per_seed.append(
            {
                "seed": int(seed),
                "f1": float(metrics["f1"]),
                "frr": float(metrics["frr"]),
                "far": float(metrics["far"]),
                "roc_auc": float(auc["roc_auc"]),
                "pr_auc_in_domain": float(auc["pr_auc_in_domain"]),
                "pr_auc_reject": float(auc["pr_auc_reject"]),
                "fold_thresholds": fitted,
            }
        )
        if oracle is None:
            oracle_metrics = result["oracle_upper_bound"]
            oracle = {
                "tag": "[ORACLE_UPPER_BOUND]",
                "f1": float(oracle_metrics["f1"]),
                "frr": oracle_metrics["frr"],
                "far": oracle_metrics["far"],
                "threshold": float(oracle_metrics["threshold"]),
                "tp": int(oracle_metrics["tp"]),
                "fn": int(oracle_metrics["fn"]),
                "tn": int(oracle_metrics["tn"]),
                "fp": int(oracle_metrics["fp"]),
            }
    if oracle is None or oracle.get("tag") != "[ORACLE_UPPER_BOUND]":
        raise RuntimeError("missing oracle upper bound")

    def _pack(values: Sequence[float]) -> dict[str, float]:
        arr = np.array(list(values), dtype=np.float64)
        return {"mean": float(np.mean(arr)), "std": float(np.std(arr, ddof=1))}

    return {
        "seeds": [int(seed) for seed in seeds],
        "f1": _pack(f1s),
        "frr": _pack(frrs),
        "far": _pack(fars),
        "roc_auc": _pack(rocs),
        "pr_auc_in_domain": _pack(pr_in),
        "pr_auc_reject": _pack(pr_rej),
        "per_seed": per_seed,
        "predictions": predictions,
        "oracle_upper_bound": oracle,
        "f1_mean": float(np.mean(np.array(f1s, dtype=np.float64))),
        "f1_std": float(np.std(np.array(f1s, dtype=np.float64), ddof=1)),
    }


def bootstrap_stratified_ci(
    y_true: np.ndarray,
    scores: np.ndarray,
    predictions: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    *,
    seed: int,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    frozen_f1: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    if n_resamples < 2:
        raise ValueError("bootstrap needs at least two resamples")
    y = np.asarray(y_true, dtype=bool)
    s = np.asarray(scores, dtype=np.float64)
    pred = np.asarray(predictions, dtype=bool)
    if not (y.shape == s.shape == pred.shape and y.shape[0] == len(categories) == len(subtypes)):
        raise ValueError("bootstrap fields differ in length")
    rng = np.random.Generator(np.random.PCG64(np.uint64(seed)))
    groups: dict[tuple[str, str], list[int]] = {}
    for i, (cat, sub) in enumerate(zip(categories, subtypes)):
        groups.setdefault((cat, sub), []).append(i)
    index_groups = [np.array(groups[key], dtype=np.int64) for key in sorted(groups)]
    f1 = np.empty(n_resamples, dtype=np.float64)
    frr = np.empty(n_resamples, dtype=np.float64)
    far = np.empty(n_resamples, dtype=np.float64)
    roc = np.empty(n_resamples, dtype=np.float64)
    pr = np.empty(n_resamples, dtype=np.float64)
    for draw in range(n_resamples):
        parts = [rng.choice(group, size=group.size, replace=True) for group in index_groups]
        take = np.concatenate(parts)
        metrics = sim.compute_confusion_metrics(y[take], pred[take])
        if metrics["frr"] is None or metrics["far"] is None:
            raise RuntimeError("stratified bootstrap lost a class")
        auc = sim.compute_auc_triple(y[take], s[take])
        f1[draw] = np.float64(metrics["f1"])
        frr[draw] = np.float64(metrics["frr"])
        far[draw] = np.float64(metrics["far"])
        roc[draw] = np.float64(auc["roc_auc"])
        pr[draw] = np.float64(auc["pr_auc_in_domain"])

    def _ci(arr: np.ndarray) -> dict[str, float]:
        return {
            "low": float(np.quantile(arr, np.float64(0.025), method="linear")),
            "high": float(np.quantile(arr, np.float64(0.975), method="linear")),
        }

    out: dict[str, Any] = {
        "n_resamples": int(n_resamples),
        "seed": int(seed),
        "refits_thresholds": False,
        "f1": _ci(f1),
        "frr": _ci(frr),
        "far": _ci(far),
        "roc_auc": _ci(roc),
        "pr_auc_in_domain": _ci(pr),
    }
    if frozen_f1:
        deltas: dict[str, Any] = {}
        for name, frozen in frozen_f1.items():
            delta = f1 - np.float64(frozen)
            deltas[name] = {
                "point_bootstrap_mean_minus_frozen": float(np.mean(delta)),
                "ci95": _ci(delta),
            }
        out["delta_f1"] = deltas
    return out


def recipe_vector(channels: Mapping[str, Any], name: str) -> np.ndarray:
    f1 = channels["f1"]
    f2 = channels["f2"]
    f3 = channels["f3"]
    base = np.mean(np.stack((f1, f2, f3)), axis=0)
    if name == "base":
        return base
    if name in ("base_drop_primary", "base_consistency_primary"):
        return np.array(base, dtype=np.float64, copy=True)
    if name == "base_drop_secondary":
        return np.mean(np.stack((f1, f2, channels["f3_drop_secondary"])), axis=0)
    if name == "base_consistency_secondary":
        return base * channels["consistency_secondary"]
    if name == "polarity":
        return channels["polarity"]
    if name == "polarity_plus_base":
        return np.mean(np.stack((f1, f2, f3, channels["polarity"])), axis=0)
    if not name.startswith("tail_"):
        raise ValueError(f"unsupported recipe {name}")
    body = name[len("tail_") :]
    if body.endswith("_polarity_plus_base"):
        p = int(body[: -len("_polarity_plus_base")])
        return np.mean(np.stack((f1, f2, f3, channels["tail"][p], channels["polarity"])), axis=0)
    if body.endswith("_plus_base"):
        p = int(body[: -len("_plus_base")])
        return np.mean(np.stack((f1, f2, f3, channels["tail"][p])), axis=0)
    return channels["tail"][int(body)]


def parse_frozen_headlines(markdown: str) -> dict[tuple[str, str], dict[str, str]]:
    found: dict[tuple[str, str], dict[str, str]] = {}
    for line in markdown.splitlines():
        match = _HEADLINE_RE.search(line)
        if match is None:
            continue
        key = (match.group("domain"), match.group("granularity"))
        found[key] = {name: match.group(name) for name in FROZEN_HEADLINE[("python", "full_only")]}
    return found


def parse_frozen_subtypes(markdown: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    domain = ""
    granularity = ""
    for line in markdown.splitlines():
        header = _SECTION_RE.match(line)
        if header is not None:
            domain = header.group("domain")
            granularity = header.group("granularity")
            continue
        if not domain:
            continue
        match = _SUBTYPE_RE.match(line)
        if match is None:
            continue
        subtype = match.group("subtype")
        rows[(domain, granularity, subtype)] = {
            "category": match.group("category"),
            "kind": match.group("kind"),
            "n": int(match.group("n")),
            "task011_error": float(np.float64(match.group("task011")) / np.float64(100.0)),
            "task012_oof_error": float(np.float64(match.group("task012")) / np.float64(100.0)),
        }
    return rows


def verify_frozen_headlines(parsed: Mapping[tuple[str, str], Mapping[str, str]]) -> None:
    if set(parsed) != set(FROZEN_HEADLINE):
        raise RuntimeError(f"headline rows {sorted(parsed)} != frozen keys")
    for key, expected in FROZEN_HEADLINE.items():
        got = parsed[key]
        for field, value in expected.items():
            if got[field] != value:
                raise RuntimeError(f"{key} {field} parsed {got[field]} != frozen {value}")


def frozen_rates(row: Mapping[str, str]) -> dict[str, float]:
    return {
        "task011_f1": float(np.float64(row["task011_f1"])),
        "task011_frr": float(np.float64(row["task011_frr"]) / np.float64(100.0)),
        "task011_far": float(np.float64(row["task011_far"]) / np.float64(100.0)),
        "task012_f1": float(np.float64(row["task012_f1"])),
        "task012_frr": float(np.float64(row["task012_frr"]) / np.float64(100.0)),
        "task012_far": float(np.float64(row["task012_far"]) / np.float64(100.0)),
        "task012_roc_auc": float(np.float64(row["task012_roc"])),
        "task012_pr_auc_in_domain": float(np.float64(row["task012_pr_in"])),
        "task012_pr_auc_reject": float(np.float64(row["task012_pr_rej"])),
        "task012_cal05_f1": float(np.float64(row["task012_cal05_f1"])),
    }


def assert_xray_contract(xray: Mapping[str, Any]) -> None:
    if xray.get("mode") != "v2" or int(xray.get("dim", 0)) != sim.DIM:
        raise RuntimeError("xray payload is not the v2 1024-d report")
    locale = [int(d) for d in xray["prueba_a"]["locale_lang_dims"]]
    secondary = [int(d) for d in xray["prueba_a"]["secondary_band_dims"]]
    if locale != []:
        raise RuntimeError(f"primary LOCALE_LANG_DIMS is not empty: {locale}")
    if secondary != list(SECONDARY_BAND):
        raise RuntimeError(f"secondary band {secondary} != {list(SECONDARY_BAND)}")
    if language_lock_band(secondary, locale, secondary) != "secondary_band":
        raise RuntimeError("secondary band was labeled as the primary sweet spot")
    jaccard = xray["prueba_a"]["jaccard_top_k"]
    expected_jaccard = {"16": 1.0, "32": 0.939, "64": 1.0, "128": 0.969}
    for key, expected in expected_jaccard.items():
        if round(float(jaccard[key]), 3) != expected:
            raise RuntimeError(f"jaccard@{key} {jaccard[key]} does not round to {expected}")
    for domain, expected_counts in EXPECTED_FULL_BUCKETS.items():
        counts = xray["prueba_b"]["full_doc"]["1B_full"][domain]["bucket_counts"]
        got = tuple(int(counts[name]) for name in BUCKET_ORDER)
        if got != expected_counts:
            raise RuntimeError(f"{domain} 1B_full full_doc buckets {got} != {expected_counts}")
    hypothesis = xray["hypothesis_2_3"]
    py = hypothesis["python_vs_en_near_ood_neighbor"]
    es = hypothesis["receta_vs_es_near_ood_neighbor"]
    if int(py["sep_ge_1"]) != 16 or int(py["polarity_flip_count"]) != 96:
        raise RuntimeError("python hypothesis 2.3 counts do not match the recorded facts")
    if int(es["sep_ge_1"]) != 116 or int(es["polarity_flip_count"]) != 190:
        raise RuntimeError("receta hypothesis 2.3 counts do not match the recorded facts")
    if round(float(py["sep_median"]), 3) != 0.285 or round(float(py["sep_max"]), 3) != 1.596:
        raise RuntimeError("python hypothesis 2.3 sep summary does not match the recorded facts")
    if round(float(es["sep_median"]), 3) != 0.407 or round(float(es["sep_max"]), 3) != 2.207:
        raise RuntimeError("receta hypothesis 2.3 sep summary does not match the recorded facts")


def dials_from_classification(block: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    idx: list[int] = []
    mu: list[float] = []
    for row in block["dimensions"]:
        if row["bucket"] != "POLARITY_FLIP_DIALS":
            continue
        if float(row["sep"]) < 0.35 or float(row["mean_T"]) * float(row["mean_C"]) >= 0.0:
            continue
        if float(row["mean_T"]) == 0.0:
            continue
        idx.append(int(row["dim"]))
        mu.append(float(row["mean_T"]))
    if not idx:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    order = np.argsort(np.array(idx, dtype=np.int64), kind="mergesort")
    return np.array(idx, dtype=np.int64)[order], np.array(mu, dtype=np.float64)[order]


def neg_dims_from_classification(block: Mapping[str, Any]) -> np.ndarray:
    return np.array([int(d) for d in block["bucket_dims"]["NEGATIVE_INTRUDER_SENSOR"]], dtype=np.int64)


def bundle_mean_present(values: np.ndarray, bundle_ids: np.ndarray, n_bundles: int) -> np.ndarray:
    vals = np.asarray(values, dtype=np.float64)
    bids = np.asarray(bundle_ids, dtype=np.int64)
    if vals.shape[0] != bids.shape[0]:
        raise ValueError("bundle ids do not align with values")
    sums = np.zeros(n_bundles, dtype=np.float64)
    counts = np.zeros(n_bundles, dtype=np.float64)
    np.add.at(sums, bids, vals)
    np.add.at(counts, bids, np.float64(1.0))
    present = counts > 0.0
    if int(np.sum(present)) < 2:
        raise ValueError("need at least two calibration bundles to fit q90")
    return sums[present] / counts[present]


def geometry_raw(
    vectors: np.ndarray,
    box: sim.BoxStats,
    neg_dims: np.ndarray,
    secondary_dims: Sequence[int],
) -> dict[str, Any]:
    dim = int(vectors.shape[1])
    spec = dim_spec_all_coordinates(dim, neg_dims)
    if spec.active_dims.size != dim:
        raise RuntimeError("a coordinate was dropped from F1/F2")
    raw = sim.compute_raw_distances(vectors, box, spec)
    z = tail_z_rows(vectors, box.mean, box.std_sample)
    if z.shape[1] != dim:
        raise RuntimeError("Tail-Z dropped a coordinate")
    neg_set = set(int(d) for d in np.asarray(neg_dims, dtype=np.int64).tolist())
    sec = [int(d) for d in secondary_dims if int(d) not in neg_set]
    if sec:
        sec_idx = np.array(sec, dtype=np.int64)
        sec_terms = np.exp(
            -np.abs(vectors[:, sec_idx] - box.mean[sec_idx])
            / (np.float64(2.0) * box.std_sample[sec_idx] + sim.EPS_SIGMA)
        )
        sec_sum = np.sum(sec_terms, axis=1)
    else:
        sec_sum = np.zeros(vectors.shape[0], dtype=np.float64)
    return {
        "mean_e": raw["mean_e"],
        "z2": raw["z2"],
        "f3_pos": raw["f3_anchor"],
        "neg_penalty": raw["neg_penalty"],
        "tail": {p: worst_p_mean(z, p) for p in TAIL_PS},
        "sec_sum": sec_sum,
        "anchor_count": int(spec.anchor_dims.size),
        "sec_count": len(sec),
        "neg_count": int(np.asarray(neg_dims).size),
    }


def collect_oof_raw(
    vectors: np.ndarray,
    folds: np.ndarray,
    neg_dims: np.ndarray,
    secondary_dims: Sequence[int],
) -> dict[str, Any]:
    n = vectors.shape[0]
    acc: dict[str, Any] = {
        "mean_e": np.empty(n, dtype=np.float64),
        "z2": np.empty(n, dtype=np.float64),
        "f3_pos": np.empty(n, dtype=np.float64),
        "neg_penalty": np.empty(n, dtype=np.float64),
        "tail": {p: np.empty(n, dtype=np.float64) for p in TAIL_PS},
        "sec_sum": np.empty(n, dtype=np.float64),
    }
    meta: dict[str, int] | None = None
    seen = np.zeros(n, dtype=bool)
    for fold in range(5):
        train = folds != fold
        val = np.flatnonzero(folds == fold)
        if val.size == 0:
            continue
        if int(np.sum(train)) < 2:
            raise RuntimeError("calibration fold has fewer than 2 training rows")
        box = sim.box_stats_from_matrix(vectors[train])
        part = geometry_raw(vectors[val], box, neg_dims, secondary_dims)
        acc["mean_e"][val] = part["mean_e"]
        acc["z2"][val] = part["z2"]
        acc["f3_pos"][val] = part["f3_pos"]
        acc["neg_penalty"][val] = part["neg_penalty"]
        acc["sec_sum"][val] = part["sec_sum"]
        for p in TAIL_PS:
            acc["tail"][p][val] = part["tail"][p]
        seen[val] = True
        meta = {
            "anchor_count": int(part["anchor_count"]),
            "sec_count": int(part["sec_count"]),
            "neg_count": int(part["neg_count"]),
        }
    if meta is None or not np.all(seen):
        raise RuntimeError("OOF geometry left a calibration row unscored")
    acc.update(meta)
    return acc


def scales_from_oof(raw: Mapping[str, Any], bundle_ids: np.ndarray, n_bundles: int) -> dict[str, Any]:
    def _q(values: np.ndarray) -> float:
        return calibration_bundle_q90(bundle_mean_present(values, bundle_ids, n_bundles))

    neg_scale = _q(raw["neg_penalty"]) if int(raw["neg_count"]) else float(np.float64(1.0))
    return {
        "f1": _q(raw["mean_e"]),
        "f2": _q(raw["z2"]),
        "neg": neg_scale,
        "tail": {p: _q(raw["tail"][p]) for p in TAIL_PS},
    }


def map_raw_to_channels(
    raw: Mapping[str, Any],
    scales: Mapping[str, Any],
    vectors: np.ndarray,
    dial_idx: np.ndarray,
    dial_mu: np.ndarray,
    mu_en: np.ndarray,
    mu_es: np.ndarray,
    domain_lang: str,
    secondary_dims: Sequence[int],
) -> dict[str, Any]:
    n = int(raw["mean_e"].shape[0])
    f1 = np.exp(-raw["mean_e"] / np.float64(scales["f1"]))
    f2 = np.exp(-raw["z2"] / np.float64(scales["f2"]))
    if int(raw["neg_count"]) == 0:
        f3_neg = np.ones(n, dtype=np.float64)
    else:
        f3_neg = np.exp(-raw["neg_penalty"] / np.float64(scales["neg"]))
    f3 = np.float64(0.5) * raw["f3_pos"] + np.float64(0.5) * f3_neg
    sec_count = int(raw["sec_count"])
    anchor_count = int(raw["anchor_count"])
    if sec_count <= 0 or sec_count >= anchor_count:
        f3_drop = np.array(f3, dtype=np.float64, copy=True)
    else:
        pos_drop = (raw["f3_pos"] * np.float64(anchor_count) - raw["sec_sum"]) / np.float64(anchor_count - sec_count)
        pos_drop = np.clip(pos_drop, np.float64(0.0), np.float64(1.0))
        f3_drop = np.float64(0.5) * pos_drop + np.float64(0.5) * f3_neg
    if not np.all(np.isfinite(f1)) or not np.all(np.isfinite(f3_drop)):
        raise RuntimeError("non-finite factor")
    return {
        "f1": f1,
        "f2": f2,
        "f3": f3,
        "f3_drop_secondary": f3_drop,
        "tail": {p: map_tail_score(raw["tail"][p], scales["tail"][p]) for p in TAIL_PS},
        "polarity": polarity_score(vectors, dial_idx, dial_mu),
        "consistency_secondary": monolingual_consistency(vectors, secondary_dims, mu_en, mu_es, domain_lang),
        "sec_count": sec_count,
    }


def fit_and_score(
    cal_vectors: np.ndarray,
    cal_folds: np.ndarray,
    cal_bundle_ids: np.ndarray,
    n_bundles: int,
    score_vectors: np.ndarray,
    neg_dims: np.ndarray,
    secondary_dims: Sequence[int],
    dial_idx: np.ndarray,
    dial_mu: np.ndarray,
    mu_en: np.ndarray,
    mu_es: np.ndarray,
    domain_lang: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    oof_raw = collect_oof_raw(cal_vectors, cal_folds, neg_dims, secondary_dims)
    scales = scales_from_oof(oof_raw, cal_bundle_ids, n_bundles)
    box = sim.box_stats_from_matrix(cal_vectors)
    cal_ch = map_raw_to_channels(
        oof_raw, scales, cal_vectors, dial_idx, dial_mu, mu_en, mu_es, domain_lang, secondary_dims
    )
    hold_raw = geometry_raw(score_vectors, box, neg_dims, secondary_dims)
    hold_ch = map_raw_to_channels(
        hold_raw, scales, score_vectors, dial_idx, dial_mu, mu_en, mu_es, domain_lang, secondary_dims
    )
    return cal_ch, hold_ch, scales


def assemble_matched(strategies: Sequence[str], full_box_scores: np.ndarray, clause_box_scores: np.ndarray) -> np.ndarray:
    strat = np.asarray(list(strategies), dtype=object)
    out = np.empty(strat.shape[0], dtype=np.float64)
    is_full = strat == "full_doc"
    is_clause = strat == "clause_opt2c"
    if int(np.sum(is_full)) + int(np.sum(is_clause)) != strat.shape[0]:
        raise RuntimeError("unexpected chunk strategy in a normalize=true trace")
    out[is_full] = full_box_scores[is_full]
    out[is_clause] = clause_box_scores[is_clause]
    return out


def prompt_scores_from_chunks(
    bundle: sim.PromptBundle,
    chunk_scores: np.ndarray,
    *,
    cap24: bool = False,
    w_f: float = 0.5,
) -> tuple[np.ndarray, dict[str, Any]]:
    empty = {key: np.zeros(chunk_scores.size, dtype=bool) for key in ("K1", "K2", "K3", "any")}
    agg = sim.aggregate_prompt_signals(bundle, chunk_scores, empty, use_cap24=cap24)
    if bundle.granularity == "full_only":
        return agg["full_b64_min"], agg
    w = np.float64(w_f)
    return w * agg["full_b64_min"] + (np.float64(1.0) - w) * agg["clause_min"], agg


def routed_chunk_scores(
    bundle: sim.PromptBundle,
    matched_scores: np.ndarray,
    clause_box_scores: np.ndarray,
    route_mask: np.ndarray,
) -> np.ndarray:
    hybrid = np.array(matched_scores, dtype=np.float64, copy=True)
    for prompt in np.flatnonzero(route_mask):
        pieces = [int(bundle.full_chunk_idx[prompt])]
        pieces.extend(int(i) for i in bundle.b64_chunk_slices[prompt].tolist())
        pieces.extend(int(i) for i in bundle.clause_chunk_slices[prompt].tolist())
        idx = np.array(pieces, dtype=np.int64)
        hybrid[idx] = clause_box_scores[idx]
    return hybrid


def public_confusion(metrics: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("tp", "fn", "tn", "fp", "frr", "far", "f1", "precision", "recall", "accuracy"):
        value = metrics[key]
        if value is None:
            out[key] = None
        elif key in ("tp", "fn", "tn", "fp"):
            out[key] = int(value)
        else:
            out[key] = float(value)
    return out


def subgroup_error(y_pass: np.ndarray, pred_pass: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    if not np.any(mask):
        return {"n": 0, "kind": None, "error_rate": None}
    yt = y_pass[mask]
    yp = pred_pass[mask]
    n = int(yt.size)
    if bool(np.all(yt)):
        return {"n": n, "kind": "frr", "error_rate": float(np.mean(~yp))}
    if bool(np.all(~yt)):
        return {"n": n, "kind": "far", "error_rate": float(np.mean(yp))}
    metrics = sim.compute_confusion_metrics(yt, yp)
    return {"n": n, "kind": "f1", "error_rate": float(metrics["f1"])}


def rank_key(cell: Mapping[str, Any]) -> tuple[float, float, float]:
    frr = 0.0 if cell["oof_frr"] is None else float(cell["oof_frr"])
    far = 0.0 if cell["oof_far"] is None else float(cell["oof_far"])
    return (float(cell["oof_f1"]), float(cell["roc_auc"]), -(frr + far))


def _prob_tag(prob: float) -> str:
    return f"p{int(round(prob * 100)):02d}"


def cal_metrics_for_scores(
    cal_scores: np.ndarray,
    hold_scores: np.ndarray,
    y_true: np.ndarray,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    y = np.asarray(y_true, dtype=bool)
    hold = np.asarray(hold_scores, dtype=np.float64)
    for prob, threshold in document_percentiles(cal_scores).items():
        pred = hold >= np.float64(threshold)
        out[_prob_tag(prob)] = {**public_confusion(sim.compute_confusion_metrics(y, pred)), "threshold": float(threshold)}
    return out


def fit_gray_params(
    full: np.ndarray,
    clause_lists: Sequence[np.ndarray],
    y_true: np.ndarray,
    *,
    max_gray_count: int | None = None,
    max_gray_frac: float | None = None,
    n_grid: int = 5,
) -> dict[str, float]:
    if (max_gray_count is None) == (max_gray_frac is None):
        raise ValueError("set exactly one of max_gray_count or max_gray_frac")
    full_s = np.asarray(full, dtype=np.float64)
    y = np.asarray(y_true, dtype=bool)
    clauses = [np.asarray(cl, dtype=np.float64) for cl in clause_lists]
    mins = np.array([float(np.min(cl)) for cl in clauses], dtype=np.float64)
    pooled = np.concatenate(clauses) if clauses else np.zeros(1, dtype=np.float64)
    probs = np.linspace(0.05, 0.95, n_grid)
    t_fulls = np.unique(np.round(np.quantile(full_s, probs, method="linear"), 6))
    t_hards = np.unique(np.round(np.quantile(mins, probs, method="linear"), 6))
    t_softs = np.unique(np.round(np.quantile(pooled, probs, method="linear"), 6))
    lengths = np.array([max(cl.size, 1) for cl in clauses], dtype=np.float64)
    best_key = (-1.0, -1e9, -1e9)
    best = {"t_full": float(t_fulls[0]), "t_hard": float(t_hards[0]), "t_soft": float(t_softs[0])}
    for t_soft in t_softs:
        gray = np.array([int(np.sum(cl < t_soft)) for cl in clauses], dtype=np.int64)
        if max_gray_frac is not None:
            soft_ok = (gray / lengths) <= np.float64(max_gray_frac)
        else:
            soft_ok = gray <= int(max_gray_count)
        for t_hard in t_hards:
            if float(t_hard) > float(t_soft) + 1e-12:
                continue
            cl_ok = soft_ok & (mins >= np.float64(t_hard))
            for t_full in t_fulls:
                pred = (full_s >= np.float64(t_full)) & cl_ok
                metrics = sim.compute_confusion_metrics(y, pred)
                frr = 0.0 if metrics["frr"] is None else float(metrics["frr"])
                far = 0.0 if metrics["far"] is None else float(metrics["far"])
                key = (float(metrics["f1"]), -(frr + far), -float(t_full))
                if key > best_key:
                    best_key = key
                    best = {"t_full": float(t_full), "t_hard": float(t_hard), "t_soft": float(t_soft)}
    return best


def apply_gray_rule(
    full: np.ndarray,
    clause_lists: Sequence[np.ndarray],
    params: Mapping[str, float],
    *,
    max_gray_count: int | None = None,
    max_gray_frac: float | None = None,
) -> np.ndarray:
    pred = np.zeros(len(clause_lists), dtype=bool)
    t_full = float(params["t_full"])
    t_hard = float(params["t_hard"])
    t_soft = float(params["t_soft"])
    for i, raw in enumerate(clause_lists):
        cl = np.asarray(raw, dtype=np.float64)
        if float(full[i]) < t_full or float(np.min(cl)) < t_hard:
            continue
        if max_gray_count is not None and gray_clause_count(cl, t_soft) > int(max_gray_count):
            continue
        if max_gray_frac is not None and float(np.mean(cl < t_soft)) > float(max_gray_frac):
            continue
        pred[i] = True
    return pred


def gray_rule_oof(
    full: np.ndarray,
    clause_lists: Sequence[np.ndarray],
    y_true: np.ndarray,
    folds: np.ndarray,
    *,
    max_gray_count: int | None = None,
    max_gray_frac: float | None = None,
) -> tuple[np.ndarray, list[dict[str, float]]]:
    y = np.asarray(y_true, dtype=bool)
    pred = np.zeros(y.shape[0], dtype=bool)
    fold_params: list[dict[str, float]] = []
    for fold in range(5):
        train = np.flatnonzero(folds != fold)
        test = np.flatnonzero(folds == fold)
        train_lists = [clause_lists[int(i)] for i in train.tolist()]
        test_lists = [clause_lists[int(i)] for i in test.tolist()]
        params = fit_gray_params(
            full[train],
            train_lists,
            y[train],
            max_gray_count=max_gray_count,
            max_gray_frac=max_gray_frac,
        )
        fold_params.append(params)
        pred[test] = apply_gray_rule(
            full[test],
            test_lists,
            params,
            max_gray_count=max_gray_count,
            max_gray_frac=max_gray_frac,
        )
    return pred, fold_params


def load_benchmark_table(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_general_prose_language_means(path: Path) -> tuple[np.ndarray, np.ndarray]:
    from fhv1_1_xray import load_embedding_groups

    groups = load_embedding_groups(path, expected_dim=sim.DIM)
    en = groups[("en", "full_doc", "general_prose", True)]["vectors"]
    es = groups[("es", "full_doc", "general_prose", True)]["vectors"]
    if en.shape != (300, sim.DIM) or es.shape != (300, sim.DIM):
        raise RuntimeError(f"general_prose shapes en={en.shape} es={es.shape}")
    return np.mean(en, axis=0), np.mean(es, axis=0)


def load_calibration_documents(db: Any, profile_id: str, domain: str) -> dict[str, Any]:
    table = db.open_table("fhv1_calibration_samples")
    where = (
        f"profile_id = {sim._escape_sql(profile_id)} AND "
        "(strategy_tag = 'full_doc' OR strategy_tag = 'clause_opt2c')"
    )
    arrow = (
        table.search(None)
        .select(["sample_id", "strategy_tag", "source_ref", "vector"])
        .where(where)
        .limit(None)
        .to_arrow()
    )
    vectors = sim._arrow_fixed_list_to_float64(arrow["vector"], expected_dim=sim.DIM)
    sample_ids = [str(value) for value in arrow["sample_id"].to_pylist()]
    tags = [str(value) for value in arrow["strategy_tag"].to_pylist()]
    refs = [str(value) for value in arrow["source_ref"].to_pylist()]
    if set(refs) != {domain}:
        raise RuntimeError(f"{domain} calibration source_ref values are {sorted(set(refs))}")
    bundle_ids = assign_document_bundle_ids(sample_ids, tags)
    fold_check = sim.assign_calibration_folds(sample_ids, tags, refs, n_folds=5)
    if not np.array_equal(fold_check, bundle_ids % 5):
        raise RuntimeError("document bundles do not match assign_calibration_folds")
    n_bundles = int(np.max(bundle_ids)) + 1
    if n_bundles != 600:
        raise RuntimeError(f"{domain} bundle count {n_bundles} != 600")
    full_vectors = np.empty((n_bundles, sim.DIM), dtype=np.float64)
    seen = np.zeros(n_bundles, dtype=bool)
    clause_rows: list[int] = []
    clause_bundles: list[int] = []
    for i, tag in enumerate(tags):
        bid = int(bundle_ids[i])
        if tag == "full_doc":
            if seen[bid]:
                raise RuntimeError(f"duplicate full_doc in bundle {bid}")
            full_vectors[bid] = vectors[i]
            seen[bid] = True
        elif tag == "clause_opt2c":
            clause_rows.append(i)
            clause_bundles.append(bid)
    if not np.all(seen):
        raise RuntimeError(f"{domain} is missing a full_doc bundle")
    if len(clause_rows) != EXPECTED_CLAUSE_ROWS[domain]:
        raise RuntimeError(f"{domain} clause rows {len(clause_rows)} != {EXPECTED_CLAUSE_ROWS[domain]}")
    clause_ids = np.array(clause_rows, dtype=np.int64)
    clause_bundle_ids = np.array(clause_bundles, dtype=np.int64)
    lists: list[list[int]] = [[] for _ in range(n_bundles)]
    for row, bid in enumerate(clause_bundle_ids.tolist()):
        lists[int(bid)].append(row)
    return {
        "n_bundles": n_bundles,
        "full_vectors": full_vectors,
        "full_folds": np.arange(n_bundles, dtype=np.int64) % 5,
        "full_bundle_ids": np.arange(n_bundles, dtype=np.int64),
        "clause_vectors": vectors[clause_ids],
        "clause_folds": clause_bundle_ids % 5,
        "clause_bundle_ids": clause_bundle_ids,
        "clause_slices": [np.array(ix, dtype=np.int64) for ix in lists],
        "source_ref_is_policy_id": True,
    }


def prompt_features(texts: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    from fhv1_1_xray import segment_clauses_opt2c

    words = np.empty(len(texts), dtype=np.int64)
    clauses = np.empty(len(texts), dtype=np.int64)
    for i, text in enumerate(texts):
        words[i] = len(text.split())
        parts = segment_clauses_opt2c(text)
        clauses[i] = len(parts) if parts else 1
    return words, clauses


def _cell_public(cell: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in cell.items() if not str(key).startswith("_")}


def _mean_std_block(repeated: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "seeds": list(repeated["seeds"]),
        "f1": repeated["f1"],
        "frr": repeated["frr"],
        "far": repeated["far"],
        "roc_auc": repeated["roc_auc"],
        "pr_auc_in_domain": repeated["pr_auc_in_domain"],
        "pr_auc_reject": repeated["pr_auc_reject"],
        "oracle_upper_bound": repeated["oracle_upper_bound"],
    }


def _strip_predictions(repeated: Mapping[str, Any]) -> dict[str, Any]:
    per_seed = []
    for row in repeated["per_seed"]:
        per_seed.append({key: value for key, value in row.items() if key != "fold_thresholds"})
    return {**_mean_std_block(repeated), "per_seed": per_seed}


def breakout_block(
    y_true: np.ndarray,
    pred: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=bool)
    cats = np.asarray(list(categories), dtype=object)
    subs = np.asarray(list(subtypes), dtype=object)
    out: dict[str, Any] = {}
    for name in ("IN_DOMAIN_VALID", "HYBRID_BOUNDARY", "ADVERSARIAL_FUZZING", "OUT_OF_DOMAIN_BENIGN"):
        out[name] = subgroup_error(y, pred, cats == name)
    out["near_ood_neighbor"] = subgroup_error(y, pred, subs == "near_ood_neighbor")
    return out


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(key): to_jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(value) for value in obj]
    if isinstance(obj, np.ndarray):
        return to_jsonable(obj.tolist())
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _cal_clause_lists(clause_scores: np.ndarray, slices: Sequence[np.ndarray], full_scores: np.ndarray) -> list[np.ndarray]:
    lists: list[np.ndarray] = []
    for bundle, sl in enumerate(slices):
        if sl.size == 0:
            lists.append(np.array([full_scores[bundle]], dtype=np.float64))
        else:
            lists.append(np.asarray(clause_scores[sl], dtype=np.float64))
    return lists


def run_replay_v2(
    *,
    lancedb_uri: Path,
    benchmarks_dir: Path,
    xray_v2_path: Path,
    bg_parquet: Path,
    task012_report: Path,
    task011_report: Path,
) -> dict[str, Any]:
    import lancedb

    _log("loading xray v2 and frozen reports")
    xray = json.loads(xray_v2_path.read_text(encoding="utf-8"))
    assert_xray_contract(xray)
    task012_text = task012_report.read_text(encoding="utf-8")
    headlines = parse_frozen_headlines(task012_text)
    verify_frozen_headlines(headlines)
    published_subtypes = parse_frozen_subtypes(task012_text)
    if len(published_subtypes) < 148:
        raise RuntimeError(f"parsed {len(published_subtypes)} subtype rows, expected at least 148")
    task011_text = task011_report.read_text(encoding="utf-8")
    for row in FROZEN_HEADLINE.values():
        if row["task011_f1"] not in task011_text:
            raise RuntimeError(f"TASK-011 report is missing frozen F1 {row['task011_f1']}")
    frozen = {f"{dom}/{gran}": frozen_rates(row) for (dom, gran), row in FROZEN_HEADLINE.items()}
    mu_en, mu_es = load_general_prose_language_means(bg_parquet)
    secondary = list(SECONDARY_BAND)
    locale: list[int] = []
    db = lancedb.connect(str(lancedb_uri))
    runs = sim.load_lancedb_benchmark_runs(db)
    recipes = recipe_names()
    report: dict[str, Any] = {
        "mode": "v2",
        "dtype": "float64",
        "dim": sim.DIM,
        "normalize": True,
        "locale_lang_dims": locale,
        "secondary_band_dims": secondary,
        "secondary_band_label": "secondary_band",
        "secondary_band_called_primary_sweet_spot": False,
        "matches_recorded_facts": True,
        "f1_box_mode": "minmax",
        "primary_lock_identical_to_unlocked": True,
        "recorded_hypothesis_2_3": {
            "python_vs_en_near_ood_neighbor": {
                key: xray["hypothesis_2_3"]["python_vs_en_near_ood_neighbor"][key]
                for key in ("sep_ge_1", "sep_median", "sep_p90", "sep_max", "polarity_flip_count")
            },
            "receta_vs_es_near_ood_neighbor": {
                key: xray["hypothesis_2_3"]["receta_vs_es_near_ood_neighbor"][key]
                for key in ("sep_ge_1", "sep_median", "sep_p90", "sep_max", "polarity_flip_count")
            },
        },
        "frozen_reference": frozen,
        "frozen_source": {
            "task012_report": str(task012_report),
            "task011_report": str(task011_report),
            "note": "Headline F1/FRR/FAR are the published report strings. Deleted replay JSON was not reconstructed.",
        },
        "rigor": {
            "ranking": "one stratified 5-fold, seed 0, over signal recipes",
            "full_5x5_and_bootstrap": [],
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "bootstrap_seed": 0,
            "bootstrap_refits_thresholds": False,
            "seeds": list(REPEATED_SEEDS),
            "cells_with_seed0_only": "every non-winning recipe, every short-query L, and every long_context_flooding rule",
        },
        "domains": {},
        "sqlite_subprocess_json": {},
        "long_context_flooding": {},
    }
    all_subtype_keys: set[str] = set()
    winners: list[dict[str, Any]] = []

    for domain in ("python", "receta"):
        _log(f"loading {domain} calibration and holdout")
        profile_id = sim.V1_PROFILES[domain]
        calibration = load_calibration_documents(db, profile_id, domain)
        rows = load_benchmark_table(benchmarks_dir / f"{domain}.jsonl")
        text_map = {str(row["input_id"]): str(row["text"]) for row in rows}
        subtypes_map = {str(row["input_id"]): str(row["subtype"]) for row in rows}
        categories_map = {str(row["input_id"]): str(row["category"]) for row in rows}
        expected_map = {str(row["input_id"]): bool(row["expected_pass"]) for row in rows}
        all_subtype_keys.update(subtypes_map.values())
        domain_report: dict[str, Any] = {"granularities": {}}
        token_rows: dict[str, Any] = {}
        for gran in ("full_only", "clauses"):
            run = runs[(profile_id, gran, "m0")]
            bundle = sim.load_prompt_bundle(
                db,
                run["run_id"],
                gran,
                subtypes_map,
                categories_map,
                expected_map,
            )
            texts = [text_map[iid] for iid in bundle.input_ids]
            word_counts, clause_counts = prompt_features(texts)
            seed0_folds = assign_repeated_stratified_folds(
                bundle.categories, bundle.subtypes, bundle.input_ids, n_folds=5, seed=0
            )
            y = bundle.expected_pass
            contrast_reports: dict[str, Any] = {}
            prompt_bank: dict[tuple[str, str], np.ndarray] = {}
            channel_bank: dict[str, dict[str, dict[str, Any]]] = {}
            cal_bank: dict[str, dict[str, dict[str, np.ndarray]]] = {}
            scale_bank: dict[str, dict[str, Any]] = {}
            for contrast in CONTRASTS:
                _log(f"scoring {domain}/{gran}/{contrast}")
                full_block = xray["prueba_b"]["full_doc"][contrast][domain]
                clause_block = xray["prueba_b"]["clause_opt2c"][contrast][domain]
                full_dials = dials_from_classification(full_block)
                clause_dials = dials_from_classification(clause_block)
                full_neg = neg_dims_from_classification(full_block)
                clause_neg = neg_dims_from_classification(clause_block)
                cal_full_ch, hold_full_ch, full_scales = fit_and_score(
                    calibration["full_vectors"],
                    calibration["full_folds"],
                    calibration["full_bundle_ids"],
                    calibration["n_bundles"],
                    bundle.chunk_vectors,
                    full_neg,
                    secondary,
                    full_dials[0],
                    full_dials[1],
                    mu_en,
                    mu_es,
                    DOMAIN_LANG[domain],
                )
                cal_clause_ch, hold_clause_ch, clause_scales = fit_and_score(
                    calibration["clause_vectors"],
                    calibration["clause_folds"],
                    calibration["clause_bundle_ids"],
                    calibration["n_bundles"],
                    bundle.chunk_vectors,
                    clause_neg,
                    secondary,
                    clause_dials[0],
                    clause_dials[1],
                    mu_en,
                    mu_es,
                    DOMAIN_LANG[domain],
                )
                channel_bank[contrast] = {"full_box": hold_full_ch, "clause_box": hold_clause_ch}
                cal_bank[contrast] = {"full": cal_full_ch, "clause": cal_clause_ch}
                scale_bank[contrast] = {"full_doc": full_scales, "clause_opt2c": clause_scales}
                cells: list[dict[str, Any]] = []
                reference_breakouts: dict[str, Any] = {}
                for recipe in recipes:
                    full_vec = recipe_vector(hold_full_ch, recipe)
                    clause_vec = recipe_vector(hold_clause_ch, recipe)
                    matched = assemble_matched(bundle.chunk_strategies, full_vec, clause_vec)
                    prompt, _agg = prompt_scores_from_chunks(bundle, matched, cap24=False, w_f=0.5)
                    if recipe == "base":
                        primary_drop = recipe_vector(hold_full_ch, "base_drop_primary")
                        if not np.array_equal(full_vec, primary_drop):
                            raise RuntimeError("empty primary drop changed the full-box score")
                    oof = sim.evaluate_1d_oof_cv(prompt, y, seed0_folds)
                    auc = sim.compute_auc_triple(y, prompt)
                    metrics = oof["oof_cv"]
                    cal_full = recipe_vector(cal_full_ch, recipe)
                    cal_clause = recipe_vector(cal_clause_ch, recipe)
                    if gran == "full_only":
                        cal_stat = cal_full
                    else:
                        cal_lists = _cal_clause_lists(cal_clause, calibration["clause_slices"], cal_full)
                        cal_stat = document_stat_arrays(cal_full, cal_lists, w_f=0.5)["blend_full_min_clause"]
                    cal_only = cal_metrics_for_scores(cal_stat, prompt, y)
                    cell = {
                        "contrast": contrast,
                        "recipe": recipe,
                        "signals": signal_label(recipe),
                        "oof_f1": float(metrics["f1"]),
                        "oof_frr": None if metrics["frr"] is None else float(metrics["frr"]),
                        "oof_far": None if metrics["far"] is None else float(metrics["far"]),
                        "roc_auc": float(auc["roc_auc"]),
                        "pr_auc_in_domain": float(auc["pr_auc_in_domain"]),
                        "pr_auc_reject": float(auc["pr_auc_reject"]),
                        "generalization_gap_f1": float(oof["generalization_gap_f1"]),
                        "oracle_upper_bound": {
                            "tag": "[ORACLE_UPPER_BOUND]",
                            "f1": float(oof["oracle_upper_bound"]["f1"]),
                            "frr": oof["oracle_upper_bound"]["frr"],
                            "far": oof["oracle_upper_bound"]["far"],
                        },
                        "document_cal_only": cal_only,
                        "rigor": "seed0_5fold_only",
                        "_prompt": prompt,
                        "_matched": matched,
                        "_cal_full": cal_full,
                        "_cal_clause": cal_clause,
                    }
                    cells.append(cell)
                    prompt_bank[(contrast, recipe)] = prompt
                    if recipe in ("base", "polarity", "polarity_plus_base"):
                        reference_breakouts[recipe] = breakout_block(y, oof["oof_pred"], bundle.categories, bundle.subtypes)
                base_prompt = prompt_bank[(contrast, "base")]
                drop_prompt = prompt_bank[(contrast, "base_drop_primary")]
                cons_prompt = prompt_bank[(contrast, "base_consistency_primary")]
                if not np.array_equal(base_prompt, drop_prompt) or not np.array_equal(base_prompt, cons_prompt):
                    raise RuntimeError(f"{domain}/{gran}/{contrast} primary language-lock changed the score")
                sec_delta = float(np.max(np.abs(prompt_bank[(contrast, "base_drop_secondary")] - base_prompt)))
                sec_cons_delta = float(np.max(np.abs(prompt_bank[(contrast, "base_consistency_secondary")] - base_prompt)))
                contrast_reports[contrast] = {
                    "n_polarity_dials_full_doc": int(full_dials[0].size),
                    "n_polarity_dials_clause_opt2c": int(clause_dials[0].size),
                    "n_negative_sensors_full_doc": int(full_neg.size),
                    "n_negative_sensors_clause_opt2c": int(clause_neg.size),
                    "secondary_dims_in_positive_bonus_full": int(hold_full_ch["sec_count"]),
                    "secondary_dims_in_positive_bonus_clause": int(hold_clause_ch["sec_count"]),
                    "primary_lock_max_abs_delta": 0.0,
                    "secondary_drop_max_abs_delta": sec_delta,
                    "secondary_consistency_max_abs_delta": sec_cons_delta,
                    "scales_full_doc": {k: v for k, v in full_scales.items() if k != "tail"} | {"tail_q90": full_scales["tail"]},
                    "scales_clause_opt2c": {k: v for k, v in clause_scales.items() if k != "tail"} | {"tail_q90": clause_scales["tail"]},
                    "breakouts": reference_breakouts,
                    "sweep_seed0": [_cell_public(cell) for cell in sorted(cells, key=rank_key, reverse=True)],
                    "_cells": cells,
                }
            ranked = [cell for contrast in CONTRASTS for cell in contrast_reports[contrast]["_cells"]]
            named = sorted(ranked, key=lambda cell: (str(cell["contrast"]), str(cell["recipe"])))
            winner = max(named, key=rank_key)
            winner_contrast = str(winner["contrast"])
            winner_recipe = str(winner["recipe"])
            _log(f"winner {domain}/{gran} {winner_contrast} {winner_recipe} F1={winner['oof_f1']:.4f}")
            repeated = repeated_stratified_oof(
                winner["_prompt"], y, bundle.categories, bundle.subtypes, bundle.input_ids
            )
            if abs(float(repeated["per_seed"][0]["f1"]) - float(winner["oof_f1"])) > 0.0:
                raise RuntimeError("seed-0 repeated OOF does not reproduce the ranking fold")
            frozen_pair = {
                "task012": frozen[f"{domain}/{gran}"]["task012_f1"],
                "task011": frozen[f"{domain}/{gran}"]["task011_f1"],
            }
            boot = bootstrap_stratified_ci(
                y,
                winner["_prompt"],
                repeated["predictions"][0],
                bundle.categories,
                bundle.subtypes,
                seed=0,
                n_resamples=BOOTSTRAP_RESAMPLES,
                frozen_f1=frozen_pair,
            )
            point_delta = {
                name: float(np.float64(repeated["f1"]["mean"]) - np.float64(value))
                for name, value in frozen_pair.items()
            }
            cal_full = winner["_cal_full"]
            cal_clause = winner["_cal_clause"]
            cal_lists = _cal_clause_lists(cal_clause, calibration["clause_slices"], cal_full)
            cal_stats = document_stat_arrays(cal_full, cal_lists, w_f=0.5)
            _prompt, agg = prompt_scores_from_chunks(bundle, winner["_matched"], cap24=False, w_f=0.5)
            if gran == "clauses":
                hold_stats = document_stat_arrays(agg["full_b64_min"], agg["clause_arrays"], w_f=0.5)
                headline_name = "blend_full_min_clause"
                headline_hold = hold_stats[headline_name]
                headline_cal = cal_stats[headline_name]
            else:
                hold_stats = {"full_b64_min": agg["full_b64_min"]}
                headline_name = "full_b64_min"
                headline_hold = agg["full_b64_min"]
                headline_cal = cal_full
            document_table: dict[str, Any] = {}
            for name, cal_values in ({headline_name: headline_cal, **cal_stats}).items():
                if name not in hold_stats and name != headline_name:
                    if gran != "clauses":
                        document_table[name] = {
                            "calibration_percentiles": {
                                _prob_tag(prob): float(threshold)
                                for prob, threshold in document_percentiles(cal_values).items()
                            },
                            "holdout": "not applied; full_only prompts have no clause interval",
                        }
                        continue
                hold_values = hold_stats.get(name, headline_hold if name == headline_name else None)
                if hold_values is None:
                    continue
                document_table[name] = cal_metrics_for_scores(cal_values, hold_values, y)
            chunk_compare: dict[str, Any] = {}
            if gran == "clauses":
                cal_clause_rows = cal_clause
                hold_clause_min = np.array([float(np.min(cl)) for cl in agg["clause_arrays"]], dtype=np.float64)
                for prob in DOC_PROBS:
                    t_full = float(np.quantile(cal_full, np.float64(prob), method="linear"))
                    t_clause = float(np.quantile(cal_clause_rows, np.float64(prob), method="linear"))
                    pred = (agg["full_b64_min"] >= t_full) & (hold_clause_min >= t_clause)
                    doc_pred_threshold = document_percentiles(headline_cal)[prob]
                    doc_pred = headline_hold >= np.float64(doc_pred_threshold)
                    chunk_compare[_prob_tag(prob)] = {
                        "chunk_level_hard_kill": public_confusion(sim.compute_confusion_metrics(y, pred)),
                        "document_level": public_confusion(sim.compute_confusion_metrics(y, doc_pred)),
                        "chunk_thresholds": {"t_full": t_full, "t_clause": t_clause},
                        "document_threshold": float(doc_pred_threshold),
                    }
            else:
                for prob in DOC_PROBS:
                    threshold = float(document_percentiles(headline_cal)[prob])
                    pred = headline_hold >= np.float64(threshold)
                    metrics = public_confusion(sim.compute_confusion_metrics(y, pred))
                    chunk_compare[_prob_tag(prob)] = {
                        "chunk_level_hard_kill": metrics,
                        "document_level": metrics,
                        "document_threshold": threshold,
                        "note": "full_only has one score per document, so chunk-level and document-level share that threshold",
                    }
            short_rows: list[dict[str, Any]] = []
            for recipe_for_route in (winner_recipe, "base"):
                full_vec = recipe_vector(channel_bank[winner_contrast]["full_box"], recipe_for_route)
                clause_vec = recipe_vector(channel_bank[winner_contrast]["clause_box"], recipe_for_route)
                matched = assemble_matched(bundle.chunk_strategies, full_vec, clause_vec)
                unrouted, _ = prompt_scores_from_chunks(bundle, matched, cap24=False, w_f=0.5)
                unrouted_oof = sim.evaluate_1d_oof_cv(unrouted, y, seed0_folds)
                for limit in SHORT_LIMITS:
                    route = np.array(
                        [
                            short_query_uses_clause_model(int(word_counts[i]), int(clause_counts[i]), limit)
                            for i in range(word_counts.size)
                        ],
                        dtype=bool,
                    )
                    hybrid = routed_chunk_scores(bundle, matched, clause_vec, route)
                    routed, _ = prompt_scores_from_chunks(bundle, hybrid, cap24=False, w_f=0.5)
                    routed_oof = sim.evaluate_1d_oof_cv(routed, y, seed0_folds)
                    pred = routed_oof["oof_pred"]
                    short_rows.append(
                        {
                            "recipe": recipe_for_route,
                            "L": int(limit),
                            "n_routed": int(np.sum(route)),
                            "oof_f1": float(routed_oof["oof_cv"]["f1"]),
                            "delta_f1_vs_unrouted": float(routed_oof["oof_cv"]["f1"] - unrouted_oof["oof_cv"]["f1"]),
                            "short_idiom_query": subgroup_error(y, pred, np.array(bundle.subtypes) == "short_idiom_query"),
                            "consulta_corta": subgroup_error(y, pred, np.array(bundle.subtypes) == "consulta_corta"),
                            "extreme_short_punct": subgroup_error(y, pred, np.array(bundle.subtypes) == "extreme_short_punct"),
                            "obfuscation_base64": subgroup_error(y, pred, np.array(bundle.subtypes) == "obfuscation_base64"),
                            "rigor": "seed0_5fold_only",
                        }
                    )
            subtype_rows: list[dict[str, Any]] = []
            pred_cal = headline_hold >= np.float64(document_percentiles(headline_cal)[0.10])
            trace_pred = bundle.baseline_passed
            for subtype in sorted(set(bundle.subtypes)):
                mask = np.array(bundle.subtypes) == subtype
                published = published_subtypes.get((domain, gran, subtype))
                trace = subgroup_error(y, trace_pred, mask)
                if published is not None and trace["error_rate"] is not None:
                    if abs(float(published["task011_error"]) - float(trace["error_rate"])) > 5e-4:
                        raise RuntimeError(
                            f"{domain}/{gran}/{subtype} published TASK-011 {published['task011_error']} "
                            f"!= trace {trace['error_rate']}"
                        )
                oof_errs = []
                for pred_seed in repeated["predictions"]:
                    oof_errs.append(subgroup_error(y, pred_seed, mask)["error_rate"])
                err_arr = np.array(oof_errs, dtype=np.float64)
                subtype_rows.append(
                    {
                        "domain": domain,
                        "granularity": gran,
                        "subtype": subtype,
                        "n": int(np.sum(mask)),
                        "task011_published_error": None if published is None else float(published["task011_error"]),
                        "task011_trace_error": trace["error_rate"],
                        "task011_source": "published_report" if published is not None else "lancedb_m0_overall_passed",
                        "task012_published_oof_error": None if published is None else float(published["task012_oof_error"]),
                        "task013_document_cal_only_p10_error": subgroup_error(y, pred_cal, mask)["error_rate"],
                        "task013_repeated_oof_error_mean": float(np.mean(err_arr)),
                        "task013_repeated_oof_error_std": float(np.std(err_arr, ddof=1)),
                    }
                )
            best_public = {
                "domain": domain,
                "granularity": gran,
                "contrast": winner_contrast,
                "recipe": winner_recipe,
                "signals": signal_label(winner_recipe),
                "document_statistic": headline_name,
                "document_cal_only": document_table[headline_name],
                "repeated_oof_5x5": _strip_predictions(repeated),
                "bootstrap_95ci": {key: boot[key] for key in ("f1", "frr", "far", "roc_auc", "pr_auc_in_domain", "delta_f1")},
                "delta_f1_5x5_mean_minus_frozen": point_delta,
                "oracle_upper_bound": repeated["oracle_upper_bound"],
                "seed0_oof": {
                    "f1": winner["oof_f1"],
                    "frr": winner["oof_frr"],
                    "far": winner["oof_far"],
                    "roc_auc": winner["roc_auc"],
                    "pr_auc_in_domain": winner["pr_auc_in_domain"],
                    "pr_auc_reject": winner["pr_auc_reject"],
                },
            }
            report["rigor"]["full_5x5_and_bootstrap"].append(f"{domain}/{gran}/{winner_contrast}/{winner_recipe}")
            for contrast in CONTRASTS:
                contrast_reports[contrast].pop("_cells", None)
            domain_report["granularities"][gran] = {
                "n_prompts": int(len(bundle.input_ids)),
                "contrasts": contrast_reports,
                "best": best_public,
                "document_level_cal_only": document_table,
                "chunk_vs_document": chunk_compare,
                "short_query": short_rows,
                "subtype_table": subtype_rows,
                "breakouts_best_seed0": breakout_block(
                    y, repeated["predictions"][0], bundle.categories, bundle.subtypes
                ),
            }
            winners.append(best_public)
            if domain == "python":
                movement: dict[str, Any] = {"granularity": gran, "recipes": {}}
                token_mask = np.array(
                    [bool(_TOKEN_RE.search(text)) and cat == "IN_DOMAIN_VALID" for text, cat in zip(texts, bundle.categories)],
                    dtype=bool,
                )
                details = []
                for recipe in ("base", "polarity", "polarity_plus_base"):
                    score_base = prompt_bank[("1B_base_tech", recipe)]
                    score_full = prompt_bank[("1B_full", recipe)]
                    base_cell = next(c for c in ranked if c["contrast"] == "1B_base_tech" and c["recipe"] == recipe)
                    full_cell = next(c for c in ranked if c["contrast"] == "1B_full" and c["recipe"] == recipe)
                    t_base = float(base_cell["document_cal_only"]["p10"]["threshold"])
                    t_full = float(full_cell["document_cal_only"]["p10"]["threshold"])
                    d_base = score_base >= t_base
                    d_full = score_full >= t_full
                    delta = score_full - score_base
                    movement["recipes"][recipe] = {
                        "n": int(np.sum(token_mask)),
                        "n_score_moved": int(np.sum((delta != 0.0) & token_mask)),
                        "n_decision_moved": int(np.sum((d_base != d_full) & token_mask)),
                        "mean_delta_full_minus_base": float(np.mean(delta[token_mask])) if np.any(token_mask) else None,
                        "max_abs_delta": float(np.max(np.abs(delta[token_mask]))) if np.any(token_mask) else None,
                    }
                    if recipe == "polarity_plus_base":
                        for i in np.flatnonzero(token_mask):
                            found = sorted({tok.lower() for tok in _TOKEN_RE.findall(texts[int(i)])})
                            details.append(
                                {
                                    "input_id": bundle.input_ids[int(i)],
                                    "subtype": bundle.subtypes[int(i)],
                                    "tokens": found,
                                    "score_1B_base_tech": float(score_base[int(i)]),
                                    "score_1B_full": float(score_full[int(i)]),
                                    "delta": float(delta[int(i)]),
                                    "decision_1B_base_tech": bool(d_base[int(i)]),
                                    "decision_1B_full": bool(d_full[int(i)]),
                                }
                            )
                movement["prompts_polarity_plus_base"] = details
                token_rows[gran] = movement
            if domain == "python" and gran == "clauses":
                flood: dict[str, Any] = {"cap_policy": {}, "measured_note": "FAR is the false-accept rate on subtype long_context_flooding."}
                flood_mask = np.array(bundle.subtypes) == "long_context_flooding"
                for cap24 in (True, False):
                    _prompt_f, agg_f = prompt_scores_from_chunks(bundle, winner["_matched"], cap24=cap24, w_f=0.5)
                    full = agg_f["full_b64_min"]
                    lists = agg_f["clause_arrays"]
                    clause_min = np.array([float(np.min(cl)) for cl in lists], dtype=np.float64)
                    rules: list[dict[str, Any]] = []
                    for count in (0, 1, 2):
                        pred, _params = gray_rule_oof(
                            full, lists, y, seed0_folds, max_gray_count=count
                        )
                        rules.append(
                            {
                                "rule": "max_gray_count",
                                "max_gray_count": count,
                                "oof_f1": float(sim.compute_confusion_metrics(y, pred)["f1"]),
                                "long_context_flooding": subgroup_error(y, pred, flood_mask),
                                "rigor": "seed0_5fold_only",
                            }
                        )
                    pred_frac, _params = gray_rule_oof(full, lists, y, seed0_folds, max_gray_frac=0.35)
                    rules.append(
                        {
                            "rule": "max_gray_frac",
                            "max_gray_frac": 0.35,
                            "oof_f1": float(sim.compute_confusion_metrics(y, pred_frac)["f1"]),
                            "long_context_flooding": subgroup_error(y, pred_frac, flood_mask),
                            "rigor": "seed0_5fold_only",
                        }
                    )
                    for w_f in (0.3, 0.5, 0.7):
                        blend = np.float64(w_f) * full + (np.float64(1.0) - np.float64(w_f)) * clause_min
                        blend_oof = sim.evaluate_1d_oof_cv(blend, y, seed0_folds)
                        rules.append(
                            {
                                "rule": "blend_full_min_clause",
                                "w_f": w_f,
                                "oof_f1": float(blend_oof["oof_cv"]["f1"]),
                                "long_context_flooding": subgroup_error(y, blend_oof["oof_pred"], flood_mask),
                                "rigor": "seed0_5fold_only",
                            }
                        )
                    hard = sim.evaluate_2d_hard_kill_oof_cv(full, clause_min, y, seed0_folds)
                    rules.append(
                        {
                            "rule": "hard_kill",
                            "oof_f1": float(hard["oof_cv"]["f1"]),
                            "long_context_flooding": subgroup_error(y, hard["oof_pred"], flood_mask),
                            "rigor": "seed0_5fold_only",
                        }
                    )
                    flood["cap_policy"]["cap24" if cap24 else "uncapped"] = {
                        "evaluated_chunks": int(agg_f["evaluated_chunks"]),
                        "base64_fail_closed": True,
                        "cap24_index_rule": "8+8+8" if cap24 else None,
                        "rules": rules,
                    }
                report["long_context_flooding"] = {
                    "domain": "python",
                    "granularity": "clauses",
                    "score": f"{winner_contrast}/{winner_recipe}",
                    **flood,
                }
        domain_report["python_token_movement"] = token_rows
        report["domains"][domain] = domain_report
        if domain == "python":
            report["sqlite_subprocess_json"] = token_rows

    if len(all_subtype_keys) != 57:
        raise RuntimeError(f"subtype key count {len(all_subtype_keys)} != 57")
    report["subtype_key_count"] = len(all_subtype_keys)
    report["subtype_keys"] = sorted(all_subtype_keys)
    best_overall = max(winners, key=lambda row: float(row["repeated_oof_5x5"]["f1"]["mean"]))
    report["best_overall_by_repeated_f1"] = {
        "domain": best_overall["domain"],
        "granularity": best_overall["granularity"],
        "contrast": best_overall["contrast"],
        "recipe": best_overall["recipe"],
        "signals": best_overall["signals"],
    }
    encoded = to_jsonable(report)
    json.dumps(encoded, allow_nan=False)
    return encoded


def format_v2_summary(report: Mapping[str, Any]) -> str:
    lines = ["=== FHV1.1 v2 replay (1024D, normalize=true, float64) ==="]
    lines.append(
        "primary LOCALE_LANG_DIMS empty; secondary_band="
        + ",".join(str(d) for d in report["secondary_band_dims"])
    )
    lines.append("full 5x5+bootstrap: " + ", ".join(report["rigor"]["full_5x5_and_bootstrap"]))
    for domain in ("python", "receta"):
        for gran in ("full_only", "clauses"):
            best = report["domains"][domain]["granularities"][gran]["best"]
            cal = best["document_cal_only"]["p10"]
            rep = best["repeated_oof_5x5"]
            boot = best["bootstrap_95ci"]["f1"]
            delta = best["delta_f1_5x5_mean_minus_frozen"]["task012"]
            dboot = best["bootstrap_95ci"]["delta_f1"]["task012"]["ci95"]
            lines.append(
                f"[{domain}/{gran}] {best['contrast']} {best['signals']} "
                f"CAL_p10 F1={cal['f1']:.4f} FRR={cal['frr']:.4f} FAR={cal['far']:.4f} "
                f"5x5 F1={rep['f1']['mean']:.4f}±{rep['f1']['std']:.4f} "
                f"FRR={rep['frr']['mean']:.4f}±{rep['frr']['std']:.4f} "
                f"FAR={rep['far']['mean']:.4f}±{rep['far']['std']:.4f} "
                f"ROC={rep['roc_auc']['mean']:.4f}±{rep['roc_auc']['std']:.4f} "
                f"bootF1=[{boot['low']:.4f},{boot['high']:.4f}] "
                f"dF1_vs_TASK012={delta:+.4f} boot_dF1=[{dboot['low']:.4f},{dboot['high']:.4f}] "
                f"oracle_f1={best['oracle_upper_bound']['f1']:.4f} [ORACLE_UPPER_BOUND]"
            )
    tokens = report.get("sqlite_subprocess_json", {})
    for gran, block in tokens.items():
        pol = block["recipes"]["polarity_plus_base"]
        base = block["recipes"]["base"]
        lines.append(
            f"[python/{gran} tokens] n={pol['n']} polarity+base moved_scores={pol['n_score_moved']} "
            f"moved_decisions={pol['n_decision_moved']} mean_delta={pol['mean_delta_full_minus_base']} "
            f"base_moved_scores={base['n_score_moved']}"
        )
    flood = report.get("long_context_flooding", {})
    cap = flood.get("cap_policy", {}).get("cap24", {})
    for rule in cap.get("rules", []):
        measured = rule["long_context_flooding"]
        label = rule["rule"]
        if "max_gray_count" in rule:
            label += f"={rule['max_gray_count']}"
        if "max_gray_frac" in rule:
            label += f"={rule['max_gray_frac']}"
        if "w_f" in rule:
            label += f" w_f={rule['w_f']}"
        lines.append(
            f"[flood cap24 {label}] FAR={measured['error_rate']} n={measured['n']} OOF_F1={rule['oof_f1']:.4f}"
        )
    lines.append(f"subtype_keys={report['subtype_key_count']}")
    return "\n".join(lines)
