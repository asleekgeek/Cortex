---
title: "ADR-0836 — benchmarks/llm_head_to_head/__init__.py rationale"
status: accepted
source: benchmarks/llm_head_to_head/__init__.py
---

# ADR-0836 — benchmarks/llm_head_to_head/__init__.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Stage-0 scaffold for the pre-registered protocol at
``docs/provenance/beam-10m-llm-head-to-head-protocol.md`` (v3, frozen 2026-04-30).
````

## module — original line 6 (docstring)

````text
Four conditions feed the SAME generator prompt:
  A — naive long-context (recency-truncated to model window)
  B — standard top-20 vector RAG (Lewis 2020, no Cortex stack)
  C — Cortex-assembled (production ``handlers.recall.handler``)
  D — Oracle (gold ``source_chat_ids`` turns)
````

## module — original line 12 (docstring)

````text
NO API spend at scaffold stage; the orchestrator's ``--dry-run`` mode
must produce all four context blocks without firing any HTTP requests.

````

## module — original line 16 (comment)

````text
# precondition: package import is side-effect free; no API keys read here.
# postcondition: re-exporting module names resolves cleanly so callers can
#   ``from benchmarks.llm_head_to_head import data_loader`` without import-
#   time network or DB access.
````
