"""Integration test for A1 attentional control wired into SensoryBuffer.

Verifies SensoryBuffer.focus() runs the attention-allocation pass over the
live working set non-destructively and returns a bounded, query-weighted focus.
"""

from __future__ import annotations

from mcp_server.core.sensory_buffer import SensoryBuffer


def _fill(buf, contents):
    for c in contents:
        buf.push(c)


def test_focus_returns_query_relevant_items_first():
    buf = SensoryBuffer(capacity=50)
    _fill(
        buf,
        [
            "grocery list for the weekend",
            "the memory decay half-life needs tuning",
            "random unrelated chatter",
            "decay curve thermodynamics review",
        ],
    )
    alloc = buf.focus("memory decay half-life", capacity=2)
    assert len(alloc.focus) == 2
    assert "decay" in alloc.focus[0]["content"]
    # weights form a distribution
    assert abs(sum(alloc.weights) - 1.0) < 1e-9


def test_focus_is_non_destructive():
    buf = SensoryBuffer(capacity=50)
    _fill(buf, ["one item", "two item", "three item"])
    before = buf.size
    buf.focus("item", capacity=2)
    assert buf.size == before  # peek-like, nothing drained


def test_focus_respects_capacity_ceiling():
    buf = SensoryBuffer(capacity=50)
    _fill(buf, [f"decay note number {i}" for i in range(10)])
    alloc = buf.focus("decay note", capacity=4)
    assert len(alloc.focus) == 4
    assert alloc.overflow == 6


def test_focus_empty_buffer():
    buf = SensoryBuffer(capacity=50)
    alloc = buf.focus("anything")
    assert alloc.focus == []
    assert alloc.entropy == 0.0


def test_focus_items_carry_attention_weight():
    buf = SensoryBuffer(capacity=50)
    _fill(buf, ["decay one", "decay two"])
    alloc = buf.focus("decay", capacity=2)
    for f in alloc.focus:
        assert "attention_weight" in f
