"""Tests for the T2-H3 recall→session-registry wiring (T2-D7).

recall.py's T1 receipt emission resolves the current window's session
id fresh at every call via ``session_registry.current_window_session``
(no cache — T2-D7). Two layers are exercised here:

  1. ``_resolve_session_id`` (recall.py's own boundary guard): mocked at
     the ``mcp_server.handlers.recall.current_window_session`` import
     site — proves the handler degrades to None on any registry
     exception without failing recall's primary path.
  2. The call-site wiring inside ``_handler_impl``: proves the resolved
     session id reaches ``emit_injection_receipt`` (and therefore
     ``store.insert_injection_receipt``) unmodified, for both the
     "registry answers" and "registry absent/tombstoned/divergent"
     cases (registry-internal absent/tombstone/divergent scenarios are
     already unit-tested at their own layer in
     ``tests_py/infrastructure/test_session_registry.py`` — this file
     only proves the handler *consumes* that contract correctly).
"""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from mcp_server.handlers import recall as recall_mod


def test_resolve_session_id_returns_registry_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(recall_mod, "current_window_session", lambda: "sess-abc")
    assert recall_mod._resolve_session_id() == "sess-abc"


def test_resolve_session_id_returns_none_when_registry_answers_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(recall_mod, "current_window_session", lambda: None)
    assert recall_mod._resolve_session_id() is None


def test_resolve_session_id_degrades_on_registry_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Best-effort contract (design §1/§risk-5, T2-H3 task spec item 3):
    an exception from the registry must never surface into recall."""

    def _raise() -> str | None:
        raise RuntimeError("registry blew up")

    monkeypatch.setattr(recall_mod, "current_window_session", _raise)
    assert recall_mod._resolve_session_id() is None


class _FakeStore:
    """Minimal store double: records the receipt insert call, answers
    every other MemoryStore method the handler's enrichment path needs
    with empty/no-op results so ``_handler_impl`` runs end-to-end
    without a live DB."""

    def __init__(self) -> None:
        self.receipt_calls: list[dict] = []

    def insert_injection_receipt(
        self, channel: str, items: list[dict], session_id: str | None = None
    ) -> int:
        self.receipt_calls.append(
            {"channel": channel, "items": items, "session_id": session_id}
        )
        return 99

    # No-op enrichment hooks touched downstream of pg_recall in the
    # production path when results are non-empty (co-activation,
    # rules, replay tracking) — irrelevant to this test's assertion,
    # kept as inert no-ops so the handler doesn't raise on a missing
    # attribute.
    def get_all_active_rules(self) -> list[dict]:
        return []

    def __getattr__(self, name: str):
        def _noop(*args, **kwargs):
            return None

        return _noop


def _emb() -> bytes:
    rng = np.random.default_rng(0)
    v = rng.standard_normal(384).astype(np.float32)
    v /= np.linalg.norm(v)
    return v.tobytes()


def _run_recall_with_session(monkeypatch: pytest.MonkeyPatch, session_value):
    """Drive ``_handler_impl`` through a single pg_recall hit, with the
    session registry and store both faked, to prove the wiring reaches
    ``emit_injection_receipt`` and hence ``store.insert_injection_receipt``.
    """
    store = _FakeStore()
    fake_result = [{"memory_id": 5, "content": "hit", "score": 0.8}]

    monkeypatch.setattr(recall_mod, "_get_store", lambda: store)
    monkeypatch.setattr(recall_mod, "get_embedding_engine", lambda: _emb())
    monkeypatch.setattr(recall_mod, "pg_recall", lambda **kwargs: list(fake_result))
    monkeypatch.setattr(recall_mod, "root_agent_topic", lambda: None)
    # Real settings (env-derived config, no I/O) — avoids hand-maintaining
    # a fake settings object's growing attribute surface.
    if isinstance(session_value, Exception):

        def _cws():
            raise session_value

        monkeypatch.setattr(recall_mod, "current_window_session", _cws)
    else:
        monkeypatch.setattr(recall_mod, "current_window_session", lambda: session_value)

    result = asyncio.run(recall_mod._handler_impl({"query": "probe"}))
    return store, result


class TestRecallReceiptSessionWiring:
    def test_receipt_carries_resolved_session_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store, result = _run_recall_with_session(monkeypatch, "window-session-xyz")
        assert store.receipt_calls, "expected a receipt insert call"
        assert store.receipt_calls[0]["session_id"] == "window-session-xyz"
        assert store.receipt_calls[0]["channel"] == "recall"
        assert result.get("receipt_id") == 99

    def test_receipt_carries_none_when_registry_has_no_entry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store, _ = _run_recall_with_session(monkeypatch, None)
        assert store.receipt_calls[0]["session_id"] is None

    def test_recall_does_not_fail_when_registry_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store, result = _run_recall_with_session(
            monkeypatch, RuntimeError("registry down")
        )
        assert "memories" in result
        assert store.receipt_calls[0]["session_id"] is None
