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
"""Phase 0 1A/1B and v2 read-only 1,024D X-ray analyzer for fhv1_1 (IEEE 754 float64)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import httpx
import lancedb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

DIM = 1024
EPS = 1e-12
ROGUE_DIMS: tuple[int, ...] = (292, 297, 308, 329, 386, 404, 577, 616, 780)
TOPK_SWEEP: tuple[int, ...] = (32, 64, 128, 256)

SUB_WINDOW = 10
SUB_STRIDE = 5
MAX_UNWINDOWED_WORDS = 14
CLAUSE_CONNECTORS: tuple[str, ...] = (
    " y de paso ",
    " außerdem ",
    " también ",
    " además ",
    " also ",
    " plus ",
    " pero ",
    " aber ",
    " and ",
    " but ",
    " und ",
    " or ",
    " y ",
    " o ",
)
_ASCII_WHITESPACE: frozenset[str] = frozenset((" ", "\t", "\n", "\r", "\x0c"))
_INVISIBLE_CONTROLS: frozenset[str] = frozenset(
    ("\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u00ad")
)
_HOMOGLYPH_MAP: dict[str, str] = {
    "\u0430": "a",
    "\u0441": "c",
    "\u0435": "e",
    "\u0456": "i",
    "\u0458": "j",
    "\u043e": "o",
    "\u0440": "p",
    "\u0455": "s",
    "\u0443": "y",
    "\u0445": "x",
    "\u0410": "A",
    "\u0412": "B",
    "\u0421": "C",
    "\u0415": "E",
    "\u041d": "H",
    "\u0406": "I",
    "\u0408": "J",
    "\u041a": "K",
    "\u041c": "M",
    "\u041e": "O",
    "\u0420": "P",
    "\u0405": "S",
    "\u0422": "T",
    "\u0425": "X",
    "\u03bf": "o",
    "\u03bd": "v",
    "\u03ba": "k",
    "\u03c1": "p",
    "\u0391": "A",
    "\u0392": "B",
    "\u0395": "E",
    "\u0396": "Z",
    "\u0397": "H",
    "\u0399": "I",
    "\u039a": "K",
    "\u039c": "M",
    "\u039d": "N",
    "\u039f": "O",
    "\u03a1": "P",
    "\u03a4": "T",
    "\u03a5": "Y",
    "\u03a7": "X",
}

V1_PROFILES: dict[str, str] = {
    "python": "python-v1-42270ed8870d",
    "receta": "receta-v1-5c820b9b36b3",
}
V2_PROFILES: dict[str, str] = {
    "python": "python-v2-42270ed8870d",
    "receta": "receta-v2-5c820b9b36b3",
}

GRANULARITIES: tuple[str, ...] = ("full_doc", "clause_opt2c", "pooled")
BUCKET_ORDER: tuple[str, ...] = (
    "BACKBONE_ENGINE",
    "FIRM_DOMAIN_ANCHOR",
    "NEGATIVE_INTRUDER_SENSOR",
    "DEAD_OR_OSCILLATOR",
)
V2_BUCKET_ORDER: tuple[str, ...] = (
    "BACKBONE_UNIVERSAL",
    "LOCALE_LANG_DIMS",
    "POLARITY_FLIP_DIALS",
    "FIRM_DOMAIN_ANCHOR",
    "NEGATIVE_INTRUDER_SENSOR",
    "SUBTLE_DISCRIMINATORS",
    "LOW_SIGNAL_NOISE",
)
V2_LANG_TOPK: tuple[int, ...] = (16, 32, 64, 128)
V2_BASE_STRATA: tuple[str, ...] = ("general_prose", "technical_structured")
V2_FULL_STRATA: tuple[str, ...] = ("general_prose", "technical_structured", "near_ood_neighbor")
V2_DOMAIN_LANG: dict[str, str] = {"python": "en", "receta": "es"}
V2_FULL_DOC_COUNTS: dict[tuple[str, str], int] = {
    ("en", "general_prose"): 300,
    ("es", "general_prose"): 300,
    ("en", "technical_structured"): 100,
    ("es", "technical_structured"): 100,
    ("en", "near_ood_neighbor"): 100,
    ("es", "near_ood_neighbor"): 100,
}
V2_CLAUSE_COUNTS: dict[tuple[str, str], int] = {
    ("en", "general_prose"): 1618,
    ("en", "technical_structured"): 835,
    ("en", "near_ood_neighbor"): 855,
    ("es", "general_prose"): 1661,
    ("es", "technical_structured"): 884,
    ("es", "near_ood_neighbor"): 791,
}
V2_CALIBRATION_CLAUSE_COUNTS: dict[str, int] = {"python": 3579, "receta": 4066}
NEG_SENSOR_ABS_MU_MAX_EXCLUSIVE = 0.015
NEG_SENSOR_SNR_MAX_EXCLUSIVE = 0.75
NEG_SENSOR_SEP_MIN = 1.0
NEG_SENSOR_INTRUDER_MIN = 1.8
BENCHMARK_CATEGORIES: tuple[str, ...] = (
    "IN_DOMAIN_VALID",
    "OUT_OF_DOMAIN_BENIGN",
    "HYBRID_BOUNDARY",
    "ADVERSARIAL_FUZZING",
)

BOX_RATIO_QUANTILES: tuple[tuple[str, float], ...] = (
    ("min", 0.0),
    ("p25", 0.25),
    ("median", 0.50),
    ("p75", 0.75),
    ("p90", 0.90),
    ("max", 1.0),
)
NORM_QUANTILES: tuple[tuple[str, float], ...] = (
    ("min", 0.0),
    ("p10", 0.10),
    ("p50", 0.50),
    ("p90", 0.90),
    ("max", 1.0),
)

CLASSIFICATION_THRESHOLDS: dict[str, Any] = {
    "ddof": 1,
    "eps": EPS,
    "classification_order": list(BUCKET_ORDER),
    "backbone_engine": {
        "snr_target_min": 1.5,
        "snr_contrast_min": 1.5,
        "same_sign_product_gt": 0.0,
        "sep_max_exclusive": 0.75,
        "rank_by": "min(snr_T, snr_C) desc",
    },
    "firm_domain_anchor": {
        "sep_min": 1.0,
        "snr_target_min_or_abs_mu_gt_contrast": 1.0,
        "rank_by": "sep desc",
    },
    "negative_intruder_sensor": {
        "abs_mu_target_max_exclusive": 0.015,
        "snr_target_max_exclusive": 0.75,
        "sep_min_or": 1.0,
        "intruder_ratio_min_or": 1.8,
        "rank_by": "max(sep, intruder_ratio) desc",
    },
    "dead_or_oscillator": {
        "rule": "remaining dimensions",
        "rank_by": "max(std_T, std_C) desc",
    },
}


@dataclass(frozen=True)
class CoordinateMoments:
    """Exact IEEE 754 float64 coordinate-wise moments for one sample matrix."""

    sample_count: int
    min: np.ndarray
    max: np.ndarray
    mean: np.ndarray
    span: np.ndarray
    variance_sample: np.ndarray
    variance_pop: np.ndarray
    std_dev_sample: np.ndarray
    std_dev_pop: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "min": self.min.tolist(),
            "max": self.max.tolist(),
            "mean": self.mean.tolist(),
            "span": self.span.tolist(),
            "variance_sample": self.variance_sample.tolist(),
            "variance_pop": self.variance_pop.tolist(),
            "std_dev_sample": self.std_dev_sample.tolist(),
            "std_dev_pop": self.std_dev_pop.tolist(),
        }


def _escape_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def compute_coordinate_moments(matrix: np.ndarray, expected_dim: int = DIM) -> CoordinateMoments:
    """Compute exact IEEE 754 float64 moments (ddof=1 and ddof=0) per dimension."""
    arr = np.asarray(matrix, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != expected_dim:
        raise ValueError(f"expected shape (N, {expected_dim}), got {arr.shape}")
    if arr.shape[0] < 2:
        raise ValueError(f"need at least 2 rows for ddof=1 moments, got {arr.shape[0]}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("non-finite coordinate detected in calibration matrix")

    min_v = np.min(arr, axis=0)
    max_v = np.max(arr, axis=0)
    mean_v = np.mean(arr, axis=0)
    span_v = max_v - min_v
    var_sample = np.var(arr, axis=0, ddof=1)
    var_pop = np.var(arr, axis=0, ddof=0)
    std_sample = np.sqrt(var_sample)
    std_pop = np.sqrt(var_pop)
    return CoordinateMoments(
        sample_count=int(arr.shape[0]),
        min=min_v,
        max=max_v,
        mean=mean_v,
        span=span_v,
        variance_sample=var_sample,
        variance_pop=var_pop,
        std_dev_sample=std_sample,
        std_dev_pop=std_pop,
    )


def summarize_distribution(
    values: np.ndarray,
    quantiles: tuple[tuple[str, float], ...],
    *,
    include_mean_std: bool = True,
) -> dict[str, Any]:
    """Summarize a 1D float64 vector with Hyndman-Fan type 7 linear quantiles."""
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"expected non-empty 1D array, got shape {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("non-finite value detected in distribution summary")

    probs = [q for _, q in quantiles]
    q_values = np.quantile(arr, probs, method="linear")
    summary: dict[str, Any] = {"count": int(arr.size)}
    for (label, _), val in zip(quantiles, q_values):
        summary[label] = float(val)
    if include_mean_std:
        summary["mean"] = float(np.mean(arr))
        summary["std_ddof1"] = float(np.std(arr, ddof=1)) if arr.size >= 2 else 0.0
        summary["std_ddof0"] = float(np.std(arr, ddof=0))
    return summary


def compute_box_inflation_metrics(
    full_doc: CoordinateMoments,
    clause: CoordinateMoments,
    pooled: CoordinateMoments,
    *,
    eps: float = EPS,
) -> dict[str, Any]:
    """Compute span and std-dev inflation distributions across granularities."""
    ratios = {
        "span_pooled_over_full_doc": pooled.span / (full_doc.span + eps),
        "span_pooled_over_clause": pooled.span / (clause.span + eps),
        "std_pooled_over_full_doc_ddof1": pooled.std_dev_sample / (full_doc.std_dev_sample + eps),
        "std_pooled_over_full_doc_ddof0": pooled.std_dev_pop / (full_doc.std_dev_pop + eps),
        "std_pooled_over_clause_ddof1": pooled.std_dev_sample / (clause.std_dev_sample + eps),
        "std_pooled_over_clause_ddof0": pooled.std_dev_pop / (clause.std_dev_pop + eps),
    }
    return {
        name: summarize_distribution(vec, BOX_RATIO_QUANTILES, include_mean_std=True)
        for name, vec in ratios.items()
    }


def compare_moments_against_stored(
    computed_pooled: CoordinateMoments,
    stored_profile: Mapping[str, Any],
) -> dict[str, float]:
    """Verify exact float64 parity between pooled moments and stored fhv1_profiles row."""
    checks: list[tuple[str, np.ndarray, str]] = [
        ("min_max_abs_diff", computed_pooled.min, "min_vector"),
        ("max_max_abs_diff", computed_pooled.max, "max_vector"),
        ("mean_max_abs_diff", computed_pooled.mean, "mean_vector"),
        ("span_max_abs_diff", computed_pooled.span, "span_vector"),
        ("variance_pop_max_abs_diff", computed_pooled.variance_pop, "variance_vector"),
        ("std_dev_pop_max_abs_diff", computed_pooled.std_dev_pop, "std_dev_vector"),
        ("std_dev_sample_vs_stored_max_abs_diff", computed_pooled.std_dev_sample, "std_dev_vector"),
    ]
    diffs: dict[str, float] = {}
    for out_key, computed_vec, stored_col in checks:
        stored_vec = np.asarray(stored_profile[stored_col], dtype=np.float64)
        if stored_vec.shape != computed_vec.shape:
            raise ValueError(
                f"stored {stored_col} shape {stored_vec.shape} != computed {computed_vec.shape}"
            )
        diffs[out_key] = float(np.max(np.abs(computed_vec - stored_vec)))
    return diffs


def coordinate_contrast_stats(
    mu_t: np.ndarray,
    std_t: np.ndarray,
    mu_c: np.ndarray,
    std_c: np.ndarray,
    *,
    eps: float = EPS,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return snr_T, snr_C, rms_T, rms_C, sep, and intruder_ratio in float64."""
    snr_t = np.abs(mu_t) / (std_t + eps)
    snr_c = np.abs(mu_c) / (std_c + eps)
    rms_t = np.sqrt(mu_t * mu_t + std_t * std_t)
    rms_c = np.sqrt(mu_c * mu_c + std_c * std_c)
    sep = np.abs(mu_t - mu_c) / (np.sqrt((std_t * std_t + std_c * std_c) / 2.0) + eps)
    intruder_ratio = rms_c / (rms_t + eps)
    return snr_t, snr_c, rms_t, rms_c, sep, intruder_ratio


def negative_intruder_mask(
    mu_t: np.ndarray,
    snr_t: np.ndarray,
    sep: np.ndarray,
    intruder_ratio: np.ndarray,
) -> np.ndarray:
    """Quiet near 0 on T and active on C by the mean-shift or variance-energy rule."""
    return (
        (np.abs(mu_t) < NEG_SENSOR_ABS_MU_MAX_EXCLUSIVE)
        & (snr_t < NEG_SENSOR_SNR_MAX_EXCLUSIVE)
        & ((sep >= NEG_SENSOR_SEP_MIN) | (intruder_ratio >= NEG_SENSOR_INTRUDER_MIN))
    )


