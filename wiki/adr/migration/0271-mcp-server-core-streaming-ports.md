---
title: "ADR-0271 — mcp_server/core/streaming/ports.py rationale"
status: accepted
source: mcp_server/core/streaming/ports.py
---

# ADR-0271 — mcp_server/core/streaming/ports.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Pure business logic — no I/O. Infrastructure implements these protocols
(CursorStreamSource, CopyBatchSink, ExecuteManyBatchSink, StagingResolveSink);
handlers wire them into a BackpressurePipeline.
````

## module — original line 7 (docstring)

````text
The contracts encode the invariant that makes peak RAM independent of total
row count:
  - every producer is a generator yielding bounded batches, never a full list;
  - every consumer flushes one batch and releases it, never accumulating
    across batches (no stage-spanning buffer — not even a name->id map).

````

## StreamSource — original line 25 (docstring)

````text
    Contract:
      - ``stream`` MUST be a generator; it never materializes the full result
        set. Peak resident rows from the source is one yielded batch.
      - Each yielded list is non-empty and ``len(batch) <= max_batch``.
      - Iteration order is deterministic (keyset / cursor order) so a consumer
        may record the last item and resume after an interruption. OFFSET
        pagination is forbidden — it drifts under concurrent mutation.
    
````
