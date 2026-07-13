"""Standalone schema-migration entry point for Cortex.

Applies Cortex's PostgreSQL schema (``pg_schema.get_all_ddl()``) via the
exact same hash-gated, advisory-lock-serialized path
``PgMemoryStore._init_schema`` runs at construction — this module never
re-derives the DDL set or the migration algorithm, it only decides
*whether a migration happened* so it can report an accurate summary line,
using the read-only helpers ``pg_store.compute_ddl_hash`` /
``pg_store.read_schema_hash`` (the same functions ``_init_schema`` itself
calls).

Exists so a caller can force a schema migration WITHOUT booting the full
MCP server (FastMCP, the sentence-transformers embedding model, tool
registries) — e.g. the cortex-viz plugin, which detects an old schema
from its read-only PG connection and needs a lightweight way to bring it
current.

Invocation:
    python3 -m mcp_server.migrate

DATABASE_URL resolution is identical to the MCP server's — both call
``mcp_server.infrastructure.pg_store._get_database_url()``, so this entry
point and the server never disagree on which database they're pointed
at (env ``DATABASE_URL``, falling back to the packaged default
``postgresql://127.0.0.1:5432/cortex``).

Contract (frozen — consumed by the cortex-viz plugin):
    DATABASE_URL=<url> python3 -m mcp_server.migrate
    exit 0  -> schema already at the code's revision, or successfully
               migrated to it. stdout carries exactly one summary line:
                 "cortex-migrate: schema up to date"
                 "cortex-migrate: applied N statements"
    exit 1  -> migration failed. stderr carries a one-line reason.
               No corrupted state is left: every statement in
               get_all_ddl() is independently idempotent (CREATE TABLE
               IF NOT EXISTS, CREATE OR REPLACE FUNCTION, guarded
               ALTER TABLE ADD COLUMN — see pg_schema.py), and
               _init_schema logs+skips any single statement that fails
               rather than aborting, so re-running this entry point
               after a failure is always safe.

Not a single PostgreSQL transaction: get_all_ddl() contains no
transaction-hostile statements (no CREATE INDEX CONCURRENTLY — verified
against pg_schema.py), so each DDL statement commits independently under
autocommit, exactly as PgMemoryStore._init_schema already does. Atomicity
is provided by idempotence + the advisory lock (_SCHEMA_LOCK_ID in
pg_store.py), not by a wrapping transaction — a partial apply is safe to
resume because a second run reapplies every statement and every
statement tolerates being re-run.
"""

from __future__ import annotations

import sys


def _run() -> int:
    """Resolve DATABASE_URL, connect, and migrate schema to the code's revision.

    Pre: none required from the caller; DATABASE_URL is optional (see
    module docstring for the resolution order).
    Post: exactly one line printed to stdout on success (return 0), or
    exactly one line to stderr on failure (return 1). Never raises —
    every exception is caught and mapped to the frozen exit contract.
    """
    import psycopg

    from mcp_server.infrastructure.pg_schema import get_all_ddl
    from mcp_server.infrastructure.pg_store import (
        PgMemoryStore,
        _get_database_url,
        compute_ddl_hash,
        read_schema_hash,
    )

    url = _get_database_url()
    target_hash = compute_ddl_hash()

    # Read the pre-migration state on our own short-lived probe connection
    # (never PgMemoryStore's, which we haven't constructed yet) so the
    # "up to date" vs. "applied" report reflects what was true BEFORE this
    # process touched the DB — read_schema_hash is the same read
    # _init_schema itself performs, just invoked before construction.
    try:
        from psycopg.rows import dict_row

        with psycopg.connect(
            url, connect_timeout=10, autocommit=True, row_factory=dict_row
        ) as probe:
            was_current = read_schema_hash(probe) == target_hash
    except Exception as exc:
        print(f"cortex-migrate: cannot connect to database: {exc}", file=sys.stderr)
        return 1

    store: PgMemoryStore | None = None
    try:
        # Constructing PgMemoryStore IS the migration: __init__ calls
        # _init_schema(), which applies get_all_ddl() under the advisory
        # lock iff the recorded hash is stale. Single source of truth —
        # this module never re-applies DDL itself.
        store = PgMemoryStore(database_url=url)
    except Exception as exc:
        print(f"cortex-migrate: schema migration failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if store is not None:
            store.close()

    if was_current:
        print("cortex-migrate: schema up to date")
    else:
        print(f"cortex-migrate: applied {len(get_all_ddl())} statements")
    return 0


def main() -> int:
    return _run()


if __name__ == "__main__":
    sys.exit(main())
