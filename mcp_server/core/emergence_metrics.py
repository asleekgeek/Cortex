"""Emergence tracker — forgetting curve fitting and aggregate report.

source: ADR-0171

Pure business logic — no I/O.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

# source: ADR-0171

# source: ADR-0171
_OLS_EPSILON = 1e-10

# source: ADR-0171
# source: ADR-0171
_FIT_R2_POOR = 0.10
_FIT_R2_WEAK = 0.50

# source: ADR-0171

# source: ADR-0171
_MIN_FIT_POINTS = 5
_MIN_FIT_BINS = 3

# source: ADR-0171

# source: ADR-0171
_HEAT_FLOOR = 0.01

# source: ADR-0171

# source: ADR-0171
_SCHEMA_MATCH_HIGH = 0.5
_SCHEMA_MATCH_LOW = 0.3

# source: ADR-0171
# source: ADR-0171
_THETA_PHASE_SPLIT = 0.5

# source: ADR-0171

# source: ADR-0171
_ALIVE_HEAT = 0.1

# ── Forgetting Curve ─────────────────────────────────────────────────────


def _bin_memories_by_age(
    memories_by_age: list[tuple[float, float]],
    bin_width_hours: float = 6.0,
) -> list[tuple[float, float]]:
    """Bin memories by age and compute average heat per bin.

    Args:
        memories_by_age: List of (age_hours, heat) tuples.
        bin_width_hours: Width of each bin in hours.

    Returns:
        List of (bin_center_hours, mean_heat) tuples, sorted by age.
    """
    bins: dict[int, list[float]] = {}
    for age, heat in memories_by_age:
        bin_idx = max(0, int(age / bin_width_hours))
        bins.setdefault(bin_idx, []).append(heat)

    return [
        (bin_idx * bin_width_hours + bin_width_hours / 2, sum(heats) / len(heats))
        for bin_idx, heats in sorted(bins.items())
    ]


_DEGENERATE_RESULT = {
    "curve_type": "degenerate",
    "r_squared": 0.0,
    "fit_quality": "degenerate",
    "half_life_hours": 0.0,
    "retention_at_24h": 0.0,
}


def _ols_sums(
    log_heats: list[tuple[float, float]],
) -> tuple[int, float, float, float, float]:
    """Compute OLS summary statistics."""
    n = len(log_heats)
    sum_x = sum(t for t, _ in log_heats)
    sum_y = sum(y for _, y in log_heats)
    sum_xy = sum(t * y for t, y in log_heats)
    sum_x2 = sum(t * t for t, _ in log_heats)
    return n, sum_x, sum_y, sum_xy, sum_x2


def _fit_log_linear(
    log_heats: list[tuple[float, float]],
) -> dict[str, float | str]:
    """Fit log-linear regression: log(heat) = log(a) - b * age via OLS.

    source: ADR-0171

    Returns dict with curve_type, r_squared, half_life_hours,
    retention_at_24h, decay_rate, initial_retention, and a
    ``fit_quality`` flag (darval's v3.13.2 P3 — signal when r²
    is too low to trust the derived metrics).
    """
    n, sum_x, sum_y, sum_xy, sum_x2 = _ols_sums(log_heats)

    denom = n * sum_x2 - sum_x**2
    if abs(denom) < _OLS_EPSILON:
        return dict(_DEGENERATE_RESULT)

    b = -(n * sum_xy - sum_x * sum_y) / denom
    log_a = (sum_y + b * sum_x) / n
    a = math.exp(log_a)

    mean_y = sum_y / n
    ss_tot = sum((y - mean_y) ** 2 for _, y in log_heats)
    ss_res = sum((y - (log_a - b * t)) ** 2 for t, y in log_heats)
    r2 = 1.0 - ss_res / max(ss_tot, 1e-10)
    r2_clamped = max(0.0, r2)

    half_life = math.log(2) / max(b, 1e-10) if b > 0 else float("inf")
    retention_24h = a * math.exp(-b * 24) if b > 0 else a

    return {
        "curve_type": "exponential",
        "r_squared": round(r2_clamped, 4),
        "fit_quality": _fit_quality_for(r2_clamped),
        "half_life_hours": round(min(half_life, 10000), 1),
        "retention_at_24h": round(max(0.0, min(1.0, retention_24h)), 4),
        "decay_rate": round(b, 6),
        "initial_retention": round(min(a, 1.0), 4),
    }


def _fit_quality_for(r_squared: float) -> str:
    """Bucket the fit r² into a consumer-friendly quality label.

    source: ADR-0171"""
    if r_squared < _FIT_R2_POOR:
        return "poor"
    if r_squared < _FIT_R2_WEAK:
        return "weak"
    return "good"


_INSUFFICIENT = {
    "curve_type": "insufficient_data",
    "r_squared": 0.0,
    "fit_quality": "insufficient_data",
    "half_life_hours": 0.0,
    "retention_at_24h": 0.0,
}


def compute_forgetting_curve(
    memories_by_age: list[tuple[float, float]],
) -> dict[str, float | str]:
    """Fit a forgetting curve to memory age vs heat data.

    source: ADR-0171

    Args:
        memories_by_age: List of (age_hours, heat) tuples.

    Returns:
        Dict with: curve_type, r_squared, half_life_hours, retention_at_24h.
    """
    if len(memories_by_age) < _MIN_FIT_POINTS:
        return dict(_INSUFFICIENT)

    bin_means = _bin_memories_by_age(memories_by_age)
    return _forgetting_from_bin_means(bin_means, n_points=len(memories_by_age))


def _forgetting_from_bin_means(
    bin_means: list[tuple[float, float]], n_points: int
) -> dict[str, float | str]:
    """Fit the curve from already-binned (center, mean_heat) data.

    source: ADR-0171"""
    if n_points < _MIN_FIT_POINTS:
        return dict(_INSUFFICIENT)
    if len(bin_means) < _MIN_FIT_BINS:
        return {
            "curve_type": "insufficient_bins",
            "r_squared": 0.0,
            "fit_quality": "insufficient_data",
            "half_life_hours": 0.0,
            "retention_at_24h": 0.0,
        }

    log_heats = [
        (t, math.log(max(h, _HEAT_FLOOR))) for t, h in bin_means if h > _HEAT_FLOOR
    ]
    if len(log_heats) < _MIN_FIT_BINS:
        return {
            "curve_type": "no_fit",
            "r_squared": 0.0,
            "fit_quality": "insufficient_data",
            "half_life_hours": 0.0,
            "retention_at_24h": 0.0,
        }

    return _fit_log_linear(log_heats)


def _bins_to_means(bins: dict[int, list]) -> list[tuple[float, float]]:
    """Convert online ``bin_idx -> [heat_sum, count]`` to sorted bin means."""
    return [
        (bin_idx * 6.0 + 3.0, hs / cnt)
        for bin_idx, (hs, cnt) in sorted(bins.items())
        if cnt
    ]


# ── Aggregate Report ─────────────────────────────────────────────────────


def generate_emergence_report(
    memories: list[dict],
    events: list | None = None,
) -> dict:
    """Generate a full emergence report from an in-memory list.

    source: ADR-0171"""
    return generate_emergence_report_streamed([memories], events=events)


def _schema_acceleration_from_agg(cons: dict, incons: dict) -> dict:
    """schema-acceleration metric from streamed cohort aggregates.

    source: ADR-0171"""
    c_count, i_count = cons["count"], incons["count"]
    c_time = (
        cons["time_sum"] / cons["consolidated"]
        if cons["consolidated"]
        else float("inf")
    )
    i_time = (
        incons["time_sum"] / incons["consolidated"]
        if incons["consolidated"]
        else float("inf")
    )
    ratio_defined = True
    reason = ""
    if c_count == 0:
        ratio_defined, reason, ratio = False, "no_schemas_promoted_yet", 1.0
    elif i_count == 0:
        ratio_defined, reason, ratio = False, "no_baseline_population", 1.0
    elif i_time > 0 and c_time < float("inf"):
        ratio = i_time / max(c_time, 0.1)
    else:
        ratio_defined, reason, ratio = False, "no_consolidated_memories", 1.0
    out = {
        "consistent_count": c_count,
        "inconsistent_count": i_count,
        "consistent_consolidated_fraction": round(
            cons["consolidated"] / c_count if c_count else 0.0, 4
        ),
        "inconsistent_consolidated_fraction": round(
            incons["consolidated"] / i_count if i_count else 0.0, 4
        ),
        "acceleration_ratio": round(ratio, 4),
        "ratio_defined": ratio_defined,
    }
    if reason:
        out["reason_for_undefined"] = reason
    return out


def _phase_locking_from_agg(enc: dict, ret: dict) -> dict:
    """phase-locking metric from streamed per-phase aggregates."""

    def avg(d: dict) -> float:
        return d["heat_sum"] / d["count"] if d["count"] else 0.0

    def surv(d: dict) -> float:
        return d["alive"] / d["count"] if d["count"] else 0.0

    enc_heat, ret_heat = avg(enc), avg(ret)
    return {
        "encoding_phase_count": enc["count"],
        "retrieval_phase_count": ret["count"],
        "encoding_phase_avg_heat": round(enc_heat, 4),
        "retrieval_phase_avg_heat": round(ret_heat, 4),
        "phase_benefit": round(enc_heat - ret_heat, 4),
        "encoding_phase_survival": round(surv(enc), 4),
        "retrieval_phase_survival": round(surv(ret), 4),
    }


def generate_emergence_report_streamed(
    memory_chunks,
    events: list | None = None,
) -> dict:
    """Constant-memory emergence report: one streaming pass of bounded reducers.

    source: ADR-0171"""
    bins: dict[int, list] = {}  # bin_idx -> [heat_sum, count]
    n_age = 0
    cons = {"count": 0, "consolidated": 0, "time_sum": 0.0}
    incons = {"count": 0, "consolidated": 0, "time_sum": 0.0}
    enc = {"count": 0, "heat_sum": 0.0, "alive": 0}
    ret = {"count": 0, "heat_sum": 0.0, "alive": 0}
    stage_dist: dict[str, int] = {}
    interference_sum = 0.0
    total = 0

    for chunk in memory_chunks:
        for m in chunk:
            total += 1
            heat = m.get("heat", 0)
            if heat > _HEAT_FLOOR:
                bucket = bins.setdefault(
                    max(0, int((m.get("hours_in_stage", 0) + 1.0) / 6.0)), [0.0, 0]
                )
                bucket[0] += heat
                bucket[1] += 1
                n_age += 1
            score = m.get("schema_match_score", 0)
            consolidated = m.get("consolidation_stage") == "consolidated"
            if score >= _SCHEMA_MATCH_HIGH:
                _fold_schema_cohort(cons, m, consolidated)
            elif score < _SCHEMA_MATCH_LOW:
                _fold_schema_cohort(incons, m, consolidated)
            phase = (
                enc if m.get("theta_phase_at_encoding", 0) < _THETA_PHASE_SPLIT else ret
            )
            phase["count"] += 1
            phase["heat_sum"] += m.get("heat", 0)
            if m.get("heat", 0) >= _ALIVE_HEAT:
                phase["alive"] += 1
            stage = m.get("consolidation_stage", "unknown")
            stage_dist[stage] = stage_dist.get(stage, 0) + 1
            interference_sum += m.get("interference_score", 0)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "memory_count": total,
        "forgetting_curve": _forgetting_from_bin_means(_bins_to_means(bins), n_age),
        "schema_acceleration": _schema_acceleration_from_agg(cons, incons),
        "phase_locking": _phase_locking_from_agg(enc, ret),
        "stage_distribution": stage_dist,
        "avg_interference": round(interference_sum / max(total, 1), 4),
    }


def _fold_schema_cohort(cohort: dict, mem: dict, consolidated: bool) -> None:
    """Fold one memory into a schema cohort aggregate."""
    cohort["count"] += 1
    if consolidated:
        cohort["consolidated"] += 1
        cohort["time_sum"] += mem.get("hours_in_stage", 0) + 24.0
