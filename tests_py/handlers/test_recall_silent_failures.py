"""Silent-except sweep (audit 2026-07-11): recall handler's production
enrichments (docstring: "co-activation Hebbian learning, neuro-symbolic
rules"). Both were a bare ``except Exception: pass`` -- a real regression
in either would silently and permanently disable a named production
enrichment with zero signal, the same shape as the FlashRank
(bb1c581f) and spread_activation incidents this audit was triggered by.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mcp_server.handlers.recall import _apply_co_activation, _apply_rules_and_order
from mcp_server.observability import silent_failure


@pytest.fixture(autouse=True)
def _reset():
    silent_failure.reset()
    yield
    silent_failure.reset()


class TestHebbianCoActivationFailureIsObservable:
    def test_relationship_write_failure_is_logged(self, caplog, monkeypatch):
        monkeypatch.setattr(
            "mcp_server.core.ablation.is_mechanism_disabled", lambda m: False
        )
        monkeypatch.setattr(
            "mcp_server.handlers.recall.extract_entities",
            lambda content: [{"name": n} for n in content.split()],
        )
        store = MagicMock()
        store.reinforce_or_create_relationship.side_effect = RuntimeError("pg down")
        settings = SimpleNamespace(
            CO_ACTIVATION_ENABLED=True,
            CO_ACTIVATION_MIN_SCORE=0.0,
            CO_ACTIVATION_LEARNING_RATE=0.1,
        )
        results = [
            {"score": 0.9, "content": "Alice Bob"},
            {"score": 0.8, "content": "Carol Dave"},
        ]
        with caplog.at_level(
            "WARNING", logger="mcp_server.observability.silent_failure"
        ):
            _apply_co_activation(results, store, settings)

        assert any("recall.hebbian_co_activation" in r.message for r in caplog.records)


class TestNeuroSymbolicRulesFailureIsObservable:
    def test_rules_read_failure_is_logged(self, caplog):
        store = MagicMock()
        store.get_all_active_rules.side_effect = RuntimeError("pg down")
        settings = SimpleNamespace(
            STRATEGIC_ORDERING_ENABLED=False,
            STRATEGIC_TOP_FRACTION=0.3,
            STRATEGIC_BOTTOM_FRACTION=0.2,
        )
        results = [{"score": 0.5}]
        with caplog.at_level(
            "WARNING", logger="mcp_server.observability.silent_failure"
        ):
            out = _apply_rules_and_order(results, store, settings, max_results=10)

        # Behavior-preserving: falls back to the unfiltered results.
        assert out == results
        assert any("recall.neuro_symbolic_rules" in r.message for r in caplog.records)
