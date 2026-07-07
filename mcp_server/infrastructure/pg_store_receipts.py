"""Injection-receipt persistence, PostgreSQL backend.

Blame path T1 (decision Cortex 4255039): receipts are an append-only
record of what a channel injected into a context — there is no update
or delete surface by design.
"""

from __future__ import annotations


class PgReceiptsMixin:
    """Append-only injection receipts (blame path T1)."""

    def insert_injection_receipt(
        self,
        channel: str,
        items: list[dict],
        session_id: str | None = None,
    ) -> int:
        """Insert one receipt header + its items atomically; return receipt_id.

        Single data-modifying-CTE statement on purpose: ``_execute``
        borrows a pool connection per call, so two separate INSERTs
        could land on two connections and lose header/items atomicity.
        """
        if not items:
            raise ValueError("injection receipt requires at least one item")
        memory_ids = [int(i["memory_id"]) for i in items]
        ranks = [int(i["rank"]) for i in items]
        scores = [
            None if i.get("score") is None else float(i["score"]) for i in items
        ]
        row = self._execute(
            "WITH r AS ("
            "  INSERT INTO injection_receipts (session_id, channel)"
            "  VALUES (%s, %s) RETURNING id"
            ") "
            "INSERT INTO injection_receipt_items"
            "  (receipt_id, memory_id, rank, score) "
            "SELECT r.id, t.memory_id, t.rank, t.score "
            "FROM r, UNNEST(%s::int[], %s::int[], %s::real[])"
            "  AS t(memory_id, rank, score) "
            "RETURNING receipt_id",
            (session_id, channel, memory_ids, ranks, scores),
        ).fetchone()
        self._conn.commit()
        return int(row["receipt_id"])
