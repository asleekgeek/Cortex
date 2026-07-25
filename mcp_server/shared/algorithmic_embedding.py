"""Deterministic, download-free algorithmic text embeddings.

The zero-model fallback for ``EmbeddingEngine``: when sentence-transformers is
unavailable (import fails, or the model weights are absent and cannot be
downloaded), this module produces a fixed-dimension dense vector for any text
with no network, no model files, and no learned parameters — only arithmetic
seeded by the token strings themselves. The same input always yields the same
vector, on any platform (all hashing is ``hashlib``-based, never Python's
salted ``hash()``).

Signal selection (adapted from the codebase-memory-mcp 11-signal embedder,
``src/semantic/semantic.{c,h}``). Cortex memories are conversational / decision
prose, not code symbol tables, so only the signals that transfer to prose are
kept:

  INCLUDED
  * Sublinear term-frequency weighting — ``1 + log(tf)`` (Manning, Raghavan &
    Schütze, *Introduction to Information Retrieval*, 2008, §6.4 "sublinear tf
    scaling"). Dampens repeated tokens without a corpus.
  * Random Indexing — each token maps to a sparse ternary index vector; the
    document vector is the tf-weighted sum. Deterministic, corpus-free, and
    projects an unbounded vocabulary into ``dim`` dimensions (Kanerva,
    Kristofersson & Holst 2000; Sahlgren, "An Introduction to Random Indexing",
    2005). Sparse ternary projections are near-orthogonal in expectation
    (Achlioptas, "Database-friendly random projections", 2003).
  * Co-occurrence bridging — each token's contribution is enriched by the index
    vectors of its neighbours within a symmetric window, distance-weighted
    ``1/d``. Two texts that use different but co-occurring vocabulary move
    closer, the synonym-bridging effect Sahlgren (2005) describes.
  * Frequent-token subsampling — a token whose within-document occurrence
    count exceeds ``_MAX_OCCUR`` has *only its co-occurrence contribution*
    stride-subsampled; its first-order term is always complete. This mirrors
    CBM's ``cooccur_sparse_one_target`` (semantic.c:874): the trigger is the
    per-token occurrence count and the scope is the co-occurrence pass alone.
    It is *inspired by* word2vec/GloVe frequent-word subsampling (Mikolov et
    al. 2013) — the motivation, dampening dominant tokens — but does NOT
    implement their ``P(discard) = 1 - sqrt(t/f(w))`` formula: that needs a
    corpus-relative frequency ``f(w)``, which this stateless per-text seam does
    not have (same reason IDF is excluded below). Inert for normal memories: a
    token must repeat >``_MAX_OCCUR`` times in ONE memory to trigger, which
    conversational prose effectively never does.

  EXCLUDED (with reason)
  * IDF — needs a persistent corpus. The ``encode(text)`` seam is stateless and
    per-text; a global IDF table would couple every call to mutable cross-call
    state and break determinism. Omitted, not faked.
  * MinHash, API/type signatures, AST profile, graph diffusion, Halstead-lite —
    all consume code structure (call graphs, type signatures, ASTs) that
    conversational memories do not carry. Not applicable to prose.

Pure utility — no I/O. Shared layer (numpy only, like ``shared.linear_algebra``
and ``shared.minhash``).
"""

from __future__ import annotations

import hashlib
import math
import struct

import numpy as np

from mcp_server.shared.code_tokenize import split_identifier

# source: CBM_SEM_SPARSE_NNZE = 8 (semantic.h:39) — non-zero entries per sparse
# random index vector. 8 keeps index vectors near-orthogonal at 256–768 dims
# (Achlioptas 2003) while staying cheap.
_NONZERO_PER_TOKEN = 8

# source: CBM_SEM_WINDOW = 5 (semantic.h:42) — co-occurrence window half-width.
_WINDOW = 5

# source: CBM_SEM_MAX_OCCUR = 512 (semantic.h:52, applied in semantic.c:874
# cooccur_sparse_one_target) — frequent-token subsampling cap. Trigger: a token
# whose within-document occurrence count exceeds this. Scope: that token's
# co-occurrence pass only (its occurrence positions are strided to ~this count);
# the first-order term is untouched. Direction is preserved by the final L2
# normalize. Verified equal-or-better to no-subsampling on LongMemEval-S:
# source: benchmark benchmarks/results/subsample-fidelity-184/MANIFEST.md.
_MAX_OCCUR = 512


def _token_seed(token: str) -> int:
    """Deterministic 64-bit seed for a token (platform-independent).

    source: mirrors CBM's ``XXH3_64bits(token)`` seed (semantic.c:459); uses
    ``hashlib.blake2b`` (stdlib) so the value is stable across processes and
    platforms, unlike Python's salted ``hash()``.
    """
    return int.from_bytes(
        hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big"
    )


