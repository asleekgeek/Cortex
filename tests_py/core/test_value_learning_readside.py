"""Read-side integration tests for B2 value learning.

Covers the two behavior-changing wirings: value nudging recall ranking
(recall_pipeline.value_priority_rerank) and value slowing decay
(thermodynamics.compute_decay).
"""

from __future__ import annotations

import os

import pytest

from mcp_server.core import recall_pipeline as rp
from mcp_server.core import thermodynamics as thermo


# ── VALUE_PRIORITY rerank stage ─────────────────────────────────────────────
def test_value_breaks_score_tie():
    cands = [
        {"memory_id": 1, "score": 1.0, "value": 0.2},
        {"memory_id": 2, "score": 1.0, "value": 0.9},
    ]
    out = rp.value_priority_rerank(cands)
    assert [c["memory_id"] for c in out] == [2, 1]


def test_value_nudge_does_not_override_strong_match():
    # A much stronger content score should stay ahead despite lower value.
    cands = [
        {"memory_id": 1, "score": 2.0, "value": 0.0},
        {"memory_id": 2, "score": 1.0, "value": 1.0},
    ]
    out = rp.value_priority_rerank(cands)
    assert out[0]["memory_id"] == 1  # weight 0.15 can't close a 2x gap


def test_missing_value_is_noop_for_that_candidate():
    cands = [
        {"memory_id": 1, "score": 1.0},            # no value key
        {"memory_id": 2, "score": 1.0, "value": 0.9},
    ]
    out = rp.value_priority_rerank(cands)
    # id 1 keeps its exact score; id 2 boosted above it.
    scores = {c["memory_id"]: c["score"] for c in out}
    assert scores[1] == 1.0
    assert scores[2] > 1.0


def test_value_priority_ablation_guard():
    cands = [
        {"memory_id": 1, "score": 1.0, "value": 0.2},
        {"memory_id": 2, "score": 1.0, "value": 0.9},
    ]
    os.environ["CORTEX_ABLATE_VALUE_PRIORITY"] = "1"
    try:
        out = rp.value_priority_rerank([dict(c) for c in cands])
        # Disabled: original order preserved, scores untouched.
        assert [c["memory_id"] for c in out] == [1, 2]
        assert out[0]["score"] == 1.0 and out[1]["score"] == 1.0
    finally:
        del os.environ["CORTEX_ABLATE_VALUE_PRIORITY"]


def test_single_candidate_noop():
    cands = [{"memory_id": 1, "score": 1.0, "value": 0.9}]
    out = rp.value_priority_rerank(cands)
    assert out == cands


# ── Value in the decay function ─────────────────────────────────────────────
def test_high_value_resists_decay():
    neutral = thermo.compute_decay(1.0, 24, value=0.5)
    high = thermo.compute_decay(1.0, 24, value=1.0)
    assert high > neutral


def test_low_value_does_not_accelerate_decay():
    neutral = thermo.compute_decay(1.0, 24, value=0.5)
    low = thermo.compute_decay(1.0, 24, value=0.0)
    assert low == pytest.approx(neutral)


def test_value_default_preserves_prior_halflife():
    # Default call (no value arg) must equal explicit neutral value=0.5, so
    # existing callers see unchanged decay.
    default = thermo.compute_decay(1.0, 24)
    neutral = thermo.compute_decay(1.0, 24, value=0.5)
    assert default == pytest.approx(neutral)
