"""Tests for the deterministic algorithmic embedder (issue #169).

Contract assertions (each must fail on regression):
  - Output dimension equals the requested dim (space contract)
  - Deterministic: same (text, dim) → byte-identical vector
  - L2-normalized for non-empty text; zero vector for empty
  - Semantic ordering: a topically-matching text out-scores an unrelated one
  - camelCase identifiers bridge to their split words (shared tokenizer)
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np

import mcp_server.shared.algorithmic_embedding as ae
from mcp_server.shared.algorithmic_embedding import _MAX_OCCUR, embed_text, index_vector


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # both already L2-normalized


def test_dimension_contract():
    for dim in (128, 384, 768):
        assert embed_text("some memory text", dim).shape == (dim,)


def test_determinism():
    a = embed_text("normalizePaymentAmount rounds the charge", 384)
    b = embed_text("normalizePaymentAmount rounds the charge", 384)
    assert np.array_equal(a, b)


def test_normalized_nonempty():
    v = embed_text("a decision about the checkout transaction boundary", 384)
    assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-5


def test_empty_is_zero_vector():
    v = embed_text("", 384)
    assert float(np.linalg.norm(v)) == 0.0
    assert v.dtype == np.float32  # empty path keeps the float32 output contract


def test_output_is_float32():
    v = embed_text("a decision about the checkout transaction boundary", 384)
    assert v.dtype == np.float32


def test_index_vector_is_sparse_ternary():
    v = index_vector("payment", 384)
    nz = v[v != 0]
    assert len(nz) <= 8  # source: CBM_SEM_SPARSE_NNZE=8
    assert set(np.unique(nz)).issubset({-1.0, 1.0})


def test_semantic_ordering():
    q = embed_text("how to normalize a payment amount", 384)
    related = embed_text("payment normalization converts the amount to cents", 384)
    unrelated = embed_text("the weather in Paris was cold and rainy", 384)
    assert _cos(q, related) > _cos(q, unrelated)


def test_camelcase_bridges_to_words():
    q = embed_text("payment amount", 384)
    camel = embed_text("normalizePaymentAmount", 384)
    unrelated = embed_text("mountain hiking trip", 384)
    assert _cos(q, camel) > _cos(q, unrelated)


# ── Frequent-token subsampling branch (issue #184) ────────────────────────
# CBM semantics: the co-occurrence pass is strided only for a token whose
# within-document occurrence count exceeds _MAX_OCCUR; first-order terms are
# always complete. These tests exercise the stride branch (never touched by the
# original 7 tests, every input of which was far under the cap) and pin the
# per-token trigger + co-occurrence-only scope against regression.


def _count_window_calls(text: str, dim: int = 384) -> tuple[int, np.ndarray]:
    """Return (co-occurrence window invocations, embedding). One invocation per
    visited occurrence position — so it counts exactly the co-occurrence work
    the subsampling branch bounds."""
    calls = {"n": 0}
    real = ae._accumulate_window

    def _spy(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    with patch.object(ae, "_accumulate_window", _spy):
        vec = ae.embed_text(text, dim)
    return calls["n"], vec


def test_normal_memory_takes_no_subsampling():
    # §13 G4 negative assertion: a normal-length memory must NOT be strided —
    # every token occurrence contributes a co-occurrence window (step == 1).
    text = "a decision about the checkout transaction boundary and its retries"
    n_tokens = len(ae._tokenize(text))
    calls, vec = _count_window_calls(text)
    assert calls == n_tokens  # one window per occurrence: no subsampling
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-5


def test_boundary_at_exactly_max_occur_does_not_stride():
    # A token occurring EXACTLY _MAX_OCCUR times is at the cap, not above it:
    # step = max(1, _MAX_OCCUR // _MAX_OCCUR) = 1 → no striding.
    text = "spam " * _MAX_OCCUR
    calls, _ = _count_window_calls(text)
    assert calls == _MAX_OCCUR  # every occurrence still visited


def test_frequent_token_triggers_subsampling_and_bounds_work():
    # A token occurring well above the cap has its co-occurrence pass strided to
    # ~_MAX_OCCUR samples: bounded work, and far fewer than the raw occurrences.
    n_occ = 2 * _MAX_OCCUR + 1
    text = "spam " * n_occ
    calls, _ = _count_window_calls(text)
    assert calls < n_occ  # striding actually fired
    assert calls <= _MAX_OCCUR + 1  # bounded to ~the cap


def test_subsampling_preserves_direction_within_tolerance():
    # CBM's rationale: an evenly-spaced subsample preserves the enriched
    # vector's DIRECTION (it is L2-normalized after). Compare a triggering
    # document against the same document with subsampling disabled.
    text = "spam " * (2 * _MAX_OCCUR + 1)
    strided = ae.embed_text(text, 384)
    with patch.object(ae, "_MAX_OCCUR", 10**9):  # disable striding
        full = ae.embed_text(text, 384)
    assert _cos(strided, full) > 0.99


def test_first_order_terms_are_never_subsampled():
    # A document of DISTINCT tokens far exceeding _MAX_OCCUR positions: no single
    # token repeats, so nothing is strided and every first-order term survives.
    # (The shipped document-length striding this replaces would have dropped
    # half of them — issue #184.)
    # Distinct 4-letter alphabetic words (no digits → the identifier splitter
    # keeps each whole and none share form), well past _MAX_OCCUR positions.
    def _word(i: int) -> str:
        return "".join(chr(ord("a") + (i // 26**k) % 26) for k in range(4))

    words = [_word(i) for i in range(2 * _MAX_OCCUR)]
    assert len(set(words)) == len(words)  # genuinely distinct
    text = " ".join(words)
    n_tokens = len(ae._tokenize(text))
    calls, vec = _count_window_calls(text)
    assert calls == n_tokens  # no striding despite > _MAX_OCCUR positions
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-5


# ── Co-occurrence window + first-order contract (direct unit tests) ────────
# The window bounds, distance weighting, and accumulation are numeric and were
# not pinned by the coarse semantic-ordering tests. These call the passes with
# a one-hot cache (each token → its own basis vector) so the accumulator can be
# read off exactly, killing the arithmetic mutants in the co-occurrence path.


def _onehot_cache(tokens: list[str]) -> dict[str, np.ndarray]:
    distinct = list(dict.fromkeys(tokens))
    dim = len(distinct)
    return {t: np.eye(dim, dtype=np.float32)[k] for k, t in enumerate(distinct)}


def test_accumulate_window_distance_weighting_and_accumulation():
    # center at index 2; neighbours at distances 2 (left edge), 1, 1.
    tokens = ["n2", "n1", "c", "f1"]
    cache = _onehot_cache(tokens)
    acc = np.zeros(len(cache), dtype=np.float32)
    ae._accumulate_window(acc, tokens, cache, center=2, weight=1.0)
    # 1/2 from n2, 1 from n1, 0 (center excluded), 1 from f1.
    assert np.allclose(acc, [0.5, 1.0, 0.0, 1.0])


def test_accumulate_window_respects_window_bounds():
    # 13 distinct tokens, center at 6; _WINDOW=5 → only |j-6| in 1..5 contribute.
    tokens = [f"w{i:02d}" for i in range(13)]
    cache = _onehot_cache(tokens)
    acc = np.zeros(len(cache), dtype=np.float32)
    ae._accumulate_window(acc, tokens, cache, center=6, weight=1.0)
    expected = np.zeros(13, dtype=np.float32)
    for j in range(13):
        if 1 <= abs(j - 6) <= ae._WINDOW:
            expected[j] = 1.0 / abs(j - 6)
    assert np.allclose(acc, expected)
    assert acc[0] == 0.0 and acc[12] == 0.0  # beyond the window, excluded


def test_first_order_pass_sums_every_occurrence_weighted():
    # "a" occurs twice, "b" once; each occurrence adds its tf-weighted vector.
    tokens = ["a", "b", "a"]
    tf = {"a": 1.0 + np.log(2), "b": 1.0}
    cache = _onehot_cache(tokens)  # a → [1,0], b → [0,1]
    acc = np.zeros(2, dtype=np.float32)
    ae._first_order_pass(acc, tokens, tf, cache)
    assert np.allclose(acc, [2.0 * tf["a"], tf["b"]])


# Documented-equivalent / out-of-scope surviving mutants (mutmut, §12), so a
# reviewer re-running the scoped run knows they are accounted for, not missed:
#   * embed_text `dtype=None` on the INTERNAL accumulator (not the empty-return
#     path, which test_empty_is_zero_vector now pins): the final
#     `acc.astype(np.float32)` fixes the output dtype, so a float64 internal
#     accumulator is observably identical to float32 tolerance — equivalent.
#   * `norm > 0.0` → `>= 0.0` / `> 1.0`: the pre-normalization norm of any
#     NON-EMPTY ternary-sum embedding is ≥ 1 (integer-valued index vectors),
#     and the empty case returns early, so all three predicates normalize the
#     same reachable inputs — equivalent in practice.
#   * Survivors in index_vector / _token_seed / _tf_weights / _tokenize predate
#     issue #184 (unchanged functions; not the stride branch this issue scopes)
#     and are out of scope for this fix.
