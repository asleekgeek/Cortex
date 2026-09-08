"""Tolerance-based equivalence for float32 embedding/scoring comparisons.

source: ADR-0083"""

from __future__ import annotations

import math
from collections.abc import Sequence

# source: ADR-0083
FLOAT32_ULP = 2.0**-23

# source: ADR-0083
DEFAULT_MAX_ULP = 4


def ulp_delta(a: float, b: float, *, ulp: float = FLOAT32_ULP) -> float:
    """How many float32 ULPs apart a and b are (0.0 if a == b)."""
    if a == b:
        return 0.0
    return abs(a - b) / ulp


def scalars_equivalent(a: float, b: float, *, max_ulp: float = DEFAULT_MAX_ULP) -> bool:
    """True if a and b differ by no more than max_ulp float32 ULPs."""
    return ulp_delta(a, b) <= max_ulp


def vectors_equivalent(
    a: Sequence[float], b: Sequence[float], *, max_ulp: float = DEFAULT_MAX_ULP
) -> bool:
    """True if every paired component of a and b is ULP-equivalent.

    Pre: len(a) == len(b). Post: False on any length mismatch or any
    component pair exceeding max_ulp (fails fast, does not report which).
    """
    if len(a) != len(b):
        return False
    return all(
        scalars_equivalent(x, y, max_ulp=max_ulp) for x, y in zip(a, b, strict=True)
    )


def rank_stable(
    scores_before: Sequence[float],
    scores_after: Sequence[float],
    *,
    max_ulp: float = DEFAULT_MAX_ULP,
) -> bool:
    """True if reordering by scores_after never separates two items that
        were NOT already within tolerance under scores_before.

    source: ADR-0083"""
    n = len(scores_before)
    if len(scores_after) != n:
        return False
    order_before = sorted(range(n), key=lambda i: scores_before[i], reverse=True)
    order_after = sorted(range(n), key=lambda i: scores_after[i], reverse=True)
    if order_before == order_after:
        return True
    for i in range(n):
        idx_before, idx_after = order_before[i], order_after[i]
        if idx_before == idx_after:
            continue
        # A swap at this rank is acceptable only if the two candidates it
        # swapped were already within tolerance under EITHER score set —
        # i.e. the pre-optimization ranking already treated them as tied.
        if not (
            scalars_equivalent(
                scores_before[idx_before], scores_before[idx_after], max_ulp=max_ulp
            )
            or scalars_equivalent(
                scores_after[idx_before], scores_after[idx_after], max_ulp=max_ulp
            )
        ):
            return False
    return True


def is_finite_vector(v: Sequence[float]) -> bool:
    """True if every component is finite (guards NaN/inf slipping past a
    tolerance comparison — abs(nan - x) is nan, and nan <= max_ulp is
    always False, so this is a belt-and-suspenders explicit check, not a
    silent behavior change)."""
    return all(math.isfinite(x) for x in v)
