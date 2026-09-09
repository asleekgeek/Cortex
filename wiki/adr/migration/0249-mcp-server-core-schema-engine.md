---
title: "ADR-0249 — mcp_server/core/schema_engine.py rationale"
status: accepted
source: mcp_server/core/schema_engine.py
---

# ADR-0249 — mcp_server/core/schema_engine.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Orchestrates the schema lifecycle after formation:
  - Matching: compare new memories against existing schemas
  - Accommodation: update schemas when assimilation fails (Piaget)
  - Revision: detect when a schema needs splitting
  - Predictions: generate top-down expectations for predictive coding
````

## module — original line 9 (docstring)

````text
Re-exports formation/merging/serialization from schema_extraction for
backward compatibility.
````

## module — original line 12 (docstring)

````text
Theoretical basis (all qualitative — no published equations):
    Tse D et al. (2007) — Experimental demonstration that prior schemas
        accelerate consolidation ~15x in rats. Purely behavioral data;
        no mathematical model or equations are provided.
    van Kesteren MTR et al. (2012) — Conceptual framework: mPFC-mediated
        schema congruency vs MTL-mediated novelty encoding (dual pathway).
        Descriptive model with no computational specification.
    Piaget J (1952) — Assimilation (fit into existing schema) and
        accommodation (modify schema on mismatch) are qualitative
        developmental theory, not a computational model.
````

## module — original line 23 (docstring)

````text
Engineering implementation:
    Schema matching uses Jaccard similarity between entity/tag sets —
    an engineering choice to operationalize qualitative "congruency."
    Accommodation uses EMA updates — a standard signal processing
    technique, not derived from any schema paper.
    All thresholds are hand-tuned:
      _HIGH_MATCH=0.7, _MEDIUM_MATCH=0.3, _MAX_VIOLATIONS=10,
      _SCHEMA_EMA_ALPHA=0.1
````

## module — original line 32 (docstring)

````text
Pure business logic — no I/O.

````

## module — original line 47 (comment)

````text
# Best-match scores below this floor count as no schema match.
# source: hand-tuned — module docstring "All thresholds are hand-tuned"
````

## module — original line 50 (comment)

````text
# Signature weights decayed below this floor are pruned from the EMA dict.
# source: hand-tuned — module docstring "All thresholds are hand-tuned"
````

## module — original line 53 (comment)

````text
# Above this violation/usage ratio a schema needs revision.
# source: hand-tuned — module docstring "All thresholds are hand-tuned"
````
