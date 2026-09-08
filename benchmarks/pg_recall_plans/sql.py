"""Compose the plan experiment from production DDL and the frozen reference."""

from __future__ import annotations

from pathlib import Path

from benchmarks.pg_recall_plans.fixture import load_sql, recall_sql
from mcp_server.infrastructure.pg_schema import get_all_ddl

# source: W4-1 adds only these two indexes; the baseline phase excludes them.
NEW_INDEXES = (
    "idx_memories_curated_heat_base",
    "idx_memories_curated_created_at",
)
# source: remediation plan §3's four/first-discarded protocol, explicitly
# extended to this PG experiment by the W4-1 harness review request.
REPETITIONS = (1, 2, 3, 4)


def case_labels(phase: str) -> list[str]:
    """Publish the execution order; each mode repeats global then scoped."""
    return [
        f"{phase}-{mode}-{scope}-r{repetition}"
        for mode in ("normal", "exact")
        for repetition in REPETITIONS
        for scope in ("global", "scoped")
    ]


def reference_sql() -> str:
    return Path(__file__).with_name("reference.sql").read_text()


def phase_sql(phase: str) -> str:
    """Collect normal plans plus an exact-scan semantic control, without tuning ANN."""
    if phase not in {"before", "after"}:
        raise ValueError("unexpected experiment phase")
    function = "recall_memories_reference" if phase == "before" else "recall_memories"
    statements = []
    for label in case_labels(phase):
        _, mode, scope, _ = label.split("-")
        scan = "on" if mode == "normal" else "off"
        statements.append(f"SET LOCAL enable_indexscan = {scan};")
        statements.append(f"SET LOCAL enable_bitmapscan = {scan};")
        query = recall_sql(function, scope == "scoped", exact_witness=mode == "exact")
        statements.append(
            f"SELECT json_build_object('case', '{label}', 'rows', "  # noqa: S608 — phase allowlist, fixed mode/scope and query grammar
            f"COALESCE(json_agg(r), '[]'::json)) FROM ({query}) r;"
        )
    return "\n".join(statements)


def metadata_sql() -> str:
    """Record the actual fixture cardinality and transaction clock before plans."""
    return "\n".join(
        [
            "SELECT json_build_object('experiment', json_build_object("
            "'fixture_rows', (SELECT count(*) FROM memories), 'snapshot_now', NOW()));",
            "SELECT json_build_object('server', version(), 'vector', extversion) "
            "FROM pg_extension WHERE extname = 'vector';",
            "SELECT json_object_agg(extname, extversion) FROM pg_extension;",
            "SELECT json_object_agg(name, setting) FROM pg_settings "
            "WHERE name LIKE 'hnsw.%' OR name LIKE 'pg_trgm.%' "
            "OR name IN ('work_mem', 'plan_cache_mode', 'random_page_cost', "
            "'enable_indexscan', 'enable_bitmapscan', "
            "'max_parallel_workers_per_gather');",
        ]
    )


def experiment_sql(rows: int) -> str:
    """One transaction fixes NOW() for both versions and all heat calculations."""
    ddl = get_all_ddl()
    added = [s for s in ddl if any(name in s for name in NEW_INDEXES)]
    initial = [s for s in ddl if s not in added]
    return "\n".join(
        [
            "BEGIN;",
            *initial,
            reference_sql(),
            load_sql(rows),
            metadata_sql(),
            "LOAD 'auto_explain';",
            # source: PostgreSQL 16 auto_explain documentation. Zero logs all
            # statements, including nested function plans; NOTICE returns them
            # to psql stderr as well as the container log.
            "SET LOCAL auto_explain.log_min_duration = 0;",
            "SET LOCAL auto_explain.log_analyze = on;",
            "SET LOCAL auto_explain.log_buffers = on;",
            "SET LOCAL auto_explain.log_nested_statements = on;",
            "SET LOCAL auto_explain.log_format = json;",
            "SET LOCAL auto_explain.log_level = notice;",
            phase_sql("before"),
            *added,
            *added,  # Exercise IF NOT EXISTS idempotence in the isolated DB.
            "ANALYZE memories;",
            phase_sql("after"),
            "COMMIT;",
        ]
    )
