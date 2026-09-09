---
title: "ADR-0830 — benchmarks/forgetting_curve/run_benchmark.py rationale"
status: accepted
source: benchmarks/forgetting_curve/run_benchmark.py
---

# ADR-0830 — benchmarks/forgetting_curve/run_benchmark.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Forgetting-curve fidelity benchmark — paper-form validation of effective_heat.
````

## module — original line 3 (docstring)

````text
WHAT THIS TESTS (and why the retrieval benchmarks cannot)
---------------------------------------------------------
LongMemEval / LoCoMo / BEAM and the longitudinal harness measure RANKING,
not the decay LAW: at year-scale ages heat collapses to its stage floor
regardless of law, and on synthetic corpora vector/lexical similarity
dominates ranking so the heat signal is never decisive (A/B on the
longitudinal runner: ±1 hit/100 = noise). The biomimetic forgetting law must
therefore be validated on PAPER FIDELITY — does the curve effective_heat()
produces over real elapsed time match the FORM of published retention curves?
````

## module — original line 13 (docstring)

````text
NON-CIRCULARITY: ground truth = published curve FORMS + parameter ranges, NOT
Cortex's own heat/importance/stage signals. The target is external:
  - Wixted & Ebbesen 1991 (Psych. Sci. 2:409): human forgetting is fit BETTER
    by a power law R=a·t^-b than by a single exponential. Falsifiable claim =
    the ORDERING (power ≥ exponential). b is small, ~0.1-0.5.
  - Anderson & Schooler 1991 / ACT-R: retention follows a power law, d≈0.5.
  - Benna & Fusi 2016 (Nat. Neurosci. 19:1697): cascade synapse decays ∝ 1/√t
    (power law b≈0.5) via a continuum of separated timescales. The α-ladder
    (2.0→1.2→0.8→0.5) is a 4-level discrete analog — does it approximate the
    power law, or just a piecewise/single exponential?
  - Bahrick 1984 (JEP:General 113:1): "permastore" — a residual retention
    floor that persists for decades and does NOT decay to zero.
````

## module — original line 26 (docstring)

````text
ARTIFACT UNDER TEST: effective_heat() + effective_stage() in
mcp_server/infrastructure/pg_schema.py. Probed directly via SQL against a
single synthetic row per signal-profile, varying t_now across an age grid.
````

## module — original line 30 (docstring)

````text
This benchmark CAN FAIL. If the cascade produces only a single exponential
plus a floor (no power-law character), criterion 1 fails — and that is
reported as a (partial) falsification, not hidden.
````

## module — original line 34 (docstring)

````text
Run:
    .venv/bin/python3 benchmarks/forgetting_curve/run_benchmark.py
    .venv/bin/python3 benchmarks/forgetting_curve/run_benchmark.py --quick

````

## module — original line 63 (comment)

````text
# Age grid in hours. Dense in the 0-8h stage-transition window (captures the
# α-ladder) then logarithmic out to 365d (captures the floor regime).
# source: task spec grid (1h,6h,1d,3d,7d,14d,30d,60d,90d,180d,270d,365d)
# enriched with sub-day points to resolve the cascade transitions.
````

## inline — original line 141 (directive-rationale)

````text
# noqa: PLC0415 — deferred: module hard-imports pgvector/psycopg/psycopg_pool at top level; hoisting would break installs without it
````
