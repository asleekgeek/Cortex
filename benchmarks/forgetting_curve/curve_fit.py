"""Pure curve-fitting helpers for the forgetting-curve fidelity benchmark.

source: ADR-0829
"""

from __future__ import annotations

import math

# source: ADR-0829


AIC_INDISTINGUISHABLE = 2.0

# source: ADR-0829


# source: ADR-0829
_NEAR_ZERO_TOL = 1e-12


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Ordinary least squares of ys on xs. Returns (slope, intercept, r2)."""
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    # source: ADR-0829

    sxy = sum(x * y for x, y in zip(xs, ys, strict=True))
    sx2 = sum(x * x for x in xs)
    denom = n * sx2 - sx * sx
    if abs(denom) < _NEAR_ZERO_TOL:
        return 0.0, sy / n if n else 0.0, 0.0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    mean_y = sy / n
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    # strict=True: same paired-observations invariant as sxy above.
    ss_res = sum(
        (y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys, strict=True)
    )
    r2 = 1.0 - ss_res / ss_tot if ss_tot > _NEAR_ZERO_TOL else 0.0
    return slope, intercept, r2


def _r2_hspace(points: list[tuple[float, float]], pred) -> tuple[float, float]:
    """r² and RSS of a model `pred(t)->h` against actual h, in h-space."""
    heats = [h for _, h in points]
    mean_h = sum(heats) / len(heats)
    ss_tot = sum((h - mean_h) ** 2 for h in heats)
    ss_res = sum((h - pred(t)) ** 2 for t, h in points)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > _NEAR_ZERO_TOL else 0.0
    return r2, ss_res


def _aic(rss: float, n: int, k: int = 3) -> float:
    """AIC for a Gaussian-residual model. k = slope+intercept+variance = 3."""
    if rss <= 0.0:
        rss = 1e-300
    return n * math.log(rss / n) + 2 * k


def fit_exponential(points: list[tuple[float, float]]) -> dict:
    """Fit h = a·exp(-b·t). points = [(age_hours, heat), …], heat>0."""
    ts = [t for t, _ in points]
    ln_h = [math.log(h) for _, h in points]
    neg_b, ln_a, r2_fit = _ols(ts, ln_h)
    a, b = math.exp(ln_a), -neg_b

    def pred(t: float) -> float:
        return a * math.exp(-b * t)

    r2_h, rss_h = _r2_hspace(points, pred)
    half_life = math.log(2) / b if b > _NEAR_ZERO_TOL else float("inf")
    return {
        "model": "exponential",
        "a": round(a, 6),
        "b_per_hour": round(b, 8),
        "r2_fitspace": round(max(0.0, r2_fit), 5),
        "r2_hspace": round(max(0.0, r2_h), 5),
        "rss_hspace": rss_h,
        "aic_hspace": round(_aic(rss_h, len(points)), 3),
        "half_life_hours": (round(half_life, 2) if math.isfinite(half_life) else None),
    }


def fit_power_law(points: list[tuple[float, float]]) -> dict:
    """Fit h = a·t^(-b). points = [(age_hours, heat), …], t>0, heat>0."""
    ln_t = [math.log(t) for t, _ in points]
    ln_h = [math.log(h) for _, h in points]
    neg_b, ln_a, r2_fit = _ols(ln_t, ln_h)
    a, b = math.exp(ln_a), -neg_b

    def pred(t: float) -> float:
        return a * (t ** (-b))

    r2_h, rss_h = _r2_hspace(points, pred)
    # Power-law half-life: t at which h = a·t^-b falls to half of h(1h)=a.
    half_life = 2.0 ** (1.0 / b) if b > _NEAR_ZERO_TOL else float("inf")
    return {
        "model": "power_law",
        "a": round(a, 6),
        "b_exponent": round(b, 6),
        "r2_fitspace": round(max(0.0, r2_fit), 5),
        "r2_hspace": round(max(0.0, r2_h), 5),
        "rss_hspace": rss_h,
        "aic_hspace": round(_aic(rss_h, len(points)), 3),
        "half_life_hours": (round(half_life, 2) if math.isfinite(half_life) else None),
    }


def compare_models(power: dict, expo: dict) -> dict:
    """Power-law-over-exponential verdict via ΔAIC in h-space.

    delta_aic = AIC_exp - AIC_power. Positive ⇒ power law favoured.
    Power law is "at least as good" iff it is not meaningfully worse than
    exponential: AIC_power ≤ AIC_exp + AIC_INDISTINGUISHABLE.
    """
    delta_aic = expo["aic_hspace"] - power["aic_hspace"]
    power_at_least_as_good = (
        power["aic_hspace"] <= expo["aic_hspace"] + AIC_INDISTINGUISHABLE
    )
    if delta_aic > AIC_INDISTINGUISHABLE:
        winner = "power_law"
    elif delta_aic < -AIC_INDISTINGUISHABLE:
        winner = "exponential"
    else:
        winner = "indistinguishable"
    return {
        "delta_aic_exp_minus_power": round(delta_aic, 3),
        "aic_threshold": AIC_INDISTINGUISHABLE,
        "winner": winner,
        "power_law_at_least_as_good": power_at_least_as_good,
        "r2_hspace_power": power["r2_hspace"],
        "r2_hspace_exp": expo["r2_hspace"],
    }
