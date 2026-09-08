"""Exact-scan semantic contract; ANN plans are a separate 30k-row experiment.

All rows/functions live in a rollback-only transaction on the test database.
Numbers are fixture inputs covering the W4-1 boundary cases, not tuning.
"""

from __future__ import annotations

import os

import pytest

psycopg = pytest.importorskip("psycopg")

from benchmarks.pg_recall_plans.evidence import compare_rows  # noqa: E402
from benchmarks.pg_recall_plans.fixture import DIMENSIONS  # noqa: E402
from benchmarks.pg_recall_plans.sql import reference_sql  # noqa: E402
from tests_py.conftest import _USE_PG  # noqa: E402

pytestmark = pytest.mark.skipif(not _USE_PG, reason="requires isolated PostgreSQL")


@pytest.fixture
def conn():
    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        connection.execute(reference_sql())
        connection.execute("SET LOCAL enable_indexscan = off")
        connection.execute("SET LOCAL enable_bitmapscan = off")
        try:
            yield connection
        finally:
            connection.rollback()


def embedding(first=1, second=0):
    return str([first, second] + [0] * (DIMENSIONS - 2))


def insert(conn, **overrides):
    from psycopg import sql

    fields = {
        "content": "fixture needle",
        "embedding": embedding(),
        "domain": "w4-fixture",
        "source": "lesson",
        "heat_base": 0.8,
        "no_decay": True,
        "is_benchmark": True,
    } | overrides
    statement = sql.SQL("INSERT INTO memories ({}) VALUES ({}) RETURNING id").format(
        sql.SQL(",").join(map(sql.Identifier, fields)),
        sql.SQL(",").join(sql.Placeholder() for _ in fields),
    )
    return conn.execute(statement, list(fields.values())).fetchone()[0]


def recall(conn, function, options):
    from psycopg import sql
    from psycopg.rows import dict_row

    values = {
        "p_query_text": "needle",
        "p_query_emb": embedding(),
        "p_domain": "w4-fixture",
        "p_include_globals": False,
    } | options
    # source: both SQL signatures declare weights/heat/trust as REAL;
    # psycopg adapts Python float to float8, which overload lookup won't narrow.
    args = sql.SQL(", ").join(
        sql.SQL("{} => {}").format(
            sql.Identifier(name),
            sql.Placeholder() + sql.SQL("::real")
            if isinstance(value, float)
            else sql.Placeholder(),
        )
        for name, value in values.items()
    )
    statement = sql.SQL("SELECT * FROM {}({})").format(sql.Identifier(function), args)
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(statement, list(values.values()))
        return cursor.fetchall()


def equivalent(conn, **options):
    before = recall(conn, "recall_memories_reference", options)
    after = recall(conn, "recall_memories", options)
    comparison = compare_rows(before, after)
    assert comparison["rows_equal"], comparison
    return after


@pytest.mark.parametrize(
    "stage", ["labile", "early_ltp", "late_ltp", "consolidated", "reconsolidating"]
)
@pytest.mark.parametrize("valence", [-1.0, 0.0, 1.0])
def test_ages_stages_valence_and_protection(conn, stage, valence):
    for age in ("1 hour", "30 days", "365 days"):
        anchor = conn.execute("SELECT NOW() - %s::interval", (age,)).fetchone()[0]
        insert(
            conn,
            no_decay=False,
            consolidation_stage=stage,
            emotional_valence=valence,
            created_at=anchor,
            heat_base_set_at=anchor,
            last_accessed=anchor,
        )
    insert(conn, is_protected=True, no_decay=False, heat_base=0.2)
    insert(conn, no_decay=True, heat_base=0.7)
    equivalent(
        conn, p_w_vector=0.0, p_w_fts=0.0, p_w_ngram=0.0, p_w_heat=1.0, p_w_recency=1.0
    )


def test_trigram_between_point_one_and_session_default(conn):
    text = "needle abcdefghijklmnopqrstuvwxyz"
    similarity = conn.execute("SELECT similarity(%s, 'needle')", (text,)).fetchone()[0]
    assert 0.1 < similarity < 0.3
    identity = insert(conn, content=text, embedding=None, source="post_tool_capture")
    conn.execute("SET LOCAL pg_trgm.similarity_threshold = '0.3'")
    rows = equivalent(conn, p_w_vector=0.0, p_w_fts=0.0, p_w_heat=0.0, p_w_ngram=1.0)
    assert [row["memory_id"] for row in rows] == [identity]
    assert float(conn.execute("SHOW pg_trgm.similarity_threshold").fetchone()[0]) == 0.3


