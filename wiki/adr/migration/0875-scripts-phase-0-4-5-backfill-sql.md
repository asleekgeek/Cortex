---
title: "ADR-0875 — scripts/phase_0_4_5_backfill.sql rationale"
status: accepted
source: scripts/phase_0_4_5_backfill.sql
---

# ADR-0875 — scripts/phase_0_4_5_backfill.sql

Source rationale preserved verbatim. Identifiers inside historical quotations are not current identities.

## scripts/phase_0_4_5_backfill.sql — original line 5

````text
-- Purpose:
--   Repair the I4 undercoverage defect identified by Curie's audit (see
--   docs/invariants/cortex-invariants.md §I4 and docs/program/phase-0.4.5-
--   backfill-design.md). On the darval production store, memory_entities
--   coverage is 0.49% vs the required 99%; 129,670 pairs are missing, of
--   which 91,125 have length(e.name) >= 4 (Option A policy: drop 117 junk
--   entities of length < 4).
````

## scripts/phase_0_4_5_backfill.sql — original line 21

````text
-- Why `enable_seqscan = off` + `enable_material = off` inside this transaction:
--   On the local `cortex` DB (800 memories, 17K entities) the planner prefers
--   a Seq Scan on memories with Materialize (cost estimate ~92k) over the
--   bitmap-index path (cost estimate ~108k). Actual runtimes invert: 217s
--   seq/material vs 6.57s forced-index. The cost model undercounts the
--   penalty of reading 800 × 17K = 13.6M memory rows through the Materialize
--   node because the `content` column averages 3.2 kB per row. Disabling both
--   is scoped to this single transaction; production config is untouched.
````

## scripts/phase_0_4_5_backfill.sql — original line 40

````text
-- Progress:
--   The PL/pgSQL block at the bottom runs the backfill in chunks of 500
--   entities and RAISE NOTICEs after each chunk (so a 66K store run emits
--   ~200 progress messages at roughly 2s intervals). For the one-shot
--   single-statement variant, use section A and skip the chunked block.
````

## scripts/phase_0_4_5_backfill.sql — original line 46

````text
-- -----------------------------------------------------------------------------
-- Benchmark on local `cortex` (800 memories × 17K entities, April 2026):
````

## scripts/phase_0_4_5_backfill.sql — original line 55

````text
-- Extrapolation to 66K memories × 100K entities (darval):
--   Expected candidate memories per entity: heavy-tailed. For the 800-mem
--   sample, avg probe returned 5 candidates (91,765 matches / 16,977 entities
--   = 5.4 pairs/entity). Scaling to 66K memories, k (candidates/probe)
--   grows sub-linearly but heap-fetch cost grows (cold pages):
--     probe_time ≈ bitmap_index_cost + k × heap_fetch_and_recheck
--     total_time ≈ entities × probe_time
--   Projection range: 5-30 minutes one-shot. See design doc §2 for the
--   optimistic (2.5 min) and pessimistic (2.5 h) bounds; plan a 60-minute
--   maintenance window. If runtime exceeds 45 min, kill and switch to
--   Section B chunked variant (500-entity sub-transactions, NOTICE logs).
````

## scripts/phase_0_4_5_backfill.sql — original line 83

````text
-- -----------------------------------------------------------------------------
-- Pre-verification: record the before-state for post-hoc comparison.
-- Run these two SELECTs manually and save the numbers before executing
-- the backfill.  They are not inside the transaction so they commit no
-- state.
-- -----------------------------------------------------------------------------
````

## scripts/phase_0_4_5_backfill.sql — original line 204

````text
--         -- Emit progress every 10K pairs inserted OR every 20 chunks
--         -- (whichever comes first), bounded so low-hit chunks still
--         -- produce telemetry on long runs.
--         IF (inserted / 10000) > ((inserted - chunk_inserted) / 10000)
--            OR total_chunks % 20 = 0 THEN
--             RAISE NOTICE
--                 'phase_0_4_5_backfill: entities up to %, pairs inserted=%',
--                 cur_id, inserted;
--         END IF;
--     END LOOP;
````
