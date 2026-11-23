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
"""Phase 2 offline replay simulator for fhv1_1 (2A/2B, 3A, Cal OOF, Stratified OOF CV, float64)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import lancedb
import numpy as np
import pyarrow as pa

DIM = 1024
EPS_SIGMA = 1e-9
EPS_VAR = 1e-12
SCALE_FLOOR = 1e-3

V1_PROFILES: dict[str, str] = {
    "python": "python-v1-42270ed8870d",
    "receta": "receta-v1-5c820b9b36b3",
}
V2_PROFILES: dict[str, str] = {
    "python": "python-v2-42270ed8870d",
    "receta": "receta-v2-5c820b9b36b3",
}

BENCHMARK_CATEGORIES: tuple[str, ...] = (
    "IN_DOMAIN_VALID",
    "OUT_OF_DOMAIN_BENIGN",
    "HYBRID_BOUNDARY",
    "ADVERSARIAL_FUZZING",
)

KEY_SUBTYPES: tuple[str, ...] = (
    "long_architecture_guide",
    "long_debugging_walkthrough",
    "diagnostico_pasteleria_panaderia",
    "guia_culinaria_larga",
    "smuggle_json_yaml",
    "dilution_50_50",
    "near_ood_neighbor",
    "obfuscation_base64",
    "prompt_injection_jailbreak",
    "long_context_flooding",
)

K_SWEEP: tuple[int, ...] = (32, 64, 128, 256)
M_SWEEP: tuple[int, ...] = (32, 64, 128)
K_BOX_SWEEP: tuple[float, ...] = (5.0, 7.0, 10.0)
K_NEG_SWEEP: tuple[float, ...] = (4.0, 5.0, 6.0)
K_NORM_SWEEP: tuple[float, ...] = (3.5, 4.0, 5.0)
MAX_GRAY_FRAC_SWEEP: tuple[float, ...] = (0.15, 0.25, 0.35)


def build_simplex_weight_grid(step_denom: int = 10) -> tuple[tuple[float, float, float], ...]:
    """Build exact 66 simplex triples (w1, w2, w3) summing to 1.0 in step 1/step_denom."""
    grid: list[tuple[float, float, float]] = []
    for i in range(step_denom + 1):
        for j in range(step_denom + 1 - i):
            k = step_denom - i - j
            grid.append((i / float(step_denom), j / float(step_denom), k / float(step_denom)))
    return tuple(grid)


WEIGHT_GRID_66: tuple[tuple[float, float, float], ...] = build_simplex_weight_grid(10)


@dataclass(frozen=True)
class BoxStats:
    """Coordinate-wise calibration bounds and sample moments (IEEE 754 float64)."""

    min: np.ndarray
    max: np.ndarray
    mean: np.ndarray
    std_sample: np.ndarray
    lo: np.ndarray
    hi: np.ndarray


@dataclass(frozen=True)
class FactorScales:
    """Calibration-OOF normalization scales for raw distance factors."""

    s_f1: float
    s_l1: float
    s_l2: float
    s_neg: float

    def to_dict(self) -> dict[str, float]:
        return {
            "s_F1": self.s_f1,
            "s_L1": self.s_l1,
            "s_L2": self.s_l2,
            "s_neg": self.s_neg,
        }


@dataclass(frozen=True)
class DimSpec:
    """Active dimensions, anchor dimensions + sep weights, and negative sensor dimensions."""

    active_dims: np.ndarray
    anchor_dims: np.ndarray
    anchor_weights: np.ndarray
    neg_sensor_dims: np.ndarray


@dataclass(frozen=True)
class ChunkFactors:
    """Normalized [0.0, 1.0] factors and kill-switch telemetry per evaluated chunk."""

    f1: np.ndarray
    f2_l1: np.ndarray
    f2_l2: np.ndarray
    f3_anchor: np.ndarray
    f3_neg: np.ndarray
    f3_add: np.ndarray
    f3_mul: np.ndarray
    max_excess_sigma: np.ndarray
    max_neg_sensor_z: np.ndarray
    in_bounds_ratio: np.ndarray
    failed_dims_count: np.ndarray
    norm_z: np.ndarray | None = None

    def get_f2(self, variant: str) -> np.ndarray:
        if variant == "F2_L1":
            return self.f2_l1
        if variant == "F2_L2":
            return self.f2_l2
        raise ValueError(f"unsupported F2 variant: {variant}")

    def get_f3(self, variant: str) -> np.ndarray:
        if variant == "add":
            return self.f3_add
        if variant == "mul":
            return self.f3_mul
        if variant == "anchor":
            return self.f3_anchor
        if variant == "neg":
            return self.f3_neg
        raise ValueError(f"unsupported F3 variant: {variant}")

    def composite(self, weights: tuple[float, float, float], *, f2_variant: str = "F2_L2", f3_variant: str = "add") -> np.ndarray:
        w1, w2, w3 = weights
        return (w1 * self.f1) + (w2 * self.get_f2(f2_variant)) + (w3 * self.get_f3(f3_variant))


@dataclass(frozen=True)
class PromptBundle:
    """Aligned chunk vectors and prompt metadata for one benchmark run."""

    granularity: str
    input_ids: tuple[str, ...]
    categories: tuple[str, ...]
    subtypes: tuple[str, ...]
    expected_pass: np.ndarray
    strat_folds: np.ndarray
    chunk_strategies: tuple[str, ...]
    chunk_vectors: np.ndarray
    chunk_norm_z: np.ndarray | None
    full_chunk_idx: np.ndarray
    b64_chunk_slices: tuple[np.ndarray, ...]
    clause_chunk_slices: tuple[np.ndarray, ...]
    clause_cap24_slices: tuple[np.ndarray, ...]
    baseline_passed: np.ndarray


def _escape_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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
    out = np.asarray(flat, dtype=np.float64).reshape(n_rows, expected_dim)
    if not np.all(np.isfinite(out)):
        raise ValueError("non-finite value detected in vector matrix")
    return out


def compute_moments_from_matrix(matrix: np.ndarray, *, expected_dim: int | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute coordinate-wise (min, max, mean, std_ddof1) in IEEE 754 float64."""
    arr = np.asarray(matrix, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] < 2:
        raise ValueError(f"expected 2D matrix with >=2 rows, got {arr.shape}")
    if expected_dim is not None and arr.shape[1] != expected_dim:
        raise ValueError(f"expected dim {expected_dim}, got {arr.shape[1]}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("non-finite value in calibration matrix")
    return (
        np.min(arr, axis=0),
        np.max(arr, axis=0),
        np.mean(arr, axis=0),
        np.std(arr, axis=0, ddof=1),
    )


def build_box_stats(
    min_v: np.ndarray,
    max_v: np.ndarray,
    mean_v: np.ndarray,
    std_sample: np.ndarray,
    box_mode: str = "minmax",
) -> BoxStats:
    """Construct BoxStats for empirical [min, max] or sigma-trimmed [mu - 3s, mu + 3s]."""
    mn = np.asarray(min_v, dtype=np.float64)
    mx = np.asarray(max_v, dtype=np.float64)
    mu = np.asarray(mean_v, dtype=np.float64)
    sd = np.asarray(std_sample, dtype=np.float64)
    if box_mode == "minmax":
        lo, hi = mn, mx
    elif box_mode == "sigma3":
        lo, hi = mu - 3.0 * sd, mu + 3.0 * sd
    else:
        raise ValueError(f"unsupported box_mode: {box_mode}")
    return BoxStats(min=mn, max=mx, mean=mu, std_sample=sd, lo=lo, hi=hi)


def box_stats_from_matrix(matrix: np.ndarray, box_mode: str = "minmax") -> BoxStats:
    """Compute BoxStats directly from a sample matrix in float64."""
    mn, mx, mu, sd = compute_moments_from_matrix(matrix)
    return build_box_stats(mn, mx, mu, sd, box_mode=box_mode)


def extract_dim_spec_from_classification(
    cls_report: Mapping[str, Any],
    *,
    dim_count: int | None = None,
    global_backbone: Sequence[int] = (),
    dim_mask_mode: str = "1024d",
    anchor_mode: str = "non_bb_directional",
    k: int = 64,
    m: int = 64,
) -> DimSpec:
    """Build active dims, top-K anchors + sep weights, and top-M negative sensors from X-ray stats."""
    dims_list = cls_report["dimensions"]
    total_dims = len(dims_list) if dim_count is None else int(dim_count)
    domain_bb = {int(d) for d in cls_report["bucket_dims"]["BACKBONE_ENGINE"]}
    global_bb = {int(d) for d in global_backbone}

    if dim_mask_mode == "1024d":
        excluded_bb: set[int] = set()
    elif dim_mask_mode == "no_bb_domain":
        excluded_bb = domain_bb
    elif dim_mask_mode == "no_bb_global":
        excluded_bb = global_bb
    else:
        raise ValueError(f"unsupported dim_mask_mode: {dim_mask_mode}")

    active_dims = np.array([d for d in range(total_dims) if d not in excluded_bb], dtype=np.int64)
    if active_dims.size == 0:
        raise ValueError("active_dims cannot be empty")

    if anchor_mode == "non_bb_directional":
        anchor_candidates = [
            row
            for row in dims_list
            if row["bucket"] != "BACKBONE_ENGINE"
            and (abs(float(row["mean_T"])) > abs(float(row["mean_C"])) or float(row["snr_T"]) >= float(row["snr_C"]))
        ]
        anchor_candidates.sort(key=lambda r: (-float(r["sep"]), int(r["dim"])))
    elif anchor_mode == "strict_firm_anchor":
        dim_map = {int(r["dim"]): r for r in dims_list}
        anchor_candidates = [dim_map[int(d)] for d in cls_report["bucket_dims"]["FIRM_DOMAIN_ANCHOR"]]
    else:
        raise ValueError(f"unsupported anchor_mode: {anchor_mode}")

    chosen_anchors = anchor_candidates[:k]
    anchor_dims = np.array([int(r["dim"]) for r in chosen_anchors], dtype=np.int64)
    raw_seps = np.array([max(float(r["sep"]), 0.0) for r in chosen_anchors], dtype=np.float64)
    sep_sum = float(np.sum(raw_seps)) if raw_seps.size > 0 else 0.0
    if raw_seps.size == 0:
        anchor_weights = np.empty(0, dtype=np.float64)
    elif sep_sum > 0.0:
        anchor_weights = raw_seps / sep_sum
    else:
        anchor_weights = np.full(raw_seps.size, 1.0 / float(raw_seps.size), dtype=np.float64)

    anchor_set = set(anchor_dims.tolist())
    tier1_neg = [
        row
        for row in dims_list
        if row["bucket"] != "BACKBONE_ENGINE"
        and int(row["dim"]) not in anchor_set
        and abs(float(row["mean_T"])) < 0.015
        and float(row["snr_T"]) < 0.75
    ]
    tier1_neg.sort(key=lambda r: (-max(float(r["sep"]), float(r["intruder_ratio"])), int(r["dim"])))

    chosen_neg = list(tier1_neg[:m])
    if len(chosen_neg) < m:
        chosen_ids = anchor_set | {int(r["dim"]) for r in chosen_neg}
        tier2_neg = [
            row
            for row in dims_list
            if row["bucket"] != "BACKBONE_ENGINE" and int(row["dim"]) not in chosen_ids
        ]
        tier2_neg.sort(key=lambda r: (-max(float(r["sep"]), float(r["intruder_ratio"])), int(r["dim"])))
        chosen_neg.extend(tier2_neg[: m - len(chosen_neg)])

    neg_sensor_dims = np.array([int(r["dim"]) for r in chosen_neg], dtype=np.int64)
    return DimSpec(
        active_dims=active_dims,
        anchor_dims=anchor_dims,
        anchor_weights=anchor_weights,
        neg_sensor_dims=neg_sensor_dims,
    )


def compute_raw_distances(vectors: np.ndarray, box: BoxStats, dim_spec: DimSpec) -> dict[str, np.ndarray]:
    """Compute raw unscaled distance signals and box/sensor telemetry in float64."""
    x = np.asarray(vectors, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != box.mean.shape[0]:
        raise ValueError(f"shape mismatch: vectors {x.shape} vs stats {box.mean.shape}")
    if not np.all(np.isfinite(x)):
        raise ValueError("non-finite coordinate in evaluated vectors")

    act = dim_spec.active_dims
    x_act = x[:, act]
    lo_act = box.lo[act]
    hi_act = box.hi[act]
    mu_act = box.mean[act]
    sd_act = box.std_sample[act]

    viol = np.maximum(0.0, np.maximum(lo_act - x_act, x_act - hi_act))
    excess_sigma = viol / (sd_act + EPS_SIGMA)
    in_bounds = (x_act >= lo_act) & (x_act <= hi_act)

    mean_e = np.mean(excess_sigma, axis=1)
    max_excess_sigma = np.max(excess_sigma, axis=1)
    in_bounds_ratio = np.mean(in_bounds, axis=1)
    failed_dims_count = np.sum(~in_bounds, axis=1).astype(np.int64)

    abs_z = np.abs(x_act - mu_act) / (sd_act + EPS_SIGMA)
    z1 = np.mean(abs_z, axis=1)
    z2 = np.sqrt(np.mean(((x_act - mu_act) ** 2) / (sd_act**2 + EPS_VAR), axis=1))

    if dim_spec.anchor_dims.size > 0:
        ak = dim_spec.anchor_dims
        anchor_terms = np.exp(-np.abs(x[:, ak] - box.mean[ak]) / (2.0 * box.std_sample[ak] + EPS_SIGMA))
        f3_anchor = np.sum(anchor_terms * dim_spec.anchor_weights[None, :], axis=1)
    else:
        f3_anchor = np.ones(x.shape[0], dtype=np.float64)

    if dim_spec.neg_sensor_dims.size > 0:
        sm = dim_spec.neg_sensor_dims
        neg_z = np.abs(x[:, sm] - box.mean[sm]) / (box.std_sample[sm] + EPS_SIGMA)
        neg_excess = np.maximum(0.0, neg_z - 2.0)
        neg_penalty = np.mean(neg_excess, axis=1)
        max_neg_sensor_z = np.max(neg_z, axis=1)
    else:
        neg_penalty = np.zeros(x.shape[0], dtype=np.float64)
        max_neg_sensor_z = np.zeros(x.shape[0], dtype=np.float64)

    return {
        "mean_e": mean_e,
        "z1": z1,
        "z2": z2,
        "f3_anchor": f3_anchor,
        "neg_penalty": neg_penalty,
        "max_excess_sigma": max_excess_sigma,
        "max_neg_sensor_z": max_neg_sensor_z,
        "in_bounds_ratio": in_bounds_ratio,
        "failed_dims_count": failed_dims_count,
    }


def scales_from_oof_raw(raw: Mapping[str, np.ndarray], *, quantile: float = 0.90) -> FactorScales:
    """Fix factor scales strictly from calibration-OOF raw distance quantiles with 1e-3 floor."""
    return FactorScales(
        s_f1=max(float(np.quantile(raw["mean_e"], quantile, method="linear")), SCALE_FLOOR),
        s_l1=max(float(np.quantile(raw["z1"], quantile, method="linear")), SCALE_FLOOR),
        s_l2=max(float(np.quantile(raw["z2"], quantile, method="linear")), SCALE_FLOOR),
        s_neg=max(float(np.quantile(raw["neg_penalty"], quantile, method="linear")), SCALE_FLOOR),
    )


def normalize_factors(
    raw: Mapping[str, np.ndarray],
    scales: FactorScales,
    *,
    norm_z: np.ndarray | None = None,
) -> ChunkFactors:
    """Map raw distances into [0.0, 1.0] factors using fixed calibration-OOF scales."""
    f1 = np.clip(np.exp(-raw["mean_e"] / scales.s_f1), 0.0, 1.0)
    f2_l1 = np.clip(np.exp(-raw["z1"] / scales.s_l1), 0.0, 1.0)
    f2_l2 = np.clip(np.exp(-raw["z2"] / scales.s_l2), 0.0, 1.0)
    f3_anchor = np.clip(raw["f3_anchor"], 0.0, 1.0)
    f3_neg = np.clip(np.exp(-raw["neg_penalty"] / scales.s_neg), 0.0, 1.0)
    f3_add = 0.5 * f3_anchor + 0.5 * f3_neg
    f3_mul = f3_anchor * f3_neg
    return ChunkFactors(
        f1=f1,
        f2_l1=f2_l1,
        f2_l2=f2_l2,
        f3_anchor=f3_anchor,
        f3_neg=f3_neg,
        f3_add=f3_add,
        f3_mul=f3_mul,
        max_excess_sigma=raw["max_excess_sigma"],
        max_neg_sensor_z=raw["max_neg_sensor_z"],
        in_bounds_ratio=raw["in_bounds_ratio"],
        failed_dims_count=raw["failed_dims_count"],
        norm_z=norm_z,
    )


def assign_calibration_folds(
    sample_ids: Sequence[str],
    tags: Sequence[str],
    source_refs: Sequence[str],
    *,
    n_folds: int = 5,
) -> np.ndarray:
    """Assign deterministic calibration folds grouped by parent doc or non-empty source_ref."""
    n = len(sample_ids)
    if n == 0:
        return np.empty(0, dtype=np.int64)

    has_numeric_prefix = all("-" in sid and sid.split("-", 1)[0].isdigit() for sid in sample_ids)
    if has_numeric_prefix and "full_doc" in set(tags):
        order = sorted(range(n), key=lambda i: (int(sample_ids[i].split("-", 1)[0]), sample_ids[i]))
        folds = np.empty(n, dtype=np.int64)
        cur_doc = -1
        for idx in order:
            if tags[idx] == "full_doc":
                cur_doc += 1
            folds[idx] = max(cur_doc, 0) % n_folds
        return folds

    distinct_non_empty = sorted({ref for ref in source_refs if ref})
    if len(distinct_non_empty) > 1 and all(bool(ref) for ref in source_refs):
        ref_to_idx = {ref: i for i, ref in enumerate(distinct_non_empty)}
        return np.array([ref_to_idx[ref] % n_folds for ref in source_refs], dtype=np.int64)

    return np.arange(n, dtype=np.int64) % n_folds


def compute_cal_oof_for_granularity(
    train_pool_vectors: np.ndarray,
    train_pool_folds: np.ndarray,
    eval_vectors: np.ndarray,
    eval_folds: np.ndarray,
    dim_spec: DimSpec,
    *,
    box_mode: str = "minmax",
    n_folds: int = 5,
) -> tuple[ChunkFactors, FactorScales, dict[str, Any]]:
    """Run 5-Fold Cal OOF: fit stats on 4/5 train split, collect raw distances on 1/5 val split."""
    n_eval = eval_vectors.shape[0]
    raw_oof: dict[str, np.ndarray] = {
        "mean_e": np.empty(n_eval, dtype=np.float64),
        "z1": np.empty(n_eval, dtype=np.float64),
        "z2": np.empty(n_eval, dtype=np.float64),
        "f3_anchor": np.empty(n_eval, dtype=np.float64),
        "neg_penalty": np.empty(n_eval, dtype=np.float64),
        "max_excess_sigma": np.empty(n_eval, dtype=np.float64),
        "max_neg_sensor_z": np.empty(n_eval, dtype=np.float64),
        "in_bounds_ratio": np.empty(n_eval, dtype=np.float64),
        "failed_dims_count": np.empty(n_eval, dtype=np.int64),
    }

    for fold in range(n_folds):
        tr_mask = train_pool_folds != fold
        va_mask = eval_folds == fold
        if not np.any(va_mask):
            continue
        box_fold = box_stats_from_matrix(train_pool_vectors[tr_mask], box_mode=box_mode)
        raw_fold = compute_raw_distances(eval_vectors[va_mask], box_fold, dim_spec)
        for key, arr in raw_fold.items():
            raw_oof[key][va_mask] = arr

    scales = scales_from_oof_raw(raw_oof, quantile=0.90)
    factors_oof = normalize_factors(raw_oof, scales)
    raw_summary = {
        key: {
            "p50": float(np.quantile(raw_oof[key], 0.50, method="linear")),
            "p90": float(np.quantile(raw_oof[key], 0.90, method="linear")),
            "p99": float(np.quantile(raw_oof[key], 0.99, method="linear")),
            "max": float(np.max(raw_oof[key])),
        }
        for key in ("mean_e", "z1", "z2", "neg_penalty", "max_excess_sigma", "max_neg_sensor_z")
    }
    return factors_oof, scales, raw_summary


def compute_cap24_clause_indices(n_clauses: int) -> list[int]:
    """Select first 8 + middle 8 + last 8 clause indices when n_clauses > 24."""
    if n_clauses <= 24:
        return list(range(n_clauses))
    mid_start = (n_clauses - 8) // 2
    return list(range(8)) + list(range(mid_start, mid_start + 8)) + list(range(n_clauses - 8, n_clauses))


def compute_chunk_veto_components(
    factors: ChunkFactors,
    *,
    k_box: float | None = None,
    k_neg: float | None = None,
    k_norm: float | None = None,
) -> dict[str, np.ndarray]:
    """Compute boolean K1/K2/K3 veto flags per chunk."""
    n = factors.f1.size
    k1 = factors.max_excess_sigma > k_box if k_box is not None else np.zeros(n, dtype=bool)
    k2 = factors.max_neg_sensor_z > k_neg if k_neg is not None else np.zeros(n, dtype=bool)
    if k_norm is not None and factors.norm_z is not None:
        valid_norm = np.isfinite(factors.norm_z)
        k3 = np.where(valid_norm, factors.norm_z > k_norm, False)
    else:
        k3 = np.zeros(n, dtype=bool)
    return {"K1": k1, "K2": k2, "K3": k3, "any": k1 | k2 | k3}


def aggregate_prompt_signals(
    bundle: PromptBundle,
    chunk_scores: np.ndarray,
    chunk_veto_components: Mapping[str, np.ndarray],
    *,
    use_cap24: bool = False,
) -> dict[str, Any]:
    """Aggregate chunk scores and veto flags per prompt cleanly preserving Base64 fail-closed."""
    n_prompts = len(bundle.input_ids)
    full_scores = chunk_scores[bundle.full_chunk_idx]
    b64_min_scores = np.ones(n_prompts, dtype=np.float64)
    clause_min_scores = np.ones(n_prompts, dtype=np.float64)
    clause_p10_scores = np.ones(n_prompts, dtype=np.float64)
    clause_arrays: list[np.ndarray] = []

    veto_any_chunk = chunk_veto_components["any"]
    veto_k1 = chunk_veto_components["K1"]
    veto_k2 = chunk_veto_components["K2"]
    veto_k3 = chunk_veto_components["K3"]

    prompt_veto = veto_any_chunk[bundle.full_chunk_idx].copy()
    prompt_k1 = veto_k1[bundle.full_chunk_idx].copy()
    prompt_k2 = veto_k2[bundle.full_chunk_idx].copy()
    prompt_k3 = veto_k3[bundle.full_chunk_idx].copy()
    evaluated_chunks = 0

    slices_to_use = bundle.clause_cap24_slices if use_cap24 else bundle.clause_chunk_slices
    for p in range(n_prompts):
        evaluated_chunks += 1
        b64_idx = bundle.b64_chunk_slices[p]
        if b64_idx.size > 0:
            evaluated_chunks += int(b64_idx.size)
            b64_min_scores[p] = float(np.min(chunk_scores[b64_idx]))
            prompt_veto[p] |= bool(np.any(veto_any_chunk[b64_idx]))
            prompt_k1[p] |= bool(np.any(veto_k1[b64_idx]))
            prompt_k2[p] |= bool(np.any(veto_k2[b64_idx]))
            prompt_k3[p] |= bool(np.any(veto_k3[b64_idx]))

        cl_idx = slices_to_use[p]
        if cl_idx.size > 0:
            evaluated_chunks += int(cl_idx.size)
            cl_s = chunk_scores[cl_idx]
            clause_arrays.append(cl_s)
            clause_min_scores[p] = float(np.min(cl_s))
            clause_p10_scores[p] = float(np.quantile(cl_s, 0.10, method="linear"))
            prompt_veto[p] |= bool(np.any(veto_any_chunk[cl_idx]))
            prompt_k1[p] |= bool(np.any(veto_k1[cl_idx]))
            prompt_k2[p] |= bool(np.any(veto_k2[cl_idx]))
            prompt_k3[p] |= bool(np.any(veto_k3[cl_idx]))
        else:
            clause_arrays.append(np.array([full_scores[p]], dtype=np.float64))
            clause_min_scores[p] = float(full_scores[p])
            clause_p10_scores[p] = float(full_scores[p])

    full_b64_min = np.minimum(full_scores, b64_min_scores)
    if bundle.granularity == "full_only":
        cont_scores = {"full_min_b64": full_b64_min}
    else:
        cont_scores = {
            "min_all": np.minimum(full_b64_min, clause_min_scores),
            "blend_full_min_clause": 0.5 * full_b64_min + 0.5 * clause_min_scores,
            "p10_clause_min_full": np.minimum(full_b64_min, clause_p10_scores),
        }

    return {
        "full_b64_min": full_b64_min,
        "clause_min": clause_min_scores,
        "clause_p10": clause_p10_scores,
        "clause_arrays": clause_arrays,
        "continuous": cont_scores,
        "prompt_veto": prompt_veto,
        "prompt_k1": prompt_k1,
        "prompt_k2": prompt_k2,
        "prompt_k3": prompt_k3,
        "evaluated_chunks": evaluated_chunks,
    }


def compute_confusion_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Compute TP, FN, TN, FP, FRR, FAR, precision, recall, F1, accuracy matching TASK-011."""
    yt = np.asarray(y_true, dtype=bool)
    yp = np.asarray(y_pred, dtype=bool)
    if yt.shape != yp.shape:
        raise ValueError(f"shape mismatch: {yt.shape} vs {yp.shape}")

    tp = int(np.sum(yt & yp))
    fn = int(np.sum(yt & (~yp)))
    tn = int(np.sum((~yt) & (~yp)))
    fp = int(np.sum((~yt) & yp))
    n_pos = tp + fn
    n_neg = tn + fp
    total = n_pos + n_neg

    frr = float(fn / n_pos) if n_pos > 0 else None
    far = float(fp / n_neg) if n_neg > 0 else None
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / n_pos) if n_pos > 0 else None
    f1 = float(2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) > 0 else 0.0
    accuracy = float((tp + tn) / total) if total > 0 else 0.0

    return {
        "tp": tp,
        "fn": fn,
        "tn": tn,
        "fp": fp,
        "frr": frr,
        "far": far,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def compute_roc_auc_trapezoidal(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Compute exact trapezoidal ROC-AUC in IEEE 754 float64 with tie grouping."""
    y = np.asarray(y_true, dtype=np.int64)
    scores = np.asarray(y_score, dtype=np.float64)
    if y.ndim != 1 or scores.ndim != 1 or y.size != scores.size:
        raise ValueError(f"mismatched shapes for ROC-AUC: {y.shape} vs {scores.shape}")
    if not np.all(np.isfinite(scores)):
        raise ValueError("non-finite score detected in ROC-AUC")
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    if n_pos == 0 or n_neg == 0:
        raise ValueError(f"ROC-AUC requires both classes; got n_pos={n_pos}, n_neg={n_neg}")

    order = np.argsort(-scores, kind="mergesort")
    y_sorted = y[order]
    s_sorted = scores[order]
    breaks = np.flatnonzero(np.diff(s_sorted))
    thresh_idx = np.concatenate((breaks, np.array([y_sorted.size - 1], dtype=np.int64)))
    tps = np.cumsum(y_sorted, dtype=np.float64)[thresh_idx]
    fps = (thresh_idx.astype(np.float64) + 1.0) - tps

    tpr = np.concatenate((np.array([0.0], dtype=np.float64), tps / float(n_pos)))
    fpr = np.concatenate((np.array([0.0], dtype=np.float64), fps / float(n_neg)))
    return float(np.sum((fpr[1:] - fpr[:-1]) * (tpr[1:] + tpr[:-1]) * 0.5))


def compute_pr_auc_ap(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Compute exact step-wise PR-AUC (Average Precision) with tie grouping in float64."""
    y = np.asarray(y_true, dtype=np.int64)
    scores = np.asarray(y_score, dtype=np.float64)
    if y.ndim != 1 or scores.ndim != 1 or y.size != scores.size:
        raise ValueError(f"mismatched shapes for PR-AUC: {y.shape} vs {scores.shape}")
    if not np.all(np.isfinite(scores)):
        raise ValueError("non-finite score detected in PR-AUC")
    n_pos = int(np.sum(y == 1))
    if n_pos == 0:
        raise ValueError("PR-AUC requires at least one positive sample")

    order = np.argsort(-scores, kind="mergesort")
    y_sorted = y[order]
    s_sorted = scores[order]
    breaks = np.flatnonzero(np.diff(s_sorted))
    thresh_idx = np.concatenate((breaks, np.array([y_sorted.size - 1], dtype=np.int64)))
    tps = np.cumsum(y_sorted, dtype=np.float64)[thresh_idx]
    total_k = thresh_idx.astype(np.float64) + 1.0
    precision = tps / total_k
    recall = np.concatenate((np.array([0.0], dtype=np.float64), tps / float(n_pos)))
    return float(np.sum((recall[1:] - recall[:-1]) * precision))


def compute_auc_triple(y_true: np.ndarray, prompt_scores: np.ndarray) -> dict[str, float]:
    """Compute ROC-AUC, PR-AUC(in_domain), and PR-AUC(reject) on prompt scores."""
    y_int = np.asarray(y_true, dtype=np.int64)
    scores = np.asarray(prompt_scores, dtype=np.float64)
    return {
        "roc_auc": compute_roc_auc_trapezoidal(y_int, scores),
        "pr_auc_in_domain": compute_pr_auc_ap(y_int, scores),
        "pr_auc_reject": compute_pr_auc_ap(1 - y_int, 1.0 - scores),
    }


def assign_stratified_folds(
    categories: Sequence[str],
    subtypes: Sequence[str],
    input_ids: Sequence[str],
    *,
    n_folds: int = 5,
) -> np.ndarray:
    """Assign deterministic 5-fold splits stratified by (category, subtype)."""
    n = len(input_ids)
    order = sorted(range(n), key=lambda i: (categories[i], subtypes[i], input_ids[i]))
    folds = np.empty(n, dtype=np.int64)
    for pos, idx in enumerate(order):
        folds[idx] = pos % n_folds
    return folds


def fit_best_1d_threshold(
    scores: np.ndarray,
    y_true: np.ndarray,
    *,
    allowed_mask: np.ndarray | None = None,
) -> tuple[float, dict[str, Any]]:
    """Find threshold T maximizing F1 (tie-break: lowest FAR+FRR, median tied T) in vectorized O(N log N)."""
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(y_true, dtype=bool)
    allowed = np.ones_like(y, dtype=bool) if allowed_mask is None else np.asarray(allowed_mask, dtype=bool)

    eff_y = y[allowed]
    eff_s = s[allowed]
    fn_blocked = int(np.sum(y & (~allowed)))
    n_pos_total = int(np.sum(y))
    n_neg_total = int(np.sum(~y))

    if eff_s.size == 0:
        pred = np.zeros_like(y, dtype=bool)
        return 1.0 + 1e-6, compute_confusion_metrics(y, pred)

    order = np.argsort(-eff_s, kind="mergesort")
    s_sorted = eff_s[order]
    y_sorted = eff_y[order].astype(np.int64)

    distinct_breaks = np.flatnonzero(np.diff(s_sorted))
    group_ends = np.concatenate((distinct_breaks, np.array([s_sorted.size - 1], dtype=np.int64)))
    tp_cum = np.cumsum(y_sorted)[group_ends]
    fp_cum = (group_ends + 1) - tp_cum
    thresh_vals = s_sorted[group_ends]

    # Also consider rejecting everything (threshold > max score)
    tp_all = np.concatenate((np.array([0], dtype=np.int64), tp_cum))
    fp_all = np.concatenate((np.array([0], dtype=np.int64), fp_cum))
    thresh_all = np.concatenate((np.array([float(s_sorted[0]) + 1e-9], dtype=np.float64), thresh_vals))

    fn_all = n_pos_total - tp_all
    denom = 2 * tp_all + fp_all + fn_all
    f1_all = np.where(denom > 0, (2.0 * tp_all) / np.maximum(denom, 1), 0.0)
    frr_all = fn_all / float(max(n_pos_total, 1))
    far_all = fp_all / float(max(n_neg_total, 1))
    err_all = frr_all + far_all

    max_f1 = float(np.max(f1_all))
    cand = np.flatnonzero(np.isclose(f1_all, max_f1, rtol=0.0, atol=1e-12))
    min_err = float(np.min(err_all[cand]))
    cand2 = cand[np.isclose(err_all[cand], min_err, rtol=0.0, atol=1e-12)]
    chosen_idx = int(cand2[len(cand2) // 2])
    best_t = float(thresh_all[chosen_idx])

    pred = allowed & (s >= best_t)
    return best_t, compute_confusion_metrics(y, pred)


def _dual_zone_predict(
    full_b64_min: np.ndarray,
    clause_arrays: Sequence[np.ndarray],
    t_full: float,
    t_hard: float,
    t_soft: float,
    max_gray_frac: float,
    *,
    allowed_mask: np.ndarray | None = None,
) -> np.ndarray:
    n = full_b64_min.size
    pred = full_b64_min >= t_full
    if allowed_mask is not None:
        pred &= allowed_mask
    for p in range(n):
        if not pred[p]:
            continue
        cl = clause_arrays[p]
        if float(np.min(cl)) < t_hard:
            pred[p] = False
            continue
        gray_frac = float(np.mean(cl < t_soft))
        if gray_frac > max_gray_frac:
            pred[p] = False
    return pred


def _build_quantile_candidates(values: np.ndarray, y_true: np.ndarray, n_grid: int = 13) -> np.ndarray:
    pos_vals = values[y_true]
    probs_all = np.linspace(0.05, 0.95, n_grid)
    probs_pos = np.linspace(0.01, 0.50, 9)
    cands = np.concatenate(
        (
            np.quantile(values, probs_all, method="linear"),
            np.quantile(pos_vals, probs_pos, method="linear") if pos_vals.size > 0 else np.empty(0),
        )
    )
    return np.unique(np.round(cands, 6))


def fit_best_dual_zone_params(
    full_b64_min: np.ndarray,
    clause_arrays: Sequence[np.ndarray],
    y_true: np.ndarray,
    *,
    allowed_mask: np.ndarray | None = None,
    gray_frac_grid: Sequence[float] = MAX_GRAY_FRAC_SWEEP,
) -> dict[str, Any]:
    """Fit (t_full, t_hard, t_soft, max_gray_frac) strictly on given training subset."""
    n = full_b64_min.size
    allowed = np.ones(n, dtype=bool) if allowed_mask is None else allowed_mask
    cl_mins = np.array([float(np.min(cl)) for cl in clause_arrays], dtype=np.float64)
    all_cl_vals = np.concatenate(list(clause_arrays))

    t_full_cands = _build_quantile_candidates(full_b64_min, y_true, n_grid=11)
    t_soft_cands = _build_quantile_candidates(all_cl_vals, np.ones(all_cl_vals.size, dtype=bool), n_grid=13)
    t_hard_cands = _build_quantile_candidates(cl_mins, y_true, n_grid=11)

    # Precompute gray fractions matrix: shape (n, len(t_soft_cands))
    gray_mat = np.empty((n, t_soft_cands.size), dtype=np.float64)
    for p in range(n):
        cl = clause_arrays[p][:, None]
        gray_mat[p] = np.mean(cl < t_soft_cands[None, :], axis=0)

    full_ok_mat = (full_b64_min[:, None] >= t_full_cands[None, :]) & allowed[:, None]
    hard_ok_mat = cl_mins[:, None] >= t_hard_cands[None, :]

    n_pos = float(max(int(np.sum(y_true)), 1))
    n_neg = float(max(int(np.sum(~y_true)), 1))
    best_key: tuple[float, float, float] = (-1.0, -1e9, -1e9)
    best_params: dict[str, Any] = {}

    for gfrac in gray_frac_grid:
        soft_ok_mat = gray_mat <= gfrac
        for s_idx, t_soft in enumerate(t_soft_cands):
            soft_vec = soft_ok_mat[:, s_idx]
            for h_idx, t_hard in enumerate(t_hard_cands):
                if t_hard > t_soft + 1e-12:
                    continue
                cl_ok = soft_vec & hard_ok_mat[:, h_idx]
                preds = full_ok_mat & cl_ok[:, None]
                tp = np.sum(preds & y_true[:, None], axis=0)
                fp = np.sum(preds & (~y_true)[:, None], axis=0)
                fn = int(np.sum(y_true)) - tp
                denom = 2 * tp + fp + fn
                f1_vec = np.where(denom > 0, (2.0 * tp) / np.maximum(denom, 1), 0.0)
                err_vec = (fn / n_pos) + (fp / n_neg)
                best_f_idx = int(np.argmax(f1_vec))
                key = (float(f1_vec[best_f_idx]), -float(err_vec[best_f_idx]), -float(gfrac))
                if key > best_key:
                    best_key = key
                    best_params = {
                        "t_full": float(t_full_cands[best_f_idx]),
                        "t_hard": float(t_hard),
                        "t_soft": float(t_soft),
                        "max_gray_frac": float(gfrac),
                    }

    return best_params


def evaluate_dual_zone_oof_cv(
    bundle: PromptBundle,
    chunk_scores: np.ndarray,
    chunk_vetos: Mapping[str, np.ndarray],
    *,
    use_cap24: bool = False,
    apply_veto: bool = False,
) -> dict[str, Any]:
    """Run strict 5-Fold Stratified OOF CV for clauses_dual_zone."""
    agg = aggregate_prompt_signals(bundle, chunk_scores, chunk_vetos, use_cap24=use_cap24)
    allowed = (~agg["prompt_veto"]) if apply_veto else np.ones(len(bundle.input_ids), dtype=bool)
    oof_pred = np.zeros(len(bundle.input_ids), dtype=bool)
    fold_params: list[dict[str, Any]] = []

    for fold in range(5):
        tr = bundle.strat_folds != fold
        te = bundle.strat_folds == fold
        tr_cl = [agg["clause_arrays"][i] for i in np.flatnonzero(tr)]
        te_cl = [agg["clause_arrays"][i] for i in np.flatnonzero(te)]
        params = fit_best_dual_zone_params(
            agg["full_b64_min"][tr],
            tr_cl,
            bundle.expected_pass[tr],
            allowed_mask=allowed[tr],
        )
        fold_params.append(params)
        oof_pred[te] = _dual_zone_predict(
            agg["full_b64_min"][te],
            te_cl,
            params["t_full"],
            params["t_hard"],
            params["t_soft"],
            params["max_gray_frac"],
            allowed_mask=allowed[te],
        )

    oracle_params = fit_best_dual_zone_params(
        agg["full_b64_min"],
        agg["clause_arrays"],
        bundle.expected_pass,
        allowed_mask=allowed,
    )
    oracle_pred = _dual_zone_predict(
        agg["full_b64_min"],
        agg["clause_arrays"],
        oracle_params["t_full"],
        oracle_params["t_hard"],
        oracle_params["t_soft"],
        oracle_params["max_gray_frac"],
        allowed_mask=allowed,
    )
    oof_m = compute_confusion_metrics(bundle.expected_pass, oof_pred)
    oracle_m = compute_confusion_metrics(bundle.expected_pass, oracle_pred)
    return {
        "oof_cv": oof_m,
        "oof_pred": oof_pred,
        "fold_params": fold_params,
        "oracle_upper_bound": {**oracle_m, "params": oracle_params, "tag": "[ORACLE_UPPER_BOUND]"},
        "generalization_gap_f1": float(oracle_m["f1"] - oof_m["f1"]),
        "evaluated_chunks": agg["evaluated_chunks"],
    }


def evaluate_1d_oof_cv(
    prompt_scores: np.ndarray,
    y_true: np.ndarray,
    strat_folds: np.ndarray,
    *,
    allowed_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    """Run strict 5-Fold Stratified OOF CV + [ORACLE_UPPER_BOUND] for a 1D prompt score."""
    n = y_true.size
    allowed = np.ones(n, dtype=bool) if allowed_mask is None else allowed_mask
    oof_pred = np.zeros(n, dtype=bool)
    fold_thresholds: list[float] = []

    for fold in range(5):
        tr = strat_folds != fold
        te = strat_folds == fold
        t_fold, _ = fit_best_1d_threshold(prompt_scores[tr], y_true[tr], allowed_mask=allowed[tr])
        fold_thresholds.append(t_fold)
        oof_pred[te] = allowed[te] & (prompt_scores[te] >= t_fold)

    oracle_t, oracle_m = fit_best_1d_threshold(prompt_scores, y_true, allowed_mask=allowed)
    oof_m = compute_confusion_metrics(y_true, oof_pred)
    return {
        "oof_cv": oof_m,
        "oof_pred": oof_pred,
        "fold_thresholds": fold_thresholds,
        "mean_fold_threshold": float(np.mean(fold_thresholds)),
        "oracle_upper_bound": {**oracle_m, "threshold": oracle_t, "tag": "[ORACLE_UPPER_BOUND]"},
        "generalization_gap_f1": float(oracle_m["f1"] - oof_m["f1"]),
    }


def fit_best_2d_hard_kill(
    full_b64_min: np.ndarray,
    clause_min: np.ndarray,
    y_true: np.ndarray,
    *,
    allowed_mask: np.ndarray | None = None,
) -> tuple[float, float]:
    """Fit separate (t_full, t_clause_hard) thresholds on training fold."""
    allowed = np.ones_like(y_true, dtype=bool) if allowed_mask is None else allowed_mask
    t_full_cands = _build_quantile_candidates(full_b64_min, y_true, n_grid=15)
    t_cl_cands = _build_quantile_candidates(clause_min, y_true, n_grid=15)

    full_ok = (full_b64_min[:, None] >= t_full_cands[None, :]) & allowed[:, None]
    cl_ok = clause_min[:, None] >= t_cl_cands[None, :]
    n_pos = float(max(int(np.sum(y_true)), 1))
    n_neg = float(max(int(np.sum(~y_true)), 1))

    best_key = (-1.0, -1e9)
    best_pair = (0.5, 0.5)
    for c_idx, t_cl in enumerate(t_cl_cands):
        preds = full_ok & cl_ok[:, c_idx : c_idx + 1]
        tp = np.sum(preds & y_true[:, None], axis=0)
        fp = np.sum(preds & (~y_true)[:, None], axis=0)
        fn = int(np.sum(y_true)) - tp
        denom = 2 * tp + fp + fn
        f1_vec = np.where(denom > 0, (2.0 * tp) / np.maximum(denom, 1), 0.0)
        err_vec = (fn / n_pos) + (fp / n_neg)
        f_idx = int(np.argmax(f1_vec))
        key = (float(f1_vec[f_idx]), -float(err_vec[f_idx]))
        if key > best_key:
            best_key = key
            best_pair = (float(t_full_cands[f_idx]), float(t_cl))
    return best_pair


def evaluate_2d_hard_kill_oof_cv(
    full_b64_min: np.ndarray,
    clause_min: np.ndarray,
    y_true: np.ndarray,
    strat_folds: np.ndarray,
    *,
    allowed_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    """Run strict 5-Fold Stratified OOF CV for decoupled (T_full, T_clause_hard)."""
    n = y_true.size
    allowed = np.ones(n, dtype=bool) if allowed_mask is None else allowed_mask
    oof_pred = np.zeros(n, dtype=bool)
    fold_pairs: list[tuple[float, float]] = []

    for fold in range(5):
        tr = strat_folds != fold
        te = strat_folds == fold
        tf, tc = fit_best_2d_hard_kill(
            full_b64_min[tr], clause_min[tr], y_true[tr], allowed_mask=allowed[tr]
        )
        fold_pairs.append((tf, tc))
        oof_pred[te] = allowed[te] & (full_b64_min[te] >= tf) & (clause_min[te] >= tc)

    otf, otc = fit_best_2d_hard_kill(full_b64_min, clause_min, y_true, allowed_mask=allowed)
    oracle_pred = allowed & (full_b64_min >= otf) & (clause_min >= otc)
    oof_m = compute_confusion_metrics(y_true, oof_pred)
    oracle_m = compute_confusion_metrics(y_true, oracle_pred)
    return {
        "oof_cv": oof_m,
        "oof_pred": oof_pred,
        "fold_pairs": fold_pairs,
        "oracle_upper_bound": {**oracle_m, "t_full": otf, "t_clause_hard": otc, "tag": "[ORACLE_UPPER_BOUND]"},
        "generalization_gap_f1": float(oracle_m["f1"] - oof_m["f1"]),
    }


def evaluate_cal_only_predictions(
    cal_oof_scores_full: np.ndarray,
    cal_oof_scores_clause: np.ndarray,
    agg: Mapping[str, Any],
    y_true: np.ndarray,
    granularity: str,
    *,
    apply_veto: bool = False,
    rule_mode: str = "hard_kill",
) -> dict[str, Any]:
    """Compute CAL_ONLY predictions using p05 and p10 of Cal OOF composite scores (zero holdout tuning)."""
    allowed = (~agg["prompt_veto"]) if apply_veto else np.ones(y_true.size, dtype=bool)
    q_full = {
        "p01": float(np.quantile(cal_oof_scores_full, 0.01, method="linear")),
        "p05": float(np.quantile(cal_oof_scores_full, 0.05, method="linear")),
        "p10": float(np.quantile(cal_oof_scores_full, 0.10, method="linear")),
    }
    q_clause = {
        "p01": float(np.quantile(cal_oof_scores_clause, 0.01, method="linear")),
        "p05": float(np.quantile(cal_oof_scores_clause, 0.05, method="linear")),
        "p10": float(np.quantile(cal_oof_scores_clause, 0.10, method="linear")),
    }

    out: dict[str, Any] = {"thresholds_full": q_full, "thresholds_clause": q_clause}
    if granularity == "full_only":
        for tag in ("p05", "p10"):
            pred = allowed & (agg["full_b64_min"] >= q_full[tag])
            out[tag] = {**compute_confusion_metrics(y_true, pred), "threshold": q_full[tag], "pred": pred}
        return out

    if rule_mode == "hard_kill":
        for tag in ("p05", "p10"):
            pred = allowed & (agg["full_b64_min"] >= q_full[tag]) & (agg["clause_min"] >= q_clause[tag])
            out[tag] = {
                **compute_confusion_metrics(y_true, pred),
                "t_full": q_full[tag],
                "t_clause": q_clause[tag],
                "pred": pred,
            }
        return out

    if rule_mode == "dual_zone":
        # p05 config: T_full=p05, T_hard=p01, T_soft=p10, max_gray=0.25
        # p10 config: T_full=p10, T_hard=p05, T_soft=p10, max_gray=0.25
        specs = {
            "p05": (q_full["p05"], q_clause["p01"], q_clause["p10"], 0.25),
            "p10": (q_full["p10"], q_clause["p05"], q_clause["p10"], 0.25),
        }
        for tag, (tf, th, ts, mg) in specs.items():
            pred = _dual_zone_predict(
                agg["full_b64_min"], agg["clause_arrays"], tf, th, ts, mg, allowed_mask=allowed
            )
            out[tag] = {
                **compute_confusion_metrics(y_true, pred),
                "t_full": tf,
                "t_hard": th,
                "t_soft": ts,
                "max_gray_frac": mg,
                "pred": pred,
            }
        return out

    raise ValueError(f"unsupported rule_mode: {rule_mode}")


def compute_kill_switch_forensics(
    pred_2a: np.ndarray,
    pred_2b: np.ndarray,
    agg: Mapping[str, Any],
    bundle: PromptBundle,
) -> dict[str, Any]:
    """Compute exact 2A vs 2B Kill-Switch forensic deltas, exclusive catches, and false rejections."""
    y = bundle.expected_pass
    m_2a = compute_confusion_metrics(y, pred_2a)
    m_2b = compute_confusion_metrics(y, pred_2b)

    exclusive_catches_mask = (~y) & pred_2a & (~pred_2b)
    added_false_rej_mask = y & pred_2a & (~pred_2b)

    def _group_breakdown(mask: np.ndarray) -> dict[str, Any]:
        by_cat: dict[str, int] = {}
        by_sub: dict[str, int] = {}
        triggers: dict[str, int] = {"K1": 0, "K2": 0, "K3": 0}
        for idx in np.flatnonzero(mask):
            cat = bundle.categories[idx]
            sub = bundle.subtypes[idx]
            by_cat[cat] = by_cat.get(cat, 0) + 1
            by_sub[sub] = by_sub.get(sub, 0) + 1
            if bool(agg["prompt_k1"][idx]):
                triggers["K1"] += 1
            if bool(agg["prompt_k2"][idx]):
                triggers["K2"] += 1
            if bool(agg["prompt_k3"][idx]):
                triggers["K3"] += 1
        return {
            "count": int(np.sum(mask)),
            "by_category": dict(sorted(by_cat.items())),
            "by_subtype": dict(sorted(by_sub.items())),
            "trigger_counts": triggers,
        }

    return {
        "metrics_2a": m_2a,
        "metrics_2b": m_2b,
        "delta": {
            "delta_tp": m_2b["tp"] - m_2a["tp"],
            "delta_fn": m_2b["fn"] - m_2a["fn"],
            "delta_tn": m_2b["tn"] - m_2a["tn"],
            "delta_fp": m_2b["fp"] - m_2a["fp"],
            "delta_frr": float(m_2b["frr"] - m_2a["frr"]) if m_2a["frr"] is not None else 0.0,
            "delta_far": float(m_2b["far"] - m_2a["far"]) if m_2a["far"] is not None else 0.0,
            "delta_f1": float(m_2b["f1"] - m_2a["f1"]),
        },
        "exclusive_attacks_caught_only_by_veto": _group_breakdown(exclusive_catches_mask),
        "in_domain_false_rejections_added_by_veto": _group_breakdown(added_false_rej_mask),
    }


def compute_quadrant_and_subtype_breakdown(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
) -> dict[str, Any]:
    """Compute pass rate / FRR / FAR across the 4 quadrants and all subtypes."""
    cat_arr = np.array(categories, dtype=object)
    sub_arr = np.array(subtypes, dtype=object)

    by_category: dict[str, Any] = {}
    for cat in BENCHMARK_CATEGORIES:
        mask = cat_arr == cat
        n = int(np.sum(mask))
        passed = int(np.sum(y_pred[mask]))
        rejected = n - passed
        rate = float(passed / n) if n > 0 else 0.0
        entry: dict[str, Any] = {"count": n, "passed": passed, "rejected": rejected, "pass_rate": rate}
        if cat == "IN_DOMAIN_VALID":
            entry["frr"] = float(rejected / n) if n > 0 else 0.0
        else:
            entry["far"] = float(passed / n) if n > 0 else 0.0
        by_category[cat] = entry

    by_subtype: dict[str, Any] = {}
    for sub in sorted(set(subtypes)):
        mask = sub_arr == sub
        cat = str(cat_arr[mask][0])
        n = int(np.sum(mask))
        passed = int(np.sum(y_pred[mask]))
        rejected = n - passed
        is_in = cat == "IN_DOMAIN_VALID"
        by_subtype[sub] = {
            "category": cat,
            "count": n,
            "passed": passed,
            "rejected": rejected,
            "pass_rate": float(passed / n) if n > 0 else 0.0,
            "error_rate": float(rejected / n) if is_in else float(passed / n),
            "error_metric": "FRR" if is_in else "FAR",
        }

    overall = compute_confusion_metrics(y_true, y_pred)
    return {"overall": overall, "by_category": by_category, "by_subtype": by_subtype}


def evaluate_simplex_weight_grid_oof(
    bundle: PromptBundle,
    factors: ChunkFactors,
    cal_oof_full: ChunkFactors,
    cal_oof_clause: ChunkFactors,
    *,
    f2_variant: str = "F2_L2",
    f3_variant: str = "add",
    weights_grid: Sequence[tuple[float, float, float]] = WEIGHT_GRID_66,
    veto_components: Mapping[str, np.ndarray] | None = None,
) -> dict[str, Any]:
    """Evaluate all 66 simplex weights + nested 5-fold OOF selection of (w1, w2, w3, T)."""
    n_prompts = len(bundle.input_ids)
    n_w = len(weights_grid)
    prompt_scores_grid = np.empty((n_w, n_prompts), dtype=np.float64)
    grid_rows: list[dict[str, Any]] = []
    empty_veto = {
        "K1": np.zeros(factors.f1.size, dtype=bool),
        "K2": np.zeros(factors.f1.size, dtype=bool),
        "K3": np.zeros(factors.f1.size, dtype=bool),
        "any": np.zeros(factors.f1.size, dtype=bool),
    }
    vc = empty_veto if veto_components is None else veto_components

    for w_idx, w in enumerate(weights_grid):
        c_scores = factors.composite(w, f2_variant=f2_variant, f3_variant=f3_variant)
        agg = aggregate_prompt_signals(bundle, c_scores, vc, use_cap24=False)
        cont_key = "full_min_b64" if bundle.granularity == "full_only" else "min_all"
        p_scores = agg["continuous"][cont_key]
        prompt_scores_grid[w_idx] = p_scores

        allowed = (~agg["prompt_veto"]) if veto_components is not None else None
        oof_res = evaluate_1d_oof_cv(p_scores, bundle.expected_pass, bundle.strat_folds, allowed_mask=allowed)
        cal_full = cal_oof_full.composite(w, f2_variant=f2_variant, f3_variant=f3_variant)
        cal_cl = cal_oof_clause.composite(w, f2_variant=f2_variant, f3_variant=f3_variant)
        cal_res = evaluate_cal_only_predictions(
            cal_full, cal_cl, agg, bundle.expected_pass, bundle.granularity,
            apply_veto=(veto_components is not None), rule_mode="hard_kill",
        )
        eff_scores = np.where(agg["prompt_veto"], 0.0, p_scores) if veto_components is not None else p_scores
        aucs = compute_auc_triple(bundle.expected_pass, eff_scores)
        grid_rows.append(
            {
                "weights": list(w),
                "aucs": aucs,
                "cal_only_p05": {k: v for k, v in cal_res["p05"].items() if k != "pred"},
                "cal_only_p10": {k: v for k, v in cal_res["p10"].items() if k != "pred"},
                "oof_cv": oof_res["oof_cv"],
                "oracle_upper_bound": oof_res["oracle_upper_bound"],
                "generalization_gap_f1": oof_res["generalization_gap_f1"],
            }
        )

    # Nested OOF CV selecting (w1, w2, w3, T) strictly inside each 4/5 training fold
    nested_oof_pred = np.zeros(n_prompts, dtype=bool)
    nested_fold_choices: list[dict[str, Any]] = []
    for fold in range(5):
        tr = bundle.strat_folds != fold
        te = bundle.strat_folds == fold
        best_tr_key = (-1.0, -1e9)
        best_choice: tuple[int, float] = (0, 0.5)
        for w_idx in range(n_w):
            # Veto mask is independent of weights when veto_components is passed
            agg_w = None
            if veto_components is not None:
                c_scores = factors.composite(weights_grid[w_idx], f2_variant=f2_variant, f3_variant=f3_variant)
                agg_w = aggregate_prompt_signals(bundle, c_scores, vc, use_cap24=False)
                allowed_tr = ~agg_w["prompt_veto"][tr]
            else:
                allowed_tr = None
            t_fold, tr_m = fit_best_1d_threshold(
                prompt_scores_grid[w_idx, tr], bundle.expected_pass[tr], allowed_mask=allowed_tr
            )
            key = (tr_m["f1"], -((tr_m["frr"] or 0.0) + (tr_m["far"] or 0.0)))
            if key > best_tr_key:
                best_tr_key = key
                best_choice = (w_idx, t_fold)
        chosen_w_idx, chosen_t = best_choice
        if veto_components is not None:
            c_scores = factors.composite(weights_grid[chosen_w_idx], f2_variant=f2_variant, f3_variant=f3_variant)
            agg_w = aggregate_prompt_signals(bundle, c_scores, vc, use_cap24=False)
            allowed_te = ~agg_w["prompt_veto"][te]
        else:
            allowed_te = np.ones(int(np.sum(te)), dtype=bool)
        nested_oof_pred[te] = allowed_te & (prompt_scores_grid[chosen_w_idx, te] >= chosen_t)
        nested_fold_choices.append(
            {"fold": fold, "weights": list(weights_grid[chosen_w_idx]), "threshold": chosen_t, "train_f1": best_tr_key[0]}
        )

    best_fixed_row = max(grid_rows, key=lambda r: (r["oof_cv"]["f1"], r["aucs"]["roc_auc"]))
    return {
        "f2_variant": f2_variant,
        "f3_variant": f3_variant,
        "grid_count": n_w,
        "nested_weight_threshold_oof_cv": compute_confusion_metrics(bundle.expected_pass, nested_oof_pred),
        "nested_fold_choices": nested_fold_choices,
        "best_grid_row_by_oof_f1": best_fixed_row,
        "grid_rows": grid_rows,
    }


def _strip_preds(obj: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in obj.items() if k not in ("pred", "oof_pred")}


# ---------------------------------------------------------------------------
# LanceDB & X-Ray Read-Only Loaders
# ---------------------------------------------------------------------------


def load_benchmark_metadata(jsonl_path: Path) -> tuple[dict[str, str], dict[str, str], dict[str, bool]]:
    """Load input_id -> (subtype, category, expected_pass) from benchmark JSONL."""
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"missing benchmark jsonl: {jsonl_path}")
    subtypes: dict[str, str] = {}
    categories: dict[str, str] = {}
    expected: dict[str, bool] = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        obj = json.loads(trimmed)
        iid = str(obj["input_id"])
        subtypes[iid] = str(obj["subtype"])
        categories[iid] = str(obj["category"])
        expected[iid] = bool(obj["expected_pass"])
    return subtypes, categories, expected


def load_lancedb_benchmark_runs(db: lancedb.DBConnection) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Read fhv1_benchmark_runs indexed by (profile_id, eval_granularity, 'm0'/'m1')."""
    tbl = db.open_table("fhv1_benchmark_runs")
    rows = tbl.to_arrow().to_pylist()
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in rows:
        mask_tag = "m1" if r["use_rogue_mask"] else "m0"
        key = (str(r["profile_id"]), str(r["eval_granularity"]), mask_tag)
        out[key] = {
            "run_id": str(r["run_id"]),
            "profile_id": str(r["profile_id"]),
            "policy_id": str(r["policy_id"]),
            "eval_granularity": str(r["eval_granularity"]),
            "use_rogue_mask": bool(r["use_rogue_mask"]),
            "total_inputs": int(r["total_inputs"]),
            "total_chunks": int(r["total_chunks"]),
            "summary_metrics": json.loads(str(r["summary_metrics_json"])),
        }
    return out


def load_lancedb_calibration_bundle(
    db: lancedb.DBConnection,
    profile_id: str,
) -> dict[str, Any]:
    """Read calibration vectors, strategy tags, sample_ids, source_refs, and grouped 5-folds."""
    tbl = db.open_table("fhv1_calibration_samples")
    arrow = (
        tbl.search(None)
        .select(["sample_id", "strategy_tag", "source_ref", "vector"])
        .where(f"profile_id = {_escape_sql(profile_id)}")
        .limit(None)
        .to_arrow()
    )
    vectors = _arrow_fixed_list_to_float64(arrow["vector"], expected_dim=DIM)
    sample_ids = [str(v) for v in arrow["sample_id"].to_pylist()]
    tags = [str(v) for v in arrow["strategy_tag"].to_pylist()]
    source_refs = [str(v) for v in arrow["source_ref"].to_pylist()]
    folds = assign_calibration_folds(sample_ids, tags, source_refs, n_folds=5)

    tag_arr = np.array(tags, dtype=object)
    full_mask = tag_arr == "full_doc"
    clause_mask = tag_arr == "clause_opt2c"
    return {
        "all_vectors": vectors,
        "all_folds": folds,
        "full_doc_vectors": vectors[full_mask],
        "full_doc_folds": folds[full_mask],
        "clause_vectors": vectors[clause_mask],
        "clause_folds": folds[clause_mask],
        "counts": {
            "total": int(vectors.shape[0]),
            "full_doc": int(np.sum(full_mask)),
            "clause_opt2c": int(np.sum(clause_mask)),
        },
    }


def load_prompt_bundle(
    db: lancedb.DBConnection,
    run_id: str,
    granularity: str,
    subtypes_map: Mapping[str, str],
    categories_map: Mapping[str, str],
    expected_map: Mapping[str, bool],
    *,
    v2_run_id: str | None = None,
    cal_norm_mean: float | None = None,
    cal_norm_std: float | None = None,
) -> PromptBundle:
    """Load exact BENCHMARK audit traces sorted by (input_id, chunk_index) and join subtypes."""
    tbl = db.open_table("fhv1_audit_traces")
    where_clause = f"source_kind = 'BENCHMARK' AND run_id = {_escape_sql(run_id)}"
    arrow = (
        tbl.search(None)
        .select(["input_id", "category", "expected_pass", "chunk_index", "chunk_strategy", "overall_passed", "input_vector"])
        .where(where_clause)
        .limit(None)
        .to_arrow()
    )
    vectors = _arrow_fixed_list_to_float64(arrow["input_vector"], expected_dim=DIM)
    input_ids_col = [str(v) for v in arrow["input_id"].to_pylist()]
    cats_col = [str(v) for v in arrow["category"].to_pylist()]
    exp_col = [bool(v) for v in arrow["expected_pass"].to_pylist()]
    cidx_col = [int(v) for v in arrow["chunk_index"].to_pylist()]
    cstrat_col = [str(v) for v in arrow["chunk_strategy"].to_pylist()]
    opass_col = [bool(v) for v in arrow["overall_passed"].to_pylist()]

    sort_order = sorted(range(len(input_ids_col)), key=lambda i: (input_ids_col[i], cidx_col[i]))
    sorted_vectors = vectors[sort_order]

    # Optional v2 pre-L2 norm_z alignment for full_doc / Base64 chunks
    norm_z_arr: np.ndarray | None = None
    if v2_run_id is not None and cal_norm_mean is not None and cal_norm_std is not None:
        arr_v2 = (
            tbl.search(None)
            .select(["input_id", "chunk_index", "input_vector"])
            .where(f"source_kind = 'BENCHMARK' AND run_id = {_escape_sql(v2_run_id)}")
            .limit(None)
            .to_arrow()
        )
        v2_vecs = _arrow_fixed_list_to_float64(arr_v2["input_vector"], expected_dim=DIM)
        v2_norms = np.linalg.norm(v2_vecs, axis=1)
        v2_iids = [str(v) for v in arr_v2["input_id"].to_pylist()]
        v2_cidx = [int(v) for v in arr_v2["chunk_index"].to_pylist()]
        v2_lookup = {
            (v2_iids[i], v2_cidx[i]): abs(float(v2_norms[i]) - cal_norm_mean) / (cal_norm_std + EPS_SIGMA)
            for i in range(len(v2_iids))
        }
        norm_z_arr = np.full(len(sort_order), np.nan, dtype=np.float64)
        for pos, orig_idx in enumerate(sort_order):
            key = (input_ids_col[orig_idx], cidx_col[orig_idx])
            if key in v2_lookup:
                norm_z_arr[pos] = v2_lookup[key]

    grouped: dict[str, list[int]] = {}
    prompt_meta: dict[str, tuple[str, bool, bool]] = {}
    sorted_strats: list[str] = []
    for pos, orig_idx in enumerate(sort_order):
        iid = input_ids_col[orig_idx]
        cat = cats_col[orig_idx]
        exp = exp_col[orig_idx]
        if categories_map[iid] != cat or expected_map[iid] != exp:
            raise RuntimeError(f"metadata mismatch for {iid}")
        sorted_strats.append(cstrat_col[orig_idx])
        grouped.setdefault(iid, []).append(pos)
        prompt_meta[iid] = (cat, exp, opass_col[orig_idx])

    ordered_iids = sorted(grouped.keys())
    if len(ordered_iids) != 400:
        raise RuntimeError(f"expected 400 prompts in {run_id}, found {len(ordered_iids)}")

    p_cats = tuple(prompt_meta[iid][0] for iid in ordered_iids)
    p_subs = tuple(subtypes_map[iid] for iid in ordered_iids)
    p_exp = np.array([prompt_meta[iid][1] for iid in ordered_iids], dtype=bool)
    p_base = np.array([prompt_meta[iid][2] for iid in ordered_iids], dtype=bool)
    strat_folds = assign_stratified_folds(p_cats, p_subs, ordered_iids, n_folds=5)

    full_idx: list[int] = []
    b64_slices: list[np.ndarray] = []
    cl_slices: list[np.ndarray] = []
    cap24_slices: list[np.ndarray] = []
    for iid in ordered_iids:
        positions = grouped[iid]
        c0 = [pos for pos in positions if cidx_col[sort_order[pos]] == 0 and sorted_strats[pos] == "full_doc"]
        if len(c0) != 1:
            raise RuntimeError(f"expected single chunk_index=0 full_doc for {iid}, got {len(c0)}")
        full_idx.append(c0[0])
        b64 = [pos for pos in positions if cidx_col[sort_order[pos]] > 0 and sorted_strats[pos] == "full_doc"]
        cls = [pos for pos in positions if sorted_strats[pos] == "clause_opt2c"]
        b64_slices.append(np.array(b64, dtype=np.int64))
        cl_slices.append(np.array(cls, dtype=np.int64))
        keep = compute_cap24_clause_indices(len(cls))
        cap24_slices.append(np.array([cls[k] for k in keep], dtype=np.int64))

    return PromptBundle(
        granularity=granularity,
        input_ids=tuple(ordered_iids),
        categories=p_cats,
        subtypes=p_subs,
        expected_pass=p_exp,
        strat_folds=strat_folds,
        chunk_strategies=tuple(sorted_strats),
        chunk_vectors=sorted_vectors,
        chunk_norm_z=norm_z_arr,
        full_chunk_idx=np.array(full_idx, dtype=np.int64),
        b64_chunk_slices=tuple(b64_slices),
        clause_chunk_slices=tuple(cl_slices),
        clause_cap24_slices=tuple(cap24_slices),
        baseline_passed=p_base,
    )


# ---------------------------------------------------------------------------
# Replay Factor Pipeline & Simulation Suites
# ---------------------------------------------------------------------------


def _cls_pair_key(contrast_src: str, domain: str) -> str:
    if contrast_src == "1A":
        return "python_vs_receta" if domain == "python" else "receta_vs_python"
    if contrast_src == "1B":
        return "python_vs_bg_en" if domain == "python" else "receta_vs_bg_es"
    raise ValueError(f"unsupported contrast_src: {contrast_src}")


def build_chunk_and_cal_factors(
    domain: str,
    bundle: PromptBundle,
    cal_bundle: Mapping[str, Any],
    xray_1a: Mapping[str, Any],
    xray_1b: Mapping[str, Any],
    *,
    cal_mode: str = "decoupled",
    box_mode: str = "minmax",
    dim_mask_mode: str = "1024d",
    contrast_src: str = "1B",
    ranking_mode: str = "gran_matched",
    anchor_mode: str = "non_bb_directional",
    k: int = 64,
    m: int = 64,
) -> dict[str, Any]:
    """Compute leak-free Cal OOF scales/factors and benchmark chunk factors for a configuration."""
    xray_src = xray_1a if contrast_src == "1A" else xray_1b
    pair_key = _cls_pair_key(contrast_src, domain)

    cls_full = xray_src["bucket_classification"]["full_doc"][pair_key]
    cls_clause_src = cls_full if ranking_mode == "full_doc_ranking" else xray_src["bucket_classification"]["clause_opt2c"][pair_key]
    global_bb_full = xray_1b["backbone_isolation"]["full_doc"]["partition"]["global_bge_m3_backbone"]
    global_bb_clause = (
        global_bb_full
        if ranking_mode == "full_doc_ranking"
        else xray_1b["backbone_isolation"]["clause_opt2c"]["partition"]["global_bge_m3_backbone"]
    )

    spec_full = extract_dim_spec_from_classification(
        cls_full, global_backbone=global_bb_full, dim_mask_mode=dim_mask_mode, anchor_mode=anchor_mode, k=k, m=m
    )
    spec_clause = extract_dim_spec_from_classification(
        cls_clause_src, global_backbone=global_bb_clause, dim_mask_mode=dim_mask_mode, anchor_mode=anchor_mode, k=k, m=m
    )

    if cal_mode == "decoupled":
        pool_full_vecs, pool_full_folds = cal_bundle["full_doc_vectors"], cal_bundle["full_doc_folds"]
        pool_cl_vecs, pool_cl_folds = cal_bundle["clause_vectors"], cal_bundle["clause_folds"]
    elif cal_mode == "pooled":
        pool_full_vecs, pool_full_folds = cal_bundle["all_vectors"], cal_bundle["all_folds"]
        pool_cl_vecs, pool_cl_folds = cal_bundle["all_vectors"], cal_bundle["all_folds"]
    else:
        raise ValueError(f"unsupported cal_mode: {cal_mode}")

    cal_oof_full, scales_full, raw_oof_full_summary = compute_cal_oof_for_granularity(
        pool_full_vecs,
        pool_full_folds,
        cal_bundle["full_doc_vectors"],
        cal_bundle["full_doc_folds"],
        spec_full,
        box_mode=box_mode,
    )
    cal_oof_clause, scales_clause, raw_oof_clause_summary = compute_cal_oof_for_granularity(
        pool_cl_vecs,
        pool_cl_folds,
        cal_bundle["clause_vectors"],
        cal_bundle["clause_folds"],
        spec_clause,
        box_mode=box_mode,
    )

    # Production/eval box stats built strictly from calibration training pool (zero holdout!)
    box_full = box_stats_from_matrix(pool_full_vecs, box_mode=box_mode)
    box_clause = box_stats_from_matrix(pool_cl_vecs, box_mode=box_mode)

    strat_arr = np.array(bundle.chunk_strategies, dtype=object)
    is_full = strat_arr == "full_doc"
    is_clause = strat_arr == "clause_opt2c"
    n_chunks = bundle.chunk_vectors.shape[0]

    def _alloc() -> dict[str, np.ndarray]:
        return {
            "f1": np.empty(n_chunks, dtype=np.float64),
            "f2_l1": np.empty(n_chunks, dtype=np.float64),
            "f2_l2": np.empty(n_chunks, dtype=np.float64),
            "f3_anchor": np.empty(n_chunks, dtype=np.float64),
            "f3_neg": np.empty(n_chunks, dtype=np.float64),
            "f3_add": np.empty(n_chunks, dtype=np.float64),
            "f3_mul": np.empty(n_chunks, dtype=np.float64),
            "max_excess_sigma": np.empty(n_chunks, dtype=np.float64),
            "max_neg_sensor_z": np.empty(n_chunks, dtype=np.float64),
            "in_bounds_ratio": np.empty(n_chunks, dtype=np.float64),
            "failed_dims_count": np.empty(n_chunks, dtype=np.int64),
        }

    buf = _alloc()
    for mask, box_use, spec_use, scales_use in (
        (is_full, box_full, spec_full, scales_full),
        (is_clause, box_clause, spec_clause, scales_clause),
    ):
        if not np.any(mask):
            continue
        raw_part = compute_raw_distances(bundle.chunk_vectors[mask], box_use, spec_use)
        fac_part = normalize_factors(raw_part, scales_use)
        for field in buf:
            buf[field][mask] = getattr(fac_part, field)

    chunk_factors = ChunkFactors(norm_z=bundle.chunk_norm_z, **buf)
    return {
        "chunk_factors": chunk_factors,
        "cal_oof_full": cal_oof_full,
        "cal_oof_clause": cal_oof_clause,
        "scales_full": scales_full,
        "scales_clause": scales_clause,
        "raw_oof_summary": {"full_doc": raw_oof_full_summary, "clause_opt2c": raw_oof_clause_summary},
        "dim_counts": {
            "full_active": int(spec_full.active_dims.size),
            "full_anchors": int(spec_full.anchor_dims.size),
            "full_neg_sensors": int(spec_full.neg_sensor_dims.size),
            "clause_active": int(spec_clause.active_dims.size),
            "clause_anchors": int(spec_clause.anchor_dims.size),
            "clause_neg_sensors": int(spec_clause.neg_sensor_dims.size),
        },
    }


def evaluate_2a_config(
    bundle: PromptBundle,
    pack: Mapping[str, Any],
    *,
    weights: tuple[float, float, float],
    f2_variant: str = "F2_L2",
    f3_variant: str = "add",
    rule_mode: str = "hard_kill",
) -> dict[str, Any]:
    """Evaluate one 2A configuration returning AUC triple, CAL_ONLY, OOF CV, and Oracle."""
    cf: ChunkFactors = pack["chunk_factors"]
    c_scores = cf.composite(weights, f2_variant=f2_variant, f3_variant=f3_variant)
    cal_full = pack["cal_oof_full"].composite(weights, f2_variant=f2_variant, f3_variant=f3_variant)
    cal_cl = pack["cal_oof_clause"].composite(weights, f2_variant=f2_variant, f3_variant=f3_variant)
    empty_veto = {
        "K1": np.zeros(c_scores.size, dtype=bool),
        "K2": np.zeros(c_scores.size, dtype=bool),
        "K3": np.zeros(c_scores.size, dtype=bool),
        "any": np.zeros(c_scores.size, dtype=bool),
    }
    agg = aggregate_prompt_signals(bundle, c_scores, empty_veto, use_cap24=False)
    aucs = {k: compute_auc_triple(bundle.expected_pass, s) for k, s in agg["continuous"].items()}
    primary_cont = "full_min_b64" if bundle.granularity == "full_only" else "min_all"

    cal_only = evaluate_cal_only_predictions(
        cal_full, cal_cl, agg, bundle.expected_pass, bundle.granularity, apply_veto=False, rule_mode=rule_mode
    )
    if bundle.granularity == "full_only" or rule_mode == "hard_kill":
        oof_res = evaluate_1d_oof_cv(agg["continuous"][primary_cont], bundle.expected_pass, bundle.strat_folds)
    else:
        oof_res = evaluate_dual_zone_oof_cv(bundle, c_scores, empty_veto, use_cap24=False, apply_veto=False)

    return {
        "weights": list(weights),
        "f2_variant": f2_variant,
        "f3_variant": f3_variant,
        "rule_mode": rule_mode,
        "primary_aucs": aucs[primary_cont],
        "all_continuous_aucs": aucs,
        "cal_only_p05": _strip_preds(cal_only["p05"]),
        "cal_only_p10": _strip_preds(cal_only["p10"]),
        "oof_cv": oof_res["oof_cv"],
        "oracle_upper_bound": oof_res["oracle_upper_bound"],
        "generalization_gap_f1": oof_res["generalization_gap_f1"],
        "_oof_pred": oof_res["oof_pred"],
        "_cal_p05_pred": cal_only["p05"]["pred"],
        "_cal_p10_pred": cal_only["p10"]["pred"],
        "_chunk_scores": c_scores,
        "_agg": agg,
    }


def _clean_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def run_ablation_and_f3_sweeps(
    domain: str,
    bundle: PromptBundle,
    cal_bundle: Mapping[str, Any],
    xray_1a: Mapping[str, Any],
    xray_1b: Mapping[str, Any],
) -> dict[str, Any]:
    """Run Section 2 & 3A ablation matrix and F3 (K, M, 1A/1B, ranking, combination) sweeps."""
    cache: dict[tuple[Any, ...], dict[str, Any]] = {}

    def _get_pack(cal_mode: str, box_mode: str, dim_mask: str, csrc: str, rmode: str, amode: str, k: int, m: int) -> dict[str, Any]:
        key = (cal_mode, box_mode, dim_mask, csrc, rmode, amode, k, m)
        if key not in cache:
            cache[key] = build_chunk_and_cal_factors(
                domain,
                bundle,
                cal_bundle,
                xray_1a,
                xray_1b,
                cal_mode=cal_mode,
                box_mode=box_mode,
                dim_mask_mode=dim_mask,
                contrast_src=csrc,
                ranking_mode=rmode,
                anchor_mode=amode,
                k=k,
                m=m,
            )
        return cache[key]

    # 1. Core factor & design ablations
    ablation_specs: list[tuple[str, tuple[Any, ...], tuple[float, float, float], str, str]] = [
        ("F1_only_decoupled_minmax", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0, 0.0, 0.0), "F2_L2", "add"),
        ("F1_only_decoupled_sigma3", ("decoupled", "sigma3", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0, 0.0, 0.0), "F2_L2", "add"),
        ("F1_only_pooled_minmax", ("pooled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0, 0.0, 0.0), "F2_L2", "add"),
        ("F2_L1_only_1024d", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (0.0, 1.0, 0.0), "F2_L1", "add"),
        ("F2_L2_only_1024d", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (0.0, 1.0, 0.0), "F2_L2", "add"),
        ("F2_L2_only_no_bb_domain", ("decoupled", "minmax", "no_bb_domain", "1B", "gran_matched", "non_bb_directional", 64, 64), (0.0, 1.0, 0.0), "F2_L2", "add"),
        ("F2_L2_only_no_bb_global", ("decoupled", "minmax", "no_bb_global", "1B", "gran_matched", "non_bb_directional", 64, 64), (0.0, 1.0, 0.0), "F2_L2", "add"),
        ("F2_L2_only_pooled", ("pooled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (0.0, 1.0, 0.0), "F2_L2", "add"),
        ("F3_1A_only_K64_M64", ("decoupled", "minmax", "1024d", "1A", "gran_matched", "non_bb_directional", 64, 64), (0.0, 0.0, 1.0), "F2_L2", "add"),
        ("F3_1B_only_K64_M64", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (0.0, 0.0, 1.0), "F2_L2", "add"),
        ("F1_F2_L2_decoupled_minmax", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (0.5, 0.5, 0.0), "F2_L2", "add"),
        ("F1_F2_L1_decoupled_minmax", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (0.5, 0.5, 0.0), "F2_L1", "add"),
        ("F2_L2_F3_1A", ("decoupled", "minmax", "1024d", "1A", "gran_matched", "non_bb_directional", 64, 64), (0.0, 0.5, 0.5), "F2_L2", "add"),
        ("F2_L2_F3_1B", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (0.0, 0.5, 0.5), "F2_L2", "add"),
        ("F1_F2_L2_F3_1A_minmax_1024d", ("decoupled", "minmax", "1024d", "1A", "gran_matched", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "add"),
        ("F1_F2_L2_F3_1B_minmax_1024d", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "add"),
        ("F1_F2_L1_F3_1B_minmax_1024d", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L1", "add"),
        ("F1_F2_L2_F3_1B_sigma3_1024d", ("decoupled", "sigma3", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "add"),
        ("F1_F2_L2_F3_1B_minmax_no_bb_domain", ("decoupled", "minmax", "no_bb_domain", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "add"),
        ("F1_F2_L2_F3_1B_minmax_no_bb_global", ("decoupled", "minmax", "no_bb_global", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "add"),
        ("F1_F2_L2_F3_1B_pooled_minmax", ("pooled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "add"),
        ("F1_F2_L2_F3_1B_pooled_sigma3", ("pooled", "sigma3", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "add"),
        ("F1_F2_L2_F3_1B_full_doc_ranking", ("decoupled", "minmax", "1024d", "1B", "full_doc_ranking", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "add"),
        ("F1_F2_L2_F3_1B_strict_firm_anchor", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "strict_firm_anchor", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "add"),
        ("F1_F2_L2_F3_1B_mul_f3", ("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64), (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), "F2_L2", "mul"),
    ]

    ablation_rows: dict[str, Any] = {}
    for name, pack_args, weights, f2v, f3v in ablation_specs:
        pack = _get_pack(*pack_args)
        res = evaluate_2a_config(bundle, pack, weights=weights, f2_variant=f2v, f3_variant=f3v)
        ablation_rows[name] = {
            **_clean_row(res),
            "scales_full": pack["scales_full"].to_dict(),
            "scales_clause": pack["scales_clause"].to_dict(),
            "dim_counts": pack["dim_counts"],
        }

    # 2. F3 (K, M) x (1A, 1B) x (gran_matched, full_doc_ranking) x (add, mul) sweep
    f3_sweep: list[dict[str, Any]] = []
    ranking_modes = ("gran_matched",) if bundle.granularity == "full_only" else ("gran_matched", "full_doc_ranking")
    for csrc in ("1A", "1B"):
        for rmode in ranking_modes:
            for k in K_SWEEP:
                for m in M_SWEEP:
                    pack = _get_pack("decoupled", "minmax", "1024d", csrc, rmode, "non_bb_directional", k, m)
                    for f3v in ("add", "mul"):
                        res_f3 = evaluate_2a_config(bundle, pack, weights=(0.0, 0.0, 1.0), f3_variant=f3v)
                        res_comp = evaluate_2a_config(bundle, pack, weights=(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), f2_variant="F2_L2", f3_variant=f3v)
                        f3_sweep.append(
                            {
                                "contrast_src": csrc,
                                "ranking_mode": rmode,
                                "K": k,
                                "M": m,
                                "f3_variant": f3v,
                                "f3_only": _clean_row(res_f3),
                                "composite_equal_weights": _clean_row(res_comp),
                            }
                        )

    best_f3_entry = max(
        f3_sweep,
        key=lambda r: (
            r["composite_equal_weights"]["oof_cv"]["f1"],
            r["composite_equal_weights"]["primary_aucs"]["roc_auc"],
            r["f3_only"]["primary_aucs"]["roc_auc"],
        ),
    )

    return {
        "ablations": ablation_rows,
        "f3_sweep_count": len(f3_sweep),
        "best_f3_config_by_composite_oof_f1": best_f3_entry,
        "f3_sweep": f3_sweep,
        "cal_oof_raw_summary": _get_pack("decoupled", "minmax", "1024d", "1B", "gran_matched", "non_bb_directional", 64, 64)["raw_oof_summary"],
    }


def evaluate_domain_granularity(
    domain: str,
    bundle: PromptBundle,
    cal_bundle: Mapping[str, Any],
    xray_1a: Mapping[str, Any],
    xray_1b: Mapping[str, Any],
    task011_summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Run complete Slice 3 replay evaluation for one (domain, granularity)."""
    ablations_and_f3 = run_ablation_and_f3_sweeps(domain, bundle, cal_bundle, xray_1a, xray_1b)
    best_f3 = ablations_and_f3["best_f3_config_by_composite_oof_f1"]

    # Candidate canonical decoupled packs to compete honestly under 5-Fold OOF CV
    candidate_defs = [
        ("1B_minmax_1024d_F2L2", "minmax", "1024d", "1B", "gran_matched", 64, 64, "F2_L2", "add"),
        ("1B_minmax_no_bb_global_F2L2", "minmax", "no_bb_global", "1B", "gran_matched", 64, 64, "F2_L2", "add"),
        ("1B_minmax_no_bb_domain_F2L2", "minmax", "no_bb_domain", "1B", "gran_matched", 64, 64, "F2_L2", "add"),
        ("1B_sigma3_1024d_F2L2", "sigma3", "1024d", "1B", "gran_matched", 64, 64, "F2_L2", "add"),
        ("1B_minmax_1024d_F2L1", "minmax", "1024d", "1B", "gran_matched", 64, 64, "F2_L1", "add"),
        ("1A_minmax_1024d_F2L2", "minmax", "1024d", "1A", "gran_matched", 64, 64, "F2_L2", "add"),
    ]
    bf3_tuple = (
        f"bestF3_{best_f3['contrast_src']}_{best_f3['ranking_mode']}_K{best_f3['K']}M{best_f3['M']}_{best_f3['f3_variant']}",
        "minmax",
        "1024d",
        str(best_f3["contrast_src"]),
        str(best_f3["ranking_mode"]),
        int(best_f3["K"]),
        int(best_f3["M"]),
        "F2_L2",
        str(best_f3["f3_variant"]),
    )
    if bf3_tuple[1:] not in [c[1:] for c in candidate_defs]:
        candidate_defs.append(bf3_tuple)
    if bundle.granularity == "clauses":
        fd_rank_tuple = ("1B_minmax_1024d_full_doc_rank_F2L2", "minmax", "1024d", "1B", "full_doc_ranking", 64, 64, "F2_L2", "add")
        if fd_rank_tuple[1:] not in [c[1:] for c in candidate_defs]:
            candidate_defs.append(fd_rank_tuple)

    candidate_results: dict[str, Any] = {}
    simplex_grids: dict[str, Any] = {}
    best_2a_name = ""
    best_2a_score = (-1.0, -1.0, -1.0)
    best_2a_state: dict[str, Any] = {}

    for cname, box_m, dim_m, csrc, rmode, k_val, m_val, f2v, f3v in candidate_defs:
        pack = build_chunk_and_cal_factors(
            domain, bundle, cal_bundle, xray_1a, xray_1b,
            cal_mode="decoupled", box_mode=box_m, dim_mask_mode=dim_m,
            contrast_src=csrc, ranking_mode=rmode, k=k_val, m=m_val,
        )
        grid_res = evaluate_simplex_weight_grid_oof(
            bundle, pack["chunk_factors"], pack["cal_oof_full"], pack["cal_oof_clause"],
            f2_variant=f2v, f3_variant=f3v,
        )
        simplex_grids[cname] = {
            "nested_weight_threshold_oof_cv": grid_res["nested_weight_threshold_oof_cv"],
            "nested_fold_choices": grid_res["nested_fold_choices"],
            "best_grid_row_by_oof_f1": grid_res["best_grid_row_by_oof_f1"],
            "grid_rows": grid_res["grid_rows"],
        }
        eq_res = evaluate_2a_config(bundle, pack, weights=(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0), f2_variant=f2v, f3_variant=f3v)
        cand_best_w = tuple(grid_res["best_grid_row_by_oof_f1"]["weights"])
        grid_best_res = evaluate_2a_config(bundle, pack, weights=cand_best_w, f2_variant=f2v, f3_variant=f3v)
        candidate_results[cname] = {
            "equal_weights": _clean_row(eq_res),
            "best_grid_weights": _clean_row(grid_best_res),
            "nested_oof_cv": grid_res["nested_weight_threshold_oof_cv"],
        }
        # Compare equal-weight canonical vs grid-selected using OOF CV F1 then ROC-AUC
        for label_w, res_w in (("eq", eq_res), ("grid", grid_best_res)):
            sc = (res_w["oof_cv"]["f1"], res_w["primary_aucs"]["roc_auc"], res_w["primary_aucs"]["pr_auc_reject"])
            if sc > best_2a_score:
                best_2a_score = sc
                best_2a_name = f"{cname}@{label_w}"
                best_2a_state = {"pack": pack, "res": res_w, "f2_variant": f2v, "f3_variant": f3v, "weights": tuple(res_w["weights"])}

    best_pack = best_2a_state["pack"]
    best_2a_res = best_2a_state["res"]
    best_w = best_2a_state["weights"]
    best_f2v = best_2a_state["f2_variant"]
    best_f3v = best_2a_state["f3_variant"]
    best_cf: ChunkFactors = best_pack["chunk_factors"]
    best_cscores: np.ndarray = best_2a_res["_chunk_scores"]

    # 3A Multi-Chunk comparison for clauses (hard_kill same_T vs decoupled_2d vs dual_zone)
    multi_chunk_3a: dict[str, Any] = {}
    best_2a_rule_res = best_2a_res
    best_2a_rule_name = "full_only"
    if bundle.granularity == "clauses":
        agg_2a = best_2a_res["_agg"]
        cal_full = best_pack["cal_oof_full"].composite(best_w, f2_variant=best_f2v, f3_variant=best_f3v)
        cal_cl = best_pack["cal_oof_clause"].composite(best_w, f2_variant=best_f2v, f3_variant=best_f3v)
        hk_2d = evaluate_2d_hard_kill_oof_cv(
            agg_2a["full_b64_min"], agg_2a["clause_min"], bundle.expected_pass, bundle.strat_folds
        )
        dz_cal = evaluate_cal_only_predictions(
            cal_full, cal_cl, agg_2a, bundle.expected_pass, "clauses", apply_veto=False, rule_mode="dual_zone"
        )
        dz_oof = evaluate_dual_zone_oof_cv(bundle, best_cscores, {
            "K1": np.zeros(best_cscores.size, dtype=bool),
            "K2": np.zeros(best_cscores.size, dtype=bool),
            "K3": np.zeros(best_cscores.size, dtype=bool),
            "any": np.zeros(best_cscores.size, dtype=bool),
        }, use_cap24=False, apply_veto=False)

        multi_chunk_3a = {
            "clauses_hard_kill_same_threshold": _clean_row(best_2a_res),
            "clauses_hard_kill_decoupled_2d": {
                "weights": list(best_w),
                "f2_variant": best_f2v,
                "f3_variant": best_f3v,
                "primary_aucs": best_2a_res["primary_aucs"],
                "all_continuous_aucs": best_2a_res["all_continuous_aucs"],
                "oof_cv": hk_2d["oof_cv"],
                "oracle_upper_bound": hk_2d["oracle_upper_bound"],
                "generalization_gap_f1": hk_2d["generalization_gap_f1"],
                "cal_only_p05": best_2a_res["cal_only_p05"],
                "cal_only_p10": best_2a_res["cal_only_p10"],
            },
            "clauses_dual_zone": {
                "weights": list(best_w),
                "f2_variant": best_f2v,
                "f3_variant": best_f3v,
                "primary_aucs": best_2a_res["primary_aucs"],
                "all_continuous_aucs": best_2a_res["all_continuous_aucs"],
                "cal_only_p05": _strip_preds(dz_cal["p05"]),
                "cal_only_p10": _strip_preds(dz_cal["p10"]),
                "oof_cv": dz_oof["oof_cv"],
                "fold_params": dz_oof["fold_params"],
                "oracle_upper_bound": dz_oof["oracle_upper_bound"],
                "generalization_gap_f1": dz_oof["generalization_gap_f1"],
            },
        }
        # Pick winning 3A rule by honest OOF F1
        candidates_3a = [
            ("clauses_hard_kill_same", best_2a_res["oof_cv"]["f1"], best_2a_res, best_2a_res["_oof_pred"], best_2a_res["_cal_p05_pred"], "hard_kill"),
            ("clauses_hard_kill_2d", hk_2d["oof_cv"]["f1"], multi_chunk_3a["clauses_hard_kill_decoupled_2d"], hk_2d["oof_pred"], best_2a_res["_cal_p05_pred"], "hard_kill_2d"),
            ("clauses_dual_zone", dz_oof["oof_cv"]["f1"], multi_chunk_3a["clauses_dual_zone"], dz_oof["oof_pred"], dz_cal["p05"]["pred"], "dual_zone"),
        ]
        win_name, _, win_row, win_oof_pred, win_cal_pred, win_mode = max(
            candidates_3a, key=lambda item: (item[1], 1 if item[0] == "clauses_dual_zone" else 0)
        )
        best_2a_rule_name = win_name
        best_2a_rule_res = {**win_row, "_oof_pred": win_oof_pred, "_cal_p05_pred": win_cal_pred, "_mode": win_mode}

    # 2B Kill-Switch Sweep (K1 x K2, plus K3 ablation on full_only)
    cal_full = best_pack["cal_oof_full"].composite(best_w, f2_variant=best_f2v, f3_variant=best_f3v)
    cal_cl = best_pack["cal_oof_clause"].composite(best_w, f2_variant=best_f2v, f3_variant=best_f3v)
    k1_k2_sweep: list[dict[str, Any]] = []
    best_2b_entry: dict[str, Any] | None = None
    best_2b_key = (-1.0, -1.0)

    for kb in K_BOX_SWEEP:
        for kn in K_NEG_SWEEP:
            vc = compute_chunk_veto_components(best_cf, k_box=kb, k_neg=kn, k_norm=None)
            agg_2b = aggregate_prompt_signals(bundle, best_cscores, vc, use_cap24=False)
            eff_scores = {
                kname: np.where(agg_2b["prompt_veto"], 0.0, s) for kname, s in agg_2b["continuous"].items()
            }
            primary_cont = "full_min_b64" if bundle.granularity == "full_only" else "min_all"
            aucs_2b = compute_auc_triple(bundle.expected_pass, eff_scores[primary_cont])

            # Direct apples-to-apples veto impact on 2A's winning OOF & CAL_ONLY predictions
            pred_oof_direct = best_2a_rule_res["_oof_pred"] & (~agg_2b["prompt_veto"])
            pred_cal05_direct = best_2a_rule_res["_cal_p05_pred"] & (~agg_2b["prompt_veto"])
            forensic_oof = compute_kill_switch_forensics(best_2a_rule_res["_oof_pred"], pred_oof_direct, agg_2b, bundle)
            forensic_cal05 = compute_kill_switch_forensics(best_2a_rule_res["_cal_p05_pred"], pred_cal05_direct, agg_2b, bundle)

            # Re-tuned 2B OOF CV (fitting thresholds with veto active)
            if bundle.granularity == "clauses" and best_2a_rule_res.get("_mode") == "dual_zone":
                retuned_oof = evaluate_dual_zone_oof_cv(bundle, best_cscores, vc, use_cap24=False, apply_veto=True)
                cal_2b = evaluate_cal_only_predictions(
                    cal_full, cal_cl, agg_2b, bundle.expected_pass, "clauses", apply_veto=True, rule_mode="dual_zone"
                )
            elif bundle.granularity == "clauses" and best_2a_rule_res.get("_mode") == "hard_kill_2d":
                retuned_oof = evaluate_2d_hard_kill_oof_cv(
                    agg_2b["full_b64_min"], agg_2b["clause_min"], bundle.expected_pass, bundle.strat_folds,
                    allowed_mask=~agg_2b["prompt_veto"],
                )
                cal_2b = evaluate_cal_only_predictions(
                    cal_full, cal_cl, agg_2b, bundle.expected_pass, "clauses", apply_veto=True, rule_mode="hard_kill"
                )
            else:
                retuned_oof = evaluate_1d_oof_cv(
                    agg_2b["continuous"][primary_cont], bundle.expected_pass, bundle.strat_folds,
                    allowed_mask=~agg_2b["prompt_veto"],
                )
                cal_2b = evaluate_cal_only_predictions(
                    cal_full, cal_cl, agg_2b, bundle.expected_pass, bundle.granularity, apply_veto=True, rule_mode="hard_kill"
                )

            entry = {
                "k_box": kb,
                "k_neg": kn,
                "k_norm": None,
                "veto_count_total": int(np.sum(agg_2b["prompt_veto"])),
                "primary_aucs": aucs_2b,
                "cal_only_p05": _strip_preds(cal_2b["p05"]),
                "cal_only_p10": _strip_preds(cal_2b["p10"]),
                "oof_cv_direct_veto": forensic_oof["metrics_2b"],
                "oof_cv_retuned": retuned_oof["oof_cv"],
                "oracle_upper_bound": retuned_oof["oracle_upper_bound"],
                "generalization_gap_f1": retuned_oof["generalization_gap_f1"],
                "forensics_oof_direct": forensic_oof,
                "forensics_cal05_direct": forensic_cal05,
                "_oof_pred_retuned": retuned_oof["oof_pred"],
                "_oof_pred_direct": pred_oof_direct,
                "_cal_p05_pred": cal_2b["p05"]["pred"],
                "_vc": vc,
                "_agg": agg_2b,
            }
            k1_k2_sweep.append(entry)
            sc_2b = (retuned_oof["oof_cv"]["f1"], aucs_2b["roc_auc"])
            if sc_2b > best_2b_key:
                best_2b_key = sc_2b
                best_2b_entry = entry

    assert best_2b_entry is not None

    # Conditional K3 ||x||_2 ablation on full_only (K1+K2 vs K1+K2+K3)
    k3_ablation: dict[str, Any] = {}
    if bundle.granularity == "full_only":
        base_kb = best_2b_entry["k_box"]
        base_kn = best_2b_entry["k_neg"]
        k3_rows: list[dict[str, Any]] = []
        for k_norm in K_NORM_SWEEP:
            vc_k3 = compute_chunk_veto_components(best_cf, k_box=base_kb, k_neg=base_kn, k_norm=k_norm)
            agg_k3 = aggregate_prompt_signals(bundle, best_cscores, vc_k3, use_cap24=False)
            pred_oof_k3_direct = best_2b_entry["_oof_pred_direct"] & (~agg_k3["prompt_veto"])
            forensic_vs_k1k2 = compute_kill_switch_forensics(best_2b_entry["_oof_pred_direct"], pred_oof_k3_direct, agg_k3, bundle)
            retuned_k3 = evaluate_1d_oof_cv(
                agg_k3["continuous"]["full_min_b64"], bundle.expected_pass, bundle.strat_folds,
                allowed_mask=~agg_k3["prompt_veto"],
            )
            eff_s = np.where(agg_k3["prompt_veto"], 0.0, agg_k3["continuous"]["full_min_b64"])
            k3_rows.append(
                {
                    "k_box": base_kb,
                    "k_neg": base_kn,
                    "k_norm": k_norm,
                    "primary_aucs": compute_auc_triple(bundle.expected_pass, eff_s),
                    "oof_cv_direct": forensic_vs_k1k2["metrics_2b"],
                    "oof_cv_retuned": retuned_k3["oof_cv"],
                    "delta_vs_k1_k2_direct": forensic_vs_k1k2["delta"],
                    "k3_exclusive_catches": forensic_vs_k1k2["exclusive_attacks_caught_only_by_veto"],
                    "k3_added_false_rejections": forensic_vs_k1k2["in_domain_false_rejections_added_by_veto"],
                    "verdict": (
                        "helps"
                        if retuned_k3["oof_cv"]["f1"] > best_2b_entry["oof_cv_retuned"]["f1"] + 1e-12
                        else ("hurts" if retuned_k3["oof_cv"]["f1"] < best_2b_entry["oof_cv_retuned"]["f1"] - 1e-12 else "neutral")
                    ),
                }
            )
        k3_ablation = {
            "baseline_k1_k2": {"k_box": base_kb, "k_neg": base_kn, "oof_cv_retuned": best_2b_entry["oof_cv_retuned"]},
            "k3_sweep": k3_rows,
        }

    # Informative cap=24 telemetry on best clauses 2A and 2B models
    cap24_telemetry: dict[str, Any] = {}
    if bundle.granularity == "clauses":
        empty_vc = {
            "K1": np.zeros(best_cscores.size, dtype=bool),
            "K2": np.zeros(best_cscores.size, dtype=bool),
            "K3": np.zeros(best_cscores.size, dtype=bool),
            "any": np.zeros(best_cscores.size, dtype=bool),
        }
        flood_mask = np.array([s == "long_context_flooding" for s in bundle.subtypes], dtype=bool)
        total_chunks_uncapped = int(bundle.chunk_vectors.shape[0])
        flood_uncapped = sum(
            1 + int(bundle.b64_chunk_slices[p].size) + int(bundle.clause_chunk_slices[p].size)
            for p in np.flatnonzero(flood_mask)
        )
        flood_capped = sum(
            1 + int(bundle.b64_chunk_slices[p].size) + int(bundle.clause_cap24_slices[p].size)
            for p in np.flatnonzero(flood_mask)
        )

        def _run_cap24(vc_use: Mapping[str, np.ndarray], apply_veto: bool, uncapped_oof: Mapping[str, Any]) -> dict[str, Any]:
            agg_cap = aggregate_prompt_signals(bundle, best_cscores, vc_use, use_cap24=True)
            if best_2a_rule_res.get("_mode") == "dual_zone":
                cap_oof = evaluate_dual_zone_oof_cv(bundle, best_cscores, vc_use, use_cap24=True, apply_veto=apply_veto)
            elif best_2a_rule_res.get("_mode") == "hard_kill_2d":
                cap_oof = evaluate_2d_hard_kill_oof_cv(
                    agg_cap["full_b64_min"], agg_cap["clause_min"], bundle.expected_pass, bundle.strat_folds,
                    allowed_mask=(~agg_cap["prompt_veto"]) if apply_veto else None,
                )
            else:
                cap_oof = evaluate_1d_oof_cv(
                    agg_cap["continuous"]["min_all"], bundle.expected_pass, bundle.strat_folds,
                    allowed_mask=(~agg_cap["prompt_veto"]) if apply_veto else None,
                )
            m_unc = uncapped_oof
            m_cap = cap_oof["oof_cv"]
            total_cap = int(agg_cap["evaluated_chunks"])
            return {
                "uncapped_oof_cv": m_unc,
                "cap24_oof_cv": m_cap,
                "delta_frr": float(m_cap["frr"] - m_unc["frr"]),
                "delta_far": float(m_cap["far"] - m_unc["far"]),
                "delta_f1": float(m_cap["f1"] - m_unc["f1"]),
                "total_chunks_uncapped": total_chunks_uncapped,
                "total_chunks_cap24": total_cap,
                "pct_chunks_saved_overall": float(100.0 * (total_chunks_uncapped - total_cap) / total_chunks_uncapped),
                "flooding_chunks_uncapped": flood_uncapped,
                "flooding_chunks_cap24": flood_capped,
                "pct_chunks_saved_long_context_flooding": float(100.0 * (flood_uncapped - flood_capped) / max(flood_uncapped, 1)),
            }

        cap24_telemetry = {
            "best_2a": _run_cap24(empty_vc, False, best_2a_rule_res["oof_cv"]),
            "best_2b": _run_cap24(best_2b_entry["_vc"], True, best_2b_entry["oof_cv_retuned"]),
        }

    # Per-quadrant and per-subtype breakdown vs TASK-011
    t011_breakdown = compute_quadrant_and_subtype_breakdown(
        bundle.expected_pass, bundle.baseline_passed, bundle.categories, bundle.subtypes
    )
    best_2a_oof_bd = compute_quadrant_and_subtype_breakdown(
        bundle.expected_pass, best_2a_rule_res["_oof_pred"], bundle.categories, bundle.subtypes
    )
    best_2a_cal_bd = compute_quadrant_and_subtype_breakdown(
        bundle.expected_pass, best_2a_rule_res["_cal_p05_pred"], bundle.categories, bundle.subtypes
    )
    best_2b_oof_bd = compute_quadrant_and_subtype_breakdown(
        bundle.expected_pass, best_2b_entry["_oof_pred_retuned"], bundle.categories, bundle.subtypes
    )
    best_2b_cal_bd = compute_quadrant_and_subtype_breakdown(
        bundle.expected_pass, best_2b_entry["_cal_p05_pred"], bundle.categories, bundle.subtypes
    )

    return {
        "domain": domain,
        "granularity": bundle.granularity,
        "task011_baseline": {
            "stored_confusion": task011_summary["confusion"],
            "verified_breakdown": t011_breakdown,
        },
        "ablations_and_f3": ablations_and_f3,
        "simplex_weight_grids": simplex_grids,
        "candidate_summaries": candidate_results,
        "best_2a": {
            "config_name": best_2a_name,
            "rule_name": best_2a_rule_name,
            "nested_weight_threshold_oof_cv": simplex_grids[best_2a_name.split("@", 1)[0]]["nested_weight_threshold_oof_cv"],
            "equal_weights_oof_cv": candidate_results[best_2a_name.split("@", 1)[0]]["equal_weights"]["oof_cv"],
            "scales_full": best_pack["scales_full"].to_dict(),
            "scales_clause": best_pack["scales_clause"].to_dict(),
            "dim_counts": best_pack["dim_counts"],
            **_clean_row(best_2a_rule_res),
        },
        "multi_chunk_3a_comparison": multi_chunk_3a,
        "kill_switch_2b": {
            "sweep": [_clean_row(r) for r in k1_k2_sweep],
            "best_2b": _clean_row(best_2b_entry),
            "k3_norm_ablation": k3_ablation,
        },
        "cap24_telemetry": cap24_telemetry,
        "quadrant_and_subtype_comparison": {
            "task011_m0": t011_breakdown,
            "best_2a_oof_cv": best_2a_oof_bd,
            "best_2a_cal_only_p05": best_2a_cal_bd,
            "best_2b_oof_cv": best_2b_oof_bd,
            "best_2b_cal_only_p05": best_2b_cal_bd,
        },
    }


def run_simulation(
    lancedb_uri: Path,
    benchmarks_dir: Path,
    xray_1a_path: Path,
    xray_1b_path: Path,
) -> dict[str, Any]:
    """Execute full Slice 3 offline replay simulation across python & receta (full_only & clauses)."""
    xray_1a = json.loads(xray_1a_path.read_text(encoding="utf-8"))
    xray_1b = json.loads(xray_1b_path.read_text(encoding="utf-8"))
    db = lancedb.connect(str(lancedb_uri))
    runs = load_lancedb_benchmark_runs(db)

    results: dict[str, Any] = {
        "dtype": "float64",
        "dim": DIM,
        "xray_1a_source": str(xray_1a_path),
        "xray_1b_source": str(xray_1b_path),
        "domains": {},
    }

    for domain in ("python", "receta"):
        v1_pid = V1_PROFILES[domain]
        v2_pid = V2_PROFILES[domain]
        subtypes_map, categories_map, expected_map = load_benchmark_metadata(benchmarks_dir / f"{domain}.jsonl")
        cal_bundle = load_lancedb_calibration_bundle(db, v1_pid)

        v2_full_run = runs[(v2_pid, "full_only", "m0")]
        norm_stats = xray_1a["pre_l2_norm_check"][domain]["calibration_full_doc"]
        cal_norm_mean = float(norm_stats["cal_norm_mean"])
        cal_norm_std = float(norm_stats["cal_norm_std"])

        gran_reports: dict[str, Any] = {}
        for gran in ("full_only", "clauses"):
            v1_run = runs[(v1_pid, gran, "m0")]
            bundle = load_prompt_bundle(
                db,
                v1_run["run_id"],
                gran,
                subtypes_map,
                categories_map,
                expected_map,
                v2_run_id=v2_full_run["run_id"] if gran == "full_only" else None,
                cal_norm_mean=cal_norm_mean if gran == "full_only" else None,
                cal_norm_std=cal_norm_std if gran == "full_only" else None,
            )
            # Verify 100% parity against TASK-011 stored summary_metrics
            verified_m = compute_confusion_metrics(bundle.expected_pass, bundle.baseline_passed)
            stored_conf = v1_run["summary_metrics"]["confusion"]
            if (
                verified_m["tp"] != stored_conf["tp"]
                or verified_m["fp"] != stored_conf["fp"]
                or verified_m["fn"] != stored_conf["fn"]
                or verified_m["tn"] != stored_conf["tn"]
            ):
                raise RuntimeError(f"TASK-011 baseline parity mismatch for {domain}/{gran}")

            gran_reports[gran] = evaluate_domain_granularity(
                domain, bundle, cal_bundle, xray_1a, xray_1b, v1_run["summary_metrics"]
            )

        results["domains"][domain] = {
            "v1_profile_id": v1_pid,
            "v2_profile_id": v2_pid,
            "calibration_counts": cal_bundle["counts"],
            "v2_cal_norm_stats": {"cal_norm_mean": cal_norm_mean, "cal_norm_std": cal_norm_std},
            "granularities": gran_reports,
        }

    return results


def _fmt_metrics_line(label: str, m: Mapping[str, Any]) -> str:
    return (
        f"  {label:<24} F1={m['f1']:.4f} FRR={m['frr']:.4f} FAR={m['far']:.4f} "
        f"(TP={m['tp']:2d} FN={m['fn']:2d} TN={m['tn']:3d} FP={m['fp']:3d})"
    )


def format_stdout_summary(report: Mapping[str, Any]) -> str:
    """Render concise headline tables covering ablations, 2A vs 2B, 3A, cap=24, and subtypes."""
    lines: list[str] = ["=== FHV1.1 Phase 2 Offline Replay Summary (np.float64, 1024D) ==="]
    for domain in ("python", "receta"):
        dom = report["domains"][domain]
        for gran in ("full_only", "clauses"):
            g = dom["granularities"][gran]
            b2a = g["best_2a"]
            b2b = g["kill_switch_2b"]["best_2b"]
            t011 = g["task011_baseline"]["stored_confusion"]
            aucs_2a = b2a["primary_aucs"]
            aucs_2b = b2b["primary_aucs"]

            lines.append(f"\n[{domain} / {gran}] best_2a={b2a['config_name']} ({b2a['rule_name']}) | best_2b=(K_box={b2b['k_box']}, K_neg={b2b['k_neg']})")
            lines.append(f"  TASK-011 m0             F1={t011['f1']:.4f} FRR={t011['frr_fnr']:.4f} FAR={t011['far_fpr']:.4f} (TP={t011['tp']:2d} FN={t011['fn']:2d} TN={t011['tn']:3d} FP={t011['fp']:3d})")
            lines.append(f"  2A AUCs                 ROC={aucs_2a['roc_auc']:.4f} PR(in)={aucs_2a['pr_auc_in_domain']:.4f} PR(rej)={aucs_2a['pr_auc_reject']:.4f} gap={b2a['generalization_gap_f1']:+.4f}")
            lines.append(_fmt_metrics_line("2A CAL_ONLY(p05)", b2a["cal_only_p05"]))
            lines.append(_fmt_metrics_line("2A CAL_ONLY(p10)", b2a["cal_only_p10"]))
            lines.append(_fmt_metrics_line("2A EqualW OOF CV", b2a["equal_weights_oof_cv"]))
            lines.append(_fmt_metrics_line("2A Nested(W+T) OOF CV", b2a["nested_weight_threshold_oof_cv"]))
            lines.append(_fmt_metrics_line("2A 5-Fold OOF CV", b2a["oof_cv"]))
            lines.append(_fmt_metrics_line("2A [ORACLE_UPPER_BOUND]", b2a["oracle_upper_bound"]))
            lines.append(f"  2B AUCs                 ROC={aucs_2b['roc_auc']:.4f} PR(in)={aucs_2b['pr_auc_in_domain']:.4f} PR(rej)={aucs_2b['pr_auc_reject']:.4f} gap={b2b['generalization_gap_f1']:+.4f}")
            lines.append(_fmt_metrics_line("2B CAL_ONLY(p05)", b2b["cal_only_p05"]))
            lines.append(_fmt_metrics_line("2B 5-Fold OOF(direct)", b2b["oof_cv_direct_veto"]))
            lines.append(_fmt_metrics_line("2B 5-Fold OOF(retuned)", b2b["oof_cv_retuned"]))

            f_oof = b2b["forensics_oof_direct"]
            lines.append(
                f"  2B Forensics(OOF dir)   dF1={f_oof['delta']['delta_f1']:+.4f} "
                f"excl_catches={f_oof['exclusive_attacks_caught_only_by_veto']['count']} "
                f"added_in_domain_fn={f_oof['in_domain_false_rejections_added_by_veto']['count']} "
                f"excl_by_cat={f_oof['exclusive_attacks_caught_only_by_veto']['by_category']}"
            )
            if gran == "clauses":
                c24 = g["cap24_telemetry"]
                for tag in ("best_2a", "best_2b"):
                    r = c24[tag]
                    lines.append(
                        f"  cap=24 ({tag})        dF1={r['delta_f1']:+.4f} dFRR={r['delta_frr']:+.4f} dFAR={r['delta_far']:+.4f} "
                        f"saved={r['pct_chunks_saved_overall']:.2f}% flood_saved={r['pct_chunks_saved_long_context_flooding']:.2f}%"
                    )
            elif "k3_sweep" in g["kill_switch_2b"]["k3_norm_ablation"]:
                for k3r in g["kill_switch_2b"]["k3_norm_ablation"]["k3_sweep"]:
                    lines.append(
                        f"  K3(||x||_2) K_norm={k3r['k_norm']} verdict={k3r['verdict']} "
                        f"retuned_F1={k3r['oof_cv_retuned']['f1']:.4f} dF1_dir={k3r['delta_vs_k1_k2_direct']['delta_f1']:+.4f} "
                        f"excl={k3r['k3_exclusive_catches']['count']} false_rej={k3r['k3_added_false_rejections']['count']}"
                    )

            qbd = g["quadrant_and_subtype_comparison"]
            lines.append("  Quadrants (pass_rate):  [TASK-011] vs [2A OOF] vs [2B OOF]")
            for cat in BENCHMARK_CATEGORIES:
                r0 = qbd["task011_m0"]["by_category"][cat]["pass_rate"]
                r1 = qbd["best_2a_oof_cv"]["by_category"][cat]["pass_rate"]
                r2 = qbd["best_2b_oof_cv"]["by_category"][cat]["pass_rate"]
                lines.append(f"    {cat:<24} {r0:.3f} -> {r1:.3f} -> {r2:.3f}")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FHV1.1 Phase 2 Offline Replay Simulator (RFC-003 float64).")
    parser.add_argument("--mode", choices=("default", "v2", "v3"), default="default")
    parser.add_argument("--lancedb-uri", type=Path, default=Path("data/sf-lancedb"))
    parser.add_argument("--benchmarks-dir", type=Path, default=Path("data/fhv1_benchmarks"))
    parser.add_argument("--xray-1a", type=Path, default=Path("/tmp/fhv1_1_id/xray_1a.json"))
    parser.add_argument("--xray-1b", type=Path, default=Path("/tmp/fhv1_1_id/xray_1b.json"))
    parser.add_argument("--xray-v2", type=Path, default=Path("/tmp/fhv1_1_id_v2/xray_v2.json"))
    parser.add_argument("--bg-parquet", type=Path, default=Path("data/fhv1_1_research/background_embeddings_1k.parquet"))
    parser.add_argument("--augmented-dir", type=Path, default=Path("data/fhv1_augmented"))
    parser.add_argument("--task012-report", type=Path, default=Path("reports/fhv1_1_xray_and_replay_report.md"))
    parser.add_argument("--task013-report", type=Path, default=Path("reports/fhv1_1_id_v2_report.md"))
    parser.add_argument("--task011-report", type=Path, default=Path("reports/fhv1_task011_empirical_report.md"))
    parser.add_argument("--out", type=Path, default=Path("/tmp/fhv1_1_id/replay_results.json"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.mode == "v3":
        import fhv1_1_replay_v3 as replay_v3

        out_dir = args.out
        if out_dir.suffix == ".json":
            out_dir = Path("/tmp/fhv1_1_id_v3")
        bg_parquet = args.bg_parquet
        legacy_bg = Path("data/fhv1_1_research/background_embeddings_1k.parquet")
        if bg_parquet == legacy_bg:
            bg_parquet = Path("data/fhv1_1_research/background_embeddings_1200.parquet")
        text = replay_v3.run_replay_v3(
            lancedb_uri=args.lancedb_uri,
            benchmarks_dir=args.benchmarks_dir,
            bg_parquet=bg_parquet,
            augmented_dir=args.augmented_dir,
            task012_report=args.task012_report,
            task013_report=args.task013_report,
            out_dir=out_dir,
        )
        print(text)
        print(f"\nWrote {out_dir}")
        return 0
    if args.mode == "v2":
        import fhv1_1_replay_v2 as replay_v2

        report = replay_v2.run_replay_v2(
            lancedb_uri=args.lancedb_uri,
            benchmarks_dir=args.benchmarks_dir,
            xray_v2_path=args.xray_v2,
            bg_parquet=args.bg_parquet,
            task012_report=args.task012_report,
            task011_report=args.task011_report,
        )
        text = replay_v2.format_v2_summary(report)
        payload = json.dumps(report, indent=2, allow_nan=False)
    else:
        report = run_simulation(args.lancedb_uri, args.benchmarks_dir, args.xray_1a, args.xray_1b)
        text = format_stdout_summary(report)
        payload = json.dumps(report, indent=2)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8")
    print(text)
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
