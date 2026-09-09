---
title: "ADR-0268 — mcp_server/core/streaming/adaptive_writer.py rationale"
status: accepted
source: mcp_server/core/streaming/adaptive_writer.py
---

# ADR-0268 — mcp_server/core/streaming/adaptive_writer.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Pairs an ``AdaptiveBatchController`` (AIMD batch sizing from observed write
latency) with a ``BatchSink``, and fans rows across N such writers behind a
bounded queue:
````

## module — original line 7 (docstring)

````text
  - **Adaptive sizing** — each writer grows its batch while writes stay under
    the latency target and halves it when PG slows (AIMD; Jacobson 1988,
    Chiu & Jain 1989). The calibration sweep showed edge throughput rising 6x
    from 1k→10k rows/batch, so a fixed size leaves throughput on the table.
  - **Load balancing** — a bounded thread-safe queue hands each page to
    whichever of ``concurrency`` workers is free; under PG contention every
    worker's controller shrinks together, converging to a fair share (the same
    AIMD fairness property), so writers self-balance with no central scheduler.
  - **Backpressure** — the queue is bounded; a full queue blocks the producer
    (SEDA; Welsh 2001), so the async page-fetcher pauses instead of piling up.
````

## module — original line 18 (docstring)

````text
Pure orchestration — depends only on the sink / controller abstractions.

````

## compute_queue_cap — original line 43 (docstring)

````text
    Pinned to ``b_max`` (NOT the live B): the controller ramps B up to b_max,
    so sizing from a smaller live B would let peak RAM overshoot once it ramps.
    source: Little (1961), occupancy bound applied to memory. Floors at 1.
    
````

## AdaptiveBatchWriter — original line 57 (docstring)

````text
    One writer is single-threaded (its sink owns one connection). The buffer
    holds at most ``b_max + one input page`` rows, so peak RAM stays bounded.
    
````

## adaptive_drain — original line 113 (docstring)

````text
    The async producer (e.g. a Kuzu pager) stays on the event loop; each page
    is offloaded onto a bounded queue via ``asyncio.to_thread(q.put, ...)`` —
    which blocks (backpressure) when the queue is full while keeping the loop
    free to fetch the next page (producer || consumer overlap). ``concurrency``
    worker threads each run an ``AdaptiveBatchWriter`` with its own sink + AIMD
    controller. One sentinel per worker (emitted in ``finally``, so a producer
    crash still releases every worker) ends the run; workers flush their tail
    and close. Returns total rows written + any surfaced errors.
    
````

## inline — original line 139 (directive-rationale)

````text
# noqa: BLE001 — surfaced via result
````
