"""Injection-receipt persistence, SQLite backend.

Blame path T1 (decision Cortex 4255039): append-only record of what a
channel injected into a context. PG parity with pg_store_receipts.py.
"""

from __future__ import annotations


class SqliteReceiptsMixin:
    """Append-only injection receipts (blame path T1)."""

    def insert_injection_receipt(
        self,
        channel: str,
        items: list[dict],
        session_id: str | None = None,
    ) -> int:
        """Insert one receipt header + its items; return receipt_id."""
        if not items:
            raise ValueError("injection receipt requires at least one item")
        cur = self._raw_conn.execute(
            "INSERT INTO injection_receipts (session_id, channel) VALUES (?, ?)",
            (session_id, channel),
        )
        receipt_id = int(cur.lastrowid)
        self._raw_conn.executemany(
            "INSERT INTO injection_receipt_items"
            " (receipt_id, memory_id, rank, score) VALUES (?, ?, ?, ?)",
            [
                (
                    receipt_id,
                    int(i["memory_id"]),
                    int(i["rank"]),
                    None if i.get("score") is None else float(i["score"]),
                )
                for i in items
            ],
        )
        self._conn.commit()
        return receipt_id
