"""PG-gated read-path tests for injection receipts (blame path T3).

Exercises the PG-specific SQL of ``fetch_injection_receipts`` that the
SQLite parity suite cannot: ``ANY(%s::int[])`` id resolution, the LEFT
JOIN surviving a hard-forgotten memory, and recorded-facts ordering
(emitted_at DESC, id DESC, rank ASC) under real timestamptz values.

Skipped automatically when PG is not reachable (CI without pgvector).
"""

from __future__ import annotations

import pytest

from tests_py.conftest import _USE_PG, _TEST_DB_URL  # type: ignore

pytestmark = pytest.mark.skipif(
    not _USE_PG, reason="PostgreSQL not available — fetch path needs PG schema"
)

_SESSION = "sess-why-t3-fixture"


def _cleanup(conn) -> None:
    conn.execute(
        "DELETE FROM injection_receipts WHERE session_id = %s", (_SESSION,)
    )
    conn.execute(
        "DELETE FROM memories WHERE content LIKE %s", ("WHYFETCH_TEST%",)
    )


@pytest.fixture()
def _env():
    """Provisioned store + autocommit conn + clean slate, torn down after."""
    from mcp_server.infrastructure.pg_store import PgMemoryStore

    store = PgMemoryStore(database_url=_TEST_DB_URL)

    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(_TEST_DB_URL, row_factory=dict_row, autocommit=True)
    _cleanup(conn)

    yield store, conn

    _cleanup(conn)
    conn.close()
    try:
        store._conn.close()
    except Exception:
        pass


def _seed(conn, content: str, superseded_by: int | None = None) -> int:
    row = conn.execute(
        "INSERT INTO memories (content, heat_base, heat_base_set_at, "
        "is_benchmark, plasticity, no_decay, is_protected, is_global, "
        "agent_context, tags, superseded_by_id) "
        "VALUES (%s, 0.9, NOW(), FALSE, 1.0, FALSE, FALSE, FALSE, '', "
        "'[]'::jsonb, %s) RETURNING id",
        (content, superseded_by),
    ).fetchone()
    return int(row["id"])


def test_fetch_pg_resolves_joins_and_orders_by_recorded_facts(_env) -> None:
    store, conn = _env
    corrected = _seed(conn, "WHYFETCH_TEST corrected")
    wrong = _seed(conn, "WHYFETCH_TEST wrong", superseded_by=corrected)

    older = store.insert_injection_receipt(
        "recall",
        [
            {"memory_id": wrong, "rank": 0, "score": 0.9},
            # Hard-forgotten memory: no row behind this id — the LEFT
            # JOIN must keep the evidence with m.* NULL.
            {"memory_id": 2_000_000_000, "rank": 1, "score": None},
        ],
        session_id=_SESSION,
    )
    newer = store.insert_injection_receipt(
        "auto_recall",
        [{"memory_id": corrected, "rank": 0, "score": 0.7}],
        session_id=_SESSION,
    )
    # Force a strict emitted_at gap so the ordering test cannot pass by
    # id-tiebreak accident.
    conn.execute(
        "UPDATE injection_receipts SET emitted_at = NOW() - INTERVAL '1 hour' "
        "WHERE id = %s",
        (older,),
    )

    rows = store.fetch_injection_receipts([older, newer, 1_999_999_999])

    assert [r["receipt_id"] for r in rows] == [newer, older, older]
    assert [r["rank"] for r in rows] == [0, 0, 1]
    assert rows[0]["channel"] == "auto_recall"
    assert rows[0]["content"] == "WHYFETCH_TEST corrected"
    assert rows[0]["session_id"] == _SESSION
    # Superseded state surfaced, never filtered (historical evidence).
    assert rows[1]["superseded_by_id"] == corrected
    assert rows[1]["content"] == "WHYFETCH_TEST wrong"
    # LEFT JOIN survival for the hard-forgotten id.
    assert rows[2]["memory_row_id"] is None
    assert rows[2]["content"] is None
    assert rows[2]["memory_id"] == 2_000_000_000


def test_fetch_pg_unknown_and_empty_inputs(_env) -> None:
    store, _conn = _env
    assert store.fetch_injection_receipts([1_888_888_888]) == []
    assert store.fetch_injection_receipts([]) == []
