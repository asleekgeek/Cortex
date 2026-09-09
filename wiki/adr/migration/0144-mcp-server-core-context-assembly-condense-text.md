---
title: "ADR-0144 — mcp_server/core/context_assembly/condense_text.py rationale"
status: accepted
source: mcp_server/core/context_assembly/condense_text.py
---

# ADR-0144 — mcp_server/core/context_assembly/condense_text.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Condensers for free-text conversational content (issue #228 split 1/4).
````

## module — original line 3 (docstring)

````text
Extracted from ``condensers.py`` (§4.1 — the original file was 391 lines,
over this repo's 300-line cap) with zero behaviour change: same functions,
same bodies, same helpers, only the module boundary moved. See
``condensers.py`` for the shared module docstring and re-export facade.
````

## module — original line 8 (docstring)

````text
Covers the two condensers whose strategy is "keep a sentence-level slot,
drop the rest": the user-message condenser (first + questions + last) and
the timeline-event condenser (date + first sentence).

````

## condense_timeline_event — original line 64 (docstring)

````text
Extract when/what/who into a fixed-slot format within budget.
````

## module — original line 22 (comment)

````text
# source: structural — the condenser keeps first + last sentence, so texts
# of two or fewer sentences have no middle filler to drop.
````

## module — original line 47 (comment)

````text
# EQUIVALENT MUTANT (#228): `<=` → `<`. On the boundary the mutant falls
# through to `truncate_to_budget(result, token_budget)`, whose own guard
# is `estimator(text) <= token_budget` — so it returns `result` unchanged
# and the two branches coincide exactly where the mutation moves the
# comparison. The same shape recurs in condense_timeline_event below.
````

## module — original line 57 (comment)

````text
# ── Timeline-event condenser ────────────────────────────────────────────
# Strategy: extract (when, what, who) slots. A fixed schema compresses an
# event more reliably than a free-text summary because the salient fields
# are pinned. (Engineering heuristic — no biological source.)
````

## module — original line 81 (comment)

````text
# EQUIVALENT MUTANT (#228): `<=` → `<`, same shape as the one documented
# in condense_user_message — truncate_to_budget returns `compressed`
# unchanged on the boundary, so both branches agree there.
````
