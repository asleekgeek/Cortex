---
title: "ADR-0266 — mcp_server/core/streaming/__init__.py rationale"
status: accepted
source: mcp_server/core/streaming/__init__.py
---

# ADR-0266 — mcp_server/core/streaming/__init__.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
A producer (StreamSource) feeds a bounded queue feeding batch consumers
(BatchSink) with adaptive batch sizing (AdaptiveBatchController). Peak RAM
is provably (queue_cap + concurrency + 1) batches — independent of the total
number of rows — so the same code streams thousands or trillions of rows.
````

## module — original line 8 (docstring)

````text
Pure business logic only. Infrastructure provides the adapters; handlers wire
them. See ~/.claude/plans/sharded-popping-harbor.md for the design and the
genius-review findings the contracts encode.

````
