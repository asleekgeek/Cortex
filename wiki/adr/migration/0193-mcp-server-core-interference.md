---
title: "ADR-0193 — mcp_server/core/interference.py rationale"
status: accepted
source: mcp_server/core/interference.py
---

# ADR-0193 — mcp_server/core/interference.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 4 (docstring)

````text
Memory interference is the primary cause of forgetting in both biological and
artificial systems. Detection helpers live in interference_detection.py;
this module provides resolution (orthogonalization), retrieval suppression,
domain pressure metrics, and re-exports all public symbols.
````

## module — original line 9 (docstring)

````text
Computational model:
    Norman KA, Newman EL, Detre GJ (2007) A neural network model of
    retrieval-induced forgetting. Psychological Review 114:887-953.
````

## module — original line 13 (docstring)

````text
    The full Norman et al. model uses a leaky competing accumulator (LCA)
    with oscillating inhibition:
````

## module — original line 16 (docstring)

````text
        da_i/dt = -a_i/tau + sum_j(w_ij * a_j) - g * sum_j(a_j) + input_i
````

## module — original line 18 (docstring)

````text
    where g oscillates between g_high (strong lateral inhibition, only the
    strongest pattern survives) and g_low (weak inhibition, moderate
    competitors remain active). Learning uses contrastive Hebbian:
````

## module — original line 22 (docstring)

````text
        delta_w = eta * (a_plus * a_plus - a_minus * a_minus)
````

## module — original line 24 (docstring)

````text
    where a_plus/a_minus are activations at g_low/g_high respectively.
````

## module — original line 26 (docstring)

````text
    Our implementation simplifies the LCA to single-step lateral inhibition
    and projection-based orthogonalization, which captures the core insight
    (strong competitors suppress weak ones; similar representations are
    separated during offline processing) without the full oscillatory
    dynamics. This is appropriate for a memory system operating at
    hours/days timescale rather than the millisecond timescale of the
    neural model.
````

## module — original line 34 (docstring)

````text
Additional references:
    Anderson MC, Neely JH (1996) Interference and inhibition in memory
    retrieval. In: Memory (Bjork EL, Bjork RA, eds), pp 237-313.
    Academic Press. — Classic behavioral framework for retrieval-induced
    forgetting.
````

## module — original line 40 (docstring)

````text
    Wixted JT (2004) The psychology and neuroscience of forgetting.
    Annual Review of Psychology 55:235-269. — Review article providing
    context on interference vs. decay debate. No computational model;
    cited for conceptual framing only.
````

## module — original line 45 (docstring)

````text
    Yassa MA, Stark CEL (2011) Pattern separation in the hippocampus.
    Trends in Neurosciences 34:515-525. — Biological basis for
    orthogonalization of similar memory representations in dentate gyrus.
````

## module — original line 49 (docstring)

````text
Pure business logic — no I/O.

````

## _project_away — original line 115 (docstring)

````text
    Implements a simplified version of the sleep-dependent
    orthogonalization described in Yassa & Stark 2011. Each call
    removes rate * 0.5 of the shared component, modeling one
    consolidation cycle.
    
````

## orthogonalize_pair — original line 168 (docstring)

````text
    Models the offline orthogonalization component of interference
    resolution. In Norman et al. 2007, competing representations are
    separated via contrastive Hebbian learning during sleep-like replay.
    We simplify this to symmetric projection removal: each embedding
    has a fraction of its shared component with the other subtracted.
````

## compute_retrieval_suppression — original line 223 (docstring)

````text
    Simplified lateral inhibition consistent with Norman et al. 2007.
    In the full LCA model, units with higher activation suppress units
    with lower activation through the global inhibition term
    -g * sum_j(a_j). Our simplification: only competitors with scores
    higher than the target contribute suppression, proportional to their
    score advantage. This captures the key prediction of the model —
    stronger competitors suppress weaker ones — without requiring
    iterative settling dynamics.
````

## compute_retrieval_suppression — original line 232 (docstring)

````text
    The suppression_factor parameter approximates the time-averaged
    effect of oscillating g between g_high and g_low. Hand-tuned.
````

## compute_retrieval_suppression — original line 221 (mixed-contract-rationale)

````text
    Args:
        target_score: Retrieval score of the memory being evaluated.
        competitor_scores: Retrieval scores of competing (similar) memories.
        suppression_factor: Lateral inhibition strength (hand-tuned).
````

## _classify_pressure — original line 292 (docstring)

````text
    Thresholds are hand-tuned based on observed domain statistics.
    No direct mapping to Norman et al. 2007 parameters.
    
````

## compute_domain_interference_pressure — original line 318 (mixed-contract-rationale)

````text
    Args:
        embeddings: All memory embeddings in the domain.
        threshold: Similarity threshold for interference (hand-tuned).
        sample_limit: Max pairwise comparisons (for performance).
````

## module — original line 64 (comment)

````text
# ── Configuration ─────────────────────────────────────────────────────────
# All constants below are hand-tuned for this system's operating regime
# (hours/days timescale, 384-dim embeddings). They are not derived from
# Norman et al. 2007's parameters (which target ms-timescale neural dynamics).
````

## module — original line 69 (comment)

````text
# Rate at which each orthogonalization step removes the interfering
# projection component. 0.15 yields ~3-6 sleep cycles to fully separate
# two memories at sim > 0.7. Hand-tuned; no direct biological equivalent.
````

## module — original line 74 (comment)

````text
# Floor similarity — orthogonalization stops here to preserve meaningful
# semantic overlap. Hand-tuned to prevent over-separation.
````

## module — original line 78 (comment)

````text
# Lateral inhibition strength for retrieval suppression.
# Simplified from Norman et al. 2007's oscillating g parameter.
# In the full model, g oscillates between ~0.4 (g_high) and ~0.1 (g_low).
# Our fixed 0.3 approximates the time-averaged effect. Hand-tuned.
````

## module — original line 84 (comment)

````text
# Cosine similarity threshold above which two memories are considered
# to be interfering. Hand-tuned; corresponds roughly to the point where
# pattern separation mechanisms would engage in hippocampus (Yassa & Stark 2011).
````

## module — original line 89 (comment)

````text
# Numerical floor below which a vector norm is treated as zero.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 94 (comment)

````text
# Pressure-level cutoffs on the average interference score.
# source: hand-tuned thresholds documented in _classify_pressure docstring
# (observed domain statistics; no Norman et al. 2007 mapping)
````

## module — original line 101 (comment)

````text
# source: structural — pairwise interference needs at least two embeddings
````
