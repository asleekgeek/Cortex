"""Integration tests for infrastructure.pg_store_near_dup (I6-D2, INC6.4).

Live-PG tests, same skip convention as
``tests_py/handlers/consolidation/test_memory_dedup_exact_pass.py``.
Uses hand-crafted unit vectors (dimension matches ``EMBEDDING_DIM``, 384)
so pairwise cosine similarity is exactly controlled rather than depending
on a real embedding model.
"""

from __future__ import annotations

import json
import uuid

import pytest

from mcp_server.infrastructure.memory_config import get_memory_settings
from mcp_server.infrastructure.memory_store import get_shared_store
from mcp_server.infrastructure.pg_store_near_dup import (
    fetch_contents,
    fetch_member_stats,
    list_candidate_pairs,
)

EMBEDDING_DIM = 384


def _store():
    s = get_memory_settings()
    return get_shared_store(s.DB_PATH, s.EMBEDDING_DIM)


def _pg_only():
    store = _store()
    if not hasattr(store, "batch_pool"):
        pytest.skip("pg_store_near_dup requires a PostgreSQL store")
    return store


def _unit_vector(nonzero_index: int, tiny_noise: float = 0.0) -> list[float]:
    """A 384-dim one-hot-ish unit vector, optionally perturbed slightly
    (still normalized close to 1) so cosine similarity between two
    vectors built from DIFFERENT indices is exactly controllable."""
    v = [0.0] * EMBEDDING_DIM
    v[nonzero_index] = 1.0
    if tiny_noise:
        v[(nonzero_index + 1) % EMBEDDING_DIM] = tiny_noise
    return v


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(repr(x) for x in values) + "]"


def _unique_content(label: str) -> str:
    return f"I6-D2 near-dup test [{label}] {uuid.uuid4().hex}"


