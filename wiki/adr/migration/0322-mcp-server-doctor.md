---
title: "ADR-0322 — mcp_server/doctor.py rationale"
status: accepted
source: mcp_server/doctor.py
---

# ADR-0322 — mcp_server/doctor.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Helps users verify Cortex has everything it needs before first
interactive session. The check list is backend-aware
(``active_checks()``): on the zero-config SQLite default the PostgreSQL
driver/connection/extension checks are replaced by a SQLite store-open
check, so a healthy SQLite install reports green instead of four false
failures.
````

## module — original line 10 (docstring)

````text
PostgreSQL backend checks:
  * Python version >= 3.10
  * psycopg + pgvector Python packages import
  * DATABASE_URL reachable, PG >= 15
  * pgvector + pg_trgm extensions installed
  * memories table exists (schema auto-init ran)
  * cache dir ~/.claude/methodology is writable
  * POOL_INTERACTIVE_MAX matches I10 invariant
````

## module — original line 19 (docstring)

````text
SQLite backend checks:
  * Python version >= 3.10
  * SQLite store opens and its schema initializes
  * cache dir ~/.claude/methodology is writable
  * POOL_INTERACTIVE_MAX matches I10 invariant
````

## module — original line 25 (docstring)

````text
Exit 0 on full green. Exit 1 with a numbered list of fixes otherwise.
````

## module — original line 27 (docstring)

````text
Invocation:
    python -m mcp_server.doctor
    hypermnesia-mcp doctor       (once entry point is wired)
````

## module — original line 31 (docstring)

````text
Source: docs/program/phase-5-pool-admission-design.md §7 (marketplace
readiness), I10 invariant.

````

## _codebase_pipeline — original line 211 (docstring)

````text
    Cortex integrates with it to turn codebase analysis into wiki pages +
    memories + KG entities via the ``ingest_codebase`` tool. Not required
    for core memory operations — users who don't do codebase ingestion
    can ignore this check. Gated to ``optional=True`` so doctor still
    exits 0 on its absence.
````

## _sqlite_store — original line 286 (docstring)

````text
    One check replaces the four PG checks (driver, URL, connection,
    extensions): SqliteMemoryStore's constructor runs the DDL +
    migrations, so a successful open proves the whole storage path.
    
````

## active_checks — original line 332 (docstring)

````text
    Resolves the backend exactly like the launcher/hooks do
    (env var, then the installer's backend marker — see
    ``infrastructure.backend_marker.effective_backend``), so doctor
    diagnoses the same store the server would actually open. Any
    resolution failure falls back to the PostgreSQL list — the
    stricter, historical behaviour.
    
````

## run — original line 350 (docstring)

````text
    Subcommands:
      (none)   Full setup verification (Python, PG, extensions, etc.)
      mcp      MCP startup diagnostics (Discord-debug-friendly)
               Flags:
                 --json   Emit machine-readable JSON report
                 --copy   Prepend a "paste me in Discord" header to the
                          human output (useful for issue templates)
    
````

## _run_full_check — original line 368 (docstring)

````text
Full setup verification (legacy `cortex-doctor` behaviour).
````

## inline — original line 90 (directive-rationale)

````text
# noqa: PLC0415, F401 — optional-feature probe: ImportError here is a handled degraded mode
````

## inline — original line 99 (directive-rationale)

````text
# noqa: PLC0415, F401 — optional-feature probe: ImportError here is a handled degraded mode
````

## inline — original line 108 (directive-rationale)

````text
# noqa: PLC0415, F401 — optional-feature probe: ImportError here is a handled degraded mode
````

## inline — original line 133 (directive-rationale)

````text
# noqa: PLC0415 — optional-feature probe: ImportError here is a handled degraded mode
````

## inline — original line 143 (directive-rationale)

````text
# noqa: BLE001 — diagnostic probe — any failure becomes the check's failure report
````

## inline — original line 155 (directive-rationale)

````text
# noqa: PLC0415 — optional-feature probe: ImportError here is a handled degraded mode
````

## inline — original line 180 (directive-rationale)

````text
# noqa: BLE001 — diagnostic probe — any failure becomes the check's failure report
````

## module — original line 190 (comment)

````text
# home_dir() honors $HOME on every OS; Path.expanduser() ignores it on
# Windows. source: RAPPORT_INSTALLATION_CORTEX_WINDOWS.md §5.1
````

## inline — original line 199 (directive-rationale)

````text
# noqa: BLE001 — diagnostic probe — any failure becomes the check's failure report
````

## inline — original line 279 (directive-rationale)

````text
# noqa: BLE001 — diagnostic probe — any failure becomes the check's failure report
````

## inline — original line 298 (directive-rationale)

````text
# noqa: BLE001 — diagnostic probe — any failure becomes the check's failure report
````

## inline — original line 342 (directive-rationale)

````text
# noqa: BLE001 — PG check list is the documented fallback
````
