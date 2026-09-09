---
title: "ADR-0152 — mcp_server/core/context_assembly/warning.py rationale"
status: accepted
source: mcp_server/core/context_assembly/warning.py
---

# ADR-0152 — mcp_server/core/context_assembly/warning.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
When the prompt decomposer must condense placeholders to fit the
context window, it injects a warning banner at the top of the final
prompt. The LLM sees an explicit list of what was cut and by how much,
so it can reason about missing information rather than hallucinating.
````

## module — original line 8 (docstring)

````text
This is a direct port of the Swift `buildTruncationWarning` helper in
ContextDecomposer.swift. The mechanism is Clément Deust's invention —
no paper precedent has been found for injecting truncation awareness
into the prompt itself.
````

## module — original line 13 (docstring)

````text
Original: ai-architect-prd-builder/packages/AIPRDMetaPromptingEngine/
          Sources/Pipeline/ContextDecomposer.swift → buildTruncationWarning

````

## module — original line 22 (comment)

````text
# Reduction threshold below which a placeholder is considered "truncated"
# for the purposes of the warning. Matches the Swift default of 10%.
````
