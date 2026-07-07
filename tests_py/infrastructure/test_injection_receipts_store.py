"""Parity roundtrip for injection receipts (blame path T1, decision 4255039).

Falsifiable T1 criterion: the persisted receipt items mirror the bound
payload exactly — same memory_ids, same order (rank), same scores.
Runs against the SQLite backend; the PG mixin shares the same contract
(PG parity asserted by the shared insert signature and DDL parity).
"""

from __future__ import annotations

import pytest

from mcp_server.infrastructure.sqlite_store import SqliteMemoryStore


def _store() -> SqliteMemoryStore:
    return SqliteMemoryStore(db_path=":memory:")


def _payload() -> list[dict]:
    return [
        {"memory_id": 11, "rank": 0, "score": 0.9},
        {"memory_id": 7, "rank": 1, "score": 0.5},
        {"memory_id": 3, "rank": 2, "score": None},
    ]


def test_roundtrip_items_mirror_payload() -> None:
    s = _store()
    rid = s.insert_injection_receipt("recall", _payload())
    rows = s._conn.execute(
        "SELECT memory_id, rank, score FROM injection_receipt_items "
        "WHERE receipt_id = ? ORDER BY rank",
        (rid,),
    ).fetchall()
    assert [(r["memory_id"], r["rank"], r["score"]) for r in rows] == [
        (11, 0, 0.9),
        (7, 1, 0.5),
        (3, 2, None),
    ]


def test_header_records_channel_and_timestamp() -> None:
    s = _store()
    rid = s.insert_injection_receipt("recall", _payload(), session_id="s-1")
    row = s._conn.execute(
        "SELECT session_id, channel, emitted_at FROM injection_receipts "
        "WHERE id = ?",
        (rid,),
    ).fetchone()
    assert row["session_id"] == "s-1"
    assert row["channel"] == "recall"
    assert row["emitted_at"]


def test_session_id_nullable() -> None:
    # Decision 4255039 correction 1: the mcp recall handler has no
    # session identity in scope — NOT NULL would be unexecutable DDL.
    s = _store()
    rid = s.insert_injection_receipt("recall", _payload())
    row = s._conn.execute(
        "SELECT session_id FROM injection_receipts WHERE id = ?", (rid,)
    ).fetchone()
    assert row["session_id"] is None


def test_receipts_are_distinct_appends() -> None:
    s = _store()
    a = s.insert_injection_receipt("recall", _payload())
    b = s.insert_injection_receipt("recall", _payload())
    assert a != b
    count = s._conn.execute(
        "SELECT COUNT(*) AS c FROM injection_receipt_items"
    ).fetchone()["c"]
    assert count == 6


def test_empty_items_rejected() -> None:
    s = _store()
    with pytest.raises(ValueError):
        s.insert_injection_receipt("recall", [])
