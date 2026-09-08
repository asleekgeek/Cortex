---
title: "ADR-0149 — mcp_server/core/context_assembly/stage_assembler.py rationale"
status: accepted
source: mcp_server/core/context_assembly/stage_assembler.py
---

# ADR-0149 — mcp_server/core/context_assembly/stage_assembler.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Ports Clément Deust's Swift `StageAwareContextAssembler` from
ai-architect-prd-builder/packages/AIPRDRAGEngine/Sources/Services/
StageAwareContextAssembler.swift to Python, adapted for Cortex's
memory types and complemented with paper-backed mechanisms at three
specific points.
````

## module — original line 9 (docstring)

````text
## The algorithm
````

## module — original line 11 (docstring)

````text
Given a query and a token budget, assemble a structured context in
three phases with a fixed 60/30/10 split:
````

## module — original line 14 (docstring)

````text
  Phase 1 — Own-stage (60% of budget)
    Search the current stage's memories by query.
    Select chunks via submodular coverage (Krause & Guestrin 2008)
    instead of top-k, to avoid near-duplicate drowning.
````

## module — original line 19 (docstring)

````text
  Phase 2 — Adjacent stages via entity graph (30% of budget)
    Extract entities from Phase 1 results.
    Run Personalized PageRank (HippoRAG, Gutiérrez NeurIPS 2024) over
    Cortex's entity graph seeded on those entities.
    Select cross-stage memories ranked by PPR mass.
````

## module — original line 25 (docstring)

````text
  Phase 3 — Summary fallback (10% of budget)
    For stages not covered by Phase 1+2, retrieve pre-computed
    schema-structured summaries ordered by stage proximity.
````

## module — original line 29 (docstring)

````text
## Output
````

## module — original line 31 (docstring)

````text
A `StageContextResult` with four fields:
  - own_stage_context: Phase 1 text
  - adjacent_stage_context: Phase 2 text
  - stage_summaries: Phase 3 text
  - assembled_context: all three concatenated with section headers,
    ready to be fed into `decomposer.assemble_prompt` as a single
    placeholder or split into multiple placeholders by priority.
````

## module — original line 39 (docstring)

````text
## What's the user's design vs what's paper-backed
````

## module — original line 41 (docstring)

````text
  - The 3-phase structure, the 60/30/10 split, and the section labels
    are Clément Deust's invention (Swift original).
  - Phase 1 candidate SOURCE (dense WRRF over the stage's memories) is
    Cortex's existing primitive.
  - Phase 1 SELECTION (submodular coverage) is Krause & Guestrin 2008.
  - Phase 2 GRAPH SOURCE (Cortex's entity + relationship tables) is
    Cortex's existing primitive.
  - Phase 2 WALK (Personalized PageRank) is HippoRAG NeurIPS 2024.
  - Phase 3 SUMMARIES (schema-structured) uses Cortex's
    `schema_engine.py` (Tse 2007 schema-congruent consolidation).

````

## StageContextResult — original line 104 (docstring)

````text
    ``selected_memories`` contains the actual memory dicts that were
    chosen in Phase 1 and Phase 2, each tagged with a ``phase`` field
    (1 or 2). This is what downstream evaluators read when computing
    retrieval hits — the concatenated text fields are for the LLM
    reader, not for scoring.
    
````

## StageAwareContextAssembler — original line 137 (docstring)

````text
    Wire dependencies at construction time. All external calls are
    callbacks so this module stays dependency-free (no direct pg_store,
    no direct embeddings, no direct schema_engine).
````

## assemble — original line 191 (docstring)

````text
        Under a budget every selected item still reaches the output: a
        phase condenses over-share items (``stage_phases``) rather than
        dropping them, so the selected-memory count never depends on
        how long the individual memories happen to be.
        
````

## _select_own_stage — original line 247 (docstring)

````text
        Ranking metrics must not depend on memory length, so selection
        picks up to ``max_chunks_per_phase`` items and leaves the budget
        to text assembly, which condenses instead of dropping.
        
````

## module — original line 75 (comment)

````text
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
