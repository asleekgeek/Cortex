---
title: "ADR-0130 — mcp_server/core/cognitive_map.py rationale"
status: accepted
source: mcp_server/core/cognitive_map.py
---

# ADR-0130 — mcp_server/core/cognitive_map.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Tracks temporal co-access (memories accessed within a session window are linked)
and uses discounted SR weights for retrieval scoring and BFS navigation.
````

## module — original line 6 (docstring)

````text
Pure business logic — no I/O. Callers pass pre-fetched access history.
````

## module — original line 8 (docstring)

````text
References:
  Dayan (1993) "Improving Generalization for Temporal Difference Learning"
    — the Successor Representation M = (I - γT)⁻¹.
  Stachenfeld et al. (2017) "The Hippocampus as a Predictive Map" — the SR
    matrix's eigenvectors form a low-dimensional embedding of the state
    graph (grid-cell-like); used by ``project_to_2d``.
  Belkin & Niyogi (2003) "Laplacian Eigenmaps" — those eigenvectors are
    computed here via S = D^(-1/2) W D^(-1/2), which is similar to T = D⁻¹W.

````

## _symmetric_normalized_adjacency — original line 213 (docstring)

````text
    W is the symmetrised co-access weight matrix. S is similar to the random
    walk T = D⁻¹W, hence shares the eigenvectors of the SR matrix
    M = (I - γT)⁻¹ — so its spectrum yields the SR/Laplacian eigenmap
    (Stachenfeld 2017; Belkin & Niyogi 2003).
    
````

## project_to_2d — original line 263 (docstring)

````text
    Faithful to Stachenfeld et al. (2017): the SR eigenvectors embed the
    state graph. They are computed from S = D^(-1/2) W D^(-1/2) (similar to
    T = D⁻¹W, so sharing the SR matrix's eigenvectors — Belkin & Niyogi
    2003). S's top eigenvalue is the trivial stationary component
    (eigenvector ∝ √degree); the two subdominant eigenvectors are the
    grid-cell-like (x, y) axes, placing co-accessed memories near each other.
    Isolated memories (no edge) have no predictive map → placed at origin.
````

## module — original line 28 (comment)

````text
# The 2D spectral embedding (project_to_2d) uses the eigenvectors of the SR
# matrix M = (I - γT)⁻¹, which are a function of T alone — they are identical
# for every discount γ ∈ (0, 1) — so no γ value is needed here.
````

## inline — original line 70 (comment)

````text
# Sorted, so all further pairs are further apart
````

## module — original line 251 (comment)

````text
# source: structural — spectral embedding axes exist only past these node
# counts (one non-trivial eigenvector needs >= 2 nodes; a second needs >= 3)
````
