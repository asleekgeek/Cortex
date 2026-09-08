---
title: "ADR-0248 — mcp_server/core/retrieval_signals.py rationale"
status: accepted
source: mcp_server/core/retrieval_signals.py
---

# ADR-0248 — mcp_server/core/retrieval_signals.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 19 (comment)

````text
# Tokens at or below this length are dropped from SA query terms.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## inline — original line 56 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("retrieval_signals.hopfield")
````

## inline — original line 66 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("retrieval_signals.hdc")
````

## inline — original line 109 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("retrieval_signals.successor_representation")
````

## inline — original line 145 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary; failure is observable via silent_failure
````
