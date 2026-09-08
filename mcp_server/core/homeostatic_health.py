"""Homeostatic plasticity — distribution health metrics.

source: ADR-0190"""

from __future__ import annotations

import math

# source: ADR-0190

# source: ADR-0190
_STD_EPSILON = 1e-10

# source: ADR-0190

# source: ADR-0190
_LOW_STD_THRESHOLD = 0.05


def _compute_moments(
    values: list[float],
) -> tuple[float, float, float, float]:
    """Compute mean, std, skewness, and excess kurtosis in a single pass.

    source: ADR-0190

    After the loop, the variance, skewness and excess-kurtosis estimators
    match the biased-n formulations used by the original implementation:
        variance    = M2 / (n-1)        — sample variance
        skew        = M3 / (n * std^3)
        kurtosis_ex = M4 / (n * std^4) - 3.0

    Args:
        values: Non-empty list of numeric values.

    Returns:
        Tuple of (mean, std, skew, kurtosis_excess). For empty input
        returns (0, 0, 0, 0).

    Precondition: values is iterable of finite floats.
    Postcondition: results are within 1e-9 of the four-pass implementation
    on well-conditioned inputs.
    Invariant: after n values, (m1, M2, M3, M4) are the running moments.
    source: ADR-0190"""
    n = 0
    m1 = 0.0
    m2 = 0.0
    m3 = 0.0
    m4 = 0.0

    for x in values:
        n1 = n
        n += 1
        delta = x - m1
        delta_n = delta / n
        delta_n2 = delta_n * delta_n
        term1 = delta * delta_n * n1  # (x - m1_old) * delta_n * (n-1)

        # Fourth moment must be updated before M3 and M2 (depends on old M2, M3).
        m4 += (
            term1 * delta_n2 * (n * n - 3 * n + 3)
            + 6.0 * delta_n2 * m2
            - 4.0 * delta_n * m3
        )
        # Third moment depends on old M2, must precede M2 update.
        m3 += term1 * delta_n * (n - 2) - 3.0 * delta_n * m2
        m2 += term1
        m1 += delta_n

    if n == 0:
        return 0.0, 0.0, 0.0, 0.0

    variance = m2 / max(n - 1, 1)
    std = math.sqrt(variance)

    if std > _STD_EPSILON:
        skew = m3 / (n * std**3)
        kurtosis = m4 / (n * std**4) - 3.0
    else:
        skew = 0.0
        kurtosis = 0.0

    return m1, std, skew, kurtosis


def _compute_health_score(
    deviation: float,
    bimodality: float,
    skew: float,
    std: float,
) -> float:
    """Compute overall health score from distribution statistics.

    Health = 1.0 (perfectly healthy) to 0.0 (needs intervention).
    Penalizes: high deviation, high bimodality, extreme skew, low variance.

    Args:
        deviation: Absolute deviation from target mean.
        bimodality: Bimodality coefficient.
        skew: Distribution skewness.
        std: Standard deviation.

    Returns:
        Health score clamped to [0, 1].
    """
    health = 1.0
    health -= min(deviation * 2.0, 0.4)
    health -= min(max(bimodality - 0.4, 0) * 1.5, 0.3)
    health -= min(abs(skew) * 0.15, 0.2)
    if std < _LOW_STD_THRESHOLD:
        health -= 0.1
    return max(0.0, min(1.0, health))


_EMPTY_HEALTH = {
    "mean": 0.0,
    "std": 0.0,
    "skew": 0.0,
    "kurtosis_excess": 0.0,
    "deviation_from_target": 1.0,
    "bimodality_coefficient": 0.0,
    "health_score": 0.0,
}


def compute_distribution_health(
    values: list[float],
    target_mean: float,
) -> dict[str, float]:
    """Compute health metrics for a distribution of values (heats, weights, etc.).

    Returns metrics that indicate whether homeostatic mechanisms are needed.

    Args:
        values: List of values (e.g., heats).
        target_mean: Desired mean value.

    Returns:
        Dict with: mean, std, skew, kurtosis_excess, deviation_from_target,
        bimodality_coefficient, health_score (0=unhealthy, 1=healthy).
    """
    if not values:
        return dict(_EMPTY_HEALTH)

    mean, std, skew, kurtosis = _compute_moments(values)
    return _health_from_moments(mean, std, skew, kurtosis, target_mean)


def _health_from_moments(
    mean: float,
    std: float,
    skew: float,
    kurtosis: float,
    target_mean: float,
) -> dict[str, float]:
    """Build the health dict from pre-computed moments. Shared by the
    list-based and streaming paths."""
    bimodality = (skew**2 + 1) / max(kurtosis + 3, 0.01)
    deviation = abs(mean - target_mean)
    health = _compute_health_score(deviation, bimodality, skew, std)

    return {
        "mean": round(mean, 4),
        "std": round(std, 4),
        "skew": round(skew, 4),
        "kurtosis_excess": round(kurtosis, 4),
        "deviation_from_target": round(deviation, 4),
        "bimodality_coefficient": round(bimodality, 4),
        "health_score": round(health, 4),
    }


