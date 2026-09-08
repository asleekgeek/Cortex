"""Platt scaling calibration for FlashRank cross-encoder scores.

source: ADR-0222
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# source: ADR-0222

# source: ADR-0222
_SINGULAR_DET_EPS = 1e-12

# ── Defaults ───────────────────────────────────────────────────────────

# source: ADR-0222
# source: ADR-0222
MIN_SAMPLES: int = 50
# source: ADR-0222
MAX_ITERATIONS: int = 100
# source: ADR-0222
CONVERGENCE_TOL: float = 1e-5  # Gradient norm below this -> fit done.


@dataclass(frozen=True)
class PlattParams:
    """Fitted logistic regression parameters for Platt scaling.

    source: ADR-0222

    Invariants:
      - A and B are finite real numbers.
      - ``n_samples`` is the training-set size at fit time.
      - When applied: P = 1 / (1 + exp(A * raw_score + B)).
    """

    A: float
    B: float
    n_samples: int


# ── Training sample shape ─────────────────────────────────────────────────


@dataclass
class TrainingSample:
    """One (raw_score, label) pair from user rate_memory feedback.

    ``raw_score`` is the FlashRank CE score at the time the memory was
    surfaced. ``label`` is 1 if the user marked useful, 0 otherwise.
    """

    raw_score: float
    label: int  # 0 or 1


# ── Fit (Newton-Raphson on log-likelihood) ────────────────────────────────


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        ex = math.exp(-x)
        return 1.0 / (1.0 + ex)
    ex = math.exp(x)
    return ex / (1.0 + ex)


def _predict_platt(A: float, B: float, s: float) -> float:  # noqa: N803 — source: ADR-0222
    """Predicted P(useful | s) under parameters (A, B)."""
    return _sigmoid(-(A * s + B))


def _smoothed_target(y: int, n_pos: int, n_neg: int) -> float:
    """Platt-smoothed regression target for one example.

    source: ADR-0222
    """
    if y == 1:
        return (n_pos + 1.0) / (n_pos + 2.0)
    return 1.0 / (n_neg + 2.0)


def fit_platt(
    samples: list[TrainingSample],
    *,
    min_samples: int = MIN_SAMPLES,
    max_iter: int = MAX_ITERATIONS,
    tol: float = CONVERGENCE_TOL,
) -> PlattParams | None:
    """Fit A, B via Newton-Raphson on the logistic log-likelihood.

    Contract:
      pre:  ``samples`` is a list where each entry has raw_score in R
            and label in {0, 1}.
      post: Returns None if len(samples) < min_samples OR if all labels
            are identical (degenerate case — logistic loss unbounded).
            Otherwise returns finite PlattParams where A, B are the MLE
            solution to the Bernoulli log-likelihood under the sigmoid.

    Newton-Raphson updates:
      grad = sum_i (p_i - y_i) * [-s_i, -1]
      Hess = sum_i p_i * (1 - p_i) * [[s_i^2, s_i], [s_i, 1]]
      [A, B] -= Hess^-1 @ grad

    source: ADR-0222"""
    n = len(samples)
    if n < min_samples:
        return None
    labels = [s.label for s in samples]
    if all(lbl == labels[0] for lbl in labels):
        # Degenerate: logistic MLE diverges when classes are pure.
        return None

    # source: ADR-0222
    n_pos = sum(labels)
    n_neg = n - n_pos
    prior1 = (n_pos + 1.0) / (n + 2.0)  # Laplace-smoothed base rate.
    A, B = 0.0, math.log((n_neg + 1.0) / (n_pos + 1.0))  # noqa: N806 — source: ADR-0222

    for _ in range(max_iter):
        # Accumulate gradient and Hessian.
        g_a, g_b = 0.0, 0.0
        h_aa, h_ab, h_bb = 0.0, 0.0, 0.0
        for sample in samples:
            s = sample.raw_score
            y = sample.label
            p = _sigmoid(-(A * s + B))
            t = _smoothed_target(y, n_pos, n_neg)
            d = p - t
            g_a += d * (-s)  # partial derivative w.r.t. A
            g_b += d * (-1.0)
            w = p * (1.0 - p)
            h_aa += w * s * s
            h_ab += w * s
            h_bb += w * 1.0

        # Gradient norm test.
        if math.sqrt(g_a * g_a + g_b * g_b) < tol:
            break

        # Solve 2x2 Hessian: [[h_aa, h_ab], [h_ab, h_bb]] @ delta = grad
        det = h_aa * h_bb - h_ab * h_ab
        if abs(det) < _SINGULAR_DET_EPS:
            break  # Hessian singular — cannot step.
        inv = 1.0 / det
        d_a = inv * (h_bb * g_a - h_ab * g_b)
        d_b = inv * (-h_ab * g_a + h_aa * g_b)
        A -= d_a  # noqa: N806 — source: ADR-0222
        B -= d_b  # noqa: N806 — source: ADR-0222

    # Guard: reject non-finite parameters.
    if not (math.isfinite(A) and math.isfinite(B)):
        return None

    # Use prior1 for observability only (not the returned value).
    _ = prior1
    return PlattParams(A=A, B=B, n_samples=n)


# ── Apply ─────────────────────────────────────────────────────────────────


def calibrate_score(raw_score: float, params: PlattParams | None) -> float:
    """Return the calibrated P(useful | raw_score).

    source: ADR-0222

    Contract:
      pre:  raw_score is finite; params is either None or a fitted PlattParams.
      post: Returns raw_score unchanged when params is None (no-op fallback);
            otherwise returns a probability in (0, 1) via sigmoid(-(A*s + B)).
    """
    if params is None:
        return raw_score
    return _predict_platt(params.A, params.B, raw_score)


def calibrate_scores(
    raw_scores: list[float],
    params: PlattParams | None,
) -> list[float]:
    """Vectorised apply for a list of raw CE scores."""
    if params is None:
        return list(raw_scores)
    return [_predict_platt(params.A, params.B, s) for s in raw_scores]


# ── Pairwise discrimination metric (for tests) ─────────────────────────────


def pairwise_discrimination(
    params: PlattParams | None,
    useful_scores: list[float],
    not_useful_scores: list[float],
) -> float:
    """Fraction of (useful, not-useful) pairs where calibrated(useful) >
    calibrated(not-useful).

    source: ADR-0222

    Returns a float in [0, 1]. 1.0 = perfect pairwise separation.
    """
    calibrated_useful = calibrate_scores(useful_scores, params)
    calibrated_not = calibrate_scores(not_useful_scores, params)
    if not calibrated_useful or not calibrated_not:
        return 0.5  # No pairs to compare.
    total = 0
    wins = 0
    for u in calibrated_useful:
        for n in calibrated_not:
            total += 1
            if u > n:
                wins += 1
    return wins / total if total > 0 else 0.5
