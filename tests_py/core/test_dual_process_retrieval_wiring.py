"""Integration test for C2 dual-process (familiarity-triage) wiring.

Verifies the ``familiarity_triage`` stage (mcp_server/core/recall_pipeline.py)
as it is invoked from pg_recall.recall()'s early triage step:
  - the stage annotates each candidate with a per-candidate ``familiarity``
    computed from real query↔candidate cosine similarity (bulk embedding read);
  - an overwhelming, single-dominant familiarity hit with allow_shortcut=True
    licenses a recollection short-circuit;
  - the default (allow_shortcut=False) never short-circuits and preserves order
    and membership — parity with a no-triage run;
  - CORTEX_ABLATE_DUAL_PROCESS=1 disables the stage (identity, no annotation);
  - the stage is non-fatal on a store without embeddings.

No Postgres — a fake store returns float32 embedding blobs from a dict.
"""

from __future__ import annotations

import os
import struct

import pytest

from mcp_server.core import dual_process_retrieval as dpr
from mcp_server.core.recall_pipeline import familiarity_triage


def _blob(vec):
    """Pack a float vector as the little-endian float32 bytes pgvector stores."""
    return struct.pack(f"<{len(vec)}f", *vec)


class _FakeStore:
    """Minimal store exposing the bulk embedding read the triage uses."""

    def __init__(self, emb_by_id):
        self._emb = {mid: _blob(v) for mid, v in emb_by_id.items()}

    def get_embeddings_for_memories(self, ids):
        return {mid: self._emb[mid] for mid in ids if mid in self._emb}


def _cand(mid, score, text="m"):
    return {"memory_id": mid, "score": score, "content": text}


# ── Annotation + similarity read ──────────────────────────────────────────────
def test_triage_annotates_familiarity_from_real_cosine():
    # q == candidate 1's vector → cosine 1.0; candidate 2 orthogonal → 0.0.
    q = _blob([1.0, 0.0, 0.0])
    store = _FakeStore({1: [1.0, 0.0, 0.0], 2: [0.0, 1.0, 0.0]})
    cands = [_cand(1, 0.9), _cand(2, 0.8)]
    res = familiarity_triage(cands, q, store)
    fam = {c["memory_id"]: c["familiarity"] for c in res.candidates}
    assert fam[1] == pytest.approx(1.0, abs=1e-5)
    assert fam[2] == pytest.approx(0.0, abs=1e-5)
    # Order & membership untouched.
    assert [c["memory_id"] for c in res.candidates] == [1, 2]


# ── High-familiarity short-circuit (opt-in) ───────────────────────────────────
def test_overwhelming_hit_shortcuts_when_opted_in():
    q = _blob([1.0, 0.0, 0.0])
    store = _FakeStore({1: [1.0, 0.0, 0.0], 2: [0.0, 1.0, 0.0]})
    cands = [_cand(1, 0.9), _cand(2, 0.8)]
    res = familiarity_triage(cands, q, store, allow_shortcut=True)
    assert res.recollection_needed is False
    assert res.shortcut is True


def test_overwhelming_hit_default_does_not_shortcut():
    q = _blob([1.0, 0.0, 0.0])
    store = _FakeStore({1: [1.0, 0.0, 0.0], 2: [0.0, 1.0, 0.0]})
    cands = [_cand(1, 0.9), _cand(2, 0.8)]
    res = familiarity_triage(cands, q, store)  # default allow_shortcut=False
    assert res.recollection_needed is False  # familiarity IS sufficient
    assert res.shortcut is False  # but default path never skips recollection


def test_ambiguous_high_similarity_needs_recollection():
    # Two near-identical vectors → both high similarity, no clear winner.
    q = _blob([1.0, 0.02, 0.0])
    store = _FakeStore({1: [1.0, 0.0, 0.0], 2: [1.0, 0.05, 0.0]})
    cands = [_cand(1, 0.9), _cand(2, 0.88)]
    res = familiarity_triage(cands, q, store, allow_shortcut=True)
    assert res.recollection_needed is True
    assert res.shortcut is False


# ── Ablation guard ────────────────────────────────────────────────────────────
def test_ablation_disables_triage():
    q = _blob([1.0, 0.0, 0.0])
    store = _FakeStore({1: [1.0, 0.0, 0.0], 2: [0.0, 1.0, 0.0]})
    cands = [_cand(1, 0.9), _cand(2, 0.8)]
    os.environ["CORTEX_ABLATE_DUAL_PROCESS"] = "1"
    try:
        res = familiarity_triage(cands, q, store, allow_shortcut=True)
    finally:
        del os.environ["CORTEX_ABLATE_DUAL_PROCESS"]
    # Identity: no annotation, full recollection runs, no shortcut.
    assert all("familiarity" not in c for c in res.candidates)
    assert res.recollection_needed is True
    assert res.shortcut is False


# ── Non-fatal / no-embedding fallbacks ────────────────────────────────────────
def test_no_query_embedding_is_identity():
    store = _FakeStore({1: [1.0, 0.0, 0.0]})
    cands = [_cand(1, 0.9)]
    res = familiarity_triage(cands, None, store, allow_shortcut=True)
    assert res.candidates is cands  # untouched
    assert res.recollection_needed is True
    assert res.shortcut is False


def test_store_without_embeddings_is_identity():
    q = _blob([1.0, 0.0, 0.0])
    store = _FakeStore({})  # returns {} for any ids
    cands = [_cand(1, 0.9), _cand(2, 0.8)]
    res = familiarity_triage(cands, q, store, allow_shortcut=True)
    assert res.signal.method == dpr.METHOD_EMPTY
    assert res.recollection_needed is True
    assert res.shortcut is False


def test_empty_candidates_is_identity():
    q = _blob([1.0, 0.0, 0.0])
    store = _FakeStore({1: [1.0, 0.0, 0.0]})
    res = familiarity_triage([], q, store, allow_shortcut=True)
    assert res.candidates == []
    assert res.shortcut is False


# ── Result-parity: annotation aside, membership/order match no-triage ──────────
def test_default_triage_parity_membership_and_order():
    q = _blob([0.6, 0.4, 0.0])
    store = _FakeStore({1: [1.0, 0.0, 0.0], 2: [0.0, 1.0, 0.0], 3: [0.5, 0.5, 0.0]})
    cands = [_cand(1, 0.9), _cand(2, 0.7), _cand(3, 0.5)]
    before_ids = [c["memory_id"] for c in cands]
    before_scores = [c["score"] for c in cands]
    res = familiarity_triage(cands, q, store)  # default: no shortcut
    after_ids = [c["memory_id"] for c in res.candidates]
    after_scores = [c["score"] for c in res.candidates]
    assert after_ids == before_ids  # same membership, same order
    assert after_scores == before_scores  # scores untouched (annotation only)
    assert all("familiarity" in c for c in res.candidates)
