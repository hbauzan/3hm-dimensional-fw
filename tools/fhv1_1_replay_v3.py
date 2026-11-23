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
"""v3 replay: all-1024 directional dials, structural hook, document CAL_ONLY.

Directional margins use the contrast ``std_pool`` from ``coordinate_contrast_stats``
and ``fhv1_1_replay_sim.EPS_SIGMA`` in the denominator. Geometry channels call the
existing Tail-Z, F2_L2, and ``positive_f3_bonus`` implementations. ``polarity_v2_subset``
calls ``polarity_score`` on the ``POLARITY_FLIP_DIALS`` mask from ``classify_dimensions_v2``.

Empty matrices and non-finite inputs raise ``ValueError``. Public score arrays are
finite. JSON for the sweep is written only under the caller-supplied directory.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import fhv1_1_lexical_profile as lex
import fhv1_1_replay_sim as sim
import fhv1_1_replay_v2 as v2
import fhv1_1_xray as xray

DIR_VARIANTS: tuple[str, ...] = (
    "dir1024_sig_sep",
    "dir1024_sig_sep2",
    "dir1024_clip_polboost",
)
GUARDS: tuple[str, ...] = ("f2_l2", "tail_p5", "tail_p10", "tail_p25")
BASELINES: tuple[str, ...] = (
    "polarity_v2_subset",
    "base_repaired",
    "f2_l2",
    "tail_p3",
    "tail_p5",
    "tail_p10",
    "tail_p25",
)
TAIL_P: tuple[int, ...] = (3, 5, 10, 25)
ALPHAS: tuple[float, ...] = (0.00, 0.05, 0.10, 0.15, 0.20, 0.30)
BETAS: tuple[float, ...] = (0.00, 0.05, 0.10, 0.15, 0.20, 0.30)
GAMMAS: tuple[float, ...] = (0.10, 0.25, 0.50)
W_F: tuple[float, ...] = (0.20, 0.35, 0.50, 0.70)
PRESETS: tuple[str, ...] = ("1B_base_tech", "1B_base_tech_noise", "1B_full", "1B_full_v3")
PROB_TAGS: tuple[tuple[float, str], ...] = ((0.05, "p05"), (0.10, "p10"), (0.15, "p15"))
BOOTSTRAP_PROBABILITY = 0.10
CANARY_RE = re.compile(r"\b(?:sqlite3|subprocess|json)\b", re.IGNORECASE)
FOCUS_SUBTYPES: tuple[str, ...] = ("smuggle_recipe_footnote", "dilution_80_20")
QUADRANT_NAMES: tuple[str, ...] = (
    "IN_DOMAIN_VALID",
    "OUT_OF_DOMAIN_BENIGN",
    "HYBRID_BOUNDARY",
    "ADVERSARIAL_FUZZING",
)

# Parsed from reports/fhv1_1_id_v2_report.md section 7.1. The loader checks the file
# against these strings and stops if the published cell does not match.
TASK013_CAL_P10_F1: dict[tuple[str, str], str] = {
    ("python", "full_only"): "0.6338028169014085",
    ("python", "clauses"): "0.6714801444043321",
    ("receta", "full_only"): "0.7403846153846154",
    ("receta", "clauses"): "0.7981220657276995",
}
TASK013_REPEATED_F1: dict[tuple[str, str], str] = {
    ("python", "full_only"): "0.6277631674623869",
    ("python", "clauses"): "0.6922652099467881",
    ("receta", "full_only"): "0.7513565819177839",
    ("receta", "clauses"): "0.7845709402740869",
}

_CAL_P10_RE = re.compile(
    r"^\| `(?P<cell>python/full_only|python/clauses|receta/full_only|receta/clauses)` \| "
    r"`(?P<f1>\d+\.\d{10,})` \| `(?P<frr>\d+\.\d+)` \| `(?P<far>\d+\.\d+)` \|"
)
_REPEATED_F1_RE = re.compile(
    r"^\| `(?P<cell>python/full_only|python/clauses|receta/full_only|receta/clauses)` \| `f1` \| "
    r"`(?P<mean>\d+\.\d+)` \| `(?P<std>\d+\.\d+(?:e[+-]?\d+)?)` \|"
)


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _as_f64_matrix(values: np.ndarray, *, name: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError(f"{name} must be a non-empty 2D matrix, got {matrix.shape}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"non-finite value in {name}")
    return matrix


def _sigmoid(margin: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(margin, dtype=np.float64), -60.0, 60.0)
    return np.float64(1.0) / (np.float64(1.0) + np.exp(-clipped))


@dataclass(frozen=True)
class DirectionalFit:
    """Per-coordinate direction, midpoint, pooled std, and separation."""

    mu_t: np.ndarray
    std_t: np.ndarray
    mu_c: np.ndarray
    std_c: np.ndarray
    std_pool: np.ndarray
    sep: np.ndarray
    direction: np.ndarray
    midpoint: np.ndarray
    tie_count: int

    @property
    def dim(self) -> int:
        return int(self.direction.shape[0])


def fit_directional(mu_t: np.ndarray, std_t: np.ndarray, mu_c: np.ndarray, std_c: np.ndarray) -> DirectionalFit:
    """Fit one directional dial on already-computed sample moments.

    ``direction`` is ``sign(mu_T - mu_C)`` and is 0 only when the two means are
    exactly equal. ``sep`` is the ``coordinate_contrast_stats`` separation.
    """
    target_mean = np.asarray(mu_t, dtype=np.float64)
    target_std = np.asarray(std_t, dtype=np.float64)
    contrast_mean = np.asarray(mu_c, dtype=np.float64)
    contrast_std = np.asarray(std_c, dtype=np.float64)
    shape = target_mean.shape
    if target_std.shape != shape or contrast_mean.shape != shape or contrast_std.shape != shape:
        raise ValueError("directional moments differ in shape")
    if shape[0] == 0:
        raise ValueError("directional fit needs at least one coordinate")
    stacked = np.stack((target_mean, target_std, contrast_mean, contrast_std))
    if not np.all(np.isfinite(stacked)):
        raise ValueError("non-finite directional moment")
    std_pool = np.sqrt((target_std * target_std + contrast_std * contrast_std) / np.float64(2.0))
    _, _, _, _, sep, _ = xray.coordinate_contrast_stats(target_mean, target_std, contrast_mean, contrast_std)
    direction = np.sign(target_mean - contrast_mean)
    return DirectionalFit(
        mu_t=target_mean,
        std_t=target_std,
        mu_c=contrast_mean,
        std_c=contrast_std,
        std_pool=std_pool,
        sep=np.asarray(sep, dtype=np.float64),
        direction=np.asarray(direction, dtype=np.float64),
        midpoint=np.float64(0.5) * (target_mean + contrast_mean),
        tie_count=int(np.sum(direction == 0.0)),
    )


def fit_directional_matrices(target: np.ndarray, contrast: np.ndarray) -> DirectionalFit:
    """Sample moments (ddof=1) of two normalize=true matrices. Holdout rows stay out."""
    target_m = _as_f64_matrix(target, name="calibration")
    contrast_m = _as_f64_matrix(contrast, name="background")
    if target_m.shape[1] != contrast_m.shape[1]:
        raise ValueError(f"directional matrices {target_m.shape} vs {contrast_m.shape}")
    dim = int(target_m.shape[1])
    target_moments = xray.compute_coordinate_moments(target_m, expected_dim=dim)
    contrast_moments = xray.compute_coordinate_moments(contrast_m, expected_dim=dim)
    return fit_directional(
        target_moments.mean,
        target_moments.std_dev_sample,
        contrast_moments.mean,
        contrast_moments.std_dev_sample,
    )


def directional_margin(vectors: np.ndarray, fit: DirectionalFit) -> np.ndarray:
    """``u_d = dir_d * (x_d - m_d) / (std_pool_d + EPS_SIGMA)`` for every row."""
    matrix = _as_f64_matrix(vectors, name="vectors")
    if matrix.shape[1] != fit.dim:
        raise ValueError(f"vectors dim {matrix.shape[1]} != fit dim {fit.dim}")
    return fit.direction * (matrix - fit.midpoint) / (fit.std_pool + np.float64(sim.EPS_SIGMA))


def variant_weights(fit: DirectionalFit, variant: str) -> np.ndarray:
    """Strictly positive weights on every coordinate of one directional variant."""
    if variant == "dir1024_sig_sep":
        weights = np.maximum(fit.sep, np.float64(0.05))
    elif variant == "dir1024_sig_sep2":
        weights = np.maximum(fit.sep * fit.sep, np.float64(0.01))
    elif variant == "dir1024_clip_polboost":
        boost = np.where(fit.mu_t * fit.mu_c < np.float64(0.0), np.float64(1.5), np.float64(1.0))
        weights = np.maximum(fit.sep, np.float64(0.05)) * boost
    else:
        raise ValueError(f"unknown directional variant {variant}")
    if weights.shape != (fit.dim,) or np.any(weights <= np.float64(0.0)) or not np.all(np.isfinite(weights)):
        raise RuntimeError(f"{variant} weights are not strictly positive and finite")
    return weights


def score_dir1024(vectors: np.ndarray, fit: DirectionalFit, variant: str) -> np.ndarray:
    """Score every row. Same-sign coordinates stay in the weighted sum."""
    margin = directional_margin(vectors, fit)
    weights = variant_weights(fit, variant)
    if variant in ("dir1024_sig_sep", "dir1024_sig_sep2"):
        atom = _sigmoid(margin)
    else:
        atom = np.clip(np.float64(0.5) + np.float64(0.5) * margin, np.float64(0.0), np.float64(1.0))
    scores = (atom * weights).sum(axis=1) / np.sum(weights)
    if not np.all(np.isfinite(scores)):
        raise RuntimeError(f"non-finite {variant} score")
    return scores


def couple_additive(s_dir: np.ndarray, s_guard: np.ndarray, alpha: float) -> np.ndarray:
    """``(1 - alpha) * S_dir + alpha * S_guard``. Alpha 0 is exactly ``S_dir``."""
    left = np.asarray(s_dir, dtype=np.float64)
    right = np.asarray(s_guard, dtype=np.float64)
    if left.shape != right.shape:
        raise ValueError("additive guard shapes differ")
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise ValueError("non-finite guard input")
    weight = np.float64(alpha)
    if weight == np.float64(0.0):
        return np.array(left, dtype=np.float64, copy=True)
    return (np.float64(1.0) - weight) * left + weight * right


def couple_multiplicative(s_dir: np.ndarray, s_guard: np.ndarray, alpha: float) -> np.ndarray:
    """``S_dir ** (1 - alpha) * S_guard ** alpha``. Alpha 0 is exactly ``S_dir``."""
    left = np.asarray(s_dir, dtype=np.float64)
    right = np.asarray(s_guard, dtype=np.float64)
    if left.shape != right.shape:
        raise ValueError("multiplicative guard shapes differ")
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise ValueError("non-finite guard input")
    weight = np.float64(alpha)
    if weight == np.float64(0.0):
        return np.array(left, dtype=np.float64, copy=True)
    base_dir = np.clip(left, np.float64(0.0), np.float64(1.0))
    base_guard = np.clip(right, np.float64(0.0), np.float64(1.0))
    coupled = np.power(base_dir, np.float64(1.0) - weight) * np.power(base_guard, weight)
    if not np.all(np.isfinite(coupled)):
        raise RuntimeError("non-finite multiplicative guard")
    return coupled


def apply_beta_struct(s_sem: np.ndarray, s_struct: np.ndarray, beta: float) -> np.ndarray:
    """``S_sem * (1 - beta * (1 - S_struct))``. ``S_struct == 1`` leaves ``S_sem``."""
    semantic = np.asarray(s_sem, dtype=np.float64)
    struct = np.asarray(s_struct, dtype=np.float64)
    if semantic.shape != struct.shape:
        raise ValueError("beta hook shapes differ")
    if not np.all(np.isfinite(semantic)) or not np.all(np.isfinite(struct)):
        raise ValueError("non-finite structural hook input")
    hooked = semantic * (np.float64(1.0) - np.float64(beta) * (np.float64(1.0) - struct))
    if not np.all(np.isfinite(hooked)):
        raise RuntimeError("non-finite beta hook")
    return hooked


def apply_gamma_struct(s_sem: np.ndarray, s_struct: np.ndarray, gamma: float) -> np.ndarray:
    """``S_sem * (S_struct ** gamma)``. ``S_struct == 1`` leaves ``S_sem``."""
    semantic = np.asarray(s_sem, dtype=np.float64)
    struct = np.asarray(s_struct, dtype=np.float64)
    if semantic.shape != struct.shape:
        raise ValueError("gamma hook shapes differ")
    if not np.all(np.isfinite(semantic)) or not np.all(np.isfinite(struct)):
        raise ValueError("non-finite structural hook input")
    if np.any(struct < np.float64(0.0)):
        raise ValueError("S_struct must be >= 0 before the power hook")
    hooked = semantic * np.power(struct, np.float64(gamma))
    if not np.all(np.isfinite(hooked)):
        raise RuntimeError("non-finite gamma hook")
    return hooked


def struct_reductions(full_score: float, clause_scores: Sequence[float]) -> tuple[float, float]:
    """Return ``S_struct(full_doc)`` and ``min(full_doc, min clause)``.

    An empty clause list has no poisoned clause, so the clause minimum is 1.
    """
    full = float(full_score)
    if not np.isfinite(full):
        raise ValueError("non-finite full-document S_struct")
    if len(clause_scores) == 0:
        return full, full if full < 1.0 else min(full, 1.0)
    clause = np.asarray(list(clause_scores), dtype=np.float64)
    if not np.all(np.isfinite(clause)):
        raise ValueError("non-finite clause S_struct")
    reduced = min(full, float(np.min(clause)))
    return full, reduced


def anchor_drop_dims(sep: np.ndarray, polarity_dims: Sequence[int]) -> np.ndarray:
    """Drop coordinates with ``sep < 1``. A sign-flip anchor with ``sep >= 1`` stays.

    Polarity membership is not a reason to drop. The returned indices are the
    ``drop_dims`` argument of ``positive_f3_bonus``.
    """
    separation = np.asarray(sep, dtype=np.float64)
    if separation.ndim != 1 or separation.shape[0] == 0:
        raise ValueError("sep must be a non-empty coordinate vector")
    if not np.all(np.isfinite(separation)):
        raise ValueError("non-finite sep")
    drop = [dim for dim in range(separation.shape[0]) if separation[dim] < np.float64(1.0)]
    drop_set = set(drop)
    for raw in polarity_dims:
        dim = int(raw)
        if dim < 0 or dim >= separation.shape[0]:
            raise ValueError(f"polarity dim {dim} outside 0..{separation.shape[0] - 1}")
        if separation[dim] >= np.float64(1.0) and dim in drop_set:
            raise RuntimeError(f"sign-flip anchor {dim} was dropped")
    return np.array(drop, dtype=np.int64)


def base_repaired_from_factors(f1: np.ndarray, f2: np.ndarray, f3: np.ndarray) -> np.ndarray:
    """Equal mean of F1, F2_L2, and the repaired positive F3 bonus."""
    parts = [np.asarray(f1, dtype=np.float64), np.asarray(f2, dtype=np.float64), np.asarray(f3, dtype=np.float64)]
    if parts[0].shape != parts[1].shape or parts[0].shape != parts[2].shape:
        raise ValueError("base_repaired factors differ in shape")
    stacked = np.stack(parts)
    if not np.all(np.isfinite(stacked)):
        raise ValueError("non-finite base_repaired factor")
    return np.mean(stacked, axis=0)


def polarity_v2_subset(vectors: np.ndarray, classification: Mapping[str, Any]) -> np.ndarray:
    """``polarity_score`` on the ``POLARITY_FLIP_DIALS`` mask. Does not reimplement it."""
    dial_idx, dial_mu = v2.dials_from_classification(classification)
    return v2.polarity_score(vectors, dial_idx, dial_mu)


def map_f1(raw_mean_e: np.ndarray, scale: float) -> np.ndarray:
    """F1 map used by ``normalize_factors`` once the scale is already floored."""
    raw = np.asarray(raw_mean_e, dtype=np.float64)
    return np.clip(np.exp(-raw / np.float64(scale)), np.float64(0.0), np.float64(1.0))


def map_f2_l2(raw_z2: np.ndarray, scale: float) -> np.ndarray:
    """F2_L2 map used by ``normalize_factors`` once the scale is already floored."""
    raw = np.asarray(raw_z2, dtype=np.float64)
    return np.clip(np.exp(-raw / np.float64(scale)), np.float64(0.0), np.float64(1.0))


def tail_channel(vectors: np.ndarray, mu: np.ndarray, sigma: np.ndarray, p: int, q90: float) -> np.ndarray:
    """Existing Tail-Z implementation. The percentile is a caller-fit calibration q90."""
    return v2.tail_scores_all_dimensions(vectors, mu, sigma, p, q90)


def _dim_spec(dim: int) -> sim.DimSpec:
    return sim.DimSpec(
        active_dims=np.arange(dim, dtype=np.int64),
        anchor_dims=np.zeros(0, dtype=np.int64),
        anchor_weights=np.zeros(0, dtype=np.float64),
        neg_sensor_dims=np.zeros(0, dtype=np.int64),
    )


def fit_best_thresholds_matrix(scores: np.ndarray, y_true: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Column-wise copy of ``fit_best_1d_threshold``.

    Returns thresholds, train F1, and train ``FRR + FAR`` for every column.
    Ties use the same atol ``1e-12`` and the same median index.
    """
    matrix = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(y_true, dtype=bool)
    if matrix.ndim != 2 or labels.ndim != 1 or matrix.shape[0] != labels.shape[0] or matrix.shape[0] == 0:
        raise ValueError(f"threshold matrix {matrix.shape} vs labels {labels.shape}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("non-finite score in threshold fit")
    n_rows, n_cols = matrix.shape
    n_pos = int(np.sum(labels))
    n_neg = int(labels.size - n_pos)
    order = np.argsort(-matrix, axis=0, kind="mergesort")
    y_sorted = np.asarray(labels, dtype=np.int64)[order]
    s_sorted = np.take_along_axis(matrix, order, axis=0)
    is_end = np.empty((n_rows, n_cols), dtype=bool)
    is_end[-1] = True
    if n_rows > 1:
        is_end[:-1] = s_sorted[:-1] != s_sorted[1:]
    tp = np.cumsum(y_sorted, axis=0, dtype=np.int64)
    prefix = np.arange(1, n_rows + 1, dtype=np.int64)[:, None]
    fp = prefix - tp
    fn = n_pos - tp
    denom = (2 * tp) + fp + fn
    f1_prefix = np.where(denom > 0, (np.float64(2.0) * tp) / np.maximum(denom, 1), np.float64(0.0))
    pos_denom = float(max(n_pos, 1))
    neg_denom = float(max(n_neg, 1))
    err_prefix = (fn / pos_denom) + (fp / neg_denom)
    f1_all = np.full((n_rows + 1, n_cols), np.float64(-1.0), dtype=np.float64)
    err_all = np.full((n_rows + 1, n_cols), np.float64(np.inf), dtype=np.float64)
    reject_denom = n_pos
    if reject_denom > 0:
        f1_all[0] = np.float64(0.0)
    else:
        f1_all[0] = np.float64(0.0)
    err_all[0] = (n_pos / pos_denom) + np.float64(0.0)
    f1_all[1:] = np.where(is_end, f1_prefix, np.float64(-1.0))
    err_all[1:] = np.where(is_end, err_prefix, np.float64(np.inf))
    max_f1 = np.max(f1_all, axis=0)
    near_f1 = np.abs(f1_all - max_f1) <= np.float64(1e-12)
    err_masked = np.where(near_f1, err_all, np.float64(np.inf))
    min_err = np.min(err_masked, axis=0)
    best = near_f1 & (np.abs(err_masked - min_err) <= np.float64(1e-12))
    counts = np.sum(best, axis=0)
    if np.any(counts < 1):
        raise RuntimeError("threshold search lost every candidate")
    target = (counts // 2) + 1
    cumulative = np.cumsum(best, axis=0)
    chosen = np.argmax(cumulative == target, axis=0)
    thresholds = np.empty(n_cols, dtype=np.float64)
    reject = s_sorted[0] + np.float64(1e-9)
    prefix_threshold = s_sorted
    for col in range(n_cols):
        row = int(chosen[col])
        thresholds[col] = reject[col] if row == 0 else prefix_threshold[row - 1, col]
    chosen_f1 = f1_all[chosen, np.arange(n_cols)]
    chosen_err = err_all[chosen, np.arange(n_cols)]
    return thresholds, chosen_f1, chosen_err


def pick_column(f1: np.ndarray, err: np.ndarray) -> int:
    """Highest F1, then lowest FRR+FAR, then the lowest column index."""
    quality = np.asarray(f1, dtype=np.float64)
    cost = np.asarray(err, dtype=np.float64)
    if quality.shape != cost.shape or quality.ndim != 1 or quality.shape[0] == 0:
        raise ValueError("recipe key shape is invalid")
    order = np.lexsort((np.arange(quality.shape[0]), cost, -quality))
    return int(order[0])


def select_recipe_on_train(
    scores: np.ndarray,
    y_true: np.ndarray,
    train_idx: np.ndarray,
) -> tuple[int, float, float]:
    """Choose a column using training rows only. The held-out rows are not read."""
    matrix = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(y_true, dtype=bool)
    train = np.asarray(train_idx, dtype=np.int64)
    if train.size == 0:
        raise ValueError("training fold is empty")
    if np.any(train < 0) or np.any(train >= matrix.shape[0]):
        raise ValueError("training index outside the score matrix")
    thresholds, f1, err = fit_best_thresholds_matrix(matrix[train], labels[train])
    chosen = pick_column(f1, err)
    return chosen, float(thresholds[chosen]), float(f1[chosen])


def holdout_parts(chunk_scores: np.ndarray, bundle: sim.PromptBundle) -> tuple[np.ndarray, np.ndarray]:
    """Surface after ``fail_closed_min``, and the clause minimum used by the blend.

    A prompt with no clause rows uses its raw full-document score as the clause
    minimum, matching ``aggregate_prompt_signals``.
    """
    scores = np.asarray(chunk_scores, dtype=np.float64)
    if scores.ndim != 1 or scores.shape[0] != bundle.chunk_vectors.shape[0]:
        raise ValueError("chunk scores do not align with the prompt bundle")
    if not np.all(np.isfinite(scores)):
        raise ValueError("non-finite chunk score")
    full = scores[bundle.full_chunk_idx]
    n_prompts = int(full.shape[0])
    payload_min = np.full(n_prompts, np.inf, dtype=np.float64)
    for prompt, sl in enumerate(bundle.b64_chunk_slices):
        if sl.size:
            payload_min[prompt] = np.min(scores[sl])
    surface = np.array(full, dtype=np.float64, copy=True)
    has_payload = np.isfinite(payload_min)
    surface[has_payload] = np.minimum(full[has_payload], payload_min[has_payload])
    clause_min = np.empty(n_prompts, dtype=np.float64)
    for prompt, sl in enumerate(bundle.clause_chunk_slices):
        if sl.size:
            clause_min[prompt] = np.min(scores[sl])
        else:
            clause_min[prompt] = full[prompt]
    return surface, clause_min


def blend_documents(surface: np.ndarray, clause_min: np.ndarray, w_f: float) -> np.ndarray:
    """Vector form of ``blend_full_min_clause`` on aligned document arrays."""
    full = np.asarray(surface, dtype=np.float64)
    clauses = np.asarray(clause_min, dtype=np.float64)
    if full.shape != clauses.shape:
        raise ValueError("blend arrays differ in shape")
    weight = np.float64(w_f)
    return weight * full + (np.float64(1.0) - weight) * clauses


def calibration_clause_min(
    full_scores: np.ndarray,
    clause_scores: np.ndarray,
    clause_bundle_ids: np.ndarray,
    n_bundles: int,
) -> np.ndarray:
    """Per-bundle minimum clause score. Bundles with no clause keep the full score."""
    full = np.asarray(full_scores, dtype=np.float64)
    if full.shape != (n_bundles,):
        raise ValueError(f"full scores {full.shape} != ({n_bundles},)")
    clause_min = np.full(n_bundles, np.inf, dtype=np.float64)
    clauses = np.asarray(clause_scores, dtype=np.float64)
    bundles = np.asarray(clause_bundle_ids, dtype=np.int64)
    if clauses.shape != bundles.shape:
        raise ValueError("clause scores do not align with bundle ids")
    if clauses.size:
        np.minimum.at(clause_min, bundles, clauses)
    empty = ~np.isfinite(clause_min)
    clause_min[empty] = full[empty]
    return clause_min


@dataclass(frozen=True)
class RecipeSpec:
    """One swept document score. Alpha 0 does not name a guard."""

    family: str
    coupling: str
    alpha: float
    guard: str | None
    struct_hook: str
    beta: float
    gamma: float | None
    struct_reduction: str
    w_f: float | None

    def name(self) -> str:
        guard = "-" if self.guard is None else self.guard
        gamma = "-" if self.gamma is None else f"{self.gamma:.2f}"
        weight = "-" if self.w_f is None else f"{self.w_f:.2f}"
        return (
            f"{self.family}|{self.coupling}|a={self.alpha:.2f}|g={guard}|"
            f"{self.struct_hook}|b={self.beta:.2f}|y={gamma}|r={self.struct_reduction}|w={weight}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name(),
            "family": self.family,
            "coupling": self.coupling,
            "alpha": float(self.alpha),
            "guard": self.guard,
            "struct_hook": self.struct_hook,
            "beta": float(self.beta),
            "gamma": None if self.gamma is None else float(self.gamma),
            "struct_reduction": self.struct_reduction,
            "w_f": None if self.w_f is None else float(self.w_f),
        }


def reductions_for(granularity: str) -> tuple[str, ...]:
    if granularity == "full_only":
        return ("full_doc",)
    if granularity == "clauses":
        return ("full_doc", "min_full_clause")
    raise ValueError(f"unsupported granularity {granularity}")


def weights_for(granularity: str) -> tuple[float | None, ...]:
    if granularity == "full_only":
        return (None,)
    if granularity == "clauses":
        return W_F
    raise ValueError(f"unsupported granularity {granularity}")


def iter_recipe_specs(granularity: str) -> tuple[RecipeSpec, ...]:
    """Cartesian sweep. Alpha 0 is a single identity column, not one per guard."""
    specs: list[RecipeSpec] = []
    for family in DIR_VARIANTS:
        for weight in weights_for(granularity):
            for reduction in reductions_for(granularity):
                for alpha in ALPHAS:
                    if alpha == 0.0:
                        couplings = (("identity", None),)
                    else:
                        couplings = tuple(("additive", guard) for guard in GUARDS) + tuple(
                            ("multiplicative", guard) for guard in GUARDS
                        )
                    for coupling, guard in couplings:
                        for beta in BETAS:
                            specs.append(
                                RecipeSpec(
                                    family=family,
                                    coupling=coupling,
                                    alpha=float(alpha),
                                    guard=guard,
                                    struct_hook="beta",
                                    beta=float(beta),
                                    gamma=None,
                                    struct_reduction=reduction,
                                    w_f=None if weight is None else float(weight),
                                )
                            )
                        for gamma in GAMMAS:
                            specs.append(
                                RecipeSpec(
                                    family=family,
                                    coupling=coupling,
                                    alpha=float(alpha),
                                    guard=guard,
                                    struct_hook="gamma",
                                    beta=0.0,
                                    gamma=float(gamma),
                                    struct_reduction=reduction,
                                    w_f=None if weight is None else float(weight),
                                )
                            )
    for family in BASELINES:
        for weight in weights_for(granularity):
            for reduction in reductions_for(granularity):
                for beta in BETAS:
                    specs.append(
                        RecipeSpec(
                            family=family,
                            coupling="identity",
                            alpha=0.0,
                            guard=None,
                            struct_hook="beta",
                            beta=float(beta),
                            gamma=None,
                            struct_reduction=reduction,
                            w_f=None if weight is None else float(weight),
                        )
                    )
                for gamma in GAMMAS:
                    specs.append(
                        RecipeSpec(
                            family=family,
                            coupling="identity",
                            alpha=0.0,
                            guard=None,
                            struct_hook="gamma",
                            beta=0.0,
                            gamma=float(gamma),
                            struct_reduction=reduction,
                            w_f=None if weight is None else float(weight),
                        )
                    )
    return tuple(specs)


def _apply_spec(
    spec: RecipeSpec,
    channels: Mapping[str, np.ndarray],
    struct: Mapping[str, np.ndarray],
) -> np.ndarray:
    base = channels[spec.family]
    if spec.coupling == "identity":
        semantic = base
    elif spec.coupling == "additive":
        if spec.guard is None:
            raise ValueError("additive coupling requires a guard")
        semantic = couple_additive(base, channels[spec.guard], spec.alpha)
    elif spec.coupling == "multiplicative":
        if spec.guard is None:
            raise ValueError("multiplicative coupling requires a guard")
        semantic = couple_multiplicative(base, channels[spec.guard], spec.alpha)
    else:
        raise ValueError(f"unsupported coupling {spec.coupling}")
    struct_score = struct[spec.struct_reduction]
    if spec.struct_hook == "beta":
        return apply_beta_struct(semantic, struct_score, spec.beta)
    if spec.struct_hook == "gamma":
        if spec.gamma is None:
            raise ValueError("gamma hook requires gamma")
        return apply_gamma_struct(semantic, struct_score, spec.gamma)
    raise ValueError(f"unsupported struct hook {spec.struct_hook}")


def materialize_recipes(
    hold_channels: Mapping[float | None, Mapping[str, np.ndarray]],
    cal_channels: Mapping[float | None, Mapping[str, np.ndarray]],
    hold_struct: Mapping[str, np.ndarray],
    cal_struct: Mapping[str, np.ndarray],
    granularity: str,
) -> tuple[tuple[RecipeSpec, ...], np.ndarray, np.ndarray]:
    """Build the document-level sweep. Rows are prompts or calibration bundles."""
    specs = iter_recipe_specs(granularity)
    n_hold = int(next(iter(hold_struct.values())).shape[0])
    n_cal = int(next(iter(cal_struct.values())).shape[0])
    hold = np.empty((n_hold, len(specs)), dtype=np.float64)
    cal = np.empty((n_cal, len(specs)), dtype=np.float64)
    for col, spec in enumerate(specs):
        hold[:, col] = _apply_spec(spec, hold_channels[spec.w_f], hold_struct)
        cal[:, col] = _apply_spec(spec, cal_channels[spec.w_f], cal_struct)
    if not np.all(np.isfinite(hold)) or not np.all(np.isfinite(cal)):
        raise RuntimeError("non-finite recipe matrix")
    return specs, hold, cal


def confusion_columns(y_true: np.ndarray, pred: np.ndarray) -> dict[str, np.ndarray]:
    """Vectorized confusion counts. ``pred`` is ``(n, R)``."""
    labels = np.asarray(y_true, dtype=bool)
    decisions = np.asarray(pred, dtype=bool)
    if decisions.ndim != 2 or decisions.shape[0] != labels.shape[0]:
        raise ValueError("prediction matrix does not align with labels")
    yt = labels[:, None]
    tp = np.sum(yt & decisions, axis=0, dtype=np.int64)
    fn = np.sum(yt & ~decisions, axis=0, dtype=np.int64)
    tn = np.sum(~yt & ~decisions, axis=0, dtype=np.int64)
    fp = np.sum(~yt & decisions, axis=0, dtype=np.int64)
    n_pos = tp + fn
    n_neg = tn + fp
    predicted_pos = tp + fp
    precision = np.divide(
        tp.astype(np.float64),
        predicted_pos.astype(np.float64),
        out=np.zeros(tp.shape, dtype=np.float64),
        where=predicted_pos > 0,
    )
    recall = np.where(n_pos > 0, fn * 0 + tp / np.maximum(n_pos, 1), np.nan)
    f1_denom = (2 * tp) + fp + fn
    f1 = np.where(f1_denom > 0, (np.float64(2.0) * tp) / f1_denom, np.float64(0.0))
    frr = np.where(n_pos > 0, fn / np.maximum(n_pos, 1), np.nan)
    far = np.where(n_neg > 0, fp / np.maximum(n_neg, 1), np.nan)
    return {
        "tp": tp,
        "fn": fn,
        "tn": tn,
        "fp": fp,
        "precision": precision.astype(np.float64),
        "recall": recall.astype(np.float64),
        "f1": f1.astype(np.float64),
        "frr": frr.astype(np.float64),
        "far": far.astype(np.float64),
    }


def roc_columns(y_true: np.ndarray, scores: np.ndarray) -> np.ndarray:
    """ROC-AUC of each column via the existing trapezoidal implementation."""
    labels = np.asarray(y_true, dtype=np.int64)
    matrix = np.asarray(scores, dtype=np.float64)
    out = np.empty(matrix.shape[1], dtype=np.float64)
    for col in range(matrix.shape[1]):
        out[col] = sim.compute_roc_auc_trapezoidal(labels, matrix[:, col])
    return out


def evaluate_cal_only_matrix(
    cal_scores: np.ndarray,
    hold_scores: np.ndarray,
    y_true: np.ndarray,
    *,
    with_roc: bool,
) -> dict[str, dict[str, np.ndarray]]:
    """Percentiles of the calibration columns only. Holdout labels are not an input."""
    cal = np.asarray(cal_scores, dtype=np.float64)
    hold = np.asarray(hold_scores, dtype=np.float64)
    labels = np.asarray(y_true, dtype=bool)
    if cal.ndim != 2 or hold.ndim != 2 or cal.shape[1] != hold.shape[1]:
        raise ValueError("CAL_ONLY matrices differ in width")
    if hold.shape[0] != labels.shape[0]:
        raise ValueError("holdout scores do not align with labels")
    roc = roc_columns(labels, hold) if with_roc else None
    out: dict[str, dict[str, np.ndarray]] = {}
    for prob, tag in PROB_TAGS:
        threshold = np.quantile(cal, np.float64(prob), axis=0, method="linear")
        pred = hold >= threshold[None, :]
        block = confusion_columns(labels, pred)
        block["threshold"] = np.asarray(threshold, dtype=np.float64)
        if roc is not None:
            block["roc_auc"] = roc
        out[tag] = block
    return out


def evaluate_cal_only(cal_scores: np.ndarray, hold_scores: np.ndarray, y_true: np.ndarray) -> dict[str, Any]:
    """One score vector. The threshold percentile reads ``cal_scores`` only."""
    cal = np.asarray(cal_scores, dtype=np.float64).reshape(-1, 1)
    hold = np.asarray(hold_scores, dtype=np.float64).reshape(-1, 1)
    matrix = evaluate_cal_only_matrix(cal, hold, y_true, with_roc=True)
    out: dict[str, Any] = {}
    for tag, block in matrix.items():
        metrics = {
            "tp": int(block["tp"][0]),
            "fn": int(block["fn"][0]),
            "tn": int(block["tn"][0]),
            "fp": int(block["fp"][0]),
            "precision": float(block["precision"][0]),
            "recall": None if not np.isfinite(block["recall"][0]) else float(block["recall"][0]),
            "f1": float(block["f1"][0]),
            "frr": None if not np.isfinite(block["frr"][0]) else float(block["frr"][0]),
            "far": None if not np.isfinite(block["far"][0]) else float(block["far"][0]),
            "threshold": float(block["threshold"][0]),
            "roc_auc": float(block["roc_auc"][0]),
        }
        out[tag] = metrics
    return out


def _ci(values: np.ndarray) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    return {
        "low": float(np.quantile(arr, np.float64(0.025), method="linear")),
        "high": float(np.quantile(arr, np.float64(0.975), method="linear")),
    }


def bootstrap_resample_indices(
    n_cal: int,
    categories: Sequence[str],
    subtypes: Sequence[str],
    *,
    seed: int,
    n_resamples: int,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Calibration draw, then stratified holdout draws. Seed 0 is bit-stable."""
    if n_resamples < 2:
        raise ValueError("bootstrap needs at least two resamples")
    if n_cal < 2:
        raise ValueError("bootstrap calibration resample needs at least two scores")
    if len(categories) != len(subtypes):
        raise ValueError("bootstrap strata differ in length")
    rng = np.random.Generator(np.random.PCG64(np.uint64(seed)))
    groups: dict[tuple[str, str], list[int]] = {}
    for i, (cat, sub) in enumerate(zip(categories, subtypes)):
        groups.setdefault((cat, sub), []).append(i)
    index_groups = [np.array(groups[key], dtype=np.int64) for key in sorted(groups)]
    cal_draws: list[np.ndarray] = []
    hold_draws: list[np.ndarray] = []
    for _ in range(n_resamples):
        cal_draws.append(rng.choice(n_cal, size=n_cal, replace=True))
        parts = [rng.choice(group, size=group.size, replace=True) for group in index_groups]
        hold_draws.append(np.concatenate(parts))
    return cal_draws, hold_draws


def bootstrap_cal_only_paired(
    methods: Mapping[str, tuple[np.ndarray, np.ndarray]],
    y_true: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    *,
    seed: int,
    n_resamples: int = v2.BOOTSTRAP_RESAMPLES,
    probability: float = BOOTSTRAP_PROBABILITY,
    frozen_f1: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Paired CAL_ONLY bootstrap. Each draw refits the calibration percentile.

    ``methods`` maps a name to ``(holdout_scores, calibration_scores)``. The same
    resample indices are applied to every method. ``refits_thresholds`` is true.
    """
    if not methods:
        raise ValueError("bootstrap needs at least one method")
    labels = np.asarray(y_true, dtype=bool)
    if labels.shape[0] != len(categories) or labels.shape[0] != len(subtypes):
        raise ValueError("bootstrap labels do not align with strata")
    names = tuple(methods)
    hold = []
    cal = []
    for name in names:
        hold_scores, cal_scores = methods[name]
        hold_arr = np.asarray(hold_scores, dtype=np.float64)
        cal_arr = np.asarray(cal_scores, dtype=np.float64)
        if hold_arr.shape != labels.shape or cal_arr.ndim != 1 or cal_arr.shape[0] < 2:
            raise ValueError(f"{name} bootstrap scores are misaligned")
        if not np.all(np.isfinite(hold_arr)) or not np.all(np.isfinite(cal_arr)):
            raise ValueError(f"non-finite bootstrap score in {name}")
        hold.append(hold_arr)
        cal.append(cal_arr)
    if any(arr.shape[0] != cal[0].shape[0] for arr in cal):
        raise ValueError("calibration score lengths differ across methods")
    cal_draws, hold_draws = bootstrap_resample_indices(
        cal[0].shape[0],
        categories,
        subtypes,
        seed=seed,
        n_resamples=n_resamples,
    )
    n_methods = len(names)
    f1 = np.empty((n_resamples, n_methods), dtype=np.float64)
    frr = np.empty((n_resamples, n_methods), dtype=np.float64)
    far = np.empty((n_resamples, n_methods), dtype=np.float64)
    roc = np.empty((n_resamples, n_methods), dtype=np.float64)
    for draw, (cal_idx, hold_idx) in enumerate(zip(cal_draws, hold_draws)):
        y_draw = labels[hold_idx]
        for method_i in range(n_methods):
            threshold = float(np.quantile(cal[method_i][cal_idx], np.float64(probability), method="linear"))
            pred = hold[method_i][hold_idx] >= np.float64(threshold)
            metrics = sim.compute_confusion_metrics(y_draw, pred)
            if metrics["frr"] is None or metrics["far"] is None:
                raise RuntimeError("stratified bootstrap lost a class")
            f1[draw, method_i] = np.float64(metrics["f1"])
            frr[draw, method_i] = np.float64(metrics["frr"])
            far[draw, method_i] = np.float64(metrics["far"])
            roc[draw, method_i] = sim.compute_roc_auc_trapezoidal(y_draw.astype(np.int64), hold[method_i][hold_idx])
    out_methods: dict[str, Any] = {}
    frozen = frozen_f1 or {}
    for method_i, name in enumerate(names):
        block: dict[str, Any] = {
            "f1": _ci(f1[:, method_i]),
            "frr": _ci(frr[:, method_i]),
            "far": _ci(far[:, method_i]),
            "roc_auc": _ci(roc[:, method_i]),
        }
        if frozen:
            deltas: dict[str, Any] = {}
            for frozen_name, frozen_value in frozen.items():
                delta = f1[:, method_i] - np.float64(frozen_value)
                deltas[frozen_name] = {
                    "point_bootstrap_mean_minus_frozen": float(np.mean(delta)),
                    "ci95": _ci(delta),
                }
            block["delta_f1"] = deltas
        out_methods[name] = block
    return {
        "n_resamples": int(n_resamples),
        "seed": int(seed),
        "refits_thresholds": True,
        "threshold_policy": "resampled_calibration_percentile",
        "probability": float(probability),
        "methods": out_methods,
    }


def nested_repeated_oof(
    scores: np.ndarray,
    y_true: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    input_ids: Sequence[str],
    *,
    seeds: Sequence[int] = v2.REPEATED_SEEDS,
    n_folds: int = 5,
) -> dict[str, Any]:
    """5x5 OOF. Each fold selects the recipe and the threshold on the training rows only."""
    matrix = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(y_true, dtype=bool)
    if matrix.ndim != 2 or matrix.shape[0] != labels.shape[0]:
        raise ValueError("nested scores do not align with labels")
    n_rows, n_recipes = matrix.shape
    wins = np.zeros(n_recipes, dtype=np.int64)
    f1_sum = np.zeros(n_recipes, dtype=np.float64)
    per_seed: list[dict[str, Any]] = []
    predictions: list[np.ndarray] = []
    f1s: list[float] = []
    frrs: list[float] = []
    fars: list[float] = []
    rocs: list[float] = []
    fold_choices: list[list[int]] = []
    for seed in seeds:
        folds = v2.assign_repeated_stratified_folds(
            categories, subtypes, input_ids, n_folds=n_folds, seed=int(seed)
        )
        pred = np.zeros(n_rows, dtype=bool)
        used = np.empty(n_rows, dtype=np.float64)
        choices: list[int | None] = [None] * n_folds
        for fold in range(n_folds):
            test = np.flatnonzero(folds == fold)
            train = np.flatnonzero(folds != fold)
            if test.size == 0:
                continue
            chosen, threshold, train_f1 = select_recipe_on_train(matrix, labels, train)
            pred[test] = matrix[test, chosen] >= np.float64(threshold)
            used[test] = matrix[test, chosen]
            choices[fold] = int(chosen)
            wins[chosen] += 1
            f1_sum[chosen] += np.float64(train_f1)
        metrics = sim.compute_confusion_metrics(labels, pred)
        if metrics["frr"] is None or metrics["far"] is None:
            raise RuntimeError("nested OOF lost a class")
        auc = sim.compute_auc_triple(labels, used)
        f1s.append(float(metrics["f1"]))
        frrs.append(float(metrics["frr"]))
        fars.append(float(metrics["far"]))
        rocs.append(float(auc["roc_auc"]))
        predictions.append(pred)
        fold_choices.append(choices)
        per_seed.append(
            {
                "seed": int(seed),
                "f1": float(metrics["f1"]),
                "frr": float(metrics["frr"]),
                "far": float(metrics["far"]),
                "roc_auc": float(auc["roc_auc"]),
                "pr_auc_in_domain": float(auc["pr_auc_in_domain"]),
                "pr_auc_reject": float(auc["pr_auc_reject"]),
                "selected_columns": [choice for choice in choices if choice is not None],
            }
        )
    seed0_scores = np.empty(n_rows, dtype=np.float64)
    folds0 = v2.assign_repeated_stratified_folds(categories, subtypes, input_ids, n_folds=n_folds, seed=int(seeds[0]))
    for fold, chosen in enumerate(fold_choices[0]):
        if chosen is None:
            continue
        test = np.flatnonzero(folds0 == fold)
        if test.size:
            seed0_scores[test] = matrix[test, chosen]
    oracle_threshold, oracle_metrics = sim.fit_best_1d_threshold(seed0_scores, labels)

    def _pack(values: Sequence[float]) -> dict[str, float]:
        arr = np.array(list(values), dtype=np.float64)
        return {"mean": float(np.mean(arr)), "std": float(np.std(arr, ddof=1))}

    mean_train = np.divide(f1_sum, np.maximum(wins, 1))
    eligible = np.where(wins > 0, wins.astype(np.float64), np.float64(-1.0))
    modal = int(np.lexsort((np.arange(n_recipes), -mean_train, -eligible))[0])
    return {
        "seeds": [int(seed) for seed in seeds],
        "f1": _pack(f1s),
        "frr": _pack(frrs),
        "far": _pack(fars),
        "roc_auc": _pack(rocs),
        "per_seed": per_seed,
        "predictions": predictions,
        "modal_column": modal,
        "modal_wins": int(wins[modal]),
        "oracle_upper_bound": {
            "tag": "[ORACLE_UPPER_BOUND]",
            "f1": float(oracle_metrics["f1"]),
            "frr": oracle_metrics["frr"],
            "far": oracle_metrics["far"],
            "threshold": float(oracle_threshold),
            "source": "seed0_mixed_scores_fit_on_all_holdout_labels",
        },
    }


def repeated_stratified_oof(
    scores: np.ndarray,
    y_true: np.ndarray,
    categories: Sequence[str],
    subtypes: Sequence[str],
    input_ids: Sequence[str],
) -> dict[str, Any]:
    """Fixed-recipe 5x5. Thresholds are refit per training fold; the recipe is not."""
    return v2.repeated_stratified_oof(scores, y_true, categories, subtypes, input_ids)


def detach_oracle(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Move an oracle object out of a metrics row. The tag is required when present."""
    if "oracle_upper_bound" not in row:
        return row, None
    oracle = row.pop("oracle_upper_bound")
    if not isinstance(oracle, dict) or oracle.get("tag") != "[ORACLE_UPPER_BOUND]":
        raise RuntimeError("oracle row is missing its tag")
    return row, oracle


def candidate_hashes(text: str) -> tuple[str, ...]:
    """SHA-256 hex of the stripped text and of that text after input normalization."""
    if not isinstance(text, str):
        raise TypeError("augmented text must be str")
    stripped = text.strip()
    normalized = xray.normalize_input_text(stripped)
    found: list[str] = []
    for piece in (stripped, normalized, normalized.strip()):
        digest = hashlib.sha256(piece.encode("utf-8")).hexdigest()
        if digest not in found:
            found.append(digest)
    return tuple(found)


def load_augmented_hash_index(path: Path) -> dict[str, str]:
    """Map candidate digests to the raw JSONL text. The file must contain 600 rows."""
    index: dict[str, str] = {}
    n_rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        text = json.loads(line)["text"]
        n_rows += 1
        for digest in candidate_hashes(text):
            previous = index.get(digest)
            if previous is not None and previous != text:
                raise RuntimeError(f"{path.name} hash {digest} maps to two texts")
            index[digest] = text
    if n_rows != 600:
        raise RuntimeError(f"{path.name} has {n_rows} texts, expected 600")
    return index


def join_full_doc_texts(digests: Sequence[str], index: Mapping[str, str]) -> list[str]:
    """Join calibration ``text_sha256`` values. A miss stops the run."""
    texts: list[str] = []
    miss = 0
    for digest in digests:
        text = index.get(digest)
        if text is None:
            miss += 1
            continue
        texts.append(text)
    if miss:
        raise RuntimeError(f"full_doc hash join coverage miss_count={miss} of {len(digests)}")
    if len(texts) != len(digests):
        raise RuntimeError("hash join dropped a matched document")
    return texts


def augmented_jsonl(directory: Path, domain: str) -> Path:
    matches = sorted(Path(directory).glob(f"{domain}_*.jsonl"))
    if len(matches) != 1:
        raise RuntimeError(f"{domain} augmented jsonl count {len(matches)} != 1 in {directory}")
    return matches[0]


def parse_task013_headlines(markdown: str) -> dict[str, dict[str, str]]:
    """Read the published CAL_ONLY p10 F1 and repeated-F1 mean strings."""
    cal: dict[str, str] = {}
    repeated: dict[str, str] = {}
    for line in markdown.splitlines():
        cal_match = _CAL_P10_RE.match(line)
        if cal_match is not None and cal_match.group("cell") not in cal:
            cal[cal_match.group("cell")] = cal_match.group("f1")
        repeated_match = _REPEATED_F1_RE.match(line)
        if repeated_match is not None and repeated_match.group("cell") not in repeated:
            repeated[repeated_match.group("cell")] = repeated_match.group("mean")
    return {"cal_p10_f1": cal, "repeated_f1": repeated}


def verify_task013_headlines(parsed: Mapping[str, Mapping[str, str]]) -> None:
    """Stop if the report parse does not reproduce the published headline strings."""
    expected_cells = {f"{domain}/{gran}" for domain, gran in TASK013_CAL_P10_F1}
    if set(parsed["cal_p10_f1"]) != expected_cells or set(parsed["repeated_f1"]) != expected_cells:
        raise RuntimeError(
            f"TASK-013 headline cells cal={sorted(parsed['cal_p10_f1'])} repeated={sorted(parsed['repeated_f1'])}"
        )
    for (domain, gran), expected in TASK013_CAL_P10_F1.items():
        cell = f"{domain}/{gran}"
        if parsed["cal_p10_f1"][cell] != expected:
            raise RuntimeError(f"{cell} CAL p10 F1 parsed {parsed['cal_p10_f1'][cell]} != {expected}")
        if parsed["repeated_f1"][cell] != TASK013_REPEATED_F1[(domain, gran)]:
            raise RuntimeError(f"{cell} repeated F1 parsed {parsed['repeated_f1'][cell]} != published")


def frozen_f1_for_cell(domain: str, granularity: str, task012: Mapping[str, float], task013: Mapping[str, Mapping[str, str]]) -> dict[str, float]:
    cell = f"{domain}/{granularity}"
    return {
        "task012_f1": float(task012[f"{domain}/{granularity}"]["task012_f1"]),
        "task013_cal_p10_f1": float(np.float64(task013["cal_p10_f1"][cell])),
        "task013_repeated_f1": float(np.float64(task013["repeated_f1"][cell])),
    }


def _percentile_us(samples: Sequence[float], percent: float) -> float:
    arr = np.asarray(list(samples), dtype=np.float64)
    if arr.size == 0 or not np.all(np.isfinite(arr)) or np.any(arr < 0.0):
        raise RuntimeError("S_struct latency sample is empty or non-finite")
    return float(np.quantile(arr, np.float64(percent) / np.float64(100.0), method="linear"))


def score_struct_corpus(
    texts: Sequence[str],
    clauses: Sequence[Sequence[str]],
    full_profile: lex.LexicalProfile,
    clause_profile: lex.LexicalProfile,
    *,
    time_calls: bool,
) -> dict[str, Any]:
    """Score raw documents. Clause reduction matches ``score_clauses``."""
    if len(texts) != len(clauses):
        raise ValueError("structural texts and clause lists differ in length")
    n_docs = len(texts)
    s_full = np.empty(n_docs, dtype=np.float64)
    s_min = np.empty(n_docs, dtype=np.float64)
    full_features: list[tuple[str, ...]] = []
    min_features: list[tuple[str, ...]] = []
    full_us: list[float] = []
    clause_us: list[float] = []
    for i, text in enumerate(texts):
        started = time.perf_counter_ns()
        full = lex.score(text, full_profile)
        if time_calls:
            full_us.append(float(time.perf_counter_ns() - started) / 1000.0)
        clause_values: list[float] = []
        clause_names: set[str] = set()
        for clause in clauses[i]:
            started = time.perf_counter_ns()
            scored = lex.score(clause, clause_profile)
            if time_calls:
                clause_us.append(float(time.perf_counter_ns() - started) / 1000.0)
            clause_values.append(float(scored.s_struct))
            clause_names.update(feature.name for feature in scored.top_triggered_features)
        full_value, reduced = struct_reductions(full.s_struct, clause_values)
        s_full[i] = full_value
        s_min[i] = reduced
        full_names = tuple(feature.name for feature in full.top_triggered_features)
        full_features.append(full_names)
        min_features.append(tuple(sorted(set(full_names) | clause_names)))
    if not np.all(np.isfinite(s_full)) or not np.all(np.isfinite(s_min)):
        raise RuntimeError("non-finite S_struct")
    return {
        "s_full": s_full,
        "s_min": s_min,
        "full_features": full_features,
        "min_features": min_features,
        "full_us": full_us,
        "clause_us": clause_us,
    }


def _feature_counts(names: Sequence[Sequence[str]], mask: np.ndarray) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in np.flatnonzero(mask):
        for name in names[int(row)]:
            counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def _latency_block(full_us: Sequence[float], clause_us: Sequence[float]) -> dict[str, Any]:
    combined = list(full_us) + list(clause_us)
    return {
        "definition": "microseconds per score() call on holdout strings",
        "p50_us": _percentile_us(combined, 50.0),
        "p99_us": _percentile_us(combined, 99.0),
        "full_doc": {
            "n": len(full_us),
            "p50_us": _percentile_us(full_us, 50.0),
            "p99_us": _percentile_us(full_us, 99.0),
        },
        "clause_opt2c": {
            "n": len(clause_us),
            "p50_us": _percentile_us(clause_us, 50.0) if clause_us else None,
            "p99_us": _percentile_us(clause_us, 99.0) if clause_us else None,
        },
    }


def _column_metrics(block: Mapping[str, np.ndarray], col: int) -> dict[str, Any]:
    recall = block["recall"][col]
    frr = block["frr"][col]
    far = block["far"][col]
    row = {
        "tp": int(block["tp"][col]),
        "fn": int(block["fn"][col]),
        "tn": int(block["tn"][col]),
        "fp": int(block["fp"][col]),
        "precision": float(block["precision"][col]),
        "recall": None if not np.isfinite(recall) else float(recall),
        "f1": float(block["f1"][col]),
        "frr": None if not np.isfinite(frr) else float(frr),
        "far": None if not np.isfinite(far) else float(far),
        "threshold": float(block["threshold"][col]),
    }
    if "roc_auc" in block:
        row["roc_auc"] = float(block["roc_auc"][col])
    return row


def _pack_repeated(block: Mapping[str, Any]) -> dict[str, Any]:
    """5x5 summary without prediction arrays and without the oracle object."""
    per_seed = []
    for row in block["per_seed"]:
        per_seed.append({key: value for key, value in row.items() if key != "fold_thresholds"})
    packed = {
        "seeds": list(block["seeds"]),
        "f1": block["f1"],
        "frr": block["frr"],
        "far": block["far"],
        "roc_auc": block["roc_auc"],
        "per_seed": per_seed,
    }
    if "pr_auc_in_domain" in block:
        packed["pr_auc_in_domain"] = block["pr_auc_in_domain"]
        packed["pr_auc_reject"] = block["pr_auc_reject"]
    return packed


def _find_spec(specs: Sequence[RecipeSpec], **expected: Any) -> int:
    for index, spec in enumerate(specs):
        if all(getattr(spec, key) == value for key, value in expected.items()):
            return index
    raise KeyError(expected)


def _subgroup_block(y_true: np.ndarray, pred: np.ndarray, categories: Sequence[str], subtypes: Sequence[str]) -> dict[str, Any]:
    labels = np.asarray(y_true, dtype=bool)
    cats = np.asarray(list(categories), dtype=object)
    subs = np.asarray(list(subtypes), dtype=object)
    quadrants = {name: v2.subgroup_error(labels, pred, cats == name) for name in QUADRANT_NAMES}
    subtype_rows = []
    for subtype in sorted(set(subs.tolist())):
        mask = subs == subtype
        row = v2.subgroup_error(labels, pred, mask)
        present = cats[mask]
        category = str(present[0]) if present.size else None
        subtype_rows.append({"subtype": str(subtype), "category": category, **row})
    return {"quadrants": quadrants, "subtypes": subtype_rows}


def _canary_block(texts: Sequence[str], categories: Sequence[str], y_true: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    marker = np.array([bool(CANARY_RE.search(text)) for text in texts], dtype=bool)
    cats = np.asarray(list(categories), dtype=object)
    in_domain = cats == "IN_DOMAIN_VALID"
    token_counts = {"sqlite3": 0, "subprocess": 0, "json": 0}
    for text, flagged in zip(texts, marker.tolist()):
        if not flagged:
            continue
        for token in CANARY_RE.findall(text):
            token_counts[token.lower()] += 1
    return {
        "pattern": r"\b(?:sqlite3|subprocess|json)\b",
        "n_marker": int(np.sum(marker)),
        "n_marker_in_domain_valid": int(np.sum(marker & in_domain)),
        "token_hit_counts": token_counts,
        "in_domain_valid_marker": v2.subgroup_error(y_true, pred, marker & in_domain),
        "all_marker": v2.subgroup_error(y_true, pred, marker),
    }


def _struct_firing(
    categories: Sequence[str],
    subtypes: Sequence[str],
    hold_struct: Mapping[str, Any],
) -> dict[str, Any]:
    subs = np.asarray(list(subtypes), dtype=object)
    cats = np.asarray(list(categories), dtype=object)
    rows = []
    for subtype in sorted(set(subs.tolist())):
        mask = subs == subtype
        present = cats[mask]
        row: dict[str, Any] = {
            "subtype": str(subtype),
            "category": str(present[0]) if present.size else None,
            "n": int(np.sum(mask)),
        }
        for key, values, features in (
            ("full_doc", hold_struct["s_full"], hold_struct["full_features"]),
            ("min_full_clause", hold_struct["s_min"], hold_struct["min_features"]),
        ):
            taken = values[mask]
            row[key] = {
                "mean": float(np.mean(taken)),
                "n_below_1": int(np.sum(taken < np.float64(1.0))),
                "feature_counts": _feature_counts(features, mask),
            }
        rows.append(row)
    return {"rows": rows}


def _reject_tracked_output(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    repo = Path(__file__).resolve().parents[1]
    for banned in (repo / "reports", repo / "data"):
        banned_resolved = banned.resolve()
        if resolved == banned_resolved or banned_resolved in resolved.parents:
            raise RuntimeError(f"refusing to write v3 JSON under {banned_resolved}")


def _matched_chunks(full_scores: np.ndarray, clause_scores: np.ndarray | None, strategies: Sequence[str]) -> np.ndarray:
    strat = np.asarray(list(strategies), dtype=object)
    out = np.empty(strat.shape[0], dtype=np.float64)
    is_full = strat == "full_doc"
    is_clause = strat == "clause_opt2c"
    if int(np.sum(is_full)) + int(np.sum(is_clause)) != strat.shape[0]:
        raise RuntimeError("unexpected chunk strategy in a normalize=true trace")
    out[is_full] = np.asarray(full_scores, dtype=np.float64)[is_full]
    if np.any(is_clause):
        if clause_scores is None:
            raise RuntimeError("clause chunks require the clause-granularity model")
        out[is_clause] = np.asarray(clause_scores, dtype=np.float64)[is_clause]
    return out


def _scale_floor(raw: np.ndarray, bundle_ids: np.ndarray, n_bundles: int) -> float:
    present = v2.bundle_mean_present(raw, bundle_ids, n_bundles)
    return max(v2.calibration_bundle_q90(present), float(sim.SCALE_FLOOR))


@dataclass
class GeometryLevel:
    """OOF calibration geometry. Holdout chunks are scored later with ``full_box``."""

    cal_f1: np.ndarray
    cal_f2: np.ndarray
    cal_tail: dict[int, np.ndarray]
    fold_stats: list[tuple[np.ndarray, np.ndarray, np.ndarray]]
    full_box: sim.BoxStats
    full_mean: np.ndarray
    full_std: np.ndarray
    scale_f1: float
    scale_f2: float
    scale_tail: dict[int, float]


def fit_geometry_level(
    cal_vectors: np.ndarray,
    folds: np.ndarray,
    bundle_ids: np.ndarray,
    n_bundles: int,
) -> GeometryLevel:
    """F1, F2_L2, and Tail-Z scales from calibration OOF. No holdout rows enter the fit."""
    spec = _dim_spec(int(cal_vectors.shape[1]))
    n_rows = int(cal_vectors.shape[0])
    raw_e = np.empty(n_rows, dtype=np.float64)
    raw_z2 = np.empty(n_rows, dtype=np.float64)
    raw_tail = {p: np.empty(n_rows, dtype=np.float64) for p in TAIL_P}
    fold_stats: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    seen = np.zeros(n_rows, dtype=bool)
    for fold in range(5):
        train = folds != fold
        val = np.flatnonzero(folds == fold)
        if val.size == 0:
            continue
        if int(np.sum(train)) < 2:
            raise RuntimeError("calibration fold has fewer than 2 rows")
        box = sim.box_stats_from_matrix(cal_vectors[train])
        raw = sim.compute_raw_distances(cal_vectors[val], box, spec)
        raw_e[val] = raw["mean_e"]
        raw_z2[val] = raw["z2"]
        z = v2.tail_z_rows(cal_vectors[val], box.mean, box.std_sample)
        for p in TAIL_P:
            raw_tail[p][val] = v2.worst_p_mean(z, p)
        fold_stats.append((val, np.array(box.mean, copy=True), np.array(box.std_sample, copy=True)))
        seen[val] = True
    if not np.all(seen):
        raise RuntimeError("OOF geometry left a calibration row unscored")
    s_f1 = _scale_floor(raw_e, bundle_ids, n_bundles)
    s_f2 = _scale_floor(raw_z2, bundle_ids, n_bundles)
    s_tail = {p: _scale_floor(raw_tail[p], bundle_ids, n_bundles) for p in TAIL_P}
    full_box = sim.box_stats_from_matrix(cal_vectors)
    return GeometryLevel(
        cal_f1=map_f1(raw_e, s_f1),
        cal_f2=map_f2_l2(raw_z2, s_f2),
        cal_tail={p: v2.map_tail_score(raw_tail[p], s_tail[p]) for p in TAIL_P},
        fold_stats=fold_stats,
        full_box=full_box,
        full_mean=np.array(full_box.mean, copy=True),
        full_std=np.array(full_box.std_sample, copy=True),
        scale_f1=float(s_f1),
        scale_f2=float(s_f2),
        scale_tail={p: float(s_tail[p]) for p in TAIL_P},
    )


def score_geometry_holdout(level: GeometryLevel, hold_vectors: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[int, np.ndarray]]:
    """Score holdout chunks with the calibration box and the OOF q90 scales."""
    spec = _dim_spec(int(hold_vectors.shape[1]))
    raw = sim.compute_raw_distances(hold_vectors, level.full_box, spec)
    z = v2.tail_z_rows(hold_vectors, level.full_box.mean, level.full_box.std_sample)
    tails = {p: v2.map_tail_score(v2.worst_p_mean(z, p), level.scale_tail[p]) for p in TAIL_P}
    return map_f1(raw["mean_e"], level.scale_f1), map_f2_l2(raw["z2"], level.scale_f2), tails


def f3_level(
    level: GeometryLevel,
    cal_vectors: np.ndarray,
    hold_vectors: np.ndarray,
    drop_dims: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Repaired F3. Fold means score calibration; the full box scores holdout."""
    cal = np.empty(cal_vectors.shape[0], dtype=np.float64)
    seen = np.zeros(cal_vectors.shape[0], dtype=bool)
    for val, mu, sigma in level.fold_stats:
        cal[val] = v2.positive_f3_bonus(cal_vectors[val], mu, sigma, drop_dims)
        seen[val] = True
    if not np.all(seen):
        raise RuntimeError("F3 OOF left a calibration row unscored")
    hold = v2.positive_f3_bonus(hold_vectors, level.full_mean, level.full_std, drop_dims)
    return cal, hold


def load_calibration_with_hashes(db: Any, profile_id: str, domain: str) -> dict[str, Any]:
    """Read-only calibration load plus full-document ``text_sha256`` in bundle order."""
    table = db.open_table("fhv1_calibration_samples")
    where = (
        f"profile_id = {sim._escape_sql(profile_id)} AND "
        "(strategy_tag = 'full_doc' OR strategy_tag = 'clause_opt2c')"
    )
    arrow = (
        table.search(None)
        .select(["sample_id", "strategy_tag", "source_ref", "normalize", "text_sha256", "vector"])
        .where(where)
        .limit(None)
        .to_arrow()
    )
    normalize = np.array([bool(value) for value in arrow["normalize"].to_pylist()], dtype=bool)
    if not np.all(normalize):
        raise RuntimeError(f"{domain} calibration slice contains normalize=false rows")
    vectors = sim._arrow_fixed_list_to_float64(arrow["vector"], expected_dim=sim.DIM)
    sample_ids = [str(value) for value in arrow["sample_id"].to_pylist()]
    tags = [str(value) for value in arrow["strategy_tag"].to_pylist()]
    refs = [str(value) for value in arrow["source_ref"].to_pylist()]
    digests = [bytes(value).hex() for value in arrow["text_sha256"].to_pylist()]
    if set(refs) != {domain}:
        raise RuntimeError(f"{domain} calibration source_ref values are {sorted(set(refs))}")
    bundle_ids = v2.assign_document_bundle_ids(sample_ids, tags)
    reference = v2.load_calibration_documents(db, profile_id, domain)
    n_bundles = int(reference["n_bundles"])
    full_hashes = [""] * n_bundles
    seen = np.zeros(n_bundles, dtype=bool)
    for i, tag in enumerate(tags):
        if tag != "full_doc":
            continue
        bid = int(bundle_ids[i])
        if seen[bid]:
            raise RuntimeError(f"duplicate full_doc in bundle {bid}")
        full_hashes[bid] = digests[i]
        seen[bid] = True
    if not np.all(seen) or any(not item for item in full_hashes):
        raise RuntimeError(f"{domain} is missing a full_doc hash")
    if not np.array_equal(reference["full_vectors"], _full_vectors_from_rows(vectors, tags, bundle_ids, n_bundles)):
        raise RuntimeError(f"{domain} full_doc vectors diverged from load_calibration_documents")
    if not np.array_equal(reference["clause_vectors"], vectors[np.array([i for i, tag in enumerate(tags) if tag == "clause_opt2c"], dtype=np.int64)]):
        raise RuntimeError(f"{domain} clause vectors diverged from load_calibration_documents")
    loaded = dict(reference)
    loaded["full_doc_sha256"] = full_hashes
    return loaded


def _full_vectors_from_rows(vectors: np.ndarray, tags: Sequence[str], bundle_ids: np.ndarray, n_bundles: int) -> np.ndarray:
    full = np.empty((n_bundles, vectors.shape[1]), dtype=np.float64)
    for i, tag in enumerate(tags):
        if tag == "full_doc":
            full[int(bundle_ids[i])] = vectors[i]
    return full


def _document_channels_for_weight(
    full_cal: Mapping[str, np.ndarray],
    full_hold_chunks: Mapping[str, np.ndarray],
    clause_cal: Mapping[str, np.ndarray] | None,
    clause_hold_chunks: Mapping[str, np.ndarray] | None,
    bundle: sim.PromptBundle,
    calibration: Mapping[str, Any],
    granularity: str,
    w_f: float | None,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    names = tuple(full_cal)
    hold: dict[str, np.ndarray] = {}
    cal: dict[str, np.ndarray] = {}
    for name in names:
        if granularity == "full_only":
            surface, _clause_min = holdout_parts(full_hold_chunks[name], bundle)
            hold[name] = surface
            cal[name] = np.asarray(full_cal[name], dtype=np.float64)
            continue
        if clause_cal is None or clause_hold_chunks is None:
            raise RuntimeError("clauses mode requires the clause model")
        matched = _matched_chunks(full_hold_chunks[name], clause_hold_chunks[name], bundle.chunk_strategies)
        surface, clause_min = holdout_parts(matched, bundle)
        if w_f is None:
            raise RuntimeError("clauses mode requires w_f")
        hold[name] = blend_documents(surface, clause_min, w_f)
        cmin = calibration_clause_min(
            full_cal[name],
            clause_cal[name],
            calibration["clause_bundle_ids"],
            int(calibration["n_bundles"]),
        )
        cal[name] = blend_documents(full_cal[name], cmin, w_f)
    return hold, cal


def _level_channels(
    directional: DirectionalFit,
    geometry: GeometryLevel,
    cal_vectors: np.ndarray,
    hold_vectors: np.ndarray,
    classification: Mapping[str, Any],
    drop_dims: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    cal_f3, hold_f3 = f3_level(geometry, cal_vectors, hold_vectors, drop_dims)
    hold_f1, hold_f2, hold_tail = score_geometry_holdout(geometry, hold_vectors)
    cal: dict[str, np.ndarray] = {
        "f2_l2": geometry.cal_f2,
        "polarity_v2_subset": polarity_v2_subset(cal_vectors, classification),
        "base_repaired": base_repaired_from_factors(geometry.cal_f1, geometry.cal_f2, cal_f3),
    }
    hold: dict[str, np.ndarray] = {
        "f2_l2": hold_f2,
        "polarity_v2_subset": polarity_v2_subset(hold_vectors, classification),
        "base_repaired": base_repaired_from_factors(hold_f1, hold_f2, hold_f3),
    }
    for p in TAIL_P:
        cal[f"tail_p{p}"] = geometry.cal_tail[p]
        hold[f"tail_p{p}"] = hold_tail[p]
    for variant in DIR_VARIANTS:
        cal[variant] = score_dir1024(cal_vectors, directional, variant)
        hold[variant] = score_dir1024(hold_vectors, directional, variant)
    for store in (cal, hold):
        for name, values in store.items():
            if not np.all(np.isfinite(values)):
                raise RuntimeError(f"non-finite channel {name}")
    return cal, hold


def _public_grid_row(spec: RecipeSpec, cal_only: Mapping[str, Mapping[str, np.ndarray]], col: int, roc: float) -> dict[str, Any]:
    block: dict[str, Any] = {"recipe": spec.as_dict(), "roc_auc": roc}
    for _prob, tag in PROB_TAGS:
        metrics = _column_metrics(cal_only[tag], col)
        metrics.pop("roc_auc", None)
        block[tag] = metrics
    return block


def _prediction_at_p10(hold_scores: np.ndarray, threshold: float) -> np.ndarray:
    return np.asarray(hold_scores, dtype=np.float64) >= np.float64(threshold)


def _strip_predictions(block: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in block.items() if key != "predictions"}


def run_replay_v3(
    *,
    lancedb_uri: Path,
    benchmarks_dir: Path,
    bg_parquet: Path,
    augmented_dir: Path,
    task012_report: Path,
    task013_report: Path,
    out_dir: Path,
) -> str:
    """Score the 16 regime cells and write JSON under ``out_dir`` only."""
    import lancedb

    _reject_tracked_output(Path(out_dir))
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    _log("parsing frozen TASK-012 and TASK-013 headlines")
    task012_text = Path(task012_report).read_text(encoding="utf-8")
    task012_rows = v2.parse_frozen_headlines(task012_text)
    v2.verify_frozen_headlines(task012_rows)
    task012_rates = {f"{domain}/{gran}": v2.frozen_rates(row) for (domain, gran), row in task012_rows.items()}
    task013_text = Path(task013_report).read_text(encoding="utf-8")
    task013_rows = parse_task013_headlines(task013_text)
    verify_task013_headlines(task013_rows)
    _log(f"loading background embeddings {bg_parquet}")
    groups = xray.load_embedding_groups(Path(bg_parquet), expected_dim=sim.DIM)
    mu_en = np.mean(groups[("en", "full_doc", "general_prose", True)]["vectors"], axis=0)
    mu_es = np.mean(groups[("es", "full_doc", "general_prose", True)]["vectors"], axis=0)
    db = lancedb.connect(str(lancedb_uri))
    runs = sim.load_lancedb_benchmark_runs(db)
    written: list[dict[str, Any]] = []
    headlines: list[str] = []
    for domain in ("python", "receta"):
        _log(f"joining {domain} calibration text by SHA-256")
        index = load_augmented_hash_index(augmented_jsonl(Path(augmented_dir), domain))
        profile_id = sim.V1_PROFILES[domain]
        calibration = load_calibration_with_hashes(db, profile_id, domain)
        raw_texts = join_full_doc_texts(calibration["full_doc_sha256"], index)
        if len(raw_texts) != 600:
            raise RuntimeError(f"{domain} joined {len(raw_texts)} full documents, expected 600")
        cal_clauses = [xray.segment_clauses_opt2c(text) for text in raw_texts]
        flat_clauses = [clause for doc in cal_clauses for clause in doc]
        if not flat_clauses:
            raise RuntimeError(f"{domain} segmentation produced no clause strings")
        _log(f"fitting S_struct on {domain} raw documents ({len(flat_clauses)} clauses)")
        full_profile = lex.fit(raw_texts, "full_doc")
        clause_profile = lex.fit(flat_clauses, "clause_opt2c")
        cal_struct_scored = score_struct_corpus(raw_texts, cal_clauses, full_profile, clause_profile, time_calls=False)
        rows = v2.load_benchmark_table(Path(benchmarks_dir) / f"{domain}.jsonl")
        text_map = {str(row["input_id"]): str(row["text"]) for row in rows}
        subtypes_map = {str(row["input_id"]): str(row["subtype"]) for row in rows}
        categories_map = {str(row["input_id"]): str(row["category"]) for row in rows}
        expected_map = {str(row["input_id"]): bool(row["expected_pass"]) for row in rows}
        lang = xray.V2_DOMAIN_LANG[domain]
        geometry: dict[str, GeometryLevel] = {}
        bundles: dict[str, sim.PromptBundle] = {}
        hold_texts: dict[str, list[str]] = {}
        hold_struct: dict[str, Any] = {}
        for granularity in ("full_only", "clauses"):
            run = runs[(profile_id, granularity, "m0")]
            bundle = sim.load_prompt_bundle(db, run["run_id"], granularity, subtypes_map, categories_map, expected_map)
            bundles[granularity] = bundle
            texts = [text_map[iid] for iid in bundle.input_ids]
            if set(texts) & set(raw_texts):
                raise RuntimeError(f"{domain}/{granularity} holdout text collided with a calibration document")
            hold_texts[granularity] = texts
            if "full_only" in hold_struct and bundles["full_only"].input_ids == bundle.input_ids:
                hold_struct[granularity] = hold_struct["full_only"]
                continue
            _log(f"scoring holdout S_struct {domain}/{granularity}")
            hold_clauses = [xray.segment_clauses_opt2c(text) for text in texts]
            hold_struct[granularity] = score_struct_corpus(
                texts, hold_clauses, full_profile, clause_profile, time_calls=True
            )
        _log(f"fitting geometry {domain}")
        geometry["full_doc"] = fit_geometry_level(
            calibration["full_vectors"],
            calibration["full_folds"],
            calibration["full_bundle_ids"],
            int(calibration["n_bundles"]),
        )
        geometry["clause_opt2c"] = fit_geometry_level(
            calibration["clause_vectors"],
            calibration["clause_folds"],
            calibration["clause_bundle_ids"],
            int(calibration["n_bundles"]),
        )
        for preset in PRESETS:
            _log(f"contrast {domain}/{preset}")
            contrast_vectors = {
                "full_doc": xray.stack_contrast_preset(groups, lang, "full_doc", preset, normalize=True),
                "clause_opt2c": xray.stack_contrast_preset(groups, lang, "clause_opt2c", preset, normalize=True),
            }
            levels: dict[str, dict[str, dict[str, np.ndarray]]] = {}
            fits: dict[str, DirectionalFit] = {}
            anchor_counts: dict[str, dict[str, int]] = {}
            for gran_name in ("full_doc", "clause_opt2c"):
                cal_vectors = calibration["full_vectors"] if gran_name == "full_doc" else calibration["clause_vectors"]
                fit = fit_directional_matrices(cal_vectors, contrast_vectors[gran_name])
                fits[gran_name] = fit
                classification = xray.classify_dimensions_v2(
                    cal_vectors,
                    contrast_vectors[gran_name],
                    locale_lang_dims=(),
                    general_prose_en_mean=mu_en,
                    general_prose_es_mean=mu_es,
                    target_name=f"{domain}_calibration_{gran_name}",
                    contrast_name=preset,
                )
                if int(classification["bucket_counts"]["LOCALE_LANG_DIMS"]) != 0:
                    raise RuntimeError(f"{domain}/{preset}/{gran_name} locale dims are not empty")
                dial_idx, _dial_mu = v2.dials_from_classification(classification)
                drop = anchor_drop_dims(fit.sep, dial_idx.tolist())
                anchor_counts[gran_name] = {
                    "sep_ge_1": int(np.sum(fit.sep >= np.float64(1.0))),
                    "sep_ge_1_and_sign_flip": int(np.sum((fit.sep >= np.float64(1.0)) & (fit.mu_t * fit.mu_c < 0.0))),
                    "polarity_dials": int(dial_idx.size),
                    "tie_count": int(fit.tie_count),
                }
                for regime in ("full_only", "clauses"):
                    if regime == "full_only" and gran_name == "clause_opt2c":
                        continue
                    hold_vectors = bundles[regime].chunk_vectors
                    cal_ch, hold_ch = _level_channels(
                        fit, geometry[gran_name], cal_vectors, hold_vectors, classification, drop
                    )
                    levels.setdefault(regime, {})[gran_name] = {"cal": cal_ch, "hold": hold_ch}
            for granularity in ("full_only", "clauses"):
                _log(f"grid {domain}/{granularity}/{preset}")
                cell = _evaluate_cell(
                    domain=domain,
                    granularity=granularity,
                    preset=preset,
                    bundle=bundles[granularity],
                    calibration=calibration,
                    full_channels=levels[granularity]["full_doc"],
                    clause_channels=levels[granularity].get("clause_opt2c"),
                    hold_struct=hold_struct[granularity],
                    cal_struct=cal_struct_scored,
                    texts=hold_texts[granularity],
                    anchor_counts=anchor_counts,
                    frozen=frozen_f1_for_cell(domain, granularity, task012_rates, task013_rows),
                )
                payload = v2.to_jsonable(cell)
                text = json.dumps(payload, indent=2, allow_nan=False)
                filename = f"{domain}__{granularity}__{preset}.json"
                destination = out_path / filename
                destination.write_text(text, encoding="utf-8")
                size = destination.stat().st_size
                written.append(
                    {
                        "file": filename,
                        "domain": domain,
                        "granularity": granularity,
                        "preset": preset,
                        "bytes": int(size),
                        "headline_label": cell["headline"]["label"],
                        "headline_recipe": cell["headline"]["recipe"],
                        "cal_only_p10_f1": cell["headline"]["f1"],
                    }
                )
                headlines.append(
                    f"{domain}/{granularity}/{preset} {cell['headline']['label']} "
                    f"{cell['headline']['recipe']} p10_f1={cell['headline']['f1']:.6f}"
                )
                _log(headlines[-1])
    manifest = {
        "mode": "v3",
        "dtype": "float64",
        "dim": sim.DIM,
        "normalize": True,
        "n_cells": len(written),
        "cells": written,
        "bootstrap_resamples": v2.BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": 0,
        "bootstrap_refits_thresholds": True,
        "primary": "document_level_CAL_ONLY",
        "output_dir": str(out_path),
    }
    manifest_path = out_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["fhv1_1 replay v3", f"cells={len(written)} dir={out_path}", *headlines, f"manifest={manifest_path} bytes={manifest_path.stat().st_size}"]
    return "\n".join(lines)


def _evaluate_cell(
    *,
    domain: str,
    granularity: str,
    preset: str,
    bundle: sim.PromptBundle,
    calibration: Mapping[str, Any],
    full_channels: Mapping[str, Mapping[str, np.ndarray]],
    clause_channels: Mapping[str, Mapping[str, np.ndarray]] | None,
    hold_struct: Mapping[str, Any],
    cal_struct: Mapping[str, Any],
    texts: Sequence[str],
    anchor_counts: Mapping[str, Mapping[str, int]],
    frozen: Mapping[str, float],
) -> dict[str, Any]:
    hold_by_weight: dict[float | None, dict[str, np.ndarray]] = {}
    cal_by_weight: dict[float | None, dict[str, np.ndarray]] = {}
    for weight in weights_for(granularity):
        hold_ch, cal_ch = _document_channels_for_weight(
            full_channels["cal"],
            full_channels["hold"],
            None if clause_channels is None else clause_channels["cal"],
            None if clause_channels is None else clause_channels["hold"],
            bundle,
            calibration,
            granularity,
            weight,
        )
        hold_by_weight[weight] = hold_ch
        cal_by_weight[weight] = cal_ch
    struct_hold = {
        "full_doc": np.asarray(hold_struct["s_full"], dtype=np.float64),
        "min_full_clause": np.asarray(hold_struct["s_min"], dtype=np.float64),
    }
    struct_cal = {
        "full_doc": np.asarray(cal_struct["s_full"], dtype=np.float64),
        "min_full_clause": np.asarray(cal_struct["s_min"], dtype=np.float64),
    }
    specs, hold, cal = materialize_recipes(hold_by_weight, cal_by_weight, struct_hold, struct_cal, granularity)
    y = bundle.expected_pass
    cal_only = evaluate_cal_only_matrix(cal, hold, y, with_roc=False)
    roc = roc_columns(y, hold)
    for tag in cal_only:
        cal_only[tag]["roc_auc"] = roc
    nested = nested_repeated_oof(hold, y, bundle.categories, bundle.subtypes, bundle.input_ids)
    modal = int(nested["modal_column"])
    modal_spec = specs[modal]
    nested_metrics, nested_oracle = detach_oracle(dict(nested))
    nested_public = _strip_predictions(_pack_repeated(nested_metrics))
    nested_public["modal_column"] = modal
    nested_public["modal_wins"] = int(nested["modal_wins"])
    nested_public["modal_recipe"] = modal_spec.as_dict()
    modal_cal = evaluate_cal_only(cal[:, modal], hold[:, modal], y)
    modal_repeated = repeated_stratified_oof(hold[:, modal], y, bundle.categories, bundle.subtypes, bundle.input_ids)
    modal_repeated_public, modal_oracle = detach_oracle(dict(modal_repeated))
    reference_columns: list[tuple[str, int]] = [("nested_modal", modal)]
    for family in DIR_VARIANTS:
        for weight in weights_for(granularity):
            reference_columns.append(
                (
                    f"{family}|a=0|b=0|w={'-' if weight is None else f'{weight:.2f}'}",
                    _find_spec(
                        specs,
                        family=family,
                        coupling="identity",
                        alpha=0.0,
                        guard=None,
                        struct_hook="beta",
                        beta=0.0,
                        gamma=None,
                        struct_reduction="full_doc",
                        w_f=weight,
                    ),
                )
            )
    for family in BASELINES:
        for weight in weights_for(granularity):
            reference_columns.append(
                (
                    f"{family}|b=0|w={'-' if weight is None else f'{weight:.2f}'}",
                    _find_spec(
                        specs,
                        family=family,
                        coupling="identity",
                        alpha=0.0,
                        guard=None,
                        struct_hook="beta",
                        beta=0.0,
                        gamma=None,
                        struct_reduction="full_doc",
                        w_f=weight,
                    ),
                )
            )
    methods = {name: (hold[:, col], cal[:, col]) for name, col in reference_columns}
    boot = bootstrap_cal_only_paired(
        methods,
        y,
        bundle.categories,
        bundle.subtypes,
        seed=0,
        n_resamples=v2.BOOTSTRAP_RESAMPLES,
        probability=BOOTSTRAP_PROBABILITY,
        frozen_f1=frozen,
    )
    primary_dir = []
    primary_base = []
    oracles: list[dict[str, Any]] = []
    if nested_oracle is not None:
        oracles.append({"source": "nested_mixed_seed0", **nested_oracle})
    if modal_oracle is not None:
        oracles.append({"source": "modal_recipe_repeated_oof", **modal_oracle})
    fixed_rows = []
    for name, col in reference_columns:
        if name == "nested_modal":
            continue
        spec = specs[col]
        cal_block = {tag: _column_metrics(cal_only[tag], col) for _prob, tag in PROB_TAGS}
        repeated = repeated_stratified_oof(hold[:, col], y, bundle.categories, bundle.subtypes, bundle.input_ids)
        repeated_public, oracle = detach_oracle(dict(repeated))
        if oracle is not None:
            oracles.append({"source": spec.name(), **oracle})
        row = {
            "recipe": spec.as_dict(),
            "cal_only": cal_block,
            "repeated_oof_5x5": _pack_repeated(repeated_public),
            "bootstrap_95ci": boot["methods"][name],
        }
        fixed_rows.append(row)
        if spec.family in DIR_VARIANTS:
            primary_dir.append(row)
        else:
            primary_base.append(row)
    pred = _prediction_at_p10(hold[:, modal], float(modal_cal["p10"]["threshold"]))
    breakdown = _subgroup_block(y, pred, bundle.categories, bundle.subtypes)
    w_effect = []
    for family in (*DIR_VARIANTS, *BASELINES):
        for weight in weights_for(granularity):
            col = _find_spec(
                specs,
                family=family,
                coupling="identity",
                alpha=0.0,
                guard=None,
                struct_hook="beta",
                beta=0.0,
                gamma=None,
                struct_reduction="full_doc",
                w_f=weight,
            )
            threshold = float(cal_only["p10"]["threshold"][col])
            decision = _prediction_at_p10(hold[:, col], threshold)
            cats = np.asarray(list(bundle.categories), dtype=object)
            subs = np.asarray(list(bundle.subtypes), dtype=object)
            w_effect.append(
                {
                    "family": family,
                    "w_f": None if weight is None else float(weight),
                    "alpha": 0.0,
                    "beta": 0.0,
                    "threshold_p10": threshold,
                    "in_domain_valid": v2.subgroup_error(y, decision, cats == "IN_DOMAIN_VALID"),
                    "smuggle_recipe_footnote": v2.subgroup_error(y, decision, subs == "smuggle_recipe_footnote"),
                    "dilution_80_20": v2.subgroup_error(y, decision, subs == "dilution_80_20"),
                }
            )
    grid = [_public_grid_row(spec, cal_only, col, float(roc[col])) for col, spec in enumerate(specs)]
    return {
        "mode": "v3",
        "domain": domain,
        "granularity": granularity,
        "preset": preset,
        "n_prompts": int(len(bundle.input_ids)),
        "n_calibration_bundles": int(calibration["n_bundles"]),
        "dtype": "float64",
        "normalize": True,
        "locale_lang_dims": [],
        "directional_tie_and_anchors": anchor_counts,
        "headline": {
            "label": "nested_modal_recipe_cal_only_p10",
            "recipe": modal_spec.name(),
            "f1": float(modal_cal["p10"]["f1"]),
            "frr": modal_cal["p10"]["frr"],
            "far": modal_cal["p10"]["far"],
        },
        "primary": {
            "rule": "document_level_CAL_ONLY",
            "holdout_labels_in_threshold": False,
            "nested_selected": {
                "selection": "modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column",
                "recipe": modal_spec.as_dict(),
                "wins": int(nested["modal_wins"]),
                "cal_only": modal_cal,
            },
            "dir1024_alpha0_beta0": [row for row in primary_dir],
            "baselines_alpha0_beta0": [row for row in primary_base],
        },
        "secondary_repeated_oof_5x5": {
            "nested_mixed": nested_public,
            "modal_recipe_fixed": _pack_repeated(modal_repeated_public),
            "dir1024_alpha0_beta0": [
                {"recipe": row["recipe"], "repeated_oof_5x5": row["repeated_oof_5x5"]} for row in primary_dir
            ],
            "baselines_alpha0_beta0": [
                {"recipe": row["recipe"], "repeated_oof_5x5": row["repeated_oof_5x5"]} for row in primary_base
            ],
        },
        "bootstrap": {
            "n_resamples": boot["n_resamples"],
            "seed": boot["seed"],
            "refits_thresholds": True,
            "threshold_policy": boot["threshold_policy"],
            "probability": boot["probability"],
            "frozen_f1": dict(frozen),
            "nested_selected": boot["methods"]["nested_modal"],
            "dir1024_alpha0_beta0": {name: boot["methods"][name] for name, _col in reference_columns if name.startswith("dir1024_")},
            "baselines_alpha0_beta0": {
                name: boot["methods"][name]
                for name, _col in reference_columns
                if not name.startswith("dir1024_") and name != "nested_modal"
            },
        },
        "oracle_upper_bound": oracles,
        "grid_cal_only": grid,
        "quadrants": breakdown["quadrants"],
        "subtypes": breakdown["subtypes"],
        "canary_sqlite_subprocess_json": _canary_block(texts, bundle.categories, y, pred),
        "struct_firing": _struct_firing(bundle.categories, bundle.subtypes, hold_struct),
        "struct_latency_us": _latency_block(hold_struct["full_us"], hold_struct["clause_us"]),
        "w_f_effect": w_effect,
        "composition": {
            "document_statistic": "fail_closed_min then blend_full_min_clause when granularity is clauses",
            "guard_coupling": "alpha applied to document scores",
            "struct_hook": "beta and gamma applied after the guard coupling",
            "calibration_directional_fit": "all calibration rows at the scored granularity; zero holdout rows",
            "calibration_geometry": "5-fold OOF on calibration bundles for F1, F2_L2, Tail-Z, and repaired F3",
            "bootstrap_refits_thresholds": True,
        },
    }


def format_v3_summary(text: str) -> str:
    return text
