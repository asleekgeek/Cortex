# ADR-0087: benchmarks/lib/run_e1_v3_locomo.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/run_e1_v3_locomo.py`; original SHA-256 `12e71c0f9b6f8dd02d51ea03b40594ebdc1a953973d5919c4f1fe1459658f241`.

## Original docstring, lines 1–36

````text
"""E1 v3 — LoCoMo per-mechanism ablation runner (two-baseline design).

Drives `benchmarks/locomo/run_benchmark.py` once per row, serially, against
the same PG instance. Each row writes its result JSON via `--results-out`.
After all rows complete, an aggregate `summary.csv` and `manifest.json`
are written.

Output: benchmarks/results/ablation/locomo_v3/

Why serial: the harness mutates a shared PG database (db.clear() per
conversation). Parallel rows would contaminate each other's haystacks.

Two-baseline design (per docs/benchmarks/e1-v3-locomo-smoke-finding.md, Option B):

LoCoMo session timestamps are real 2023 conversation dates. At 2026 wall
time, every loaded memory is ≈3 years old. Cortex's compression gates
(COMPRESSION_GIST_AGE_HOURS=168, COMPRESSION_TAG_AGE_HOURS=720) fire on
absolute timestamp diff, so consolidation collapses the corpus to gists/
tags on first pass. Smoke: MRR 0.866 (no consolidation) → 0.222 (with).

To preserve honest per-mechanism evidence:

- Longitudinal read-path mechanisms (RECONSOLIDATION, CO_ACTIVATION,
  ADAPTIVE_DECAY) are ablated against BASELINE_NO_CONSOLIDATION. These do
  not require a consolidation pass — their effect is heat / access / co-
  access tracking that accumulates via cross-question reads.

- Consolidation-only mechanisms (CASCADE, INTERFERENCE,
  HOMEOSTATIC_PLASTICITY, SYNAPTIC_PLASTICITY, MICROGLIAL_PRUNING,
  TWO_STAGE_MODEL, EMOTIONAL_DECAY, TRIPARTITE_SYNAPSE, SCHEMA_ENGINE) are
  ablated against BASELINE_WITH_CONSOLIDATION. Each row's delta is the
  mechanism's role within the observed (timestamp-collision) regime;
  this is documented as a benchmark-property disclosure in the writeup.

14 rows total. Estimated wall ~7h.
"""
````

## Original comment, lines 297–298

````text
# source: CLAUDE.md sanity tolerance — "±0.05 around 0.794" for the
# BASELINE_NO_CONSOLIDATION LoCoMo MRR headline (see the check below)
````

