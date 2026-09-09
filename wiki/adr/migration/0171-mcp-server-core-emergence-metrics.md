---
title: "ADR-0171 — mcp_server/core/emergence_metrics.py rationale"
status: accepted
source: mcp_server/core/emergence_metrics.py
---

# ADR-0171 — mcp_server/core/emergence_metrics.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Split from emergence_tracker.py to keep files under 300 lines.
Contains the forgetting curve analysis (log-linear regression) and the
aggregate emergence report generator.
````

## _fit_log_linear — original line 103 (docstring)

````text
Fit log-linear regression: log(heat) = log(a) - b * age via OLS.
````

## _fit_quality_for — original line 143 (docstring)

````text
    Source: darval's v3.13.2 P3 — "should emergence.forgetting_curve
    gate its derived metrics on a minimum r²?" Answer: emit a label,
    let consumers decide whether to display/ignore.
````

## _fit_quality_for — original line 147 (docstring)

````text
    Thresholds chosen to be conservative:
      r² < 0.10 → "poor"     — the model explains < 10% of variance;
                               half_life_hours is not meaningful.
      r² < 0.50 → "weak"     — some signal, but a single exponential
                               is an oversimplification.
      else     → "good"      — explains ≥ 50% of variance.
    
````

## compute_forgetting_curve — original line 175 (docstring)

````text
    Fits a single EXPONENTIAL R(t) = a · exp(-b · t) by OLS of ln(heat) on
    linear age (see ``_fit_log_linear``); the returned ``curve_type`` is
    ``"exponential"``. NOTE: this is the exponential null, not a power law —
    the biological power-law form R(t) = a · t^(-b) (Wixted & Ebbesen 1991;
    Anderson & Schooler 1991) requires regressing ln(heat) on ln(age), which
    this does NOT do. For the genuine power-law fit and the falsifiable
    power-vs-exponential model comparison, see
    ``benchmarks/forgetting_curve/curve_fit.py``.
````

## _forgetting_from_bin_means — original line 202 (docstring)

````text
    Shared by ``compute_forgetting_curve`` (list path) and the streaming
    emergence report, which accumulates the bins online and so never holds the
    raw point set.
    
````

## generate_emergence_report — original line 250 (docstring)

````text
    Thin wrapper over ``generate_emergence_report_streamed`` (one chunk) so the
    list path and the streaming path can never diverge.
    
````

## _schema_acceleration_from_agg — original line 259 (docstring)

````text
    Mirrors emergence_tracker.compute_schema_acceleration_metric exactly, but
    from ``{count, consolidated, time_sum}`` per cohort instead of two lists.
    
````

## generate_emergence_report_streamed — original line 327 (docstring)

````text
    Every metric in the legacy report is an aggregate (binned forgetting curve,
    schema/phase cohort sums, stage counts, interference mean), so the whole
    report needs only O(num_bins + num_stages) RAM regardless of corpus size.
    
````

## module — original line 15 (comment)

````text
# Numerical guard against division by a near-zero denominator.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 20 (comment)

````text
# source: thresholds documented in _fit_quality_for docstring
# (darval's v3.13.2 P3)
````

## module — original line 25 (comment)

````text
# Minimum raw points / bins entering the log-linear fit.
# source: pre-existing tuned values, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 31 (comment)

````text
# Heat below this floor is treated as negligible (log-domain floor and
# age-binning cutoff).
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 37 (comment)

````text
# Schema-match cohort thresholds for the streaming report.
# source: pre-existing tuned values, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 43 (comment)

````text
# source: structural — normalized theta phase lies in [0, 1); the first
# half-cycle is the encoding phase
````

## module — original line 47 (comment)

````text
# Minimum heat for a memory to count as "alive" in phase cohorts.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
