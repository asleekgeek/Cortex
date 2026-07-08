"""wiki.citations / wiki.memos DB operations, and wiki-schema diagnostics.

Split out of ``pg_store_wiki.py`` (originally 890 lines, over the
300-line file limit — CLAUDE.md "Code Quality Rules") purely for size
compliance; no logic changed.

Pure infrastructure — no core imports, no handler imports.
"""

from __future__ import annotations

import json

from psycopg import Connection
from psycopg.rows import dict_row

from mcp_server.infrastructure.pg_store_wiki_common import _returning_id


def insert_citation(
    conn: Connection,
    page_id: int,
    session_id: str = "",
    domain: str = "",
    memory_id: int | None = None,
) -> int:
    """Record that a page was cited. Trigger bumps heat + citation_count."""
    sql = """
    INSERT INTO wiki.citations (page_id, session_id, domain, memory_id)
    VALUES (%s, %s, %s, %s)
    RETURNING id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (page_id, session_id, domain, memory_id))
        return _returning_id(cur.fetchone())


def insert_memo(
    conn: Connection,
    subject_type: str,
    subject_id: int,
    decision: str,
    rationale: str = "",
    alternatives: list | None = None,
    inputs: dict | None = None,
    confidence: float = 0.5,
    author: str = "system",
) -> int:
    sql = """
    INSERT INTO wiki.memos (
        subject_type, subject_id, decision, rationale,
        alternatives, inputs, confidence, author
    )
    VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
    RETURNING id;
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                subject_type,
                subject_id,
                decision,
                rationale,
                json.dumps(alternatives or []),
                json.dumps(inputs or {}),
                confidence,
                author,
            ),
        )
        return _returning_id(cur.fetchone())


def wiki_stats(conn: Connection) -> dict:
    """Counts across the wiki schema."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM wiki.pages) AS pages,
              (SELECT COUNT(*) FROM wiki.pages WHERE lifecycle_state='active') AS active,
              (SELECT COUNT(*) FROM wiki.pages WHERE lifecycle_state='archived') AS archived,
              (SELECT COUNT(*) FROM wiki.concepts) AS concepts,
              (SELECT COUNT(*) FROM wiki.drafts WHERE status='pending') AS pending_drafts,
              (SELECT COUNT(*) FROM wiki.claim_events) AS claim_events,
              (SELECT COUNT(*) FROM wiki.links) AS links,
              (SELECT COUNT(*) FROM wiki.citations) AS citations,
              (SELECT COUNT(*) FROM wiki.memos) AS memos
            """
        )
        return cur.fetchone()
