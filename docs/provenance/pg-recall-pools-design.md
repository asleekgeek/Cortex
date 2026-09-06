# W4-1: independently planned PostgreSQL recall pools

Base: `d0f7c19bf64a2d994b2e9a2a9818244c994bc972`. Scope: F4 in
`tasks/codex-green-remediation-plan.md`; no ranking-policy change.

The filter-only `eligible AS NOT MATERIALIZED` relation exposes the base
indexes to each of the five existing top-K queries. It retains the current
view, preliminary heat_base gate, stale, domain/global and directory gates.
Each pool retains the exact effective_heat predicate **before** its LIMIT.
The vector distance ORDER BY, FTS match and trigram `%` predicate are indexable.
The trigram function-local setting is the existing strict similarity cutoff
0.1, not pg_trgm's session default 0.3. The strict numeric predicate stays.

Only the union of bounded pool IDs is materialized with the memory columns.
Pool size remains max_results × 10; final size remains max_results × 3.
The existing normalized TMM fusion (despite WRRF parameter names), channel
maxima, zero-weight behavior, agent/emotion/tag/confidence/trust boosts,
17-parameter signature, returned columns and provenance are unchanged.
Heat is sorted by effective_heat, never by heat_base: age, protection,
stage and emotional valence make those orderings different. Partial Btrees
on heat_base and created_at DESC use the exact source/stale/supersession
predicate already required by the mechanical pools, including NULL behavior.
The heat sort remains exact and potentially scans the eligible curated set;
the performance target is an empirical acceptance condition, not a claim.

Validation separates SQL equivalence under exact scans from normal ANN
plans. HNSW filtering and omitted zero vectors can change retrieved sets;
strict_order orders found candidates and does not promise exact recall.
The harness records extension versions and GUCs without tuning them. It
loads a deterministic synthetic corpus of at least 30,000 rows into the
retained reproduce.sh container after benchmark cleanup, then ANALYZE,
and captures actual nested function plans using auto_explain. Synthetic
embeddings require no model. Full LongMemEval/LoCoMo floors remain the
parent's isolated reproduce.sh gate; that runner has no BEAM floor.

Sources verified 2026-09-06:
- PostgreSQL 16 [CTE materialization](https://www.postgresql.org/docs/16/queries-with.html#QUERIES-WITH-CTE-MATERIALIZATION)
  permits filter pushdown through NOT MATERIALIZED.
- PostgreSQL 16 [pg_trgm](https://www.postgresql.org/docs/16/pgtrgm.html)
  documents similarity threshold and GIN operator support (bitmap + sort valid).
- PostgreSQL 16 [CREATE FUNCTION](https://www.postgresql.org/docs/16/sql-createfunction.html)
  scopes SET configuration to the function call.
- PostgreSQL 16 [partial indexes](https://www.postgresql.org/docs/16/indexes-partial.html)
  requires the query predicate to imply the index predicate.
- pgvector [Filtering / iterative scans / missing vectors](https://github.com/pgvector/pgvector)
  documents approximate filtering and exclusion of NULL/zero cosine vectors.
- PostgreSQL 16 [auto_explain](https://www.postgresql.org/docs/16/auto-explain.html)
  exposes nested stored-function plans; outer Function Scan alone is insufficient.

No new retrieval constants, model, reranker, decay equation or trust policy.
Existing pg_schema.py size is debt; this bounded diff does not extract it
into a newly oversized module or add a baseline exception.
