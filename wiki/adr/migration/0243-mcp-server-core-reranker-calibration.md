---
title: "ADR-0243 — mcp_server/core/reranker_calibration.py rationale"
status: accepted
source: mcp_server/core/reranker_calibration.py
---

# ADR-0243 — mcp_server/core/reranker_calibration.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Per-process store for Platt calibration of FlashRank reranker scores.
````

## module — original line 3 (docstring)

````text
Collects (raw_score, label) training pairs from ``rate_memory`` feedback
and fits Platt parameters every N pairs. The fitted parameters are cached
and applied in the reranker blend step.
````

## module — original line 7 (docstring)

````text
Persistence to a ``reranker_calibration`` table is deferred until the
Phase 3 A3 migration lands (pg_schema.py is currently owned by A3). The
in-process state is reset on restart, which is acceptable:
````

## module — original line 11 (docstring)

````text
  - Calibration converges in O(MIN_SAMPLES) rate_memory calls.
  - Cold start returns raw scores (which is the current production
    behaviour), so restart is never worse than the pre-AF-2 baseline.
````

## module — original line 15 (docstring)

````text
Pure business logic — module-level mutable state is explicit and
audited at the call site (engineer.md Move 3 §Construct 1 override for
write-once-at-startup / runtime-seed configuration).

````

## reset_for_tests — original line 83 (docstring)

````text
Test-only hook: reset all in-process calibration state.
````

## inline — original line 32 (comment)

````text
# FIFO cap so memory doesn't grow unboundedly.
````
