---
title: "ADR-0147 — mcp_server/core/context_assembly/decomposer.py rationale"
status: accepted
source: mcp_server/core/context_assembly/decomposer.py
---

# ADR-0147 — mcp_server/core/context_assembly/decomposer.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
**The core primitive**: a prompt template is a set of typed placeholders,
each with a priority rank, each optionally paired with a domain-aware
condenser. When the filled template would exceed the context window,
placeholders are progressively condensed — lowest priority first —
until the total fits. If any placeholder was materially reduced, a
truncation warning banner is injected at the top so the LLM knows
what it's missing.
````

## module — original line 11 (docstring)

````text
**The invention is Clément Deust's** (original Swift implementation in
ai-architect-prd-builder/packages/AIPRDMetaPromptingEngine/Sources/
Pipeline/ContextDecomposer.swift). This Python port adapts the semantics
1:1 for Cortex. No paper precedent was found for:
  1) priority-driven progressive condensation with per-type condensers, or
  2) injecting explicit truncation awareness into the prompt.
````

## module — original line 18 (docstring)

````text
The closest neighbors in the literature are Anthropic's Contextual
Retrieval (chunk-level LLM summaries, different goal) and various
token-budgeting recipes in LangChain-style libraries (flat truncation,
no priorities, no domain awareness, no model-side warning).

````

## module — original line 38 (comment)

````text
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
