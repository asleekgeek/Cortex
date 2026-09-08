---
title: "ADR-0831 — benchmarks/gate_precision/run_benchmark.py rationale"
status: accepted
source: benchmarks/gate_precision/run_benchmark.py
---

# ADR-0831 — benchmarks/gate_precision/run_benchmark.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Gate-precision benchmark — flat vs hierarchical write-gate novelty scoring.
````

## module — original line 3 (docstring)

````text
The three retrieval benchmarks (LongMemEval/LoCoMo/BEAM) ingest with
``is_benchmark=True``, which calls ``store.insert_memory`` directly and
NEVER ``evaluate_gate`` — so they cannot detect a regression in the write
gate. This benchmark exercises the gate itself: it measures how well each
novelty scorer separates genuinely novel content from duplicates of
already-stored content.
````

## module — original line 10 (docstring)

````text
Methodology:
  1. Extract distinct conversational messages (>= 80 chars) from the real
     LongMemEval-S corpus (Wu et al., ICLR 2025). No fabricated data.
  2. SEED set (150 distinct messages) warms the store via the production
     ingest path (decompose=False so stored content is verbatim).
  3. POSITIVES (100 held-out distinct messages): novel by construction —
     label = accept.
  4. NEGATIVES (100 duplicates of SEED entries): exact copies plus
     trivially perturbed copies (trailing space / one-word synonym swap).
     A duplicate of stored content is non-novel BY DEFINITION — labels
     are definitional, not invented.
  5. Run the production ``evaluate_gate`` on every candidate, twice:
     flat mode (CORTEX_MEMORY_WRITE_GATE_HIERARCHICAL unset) and
     hierarchical mode (=1), each against an identically re-seeded store.
````

## module — original line 25 (docstring)

````text
Metric: ROC-AUC of the gate's novelty score (positive class = novel).
AUC equals the Wilcoxon-Mann-Whitney statistic (Hanley & McNeil 1982,
Radiology 143(1)) — threshold-independent, so it measures exactly the
thing the flag changes: the score. Secondary: accept-accuracy at the
default threshold (WRITE_GATE_THRESHOLD = 0.4) and the production gate
decision (which includes bypass + calibration drift, reported for
observability).
````

## module — original line 33 (docstring)

````text
PASS criterion (build spec, user decision 2026-06-11):
    AUC_hierarchical >= AUC_flat - 0.02   (noise band)
````

## module — original line 36 (docstring)

````text
Reproducibility: fixed RNG seed for sampling/order, single process,
clean dedicated DB (run with DATABASE_URL=postgresql://127.0.0.1:5432/cortex_gateeval),
identical candidate order in both modes so in-process calibration drift
(write_gate_calibration) is order-fair.
````

## module — original line 41 (docstring)

````text
Run:
    DATABASE_URL=postgresql://127.0.0.1:5432/cortex_gateeval \
        python3 benchmarks/gate_precision/run_benchmark.py

````

## extract_corpus — original line 88 (docstring)

````text
    Haystack sessions are shared across questions, so iterate unique
    session ids in file order; dedupe contents on a whitespace/case
    normalised key. Deterministic given the file.
    
````

## _set_mode — original line 159 (docstring)

````text
Toggle the hierarchical flag and bust the settings/calibration caches.
````

## roc_auc — original line 211 (docstring)

````text
    Hanley & McNeil (1982): AUC = P(score_pos > score_neg) with ties
    counted half. Average ranks handle ties exactly.
    
````

## inline — original line 77 (comment)

````text
# reproducibility anchor (arbitrary fixed value, not tuned)
````

## inline — original line 78 (comment)

````text
# build spec noise band, user decision 2026-06-11
````

## inline — original line 151 (comment)

````text
# order-fair calibration drift, same in both modes
````

## inline — original line 179 (comment)

````text
# store verbatim so duplicates are duplicates
````

## module — original line 241 (comment)

````text
# Accuracy at the static default threshold (spec metric, deterministic).
````

## module — original line 247 (comment)

````text
# Production decision accuracy, excluding bypasses (gate didn't decide).
````
