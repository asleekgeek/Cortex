"""``memories`` domain-backfill DB operations (I6-D3).

Reads domain-less memory rows (``current_memories`` — chain heads only,
matching the audit's own scope) and rewrites their ``domain``/``tags``
columns. Split into its own module (rather than added to an existing
``pg_store_*`` file) to keep each infrastructure file focused and under
the size cap — mirrors ``pg_store_wiki_domain.py``'s precedent for the
same problem shape (ADR-0051 Volet 4, commit 4ea13310).

Pure infrastructure — no core imports, no handler imports.

Every write here is guarded by ``WHERE (domain IS NULL OR domain = '')``
at the SQL level, not just in the caller: a concurrent write racing this
campaign can never be clobbered, and re-running the same UPDATE after it
already applied is a no-op (idempotence by construction, not by
application-level bookkeeping).
"""

from __future__ import annotations

from psycopg import Connection
from psycopg.rows import dict_row

_ORPHAN_TAG = "domain-orphan"


def list_domainless_memories(conn: Connection, limit: int) -> list[dict]:
    """Active (chain-head) memories whose domain is empty, with evidence.

    Pre-condition:  ``limit`` bounds the per-cycle/per-run scan.
    Post-condition: every returned row carries ``id``, ``directory_context``
                    (``''`` if unset) and ``tags`` (JSON-decoded to a
                    Python list by psycopg's jsonb adapter). Scoped to
                    ``current_memories`` (superseded_by_id IS NULL) —
                    the same view the I6-D3 acceptance-criterion SQL
                    queries. Rows already carrying the ``domain-orphan``
                    tag are excluded: an orphan is a terminal, explicit
                    state (I6-D3 rejects a sentinel domain value, so the
                    tag is the only signal that the row was already
                    processed) — without this exclusion every re-run
                    would re-select and re-journal every orphan forever,
                    breaking the idempotence contract even though no DB
                    write would actually occur.
    """
    sql = """
    SELECT id, directory_context, tags
      FROM current_memories
     WHERE (domain IS NULL OR domain = '')
       AND NOT tags @> '["domain-orphan"]'::jsonb
     ORDER BY id
     LIMIT %(limit)s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, {"limit": limit})
        return list(cur.fetchall())


def update_memory_domain(conn: Connection, memory_id: int, domain: str) -> bool:
    """Set one memory's domain, but only if it is still empty.

    Pre-condition:  ``memory_id`` refers to an existing ``memories`` row;
                    ``domain`` is non-empty.
    Post-condition: if the row's domain was ``NULL``/``''`` at UPDATE
                    time, it now equals ``domain`` and this returns
                    ``True``. Otherwise the row is untouched (some
                    concurrent writer already gave it a domain) and
                    this returns ``False`` — never overwrites a
                    non-empty domain.
    """
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE memories
                  SET domain = %(domain)s
                WHERE id = %(id)s
                  AND (domain IS NULL OR domain = '')""",
            {"domain": domain, "id": memory_id},
        )
        return cur.rowcount > 0


def tag_memory_orphan(conn: Connection, memory_id: int) -> bool:
    """Append the ``domain-orphan`` tag, but only if the domain is still
    empty and the tag isn't already present.

    Pre-condition:  ``memory_id`` refers to an existing ``memories`` row.
    Post-condition: if the row's domain was ``NULL``/``''`` and its
                    ``tags`` did not already contain ``domain-orphan``,
                    the tag is appended and this returns ``True``. The
                    row's ``domain`` column is left empty — an orphan
                    is a tagged, explicit state, not a fabricated
                    domain value (I6-D3: "domaine sentinelle rejeté").
                    Otherwise (domain non-empty, or tag already present)
                    the row is untouched and this returns ``False``.
    """
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE memories
                  SET tags = tags || %(tag)s::jsonb
                WHERE id = %(id)s
                  AND (domain IS NULL OR domain = '')
                  AND NOT tags @> %(tag)s::jsonb""",
            {"tag": f'["{_ORPHAN_TAG}"]', "id": memory_id},
        )
        return cur.rowcount > 0


__all__ = [
    "list_domainless_memories",
    "update_memory_domain",
    "tag_memory_orphan",
]
