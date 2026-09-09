---
title: "ADR-0269 — mcp_server/core/streaming/backpressure_pipeline.py rationale"
status: accepted
source: mcp_server/core/streaming/backpressure_pipeline.py
---

# ADR-0269 — mcp_server/core/streaming/backpressure_pipeline.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Backpressure pipeline — bounded-queue producer/consumer with constant peak RAM.
````

## module — original line 3 (docstring)

````text
Pure orchestration logic — depends only on the StreamSource / BatchSink ports
(DIP); does no I/O itself. The injected sinks perform the writes.
````

## module — original line 6 (docstring)

````text
Topology: one producer thread drains a StreamSource into a bounded queue;
``concurrency`` worker threads pull batches and call ``BatchSink.write_batch``.
The bounded queue with blocking ``put`` IS the backpressure mechanism (SEDA,
Welsh et al. 2001): when writers fall behind, the queue fills, the producer
blocks, and the source stops fetching. Peak resident payload is
``(queue_cap + concurrency + 1)`` batches — independent of total row count.
````

## module — original line 13 (docstring)

````text
Shutdown: the producer emits exactly one sentinel per worker in a ``finally``
(so it fires on the crash path too); each worker consumes exactly one sentinel
and stops; the caller joins all workers before any pool is closed. There is no
other end-of-stream signal in the codebase, so this protocol is load-bearing.

````

## compute_queue_cap — original line 51 (docstring)

````text
    Pinned to ``b_max`` (NOT the live B): the controller ramps B up to b_max,
    so sizing from a smaller live B would let peak RAM overshoot the budget by
    ``b_max / B`` once it ramps. source: Little (1961), occupancy bound applied
    to memory rather than time. Floors at 1 so the pipeline always makes
    progress.
    
````

## BackpressurePipeline — original line 73 (docstring)

````text
    Data only — deliberately no methods. mutmut's mutation generator
    categorically excludes the body of any `@dataclass`-decorated class
    (`mutmut/mutation/file_mutation.py:236`) — including `@staticmethod`
    members, since the exclusion fires on the decorated `ClassDef` itself,
    before the per-method `@staticmethod` exception is ever consulted — so
    logic placed on methods here would carry zero mutation coverage no
    matter how the test loader names the module (issue #262 3rd pass;
    issue #282). `backpressure_pipeline_run` (the public entry point) plus
    the private `_bp_produce` / `_bp_consume` / `_bp_build_sink` /
    `_bp_write_one` / `_bp_close` helpers below carry the same logic as
    free functions instead.
    
````

## module — original line 103 (comment)

````text
# §12 note: the `name=` kwargs below (both threads) are debug-only
# labels (visible via `threading.enumerate()` / crash dumps) — they do
# not affect the returned PipelineResult, the only contract this
# function's tests assert against, so a mutant that changes, drops, or
# nulls a thread's `name` is EQUIVALENT for that contract. Verified
# empirically: mutating `name=` never changed a test outcome across the
# full `_bp_*` mutation sweep (issue #282).
````

## inline — original line 136 (comment)

````text
# blocks when full — this is the backpressure
````

## inline — original line 140 (directive-rationale)

````text
# noqa: BLE001 — surfaced via result, not raised
````

## module — original line 144 (comment)

````text
# Exactly one sentinel per worker — in finally so a producer crash
# still releases every worker (no hang on an empty-but-open queue).
````