def test_function_plan_policy_does_not_change_the_callers_setting(conn):
    insert(conn, content="needle", embedding=None)
    conn.execute("SET LOCAL plan_cache_mode = force_generic_plan")
    equivalent(conn, p_w_vector=0.0)
    assert conn.execute("SHOW plan_cache_mode").fetchone()[0] == "force_generic_plan"


def test_filters_precede_top_k_and_agent_is_only_a_boost(conn):
    for i in range(12):
        insert(conn, embedding=embedding(100, i), domain="excluded")
        insert(conn, embedding=embedding(100, i), is_stale=True)
        insert(conn, embedding=embedding(100, i), heat_base=0.01)
        insert(conn, embedding=embedding(100, i), directory_context="excluded")
    valid = [
        insert(
            conn,
            embedding=embedding(1, i),
            content="unrelated",
            source="post_tool_capture",
            directory_context="/valid",
        )
        for i in range(1, 12)
    ]
    rows = equivalent(
        conn,
        p_max_results=1,
        p_directory="/valid",
        p_agent_topic="other",
        p_w_vector=1.0,
        p_w_fts=0.0,
        p_w_ngram=0.0,
        p_w_heat=0.0,
    )
    assert [row["memory_id"] for row in rows] == valid[:3]


def test_heat_pool_boundary_uses_effective_heat_not_heat_base(conn):
    anchor = conn.execute("SELECT NOW() - INTERVAL '30 days'").fetchone()[0]
    for index in range(12):
        insert(
            conn,
            content="unrelated",
            embedding=None,
            no_decay=False,
            heat_base=0.9 - index / 100,
            consolidation_stage="consolidated",
            created_at=anchor,
            heat_base_set_at=anchor,
            last_accessed=anchor,
        )
    fresh = insert(conn, content="unrelated", embedding=None, heat_base=0.5)
    rows = equivalent(
        conn,
        p_max_results=1,
        p_w_vector=0.0,
        p_w_fts=0.0,
        p_w_ngram=0.0,
        p_w_heat=1.0,
        p_w_recency=0.0,
    )
    assert rows[0]["memory_id"] == fresh


@pytest.mark.parametrize("include_globals", [False, True])
def test_global_domain_directory_and_null_source(conn, include_globals):
    local = insert(conn, directory_context="/valid")
    global_id = insert(
        conn, domain="elsewhere", is_global=True, directory_context="/valid"
    )
    insert(conn, domain="elsewhere", is_global=False, directory_context="/valid")
    insert(conn, is_global=True, directory_context="/excluded")
    null_id = insert(
        conn,
        source=None,
        embedding=None,
        content="unrelated",
        directory_context="/valid",
    )
    rows = equivalent(conn, p_directory="/valid", p_include_globals=include_globals)
    identities = {row["memory_id"] for row in rows}
    assert local in identities and null_id not in identities
    assert (global_id in identities) == include_globals


@pytest.mark.parametrize("query", [None, embedding(0, 0), embedding()])
def test_null_zero_vectors_and_zero_weights(conn, query):
    insert(conn, embedding=None)
    insert(conn, embedding=embedding(0, 0))
    insert(conn, embedding=embedding(1, 1))
    equivalent(
        conn,
        p_query_emb=query,
        p_w_vector=0.0,
        p_w_fts=0.0,
        p_w_ngram=0.0,
        p_w_heat=0.0,
        p_w_recency=0.0,
    )


def test_trust_supersession_and_document_priors(conn):
    head = insert(
        conn,
        capture_origin="user_explicit",
        agent_context="agent",
        tags='["instruction"]',
        emotional_valence=1.0,
        confidence=0.9,
        source_attribution="fixture-provenance",
    )
    old = insert(conn, superseded_by_id=head, capture_origin="user_explicit")
    hostile = insert(conn, capture_origin="tool_output", confidence=1.0)
    rows = equivalent(
        conn,
        p_agent_topic="agent",
        p_intent="instruction",
        p_trusted_origins=["user_explicit"],
        p_untrusted_factor=0.0,
    )
    by_id = {row["memory_id"]: row for row in rows}
    assert old not in by_id
    assert by_id[hostile]["score"] == 0.0
    assert rows[0]["memory_id"] == head
    assert by_id[head]["source_attribution"] == "fixture-provenance"
