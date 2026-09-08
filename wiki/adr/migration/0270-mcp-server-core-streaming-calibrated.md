---
title: "ADR-0270 — mcp_server/core/streaming/calibrated.py rationale"
status: accepted
source: mcp_server/core/streaming/calibrated.py
---

# ADR-0270 — mcp_server/core/streaming/calibrated.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Calibrated streaming constants — MEASURED, not invented.
````

## module — original line 3 (docstring)

````text
source: benchmark benchmarks/streaming_calibration/run.py, measured 2026-06-04
on local PostgreSQL 15 (cortex_test). These are PROPERTIES OF THE PG INSTANCE
(schema, indexes, hardware), not portable constants — re-run the sweep and
update them when the environment changes (Kleinrock 1975: B_min/B_max are
instance properties). Provenance for every number is the committed
``benchmarks/streaming_calibration/results.json``.
````

## module — original line 10 (docstring)

````text
Sweep (p99 write latency / throughput vs batch size):
  entity: peak 73k rows/s @ 5000 (p99 111 ms); throughput drops past 5000.
  edge:   peak 221k rows/s @ 10000 (p99 131 ms) — 6x the 1000-row rate, which
          is exactly why fixed sizing is wrong and AIMD is justified.

````

## make_entity_controller — original line 43 (docstring)

````text
AIMD controller for the entity stage (measured bounds).
````

## make_edge_controller — original line 48 (docstring)

````text
AIMD controller for the edge stage (measured bounds).
````

## module — original line 21 (comment)

````text
# RAM budget for in-flight write buffers per ingest phase. Conservative — the
# bounded queue + per-worker buffers stay far under this (a few MB in practice).
````

## module — original line 37 (comment)

````text
# Hard ceiling on the bounded queue regardless of budget — small queues give
# tighter backpressure; the budget only ever *lowers* this.
````
