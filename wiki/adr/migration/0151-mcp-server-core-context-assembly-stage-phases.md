---
title: "ADR-0151 — mcp_server/core/context_assembly/stage_phases.py rationale"
status: accepted
source: mcp_server/core/context_assembly/stage_phases.py
---

# ADR-0151 — mcp_server/core/context_assembly/stage_phases.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
``stage_assembler.StageAwareContextAssembler`` orchestrates; the work of
each phase — selecting the items and rendering them into text that fits
the phase's share of the token budget — lives here.
````

## module — original line 7 (docstring)

````text
The packing rule is the point of this module. A phase used to skip any
item that did not fit the remaining budget, which contradicted the
assembler's own contract ("may truncate individual chunks but never
reduces the count of selected items") and silently dropped exactly the
long, information-dense memories the retrieval stack had just ranked
highest. ``pack_within_budget`` instead gives every item a share of the
budget (``budget.proportional_share``, the Swift ContextDecomposer rule)
and hands the over-share ones to the domain-aware condensers in
``condensers.py`` — the reduction those condensers were written for and
had no call site for until this module.
````

## module — original line 18 (docstring)

````text
Pure: no I/O, no store access. Callers inject every external lookup.

````

## pack_within_budget — original line 46 (docstring)

````text
    Every input memory produces exactly one output string — an item is
    condensed, never dropped, so ``len(texts) == len(memories)`` holds
    for any budget. ``token_budget is None`` means "no budget": contents
    are returned verbatim.
````

## pack_within_budget — original line 51 (docstring)

````text
    The output fits ``token_budget`` except where the per-item floor
    binds: with ``n`` items the ceiling is ``max(token_budget, n *
    MIN_ITEM_SHARE_TOKENS)``, because the share rule never starves an
    item below the floor at which condensation stops meaning anything.
    Callers that must not overshoot bound ``n`` (the assembler caps it
    at ``max_chunks_per_phase``).
````
