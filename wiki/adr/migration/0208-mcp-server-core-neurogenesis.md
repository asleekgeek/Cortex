---
title: "ADR-0208 — mcp_server/core/neurogenesis.py rationale"
status: accepted
source: mcp_server/core/neurogenesis.py
---

# ADR-0208 — mcp_server/core/neurogenesis.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
This module implements a temporal-context encoding heuristic: a rotating
hash-selected subset of fixed embedding dimensions is boosted by a magnitude
that decays with memory age, so recent memories cluster on shared dimensions.
It does NOT implement dentate-gyrus pattern separation. The "neurogenesis"
framing is a loose biological MOTIVATION, not a faithful model — the cited
papers below inspire the concept (young, broadly-tuned units carry temporal/
contextual signal that fades as they mature) but prescribe no weight, decay,
or threshold formula. All numeric constants here are engineering defaults
(see per-constant comments), not paper-derived values.
````

## module — original line 13 (docstring)

````text
Motivating references (concept only, NOT a source for any constant):
    Aimone JB, Deng W, Gage FH (2011) Resolving new memories: a critical look
        at the dentate gyrus, adult neurogenesis, and pattern separation.
        Neuron 70:589-596. A review proposing the "memory resolution"
        hypothesis; it gives no computational weight/threshold formula.
    Cognitive Neurodynamics (2025) Dynamic impact of adult neurogenesis on
        pattern separation in the DG neural network. (network simulation;
        not a prescription for embedding-dimension weights)
````

## module — original line 22 (docstring)

````text
Pure business logic — no I/O.

````

## compute_temporal_separation_weights — original line 111 (docstring)

````text
    A rotating hash-selected subset of dimensions is boosted by a magnitude
    that decays with memory age, so recent memories cluster on shared
    dimensions. This is a temporal-context heuristic inspired by — not an
    implementation of — Aimone's pattern-separation hypothesis (see module
    docstring); all constants are engineering defaults.
````

## module — original line 37 (comment)

````text
# Numerical floor below which a vector norm is treated as zero.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 42 (comment)

````text
# Extra weight applied to the "young" (recently-boosted) dimension subset at
# zero age. No paper prescribes this magnitude — Aimone 2011 is a review with
# no formula.
# source: engineering default; calibration pending
````

## module — original line 48 (comment)

````text
# Cosine-similarity threshold above which a neighbor counts as interference
# pressure. Mirrors the same 0.75 in separation_core.py, which is likewise an
# empirically-tuned engineering choice for 384-dim dense embeddings (the DG
# sourced value there is _SPARSITY_TARGET=0.04 sparsity from Leutgeb 2007 —
# a sparsity fraction, NOT a cosine threshold, so there is nothing to defer to).
# source: engineering default; calibration pending
````

## module — original line 78 (comment)

````text
# 6.0 = hours per temporal bucket (memories within the same 6h window share
#   the same boosted dimension subset); 7 = stride that rotates the boosted
#   window across buckets (coprime-ish with typical dims to spread coverage);
#   0.1 = fraction of dimensions boosted per bucket (~10%). None of these are
#   paper-derived; they are hand-picked knobs controlling temporal-cluster
#   granularity, and have not been calibrated against retrieval benchmarks.
# source: engineering default; calibration pending
````

## module — original line 102 (comment)

````text
# Exponential time-constant (hours) over which the boost decays via
# 1 - exp(-t/maturation_hours). 48h is a hand-chosen "recent memory" window
# at this system's hours/days timescale; Aimone 2011 discusses a weeks-long
# biological maturation window but gives no time-constant to port here.
# source: engineering default; calibration pending
````

## module — original line 150 (comment)

````text
# strict=True is safe here — the explicit length check above guarantees
# equality. Defensive: if a future edit removes the guard, strict will
# surface the regression as an exception instead of silently weighting
# only the shorter prefix.
````
