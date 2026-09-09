---
title: "ADR-0178 — mcp_server/core/entity_reconciliation.py rationale"
status: accepted
source: mcp_server/core/entity_reconciliation.py
---

# ADR-0178 — mcp_server/core/entity_reconciliation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Curie's I4 audit (docs/invariants/cortex-invariants.md §I4 and
docs/program/phase-0.4.5-backfill-design.md) found two coverage defects:
````

## module — original line 6 (docstring)

````text
1. A one-time undercoverage defect requiring a full backfill
   (`scripts/phase_0_4_5_backfill.sql`).
2. An ongoing "retroactive-entity-orphans" leak: when
   `persist_entities` creates an entity from memory M1 at time t1, no
   code links that entity's name to older memories M0 whose content
   textually contains the same name.
````

## module — original line 13 (docstring)

````text
This module builds the *windowed* maintenance query that closes the
ongoing leak after the one-shot backfill lands. Run it on the
consolidate schedule (daily). Windowing keeps runtime proportional to
recent activity, not to store size.
````

## module — original line 18 (docstring)

````text
Window semantics (both conditions AND'd, NOT OR'd):
  - memory is young enough to still be a likely target of new-entity
    linkage (default 7 days — consistent with LABILE and EARLY_LTP
    cascade stages, pg_schema.py:748-752)
  - entity is young enough that it was possibly introduced after the
    memory existed (default 24 hours — captures the write path's
    entity-creation-after-memory-creation case, but bounds the work).
````

## module — original line 26 (docstring)

````text
Pure business logic. The SQL is returned to a handler / store adapter
that runs it. This module has no PostgreSQL driver dependency.
````

## module — original line 29 (docstring)

````text
References:
  - Clean Architecture (Martin 2017) Ch. 20: the SQL is a policy the
    core owns; execution is an I/O concern of the store.
  - cortex-invariants.md I4 and I9.

````

## build_reconciliation_sql — original line 96 (docstring)

````text
    Postconditions:
      - Returned SQL is an idempotent INSERT ... ON CONFLICT DO NOTHING.
      - Params tuple order matches the %s placeholders, left-to-right:
        (min_name_length, memory_age_days, entity_age_hours).
      - Query is windowed: planner can use idx_memories_created_at and
        idx_entities (no created_at index yet — see design doc §5 risks)
        to bound candidate rows before the trigram probe.
````

## reconcile_leak_ratio — original line 166 (docstring)

````text
    Preconditions:
      - reconciled_pairs >= 0
      - eligible_pairs >= 0
      - reconciled_pairs <= eligible_pairs  (cannot insert more than the
        window contains; violation indicates a counting bug)
````

## reconcile_leak_ratio — original line 181 (docstring)

````text
    Rationale for the 1% threshold: on a healthy system, the write path
    catches entities present at memory-write time, and reconcile catches
    only the retroactive-orphan case (new entity → older memory). On a
    66K store with <100 new entities/day and <1K new memories/day, the
    retroactive set is bounded; 1% of the 7d × 24h window's eligible
    pairs is an empirical upper bound for that case. Exceeding it is a
    signal, not a proof — a confirmation test needs RCA per Move 4.
    
````

## module — original line 37 (comment)

````text
# ── Defaults ──────────────────────────────────────────────────────────────
#
# Source: chosen to be no larger than the cascade's LABILE+EARLY_LTP
# window so the reconcile job bounds work to memories that are still
# capable of being re-tagged during consolidation. See
# pg_schema.py:748-752 (decay_memories alpha exponents) and Kandel (2001)
# on consolidation windows. 7 days matches the dominant stage transition
# timeline for episodic memories.
````

## module — original line 51 (comment)

````text
# ── SQL templates ─────────────────────────────────────────────────────────
#
# Both queries embed the same trigram-accelerated join shape proven in
# `scripts/phase_0_4_5_backfill.sql`. The windowed version additionally
# constrains `m.created_at` and `e.created_at`, so the planner's
# candidate-memory set is small enough to not require the session-scoped
# `enable_seqscan = off` trick that the full backfill uses.
````

## module — original line 204 (comment)

````text
# ── Leak threshold constant ───────────────────────────────────────────────
#
# Source: empirical upper bound for the retroactive-entity-orphan rate on
# the darval 66K store (see design doc §6). Above this, the write path is
# demonstrably leaking. Below this, reconcile is serving its intended
# maintenance role. Not a magic number — it's the contract boundary
# between "working as designed" and "investigate now".
````
