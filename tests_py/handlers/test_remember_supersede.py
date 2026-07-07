"""Tests for the explicit supersession write path (PRD dual-access increment 1).

Item ① — ``remember(supersedes_id)``: append-only human correction through
the handler; ``force`` composes with it (sovereign correction bypasses the
write gate but still posts the edge). Item ② — the atomic supersession path in
``insert_and_post_process``: ``store.supersede_atomic`` inserts the new row and
the edge as one transaction, so an exhausted reconsolidation rebase rolls the
insert back and reports a conflict — never forks a chain, never leaves an
orphaned, disconnected row.

Handler tests run against the shared store wired by conftest (live PG when
available). The conflict-path test uses a duck-typed fake because the race
window — the chain head moving under the compare-and-set — cannot be opened
deterministically through the public handler.
"""

import asyncio

from mcp_server.handlers.remember import handler
from mcp_server.handlers.remember_helpers import (
    insert_and_post_process,
    validate_supersede_target,
)
from mcp_server.infrastructure.memory_config import get_memory_settings
from mcp_server.infrastructure.memory_store import get_shared_store


def _store():
    s = get_memory_settings()
    return get_shared_store(s.DB_PATH, s.EMBEDDING_DIM)


def _remember(payload: dict) -> dict:
    return asyncio.run(handler(payload))


class TestRememberSupersedes:
    """Item ① acceptance — the handler-level supersession contract."""

    def test_supersede_creates_chain(self):
        base = _remember(
            {
                "content": "Supersede-chain base fact: gateway timeout is 30s",
                "force": True,
            }
        )
        assert base["stored"] is True
        old_id = base["memory_id"]

        fix = _remember(
            {
                "content": "Supersede-chain corrected fact: gateway timeout is 60s",
                "supersedes_id": old_id,
                "force": True,
            }
        )
        assert fix["stored"] is True
        assert fix["action"] == "superseded"
        assert fix["superseded_id"] == old_id
        new_id = fix["memory_id"]

        store = _store()
        assert store.get_memory(old_id)["superseded_by_id"] == new_id
        assert store.get_memory(new_id)["supersedes_id"] == old_id

    def test_human_edit_never_lost_forced_duplicate(self):
        """Acceptance « une édition humaine ne se perd jamais » : force +
        supersedes_id lands even when the gate would reject the content as
        redundant (identical text = lowest possible novelty)."""
        content = "Team retro cadence is every second Thursday morning"
        base = _remember({"content": content, "force": True})
        assert base["stored"] is True
        old_id = base["memory_id"]

        fix = _remember(
            {"content": content, "supersedes_id": old_id, "force": True}
        )
        assert fix["stored"] is True, fix
        assert fix["action"] == "superseded"
        assert _store().get_memory(old_id)["superseded_by_id"] == fix["memory_id"]

    def test_target_not_found_rejected(self):
        result = _remember(
            {
                "content": "Correction pointing at a ghost target",
                "supersedes_id": 2_000_000_000,
                "force": True,
            }
        )
        assert result["stored"] is False
        assert result["action"] == "rejected"
        assert result["reason"] == "supersede_target_not_found"
        assert result["supersede_target_id"] == 2_000_000_000

    def test_already_superseded_target_rejected_no_fork(self):
        base = _remember(
            {"content": "Chain-fork base: build runs on runner A", "force": True}
        )
        old_id = base["memory_id"]
        first = _remember(
            {
                "content": "Chain-fork head: build runs on runner B",
                "supersedes_id": old_id,
                "force": True,
            }
        )
        assert first["action"] == "superseded"

        second = _remember(
            {
                "content": "Chain-fork attempt: build runs on runner C",
                "supersedes_id": old_id,
                "force": True,
            }
        )
        assert second["stored"] is False
        assert second["action"] == "rejected"
        assert second["reason"] == "supersede_target_already_superseded"
        assert second["current_superseded_by_id"] == first["memory_id"]
        # No silent fork: the head is still the first correction.
        assert _store().get_memory(old_id)["superseded_by_id"] == first["memory_id"]

    def test_invalid_supersedes_id_rejected(self):
        for bad in (0, -3, "not-an-id"):
            result = _remember(
                {
                    "content": "Correction with a malformed target id",
                    "supersedes_id": bad,
                    "force": True,
                }
            )
            assert result["stored"] is False, bad
            assert result["reason"] == "invalid_supersedes_id", bad


