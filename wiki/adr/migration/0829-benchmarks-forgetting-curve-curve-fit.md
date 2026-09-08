---
title: "ADR-0829 — benchmarks/forgetting_curve/curve_fit.py rationale"
status: accepted
source: benchmarks/forgetting_curve/curve_fit.py
---

# ADR-0829 — benchmarks/forgetting_curve/curve_fit.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Pure curve-fitting helpers for the forgetting-curve fidelity benchmark.
````

## module — original line 3 (docstring)

````text
Two competing models for a retention trajectory h(t) over elapsed hours t:
````

## module — original line 5 (docstring)

````text
  - EXPONENTIAL (single-rate null):  h(t) = a · exp(-b · t)
        linearised as  ln h = ln a - b · t      (OLS of ln h on t)
  - POWER LAW (heavy-tailed):        h(t) = a · t^(-b)
        linearised as  ln h = ln a - b · ln t    (OLS of ln h on ln t)
````

## module — original line 10 (docstring)

````text
The exponential linearisation is exactly what
``mcp_server.core.emergence_metrics._fit_log_linear`` computes — note that
emergence_metrics.compute_forgetting_curve's DOCSTRING calls that a "power
law R=a·t^-b" but its CODE regresses ln(heat) on age (linear t), i.e. it is
the EXPONENTIAL model. This module keeps the two models distinct and adds a
genuine power-law fit (ln h on ln t).
````

## module — original line 17 (docstring)

````text
Model selection follows Wixted & Ebbesen (1991, Psych. Science 2:409): the
falsifiable claim is the ORDERING — does the power law fit human/biomimetic
retention at least as well as a single exponential? We compare both r² and
AIC. Goodness-of-fit (RSS, r², AIC) is evaluated in the COMMON original
h-space (predicted h vs actual h) so the two linearisations are compared
fairly rather than in their own transformed spaces.
````

## module — original line 24 (docstring)

````text
Pure logic — no I/O.

````

## module — original line 31 (comment)

````text
# ΔAIC convention: models within 2 of the minimum are empirically
# indistinguishable; 4-7 considerably less support; >10 essentially none.
# source: Burnham & Anderson (2002), Model Selection and Multimodel
# Inference, 2nd ed., §2.6 (the "rules of thumb" for ΔAIC).
````

## module — original line 37 (comment)

````text
# Magnitude at or below which a float counts as zero, guarding the degenerate
# cases (singular OLS denominator, zero total variance, zero decay rate).
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 49 (comment)

````text
# strict=True: xs/ys are paired observations for OLS; unequal lengths
# would mean mismatched (x, y) pairs, a data bug worth raising on.
````
