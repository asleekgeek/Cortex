---
title: "ADR-0156 — mcp_server/core/decay_cycle.py rationale"
status: accepted
source: mcp_server/core/decay_cycle.py
---

# ADR-0156 — mcp_server/core/decay_cycle.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Memory heat decay is **not** computed here. It is computed lazily at
read time by the ``effective_heat()`` PL/pgSQL function
(``mcp_server/infrastructure/pg_schema.py``), which applies the
stage-adjusted Ebbinghaus law and the consolidation-dependent
permastore floor server-side. This module retained an eager, per-row
Python decay path (including an alternative ACT-R base-level model)
until the A3 migration moved memory decay to the SQL side; both were
removed as dead code (zero production callers since that migration —
see issue #346) rather than kept as inert reference implementations,
per coding-standards.md §9 ("if it's built, it must be called").
History: `git show b9997157` (the migration commit) and
`docs/program/phase-3-a3-migration-design.md` §6 ("Decay cycle
post-A3 — DELETE") record the decision and its rationale.
````

## module — original line 17 (docstring)

````text
What remains is **entity** heat decay: entities are not part of the
A3 lazy-heat migration (they retain an eager ``heat`` column), so they
still decay via a simple exponential law, applied per consolidation
pass by ``mcp_server/handlers/consolidation/decay.py``.
````

## module — original line 22 (docstring)

````text
Naming note — do not confuse with ``ADAPTIVE_DECAY``: the
``ADAPTIVE_DECAY`` mechanism reported in the LoCoMo v3 ablation table
(``benchmarks/results/ablation/locomo_v3/summary.csv``) is an adaptive
*decay rate* on the memory-heat Ebbinghaus path — it lives in
``mcp_server/core/thermodynamics.py`` (``compute_decay``'s
``Mechanism.ADAPTIVE_DECAY`` gate), ``mcp_server/core/pg_recall.py``,
and is configured by ``ADAPTIVE_DECAY_ENABLED`` /
``ADAPTIVE_DECAY_MIN_RATE`` / ``ADAPTIVE_DECAY_MAX_RATE`` in
``mcp_server/infrastructure/memory_config.py``. It has never lived in
this module and is unrelated to entity decay or to the ACT-R model
that used to live here.
````

## module — original line 34 (docstring)

````text
Pure business logic — receives entity data, returns updated heat values.

````

## _parse_hours_since_access — original line 73 (docstring)

````text
    Fallback chain: last_accessed → ingested_at → created_at. Entities
    do not currently carry ingested_at, so this falls through to
    created_at for them, but the same fallback order is used so entity
    and memory records can share a parsing convention if that changes.
    
````

## compute_entity_decay — original line 99 (docstring)

````text
    Entities use exponential decay (simpler — no access history tracked).
    Returns list of (entity_id, new_heat) tuples.
    
````

## module — original line 41 (comment)

````text
# Minimum heat change worth persisting as an update.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
