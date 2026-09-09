---
title: "ADR-0119 — mcp_server/core/causal_graph.py rationale"
status: accepted
source: mcp_server/core/causal_graph.py
---

# ADR-0119 — mcp_server/core/causal_graph.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Structure is learned by the faithful PC algorithm (Spirtes & Glymour 1991;
Spirtes, Glymour & Scheines 2000) in ``causal_pc``: a G² conditional-
independence test over binary entity-presence data drives skeleton learning
with growing conditioning sets, followed by v-structure (collider)
orientation. Remaining undirected edges are oriented from temporal
precedence used as PC background knowledge (a standard tiered/temporal-prior
extension; Spirtes et al. 2000 §6.6) — never overriding a v-structure.
````

## module — original line 11 (docstring)

````text
PC determines the *graph structure* (which edges exist and their direction).
Each surviving edge is additionally annotated with a pointwise-mutual-
information *effect size* purely for downstream ranking — PMI is not part of
the structure-learning decision.
````

## module — original line 16 (docstring)

````text
Adjacency representation, no networkx. Pure business logic -- no I/O.

````

## _pmi_effect_size — original line 47 (docstring)

````text
    Used only to annotate the *strength* of an edge that PC has already
    decided to keep; it plays no role in the structure-learning test.
    
````

## discover_causal_edges — original line 144 (docstring)

````text
    Algorithm (Spirtes & Glymour 1991):
      1. PC skeleton — G² conditional-independence tests with growing
         conditioning sets remove edges between independent entities.
      2. v-structure orientation — unshielded colliders X→Z←Y.
      3. Temporal precedence orients any edge left undirected (background
         knowledge), never overriding a v-structure.
````

## module — original line 133 (comment)

````text
# PC test significance level (Spirtes et al. 2000 use α as the CI-test
# level; 0.05 is the conventional default) and the conditioning-set size
# cap (standard PC tractability bound, e.g. causal-learn's default).
````

## module — original line 138 (comment)

````text
# Sparse-noise floor: drop edges with fewer than this many co-occurrences
# (engineering guard; PC's G² test already suppresses low-count pairs).
````

## module — original line 158 (comment)

````text
# entities.name carries no UNIQUE constraint (pg_schema.py /
# sqlite_schema.py — the same name may legitimately recur across
# type/domain rows), so callers flattening store rows to names can
# pass duplicates. PC treats every list element as a distinct
# variable: a duplicated name turns the complete-graph
# initialisation's frozenset((a, a)) into a degenerate 1-element
# edge that crashes the 2-tuple unpack below, and hands
# orient_v_structures fake unshielded triples (X, X, Z). Establish
# the distinct-variables precondition once, at this boundary,
# order-preservingly (observed on a 23k-entity store, 2026-07-22).
````

## inline — original line 237 (comment)

````text
# Avoid cycles
````
