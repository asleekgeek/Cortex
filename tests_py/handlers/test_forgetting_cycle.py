"""Handler tests for the active-forgetting consolidation cycle.

The noisy-OR aggregate is the load-bearing maths of the chronic-interference
signal (Pearl 1988), so it is tested directly and exhaustively here — no
database, per the SRP split that keeps aggregation in the handler. A few
fake-store wiring checks confirm the two circuits route to the right reversible
effect.
"""

from __future__ import annotations

import math

import pytest

from mcp_server.core.active_forgetting import (
    ACUTE_OVERLAP_THRESHOLD,
    ACUTE_RECENCY_WINDOW_HOURS,
)
from mcp_server.handlers.consolidation.forgetting import (
    _evaluate_memory,
    _noisy_or,
    run_forgetting_cycle,
)


# ── Noisy-OR aggregate ────────────────────────────────────────────────────


def test_noisy_or_empty_is_zero():
    """No newer neighbors → no chronic interference."""
    assert _noisy_or([]) == 0.0


def test_noisy_or_single_neighbor_equals_its_similarity():
    """One neighbor: 1 - (1 - s) == s."""
    assert _noisy_or([0.6]) == pytest.approx(0.6)


def test_noisy_or_matches_closed_form():
    """1 - ∏(1 - s_i) computed against the explicit product."""
    sims = [0.3, 0.5, 0.2]
    expected = 1.0 - (1 - 0.3) * (1 - 0.5) * (1 - 0.2)
    assert _noisy_or(sims) == pytest.approx(expected)


def test_noisy_or_grows_with_count():
    """Two equal neighbors interfere more than one (accumulation with count)."""
    one = _noisy_or([0.4])
    two = _noisy_or([0.4, 0.4])
    assert two > one
    assert two == pytest.approx(1.0 - (1 - 0.4) ** 2)


def test_noisy_or_monotone_when_adding_a_neighbor():
    """Adding any neighbor never decreases the aggregate (monotone in count)."""
    base = _noisy_or([0.5, 0.3])
    grown = _noisy_or([0.5, 0.3, 0.7])
    assert grown >= base


def test_noisy_or_bounded_unit_interval():
    """Even many strong neighbors stay within [0, 1]."""
    val = _noisy_or([0.9] * 50)
    assert 0.0 <= val <= 1.0


def test_noisy_or_clamps_negative_similarity():
    """A negative cosine (near-orthogonal) contributes nothing, never inflates."""
    assert _noisy_or([-0.5]) == 0.0
    assert _noisy_or([0.6, -0.3]) == pytest.approx(0.6)


def test_noisy_or_clamps_above_one():
    """A >1 similarity is clamped to a saturating term, not an out-of-range one."""
    assert _noisy_or([1.5]) == pytest.approx(1.0)


def test_noisy_or_order_independent():
    """Product is commutative — neighbor ordering must not change the result."""
    assert _noisy_or([0.2, 0.8, 0.4]) == pytest.approx(_noisy_or([0.8, 0.4, 0.2]))


# ── Effect wiring (fake store, no database) ───────────────────────────────


class _FakeStore:
    """Minimal duck-typed store: records the reversible effect applied."""

    def __init__(self, neighbors):
        self._neighbors = neighbors
        self.staled: list[int] = []
        self.heat_writes: dict[int, float] = {}

    def search_newer_neighbors(self, embedding, after, exclude_id, top_k=10):
        return self._neighbors

    def mark_memory_stale(self, memory_id, stale=True):
        self.staled.append(memory_id)

    def update_memory_heat(self, memory_id, heat):
        self.heat_writes[memory_id] = heat


def _memory(**over):
    base = {
        "id": 1,
        "embedding": b"\x00\x00\x80?",  # non-empty; fake store ignores content
        "created_at": "2026-01-01T00:00:00+00:00",
        "consolidation_stage": "labile",
        "heat": 0.5,
        "is_protected": False,
    }
    base.update(over)
    return base


