-- =============================================================================
-- Phase 0.4.5 — memory_entities trigram-accelerated backfill
-- =============================================================================
--
-- source: ADR-0875






--
-- Strategy:
--   Entity-driven nested loop with bitmap-index probes against
--   idx_memories_content_trgm (GIN gin_trgm_ops). For each eligible
--   entity, the pg_trgm index returns the candidate memories whose
--   content contains the entity's name as a substring; the heap recheck
--   applies ILIKE precisely. This is O(entities × avg_candidates_per_probe)
--   not O(entities × memories).
--
-- source: ADR-0875







--
-- Idempotency:
--   `ON CONFLICT (memory_id, entity_id) DO NOTHING` guarantees that
--   concurrent `persist_entities` writes (write-time I9 path) and repeated
--   runs of this script are both safe. The composite PK does the work.
--
-- Timeouts:
--   SET LOCAL statement_timeout = '1h'  -- backfill window on 66K store
--   SET LOCAL lock_timeout = '5s'       -- fail fast if concurrent DDL
--   Both are local to this transaction; they do not modify postgresql.conf.
--
-- source: ADR-0875




--
-- source: ADR-0875

--
--   Naive single-statement (planner default):     217.5 s   (plan A below)
--   Forced bitmap-index single-statement:           6.57 s  (plan A, forced)
--   Chunked PL/pgSQL (section B, 500/chunk):        6.63 s  (35 chunks × ~190ms)
--   Tuples inserted: 91,125  (matches Curie audit's eligible-pairs count)
--   Conflicting tuples: 640  (the write-time persist_entities baseline)
--
-- source: ADR-0875










--
-- Plan evidence (saved here for auditability):
--
--   Without forcing (seq+materialize):
--     Nested Loop (cost=0..92663, rows=22988) actual=217527ms rows=91765
--       -> Seq Scan on entities e (rows=16977)
--       -> Materialize (loops=16977, rows=800 each)   [the cost trap]
--
--   With `enable_seqscan=off, enable_material=off`:
--     Nested Loop actual=6660ms rows=91765
--       -> Seq Scan on entities e (rows=16977)
--       -> Bitmap Heap Scan on memories m (loops=16977, rows=5 avg)
--            Recheck Cond: content ~~* ('%' || e.name || '%')
--            -> Bitmap Index Scan on idx_memories_content_trgm (rows=13 avg)
--
-- =============================================================================

-- source: ADR-0875






-- Before-coverage: how many pairs exist today?
--   SELECT COUNT(*) AS me_before FROM memory_entities;
--
-- Eligible pairs (expected lower bound on after-count, minus current):
--   SELECT COUNT(*) AS eligible FROM entities e JOIN memories m
--     ON m.content ILIKE '%' || e.name || '%'
--    WHERE length(e.name) >= 4 AND NOT e.archived;
--
-- Before-cardinality of entities / memories:
--   SELECT (SELECT COUNT(*) FROM entities)  AS n_entities,
--          (SELECT COUNT(*) FROM memories)  AS n_memories;

-- =============================================================================
-- Section A — one-shot single-statement backfill (preferred on stores
-- where the 1h statement_timeout is comfortable, i.e. local `cortex` and
-- anything up to ~200K memories).
-- =============================================================================

BEGIN;

SET LOCAL statement_timeout = '1h';
SET LOCAL lock_timeout      = '5s';
SET LOCAL enable_seqscan    = off;
SET LOCAL enable_material   = off;

-- Explanatory audit line — lands in pg_stat_activity during execution.
SET LOCAL application_name = 'cortex_phase_0_4_5_backfill';

INSERT INTO memory_entities (memory_id, entity_id)
SELECT m.id, e.id
FROM   entities e
JOIN   memories m
  ON   m.content ILIKE '%' || e.name || '%'
WHERE  length(e.name) >= 4
  AND  NOT e.archived
ON CONFLICT (memory_id, entity_id) DO NOTHING;

COMMIT;

-- -----------------------------------------------------------------------------
-- Post-verification — same shape as pre-verification. The delta is the
-- number of pairs this backfill repaired.
-- -----------------------------------------------------------------------------

-- SELECT COUNT(*) AS me_after FROM memory_entities;
--
-- Coverage percentage against the Curie eligibility predicate:
--   SELECT
--     ROUND(100.0 * covered / eligible, 2) AS coverage_pct,
--     covered, eligible
--   FROM (
--     SELECT
--       (SELECT COUNT(*)
--          FROM entities e
--          JOIN memories m ON m.content ILIKE '%' || e.name || '%'
--          JOIN memory_entities me
--            ON me.memory_id = m.id AND me.entity_id = e.id
--         WHERE length(e.name) >= 4 AND NOT e.archived) AS covered,
--       (SELECT COUNT(*)
--          FROM entities e
--          JOIN memories m ON m.content ILIKE '%' || e.name || '%'
--         WHERE length(e.name) >= 4 AND NOT e.archived) AS eligible
--   ) t;

-- =============================================================================
-- Section B — chunked PL/pgSQL backfill (for stores where a single
-- transaction risks timing out or holding locks too long).  Each chunk
-- is its own sub-transaction via EXCEPTION handling.  Emits a NOTICE every
-- 500 entities processed.
--
-- To use section B: comment out Section A above and uncomment the DO block.
-- Both sections are idempotent; running B after A is a no-op beyond the
-- re-verification scan cost.
-- =============================================================================

-- DO $BODY$
-- DECLARE
--     chunk_size   CONSTANT INTEGER := 500;
--     cur_id       INTEGER := 0;
--     max_id       INTEGER;
--     inserted     BIGINT  := 0;
--     chunk_inserted BIGINT;
--     total_chunks INTEGER := 0;
-- BEGIN
--     SET LOCAL enable_seqscan  = off;
--     SET LOCAL enable_material = off;
--     SET LOCAL lock_timeout    = '5s';
--
--     SELECT MAX(id) INTO max_id FROM entities;
--     IF max_id IS NULL THEN
--         RAISE NOTICE 'entities table is empty; nothing to backfill';
--         RETURN;
--     END IF;
--
--     RAISE NOTICE 'starting chunked backfill: max_entity_id=%, chunk_size=%',
--                  max_id, chunk_size;
--
--     WHILE cur_id <= max_id LOOP
--         INSERT INTO memory_entities (memory_id, entity_id)
--         SELECT m.id, e.id
--         FROM   entities e
--         JOIN   memories m
--           ON   m.content ILIKE '%' || e.name || '%'
--         WHERE  e.id > cur_id
--           AND  e.id <= cur_id + chunk_size
--           AND  length(e.name) >= 4
--           AND  NOT e.archived
--         ON CONFLICT (memory_id, entity_id) DO NOTHING;
--
--         GET DIAGNOSTICS chunk_inserted = ROW_COUNT;
--         inserted := inserted + chunk_inserted;
--         total_chunks := total_chunks + 1;
--         cur_id := cur_id + chunk_size;
--
-- source: ADR-0875









--
--     RAISE NOTICE 'phase_0_4_5_backfill done: % pairs inserted across % chunks',
--                  inserted, total_chunks;
-- END;
-- $BODY$;
