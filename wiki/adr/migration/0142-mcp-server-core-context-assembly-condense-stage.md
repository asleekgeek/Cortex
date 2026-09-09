---
title: "ADR-0142 — mcp_server/core/context_assembly/condense_stage.py rationale"
status: accepted
source: mcp_server/core/context_assembly/condense_stage.py
---

# ADR-0142 — mcp_server/core/context_assembly/condense_stage.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Stage-assembler integration point (issue #228 split, extracted from
``condensers.py``).
````

## module — original line 4 (docstring)

````text
StageAwareContextAssembler (stage_assembler.py) allocates a per-phase token
sub-budget to each of own/adjacent/summaries independently (submodular
selection caps chunk count per phase), so the sum can still exceed the
caller's total token_budget: estimate_tokens is a heuristic (chars // 3),
and per-phase caps do not renegotiate against each other. pg_recall.
assemble_context() promises a "budgeted, slot-filled prompt with truncation
awareness" (module docstring) — this function is the truncation-awareness
step: it is the caller that was missing, wiring condense_memory_content +
assemble_prompt's priority-condensation into the one place that already
computes the three raw text blocks. (Original wiring: issue #196.)
````

## module — original line 15 (docstring)

````text
Extracted from ``condensers.py`` (§4.1/§4.2 — the file was 391 lines, over
this repo's 300-line cap, and this function alone was 66 lines, over the
40-line cap) with zero behaviour change: the docstring below states the
same contract, split so the "how" of the over-budget path lives beside the
helper that implements it rather than in one 66-line body. See
``condensers.py`` for the shared module docstring and re-export facade.

````

## _condense_sections_over_budget — original line 100 (docstring)

````text
    Caveat inherited from ``assemble_prompt``: its truncation-warning
    banner is prepended *after* the condensation loop and is not itself
    counted against ``token_budget``, so the returned string (banner
    included) can exceed ``token_budget`` by the banner's own length.
    
````

## module — original line 29 (comment)

````text
# (header, content, priority, key) row shape shared by the two helpers
# below: priority mirrors StageAwareContextAssembler's own emphasis order
# (own > adjacent > summaries; lower number = more important = condensed
# last, decomposer.py semantics). Keys are human-readable so
# build_truncation_banner's warning lines (which label by raw placeholder
# key) name the actual section, not an opaque index.
````

## module — original line 82 (comment)

````text
# EQUIVALENT MUTANT (#196, re-confirmed #228): summaries' priority
# 3 → 4. decomposer.assemble_prompt consumes `priority` only through
# `sorted(..., key=lambda p: p.priority, reverse=True)` (decomposer.py
# lines 119 and 156) — never as a magnitude. With ranks {1, 2, 3} and
# {1, 2, 4} the descending order is byte-identical and no tie is
# created or broken, so no input can distinguish the two.
````
