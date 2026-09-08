---
title: "ADR-0124 — mcp_server/core/claim_resolver.py rationale"
status: accepted
source: mcp_server/core/claim_resolver.py
---

# ADR-0124 — mcp_server/core/claim_resolver.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Three responsibilities:
````

## module — original line 5 (docstring)

````text
  1. Entity linking — each ClaimEvent inherits its source memory's
     entity_ids (the existing memory_entities join table is the
     authority). Also harvests inline entity name mentions from claim
     text against the entities catalogue.
````

## module — original line 10 (docstring)

````text
  2. Supersedes resolution — when a claim's text contains
     "supersedes / replaces / deprecated by", find the most likely
     prior claim it overrides (same entities + earlier in time + same
     claim_type when sensible). Writes claim_events.supersedes.
````

## module — original line 15 (docstring)

````text
  3. Conflict detection — claims about the same entities with
     opposing types (decision vs limitation about the same target) are
     surfaced as candidates. Writes a memo per detected pair so the
     curation phase can act on them.
````

## module — original line 20 (docstring)

````text
Pure logic — no I/O. The handler wires this against pg_store_wiki.
````

## module — original line 22 (docstring)

````text
Design constraint (DBA): the resolver must not JOIN into the memories
hot path. All inputs are pre-fetched by the handler; the resolver
returns plans (entity-id lists, supersedes pairs, conflict pairs) that
the handler persists in idempotent batches.

````

## SupersedesPlan — original line 47 (docstring)

````text
One claim_event.supersedes update.
````

## ConflictPlan — original line 58 (docstring)

````text
    Captured as a memo via ``insert_memo(subject_type='claim', ...)``
    rather than altering either claim — disagreement is data, not a
    correction.
    
````

## plan_entity_links — original line 92 (docstring)

````text
    Sources:
      - memory_entities for claim.memory_id (inherited from source)
      - case-insensitive name match on entities catalogue (inline mentions)
````

## plan_supersedes — original line 144 (docstring)

````text
    A claim is a supersedes-candidate when its text matches the
    supersedes pattern. We look for prior claims that:
      - share at least one entity_id with the new claim
      - have an earlier extracted_at timestamp
      - have a compatible claim_type (decision supersedes decision,
        method supersedes method; we don't supersede limitations)
````

## plan_supersedes — original line 151 (docstring)

````text
    Picks the most-recently-superseded matching prior claim if any.
    Returns one plan per superseder; never raises.
    
````

## _conflict_reason — original line 218 (docstring)

````text
Return reason text if (type_a, type_b) is a conflicting pair.
````

## plan_conflicts — original line 233 (docstring)

````text
    Pair (A, B) is a conflict candidate when:
      - claim_types match _CONFLICT_PAIRS
      - they share ≥ min_entity_overlap entities
      - they are not already in a supersedes relationship (caller
        suppresses by ordering: supersedes plan first; conflict plan
        excludes those pairs)
````

## resolve — original line 304 (docstring)

````text
    Order matters: entity links first (so supersedes/conflicts can
    use the freshly-attached ids), then supersedes (so conflict
    detection can suppress superseded pairs).
    
````

## module — original line 80 (comment)

````text
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 109 (comment)

````text
# Word-bounded substring — cheap pre-filter, no false positives
# on partial words. Misses fuzzy matches; that's a Phase 3 problem.
````

## module — original line 125 (comment)

````text
# ── Supersedes detection ──────────────────────────────────────────────
````

## module — original line 310 (comment)

````text
# Inject the planned entity ids back into the claim dicts so
# supersedes/conflict planners see the up-to-date data.
````

## module — original line 321 (comment)

````text
# Build a set of superseded ids so conflict detection can skip them
````
