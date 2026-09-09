---
title: "ADR-0176 — mcp_server/core/entity_dedup.py rationale"
status: accepted
source: mcp_server/core/entity_dedup.py
---

# ADR-0176 — mcp_server/core/entity_dedup.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Collapses near-duplicate *concept* entities that the case-canonical insert
policy (``shared.entity_canonical``) and exact-name DB upsert miss — whitespace
and punctuation variants ("Embedding Engine" vs "EmbeddingEngine"), and typos
("Postgres" vs "Postgers") — so the co-access / knowledge graph isn't fragmented
across spelling variants of one concept.
````

## module — original line 9 (docstring)

````text
Ported from graphify's batch graph deduplicator (graphify/dedup.py) and adapted
to Cortex:
    - Identity is the entity name (Cortex entities are name-keyed and already
      case-deduped on insert), so the "same label, different file → keep apart"
      guards graphify needs are unnecessary; instead we require a **same type**
      for any merge.
    - Code symbols (functions, classes, …) are exempt from label-fuzzy merging:
      their identity is structural, and two ``render`` functions in different
      modules are distinct, not duplicates (graphify #1205).
    - Match strength is a float Jaro-Winkler score with a textual reason — no
      EXTRACTED/INFERRED enum is imported.
````

## module — original line 21 (docstring)

````text
This is a *batch* operation (a maintenance/consolidation step), not the
synchronous write-gate path. It returns an alias→canonical remap; the caller
rewires ``memory_entities`` / ``relationships`` to survivors and merges heat.
````

## module — original line 25 (docstring)

````text
Pure business logic — no I/O.

````

## EntityMerge — original line 62 (docstring)

````text
One matched pair and why it matched (audit trail).
````

## DedupResult — original line 74 (docstring)

````text
    remap: alias entity key -> surviving canonical entity key.
    merges: every matched pair with its score and reason.
    survivors: entities that remain after collapsing aliases.
    
````

## _pick_winner — original line 121 (docstring)

````text
    Cortex adaptation — graphify ranks by id length only because it has no heat;
    Cortex prefers the most-established entity (mention_count, then heat) so the
    survivor is the one the rest of the graph already points at.
    
````

## module — original line 51 (comment)

````text
# Concept-ish types where spelling/spacing variants of one real-world entity
# legitimately arise. Structural code symbols and file paths are exempt — their
# identity is the symbol/path, not a fuzzy label (graphify #1205).
````

## module — original line 56 (comment)

````text
# source: structural — a merge pair needs at least two candidates
````

## module — original line 161 (comment)

````text
# Only text-extracted concepts are fuzzy-eligible; AST-extracted code
# symbols (origin='ast_symbol') are exempt (graphify #1205). Entities
# without an origin (e.g. legacy/test inputs) default to eligible.
````

## module — original line 202 (comment)

````text
# Dotted module paths / file paths are code identifiers, not fuzzy
# concepts — exempt from fuzzy candidacy (graphify #1205 analog).
````