def index_vector(token: str, dim: int) -> np.ndarray:
    """Return the sparse ternary Random-Indexing vector for ``token``.

    precondition: ``token`` is a non-empty str; ``dim`` > 0.
    postcondition: returns a float32 array of shape ``(dim,)`` with at most
    ``_NONZERO_PER_TOKEN`` non-zero entries in {-1, +1}; deterministic in
    ``(token, dim)``.

    source: CBM ``cbm_sem_random_index`` (semantic.c:437) — for i in
    0..NONZERO: h = hash(i, seed); pos = h % dim; sign = bit(h) ? +1 : -1;
    v[pos] += sign.
    """
    vec = np.zeros(dim, dtype=np.float32)
    seed = _token_seed(token)
    for i in range(_NONZERO_PER_TOKEN):
        h = int.from_bytes(
            hashlib.blake2b(
                struct.pack("<q", i), key=struct.pack("<Q", seed), digest_size=8
            ).digest(),
            "big",
        )
        pos = h % dim
        vec[pos] += 1.0 if (h & 1) else -1.0
    return vec


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase sub-tokens (same rule as the FTS tokenizer).

    postcondition: identifiers are decomposed (``normalizePaymentAmount`` →
    ``normalize, payment, amount``) so the embedding vocabulary and the FTS
    vocabulary agree; ordering is preserved for the co-occurrence window.
    """
    tokens: list[str] = []
    for word in text.replace("\n", " ").split():
        tokens.extend(split_identifier(word))
    return tokens


def _tf_weights(tokens: list[str]) -> dict[str, float]:
    """Sublinear term-frequency weight per distinct token: ``1 + log(tf)``.

    source: Manning et al. 2008 §6.4 (sublinear tf scaling).
    """
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    return {t: 1.0 + math.log(c) for t, c in counts.items()}


def _accumulate_window(
    acc: np.ndarray,
    tokens: list[str],
    cache: dict[str, np.ndarray],
    center: int,
    weight: float,
) -> None:
    """Add the distance-weighted (``1/d``) index vectors of ``center``'s
    neighbours within ``±_WINDOW`` into ``acc`` in place.

    precondition: ``acc`` is the caller's live accumulator (documented owner:
    ``embed_text``); ``0 <= center < len(tokens)``.
    postcondition: ``acc`` is incremented by ``sum_j (weight/|j-center|) *
    cache[tokens[j]]`` over the window, excluding ``j == center``.
    """
    n = len(tokens)
    lo = max(0, center - _WINDOW)
    hi = min(n, center + _WINDOW + 1)
    for j in range(lo, hi):
        if j != center:
            acc += (weight / abs(j - center)) * cache[tokens[j]]


def _first_order_pass(
    acc: np.ndarray,
    tokens: list[str],
    tf: dict[str, float],
    cache: dict[str, np.ndarray],
) -> None:
    """Add each token's tf-weighted index vector into ``acc`` in place, once per
    occurrence.

    precondition: ``acc`` is the caller's live accumulator (owner:
    ``embed_text``); ``tf`` and ``cache`` are keyed by every distinct token.
    postcondition: ``acc`` is incremented by ``sum_i tf[tokens[i]] *
    cache[tokens[i]]`` over ALL positions — never subsampled (CBM keeps a
    token's own source vector intact; semantic.c:930 sem_target_init_from_src).
    """
    for tok in tokens:
        acc += tf[tok] * cache[tok]


def _cooccurrence_pass(
    acc: np.ndarray,
    tokens: list[str],
    tf: dict[str, float],
    cache: dict[str, np.ndarray],
) -> None:
    """Add distance-weighted co-occurrence enrichment into ``acc`` in place,
    with CBM frequent-token subsampling.

    precondition: ``acc`` is the caller's live accumulator (owner:
    ``embed_text``); ``tf`` and ``cache`` are keyed by every distinct token.
    postcondition: for each distinct token, its occurrence positions contribute
    a windowed sum; a token occurring more than ``_MAX_OCCUR`` times has its
    positions strided to ~``_MAX_OCCUR`` samples (its first-order term, added by
    the caller, is untouched). source: CBM ``cooccur_sparse_one_target``
    (semantic.c:874) — per-token trigger, co-occurrence scope only.
    """
    positions: dict[str, list[int]] = {}
    for i, tok in enumerate(tokens):
        positions.setdefault(tok, []).append(i)
    for tok, occ in positions.items():
        step = max(1, len(occ) // _MAX_OCCUR)
        weight = tf[tok]
        for i in occ[::step]:
            _accumulate_window(acc, tokens, cache, i, weight)


def embed_text(text: str, dim: int) -> np.ndarray:
    """Encode ``text`` into a deterministic, L2-normalized dense vector.

    precondition: ``text`` is a str (may be empty); ``dim`` > 0.
    postcondition: returns a float32 array of shape ``(dim,)``; L2 norm is 1.0
    when ``text`` has at least one token, else the zero vector; the result is
    deterministic in ``(text, dim)`` and lies in the SAME vector-space contract
    (dimension) as the neural encoder, though NOT the same geometry — the two
    spaces are incomparable and callers must not cross-rank them.
    invariant: every token contributes exactly one complete first-order term;
    the co-occurrence pass is strided only for a token whose within-document
    occurrence count exceeds ``_MAX_OCCUR`` (CBM ``cooccur_sparse_one_target``).
    """
    tokens = _tokenize(text)
    if not tokens:
        return np.zeros(dim, dtype=np.float32)

    tf = _tf_weights(tokens)
    # Cache each distinct token's index vector once — an O(unique) not
    # O(occurrences) build.
    cache: dict[str, np.ndarray] = {t: index_vector(t, dim) for t in tf}

    acc = np.zeros(dim, dtype=np.float32)
    _first_order_pass(acc, tokens, tf, cache)
    _cooccurrence_pass(acc, tokens, tf, cache)

    norm = float(np.linalg.norm(acc))
    if norm > 0.0:
        acc /= norm
    return acc.astype(np.float32)