def classify_dimensions(
    target_moments: CoordinateMoments,
    contrast_moments: CoordinateMoments,
    target_name: str,
    contrast_name: str,
    *,
    eps: float = EPS,
) -> dict[str, Any]:
    """Classify dimensions into 4 mutually exclusive buckets using ddof=1 moments."""
    mu_t = target_moments.mean
    sig_t = target_moments.std_dev_sample
    mu_c = contrast_moments.mean
    sig_c = contrast_moments.std_dev_sample
    if mu_t.shape != mu_c.shape:
        raise ValueError(f"dimension mismatch: {mu_t.shape} != {mu_c.shape}")

    dim_count = int(mu_t.shape[0])
    snr_t, snr_c, rms_t, rms_c, sep, intruder_ratio = coordinate_contrast_stats(
        mu_t, sig_t, mu_c, sig_c, eps=eps
    )
    neg_sensor_score = np.maximum(sep, intruder_ratio)

    is_backbone = (snr_t >= 1.5) & (snr_c >= 1.5) & ((mu_t * mu_c) > 0.0) & (sep < 0.75)
    is_anchor = (~is_backbone) & (sep >= 1.0) & ((snr_t >= 1.0) | (np.abs(mu_t) > np.abs(mu_c)))
    is_neg_sensor = (~is_backbone) & (~is_anchor) & negative_intruder_mask(
        mu_t, snr_t, sep, intruder_ratio
    )

    dimensions: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in BUCKET_ORDER}
    for d in range(dim_count):
        if bool(is_backbone[d]):
            bucket = "BACKBONE_ENGINE"
        elif bool(is_anchor[d]):
            bucket = "FIRM_DOMAIN_ANCHOR"
        elif bool(is_neg_sensor[d]):
            bucket = "NEGATIVE_INTRUDER_SENSOR"
        else:
            bucket = "DEAD_OR_OSCILLATOR"

        entry = {
            "dim": d,
            "bucket": bucket,
            "mean_T": float(mu_t[d]),
            "std_T": float(sig_t[d]),
            "mean_C": float(mu_c[d]),
            "std_C": float(sig_c[d]),
            "snr_T": float(snr_t[d]),
            "snr_C": float(snr_c[d]),
            "rms_T": float(rms_t[d]),
            "rms_C": float(rms_c[d]),
            "sep": float(sep[d]),
            "intruder_ratio": float(intruder_ratio[d]),
            "neg_sensor_score": float(neg_sensor_score[d]),
        }
        dimensions.append(entry)
        grouped[bucket].append(entry)

    rank_keys: dict[str, Callable[[dict[str, Any]], tuple[float, int]]] = {
        "BACKBONE_ENGINE": lambda r: (-min(r["snr_T"], r["snr_C"]), r["dim"]),
        "FIRM_DOMAIN_ANCHOR": lambda r: (-r["sep"], r["dim"]),
        "NEGATIVE_INTRUDER_SENSOR": lambda r: (-r["neg_sensor_score"], r["dim"]),
        "DEAD_OR_OSCILLATOR": lambda r: (-max(r["std_T"], r["std_C"]), r["dim"]),
    }

    bucket_counts: dict[str, int] = {}
    bucket_dims: dict[str, list[int]] = {}
    top20_by_bucket: dict[str, list[dict[str, Any]]] = {}
    for bucket in BUCKET_ORDER:
        ranked = sorted(grouped[bucket], key=rank_keys[bucket])
        bucket_counts[bucket] = len(ranked)
        bucket_dims[bucket] = [row["dim"] for row in ranked]
        top20_by_bucket[bucket] = ranked[:20]

    return {
        "target_policy": target_name,
        "contrast_policy": contrast_name,
        "target_sample_count": target_moments.sample_count,
        "contrast_sample_count": contrast_moments.sample_count,
        "dim_count": dim_count,
        "thresholds": CLASSIFICATION_THRESHOLDS,
        "bucket_counts": bucket_counts,
        "bucket_dims": bucket_dims,
        "top20_by_bucket": top20_by_bucket,
        "dimensions": dimensions,
    }


def build_rogue_dim_autopsy(
    py_moments: CoordinateMoments,
    rec_moments: CoordinateMoments,
    py_classification: Mapping[str, Any],
    rec_classification: Mapping[str, Any],
    rogue_dims: Sequence[int] = ROGUE_DIMS,
) -> list[dict[str, Any]]:
    """Build exact diagnostic rows for the 9 rogue dimensions."""
    py_dims = py_classification["dimensions"]
    rec_dims = rec_classification["dimensions"]
    rows: list[dict[str, Any]] = []
    for dim in rogue_dims:
        p = py_dims[dim]
        r = rec_dims[dim]
        rows.append(
            {
                "dim": int(dim),
                "mean_py": float(py_moments.mean[dim]),
                "std_py": float(py_moments.std_dev_sample[dim]),
                "mean_rec": float(rec_moments.mean[dim]),
                "std_rec": float(rec_moments.std_dev_sample[dim]),
                "sep": p["sep"],
                "snr_py": p["snr_T"],
                "snr_rec": r["snr_T"],
                "intruder_ratio_py": p["intruder_ratio"],
                "intruder_ratio_rec": r["intruder_ratio"],
                "bucket_python": p["bucket"],
                "bucket_receta": r["bucket"],
            }
        )
    return rows


def compute_roc_auc_trapezoidal(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Compute exact trapezoidal ROC-AUC in IEEE 754 float64 with tie grouping."""
    y = np.asarray(y_true, dtype=np.int64)
    scores = np.asarray(y_score, dtype=np.float64)
    if y.ndim != 1 or scores.ndim != 1 or y.size != scores.size:
        raise ValueError(f"mismatched shapes for ROC-AUC: {y.shape} vs {scores.shape}")
    if not np.all(np.isfinite(scores)):
        raise ValueError("non-finite score detected in ROC-AUC computation")
    if not np.all((y == 0) | (y == 1)):
        raise ValueError("y_true must contain only binary 0/1 labels")

    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    if n_pos == 0 or n_neg == 0:
        raise ValueError(f"ROC-AUC requires both classes; got n_pos={n_pos}, n_neg={n_neg}")

    order = np.argsort(-scores, kind="mergesort")
    y_sorted = y[order]
    s_sorted = scores[order]

    distinct_breaks = np.flatnonzero(np.diff(s_sorted))
    threshold_indices = np.concatenate((distinct_breaks, np.array([y_sorted.size - 1], dtype=np.int64)))
    tps = np.cumsum(y_sorted, dtype=np.float64)[threshold_indices]
    fps = (threshold_indices.astype(np.float64) + 1.0) - tps

    tpr = np.concatenate((np.array([0.0], dtype=np.float64), tps / float(n_pos)))
    fpr = np.concatenate((np.array([0.0], dtype=np.float64), fps / float(n_neg)))
    return float(np.sum((fpr[1:] - fpr[:-1]) * (tpr[1:] + tpr[:-1]) * 0.5))


def _evaluate_binary_auc_task(
    scores: np.ndarray,
    pos_mask: np.ndarray,
    neg_mask: np.ndarray,
) -> dict[str, Any]:
    subset_mask = pos_mask | neg_mask
    n_pos = int(np.sum(pos_mask))
    n_neg = int(np.sum(neg_mask))
    if n_pos == 0 or n_neg == 0:
        return {"n_pos": n_pos, "n_neg": n_neg, "roc_auc": None}
    y_sub = pos_mask[subset_mask].astype(np.int64)
    s_sub = scores[subset_mask]
    return {
        "n_pos": n_pos,
        "n_neg": n_neg,
        "roc_auc": compute_roc_auc_trapezoidal(y_sub, s_sub),
    }


def analyze_pre_l2_norms(
    cal_full_doc_vectors: np.ndarray,
    trace_rows: Sequence[Mapping[str, Any]],
    input_subtypes: Mapping[str, str],
) -> dict[str, Any]:
    """Evaluate pre-L2 ||x||_2 distribution and deviation ROC-AUC from calibration full_doc."""
    cal_arr = np.asarray(cal_full_doc_vectors, dtype=np.float64)
    if cal_arr.ndim != 2 or cal_arr.shape[0] == 0:
        raise ValueError(f"expected non-empty 2D calibration matrix, got {cal_arr.shape}")
    if not np.all(np.isfinite(cal_arr)):
        raise ValueError("non-finite coordinate detected in calibration pre-L2 matrix")

    cal_norms = np.linalg.norm(cal_arr, axis=1)
    cal_norm_mean = float(np.mean(cal_norms))
    cal_norm_std = float(np.std(cal_norms, ddof=1)) if cal_norms.size >= 2 else 0.0
    cal_summary = summarize_distribution(cal_norms, NORM_QUANTILES, include_mean_std=True)
    cal_summary["cal_norm_mean"] = cal_norm_mean
    cal_summary["cal_norm_std"] = cal_norm_std

    chunk0_rows = [row for row in trace_rows if int(row["chunk_index"]) == 0]
    decoded_rows = [row for row in trace_rows if int(row["chunk_index"]) > 0]
    if not chunk0_rows:
        raise ValueError("no chunk_index == 0 rows found in v2 trace_rows")

    vecs_c0 = np.asarray([row["input_vector"] for row in chunk0_rows], dtype=np.float64)
    if not np.all(np.isfinite(vecs_c0)):
        raise ValueError("non-finite coordinate detected in chunk0 trace vectors")
    norms_c0 = np.linalg.norm(vecs_c0, axis=1)
    scores_c0 = np.abs(norms_c0 - cal_norm_mean)

    cats_c0 = np.array([str(row["category"]) for row in chunk0_rows], dtype=object)
    subs_c0 = np.array([input_subtypes[str(row["input_id"])] for row in chunk0_rows], dtype=object)

    ordered_cats = [c for c in BENCHMARK_CATEGORIES if c in set(cats_c0.tolist())]
    for c in sorted(set(cats_c0.tolist())):
        if c not in ordered_cats:
            ordered_cats.append(c)

    by_category = {
        cat: summarize_distribution(norms_c0[cats_c0 == cat], NORM_QUANTILES, include_mean_std=True)
        for cat in ordered_cats
    }
    by_subtype = {
        sub: {
            "category": str(cats_c0[subs_c0 == sub][0]),
            **summarize_distribution(norms_c0[subs_c0 == sub], NORM_QUANTILES, include_mean_std=True),
        }
        for sub in sorted(set(subs_c0.tolist()))
    }

    in_domain_mask = cats_c0 == "IN_DOMAIN_VALID"
    roc_auc_tasks = {
        "non_in_domain_vs_in_domain": _evaluate_binary_auc_task(
            scores_c0, ~in_domain_mask, in_domain_mask
        ),
        "adversarial_vs_in_domain": _evaluate_binary_auc_task(
            scores_c0, cats_c0 == "ADVERSARIAL_FUZZING", in_domain_mask
        ),
        "extreme_short_punct_vs_in_domain": _evaluate_binary_auc_task(
            scores_c0, subs_c0 == "extreme_short_punct", in_domain_mask
        ),
        "extreme_high_entropy_gibberish_vs_in_domain": _evaluate_binary_auc_task(
            scores_c0, subs_c0 == "extreme_high_entropy_gibberish", in_domain_mask
        ),
        "extreme_short_punct_or_gibberish_vs_in_domain": _evaluate_binary_auc_task(
            scores_c0,
            (subs_c0 == "extreme_short_punct") | (subs_c0 == "extreme_high_entropy_gibberish"),
            in_domain_mask,
        ),
    }

    decoded_payload_section: dict[str, Any]
    if decoded_rows:
        vecs_dec = np.asarray([row["input_vector"] for row in decoded_rows], dtype=np.float64)
        norms_dec = np.linalg.norm(vecs_dec, axis=1)
        scores_dec = np.abs(norms_dec - cal_norm_mean)
        decoded_entries = []
        for idx, row in enumerate(decoded_rows):
            iid = str(row["input_id"])
            decoded_entries.append(
                {
                    "input_id": iid,
                    "category": str(row["category"]),
                    "subtype": input_subtypes[iid],
                    "chunk_index": int(row["chunk_index"]),
                    "chunk_strategy": str(row["chunk_strategy"]),
                    "l2_norm": float(norms_dec[idx]),
                    "abs_norm_deviation": float(scores_dec[idx]),
                }
            )
        decoded_payload_section = {
            "count": len(decoded_rows),
            "norm_distribution": summarize_distribution(norms_dec, NORM_QUANTILES, include_mean_std=True),
            "abs_deviation_distribution": summarize_distribution(
                scores_dec, NORM_QUANTILES, include_mean_std=True
            ),
            "rows": decoded_entries,
        }
    else:
        decoded_payload_section = {
            "count": 0,
            "norm_distribution": None,
            "abs_deviation_distribution": None,
            "rows": [],
        }

    return {
        "calibration_full_doc": cal_summary,
        "chunk0_prompt_count": len(chunk0_rows),
        "by_category": by_category,
        "by_subtype": by_subtype,
        "decoded_payload_chunk_gt0": decoded_payload_section,
        "roc_auc_abs_norm_deviation": roc_auc_tasks,
    }


def _arrow_fixed_list_to_float64(column: pa.ChunkedArray | pa.Array, expected_dim: int = DIM) -> np.ndarray:
    arr = column.combine_chunks() if isinstance(column, pa.ChunkedArray) else column
    n_rows = len(arr)
    if n_rows == 0:
        return np.empty((0, expected_dim), dtype=np.float64)
    if arr.null_count != 0:
        raise ValueError(f"unexpected nulls in vector column: {arr.null_count}")
    if not isinstance(arr, pa.FixedSizeListArray) or arr.type.list_size != expected_dim:
        raise ValueError(f"expected FixedSizeList[{expected_dim}], got {arr.type}")
    flat = arr.values.slice(arr.offset * expected_dim, n_rows * expected_dim).to_numpy(zero_copy_only=False)
    return np.asarray(flat, dtype=np.float64).reshape(n_rows, expected_dim)


def load_benchmark_subtypes(jsonl_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Load ONLY input_id -> (subtype, category) metadata for diagnostic v2 norm joins."""
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"missing benchmark jsonl: {jsonl_path}")
    subtypes: dict[str, str] = {}
    categories: dict[str, str] = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        obj = json.loads(trimmed)
        iid = str(obj["input_id"])
        subtypes[iid] = str(obj["subtype"])
        categories[iid] = str(obj["category"])
    return subtypes, categories


def load_lancedb_profile_row(db: lancedb.DBConnection, profile_id: str) -> dict[str, Any]:
    """Read one row from fhv1_profiles without mutating LanceDB."""
    table = db.open_table("fhv1_profiles")
    arrow = table.search(None).where(f"profile_id = {_escape_sql(profile_id)}").limit(None).to_arrow()
    if arrow.num_rows != 1:
        raise RuntimeError(f"expected 1 row in fhv1_profiles for {profile_id}, found {arrow.num_rows}")
    return {col: arrow[col][0].as_py() for col in arrow.column_names}


