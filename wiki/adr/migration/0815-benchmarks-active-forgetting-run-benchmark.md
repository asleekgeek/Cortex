---
title: "ADR-0815 — benchmarks/active_forgetting/run_benchmark.py rationale"
status: accepted
source: benchmarks/active_forgetting/run_benchmark.py
---

# ADR-0815 — benchmarks/active_forgetting/run_benchmark.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Active-forgetting benchmark — two independent DA forgetting circuits (A2).
````

## module — original line 3 (docstring)

````text
Acceptance instrument for Tier-A item A2: a consolidation settlement pass that,
faithful to the *Drosophila* dopaminergic active-forgetting literature, applies
TWO anatomically/molecularly DISTINCT forgetting circuits — not a severity
ladder. Full design rationale lives in ADR-017; this docstring fixes only the
testable contract.
````

## module — original line 9 (docstring)

````text
This revision replaces a synthetic-abstraction benchmark that abstracted
``chronic`` into a hand-labelled [0, 1] value and so NEVER exercised the
raw-similarity → chronic construction. Against the live 6989-memory corpus that
omission hid a saturation bug: a plain noisy-OR over the 10 nearest newer
neighbours marked 46% of the corpus PERMANENT-stale in one cycle and never fired
the transient circuit. Two load-bearing changes close that gap:
````

## module — original line 16 (docstring)

````text
  - PERMANENT fixtures now carry RAW newer-neighbour similarity lists and the
    benchmark computes ``chronic`` through the core ``chronic_interference``
    (redundancy-gated excess noisy-OR), so the aggregator is exercised
    end-to-end. A non-saturation fixture makes the old failure fail loudly forever.
  - PERMANENT firing is SUSTAINED (a leaky integrator over cycles), so it is
    tested by S1–S5 *time-series* fixtures from which ``derive_thresholds`` reads
    the leak λ and accumulation threshold Θ_accum as the max-margin pair
    reproducing every label.
````

## module — original line 25 (docstring)

