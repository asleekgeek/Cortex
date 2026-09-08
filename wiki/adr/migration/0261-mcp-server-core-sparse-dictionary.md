---
title: "ADR-0261 — mcp_server/core/sparse_dictionary.py rationale"
status: accepted
source: mcp_server/core/sparse_dictionary.py
---

# ADR-0261 — mcp_server/core/sparse_dictionary.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 147 (comment)

````text
# source: learn_dictionary docstring — fall back to the seed dictionary when
# fewer than 10 conversations are available.
````

## module — original line 219 (comment)

````text
# Signals with an absolute weight at or below this floor are ignored when
# labeling a feature atom.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 258 (comment)

````text
# OMP coefficients with an absolute value at or below this epsilon are
# numerically zero and dropped from the session weights.
# source: pre-existing numerical-tolerance value, extracted unchanged
# (#197 family 3); provenance not recorded at introduction
````
