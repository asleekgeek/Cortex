"""Tolerance-based equivalence for float32 embedding/scoring comparisons.

Replaces bitwise-exact ("delta == 0") identity as the acceptance gate for
perf changes that reorder floating-point work (e.g. batching N scalar
encoder calls into one batched call). That gate is unsatisfiable by
construction: IEEE 754 float addition/multiplication is not associative,
so a batched matmul reduces in a different element order than N independent
scalar calls and will not, in general, reproduce the same bit pattern —
not because the batched result is wrong, but because both results are
independently-rounded approximations of the same real-valued computation.

Source: cdeust/Cortex PR #495 ("perf(remember): reuse embeddings for
identical merge text") and PR #497 ("perf(embeddings): batch codebase
imports and preserve cache contexts"), both measured 2026-09-07 on the
pinned sentence-transformers/all-MiniLM-L6-v2 CPU float32 encoder
(revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41). Both PRs declined a
measured batching speedup (PR #495: 7 encoder calls -> 2, CPU 18.112ms ->
10.507ms median) under an exact-identity gate, and recorded the deltas
that failed it:
  PR #495 vector delta: 1.6391277313232422e-07  (~1.375 ULP)
  PR #495 score  delta: 1.1920928955078125e-07  (exactly 1 float32 ULP)
  PR #497 vector delta: 1.0617077350616455e-07  (~0.89 ULP)
  PR #497 lessons delta: 9.313225746154785e-08   (~0.78 ULP)
  PR #497 compression delta: 1.3969838619232178e-07 (~1.17 ULP)
FLOAT32_ULP (2**-23, the spacing between adjacent float32 values near 1.0)
is 1.1920928955078125e-07 — every one of the above deltas is within 2 ULP
of it. That is the signature of independent rounding, not a computational
error: a real defect would not track machine epsilon this tightly across
five unrelated code paths.

DEFAULT_MAX_ULP=4 gives roughly 3x headroom over the largest observed
delta (~1.4 ULP) — provisional heuristic, not a derived bound; widen only
with a new measured counter-example, and cite it here.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

# source: IEEE 754 binary32, machine epsilon = 2**-23 (spacing between
# adjacent representable values in [1.0, 2.0)) — the sentence-transformers
# CPU encoder path measured above runs in float32.
FLOAT32_ULP = 2.0**-23

# source: see module docstring — largest observed delta across PR #495/#497
# was ~1.4 ULP; this multiplier is a provisional heuristic leaving ~3x
# headroom, not a derived statistical bound.
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

    This is the criterion that actually matters for a write-gate decision
    or a retrieval ranking: a score shift small enough to be numerical
    noise must not flip which candidate wins UNLESS the two candidates
    were already tied to within tolerance, in which case either order was
    already an acceptable outcome. Pre: len(scores_before) ==
    len(scores_after), same candidate at the same index in both.
    """
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
