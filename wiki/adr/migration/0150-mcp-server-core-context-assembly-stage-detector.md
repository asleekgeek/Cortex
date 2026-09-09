---
title: "ADR-0150 — mcp_server/core/context_assembly/stage_detector.py rationale"
status: accepted
source: mcp_server/core/context_assembly/stage_detector.py
---

# ADR-0150 — mcp_server/core/context_assembly/stage_detector.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
A "stage" is a **distinct subject with its own context** — the unit of
topical locality that the StageAwareContextAssembler operates on. In
the original Swift PRD pipeline (Clément Deust), stages are explicit:
Impact, Integration, PRD, Implementation. Each is a different task with
its own vocabulary and its own relevance.
````

## module — original line 9 (docstring)

````text
For Cortex, free-form conversations don't come with explicit stage
labels. This module provides pluggable detectors so stage boundary
strategies can be A/B tested empirically rather than hard-coded.
````

## module — original line 13 (docstring)

````text
Ships two detectors in v1:
  - `ExplicitStageDetector` — stage = an explicit field on the memory
    (e.g. "plan_id" for BEAM, "agent_topic" for production)
  - `TemporalStageDetector` — stage = contiguous block of memories with
    inter-memory time gaps below a threshold
````

## module — original line 19 (docstring)

````text
Future (A/B candidates): semantic clustering, LLM topic-shift detection,
hybrid explicit+temporal fallback.

````

## ExplicitStageDetector — original line 56 (docstring)

````text
    Examples:
      - BEAM benchmark: field="plan_id" (the BEAM-10M dataset has a
        plan index per turn, tagged at ingest).
      - Production Cortex: field="agent_topic" or "directory_context".
````

## TemporalStageDetector — original line 90 (mixed-contract-rationale)

````text
    Args:
        gap_hours: inter-memory gap above which a new stage begins.
            Default 4h matches a typical work-session boundary.
        time_field: name of the timestamp field. Accepts ISO strings
            or datetime objects.
    
````

## module — original line 30 (comment)

````text
# source: structural — "Month-DD-YYYY" splits on two "-" into three fields
````

## module — original line 155 (comment)

````text
# Try ISO format first (2024-03-15, 2024-03-15T10:00:00Z)
````

## module — original line 160 (comment)

````text
# Try BEAM's "Month-DD-YYYY" format (March-15-2024)
````

## module — original line 173 (comment)

````text
# naive by design: matches the sibling ISO branch
# above, which is naive too whenever `value` lacks
# an explicit offset (date-only ISO strings).
# Making only this fallback aware would introduce a
# new naive/aware mismatch across the two parsing
# paths — a behavior change out of scope for a lint
# refactor; unifying tz-awareness belongs in a
# dedicated fix.
````