def test_transient_effect_scales_heat_by_interferer_overlap():
    """DAMB block: heat × (1 - acute_overlap), magnitude from measured salience.

    Uses a ``consolidated`` stage so the permanent circuit's pressure stays
    below ``Tp`` and the transient circuit is isolated (the two read disjoint
    signals; permanent — when it fires — subsumes transient).
    """
    overlap = 0.8  # ≥ ACUTE_OVERLAP_THRESHOLD, recent → transient fires
    assert overlap >= ACUTE_OVERLAP_THRESHOLD
    store = _FakeStore([(overlap, 1.0)])  # 1.0h ago ≤ window
    effect = _evaluate_memory(
        store, _memory(consolidation_stage="consolidated", heat=0.5), set()
    )
    assert effect == "transient"
    assert store.heat_writes[1] == pytest.approx(0.5 * (1 - overlap))
    assert store.staled == []


def test_permanent_effect_marks_stale_on_labile_with_strong_chronic():
    """Rac1: a labile trace under strong accumulated newer interference is staled."""
    # Many strong newer neighbors → chronic near 1; labile vulnerability is high.
    store = _FakeStore([(0.9, 100.0)] * 5)  # old enough that transient won't fire
    effect = _evaluate_memory(
        store, _memory(consolidation_stage="labile"), set()
    )
    assert effect == "permanent"
    assert store.staled == [1]


def test_pinned_memory_is_exempt_from_both_circuits():
    """is_protected (or heat≥1.0) exempts the memory entirely."""
    store = _FakeStore([(0.95, 1.0)])  # would otherwise fire transient
    effect = _evaluate_memory(store, _memory(is_protected=True), set())
    assert effect == "retain"
    assert store.staled == [] and store.heat_writes == {}


def test_recently_active_memory_is_sleep_protected():
    """A memory replayed this cycle is exempt (sleep inhibits forgetting)."""
    store = _FakeStore([(0.95, 1.0)])
    effect = _evaluate_memory(store, _memory(id=7), recently_active_ids={7})
    assert effect == "retain"


def test_old_acute_interferer_does_not_trigger_transient():
    """Beyond the recovery window the transient block has lapsed."""
    store = _FakeStore([(0.95, ACUTE_RECENCY_WINDOW_HOURS + 5.0)])
    effect = _evaluate_memory(
        store, _memory(consolidation_stage="consolidated"), set()
    )
    # consolidated → near-zero permanent pressure; stale acute → no transient.
    assert effect == "retain"


def test_cycle_skips_when_store_lacks_newer_neighbor_query():
    """SQLite/cowork fallback degrades gracefully, never raises."""

    class _Bare:
        def iter_memories_for_decay(self):
            return [[_memory()]]

    out = run_forgetting_cycle(_Bare(), set())
    assert out["skipped"] == "unsupported_store"
    assert out["scanned"] == 0


def test_cycle_counts_scanned_and_effects():
    """End-to-end count rollup over a streamed chunk."""

    class _Streaming(_FakeStore):
        def iter_memories_for_decay(self):
            yield [
                _memory(id=1, consolidation_stage="consolidated", heat=0.5),
                _memory(id=2, consolidation_stage="consolidated", heat=0.5),
            ]

    store = _Streaming([(0.8, 1.0)])  # consolidated → permanent quiet; both transient
    out = run_forgetting_cycle(store, set())
    assert out["scanned"] == 2
    assert out["transient"] == 2
    assert out["permanent"] == 0


def test_ablation_short_circuits_cycle(monkeypatch):
    """CORTEX_ABLATE_ACTIVE_FORGETTING=1 → no-op pass."""
    monkeypatch.setenv("CORTEX_ABLATE_ACTIVE_FORGETTING", "1")
    out = run_forgetting_cycle(_FakeStore([(0.9, 1.0)]), set())
    assert out["ablated"] is True
    assert out["scanned"] == 0
