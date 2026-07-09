"""Tests for mcp_server.handlers.recall._apply_rules_and_order.

This is the hot-path call site (invoked on every recall) that consumes
mcp_server.core.memory_rules.apply_rules — the function fixed in
fix/add-rule-memory-rules-drift. These tests pin the wiring contract at
this call site so the engine fix (hard-exclude semantics, fail-safe parse
errors, tag rules) cannot silently regress at the handler boundary.
"""

from __future__ import annotations

from types import SimpleNamespace

from mcp_server.handlers.recall import _apply_rules_and_order


class _FakeStore:
    """Minimal store double exposing only what _apply_rules_and_order calls."""

    def __init__(self, rules: list[dict]):
        self._rules = rules

    def get_all_active_rules(self) -> list[dict]:
        return self._rules


def _settings(strategic_ordering: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        STRATEGIC_ORDERING_ENABLED=strategic_ordering,
        STRATEGIC_TOP_FRACTION=0.2,
        STRATEGIC_BOTTOM_FRACTION=0.2,
    )


class TestApplyRulesAndOrder:
    def test_no_active_rules_is_a_noop(self):
        results = [{"content": "a", "score": 1.0}, {"content": "b", "score": 0.5}]
        store = _FakeStore([])
        out = _apply_rules_and_order(results, store, _settings(), max_results=10)
        assert [r["content"] for r in out] == ["a", "b"]

    def test_hard_rule_excludes_matching_memories(self):
        """Pins the fixed semantics at the recall call site: a hard 'filter'
        rule removes memories that MATCH its condition."""
        results = [
            {"content": "current", "tags": ["core"], "score": 1.0},
            {"content": "old", "tags": ["deprecated"], "score": 0.9},
        ]
        store = _FakeStore(
            [
                {
                    "rule_type": "hard",
                    "condition": "tag contains deprecated",
                    "action": "filter",
                }
            ]
        )
        out = _apply_rules_and_order(results, store, _settings(), max_results=10)
        assert [r["content"] for r in out] == ["current"]

    def test_soft_rule_reranks_without_dropping(self):
        results = [
            {"content": "a", "tags": ["lesson"], "score": 0.5},
            {"content": "b", "tags": [], "score": 0.6},
        ]
        store = _FakeStore(
            [
                {
                    "rule_type": "soft",
                    "condition": "tag contains lesson",
                    "action": "boost:0.3",
                }
            ]
        )
        out = _apply_rules_and_order(results, store, _settings(), max_results=10)
        assert len(out) == 2
        assert out[0]["content"] == "a"  # boosted to 0.8, ranks first

    def test_store_exception_degrades_to_passthrough(self):
        """apply_rules failures must not break recall — the handler wraps
        the call in try/except (recall.py:329-334)."""

        class _BrokenStore:
            def get_all_active_rules(self):
                raise RuntimeError("db unavailable")

        results = [{"content": "a", "score": 1.0}]
        out = _apply_rules_and_order(
            results, _BrokenStore(), _settings(), max_results=10
        )
        assert [r["content"] for r in out] == ["a"]

    def test_max_results_applied_after_rules(self):
        results = [{"content": str(i), "score": float(i)} for i in range(5)]
        store = _FakeStore([])
        out = _apply_rules_and_order(results, store, _settings(), max_results=2)
        assert len(out) == 2
