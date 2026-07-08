"""wiki.page_sources DB operations (ADR-0051 STEP 2 — the writer).

Split out of ``pg_store_wiki.py`` (already ~874 lines, over the 300-line
file limit) rather than added there — coding-standards.md §4.1. Mirrors
the shape of ``pg_store_wiki.upsert_link``: an idempotent refresh scoped
by a key, matching how ``wiki_migrate.migrate_wiki`` already refreshes
``wiki.links`` via ``delete_links_from`` + re-insert per page.

Pure infrastructure — no core imports, no handler imports.
"""

from __future__ import annotations

from psycopg import Connection


def upsert_page_sources(
    conn: Connection,
    page_id: int,
    documents: list[str],
    *,
    link_kind: str = "documents",
    source: str = "frontmatter",
    confidence: float = 1.0,
) -> int:
    """Idempotently replace a page's ``wiki.page_sources`` rows for one link_kind.

    Delete-then-insert scoped to ``(page_id, link_kind)`` — mirrors
    ``pg_store_wiki`` refreshing ``wiki.links`` per src page before
    re-inserting the current set, so re-running the writer on an
    unchanged page produces the same rows (idempotent), and a page
    whose frontmatter dropped a file removes the stale edge instead
    of accumulating it forever.

    Pre-condition:  page_id refers to an existing wiki.pages row;
                    documents entries are already canonical
                    (mcp_server.shared.wiki_source_paths.normalize_source_path).
    Post-condition: wiki.page_sources contains exactly one row per
                    unique path in ``documents`` for this
                    (page_id, link_kind), and no other rows for that
                    (page_id, link_kind) survive from a prior call.

    Returns the number of rows inserted.
    """
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM wiki.page_sources WHERE page_id = %s AND link_kind = %s",
            (page_id, link_kind),
        )
        if not documents:
            return 0
        cur.executemany(
            """
            INSERT INTO wiki.page_sources (page_id, source_path, link_kind, confidence, source)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (page_id, source_path, link_kind) DO UPDATE SET
                confidence = EXCLUDED.confidence,
                source = EXCLUDED.source
            """,
            [(page_id, path, link_kind, confidence, source) for path in documents],
        )
        return len(documents)