def compute_distribution_health_streaming(
    value_chunks,
    target_mean: float,
) -> tuple[dict[str, float], int]:
    """Streaming moments over chunks of values — never fully materializes.

    source: ADR-0190

    Args:
        value_chunks: iterable yielding lists of floats.
        target_mean: Desired mean value.

    Returns:
        (health_dict, total_count). Returns the empty-health dict with
        count=0 when every chunk is empty.

    source: ADR-0190"""
    # Running aggregated moments (Pébay §3.1 notation).
    n, m1, m2, m3, m4 = 0, 0.0, 0.0, 0.0, 0.0

    for chunk in value_chunks:
        if not chunk:
            continue
        n, m1, m2, m3, m4 = _merge_chunk_moments(n, m1, m2, m3, m4, chunk)

    if n == 0:
        return dict(_EMPTY_HEALTH), 0
    return _moments_to_health(n, m1, m2, m3, m4, target_mean), n


def _merge_chunk_moments(
    n: int,
    m1: float,
    m2: float,
    m3: float,
    m4: float,
    chunk: list[float],
) -> tuple[int, float, float, float, float]:
    """Fold one chunk's raw moments into the running (n, M1, M2, M3, M4).

    source: ADR-0190"""
    n_b, m1_b, m2_b, m3_b, m4_b = _chunk_raw_moments(chunk)
    if n_b == 0:
        return n, m1, m2, m3, m4
    if n == 0:
        return n_b, m1_b, m2_b, m3_b, m4_b

    # Pairwise combine running (a) and chunk (b) moments.
    n_ab = n + n_b
    delta = m1_b - m1
    delta_n = delta / n_ab
    delta_n2 = delta_n * delta_n
    na_nb = n * n_b
    # source: ADR-0190

    m4_new = (
        m4
        + m4_b
        + delta * delta_n * delta_n2 * na_nb * (n * n - na_nb + n_b * n_b)
        + 6 * delta_n2 * (n * n * m2_b + n_b * n_b * m2)
        + 4 * delta_n * (n * m3_b - n_b * m3)
    )
    m3_new = (
        m3
        + m3_b
        + delta * delta_n2 * na_nb * (n - n_b)
        + 3 * delta_n * (n * m2_b - n_b * m2)
    )
    m2_new = m2 + m2_b + delta * delta_n * na_nb
    m1_new = m1 + delta_n * n_b
    return n_ab, m1_new, m2_new, m3_new, m4_new


def _moments_to_health(
    n: int,
    m1: float,
    m2: float,
    m3: float,
    m4: float,
    target_mean: float,
) -> dict[str, float]:
    """Convert raw running moments to the health dict (shared tail of the
    streaming reducers — list-based and per-class)."""
    variance = m2 / max(n - 1, 1)
    std = math.sqrt(variance)
    if std > _STD_EPSILON:
        skew = m3 / (n * std**3)
        kurtosis = m4 / (n * std**4) - 3.0
    else:
        skew = 0.0
        kurtosis = 0.0
    return _health_from_moments(m1, std, skew, kurtosis, target_mean)


def compute_distribution_health_streaming_by_class(
    class_chunks,
    target_mean: float,
    classes: tuple[str, ...],
) -> dict[str, tuple[dict[str, float], int]]:
    """Per-write-class streaming moments — M-D3 full stratification.

    source: ADR-0190

    Args:
        class_chunks: Iterable of dict[class_name, list[float]] buckets
            per database chunk; absent buckets are omitted.
        target_mean: Shared homeostatic target (0.4).
        classes: Full class set; classes with no observations return
            empty-health dictionaries and zero counts.
    source: ADR-0190

    Returns:
        ``{class_name: (health_dict, count)}`` for every class in
        ``classes``.
    """
    running: dict[str, tuple[int, float, float, float, float]] = {
        c: (0, 0.0, 0.0, 0.0, 0.0) for c in classes
    }
    for chunk in class_chunks:
        for cls, values in chunk.items():
            if cls not in running or not values:
                continue
            running[cls] = _merge_chunk_moments(*running[cls], values)

    result: dict[str, tuple[dict[str, float], int]] = {}
    for cls, (n, m1, m2, m3, m4) in running.items():
        if n == 0:
            result[cls] = (dict(_EMPTY_HEALTH), 0)
        else:
            result[cls] = (_moments_to_health(n, m1, m2, m3, m4, target_mean), n)
    return result


def _chunk_raw_moments(
    values: list[float],
) -> tuple[int, float, float, float, float]:
    """Raw (n, M1, M2, M3, M4) for a single chunk — inputs to the pairwise
    merge formulas in ``compute_distribution_health_streaming``.

    source: ADR-0190"""
    n = 0
    m1 = 0.0
    m2 = 0.0
    m3 = 0.0
    m4 = 0.0
    for x in values:
        n1 = n
        n += 1
        delta = x - m1
        delta_n = delta / n
        delta_n2 = delta_n * delta_n
        term1 = delta * delta_n * n1
        m4 += (
            term1 * delta_n2 * (n * n - 3 * n + 3)
            + 6.0 * delta_n2 * m2
            - 4.0 * delta_n * m3
        )
        m3 += term1 * delta_n * (n - 2) - 3.0 * delta_n * m2
        m2 += term1
        m1 += delta_n
    return n, m1, m2, m3, m4
