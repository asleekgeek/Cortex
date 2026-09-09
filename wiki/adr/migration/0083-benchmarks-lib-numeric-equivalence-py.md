# ADR-0083: benchmarks/lib/numeric_equivalence.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/numeric_equivalence.py`; original SHA-256 `c6a62e20063b07d0e561974cc478bec3760fb8d71f6ac94dd5520be01bf003d3`.

## Original docstring, lines 1–34

````text
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
````

## Original comment, lines 41–43

````text
# source: IEEE 754 binary32, machine epsilon = 2**-23 (spacing between
# adjacent representable values in [1.0, 2.0)) — the sentence-transformers
# CPU encoder path measured above runs in float32.
````

## Original comment, lines 46–48

````text
# source: see module docstring — largest observed delta across PR #495/#497
# was ~1.4 ULP; this multiplier is a provisional heuristic leaving ~3x
# headroom, not a derived statistical bound.
````

## Original docstring, lines 85–94

````text
"""True if reordering by scores_after never separates two items that
    were NOT already within tolerance under scores_before.

    This is the criterion that actually matters for a write-gate decision
    or a retrieval ranking: a score shift small enough to be numerical
    noise must not flip which candidate wins UNLESS the two candidates
    were already tied to within tolerance, in which case either order was
    already an acceptable outcome. Pre: len(scores_before) ==
    len(scores_after), same candidate at the same index in both.
    """
````

