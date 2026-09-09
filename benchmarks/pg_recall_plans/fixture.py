"""Deterministic SQL-only fixtures; never instantiate an embedding model.

source: ADR-0855"""

from __future__ import annotations

# source: ADR-0855
MIN_ROWS = 30_000
# source: ADR-0855
DIMENSIONS = 384


def vector_sql(first: str = "1", second: str = "0") -> str:
    """A two-coordinate test direction in the production vector dimension."""
    return (
        f"(ARRAY[({first})::real, ({second})::real] || "
        f"array_fill(0::real, ARRAY[{DIMENSIONS - 2}]))::vector"
    )


def load_sql(rows: int) -> str:
    """Populate a dedicated empty database after BenchmarkDB-style cleanup.

    source: ADR-0855
    """
    if type(rows) is not int or rows < MIN_ROWS:
        raise ValueError("fixture row count must be an integer >= W4-1 minimum")
    embedding = vector_sql("i::real", f"{rows}::real")
    return f"""DELETE FROM memories WHERE is_benchmark = TRUE;
INSERT INTO memories (content, embedding, domain, directory_context, source,
    is_benchmark, heat_base, created_at, last_accessed, heat_base_set_at,
    consolidation_stage, emotional_valence, is_global, capture_origin)
SELECT CASE WHEN i % 100 = 0 THEN 'needle target ' ELSE '' END || md5(i::text),
    {embedding}, CASE WHEN i % 2 = 0 THEN 'plans' ELSE 'other' END,
    CASE WHEN i % 3 = 0 THEN '/fixture/a' ELSE '/fixture/b' END,
    CASE WHEN i % 5 = 0 THEN 'lesson' ELSE 'post_tool_capture' END,
    TRUE, (i::real / {rows})::real,
    NOW() - i * INTERVAL '1 hour', NOW() - i * INTERVAL '1 hour',
    NOW() - i * INTERVAL '1 hour',
    (ARRAY['labile','early_ltp','late_ltp','consolidated','reconsolidating'])
        [1 + i % 5], (i % 3 - 1)::real, i % 7 = 0,
    CASE WHEN i % 2 = 0 THEN 'user_explicit' ELSE 'tool_output' END
FROM generate_series(1, {rows}) AS i;
ANALYZE memories;
ANALYZE homeostatic_state;
"""  # noqa: S608 — source: ADR-0855


def recall_sql(name: str, scoped: bool = False, exact_witness: bool = False) -> str:
    """Fixed query grammar; caller supplies only a validated function name.

    source: ADR-0855
    """
    if name not in {"recall_memories", "recall_memories_reference"}:
        raise ValueError("unexpected recall function")
    domain = "'plans'" if scoped else "NULL"
    directory = "'/fixture/a'" if scoped else "NULL"
    # The guaranteed row i=MIN_ROWS has a unique MD5 token. The broad normal
    # query has equal lexical scores at LIMIT; membership there is unspecified.
    query = f"md5('{MIN_ROWS}')" if exact_witness else "'needle target'"
    return f"""SELECT * FROM {name}(
        {query}, {vector_sql()}, p_domain => {domain},
        p_directory => {directory}, p_agent_topic => 'fixture-agent',
        p_trusted_origins => ARRAY['user_explicit'], p_untrusted_factor => 0.0
    )"""  # noqa: S608 — source: ADR-0855
