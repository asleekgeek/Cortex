---
title: "ADR-0205 — mcp_server/core/microglial_pruning.py rationale"
status: accepted
source: mcp_server/core/microglial_pruning.py
---

# ADR-0205 — mcp_server/core/microglial_pruning.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Edge pruning uses the multiscale backbone extraction algorithm from:
  Serrano MA, Boguna M, Vespignani A (2009) "Extracting the multiscale
  backbone of complex weighted networks." PNAS 106(16):6483-6488.
````

## module — original line 7 (docstring)

````text
For each edge (i,j) with weight w_ij, the disparity filter computes a
p-value alpha_ij = (1 - p_ij)^{k_i - 1} where p_ij = w_ij / strength(i).
Edges kept when alpha < threshold at EITHER endpoint (statistically
significant at either end).
````

## module — original line 12 (docstring)

````text
Temporal decay follows Aggarwal & Subbian (2014): effective weight decays
exponentially with hours since last co-access, half-life = 168h (7 days).
````

## module — original line 15 (docstring)

````text
Pure business logic -- no I/O.

````

## _temporal_decay — original line 41 (docstring)

````text
    lambda = ln(2) / half_life so that weight halves every half_life hours.
    Aggarwal & Subbian (2014).
    
````

## _disparity_alpha — original line 84 (docstring)

````text
    Serrano et al. (2009) Eq. 2. Under the null hypothesis of uniform
    weight distribution across k edges, alpha is the probability of
    observing a normalized weight >= p.
````

## identify_prunable_edges — original line 102 (docstring)

````text
Identify edges to prune via Serrano et al. (2009) disparity filter.
````

## identify_prunable_edges — original line 104 (docstring)

````text
    Steps:
      1. Apply temporal decay to raw weights (Aggarwal & Subbian 2014).
      2. For each edge, compute disparity alpha at both endpoints.
      3. Keep edge if alpha < threshold at EITHER endpoint.
      4. Never prune edges touching protected entities.
````

## _classify_prune_reasons — original line 157 (docstring)

````text
Classify why an edge was pruned for diagnostic reporting.
````

## inline — original line 26 (comment)

````text
# Standard significance level (Serrano 2009)
````

## inline — original line 27 (comment)

````text
# 7 days (Aggarwal & Subbian 2014)
````

## module — original line 29 (comment)

````text
# Heat below which both edge endpoints count as cold.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