````text
Primary sources (open-access via PMC; quotes verified against raw text):
  - Sabandal, Berry & Davis (2021), Nature 591:426-430 (PMC8522469): transient
    and permanent forgetting are "two separate DA-based circuits"; transient
    (DAMB / PPL1-α2α'2) "blocks retrieval" and is "triggered by interfering
    stimuli presented just prior to retrieval", recovering spontaneously;
    permanent (PPL1-γ2α'1 / Rac1) erodes the trace. Sustained transient
    stimulation did NOT convert to permanent loss ("returned to normal by day 14").
    Transient forgetting acts on consolidated PSD-LTM ⇒ it is STAGE-INDEPENDENT.
  - Davis & Zhong (2017), Neuron 95:490-503 (PMC5657245): "This does not
    necessarily mean that consolidated memories are immune … just much more
    resistant" ⇒ GRADED resistance, not a hard immunity gate. The intrinsic
    forgetting DA signal is "ongoing", "increased robustly with locomotor
    activity"/sensory input (interference) and "inhibit[ed]" by "sleep and rest".
  - Berry, Phan & Davis (2018), Cell Reports 25:651-662.e4 (PMC6239218): "strong
    memories … more resistant … weaker memories … more vulnerable" — ordinal
    ONLY; no quantitative strength→rate law exists in any of these papers.
````

## module — original line 42 (docstring)

````text
Benchmark-FIRST rationale: no biological rate constant exists at hours/days, so
every threshold traces to "source: benchmark <path>". This file IS that source —
the labelled fixtures fix ground truth and ``derive_thresholds`` reads
τ_dup-provenance, (λ, Θ_accum), X and W off them; the core
(mcp_server/core/active_forgetting.py) bakes them and is verified here.
````

## module — original line 48 (docstring)

````text
Run:
    Cortex/.venv/bin/python3 benchmarks/active_forgetting/run_benchmark.py

````

## derive_thresholds — original line 295 (docstring)

````text
    (λ, Θ_accum) — grid-search the leak λ; for each, the firing fixtures impose a
    floor (accum at their required-fire cycle) and the never/recovery fixtures a
    ceiling (their peak / recovered-tail accum). The admissible band is
    ``ceiling < Θ ≤ floor``; the chosen λ maximises ``floor − ceiling`` and Θ is
    its midpoint — the 2-D max-margin separator for a by-construction labelled set.
````

## fixture_non_saturation — original line 392 (docstring)

````text
A full field of background neighbours stays at chronic 0; one exact
    duplicate alone goes high. The exact guard against the 46%-saturation bug.
````

## fixture_consolidated_graded_not_immune — original line 473 (docstring)

````text
Consolidated RESISTS permanent even under sustained strong chronic (graded),
    yet is NOT globally immune: the transient circuit still fires on it
    (Davis&Zhong 2017 + Sabandal 2021).
````

## fixture_transient_stage_independent — original line 513 (docstring)

````text
An acute recent interferer triggers transient regardless of stage
    (stage is not even an argument; Sabandal 2021).
````

## fixture_circuits_independent_no_conversion — original line 533 (docstring)

````text
The circuits read disjoint signals; a purely transient (acute-only,
    chronic 0) history NEVER becomes permanent (Sabandal: no conversion).
````

## fixture_hippocampal_dependency_non_regression — original line 572 (docstring)

````text
(i) NON-REGRESSION: a cortically-independent memory (dep=0.0, the
    default cortical_availability produces no modulation) under S1's sustained
    interference still fires PERMANENT by cycle 3 — identical to the baked
    series_reproduced() result with no CLS-B involvement. If this ever
    diverges from the baseline S1 trajectory, gate C has changed pre-existing
    (non-CLS-B) forgetting behaviour, which is the one thing it must never do.
    
````

## fixture_hippocampal_dependency_protects — original line 596 (docstring)

````text
(ii) PROTECTION: the SAME S1 interference applied to a fully
    hippocampally-dependent memory (dep=1.0, today's production value for
    100% of memories — see decision memory 4261278/4261481) accumulates
    strictly less pressure every cycle and does NOT fire by S1's fire_by=3 —
    it resists longer under identical interference, without being exempted
    (the accumulator still grows, just more slowly).
````

## fixture_hippocampal_dependency_never_zeroes_pressure — original line 623 (docstring)

````text
Regression guard on the constant itself: at dep=1.0 (today's prod
    value everywhere) the modulated pressure must be STRICTLY POSITIVE, not
    zero — a naive (1-dep) factor would zero the permanent circuit corpus-wide
    until the CLS-B producer has decayed dependency, which is the exact
    regression this design rejected (see core.active_forgetting docstring).
````

## module — original line 81 (comment)

````text
# ── Permanent SIGNAL pool ───────────────────────────────────────────────────────
# Each row carries the RAW newer-neighbour cosine list ``newer_sims`` and the
# expected redundancy-gated ``chronic`` BAND (zero vs positive). This exercises
# the aggregator that the old abstracted pool never touched. τ_dup = 0.85, so only
# genuine near-duplicates (sim ≥ 0.85) contribute; the ~0.5 background band is
# excluded. ``acute`` (strongest newer sim, its age) feeds the disjoint transient
# circuit and lets the same neighbour list drive both circuits.
````

## module — original line 124 (comment)

````text
# ── Permanent TIME-SERIES pool (S1–S5): derives (λ, Θ_accum) ─────────────────────
# Each series is a per-cycle list of (chronic, recently_active) at a fixed stage.
# ``fire_by`` is the cycle index (1-based) at which the memory MUST be stale;
# ``recovers`` asserts the accumulator leaks back below Θ by the final cycle
# (reinstatement). chronic 0.667 ≈ one 0.95 near-dup ⇒ labile pressure ≈ 0.60.
# per-cycle chronic when a genuine interferer is present (labile pressure 0.60)
````

## module — original line 247 (comment)

````text
# ── CLS-B gate C pool: cortical_availability modulation of the PERMANENT
# circuit (see cortex:remember memory_id 4261603 and core.active_forgetting
# module docstring for the design). Reuses the S1 sustained-interference
# series (same chronic, same stage, same fire_by=3 at dep=0.0) so
# non-regression is checked against the EXACT baked S1 fixture above, not a
# new hand-picked one — the only variable introduced is hippocampal_dependency.
````

## module — original line 283 (comment)

````text
# ── Constant derivation (this benchmark IS the source for the core constants) ─────
````

## module — original line 285 (comment)

````text
# Age ceiling that makes a negative fixture count as "recent", so it isolates the
# overlap axis X from the recency axis W.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 385 (comment)

````text
# Chronic value above which a single near-exact duplicate counts as "high".
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 469 (comment)

````text
# ── Falsifier fixtures (paper predictions; require the core) ──────────────────────
````

## module — original line 604 (comment)

````text
# strict=True: both trajectories are produced by the same _trajectory
# call shape (only hippocampal_dependency differs), so they always
# have equal length.
````
