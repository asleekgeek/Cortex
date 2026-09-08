---
title: "ADR-0097 — mcp_server/core/abstention_gate.py rationale"
status: accepted
source: mcp_server/core/abstention_gate.py
---

# ADR-0097 — mcp_server/core/abstention_gate.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Filters retrieval results that don't actually answer the query.
The model is a fine-tuned DistilBERT trained on BEAM (query, passage,
relevant/irrelevant) pairs with hard-negative mining.
````

## module — original line 7 (docstring)

````text
When the model is unavailable, falls back to no-op (returns results
unchanged) — never breaks retrieval.
````

## module — original line 10 (docstring)

````text
Source model: github.com/cdeust/cortex-know-when-to-stop-training-model
````

## module — original line 12 (docstring)

````text
Pure business logic — no I/O beyond model inference.

````

## filter_by_abstention — original line 80 (mixed-contract-rationale)

````text
    Args:
        query: The original query text.
        candidates: Retrieved memory dicts with 'content' field.
        threshold: Minimum relevance score to keep a result.
            Default 0.45 (F1-optimal from v0.1 evaluation).
        keep_at_least: Always return at least this many results,
            even if all score below threshold. 0 = strict filtering
            (may return empty list = abstention).
````

## module — original line 27 (comment)

````text
# Calibrated thresholds (from v0.1 model evaluation):
#   Score range on diverse queries: 0.215 - 0.830
#   F1-optimal threshold: 0.45
#   Precision-optimal threshold: 0.55
#   Recall-optimal threshold: 0.35
````

## inline — original line 51 (directive-rationale)

````text
# noqa: PLC0415 — optional-feature probe: ImportError here is a handled degraded mode # pyright: ignore[reportMissingImports] — optional package, not installed in the type-check env; the except ImportError arm IS the contract
````

## inline — original line 67 (directive-rationale)

````text
# noqa: BLE001 — last-resort boundary — failure is logged; degraded mode continues
````