class _ConflictStore:
    """Duck-typed store whose atomic supersession never converges: the bounded
    reconsolidation rebase exhausts and returns (None, current_head), the
    signal that nothing was committed (the transaction rolled back each try)."""

    def __init__(self, current_head: int = 555) -> None:
        self.current_head = current_head
        self.calls: list[tuple[dict, int]] = []

    def supersede_atomic(
        self, data: dict, target_id: int
    ) -> tuple[int | None, int | None]:
        self.calls.append((dict(data), target_id))
        return None, self.current_head


class _NoopEngine:
    def encode(self, _text):
        return None

    def similarity(self, _a, _b) -> float:
        return 0.0


_MOD = {
    "heat": 0.5,
    "importance": 0.5,
    "valence": 0.0,
    "theta": 0.0,
    "enc_mod": 1.0,
    "schema_match": 0.0,
    "schema_id": None,
    "emotional_tag": None,
}


def _run_conflict(store: _ConflictStore) -> dict:
    return insert_and_post_process(
        content="corrected fact after a lost race",
        embedding=None,
        tags=[],
        source="user",
        domain="unit-test",
        directory="",
        action="supersede",
        merged_id=42,
        sims=[],
        vec_hits=[],
        ent_names=[],
        extracted=[],
        mod=_MOD,
        novelty_score=0.5,
        store=store,
        emb_engine=_NoopEngine(),
    )


class TestSupersedeConflict:
    """Item ② — conflict propagation: atomic rollback, never an orphan."""

    def test_exhausted_rebase_reports_conflict_no_orphan(self):
        store = _ConflictStore(current_head=555)
        result = _run_conflict(store)
        assert result["stored"] is False
        assert result["action"] == "superseded_conflict"
        assert result["reason"] == "supersede_chain_head_moving"
        assert result["supersede_target_id"] == 42
        assert result["current_head_id"] == 555
        # The atomic insert+edge rolls back on a lost race, so there is never a
        # committed row to delete or leave orphaned — the concept is gone.
        assert "orphan_memory_id" not in result
        assert store.calls and store.calls[0][1] == 42


class _HeadStore:
    """Minimal get_memory-only store for target validation tests."""

    def __init__(self, rows: dict) -> None:
        self._rows = rows

    def get_memory(self, mem_id: int):
        return self._rows.get(mem_id)


class TestValidateSupersedeTarget:
    def test_none_passes_through(self):
        assert validate_supersede_target(None, _HeadStore({})) == (None, None)

    def test_valid_head_resolves(self):
        store = _HeadStore({7: {"id": 7, "superseded_by_id": None}})
        assert validate_supersede_target(7, store) == (7, None)

    def test_missing_target_rejected(self):
        sid, rejection = validate_supersede_target(9, _HeadStore({}))
        assert sid is None
        assert rejection["reason"] == "supersede_target_not_found"

    def test_already_superseded_rejected_with_head(self):
        store = _HeadStore({7: {"id": 7, "superseded_by_id": 11}})
        sid, rejection = validate_supersede_target(7, store)
        assert sid is None
        assert rejection["reason"] == "supersede_target_already_superseded"
        assert rejection["current_superseded_by_id"] == 11

    def test_malformed_rejected(self):
        for bad in (0, -1, "xyz"):
            sid, rejection = validate_supersede_target(bad, _HeadStore({}))
            assert sid is None, bad
            assert rejection["reason"] == "invalid_supersedes_id", bad
