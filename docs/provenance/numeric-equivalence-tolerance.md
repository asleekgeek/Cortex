# Numeric equivalence tolerance for perf changes (retracts the exact-identity gate)

## Retraction

`docs/provenance/green-w3-2-encoding-identity.md` (PR #495) recorded: "The
requested contract is exact score identity, not a numeric tolerance" and
"No tolerance has been adopted." That decision is retracted here. It was
evaluated against the wrong predicate, not against insufficient evidence.

## Why the exact-identity gate was wrong

IEEE 754 float32 addition and multiplication are not associative. A batched
matmul (one call, N rows reduced together) does not sum its terms in the
same order as N independent scalar calls, so it will not, in general,
reproduce the same bit pattern as the scalar path — this is true even when
both computations are numerically correct, because both are independently-
rounded approximations of the same real-valued result. An acceptance gate
specified as exact bitwise equality between a scalar and a batched path is
therefore not a test of "is batching safe" — structurally, no batched
implementation can ever pass it, regardless of correctness. It will reject
every future attempt at this optimization, for the same reason, forever.

**Evidence that this is what actually happened, not a coincidence:**
`FLOAT32_ULP = 2**-23 = 1.1920928955078125e-07` (float32 machine epsilon).
Every delta recorded as a rejection in PR #495 and PR #497 is within ~1.4x
of exactly this number:

| Source | Recorded delta | In float32 ULP |
|---|---:|---:|
| PR #495 normalized-vector delta | 1.6391277313232422e-07 | ~1.375 |
| PR #495 score delta | 1.1920928955078125e-07 | **exactly 1.000** |
| PR #497 vector delta | 1.0617077350616455e-07 | ~0.891 |
| PR #497 lessons delta | 9.313225746154785e-08 | ~0.781 |
| PR #497 compression delta | 1.3969838619232178e-07 | ~1.172 |

A genuine computational defect does not track machine epsilon this tightly
across five unrelated code paths measured on two different PRs. This is
the signature of independent rounding order, not a bug — the score delta
in PR #495 is not merely *close to* one ULP, it equals one ULP to every
digit reported.

## The replacement gate

Two conditions, both implemented in `benchmarks/lib/numeric_equivalence.py`
(with unit tests in `tests_py/benchmarks/test_numeric_equivalence.py`
reproducing the exact deltas in the table above):

1. **`vectors_equivalent(a, b, max_ulp=4)`** — every paired component of
   the scalar-path and batched-path vectors must be within `max_ulp`
   float32 ULPs of each other. `DEFAULT_MAX_ULP=4` gives ~3x headroom over
   the largest observed delta (~1.4 ULP); it is a provisional heuristic,
   not a derived bound — widen it only against a new measured
   counter-example, cited the same way this document cites its own.
2. **`rank_stable(scores_before, scores_after, max_ulp=4)`** — the more
   meaningful criterion for a write-gate decision or a retrieval ranking.
   A score shift of a few ULP must not change which candidate wins UNLESS
   the two candidates were already tied to within tolerance under the
   scalar path — in which case either order was already an acceptable
   outcome before the optimization existed. This is stricter than "the
   final ranked list is unchanged" would be misleading to require: it is
   exactly as strict as the scalar path's own output already was.

Neither condition is a general "close enough" fudge: both are sized to the
one physical quantity that actually bounds float32 rounding order noise
(1 ULP), sourced to the two PRs' own measurements, not chosen to make a
particular result pass.

## What this means for PR #495 / #497

The batching this policy retracted (PR #495 commit `60e5646b`, "batch
normalized neighbors and reuse unchanged merge vectors"; PR #497's shared
scalar/batch cache context) measured real gains under the old gate before
being reverted for failing it:

- PR #495: CPU median 18.112ms -> 10.507ms (seven encoder calls -> two).
- PR #497: CPU median 342.974ms -> 180.310ms, wall 277.694ms -> 103.447ms
  (64 scalar calls -> 1 batched call), on the codebase-import path.

Applying `vectors_equivalent`/`rank_stable` (see the test file) to the
already-recorded deltas above, both would now pass. That is not, by
itself, a decision to merge the reverted batching back in: it substitutes
the correct predicate for the wrong one on data already collected, but a
maintainer with the real pinned MiniLM encoder available should re-run
each PR's own harness (`docs/provenance/green-w3-2-encoding-identity.md`'s
`/private/tmp/cortex-green-w3-2-neural-final-measure.py` for #495;
`docs/provenance/bulk-embedding-boundaries.md` for #497) against this
gate before restoring either batched code path, rather than trusting a
transcription of numbers already in a closed PR body. This session had no
`torch`/`sentence-transformers` available to re-run either harness itself.
