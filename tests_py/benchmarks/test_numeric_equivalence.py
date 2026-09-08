"""benchmarks.lib.numeric_equivalence — ULP-tolerance + rank-stability gate.

Contract under test: the tolerance-based equivalence check that replaces
bitwise-exact identity for validating perf changes that reorder float32
work (see the module docstring for the PR #495/#497 provenance). Uses the
exact deltas those PRs measured and rejected, to confirm they now pass.
"""

from __future__ import annotations

from benchmarks.lib.numeric_equivalence import (
    FLOAT32_ULP,
    rank_stable,
    scalars_equivalent,
    ulp_delta,
    vectors_equivalent,
)

# source: PR #495 body, measured 2026-09-07, sentence-transformers/
# all-MiniLM-L6-v2 rev 1110a243, CPU float32.
PR_495_VECTOR_DELTA = 1.6391277313232422e-07
# source: PR #495 body, same measurement conditions as above.
PR_495_SCORE_DELTA = 1.1920928955078125e-07

# source: PR #497 body, same measurement conditions.
PR_497_VECTOR_DELTA = 1.0617077350616455e-07
# source: PR #497 body, same measurement conditions.
PR_497_LESSONS_DELTA = 9.313225746154785e-08
# source: PR #497 body, same measurement conditions.
PR_497_COMPRESSION_DELTA = 1.3969838619232178e-07


class TestUlpDelta:
    def test_identical_values_are_zero_ulp(self):
        assert ulp_delta(0.7978, 0.7978) == 0.0

    def test_one_float32_ulp_reports_one(self):
        assert ulp_delta(1.0 + FLOAT32_ULP, 1.0) == 1.0

    def test_measured_pr495_score_delta_is_one_ulp(self):
        assert ulp_delta(0.8010, 0.8010 + PR_495_SCORE_DELTA) == 1.0


class TestScalarsEquivalent:
    def test_exact_match(self):
        assert scalars_equivalent(0.914, 0.914)

    def test_pr495_score_delta_within_default_tolerance(self):
        assert scalars_equivalent(0.8010, 0.8010 + PR_495_SCORE_DELTA)

    def test_pr497_deltas_within_default_tolerance(self):
        base = 0.75
        assert scalars_equivalent(base, base + PR_497_VECTOR_DELTA)
        assert scalars_equivalent(base, base + PR_497_LESSONS_DELTA)
        assert scalars_equivalent(base, base + PR_497_COMPRESSION_DELTA)

    def test_a_real_regression_is_still_rejected(self):
        # 0.01 is four orders of magnitude larger than every measured
        # rounding delta above — not noise, a real behavior change.
        assert not scalars_equivalent(0.80, 0.81)


class TestVectorsEquivalent:
    def test_measured_pr495_vector_delta_passes(self):
        a = [0.1, 0.2, 0.3]
        b = [0.1 + PR_495_VECTOR_DELTA, 0.2, 0.3 - PR_495_VECTOR_DELTA]
        assert vectors_equivalent(a, b)

    def test_length_mismatch_fails(self):
        assert not vectors_equivalent([0.1, 0.2], [0.1])

    def test_large_divergence_fails(self):
        assert not vectors_equivalent([0.1, 0.2], [0.1, 0.9])


class TestRankStable:
    def test_identical_order_is_stable(self):
        assert rank_stable([0.9, 0.5, 0.1], [0.9, 0.5, 0.1])

    def test_ulp_noise_swap_among_already_tied_candidates_is_stable(self):
        # Two candidates tied to 7 decimals pre-optimization; the
        # post-optimization run breaks the tie the other way. That is
        # exactly the "already tied" case the docstring describes as an
        # acceptable outcome either way.
        before = [0.9, 0.5000000, 0.5000000]
        after = [0.9, 0.5000000 - PR_495_SCORE_DELTA, 0.5000000 + PR_495_SCORE_DELTA]
        assert rank_stable(before, after)

    def test_a_real_reordering_of_distinct_candidates_is_not_stable(self):
        before = [0.9, 0.5, 0.1]
        after = [0.5, 0.9, 0.1]  # top two candidates actually swapped
        assert not rank_stable(before, after)

    def test_length_mismatch_fails(self):
        assert not rank_stable([0.9, 0.5], [0.9])