def _insert(
    conn, *, content: str, embedding: list[float], heat_base: float = 0.5
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO memories
                   (content, embedding, tags, source, heat_base, no_decay)
               VALUES (%(content)s, %(embedding)s::vector, %(tags)s::jsonb,
                       'test', %(heat_base)s, TRUE)
               RETURNING id""",
            {
                "content": content,
                "embedding": _vector_literal(embedding),
                "tags": json.dumps([]),
                "heat_base": heat_base,
            },
        )
        return cur.fetchone()["id"]


class TestListCandidatePairs:
    def test_near_identical_vectors_form_a_candidate_pair(self):
        store = _pg_only()
        # Two vectors along the same axis (index 7): cosine similarity 1.0.
        vec = _unit_vector(7)
        with store.batch_pool.connection() as conn:
            id_a = _insert(conn, content=_unique_content("identical-a"), embedding=vec)
            id_b = _insert(conn, content=_unique_content("identical-b"), embedding=vec)
            conn.commit()
        try:
            with store.batch_pool.connection() as conn:
                pairs = list_candidate_pairs(conn, top_k=10, min_similarity=0.75)
            matched = [p for p in pairs if {p.id_a, p.id_b} == {id_a, id_b}]
            assert len(matched) == 1
            assert matched[0].similarity == pytest.approx(1.0, abs=1e-4)
        finally:
            with store.batch_pool.connection() as conn:
                conn.execute("DELETE FROM memories WHERE id = ANY(%s)", ([id_a, id_b],))
                conn.commit()

    def test_orthogonal_vectors_are_not_a_candidate_pair(self):
        store = _pg_only()
        with store.batch_pool.connection() as conn:
            id_a = _insert(
                conn, content=_unique_content("orthogonal-a"), embedding=_unit_vector(0)
            )
            id_b = _insert(
                conn,
                content=_unique_content("orthogonal-b"),
                embedding=_unit_vector(100),
            )
            conn.commit()
        try:
            with store.batch_pool.connection() as conn:
                pairs = list_candidate_pairs(conn, top_k=10, min_similarity=0.75)
            matched = [p for p in pairs if {p.id_a, p.id_b} == {id_a, id_b}]
            assert matched == []
        finally:
            with store.batch_pool.connection() as conn:
                conn.execute("DELETE FROM memories WHERE id = ANY(%s)", ([id_a, id_b],))
                conn.commit()

    def test_pair_ids_are_ordered_id_a_less_than_id_b(self):
        store = _pg_only()
        vec = _unit_vector(13)
        with store.batch_pool.connection() as conn:
            id_a = _insert(conn, content=_unique_content("order-a"), embedding=vec)
            id_b = _insert(conn, content=_unique_content("order-b"), embedding=vec)
            conn.commit()
        try:
            with store.batch_pool.connection() as conn:
                pairs = list_candidate_pairs(conn, top_k=10, min_similarity=0.75)
            matched = [p for p in pairs if {p.id_a, p.id_b} == {id_a, id_b}]
            assert len(matched) == 1
            assert matched[0].id_a == min(id_a, id_b)
            assert matched[0].id_b == max(id_a, id_b)
        finally:
            with store.batch_pool.connection() as conn:
                conn.execute("DELETE FROM memories WHERE id = ANY(%s)", ([id_a, id_b],))
                conn.commit()


class TestFetchContents:
    def test_returns_content_for_present_ids_only(self):
        store = _pg_only()
        content = _unique_content("fetch-contents")
        with store.batch_pool.connection() as conn:
            mid = _insert(conn, content=content, embedding=_unit_vector(20))
            conn.commit()
        try:
            with store.batch_pool.connection() as conn:
                result = fetch_contents(conn, [mid, mid + 10_000_000])
            assert result == {mid: content}
        finally:
            with store.batch_pool.connection() as conn:
                conn.execute("DELETE FROM memories WHERE id = %s", (mid,))
                conn.commit()

    def test_empty_ids_returns_empty_dict(self):
        store = _pg_only()
        with store.batch_pool.connection() as conn:
            assert fetch_contents(conn, []) == {}


class TestFetchMemberStats:
    def test_returns_effective_heat_and_created_at(self):
        """Root cause (CI run 29109251545, 2026-07-10): this test used to
        assert effective_heat == heat_base (0.42) unconditionally. That is
        only true when the row's domain has a neutral (1.0) homeostatic
        factor — fetch_member_stats's SQL joins
        ``COALESCE(homeostatic_state.factor, 1.0)`` per domain
        (pg_store_near_dup.py), and that factor is real, mutable, per-
        domain server state, not a test-local constant. A same-session
        handler test (test_consolidate.py, real store) can leave a
        non-1.0 factor for the empty-string domain (conftest.py's
        ``homeostatic_state`` cleanup gap, now closed) — reproduced
        deterministically: 0.42 * 0.9409 == 0.395178, byte-for-byte the
        value CI observed. Fix: probe the SAME live factor
        ``fetch_member_stats`` reads (via ``store.get_homeostatic_factor``,
        the canonical accessor, pg_store.py) and assert against the
        derived expectation instead of a hardcoded constant — same
        "probe, don't predict" pattern as INC6.6
        (core/memory_reheat.py::compute_reheat_target). ``no_decay=TRUE``
        at insert (see ``_insert``) makes this structurally exact: the
        protected branch of ``effective_heat()`` is
        ``LEAST(1.0, GREATEST(0.0, heat_base * factor))`` with no time
        term, so the only free variable is the per-domain factor — no
        clock dependency remains once that is probed rather than assumed.
        """
        store = _pg_only()
        with store.batch_pool.connection() as conn:
            mid = _insert(
                conn,
                content=_unique_content("member-stats"),
                embedding=_unit_vector(30),
                heat_base=0.42,
            )
            conn.commit()
            domain_row = conn.execute(
                "SELECT domain FROM memories WHERE id = %s", (mid,)
            ).fetchone()
        domain = (domain_row["domain"] if domain_row else "") or ""
        factor = store.get_homeostatic_factor(domain)
        expected_effective_heat = min(1.0, max(0.0, 0.42 * factor))
        try:
            with store.batch_pool.connection() as conn:
                stats = fetch_member_stats(conn, [mid])
            assert mid in stats
            assert stats[mid]["effective_heat"] == pytest.approx(
                expected_effective_heat, abs=1e-3
            )
            assert stats[mid]["created_at"] is not None
        finally:
            with store.batch_pool.connection() as conn:
                conn.execute("DELETE FROM memories WHERE id = %s", (mid,))
                conn.commit()

    def test_empty_ids_returns_empty_dict(self):
        store = _pg_only()
        with store.batch_pool.connection() as conn:
            assert fetch_member_stats(conn, []) == {}
