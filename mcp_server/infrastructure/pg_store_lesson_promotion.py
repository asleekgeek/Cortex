"""Read-only query for lesson-promotion candidates (M-D6, INC 7.6).

Mirrors ``pg_store_wiki_notes.py::list_uncited_deliberate_memories`` —
same ``current_memories`` view, same read-only contract: this module
never writes a rule, a trigger, a page, or a tag. It lists candidates for
``handlers.lesson_promotion`` to package into jobs, exactly as
``curate_wiki_uncited.py`` lists candidates for wiki authoring.
"""

from __future__ import annotations

from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row


def list_lesson_promotion_candidates(
    conn: Connection, limit: int = 20
) -> list[dict[str, Any]]:
    """List active lesson/lesson-candidate memories with usage evidence.

    Precondition: none — works on any schema-provisioned DB, even with
    zero lesson-tagged rows.
    Postcondition: returns memories tagged 'lesson' or 'lesson-candidate',
    not stale, not already carrying a 'promoted:*' tag, with
    access_count > 0 OR useful_count > 0 (at least one real recall
    surfacing or rating event — a structural zero/nonzero boundary, not
    a tuned magnitude threshold), ordered by useful_count then
    access_count descending so the most-validated lessons surface
    first. Read-only: never mutates memory_rules, prospective_memories,
    wiki.citations, or the memories table itself.
    """
    sql = """
    SELECT m.id, LEFT(m.content, 500) AS content_preview, m.domain,
           m.tags, m.useful_count, m.access_count, m.created_at
    FROM current_memories m
    WHERE NOT m.is_stale
      AND (
        m.tags @> '["lesson"]'::jsonb
        OR m.tags @> '["lesson-candidate"]'::jsonb
      )
      AND (m.access_count > 0 OR m.useful_count > 0)
      AND NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements_text(m.tags) t
        WHERE t LIKE 'promoted:%%'
      )
    ORDER BY m.useful_count DESC, m.access_count DESC, m.created_at DESC
    LIMIT %s;
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (limit,))
        return list(cur.fetchall())


def count_lesson_promotion_candidates(conn: Connection) -> int:
    """Total count of promotion candidates, unbounded by any job-page limit.

    Precondition: none.
    Postcondition: returns the exact count matching the same WHERE clause
    as ``list_lesson_promotion_candidates`` (same eligibility contract),
    with no LIMIT -- ``lesson_promotion.handler``'s own ``candidate_count``
    field is ``len(candidates)`` and is truncated by ``limit`` (default
    10), so it undercounts the true backlog; this is the exact total for
    grooming-health telemetry. Read-only, single aggregate query.
    Indexed: idx_memories_tags_gin (pg_schema.py) turns the ``tags @>``
    containment checks into a bitmap index scan -- measured 81ms Seq
    Scan -> 0.8ms Bitmap Heap Scan at 11,012 rows (EXPLAIN ANALYZE,
    2026-07-11, dev DB).
    """
    sql = """
    SELECT count(*) AS c
    FROM current_memories m
    WHERE NOT m.is_stale
      AND (
        m.tags @> '["lesson"]'::jsonb
        OR m.tags @> '["lesson-candidate"]'::jsonb
      )
      AND (m.access_count > 0 OR m.useful_count > 0)
      AND NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements_text(m.tags) t
        WHERE t LIKE 'promoted:%'
      );
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)  # no params -> psycopg does not %-parse; literal '%' is safe
        row = cur.fetchone()
        return int(row["c"]) if row else 0
