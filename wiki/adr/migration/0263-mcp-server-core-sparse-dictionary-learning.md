---
title: "ADR-0263 — mcp_server/core/sparse_dictionary_learning.py rationale"
status: accepted
source: mcp_server/core/sparse_dictionary_learning.py
---

# ADR-0263 — mcp_server/core/sparse_dictionary_learning.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Extracted from sparse_dictionary.py to respect the 300-line file limit.
Contains the numerical core: OMP sparse coding, least-squares solver,
atom initialization (maximin distance), and K-SVD dictionary optimization.
````

## module — original line 29 (comment)

````text
# Determinants with an absolute value below this epsilon are treated as
# singular and yield a zero solution.
# source: pre-existing numerical-tolerance value, extracted unchanged
# (#197 family 3); provenance not recorded at introduction
````

## module — original line 116 (comment)

````text
# Residual correlations below this epsilon are numerically zero — no atom
# meaningfully matches the residual, so the pursuit stops.
# source: pre-existing numerical-tolerance value, extracted unchanged
# (#197 family 3); provenance not recorded at introduction
````
