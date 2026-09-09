---
title: "ADR-0828 — benchmarks/forgetting_curve/criteria.py rationale"
status: accepted
source: benchmarks/forgetting_curve/criteria.py
---

# ADR-0828 — benchmarks/forgetting_curve/criteria.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Falsifiable acceptance criteria for the forgetting-curve benchmark.
````

## transient_points — original line 71 (docstring)

````text
Strictly-decaying regime: heat in (floor·1.05, heat_base). Excludes the
    floored tail and underflow zeros so both models fit the same data.
````

## criterion_benna_fusi_sqrt_t — original line 163 (docstring)

````text
    Tested on the population MIXTURE — the mean retention over a cohort whose
    members terminate across all 4 stages — NOT on a single trace. A single
    stage decays as a pure exponential by construction; the only route to a
    power law in this architecture is the superposition of separated timescales
    (Benna&Fusi 2016). PASSES iff the mixture is fit better by a power law than
    by a single exponential (ΔAIC>2, power_law wins) AND its fitted exponent
    falls in the √t band [0.4, 0.6] around the canonical 0.5.
````

## criterion_benna_fusi_sqrt_t — original line 171 (docstring)

````text
    CAN FAIL — and is expected to: a 4-level α-ladder spanning a single rate
    decade (2.0→0.5) is far coarser than Benna&Fusi's many-decade continuum of
    timescales, so the mixture need not approximate 1/√t. Failure documents the
    law family honestly; it does not gate overall_passed (which tracks C1+C2).
````

## criterion_benna_fusi_sqrt_t — original line 176 (docstring)

````text
    The fit is restricted to the strictly-decaying TRANSIENT regime (same
    transient_points filter as C1/C3), excluding the permastore plateau. The
    plateau is a SEPARATE phenomenon (Bahrick floor, tested by C2), not part of
    the decay law; including it would force any monotone law to fail for the
    wrong reason (a power law a·t^-b can represent neither a ceiling at 1.0 nor a
    floor). The mixture floor is the equal-weight mean of the per-profile
    permastore floors.
````

## module — original line 11 (comment)

````text
# Signal profiles. effective_stage derives the terminal stage from these.
# source: effective_stage() gates in pg_schema.py (imp>0.3; acc≥1 or imp>0.4;
# acc≥3 for consolidated when schema<0.5).
````

## module — original line 45 (comment)

````text
# source: Bahrick 1984 permastore + pg_schema consolidated stage_floor.
````

## module — original line 47 (comment)

````text
# Collapse threshold for an unprotected labile trace at 365d (forgetting
# preserved). source: engineering default — 1% of heat_base is "gone".
````

## module — original line 50 (comment)

````text
# Power-law exponent plausibility band. source: Wixted&Ebbesen 1991 (~0.1-0.5),
# Anderson&Schooler 1991 (d≈0.5), Benna&Fusi 2016 (b≈0.5).
````

## module — original line 53 (comment)

````text
# Benna&Fusi √t law-family band: the cascade / continuum-of-timescales
# prediction is specifically h ∝ 1/√t, a power law with exponent ≈ 0.5.
# source: Benna&Fusi 2016 (Nat.Neurosci. 19:1697 — SNR∝1/√t from a density of
# timescales p(τ)∝1/τ); Anderson&Schooler 1991 (ACT-R d≈0.5). The ±0.1
# half-width around 0.5 is an engineering tolerance on the canonical exponent,
# narrower than the generic plausibility band above (which only asks "small b").
````

## module — original line 62 (comment)

````text
# Upper cut just below heat_base (1.0): excludes the pre-decay plateau so both
# models fit the strictly-decaying regime only.
# source: transient_points docstring ("heat in (floor·1.05, heat_base)"); the
# 1e-4 standoff from heat_base is a pre-existing tuned value, extracted
# unchanged (#197 family 3)
````