def load_lancedb_calibration_by_profile(
    db: lancedb.DBConnection,
    profile_id: str,
    *,
    strategy_tag: str | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Read calibration vectors and strategy tags from fhv1_calibration_samples."""
    table = db.open_table("fhv1_calibration_samples")
    where_clause = f"profile_id = {_escape_sql(profile_id)}"
    if strategy_tag is not None:
        where_clause += f" AND strategy_tag = {_escape_sql(strategy_tag)}"
    arrow = (
        table.search(None)
        .select(["strategy_tag", "vector"])
        .where(where_clause)
        .limit(None)
        .to_arrow()
    )
    vectors = _arrow_fixed_list_to_float64(arrow["vector"], expected_dim=DIM)
    tags = [str(v) for v in arrow["strategy_tag"].to_pylist()]
    return vectors, tags


def load_lancedb_v2_benchmark_traces(
    db: lancedb.DBConnection,
    profile_id: str,
) -> list[dict[str, Any]]:
    """Read BENCHMARK / full_only / use_rogue_mask=false traces for a v2 profile."""
    table = db.open_table("fhv1_audit_traces")
    where_clause = (
        f"profile_id = {_escape_sql(profile_id)} "
        "AND source_kind = 'BENCHMARK' "
        "AND eval_granularity = 'full_only' "
        "AND use_rogue_mask = false"
    )
    arrow = (
        table.search(None)
        .select(["input_id", "category", "chunk_index", "chunk_strategy", "input_vector"])
        .where(where_clause)
        .limit(None)
        .to_arrow()
    )
    vectors = _arrow_fixed_list_to_float64(arrow["input_vector"], expected_dim=DIM)
    input_ids = arrow["input_id"].to_pylist()
    categories = arrow["category"].to_pylist()
    chunk_indices = arrow["chunk_index"].to_pylist()
    chunk_strategies = arrow["chunk_strategy"].to_pylist()
    rows: list[dict[str, Any]] = []
    for idx in range(arrow.num_rows):
        rows.append(
            {
                "input_id": str(input_ids[idx]),
                "category": str(categories[idx]),
                "chunk_index": int(chunk_indices[idx]),
                "chunk_strategy": str(chunk_strategies[idx]),
                "input_vector": vectors[idx],
            }
        )
    return rows


def run_mode_1a(lancedb_uri: Path, benchmarks_dir: Path) -> dict[str, Any]:
    """Execute full Phase 0 1A read-only analysis across python-v1/receta-v1 and v2 norms."""
    db = lancedb.connect(str(lancedb_uri))

    v1_moments: dict[str, dict[str, CoordinateMoments]] = {}
    granularity_stats: dict[str, dict[str, Any]] = {}
    box_inflation: dict[str, Any] = {}
    stored_profile_parity: dict[str, dict[str, float]] = {}
    strategy_counts: dict[str, dict[str, int]] = {}
    profile_metadata: dict[str, dict[str, Any]] = {}

    for domain, pid in V1_PROFILES.items():
        stored = load_lancedb_profile_row(db, pid)
        if stored["policy_id"] != domain or stored["normalize"] is not True:
            raise RuntimeError(f"unexpected v1 profile metadata for {pid}")

        vectors, tags = load_lancedb_calibration_by_profile(db, pid)
        if vectors.shape[0] != int(stored["sample_count"]):
            raise RuntimeError(
                f"sample count mismatch for {pid}: {vectors.shape[0]} != {stored['sample_count']}"
            )

        tag_arr = np.array(tags, dtype=object)
        unique_tags, counts = np.unique(tag_arr, return_counts=True)
        strategy_counts[domain] = {str(t): int(c) for t, c in zip(unique_tags, counts)}

        full_moments = compute_coordinate_moments(vectors[tag_arr == "full_doc"])
        clause_moments = compute_coordinate_moments(vectors[tag_arr == "clause_opt2c"])
        pooled_moments = compute_coordinate_moments(vectors)

        v1_moments[domain] = {
            "full_doc": full_moments,
            "clause_opt2c": clause_moments,
            "pooled": pooled_moments,
        }
        granularity_stats[domain] = {
            gran: v1_moments[domain][gran].to_dict() for gran in GRANULARITIES
        }
        box_inflation[domain] = compute_box_inflation_metrics(
            full_moments, clause_moments, pooled_moments
        )
        stored_profile_parity[domain] = compare_moments_against_stored(pooled_moments, stored)
        profile_metadata[domain] = {
            "profile_id": pid,
            "policy_id": str(stored["policy_id"]),
            "version": int(stored["version"]),
            "normalize": bool(stored["normalize"]),
            "sample_count": int(stored["sample_count"]),
        }

    bucket_classification: dict[str, dict[str, Any]] = {}
    rogue_autopsy: dict[str, list[dict[str, Any]]] = {}
    for gran in ("full_doc", "clause_opt2c"):
        py_m = v1_moments["python"][gran]
        rec_m = v1_moments["receta"][gran]
        cls_py = classify_dimensions(py_m, rec_m, target_name="python", contrast_name="receta")
        cls_rec = classify_dimensions(rec_m, py_m, target_name="receta", contrast_name="python")
        bucket_classification[gran] = {
            "python_vs_receta": cls_py,
            "receta_vs_python": cls_rec,
        }
        rogue_autopsy[gran] = build_rogue_dim_autopsy(py_m, rec_m, cls_py, cls_rec)

    pre_l2_norms: dict[str, Any] = {}
    for domain, pid in V2_PROFILES.items():
        stored_v2 = load_lancedb_profile_row(db, pid)
        if stored_v2["policy_id"] != domain or stored_v2["normalize"] is not False:
            raise RuntimeError(f"unexpected v2 profile metadata for {pid}")

        cal_full_vecs, cal_tags = load_lancedb_calibration_by_profile(
            db, pid, strategy_tag="full_doc"
        )
        if len(cal_tags) != 600:
            raise RuntimeError(f"expected 600 full_doc calibration rows for {pid}, got {len(cal_tags)}")

        subtypes, bench_categories = load_benchmark_subtypes(benchmarks_dir / f"{domain}.jsonl")
        trace_rows = load_lancedb_v2_benchmark_traces(db, pid)
        for row in trace_rows:
            iid = row["input_id"]
            if bench_categories[iid] != row["category"]:
                raise RuntimeError(
                    f"category mismatch for {iid}: {row['category']} != {bench_categories[iid]}"
                )

        norm_report = analyze_pre_l2_norms(cal_full_vecs, trace_rows, subtypes)
        if norm_report["chunk0_prompt_count"] != 400:
            raise RuntimeError(
                f"expected 400 chunk0 traces for {pid}, got {norm_report['chunk0_prompt_count']}"
            )
        norm_report["profile_id"] = pid
        pre_l2_norms[domain] = norm_report

    return {
        "mode": "1a",
        "dtype": "float64",
        "dim": DIM,
        "rogue_dims": list(ROGUE_DIMS),
        "v1_profiles": profile_metadata,
        "calibration_strategy_counts": strategy_counts,
        "stored_profile_parity": stored_profile_parity,
        "granularity_stats": granularity_stats,
        "box_inflation": box_inflation,
        "classification_thresholds": CLASSIFICATION_THRESHOLDS,
        "bucket_classification": bucket_classification,
        "rogue_dim_autopsy": rogue_autopsy,
        "pre_l2_norm_check": pre_l2_norms,
    }


def format_stdout_summary(report: Mapping[str, Any]) -> str:
    """Render a compact, readable summary of key 1A diagnostic findings."""
    lines: list[str] = ["=== FHV1.1 Phase 0 1A X-Ray Summary (np.float64, 1024D) ==="]
    for domain in ("python", "receta"):
        parity = report["stored_profile_parity"][domain]
        infl = report["box_inflation"][domain]
        lines.append(
            f"[{domain}-v1] parity max_abs_diff: "
            f"min={parity['min_max_abs_diff']:.2e} max={parity['max_max_abs_diff']:.2e} "
            f"mean={parity['mean_max_abs_diff']:.2e} std_pop={parity['std_dev_pop_max_abs_diff']:.2e}"
        )
        for key in (
            "span_pooled_over_full_doc",
            "span_pooled_over_clause",
            "std_pooled_over_full_doc_ddof1",
            "std_pooled_over_full_doc_ddof0",
        ):
            d = infl[key]
            lines.append(
                f"  {key}: min={d['min']:.4f} p25={d['p25']:.4f} "
                f"med={d['median']:.4f} p75={d['p75']:.4f} p90={d['p90']:.4f} max={d['max']:.4f}"
            )

    for gran in ("full_doc", "clause_opt2c"):
        for pair in ("python_vs_receta", "receta_vs_python"):
            bc = report["bucket_classification"][gran][pair]["bucket_counts"]
            lines.append(f"[buckets {gran} {pair}] {bc}")

    for gran in ("full_doc", "clause_opt2c"):
        lines.append(f"[rogue 9 dims {gran}]")
        for r in report["rogue_dim_autopsy"][gran]:
            lines.append(
                f"  dim={r['dim']:3d} sep={r['sep']:.4f} "
                f"py=({r['mean_py']:+.5f}, {r['std_py']:.5f}, snr={r['snr_py']:.3f}, {r['bucket_python']}) "
                f"rec=({r['mean_rec']:+.5f}, {r['std_rec']:.5f}, snr={r['snr_rec']:.3f}, {r['bucket_receta']})"
            )

    for domain in ("python", "receta"):
        nrm = report["pre_l2_norm_check"][domain]
        cal = nrm["calibration_full_doc"]
        aucs = nrm["roc_auc_abs_norm_deviation"]
        lines.append(
            f"[{domain}-v2 ||x||_2] cal_full_doc mean={cal['cal_norm_mean']:.6f} std={cal['cal_norm_std']:.6f} "
            f"[{cal['min']:.4f}, {cal['max']:.4f}] decoded_gt0={nrm['decoded_payload_chunk_gt0']['count']}"
        )
        for k, v in aucs.items():
            lines.append(f"  roc_auc {k}: {v['roc_auc']:.6f} (pos={v['n_pos']}, neg={v['n_neg']})")

    return "\n".join(lines)


def normalize_input_text(raw_text: str) -> str:
    """Mirror crates/sf-proxy/src/normalizer.rs text cleaning and NFKC normalization."""
    cleaned = "".join(
        _HOMOGLYPH_MAP.get(ch, ch) for ch in raw_text if ch not in _INVISIBLE_CONTROLS
    )
    nfkc = unicodedata.normalize("NFKC", cleaned)
    return "".join(ch for ch in nfkc if ch not in _INVISIBLE_CONTROLS)


def _eq_ignore_case_char(left: str, right: str) -> bool:
    if left == right:
        return True
    if left.isascii() and right.isascii():
        return left.lower() == right.lower()
    left_low = left.lower()
    right_low = right.lower()
    return len(left_low) == 1 and len(right_low) == 1 and left_low == right_low


def _connector_len(prompt: str, index: int) -> int | None:
    remaining = len(prompt) - index
    for needle in CLAUSE_CONNECTORS:
        nlen = len(needle)
        if remaining < nlen:
            continue
        if all(_eq_ignore_case_char(prompt[index + k], needle[k]) for k in range(nlen)):
            return nlen
    return None


def _push_trimmed(out: list[str], prompt: str, start: int, end: int) -> None:
    if start >= end or end > len(prompt):
        return
    piece = prompt[start:end].strip()
    if piece:
        out.append(piece)


def _word_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    in_word = False
    word_start = 0
    for idx, ch in enumerate(text):
        if ch.isspace():
            if in_word:
                spans.append((word_start, idx))
                in_word = False
        elif not in_word:
            word_start = idx
            in_word = True
    if in_word:
        spans.append((word_start, len(text)))
    return spans


def _window_clause(clause: str, out: list[str]) -> None:
    spans = _word_spans(clause)
    if len(spans) <= MAX_UNWINDOWED_WORDS:
        out.append(clause)
        return
    start_idx = 0
    while start_idx < len(spans):
        end = min(start_idx + SUB_WINDOW, len(spans))
        out.append(clause[spans[start_idx][0] : spans[end - 1][1]])
        if end == len(spans):
            break
        start_idx += SUB_STRIDE


def segment_clauses_opt2c(text: str) -> list[str]:
    """Segment NFKC-normalized text identically to crates/sf-proxy/src/segmenter.rs."""
    prompt = normalize_input_text(text)
    raw: list[str] = []
    start = 0
    i = 0
    n = len(prompt)
    while i < n:
        if prompt.startswith('"""', i) or prompt.startswith("'''", i):
            _push_trimmed(raw, prompt, start, i)
            i += 3
            start = i
            continue
        if prompt.startswith("/*", i) or prompt.startswith("*/", i) or prompt.startswith("//", i):
            _push_trimmed(raw, prompt, start, i)
            i += 2
            start = i
            continue
        if prompt[i] == " ":
            clen = _connector_len(prompt, i)
            if clen is not None:
                _push_trimmed(raw, prompt, start, i)
                i += clen
                start = i
                continue
        ch = prompt[i]
        punct = (
            ch in ("\n", "\r", ";", ",", "#")
            or (
                ch in (".", "!", "?")
                and (i + 1 == n or prompt[i + 1] in _ASCII_WHITESPACE)
            )
        )
        if punct:
            _push_trimmed(raw, prompt, start, i)
            start = i + 1
        i += 1
    _push_trimmed(raw, prompt, start, n)

    clauses: list[str] = []
    for clause in raw:
        _window_clause(clause, clauses)
    if not clauses:
        trimmed = prompt.strip()
        if trimmed:
            clauses.append(trimmed)
    return clauses


def _text_sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_background_corpus(corpus_path: Path) -> list[dict[str, Any]]:
    """Read background JSONL rows preserving order and validating required keys."""
    if not corpus_path.is_file():
        raise FileNotFoundError(f"missing background corpus jsonl: {corpus_path}")
    rows: list[dict[str, Any]] = []
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        obj = json.loads(trimmed)
        row = {
            "id": str(obj["id"]),
            "lang": str(obj["lang"]),
            "topic": str(obj["topic"]),
            "text": str(obj["text"]),
        }
        if obj.get("stratum") is not None:
            row["stratum"] = str(obj["stratum"])
        rows.append(row)
    if not rows:
        raise ValueError(f"empty background corpus: {corpus_path}")
    return rows


def build_background_embedding_rows(corpus_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build normalized full_doc (norm=T/F) and per-(lang, sha256) deduplicated clause_opt2c rows."""
    full_doc_entries: list[dict[str, Any]] = []
    clause_entries: list[dict[str, Any]] = []
    seen_clauses: set[tuple[str, str]] = set()

    for doc in corpus_rows:
        doc_id = str(doc["id"])
        lang = str(doc["lang"])
        topic = str(doc["topic"])
        stratum = str(doc.get("stratum", ""))
        norm_text = normalize_input_text(str(doc["text"])).strip()
        if not norm_text:
            raise ValueError(f"empty normalized text for {doc_id}")
        full_doc_entries.append(
            {
                "doc_id": doc_id,
                "lang": lang,
                "topic": topic,
                "stratum": stratum,
                "granularity": "full_doc",
                "chunk_index": 0,
                "normalize": True,
                "text": norm_text,
                "text_sha256": _text_sha256_hex(norm_text),
            }
        )
        for chunk_idx, clause in enumerate(segment_clauses_opt2c(norm_text)):
            c_trimmed = clause.strip()
            if not c_trimmed:
                continue
            digest = _text_sha256_hex(c_trimmed)
            if (lang, digest) in seen_clauses:
                continue
            seen_clauses.add((lang, digest))
            clause_entries.append(
                {
                    "doc_id": doc_id,
                    "lang": lang,
                    "topic": topic,
                    "stratum": stratum,
                    "granularity": "clause_opt2c",
                    "chunk_index": chunk_idx,
                    "normalize": True,
                    "text": c_trimmed,
                    "text_sha256": digest,
                }
            )

    unnorm_full_entries = [{**row, "normalize": False} for row in full_doc_entries]
    return [*full_doc_entries, *clause_entries, *unnorm_full_entries]


def _embed_batches_loopback(
    client: httpx.Client,
    embed_url: str,
    texts: Sequence[str],
    *,
    normalize: bool,
    batch_size: int,
    expected_dim: int = DIM,
) -> np.ndarray:
    if not texts:
        return np.empty((0, expected_dim), dtype=np.float64)
    chunks: list[np.ndarray] = []
    endpoint = embed_url.rstrip("/") + "/embed"
    for start in range(0, len(texts), batch_size):
        batch = list(texts[start : start + batch_size])
        resp = client.post(
            endpoint,
            json={"inputs": batch, "truncate": True, "normalize": normalize},
        )
        resp.raise_for_status()
        arr = np.asarray(resp.json(), dtype=np.float64)
        if arr.shape != (len(batch), expected_dim):
            raise RuntimeError(
                f"embedder returned shape {arr.shape}, expected {(len(batch), expected_dim)}"
            )
        if not np.all(np.isfinite(arr)):
            raise RuntimeError("embedder returned non-finite coordinate")
        norms = np.linalg.norm(arr, axis=1)
        if normalize and np.max(np.abs(norms - 1.0)) > 1e-3:
            raise RuntimeError(f"normalize=true violated unit L2: max diff={np.max(np.abs(norms - 1.0))}")
        if not normalize and np.min(norms) <= 1.5:
            raise RuntimeError(f"normalize=false unexpectedly near unit norm: min={np.min(norms)}")
        chunks.append(arr)
    return np.vstack(chunks)


def write_background_embeddings_parquet(
    rows: Sequence[Mapping[str, Any]],
    vectors: np.ndarray,
    out_path: Path,
    *,
    expected_dim: int = DIM,
) -> None:
    """Persist background embeddings as FixedSizeList[float64, 1024] Parquet."""
    vec_arr = np.asarray(vectors, dtype=np.float64)
    if vec_arr.ndim != 2 or vec_arr.shape != (len(rows), expected_dim):
        raise ValueError(f"vector matrix shape {vec_arr.shape} != {(len(rows), expected_dim)}")
    schema = pa.schema(
        [
            pa.field("doc_id", pa.string(), nullable=False),
            pa.field("lang", pa.string(), nullable=False),
            pa.field("topic", pa.string(), nullable=False),
            pa.field("stratum", pa.string(), nullable=False),
            pa.field("granularity", pa.string(), nullable=False),
            pa.field("chunk_index", pa.int64(), nullable=False),
            pa.field("normalize", pa.bool_(), nullable=False),
            pa.field("text", pa.string(), nullable=False),
            pa.field("text_sha256", pa.string(), nullable=False),
            pa.field("vector", pa.list_(pa.float64(), expected_dim), nullable=False),
        ]
    )
    vec_list = pa.FixedSizeListArray.from_arrays(
        pa.array(np.ascontiguousarray(vec_arr).reshape(-1), type=pa.float64()),
        expected_dim,
    )
    table = pa.table(
        {
            "doc_id": pa.array([str(r["doc_id"]) for r in rows], type=pa.string()),
            "lang": pa.array([str(r["lang"]) for r in rows], type=pa.string()),
            "topic": pa.array([str(r["topic"]) for r in rows], type=pa.string()),
            "stratum": pa.array([str(r.get("stratum", "")) for r in rows], type=pa.string()),
            "granularity": pa.array([str(r["granularity"]) for r in rows], type=pa.string()),
            "chunk_index": pa.array([int(r["chunk_index"]) for r in rows], type=pa.int64()),
            "normalize": pa.array([bool(r["normalize"]) for r in rows], type=pa.bool_()),
            "text": pa.array([str(r["text"]) for r in rows], type=pa.string()),
            "text_sha256": pa.array([str(r["text_sha256"]) for r in rows], type=pa.string()),
            "vector": vec_list,
        },
        schema=schema,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(out_path))


def run_mode_embed_bg(
    bg_corpus_path: Path,
    bg_out_path: Path,
    embed_url: str,
    *,
    batch_size: int = 32,
    unnorm_out_path: Path | None = None,
) -> dict[str, Any]:
    """Embed background corpus on local BGE-M3.

    The primary parquet stores normalize=true rows only (full_doc plus deduped
    clause_opt2c). normalize=false is persisted only for general_prose full_doc
    rows, and only when unnorm_out_path is set.
    """
    corpus_rows = load_background_corpus(bg_corpus_path)
    all_rows = build_background_embedding_rows(corpus_rows)

    norm_rows = [r for r in all_rows if r["normalize"] is True]
    unnorm_rows = [
        r
        for r in all_rows
        if r["normalize"] is False
        and r["granularity"] == "full_doc"
        and str(r.get("stratum", "")) == "general_prose"
    ]

    with httpx.Client(timeout=120.0, trust_env=False) as client:
        health_resp = client.get(embed_url.rstrip("/") + "/health")
        health_resp.raise_for_status()
        health = health_resp.json()
        if health.get("status") != "ok" or int(health.get("dim", 0)) != DIM:
            raise RuntimeError(f"unexpected embedder health response: {health}")

        vecs_norm = _embed_batches_loopback(
            client,
            embed_url,
            [r["text"] for r in norm_rows],
            normalize=True,
            batch_size=batch_size,
        )
        vecs_unnorm = _embed_batches_loopback(
            client,
            embed_url,
            [r["text"] for r in unnorm_rows],
            normalize=False,
            batch_size=batch_size,
        )

    write_background_embeddings_parquet(norm_rows, vecs_norm, bg_out_path)
    if unnorm_out_path is not None:
        write_background_embeddings_parquet(unnorm_rows, vecs_unnorm, unnorm_out_path)

    counts_by_slice: dict[str, int] = {}
    for row in norm_rows:
        key = f"{row['lang']}:{row['granularity']}:norm={row['normalize']}"
        counts_by_slice[key] = counts_by_slice.get(key, 0) + 1

    unnorm_counts: dict[str, int] = {}
    for row in unnorm_rows:
        key = f"{row['lang']}:{row['granularity']}:norm={row['normalize']}"
        unnorm_counts[key] = unnorm_counts.get(key, 0) + 1

    unnorm_norms = np.linalg.norm(vecs_unnorm, axis=1) if len(unnorm_rows) else np.empty((0,), dtype=np.float64)
    langs_unnorm = np.array([r["lang"] for r in unnorm_rows], dtype=object)
    summary: dict[str, Any] = {
        "mode": "embed-bg",
        "embed_url": embed_url,
        "health": health,
        "corpus_docs": len(corpus_rows),
        "total_rows_written": len(norm_rows),
        "counts_by_slice": counts_by_slice,
        "pre_l2_norms": {
            lang: summarize_distribution(
                unnorm_norms[langs_unnorm == lang], NORM_QUANTILES, include_mean_std=True
            )
            for lang in ("en", "es")
            if np.any(langs_unnorm == lang)
        },
        "out_path": str(bg_out_path),
        "unnorm_rows_written": len(unnorm_rows),
        "unnorm_counts_by_slice": unnorm_counts,
    }
    if unnorm_out_path is not None:
        summary["unnorm_out_path"] = str(unnorm_out_path)
    return summary


def moments_from_dict(data: Mapping[str, Any], expected_dim: int = DIM) -> CoordinateMoments:
    """Reconstruct exact float64 CoordinateMoments from serialized xray_1a granularity_stats."""
    def _vec(key: str) -> np.ndarray:
        arr = np.asarray(data[key], dtype=np.float64)
        if arr.shape != (expected_dim,):
            raise ValueError(f"{key} shape {arr.shape} != ({expected_dim},)")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"non-finite value in serialized {key}")
        return arr

    return CoordinateMoments(
        sample_count=int(data["sample_count"]),
        min=_vec("min"),
        max=_vec("max"),
        mean=_vec("mean"),
        span=_vec("span"),
        variance_sample=_vec("variance_sample"),
        variance_pop=_vec("variance_pop"),
        std_dev_sample=_vec("std_dev_sample"),
        std_dev_pop=_vec("std_dev_pop"),
    )


def load_background_embeddings(
    bg_path: Path,
    *,
    expected_dim: int = DIM,
) -> dict[tuple[str, str, bool], dict[str, Any]]:
    """Read background_embeddings.parquet partitioned by (lang, granularity, normalize)."""
    if not bg_path.is_file():
        raise FileNotFoundError(f"missing background embeddings parquet: {bg_path}")
    table = pq.read_table(str(bg_path))
    vectors = _arrow_fixed_list_to_float64(table["vector"], expected_dim=expected_dim)
    langs = [str(v) for v in table["lang"].to_pylist()]
    topics = [str(v) for v in table["topic"].to_pylist()]
    granularities = [str(v) for v in table["granularity"].to_pylist()]
    normalizes = [bool(v) for v in table["normalize"].to_pylist()]

    grouped_idx: dict[tuple[str, str, bool], list[int]] = {}
    for idx in range(table.num_rows):
        key = (langs[idx], granularities[idx], normalizes[idx])
        grouped_idx.setdefault(key, []).append(idx)

    out: dict[tuple[str, str, bool], dict[str, Any]] = {}
    for key, indices in grouped_idx.items():
        out[key] = {
            "vectors": vectors[indices],
            "topics": [topics[i] for i in indices],
            "count": len(indices),
        }
    return out


def rank_non_backbone_directional_dims(classification: Mapping[str, Any]) -> list[int]:
    """Rank all non-backbone dims with |mu_T| > |mu_C| or snr_T >= snr_C by sep desc."""
    candidates = [
        row
        for row in classification["dimensions"]
        if row["bucket"] != "BACKBONE_ENGINE"
        and (abs(float(row["mean_T"])) > abs(float(row["mean_C"])) or float(row["snr_T"]) >= float(row["snr_C"]))
    ]
    candidates.sort(key=lambda row: (-float(row["sep"]), int(row["dim"])))
    return [int(row["dim"]) for row in candidates]


def _topk_overlap_metrics(list_1a: Sequence[int], list_1b: Sequence[int], k: int) -> dict[str, Any]:
    top_a = list(list_1a[:k])
    top_b = list(list_1b[:k])
    set_a = set(top_a)
    set_b = set(top_b)
    inter = sorted(set_a & set_b)
    union_n = len(set_a | set_b)
    return {
        "k": int(k),
        "count_1a": len(top_a),
        "count_1b": len(top_b),
        "overlap_count": len(inter),
        "jaccard": float(len(inter) / union_n) if union_n > 0 else 0.0,
        "overlap_over_k": float(len(inter) / k),
        "saturated": len(top_a) < k or len(top_b) < k,
    }


def _dim_delta_entry(
    dim: int,
    dims_1a: Mapping[int, Mapping[str, Any]],
    dims_1b: Mapping[int, Mapping[str, Any]],
    rank_1a: Mapping[int, int],
    rank_1b: Mapping[int, int],
) -> dict[str, Any]:
    r1a = dims_1a[dim]
    r1b = dims_1b[dim]
    return {
        "dim": int(dim),
        "rank_1a": rank_1a.get(dim),
        "rank_1b": rank_1b.get(dim),
        "bucket_1a": r1a["bucket"],
        "bucket_1b": r1b["bucket"],
        "sep_1a": float(r1a["sep"]),
        "sep_1b": float(r1b["sep"]),
        "sep_delta": float(r1b["sep"] - r1a["sep"]),
        "mean_T": float(r1b["mean_T"]),
        "std_T": float(r1b["std_T"]),
        "snr_T": float(r1b["snr_T"]),
        "mean_C_1a": float(r1a["mean_C"]),
        "std_C_1a": float(r1a["std_C"]),
        "snr_C_1a": float(r1a["snr_C"]),
        "mean_C_1b": float(r1b["mean_C"]),
        "std_C_1b": float(r1b["std_C"]),
        "snr_C_1b": float(r1b["snr_C"]),
    }


def compute_1a_vs_1b_domain_delta(
    cls_1a: Mapping[str, Any],
    cls_1b: Mapping[str, Any],
    *,
    ks: Sequence[int] = TOPK_SWEEP,
) -> dict[str, Any]:
    """Compare 1A cross-language vs 1B same-language rankings, dropouts, and risers."""
    anchors_1a = [int(d) for d in cls_1a["bucket_dims"]["FIRM_DOMAIN_ANCHOR"]]
    anchors_1b = [int(d) for d in cls_1b["bucket_dims"]["FIRM_DOMAIN_ANCHOR"]]
    dir_1a = rank_non_backbone_directional_dims(cls_1a)
    dir_1b = rank_non_backbone_directional_dims(cls_1b)

    dims_1a_map = {int(r["dim"]): r for r in cls_1a["dimensions"]}
    dims_1b_map = {int(r["dim"]): r for r in cls_1b["dimensions"]}
    anchor_rank_1a = {d: idx + 1 for idx, d in enumerate(anchors_1a)}
    anchor_rank_1b = {d: idx + 1 for idx, d in enumerate(anchors_1b)}
    dir_rank_1a = {d: idx + 1 for idx, d in enumerate(dir_1a)}
    dir_rank_1b = {d: idx + 1 for idx, d in enumerate(dir_1b)}

    anchor_overlap = {str(k): _topk_overlap_metrics(anchors_1a, anchors_1b, int(k)) for k in ks}
    dir_overlap = {str(k): _topk_overlap_metrics(dir_1a, dir_1b, int(k)) for k in ks}

    a64_1a = anchors_1a[:64]
    a64_1b = anchors_1b[:64]
    a64_1a_set = set(a64_1a)
    a64_1b_set = set(a64_1b)
    anchor_set_1b = set(anchors_1b)

    anchor_top64_dropouts = [
        _dim_delta_entry(d, dims_1a_map, dims_1b_map, anchor_rank_1a, anchor_rank_1b)
        for d in a64_1a
        if d not in a64_1b_set
    ]
    anchor_dropped_from_bucket = [
        _dim_delta_entry(d, dims_1a_map, dims_1b_map, anchor_rank_1a, anchor_rank_1b)
        for d in anchors_1a
        if d not in anchor_set_1b
    ]
    anchor_top64_risers = [
        {
            **_dim_delta_entry(d, dims_1a_map, dims_1b_map, anchor_rank_1a, anchor_rank_1b),
            "masked_non_anchor_in_1a": dims_1a_map[d]["bucket"] != "FIRM_DOMAIN_ANCHOR",
        }
        for d in a64_1b
        if d not in a64_1a_set
    ]

    d64_1a = dir_1a[:64]
    d64_1b = dir_1b[:64]
    d64_1a_set = set(d64_1a)
    d64_1b_set = set(d64_1b)
    dir_top64_dropouts = [
        _dim_delta_entry(d, dims_1a_map, dims_1b_map, dir_rank_1a, dir_rank_1b)
        for d in d64_1a
        if d not in d64_1b_set
    ]
    dir_top64_risers = [
        {
            **_dim_delta_entry(d, dims_1a_map, dims_1b_map, dir_rank_1a, dir_rank_1b),
            "masked_non_anchor_in_1a": dims_1a_map[d]["bucket"] != "FIRM_DOMAIN_ANCHOR",
        }
        for d in d64_1b
        if d not in d64_1a_set
    ]

    return {
        "bucket_counts_1a": dict(cls_1a["bucket_counts"]),
        "bucket_counts_1b": dict(cls_1b["bucket_counts"]),
        "topk_overlap": {
            "anchor_only": anchor_overlap,
            "non_backbone_directional": dir_overlap,
        },
        "ranked_dims_1b": {
            "firm_domain_anchor": anchors_1b,
            "non_backbone_directional_top256": dir_1b[:256],
        },
        "language_bias_dropouts": {
            "anchor_top64_dropouts_count": len(anchor_top64_dropouts),
            "anchor_top64_dropouts": anchor_top64_dropouts,
            "dropped_from_firm_anchor_altogether_count": len(anchor_dropped_from_bucket),
            "dropped_from_firm_anchor_altogether": anchor_dropped_from_bucket,
            "directional_top64_dropouts_count": len(dir_top64_dropouts),
            "directional_top64_dropouts": dir_top64_dropouts,
        },
        "pure_domain_risers": {
            "anchor_top64_risers_count": len(anchor_top64_risers),
            "anchor_top64_risers": anchor_top64_risers,
            "directional_top64_risers_count": len(dir_top64_risers),
            "directional_top64_risers": dir_top64_risers,
        },
    }


def analyze_backbone_isolation(
    cls_1a_py: Mapping[str, Any],
    cls_1a_rec: Mapping[str, Any],
    cls_1b_py: Mapping[str, Any],
    cls_1b_rec: Mapping[str, Any],
) -> dict[str, Any]:
    """Partition BACKBONE_ENGINE across 1A (EN/ES), 1B_python_en, and 1B_receta_es."""
    bb_1a_py = {int(d) for d in cls_1a_py["bucket_dims"]["BACKBONE_ENGINE"]}
    bb_1a_rec = {int(d) for d in cls_1a_rec["bucket_dims"]["BACKBONE_ENGINE"]}
    if bb_1a_py != bb_1a_rec:
        raise ValueError(f"1A backbone asymmetry: {bb_1a_py ^ bb_1a_rec}")
    bb_1a = bb_1a_py
    bb_en = {int(d) for d in cls_1b_py["bucket_dims"]["BACKBONE_ENGINE"]}
    bb_es = {int(d) for d in cls_1b_rec["bucket_dims"]["BACKBONE_ENGINE"]}

    global_bb = sorted(bb_1a & bb_en & bb_es)
    only_1a = sorted(bb_1a - (bb_en | bb_es))
    in_1a_and_en_only = sorted((bb_1a & bb_en) - bb_es)
    in_1a_and_es_only = sorted((bb_1a & bb_es) - bb_en)
    only_1b_en = sorted(bb_en - bb_1a - bb_es)
    only_1b_es = sorted(bb_es - bb_1a - bb_en)
    only_1b_both = sorted((bb_en & bb_es) - bb_1a)

    map_1a = {int(r["dim"]): r for r in cls_1a_py["dimensions"]}
    map_en = {int(r["dim"]): r for r in cls_1b_py["dimensions"]}
    map_es = {int(r["dim"]): r for r in cls_1b_rec["dimensions"]}

    details = [
        {
            "dim": d,
            "in_1a": d in bb_1a,
            "in_1b_python_en": d in bb_en,
            "in_1b_receta_es": d in bb_es,
            "bucket_1a_py": map_1a[d]["bucket"],
            "bucket_1b_py": map_en[d]["bucket"],
            "bucket_1b_rec": map_es[d]["bucket"],
            "snr_py": float(map_en[d]["snr_T"]),
            "snr_rec": float(map_es[d]["snr_T"]),
            "snr_bg_en": float(map_en[d]["snr_C"]),
            "snr_bg_es": float(map_es[d]["snr_C"]),
            "sep_1a": float(map_1a[d]["sep"]),
            "sep_1b_py": float(map_en[d]["sep"]),
            "sep_1b_rec": float(map_es[d]["sep"]),
        }
        for d in sorted(bb_1a | bb_en | bb_es)
    ]

    partition = {
        "global_bge_m3_backbone": global_bb,
        "only_1a_cross_lang": only_1a,
        "in_1a_and_1b_en_only": in_1a_and_en_only,
        "in_1a_and_1b_es_only": in_1a_and_es_only,
        "only_1b_en": only_1b_en,
        "only_1b_es": only_1b_es,
        "only_1b_both_langs_not_1a": only_1b_both,
    }
    return {
        "sets": {
            "bb_1a": sorted(bb_1a),
            "bb_1b_python_en": sorted(bb_en),
            "bb_1b_receta_es": sorted(bb_es),
            "en_locale_backbone_all": sorted(bb_en - bb_es),
            "es_locale_backbone_all": sorted(bb_es - bb_en),
            "only_1b_same_lang_union": sorted((bb_en | bb_es) - bb_1a),
        },
        "counts": {
            "bb_1a": len(bb_1a),
            "bb_1b_python_en": len(bb_en),
            "bb_1b_receta_es": len(bb_es),
            **{k: len(v) for k, v in partition.items()},
            "en_locale_backbone_all": len(bb_en - bb_es),
            "es_locale_backbone_all": len(bb_es - bb_en),
            "only_1b_same_lang_union": len((bb_en | bb_es) - bb_1a),
        },
        "partition": partition,
        "per_dim_details": details,
    }


def decompose_negative_intruder_sensors(
    classification: Mapping[str, Any],
    rogue_dims: Sequence[int] = ROGUE_DIMS,
) -> dict[str, Any]:
    """Split NEGATIVE_INTRUDER_SENSOR into mean-shift (sep>=1.0) vs variance/energy sensors."""
    neg_rows = [
        row for row in classification["dimensions"] if row["bucket"] == "NEGATIVE_INTRUDER_SENSOR"
    ]
    mean_shift = sorted(
        [row for row in neg_rows if float(row["sep"]) >= 1.0],
        key=lambda r: (-float(r["sep"]), int(r["dim"])),
    )
    variance_energy = sorted(
        [row for row in neg_rows if float(row["sep"]) < 1.0 and float(row["intruder_ratio"]) >= 1.8],
        key=lambda r: (-float(r["intruder_ratio"]), int(r["dim"])),
    )
    if len(mean_shift) + len(variance_energy) != len(neg_rows):
        raise AssertionError("negative intruder sensor partition mismatch")

    rogue_set = {int(d) for d in rogue_dims}
    ms_dims = [int(r["dim"]) for r in mean_shift]
    ve_dims = [int(r["dim"]) for r in variance_energy]
    return {
        "total_negative_intruder_sensors": len(neg_rows),
        "mean_shift_count": len(mean_shift),
        "variance_energy_count": len(variance_energy),
        "mean_shift_dims": ms_dims,
        "variance_energy_dims": ve_dims,
        "rogue_dims_in_mean_shift": sorted(rogue_set & set(ms_dims)),
        "rogue_dims_in_variance_energy": sorted(rogue_set & set(ve_dims)),
        "top20_mean_shift": mean_shift[:20],
        "top20_variance_energy": variance_energy[:20],
    }


def build_rogue_dim_autopsy_1b(
    py_m: CoordinateMoments,
    bg_en_m: CoordinateMoments,
    rec_m: CoordinateMoments,
    bg_es_m: CoordinateMoments,
    cls_py_1b: Mapping[str, Any],
    cls_rec_1b: Mapping[str, Any],
    rogue_dims: Sequence[int] = ROGUE_DIMS,
) -> list[dict[str, Any]]:
    """Inspect behavior of the 9 rogue dimensions under 1B same-language contrasts."""
    py_dims = cls_py_1b["dimensions"]
    rec_dims = cls_rec_1b["dimensions"]
    rows: list[dict[str, Any]] = []
    for dim in rogue_dims:
        p = py_dims[dim]
        r = rec_dims[dim]
        rows.append(
            {
                "dim": int(dim),
                "mean_py": float(py_m.mean[dim]),
                "std_py": float(py_m.std_dev_sample[dim]),
                "mean_bg_en": float(bg_en_m.mean[dim]),
                "std_bg_en": float(bg_en_m.std_dev_sample[dim]),
                "sep_py_bg_en": float(p["sep"]),
                "intruder_ratio_py_bg_en": float(p["intruder_ratio"]),
                "bucket_python_1b": p["bucket"],
                "mean_rec": float(rec_m.mean[dim]),
                "std_rec": float(rec_m.std_dev_sample[dim]),
                "mean_bg_es": float(bg_es_m.mean[dim]),
                "std_bg_es": float(bg_es_m.std_dev_sample[dim]),
                "sep_rec_bg_es": float(r["sep"]),
                "intruder_ratio_rec_bg_es": float(r["intruder_ratio"]),
                "bucket_receta_1b": r["bucket"],
            }
        )
    return rows


def analyze_bg_pre_l2_norms(
    bg_unnorm_vectors: np.ndarray,
    bg_topics: Sequence[str],
    cal_full_doc_summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare pre-L2 ||x||_2 of unnormalized background full_doc against v2 calibration."""
    vecs = np.asarray(bg_unnorm_vectors, dtype=np.float64)
    if vecs.ndim != 2 or vecs.shape[0] == 0:
        raise ValueError(f"expected non-empty 2D vector matrix, got {vecs.shape}")
    if not np.all(np.isfinite(vecs)):
        raise ValueError("non-finite coordinate in unnormalized background vectors")

    norms = np.linalg.norm(vecs, axis=1)
    cal_mean = float(cal_full_doc_summary["cal_norm_mean"])
    cal_std = float(cal_full_doc_summary["cal_norm_std"])
    abs_dev = np.abs(norms - cal_mean)
    z_dev = abs_dev / (cal_std + EPS)

    topic_arr = np.array(list(bg_topics), dtype=object)
    by_topic = {
        topic: summarize_distribution(norms[topic_arr == topic], NORM_QUANTILES, include_mean_std=True)
        for topic in sorted(set(bg_topics))
    }

    bg_summary = summarize_distribution(norms, NORM_QUANTILES, include_mean_std=True)
    return {
        "bg_full_doc_unnormalized": bg_summary,
        "cal_full_doc_v2_reference": dict(cal_full_doc_summary),
        "mean_diff_bg_minus_cal": float(bg_summary["mean"] - cal_mean),
        "std_ratio_bg_over_cal": float(bg_summary["std_ddof1"] / (cal_std + EPS)),
        "abs_deviation_from_cal_mean": summarize_distribution(
            abs_dev, NORM_QUANTILES, include_mean_std=True
        ),
        "z_score_abs_deviation": summarize_distribution(z_dev, NORM_QUANTILES, include_mean_std=True),
        "by_topic": by_topic,
    }


def run_mode_1b(
    xray_1a_path: Path,
    bg_embeddings_path: Path,
    *,
    expected_dim: int = DIM,
    rogue_dims: Sequence[int] = ROGUE_DIMS,
) -> dict[str, Any]:
    """Execute Phase 0 1B same-language X-ray and 1A vs 1B delta analysis."""
    if not xray_1a_path.is_file():
        raise FileNotFoundError(f"missing xray_1a json: {xray_1a_path}")
    xray_1a = json.loads(xray_1a_path.read_text(encoding="utf-8"))
    bg_slices = load_background_embeddings(bg_embeddings_path, expected_dim=expected_dim)

    bg_sample_counts = {
        f"{lang}:{gran}:norm={norm}": int(data["count"])
        for (lang, gran, norm), data in sorted(bg_slices.items())
    }

    bucket_classification: dict[str, dict[str, Any]] = {}
    language_delta: dict[str, dict[str, Any]] = {}
    backbone_isolation: dict[str, Any] = {}
    negative_sensor_split: dict[str, dict[str, Any]] = {}
    rogue_autopsy_1b: dict[str, list[dict[str, Any]]] = {}

    for gran in ("full_doc", "clause_opt2c"):
        py_m = moments_from_dict(xray_1a["granularity_stats"]["python"][gran], expected_dim=expected_dim)
        rec_m = moments_from_dict(xray_1a["granularity_stats"]["receta"][gran], expected_dim=expected_dim)
        bg_en_m = compute_coordinate_moments(bg_slices[("en", gran, True)]["vectors"], expected_dim=expected_dim)
        bg_es_m = compute_coordinate_moments(bg_slices[("es", gran, True)]["vectors"], expected_dim=expected_dim)

        cls_py_1b = classify_dimensions(py_m, bg_en_m, target_name="python", contrast_name="bg_en")
        cls_rec_1b = classify_dimensions(rec_m, bg_es_m, target_name="receta", contrast_name="bg_es")
        cls_py_1a = xray_1a["bucket_classification"][gran]["python_vs_receta"]
        cls_rec_1a = xray_1a["bucket_classification"][gran]["receta_vs_python"]

        bucket_classification[gran] = {
            "python_vs_bg_en": cls_py_1b,
            "receta_vs_bg_es": cls_rec_1b,
        }
        language_delta[gran] = {
            "python": compute_1a_vs_1b_domain_delta(cls_py_1a, cls_py_1b),
            "receta": compute_1a_vs_1b_domain_delta(cls_rec_1a, cls_rec_1b),
        }
        backbone_isolation[gran] = analyze_backbone_isolation(
            cls_py_1a, cls_rec_1a, cls_py_1b, cls_rec_1b
        )
        negative_sensor_split[gran] = {
            "python_vs_bg_en": decompose_negative_intruder_sensors(cls_py_1b, rogue_dims=rogue_dims),
            "receta_vs_bg_es": decompose_negative_intruder_sensors(cls_rec_1b, rogue_dims=rogue_dims),
        }
        rogue_autopsy_1b[gran] = build_rogue_dim_autopsy_1b(
            py_m, bg_en_m, rec_m, bg_es_m, cls_py_1b, cls_rec_1b, rogue_dims=rogue_dims
        )

    pre_l2_comparison = {
        "python_vs_bg_en": analyze_bg_pre_l2_norms(
            bg_slices[("en", "full_doc", False)]["vectors"],
            bg_slices[("en", "full_doc", False)]["topics"],
            xray_1a["pre_l2_norm_check"]["python"]["calibration_full_doc"],
        ),
        "receta_vs_bg_es": analyze_bg_pre_l2_norms(
            bg_slices[("es", "full_doc", False)]["vectors"],
            bg_slices[("es", "full_doc", False)]["topics"],
            xray_1a["pre_l2_norm_check"]["receta"]["calibration_full_doc"],
        ),
    }

    return {
        "mode": "1b",
        "dtype": "float64",
        "dim": expected_dim,
        "rogue_dims": list(rogue_dims),
        "xray_1a_source": str(xray_1a_path),
        "bg_embeddings_source": str(bg_embeddings_path),
        "bg_sample_counts": bg_sample_counts,
        "classification_thresholds": CLASSIFICATION_THRESHOLDS,
        "bucket_classification": bucket_classification,
        "language_delta_1a_vs_1b": language_delta,
        "backbone_isolation": backbone_isolation,
        "negative_intruder_sensor_decomposition": negative_sensor_split,
        "rogue_dim_autopsy_1b": rogue_autopsy_1b,
        "pre_l2_norm_comparison": pre_l2_comparison,
    }


def format_stdout_summary_1b(report: Mapping[str, Any]) -> str:
    """Render a compact quantitative summary of 1B X-ray and 1A-vs-1B delta findings."""
    lines: list[str] = [
        f"=== FHV1.1 Phase 0 1B Same-Language X-Ray & 1A-vs-1B Delta (np.float64, {report['dim']}D) ===",
        f"[bg_sample_counts] {report['bg_sample_counts']}",
    ]
    for gran in ("full_doc", "clause_opt2c"):
        for pair in ("python_vs_bg_en", "receta_vs_bg_es"):
            bc = report["bucket_classification"][gran][pair]["bucket_counts"]
            lines.append(f"[1B buckets {gran} {pair}] {bc}")

        for domain in ("python", "receta"):
            delta = report["language_delta_1a_vs_1b"][gran][domain]
            lines.append(f"[1A vs 1B delta {gran} {domain}]")
            for mode_name in ("anchor_only", "non_backbone_directional"):
                parts = []
                for k_str, stats in delta["topk_overlap"][mode_name].items():
                    parts.append(
                        f"K={k_str}:{stats['overlap_count']}/{stats['count_1b']}(J={stats['jaccard']:.3f})"
                    )
                lines.append(f"  {mode_name}: " + " ".join(parts))
            drop_info = delta["language_bias_dropouts"]
            rise_info = delta["pure_domain_risers"]
            lines.append(
                f"  dropouts(anchor_top64={drop_info['anchor_top64_dropouts_count']}, "
                f"dropped_from_anchor={drop_info['dropped_from_firm_anchor_altogether_count']}, "
                f"dir_top64={drop_info['directional_top64_dropouts_count']}) | "
                f"risers(anchor_top64={rise_info['anchor_top64_risers_count']}, "
                f"dir_top64={rise_info['directional_top64_risers_count']})"
            )

        bb = report["backbone_isolation"][gran]["counts"]
        lines.append(f"[BACKBONE isolation {gran}] {bb}")

        for pair in ("python_vs_bg_en", "receta_vs_bg_es"):
            neg = report["negative_intruder_sensor_decomposition"][gran][pair]
            lines.append(
                f"[NEG_SENSOR split {gran} {pair}] total={neg['total_negative_intruder_sensors']} "
                f"mean_shift={neg['mean_shift_count']} variance_energy={neg['variance_energy_count']} "
                f"rogue_ve={neg['rogue_dims_in_variance_energy']} rogue_ms={neg['rogue_dims_in_mean_shift']}"
            )

    for pair in ("python_vs_bg_en", "receta_vs_bg_es"):
        nrm = report["pre_l2_norm_comparison"][pair]
        bg = nrm["bg_full_doc_unnormalized"]
        cal = nrm["cal_full_doc_v2_reference"]
        lines.append(
            f"[pre-L2 ||x||_2 {pair}] bg_mean={bg['mean']:.4f} (std={bg['std_ddof1']:.4f}, "
            f"[{bg['min']:.4f}, {bg['max']:.4f}]) vs cal_mean={cal['cal_norm_mean']:.4f} "
            f"(std={cal['cal_norm_std']:.4f}) diff={nrm['mean_diff_bg_minus_cal']:+.4f}"
        )

    return "\n".join(lines)


def render_signed_number(value: float) -> str:
    """Render a finite float with an explicit leading + or -."""
    number = np.float64(value)
    if not np.isfinite(number):
        raise ValueError("non-finite value in signed render")
    text = format(float(number), ".16g")
    if bool(np.signbit(number)):
        if text.startswith("-"):
            return text
        return "-" + text.lstrip("+")
    if text.startswith("+"):
        return text
    if text.startswith("-"):
        text = text[1:]
    return "+" + text


def render_signed_float64_and_float32(value: float) -> dict[str, str]:
    """Render one coordinate as signed float64 text and as a signed float32 cast."""
    value64 = np.float64(value)
    value32 = np.float64(np.float32(value64))
    return {
        "float64": render_signed_number(value64),
        "float32": render_signed_number(value32),
    }


def sign_consistency_fraction(matrix: np.ndarray, mean: np.ndarray) -> np.ndarray:
    """Fraction of rows whose sign matches sign(mean). Zeros are not consistent."""
    values = np.asarray(matrix, dtype=np.float64)
    mu = np.asarray(mean, dtype=np.float64)
    if values.ndim != 2 or mu.shape != (values.shape[1],):
        raise ValueError(f"sign-consistency shape {values.shape} vs mean {mu.shape}")
    sign_mu = np.sign(mu)
    consistent = (np.sign(values) == sign_mu) & (values != 0.0) & (sign_mu != 0.0)
    return np.mean(consistent, axis=0)


def rank_coordinates_by_score(score: np.ndarray) -> np.ndarray:
    """Order coordinates by score descending, then by index ascending."""
    values = np.asarray(score, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError(f"expected 1D score, got {values.shape}")
    dim_index = np.arange(values.shape[0], dtype=np.int64)
    return np.lexsort((dim_index, -values))


def _jaccard(left: Sequence[int], right: Sequence[int]) -> float:
    left_set = {int(item) for item in left}
    right_set = {int(item) for item in right}
    union = len(left_set | right_set)
    if union == 0:
        return 0.0
    return float(len(left_set & right_set) / union)


def _language_separation_block(
    en_matrix: np.ndarray,
    es_matrix: np.ndarray,
    *,
    eps: float = EPS,
) -> dict[str, Any]:
    """sep_lang and SNR ratio for one normalization of EN vs ES general_prose."""
    en_arr = np.asarray(en_matrix, dtype=np.float64)
    es_arr = np.asarray(es_matrix, dtype=np.float64)
    if en_arr.ndim != 2 or es_arr.ndim != 2 or en_arr.shape[1] != es_arr.shape[1]:
        raise ValueError(f"language matrices {en_arr.shape} vs {es_arr.shape}")
    dim = int(en_arr.shape[1])
    en_moments = compute_coordinate_moments(en_arr, expected_dim=dim)
    es_moments = compute_coordinate_moments(es_arr, expected_dim=dim)
    snr_en, snr_es, _, _, sep, _ = coordinate_contrast_stats(
        en_moments.mean,
        en_moments.std_dev_sample,
        es_moments.mean,
        es_moments.std_dev_sample,
        eps=eps,
    )
    snr_ratio = (snr_en + eps) / (snr_es + eps)
    return {
        "sample_count_en": en_moments.sample_count,
        "sample_count_es": es_moments.sample_count,
        "mean_sep_lang": float(np.mean(sep)),
        "mean_snr_ratio": float(np.mean(snr_ratio)),
        "sep_lang": [float(value) for value in sep],
        "sep_ge_1_dims": [int(dim_index) for dim_index in np.flatnonzero(sep >= 1.0)],
        "secondary_band_dims": [
            int(dim_index) for dim_index in np.flatnonzero((sep >= 0.65) & (sep < 1.0))
        ],
        "_mu_en": en_moments.mean,
        "_mu_es": es_moments.mean,
        "_sep": sep,
    }


def _signed_language_means(mu_en: float, mu_es: float) -> dict[str, str]:
    en_signed = render_signed_float64_and_float32(mu_en)
    es_signed = render_signed_float64_and_float32(mu_es)
    return {
        "mean_en_float64": en_signed["float64"],
        "mean_en_float32": en_signed["float32"],
        "mean_es_float64": es_signed["float64"],
        "mean_es_float32": es_signed["float32"],
    }


def _public_language_block(block: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in block.items() if not str(key).startswith("_")}


def analyze_prueba_a(
    en_normalize_true: np.ndarray,
    es_normalize_true: np.ndarray,
    en_normalize_false: np.ndarray,
    es_normalize_false: np.ndarray,
    *,
    eps: float = EPS,
    topk: Sequence[int] = V2_LANG_TOPK,
) -> dict[str, Any]:
    """Prueba A: EN vs ES general_prose full_doc on both normalizations.

    LOCALE_LANG_DIMS and the secondary band come only from normalize=true.
    mean_snr_ratio is the mean over coordinates of (snr_en + eps) / (snr_es + eps).
    """
    true_block = _language_separation_block(en_normalize_true, es_normalize_true, eps=eps)
    false_block = _language_separation_block(en_normalize_false, es_normalize_false, eps=eps)
    if len(true_block["sep_lang"]) != len(false_block["sep_lang"]):
        raise ValueError("Prueba A normalizations disagree on dimension count")

    true_order = rank_coordinates_by_score(true_block["_sep"])
    false_order = rank_coordinates_by_score(false_block["_sep"])
    jaccard_top_k = {
        str(int(k)): _jaccard(true_order[: int(k)].tolist(), false_order[: int(k)].tolist())
        for k in topk
    }
    true_top128 = {int(dim_index) for dim_index in true_order[:128]}
    false_top128 = {int(dim_index) for dim_index in false_order[:128]}
    only_false = sorted(false_top128 - true_top128)

    mu_en_true = true_block["_mu_en"]
    mu_es_true = true_block["_mu_es"]
    mu_en_false = false_block["_mu_en"]
    mu_es_false = false_block["_mu_es"]
    sep_true = true_block["_sep"]
    sep_false = false_block["_sep"]

    def _top_rows(direction: str) -> list[dict[str, Any]]:
        if direction == "en_high":
            selected = [int(dim_index) for dim_index in true_order if mu_en_true[dim_index] > mu_es_true[dim_index]]
        else:
            selected = [int(dim_index) for dim_index in true_order if mu_es_true[dim_index] > mu_en_true[dim_index]]
        rows: list[dict[str, Any]] = []
        for rank, dim_index in enumerate(selected[:20], start=1):
            rows.append(
                {
                    "dim": dim_index,
                    "rank": rank,
                    "sep_lang_normalize_true": float(sep_true[dim_index]),
                    "sep_lang_normalize_false": float(sep_false[dim_index]),
                    "normalize_true": _signed_language_means(
                        float(mu_en_true[dim_index]), float(mu_es_true[dim_index])
                    ),
                    "normalize_false": _signed_language_means(
                        float(mu_en_false[dim_index]), float(mu_es_false[dim_index])
                    ),
                }
            )
        return rows

    locale_dims = list(true_block["sep_ge_1_dims"])
    secondary_dims = list(true_block["secondary_band_dims"])
    if set(locale_dims) & set(secondary_dims):
        raise ValueError("secondary language band overlaps LOCALE_LANG_DIMS")
    return {
        "normalize_true": _public_language_block(true_block),
        "normalize_false": _public_language_block(false_block),
        "locale_lang_dims": locale_dims,
        "secondary_band_dims": secondary_dims,
        "mean_sep_lang": {
            "normalize_true": true_block["mean_sep_lang"],
            "normalize_false": false_block["mean_sep_lang"],
        },
        "mean_snr_ratio": {
            "normalize_true": true_block["mean_snr_ratio"],
            "normalize_false": false_block["mean_snr_ratio"],
        },
        "jaccard_top_k": jaccard_top_k,
        "only_in_normalize_false_top128": only_false,
        "top20_en_high": _top_rows("en_high"),
        "top20_es_high": _top_rows("es_high"),
    }


def classify_dimensions_v2(
    target_matrix: np.ndarray,
    contrast_matrix: np.ndarray,
    *,
    locale_lang_dims: Sequence[int],
    general_prose_en_mean: np.ndarray,
    general_prose_es_mean: np.ndarray,
    target_name: str,
    contrast_name: str,
    eps: float = EPS,
) -> dict[str, Any]:
    """Label every coordinate with the six-way v2 priority.

    The language-sign gate uses the supplied EN and ES general_prose means.
    LOCALE_LANG_DIMS is exactly the caller-supplied primary set; the secondary
    band is not applied here.
    """
    target = np.asarray(target_matrix, dtype=np.float64)
    contrast = np.asarray(contrast_matrix, dtype=np.float64)
    if target.ndim != 2 or contrast.ndim != 2 or target.shape[1] != contrast.shape[1]:
        raise ValueError(f"v2 matrices {target.shape} vs {contrast.shape}")
    dim = int(target.shape[1])
    target_moments = compute_coordinate_moments(target, expected_dim=dim)
    contrast_moments = compute_coordinate_moments(contrast, expected_dim=dim)
    mu_t = target_moments.mean
    sig_t = target_moments.std_dev_sample
    mu_c = contrast_moments.mean
    sig_c = contrast_moments.std_dev_sample
    snr_t, snr_c, _, _, sep, intruder_ratio = coordinate_contrast_stats(
        mu_t, sig_t, mu_c, sig_c, eps=eps
    )
    neg_sensor_score = np.maximum(sep, intruder_ratio)
    consistency = sign_consistency_fraction(target, mu_t)

    gp_en = np.asarray(general_prose_en_mean, dtype=np.float64)
    gp_es = np.asarray(general_prose_es_mean, dtype=np.float64)
    if gp_en.shape != (dim,) or gp_es.shape != (dim,):
        raise ValueError(f"general_prose means shape {gp_en.shape}, {gp_es.shape} != ({dim},)")
    if not np.all(np.isfinite(gp_en)) or not np.all(np.isfinite(gp_es)):
        raise ValueError("non-finite general_prose mean")

    locale_mask = np.zeros(dim, dtype=bool)
    for raw_dim in locale_lang_dims:
        idx = int(raw_dim)
        if idx < 0 or idx >= dim:
            raise ValueError(f"locale dim {idx} outside 0..{dim - 1}")
        locale_mask[idx] = True

    same_target_contrast = (mu_t * mu_c) > 0.0
    opposite_target_contrast = (mu_t * mu_c) < 0.0
    same_language_sign = (gp_en * gp_es) > 0.0
    is_backbone = (
        (snr_t >= 1.5) & (snr_c >= 1.5) & same_target_contrast & (sep < 0.75) & same_language_sign
    )
    is_locale = (~is_backbone) & locale_mask
    is_polarity = (~is_backbone) & (~is_locale) & opposite_target_contrast & (sep >= 0.35)
    is_anchor = (
        (~is_backbone)
        & (~is_locale)
        & (~is_polarity)
        & (sep >= 1.0)
        & ((snr_t >= 1.0) | (np.abs(mu_t) > np.abs(mu_c)))
    )
    is_neg = (
        (~is_backbone)
        & (~is_locale)
        & (~is_polarity)
        & (~is_anchor)
        & negative_intruder_mask(mu_t, snr_t, sep, intruder_ratio)
    )
    is_subtle = (
        (~is_backbone)
        & (~is_locale)
        & (~is_polarity)
        & (~is_anchor)
        & (~is_neg)
        & (sep >= 0.35)
        & (sep < 1.0)
    )
    is_noise = ~(is_backbone | is_locale | is_polarity | is_anchor | is_neg | is_subtle)
    covered = (
        is_backbone.astype(np.int8)
        + is_locale.astype(np.int8)
        + is_polarity.astype(np.int8)
        + is_anchor.astype(np.int8)
        + is_neg.astype(np.int8)
        + is_subtle.astype(np.int8)
        + is_noise.astype(np.int8)
    )
    if not np.all(covered == 1):
        raise AssertionError("v2 bucket masks are not an exclusive partition")

    masks = {
        "BACKBONE_UNIVERSAL": is_backbone,
        "LOCALE_LANG_DIMS": is_locale,
        "POLARITY_FLIP_DIALS": is_polarity,
        "FIRM_DOMAIN_ANCHOR": is_anchor,
        "NEGATIVE_INTRUDER_SENSOR": is_neg,
        "SUBTLE_DISCRIMINATORS": is_subtle,
        "LOW_SIGNAL_NOISE": is_noise,
    }
    dimensions: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in V2_BUCKET_ORDER}
    for dim_index in range(dim):
        bucket = next(name for name, mask in masks.items() if bool(mask[dim_index]))
        polarity_band = None
        if bucket == "POLARITY_FLIP_DIALS":
            polarity_band = "strong" if float(sep[dim_index]) >= 1.0 else "fine"
        entry = {
            "dim": dim_index,
            "bucket": bucket,
            "mean_T": float(mu_t[dim_index]),
            "std_T": float(sig_t[dim_index]),
            "mean_C": float(mu_c[dim_index]),
            "std_C": float(sig_c[dim_index]),
            "snr_T": float(snr_t[dim_index]),
            "snr_C": float(snr_c[dim_index]),
            "sep": float(sep[dim_index]),
            "intruder_ratio": float(intruder_ratio[dim_index]),
            "neg_sensor_score": float(neg_sensor_score[dim_index]),
            "sign_consistency_T": float(consistency[dim_index]),
            "polarity_band": polarity_band,
        }
        dimensions.append(entry)
        grouped[bucket].append(entry)

    rank_keys: dict[str, Callable[[dict[str, Any]], tuple[float, int]]] = {
        "BACKBONE_UNIVERSAL": lambda row: (-min(row["snr_T"], row["snr_C"]), row["dim"]),
        "LOCALE_LANG_DIMS": lambda row: (-row["sep"], row["dim"]),
        "POLARITY_FLIP_DIALS": lambda row: (-row["sep"], row["dim"]),
        "FIRM_DOMAIN_ANCHOR": lambda row: (-row["sep"], row["dim"]),
        "NEGATIVE_INTRUDER_SENSOR": lambda row: (-row["neg_sensor_score"], row["dim"]),
        "SUBTLE_DISCRIMINATORS": lambda row: (-row["sep"], row["dim"]),
        "LOW_SIGNAL_NOISE": lambda row: (-row["sep"], row["dim"]),
    }
    bucket_counts: dict[str, int] = {}
    bucket_dims: dict[str, list[int]] = {}
    for bucket in V2_BUCKET_ORDER:
        ranked = sorted(grouped[bucket], key=rank_keys[bucket])
        bucket_counts[bucket] = len(ranked)
        bucket_dims[bucket] = [int(row["dim"]) for row in ranked]

    polarity_ranked = bucket_dims["POLARITY_FLIP_DIALS"]
    strong_dims = [dim_index for dim_index in polarity_ranked if dimensions[dim_index]["sep"] >= 1.0]
    fine_dims = [dim_index for dim_index in polarity_ranked if dimensions[dim_index]["sep"] < 1.0]
    return {
        "target_policy": target_name,
        "contrast_policy": contrast_name,
        "target_sample_count": target_moments.sample_count,
        "contrast_sample_count": contrast_moments.sample_count,
        "dim_count": dim,
        "bucket_counts": bucket_counts,
        "bucket_dims": bucket_dims,
        "dimensions": dimensions,
        "polarity_split": {
            "strong_count": len(strong_dims),
            "fine_count": len(fine_dims),
            "strong_dims": strong_dims,
            "fine_dims": fine_dims,
        },
    }


def count_turned_on_by_near_ood(
    classification_base: Mapping[str, Any],
    classification_full: Mapping[str, Any],
) -> dict[str, Any]:
    """Dims that are LOW_SIGNAL_NOISE on 1B_base_tech and leave that bucket on 1B_full."""
    if int(classification_base["dim_count"]) != int(classification_full["dim_count"]):
        raise ValueError("near-OOD comparison dimension mismatch")
    base_noise = [int(dim_index) for dim_index in classification_base["bucket_dims"]["LOW_SIGNAL_NOISE"]]
    full_rows = classification_full["dimensions"]
    turned = sorted(
        dim_index for dim_index in base_noise if full_rows[dim_index]["bucket"] != "LOW_SIGNAL_NOISE"
    )
    return {"count": len(turned), "dims": turned}


def summarize_hypothesis_23(
    target_matrix: np.ndarray,
    contrast_matrix: np.ndarray,
    *,
    target_name: str,
    contrast_name: str,
    eps: float = EPS,
) -> dict[str, Any]:
    """Sep bands, polarity-flip count, and top-20 dims for hypothesis 2.3."""
    target = np.asarray(target_matrix, dtype=np.float64)
    contrast = np.asarray(contrast_matrix, dtype=np.float64)
    if target.ndim != 2 or contrast.ndim != 2 or target.shape[1] != contrast.shape[1]:
        raise ValueError(f"hypothesis matrices {target.shape} vs {contrast.shape}")
    dim = int(target.shape[1])
    target_moments = compute_coordinate_moments(target, expected_dim=dim)
    contrast_moments = compute_coordinate_moments(contrast, expected_dim=dim)
    mu_t = target_moments.mean
    sig_t = target_moments.std_dev_sample
    mu_c = contrast_moments.mean
    sig_c = contrast_moments.std_dev_sample
    _, _, _, _, sep, _ = coordinate_contrast_stats(mu_t, sig_t, mu_c, sig_c, eps=eps)
    polarity = (mu_t * mu_c < 0.0) & (sep >= 0.35)
    order = rank_coordinates_by_score(sep)
    top20: list[dict[str, Any]] = []
    for dim_index in order[:20]:
        idx = int(dim_index)
        top20.append(
            {
                "dim": idx,
                "sep": float(sep[idx]),
                "mean_T": float(mu_t[idx]),
                "std_T": float(sig_t[idx]),
                "mean_C": float(mu_c[idx]),
                "std_C": float(sig_c[idx]),
                "polarity_flip": bool(polarity[idx]),
            }
        )
    return {
        "target": target_name,
        "contrast": contrast_name,
        "target_sample_count": target_moments.sample_count,
        "contrast_sample_count": contrast_moments.sample_count,
        "dim_count": dim,
        "sep_ge_1": int(np.sum(sep >= 1.0)),
        "sep_0_5_to_1": int(np.sum((sep >= 0.5) & (sep < 1.0))),
        "sep_0_35_to_0_5": int(np.sum((sep >= 0.35) & (sep < 0.5))),
        "sep_median": float(np.quantile(sep, 0.5, method="linear")),
        "sep_p90": float(np.quantile(sep, 0.9, method="linear")),
        "sep_max": float(np.max(sep)),
        "polarity_flip_count": int(np.sum(polarity)),
        "top20": top20,
    }


def finalize_v2_report(
    out_path: Path,
    unnorm_path: Path,
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Write v2 JSON, reload it, and only then delete the unnormalized parquet."""
    if not isinstance(report, Mapping) or report.get("mode") != "v2":
        raise ValueError("v2 report payload missing mode")
    if not unnorm_path.is_file():
        raise FileNotFoundError(f"missing unnormalized parquet: {unnorm_path}")
    encoded = json.dumps(report, indent=2, allow_nan=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(encoded, encoding="utf-8")
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or loaded.get("mode") != "v2":
        raise ValueError("v2 report failed to parse after write")
    unnorm_path.unlink()
    return loaded


def execute_mode_v2(
    *,
    out_path: Path,
    unnorm_path: Path,
    build_report: Callable[[], Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a v2 report, then publish it. A failed build leaves the parquet in place."""
    report = build_report()
    return finalize_v2_report(out_path, unnorm_path, report)


def load_embedding_groups(
    path: Path,
    *,
    expected_dim: int = DIM,
) -> dict[tuple[str, str, str, bool], dict[str, Any]]:
    """Group embedding rows by (lang, granularity, stratum, normalize)."""
    if not path.is_file():
        raise FileNotFoundError(f"missing embeddings parquet: {path}")
    table = pq.read_table(
        str(path),
        columns=["doc_id", "lang", "stratum", "granularity", "normalize", "vector"],
    )
    vectors = _arrow_fixed_list_to_float64(table["vector"], expected_dim=expected_dim)
    if vectors.shape[0] != table.num_rows:
        raise RuntimeError(f"vector row count mismatch in {path}")
    if not np.all(np.isfinite(vectors)):
        raise ValueError(f"non-finite coordinate in {path}")
    doc_ids = [str(value) for value in table["doc_id"].to_pylist()]
    langs = [str(value) for value in table["lang"].to_pylist()]
    strata = [str(value) for value in table["stratum"].to_pylist()]
    granularities = [str(value) for value in table["granularity"].to_pylist()]
    normalizes = [bool(value) for value in table["normalize"].to_pylist()]
    grouped: dict[tuple[str, str, str, bool], list[int]] = {}
    for idx in range(table.num_rows):
        key = (langs[idx], granularities[idx], strata[idx], normalizes[idx])
        grouped.setdefault(key, []).append(idx)
    out: dict[tuple[str, str, str, bool], dict[str, Any]] = {}
    for key, indices in grouped.items():
        out[key] = {
            "vectors": vectors[indices],
            "doc_ids": [doc_ids[i] for i in indices],
        }
    return out


def _stack_embedding_groups(
    groups: Mapping[tuple[str, str, str, bool], Mapping[str, Any]],
    lang: str,
    granularity: str,
    strata: Sequence[str],
    *,
    normalize: bool,
) -> np.ndarray:
    parts: list[np.ndarray] = []
    for stratum in strata:
        key = (lang, granularity, stratum, normalize)
        if key not in groups:
            raise KeyError(f"missing embedding slice {key}")
        parts.append(np.asarray(groups[key]["vectors"], dtype=np.float64))
    if not parts:
        raise ValueError("empty embedding stack")
    return np.concatenate(parts, axis=0)


def _assert_unit_norm(matrix: np.ndarray, label: str) -> None:
    norms = np.linalg.norm(matrix, axis=1)
    error = float(np.max(np.abs(norms - 1.0)))
    if error > 1e-3:
        raise RuntimeError(f"{label} normalize=true L2 error {error}")


def _assert_unnormalized_norm(matrix: np.ndarray, label: str) -> None:
    norms = np.linalg.norm(matrix, axis=1)
    minimum = float(np.min(norms))
    if minimum <= 1.5:
        raise RuntimeError(f"{label} normalize=false L2 min {minimum}")


def _unique_doc_ids(doc_ids: Sequence[str], label: str) -> set[str]:
    unique = set(doc_ids)
    if len(unique) != len(doc_ids):
        raise RuntimeError(f"duplicate doc_ids in {label}")
    return unique


def load_v1_calibration_matrices(db: lancedb.DBConnection) -> dict[str, dict[str, np.ndarray]]:
    """Read normalize=true full_doc and clause_opt2c calibration matrices. Read-only."""
    out: dict[str, dict[str, np.ndarray]] = {}
    for domain, profile_id in V1_PROFILES.items():
        stored = load_lancedb_profile_row(db, profile_id)
        if stored["policy_id"] != domain or stored["normalize"] is not True:
            raise RuntimeError(f"unexpected v1 profile metadata for {profile_id}")
        expected = {
            "full_doc": 600,
            "clause_opt2c": V2_CALIBRATION_CLAUSE_COUNTS[domain],
        }
        matrices: dict[str, np.ndarray] = {}
        for granularity, count in expected.items():
            vectors, tags = load_lancedb_calibration_by_profile(
                db, profile_id, strategy_tag=granularity
            )
            if vectors.shape[0] != count or any(tag != granularity for tag in tags):
                raise RuntimeError(
                    f"{profile_id} {granularity} count {vectors.shape[0]} != {count}"
                )
            if not np.all(np.isfinite(vectors)):
                raise RuntimeError(f"non-finite calibration vector in {profile_id} {granularity}")
            matrices[granularity] = vectors
        out[domain] = matrices
    return out


def _count_pair(groups: Mapping[tuple[str, str, str, bool], Mapping[str, Any]], granularity: str, stratum: str) -> dict[str, int]:
    return {
        lang: int(groups[(lang, granularity, stratum, True)]["vectors"].shape[0])
        for lang in ("en", "es")
    }


def build_v2_report(
    lancedb_uri: Path,
    bg_1k_path: Path,
    unnorm_path: Path,
) -> dict[str, Any]:
    """Label all 1,024 coordinates. Does not delete the unnormalized parquet."""
    groups = load_embedding_groups(bg_1k_path)
    unnorm_groups = load_embedding_groups(unnorm_path)
    expected_1k = {
        (lang, granularity, stratum, True)
        for lang in ("en", "es")
        for granularity in ("full_doc", "clause_opt2c")
        for stratum in V2_FULL_STRATA
    }
    if set(groups) != expected_1k:
        raise RuntimeError(f"unexpected 1k embedding slices: {sorted(set(groups) - expected_1k)}")
    expected_unnorm = {
        ("en", "full_doc", "general_prose", False),
        ("es", "full_doc", "general_prose", False),
    }
    if set(unnorm_groups) != expected_unnorm:
        raise RuntimeError(f"unexpected unnorm slices: {sorted(unnorm_groups)}")

    for key, group in groups.items():
        label = f"{key[0]}:{key[1]}:{key[2]}"
        matrix = np.asarray(group["vectors"], dtype=np.float64)
        expected = V2_FULL_DOC_COUNTS[(key[0], key[2])] if key[1] == "full_doc" else V2_CLAUSE_COUNTS[(key[0], key[2])]
        if matrix.shape != (expected, DIM):
            raise RuntimeError(f"{label} shape {matrix.shape} != ({expected}, {DIM})")
        _assert_unit_norm(matrix, label)
    for key, group in unnorm_groups.items():
        matrix = np.asarray(group["vectors"], dtype=np.float64)
        if matrix.shape != (300, DIM):
            raise RuntimeError(f"unnorm {key[0]} shape {matrix.shape} != (300, {DIM})")
        _assert_unnormalized_norm(matrix, f"unnorm {key[0]}")
        true_ids = _unique_doc_ids(groups[(key[0], "full_doc", "general_prose", True)]["doc_ids"], f"1k {key[0]}")
        false_ids = _unique_doc_ids(group["doc_ids"], f"unnorm {key[0]}")
        if true_ids != false_ids:
            raise RuntimeError(f"{key[0]} general_prose doc_ids differ across normalizations")

    en_true = _stack_embedding_groups(groups, "en", "full_doc", ("general_prose",), normalize=True)
    es_true = _stack_embedding_groups(groups, "es", "full_doc", ("general_prose",), normalize=True)
    en_false = _stack_embedding_groups(unnorm_groups, "en", "full_doc", ("general_prose",), normalize=False)
    es_false = _stack_embedding_groups(unnorm_groups, "es", "full_doc", ("general_prose",), normalize=False)
    prueba_a = analyze_prueba_a(en_true, es_true, en_false, es_false)
    locale_dims = prueba_a["locale_lang_dims"]
    if set(locale_dims) & set(prueba_a["secondary_band_dims"]):
        raise RuntimeError("secondary band was folded into LOCALE_LANG_DIMS")

    gp_en = np.mean(en_true, axis=0)
    gp_es = np.mean(es_true, axis=0)
    db = lancedb.connect(str(lancedb_uri))
    calibration = load_v1_calibration_matrices(db)

    classifications: dict[str, dict[str, dict[str, Any]]] = {}
    for granularity in ("full_doc", "clause_opt2c"):
        classifications[granularity] = {}
        for background_name, strata in (
            ("1B_base_tech", V2_BASE_STRATA),
            ("1B_full", V2_FULL_STRATA),
        ):
            classifications[granularity][background_name] = {}
            for domain, lang in V2_DOMAIN_LANG.items():
                contrast = _stack_embedding_groups(
                    groups, lang, granularity, strata, normalize=True
                )
                if granularity == "full_doc":
                    expected_rows = 400 if background_name == "1B_base_tech" else 500
                    if contrast.shape[0] != expected_rows:
                        raise RuntimeError(
                            f"{background_name} {lang} full_doc rows {contrast.shape[0]} != {expected_rows}"
                        )
                classifications[granularity][background_name][domain] = classify_dimensions_v2(
                    calibration[domain][granularity],
                    contrast,
                    locale_lang_dims=locale_dims,
                    general_prose_en_mean=gp_en,
                    general_prose_es_mean=gp_es,
                    target_name=domain,
                    contrast_name=f"{background_name}:{lang}",
                )

    turned_on = {
        granularity: {
            domain: count_turned_on_by_near_ood(
                classifications[granularity]["1B_base_tech"][domain],
                classifications[granularity]["1B_full"][domain],
            )
            for domain in ("python", "receta")
        }
        for granularity in ("full_doc", "clause_opt2c")
    }

    near_en = _stack_embedding_groups(groups, "en", "full_doc", ("near_ood_neighbor",), normalize=True)
    near_es = _stack_embedding_groups(groups, "es", "full_doc", ("near_ood_neighbor",), normalize=True)
    if near_en.shape[0] != 100 or near_es.shape[0] != 100:
        raise RuntimeError("near_ood_neighbor full_doc counts are not 100 per language")
    hypothesis = {
        "python_vs_en_near_ood_neighbor": summarize_hypothesis_23(
            calibration["python"]["full_doc"],
            near_en,
            target_name="python-v1",
            contrast_name="en_near_ood_neighbor",
        ),
        "receta_vs_es_near_ood_neighbor": summarize_hypothesis_23(
            calibration["receta"]["full_doc"],
            near_es,
            target_name="receta-v1",
            contrast_name="es_near_ood_neighbor",
        ),
    }

    def _strata_counts(granularity: str) -> dict[str, dict[str, int]]:
        counts = {
            stratum: _count_pair(groups, granularity, stratum) for stratum in V2_FULL_STRATA
        }
        counts["1B_base_tech"] = {
            lang: counts["general_prose"][lang] + counts["technical_structured"][lang]
            for lang in ("en", "es")
        }
        counts["1B_full"] = {
            lang: counts["1B_base_tech"][lang] + counts["near_ood_neighbor"][lang]
            for lang in ("en", "es")
        }
        return counts

    return {
        "mode": "v2",
        "dtype": "float64",
        "dim": DIM,
        "eps": EPS,
        "thresholds": {
            "eps": EPS,
            "ddof": 1,
            "locale_primary_sep_min": 1.0,
            "locale_secondary_sep_min": 0.65,
            "polarity_sep_min": 0.35,
            "subtle_sep_min": 0.35,
            "subtle_sep_max_exclusive": 1.0,
            "backbone_snr_min": 1.5,
            "backbone_sep_max_exclusive": 0.75,
            "anchor_sep_min": 1.0,
            "anchor_snr_min": 1.0,
            "negative_intruder": {
                "abs_mu_target_max_exclusive": NEG_SENSOR_ABS_MU_MAX_EXCLUSIVE,
                "snr_target_max_exclusive": NEG_SENSOR_SNR_MAX_EXCLUSIVE,
                "sep_min_or": NEG_SENSOR_SEP_MIN,
                "intruder_ratio_min_or": NEG_SENSOR_INTRUDER_MIN,
            },
            "language_sign_gate": "normalize=true general_prose full_doc means",
            "mean_snr_ratio": "(snr_en + eps) / (snr_es + eps), mean over coordinates",
            "classification_order": list(V2_BUCKET_ORDER),
        },
        "sources": {
            "lancedb_uri": str(lancedb_uri),
            "bg_embeddings_1k": str(bg_1k_path),
            "bg_general_unnorm": str(unnorm_path),
            "profiles": {"python": V1_PROFILES["python"], "receta": V1_PROFILES["receta"]},
        },
        "sample_counts": {
            "background_1k_rows": int(sum(group["vectors"].shape[0] for group in groups.values())),
            "unnorm_rows": int(sum(group["vectors"].shape[0] for group in unnorm_groups.values())),
            "full_doc": _strata_counts("full_doc"),
            "clause_opt2c": _strata_counts("clause_opt2c"),
            "calibration": {
                "full_doc": {
                    domain: int(calibration[domain]["full_doc"].shape[0]) for domain in ("python", "receta")
                },
                "clause_opt2c": {
                    domain: int(calibration[domain]["clause_opt2c"].shape[0])
                    for domain in ("python", "receta")
                },
            },
        },
        "prueba_a": prueba_a,
        "prueba_b": {
            "full_doc": classifications["full_doc"],
            "clause_opt2c": classifications["clause_opt2c"],
            "turned_on_by_near_ood_neighbor": turned_on,
        },
        "hypothesis_2_3": hypothesis,
    }


def run_mode_v2(
    lancedb_uri: Path,
    bg_1k_path: Path,
    unnorm_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    """Run v2 and delete the unnormalized parquet only after the JSON parses."""

    def build() -> dict[str, Any]:
        return build_v2_report(lancedb_uri, bg_1k_path, unnorm_path)

    return execute_mode_v2(out_path=out_path, unnorm_path=unnorm_path, build_report=build)


def format_stdout_summary_v2(report: Mapping[str, Any]) -> str:
    """Render bucket counts and hypothesis 2.3 bands for a v2 report."""
    prueba_a = report["prueba_a"]
    lines = [
        f"=== FHV1.1 v2 fine dials ({report['dtype']}, {report['dim']}D) ===",
        (
            f"[Prueba A] LOCALE_LANG_DIMS={len(prueba_a['locale_lang_dims'])} "
            f"secondary={len(prueba_a['secondary_band_dims'])} "
            f"jaccard128={prueba_a['jaccard_top_k']['128']:.6f} "
            f"only_unnorm_top128={len(prueba_a['only_in_normalize_false_top128'])}"
        ),
    ]
    for domain in ("python", "receta"):
        counts = report["prueba_b"]["full_doc"]["1B_full"][domain]["bucket_counts"]
        turned = report["prueba_b"]["turned_on_by_near_ood_neighbor"]["full_doc"][domain]["count"]
        lines.append(f"[1B_full full_doc {domain}] {counts} turned_on={turned}")
    for key in ("python_vs_en_near_ood_neighbor", "receta_vs_es_near_ood_neighbor"):
        hyp = report["hypothesis_2_3"][key]
        lines.append(
            f"[hypothesis 2.3 {key}] sep>=1:{hyp['sep_ge_1']} "
            f"[0.5,1):{hyp['sep_0_5_to_1']} [0.35,0.5):{hyp['sep_0_35_to_0_5']} "
            f"polarity={hyp['polarity_flip_count']} "
            f"median={hyp['sep_median']:.6f} p90={hyp['sep_p90']:.6f} max={hyp['sep_max']:.6f}"
        )
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only 1,024D X-ray analyzer for fhv1_1 Phase 0 and v2 diagnostics."
    )
    parser.add_argument(
        "--mode",
        choices=("1a", "embed-bg", "1b", "v2"),
        default="1a",
        help="Analysis mode (1a, embed-bg, 1b, or v2).",
    )
    parser.add_argument(
        "--lancedb-uri",
        type=Path,
        default=Path("data/sf-lancedb"),
        help="Path to read-only LanceDB directory.",
    )
    parser.add_argument(
        "--benchmarks-dir",
        type=Path,
        default=Path("data/fhv1_benchmarks"),
        help="Path to benchmark JSONL metadata directory for v2 subtype joins.",
    )
    parser.add_argument(
        "--bg-corpus",
        type=Path,
        default=Path("tools/fhv1_1_background_corpus.jsonl"),
        help="Path to background corpus JSONL for --mode embed-bg.",
    )
    parser.add_argument(
        "--bg-out",
        type=Path,
        default=Path("data/fhv1_1_research/background_embeddings.parquet"),
        help="Output Parquet path for normalize=true rows in --mode embed-bg.",
    )
    parser.add_argument(
        "--bg-unnorm-out",
        type=Path,
        default=Path("/tmp/fhv1_1_id_v2/bg_general_unnorm.parquet"),
        help="normalize=false general_prose full_doc parquet. embed-bg writes it; v2 reads it and deletes it after the JSON parses.",
    )
    parser.add_argument(
        "--embed-url",
        type=str,
        default="http://127.0.0.1:8080",
        help="Local BGE-M3 HTTP server URL for --mode embed-bg.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size for --mode embed-bg.",
    )
    parser.add_argument(
        "--xray-1a",
        type=Path,
        default=Path("/tmp/fhv1_1_id/xray_1a.json"),
        help="Path to Phase 0 1A X-ray JSON for --mode 1b.",
    )
    parser.add_argument(
        "--bg-embeddings",
        type=Path,
        default=Path("data/fhv1_1_research/background_embeddings.parquet"),
        help="Path to background embeddings Parquet for --mode 1b.",
    )
    parser.add_argument(
        "--bg-1k",
        type=Path,
        default=Path("data/fhv1_1_research/background_embeddings_1k.parquet"),
        help="normalize=true 1,000-doc background parquet for --mode v2.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/fhv1_1_id/xray_1a.json"),
        help="Output JSON path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = build_arg_parser().parse_args(raw_argv)
    if args.mode == "1a":
        report = run_mode_1a(args.lancedb_uri, args.benchmarks_dir)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(format_stdout_summary(report))
        print(f"Wrote {args.out}")
        return 0
    if args.mode == "embed-bg":
        summary = run_mode_embed_bg(
            args.bg_corpus,
            args.bg_out,
            args.embed_url,
            batch_size=args.batch_size,
            unnorm_out_path=args.bg_unnorm_out,
        )
        print(json.dumps(summary, indent=2))
        return 0
    if args.mode == "1b":
        has_explicit_out = any(tok == "--out" or tok.startswith("--out=") for tok in raw_argv)
        out_path = args.out if has_explicit_out else Path("/tmp/fhv1_1_id/xray_1b.json")
        report = run_mode_1b(args.xray_1a, args.bg_embeddings)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(format_stdout_summary_1b(report))
        print(f"Wrote {out_path}")
        return 0
    if args.mode == "v2":
        has_explicit_out = any(tok == "--out" or tok.startswith("--out=") for tok in raw_argv)
        out_path = args.out if has_explicit_out else Path("/tmp/fhv1_1_id_v2/xray_v2.json")
        report = run_mode_v2(args.lancedb_uri, args.bg_1k, args.bg_unnorm_out, out_path)
        print(format_stdout_summary_v2(report))
        print(f"Wrote {out_path}")
        return 0
    raise ValueError(f"unsupported mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
