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
"""Phase 0 1A read-only 1,024D X-ray analyzer for fhv1_1 (RFC-003 IEEE 754 float64)."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import lancedb
import numpy as np
import pyarrow as pa

DIM = 1024
EPS = 1e-12
ROGUE_DIMS: tuple[int, ...] = (292, 297, 308, 329, 386, 404, 577, 616, 780)

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
    snr_t = np.abs(mu_t) / (sig_t + eps)
    snr_c = np.abs(mu_c) / (sig_c + eps)
    rms_t = np.sqrt(mu_t**2 + sig_t**2)
    rms_c = np.sqrt(mu_c**2 + sig_c**2)
    sep = np.abs(mu_t - mu_c) / (np.sqrt((sig_t**2 + sig_c**2) / 2.0) + eps)
    intruder_ratio = rms_c / (rms_t + eps)
    neg_sensor_score = np.maximum(sep, intruder_ratio)

    is_backbone = (snr_t >= 1.5) & (snr_c >= 1.5) & ((mu_t * mu_c) > 0.0) & (sep < 0.75)
    is_anchor = (~is_backbone) & (sep >= 1.0) & ((snr_t >= 1.0) | (np.abs(mu_t) > np.abs(mu_c)))
    is_neg_sensor = (
        (~is_backbone)
        & (~is_anchor)
        & (np.abs(mu_t) < 0.015)
        & (snr_t < 0.75)
        & ((sep >= 1.0) | (intruder_ratio >= 1.8))
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


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only 1,024D X-ray analyzer for fhv1_1 Phase 0 diagnostics."
    )
    parser.add_argument("--mode", choices=("1a",), default="1a", help="Analysis mode (1a).")
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
        "--out",
        type=Path,
        default=Path("/tmp/fhv1_1_id/xray_1a.json"),
        help="Output JSON path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.mode != "1a":
        raise ValueError(f"unsupported mode: {args.mode}")
    report = run_mode_1a(args.lancedb_uri, args.benchmarks_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(format_stdout_summary(report))
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
