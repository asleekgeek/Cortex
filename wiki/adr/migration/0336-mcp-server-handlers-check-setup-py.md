# ADR-0336: mcp_server/handlers/check_setup.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/check_setup.py`; original SHA-256 `83b1f6c47c36771aaffef1299210faf29e9ac214cd6cc46e44fa1538397ed0cd`.

## Original docstring, lines 1–19

````text
"""Handler: check_setup — MCP facade over mcp_server.doctor's checks.

Runs the exact same check functions as `python -m mcp_server.doctor`
(the plugin-marketplace CLI) and returns them as structured MCP data
instead of console text, mirroring the `check_vision_setup` /
`check_voice_setup` pattern from the cortex-vision / cortex-voice
plugins: call once before first interactive session to confirm the
environment before install day.

No check logic is duplicated here — every entry in doctor's
backend-aware `active_checks()` list is imported and invoked as-is, in
doctor's own dependency order (PostgreSQL backend: Python version -> PG
driver -> DATABASE_URL -> live PG connection -> pgvector/pg_trgm
extensions -> ~/.claude/methodology writability -> I10 pool config ->
optional ai-architect-mcp-codebase probe; SQLite backend: Python version ->
SQLite store open -> writability -> I10 -> pipeline probe). A failure
early in the list explains later ones (e.g. no DATABASE_URL implies no
PG connection), so callers should fix in list order.
"""
````

