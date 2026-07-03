"""Integration test for A2 conflict-monitor wiring into the recall pipeline.

Verifies the ``conflict_monitor_rerank`` stage (mcp_server/core/recall_pipeline.py)
as it is called from pg_recall.py's post-WRRF stage chain:
  - a high-conflict set demotes the losing memory and re-sorts;
  - typed-claim candidates additionally get claim_resolver ConflictPlans attached;
  - a low-conflict / consistent set passes through unchanged;
  - CORTEX_ABLATE_CONFLICT_MONITOR=1 fully disables the stage (identity);
  - the stage is non-fatal (never raises) on malformed candidates.

No Postgres required — the stage operates on plain candidate dicts.
"""

from __future__ import annotations

import os


from mcp_server.core.recall_pipeline import conflict_monitor_rerank


def _cand(mid, score, text, **extra):
    d = {"memory_id": mid, "score": score, "content": text}
    d.update(extra)
    return d


# ── High-conflict path ────────────────────────────────────────────────────────
def test_high_conflict_demotes_loser():
    cands = [
        _cand(1, 0.90, "the auth service uses jwt tokens for sessions"),
        _cand(2, 0.88, "the auth service does not use jwt tokens for sessions"),
    ]
    out = conflict_monitor_rerank(cands)
    loser = next(c for c in out if c["memory_id"] == 2)
    assert loser["score"] < 0.88
    assert loser.get("conflict_downweighted") is True
    # Winner ends up on top after re-sort.
    assert out[0]["memory_id"] == 1


def test_high_conflict_typed_claims_route_to_resolver():
    # Texts must both lexically contradict (so the scalar fires and gates the
    # route) AND carry typed-claim metadata (so the resolver has something to
    # plan over). The scalar and the typed resolver are two distinct signals;
    # the route is gated by the scalar being high, by design.
    cands = [
        _cand(
            10,
            0.90,
            "the redis cache is the chosen backing store for sessions",
            claim_type="decision",
            entity_ids=[42],
        ),
        _cand(
            11,
            0.88,
            "the redis cache is not the chosen backing store for sessions",
            claim_type="limitation",
            entity_ids=[42],
        ),
    ]
    out = conflict_monitor_rerank(cands)
    # Plans attach to the top candidate.
    top = out[0]
    assert "conflict_plans" in top
    assert len(top["conflict_plans"]) >= 1
    assert "conflict_assessment" in top
    assert top["conflict_assessment"]["high"] is True


# ── Low-conflict / pass-through path ───────────────────────────────────────────
def test_low_conflict_passes_through():
    cands = [
        _cand(1, 0.90, "the auth service uses jwt tokens for sessions"),
        _cand(2, 0.80, "jwt tokens are validated on every auth request"),
        _cand(3, 0.70, "sessions expire after one hour"),
    ]
    before = [dict(c) for c in cands]
    out = conflict_monitor_rerank(cands)
    assert [c["score"] for c in out] == [c["score"] for c in before]
    assert all("conflict_downweighted" not in c for c in out)


def test_singleton_passes_through():
    cands = [_cand(1, 0.9, "only one memory here")]
    out = conflict_monitor_rerank(cands)
    assert out == cands


def test_empty_passes_through():
    assert conflict_monitor_rerank([]) == []


# ── Ablation guard ─────────────────────────────────────────────────────────────
def test_ablation_disables_stage():
    cands = [
        _cand(1, 0.90, "the auth service uses jwt tokens for sessions"),
        _cand(2, 0.88, "the auth service does not use jwt tokens for sessions"),
    ]
    os.environ["CORTEX_ABLATE_CONFLICT_MONITOR"] = "1"
    try:
        out = conflict_monitor_rerank(cands)
    finally:
        del os.environ["CORTEX_ABLATE_CONFLICT_MONITOR"]
    # Untouched — same scores, no down-weight flag.
    assert [c["score"] for c in out] == [0.90, 0.88]
    assert all("conflict_downweighted" not in c for c in out)


# ── Non-fatal on malformed input ───────────────────────────────────────────────
def test_non_fatal_on_malformed_candidates():
    # Missing score/content — must not raise; stage returns the list.
    cands = [{"memory_id": 1}, {"memory_id": 2}]
    out = conflict_monitor_rerank(cands)
    assert out is cands or out == cands


def test_store_argument_accepted_and_ignored():
    class Dummy:
        pass

    cands = [
        _cand(1, 0.90, "the deploy pipeline is green and healthy"),
        _cand(2, 0.89, "the deploy pipeline is not green, it is broken"),
    ]
    out = conflict_monitor_rerank(cands, Dummy())
    # High-conflict near-tied pair -> loser demoted even with a store passed.
    loser = next(c for c in out if c["memory_id"] == 2)
    assert loser["score"] < 0.89
