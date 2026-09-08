---
title: "ADR-0323 — mcp_server/doctor_mcp.py rationale"
status: accepted
source: mcp_server/doctor_mcp.py
---

# ADR-0323 — mcp_server/doctor_mcp.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Helps Discord/issue-tracker users diagnose "MCP server failed to start"
without staring at silent errors. Every check reports what command was
attempted and the exact error if it failed — never just "broken."
````

## module — original line 7 (docstring)

````text
Checks performed (in order):
  * Python interpreter — `which python3`, `which python`, `python --version`
  * `~/.claude/plugins/installed_plugins.json` — exists, parses, key
    `hypermnesia-mcp@cortex-plugins` present, installPath valid, launcher present
  * `CLAUDE_PLUGIN_ROOT` env var presence (informational — only set by
    Claude Code at hook/MCP spawn time, normally absent in shells)
  * Launcher smoke probe: spawn the launcher with no module argv and
    assert the usage-and-exit-1 contract.
  * `DATABASE_URL` presence + URL parse
  * PostgreSQL reachable — `SELECT 1` against the configured DSN
  * PostgreSQL extensions — enumerate `vector`, `pg_trgm` via pg_extension
  * Critical Python deps importable (psycopg, pgvector, mcp, pydantic,
    sentence_transformers)
````

## module — original line 21 (docstring)

````text
What we explicitly do NOT check (Feynman discipline — say "I don't know"
when a probe is unreliable):
  * MCP stdio handshake. Spawning the actual server, sending an
    `initialize` JSON-RPC frame, and reading the response is a moving
    target (MCP SDK version, transport buffering, race against the
    server's own dependency-install step in launcher.py). A flaky check
    is worse than no check — it sends users chasing phantom failures.
    Status: not implemented; reported as "I don't know" in --json so the
    consumer knows it was deliberately skipped.
````

## module — original line 31 (docstring)

````text
Output:
  - Human-readable by default (one line per check + actionable fix).
    ANSI colour when stdout is a TTY (green=ok, red=fail, yellow=warn).
  - `--json` flag emits a machine-readable report (Discord-paste friendly).
  - `--copy` flag adds a header that tells users where to paste the output.
````

## module — original line 37 (docstring)

````text
This module is invoked from `cortex-doctor mcp` via `mcp_server.doctor.run`
(the entry point registered in pyproject.toml).
````

## module — original line 40 (docstring)

````text
Source: Discord report 2026-05-09 (MCP server "✘ failed" with no
actionable error). Root cause was a fragile inline `python -c` wrapper in
`.mcp.json` that swallowed launcher startup errors.

````

## McpReport — original line 76 (docstring)

````text
    Data only — deliberately no methods. mutmut's mutation generator
    categorically excludes the body of any `@dataclass`-decorated class
    (`mutmut/mutation/file_mutation.py:236`, confirmed empirically: issue
    #262's 3rd pass, `RepoBadge` in scripts/generate_repo_badges.py), so
    logic placed on methods here would carry zero mutation coverage no
    matter how the test loader names the module. `mcp_report_required_fails`
    / `mcp_report_warnings` / `mcp_report_to_dict` below carry the same
    logic as free functions instead (issue #282).
    
````

## _check_python_interpreter — original line 121 (docstring)

````text
    Source: mcp_server/doctor_mcp.py — Discord triage rule #1.
    
````

## _check_installed_plugins_json — original line 169 (docstring)

````text
    Returns the check + the parsed JSON (or None) so subsequent checks
    can reuse it without re-reading.
    
````

## _check_claude_plugin_root_env — original line 329 (docstring)

````text
    This var is set by Claude Code only at hook/MCP spawn time, so its
    absence from a shell is normal. We report it for completeness — when
    debugging from inside a hook or MCP context, its presence confirms
    Claude Code is doing variable substitution correctly.
    
````

## _check_launcher_smoke — original line 361 (docstring)

````text
    Source: scripts/launcher.py:127-134 (the usage-and-exit-1 branch).
    
````

## _check_pg_reachable — original line 447 (docstring)

````text
    Source: psycopg 3 docs — psycopg.connect(dsn, connect_timeout=...).
    
````

## _check_pg_extensions — original line 506 (docstring)

````text
    Cortex requires both. Source: mcp_server/infrastructure/pg_schema.py
    (CREATE EXTENSION IF NOT EXISTS vector / pg_trgm).
    
````

## _check_critical_imports — original line 570 (docstring)

````text
    Source: scripts/launcher.py:_ensure_deps for the hard list,
    _ensure_all_deps for sentence_transformers (session_start path).
    
````

## _check_optional_imports — original line 602 (docstring)

````text
    Reported as warn (not fail) because the MCP server itself starts
    fine without sentence_transformers — only the SessionStart hook
    needs it. Users hitting "MCP server failed" usually have a hard-dep
    failure; sentence_transformers is informational.
    
````

## _skipped_stdio_handshake — original line 640 (docstring)

````text
    Feynman discipline: a flaky check is worse than no check. We declare
    this skipped explicitly so the consumer of --json knows it's a
    deliberate omission, not a bug.
    
````

## module — original line 214 (comment)

````text
# Print a compact shape summary so the Discord paste is self-contained.
````

## module — original line 377 (comment)

````text
# Never resolve "python3"/"python" by name: on Windows PATH those hit the
# Microsoft Store stub (exit 9009, no interpreter), making this smoke test
# spuriously fail. The launcher must run under THIS interpreter anyway.
# source: RAPPORT_INSTALLATION_CORTEX_WINDOWS.md §5.2
````

## inline — original line 458 (directive-rationale)

````text
# noqa: PLC0415 — optional-feature probe: ImportError here is a handled degraded mode
````

## inline — original line 471 (directive-rationale)

````text
# noqa: BLE001 — diagnostic probe — any failure becomes the check's failure report
````

## module — original line 472 (comment)

````text
# Catch-all here is intentional: psycopg raises a wide variety of
# subclasses (OperationalError, DatabaseError, etc.) and we want
# the precise exception type + message in the report.
# scrub_secrets guards against psycopg OperationalError embedding the
# full DSN (including password) in its message on connection failure.
````

## inline — original line 517 (directive-rationale)

````text
# noqa: PLC0415 — optional-feature probe: ImportError here is a handled degraded mode
````

## inline — original line 529 (directive-rationale)

````text
# noqa: BLE001 — diagnostic probe — any failure becomes the check's failure report
````

## module — original line 530 (comment)

````text
# scrub_secrets guards against psycopg OperationalError embedding the
# full DSN (including password) in its message on connection failure.
````

## module — original line 559 (comment)

````text
# Critical imports the MCP server pulls in at startup. sentence_transformers
# is heavy (downloads ML weights) but session_start hook needs it; we check
# it as warn rather than fail because a non-session-start MCP startup will
# still work without it.
````

## module — original line 682 (comment)

````text
# ANSI codes — only emitted when stdout is a TTY (prevents garbage in
# pipes, files, and Discord pastes; users running interactively still
# see the colour cues).
````
