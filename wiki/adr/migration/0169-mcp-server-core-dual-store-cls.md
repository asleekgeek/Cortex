---
title: "ADR-0169 — mcp_server/core/dual_store_cls.py rationale"
status: accepted
source: mcp_server/core/dual_store_cls.py
---

# ADR-0169 — mcp_server/core/dual_store_cls.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Classifies memories as "episodic" (specific events with line numbers, paths,
timestamps) or "semantic" (general knowledge with decision/architecture/
convention keywords). Used to weight retrieval results.
````

## module — original line 7 (docstring)

````text
NOTE: Previously cited McClelland et al. (1995) CLS theory and Go-CLS (Sun
et al., 2023). Those papers describe dual learning systems (fast hippocampal
binding vs slow cortical gradient descent) and gated encoding architectures.
This module implements neither — it is a keyword-based text classifier.
Citations removed per zetetic standard.
````

## module — original line 13 (docstring)

````text
The episodic/semantic distinction is conceptually aligned with CLS theory's
two-store model, but the implementation mechanism (regex) bears no
relationship to the paper's computational model (neural network learning).
````

## module — original line 17 (docstring)

````text
Pure business logic — no I/O.

````

## classify_memory — original line 69 (docstring)

````text
    Resolution order:
      1. Tag-based: semantic tags -> "semantic"
      2. Specificity override: line numbers, paths, tracebacks -> "episodic"
      3. Content keywords: decision/architecture words -> "semantic"
      4. Default: "episodic"
    
````
