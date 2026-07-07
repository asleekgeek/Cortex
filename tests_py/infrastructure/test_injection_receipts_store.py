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


# ── T2: channel enum hardening (decision 4255039 correction 3) ───────────


def _ddl_check_members(ddl: str) -> set[str]:
    """Extract the channel CHECK members from a DDL string."""
    import re

    m = re.search(r"channel IN \(([^)]*)\)", ddl)
    assert m, "channel CHECK constraint not found in DDL"
    return {v.strip().strip("'") for v in m.group(1).split(",")}


def test_channel_enum_parity_sqlite_ddl() -> None:
    from mcp_server.handlers.injection_receipts import INJECTION_CHANNELS
    from mcp_server.infrastructure.sqlite_schema import INJECTION_RECEIPTS_DDL

    assert _ddl_check_members(INJECTION_RECEIPTS_DDL) == set(INJECTION_CHANNELS)


def test_channel_enum_parity_pg_ddl_and_migration() -> None:
    from mcp_server.handlers.injection_receipts import INJECTION_CHANNELS
    from mcp_server.infrastructure import pg_schema

    ddl = pg_schema.SUPPORT_TABLES_DDL
    assert _ddl_check_members(ddl) == set(INJECTION_CHANNELS)
    # The migration that hardens T1-created tables must carry the same enum.
    assert _ddl_check_members(pg_schema.MIGRATIONS_DDL) == set(INJECTION_CHANNELS)


def test_fresh_sqlite_table_rejects_unknown_channel() -> None:
    # Fresh tables carry the CHECK; pre-T2 tables keep free TEXT and rely
    # on the emitter-level validation (documented DDL deviation).
    import sqlite3

    s = _store()
    with pytest.raises(sqlite3.IntegrityError):
        s.insert_injection_receipt("banner", _payload())


def test_all_enum_channels_accepted_by_fresh_sqlite_table() -> None:
    from mcp_server.handlers.injection_receipts import INJECTION_CHANNELS

    s = _store()
    for channel in sorted(INJECTION_CHANNELS):
        assert s.insert_injection_receipt(channel, _payload()) > 0
