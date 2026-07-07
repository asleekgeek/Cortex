"""Injection-receipt persistence, PostgreSQL backend.

Blame path T1/T2 (decision Cortex 4255039): receipts are an append-only
record of what a channel injected into a context — there is no update
or delete surface by design.

Two write paths share the single-statement SQL below:

* ``PgReceiptsMixin.insert_injection_receipt`` — the store path used by
  the MCP recall handler (pooled connections via ``_execute``).
* ``insert_receipt_on_connection`` — the hook path (T2): SessionStart /
  UserPromptSubmit / SubagentStart hooks own a short-lived psycopg
  connection and no store instance.
"""

from __future__ import annotations

# Single data-modifying-CTE statement on purpose: the store's
# ``_execute`` borrows a pool connection per call, so two separate
# INSERTs could land on two connections and lose header/items atomicity.
_INSERT_RECEIPT_SQL = (
    "WITH r AS ("
    "  INSERT INTO injection_receipts (session_id, channel)"
    "  VALUES (%s, %s) RETURNING id"
    ") "
    "INSERT INTO injection_receipt_items"
    "  (receipt_id, memory_id, rank, score) "
    "SELECT r.id, t.memory_id, t.rank, t.score "
    "FROM r, UNNEST(%s::int[], %s::int[], %s::real[])"
    "  AS t(memory_id, rank, score) "
    "RETURNING receipt_id"
)


def _receipt_params(
    channel: str, items: list[dict], session_id: str | None
) -> tuple:
    """Coerce items into the (session_id, channel, ids, ranks, scores) tuple."""
    if not items:
        raise ValueError("injection receipt requires at least one item")
    memory_ids = [int(i["memory_id"]) for i in items]
    ranks = [int(i["rank"]) for i in items]
    scores = [
        None if i.get("score") is None else float(i["score"]) for i in items
    ]
    return (session_id, channel, memory_ids, ranks, scores)


def insert_receipt_on_connection(
    conn,
    channel: str,
    items: list[dict],
    session_id: str | None = None,
) -> int:
    """Insert one receipt atomically on a caller-owned psycopg connection.

    Hook channels (T2) own their connection lifecycle — dict_row or
    tuple rows both work. Commit is a no-op under autocommit (the hook
    default); otherwise the receipt commits here.
    """
    row = conn.execute(
        _INSERT_RECEIPT_SQL, _receipt_params(channel, items, session_id)
    ).fetchone()
    if not getattr(conn, "autocommit", False):
        conn.commit()
    return int(row["receipt_id"] if isinstance(row, dict) else row[0])


class PgReceiptsMixin:
    """Append-only injection receipts (blame path T1)."""

    def insert_injection_receipt(
        self,
        channel: str,
        items: list[dict],
        session_id: str | None = None,
    ) -> int:
        """Insert one receipt header + its items atomically; return receipt_id."""
        row = self._execute(
            _INSERT_RECEIPT_SQL, _receipt_params(channel, items, session_id)
        ).fetchone()
        self._conn.commit()
        return int(row["receipt_id"])
