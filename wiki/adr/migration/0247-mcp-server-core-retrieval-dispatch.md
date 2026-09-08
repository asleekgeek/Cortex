---
title: "ADR-0247 — mcp_server/core/retrieval_dispatch.py rationale"
status: accepted
source: mcp_server/core/retrieval_dispatch.py
---

# ADR-0247 — mcp_server/core/retrieval_dispatch.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Dispatch strategy (validated via LoCoMo, LongMemEval, BEAM benchmarks):
  - Simple: balanced 9-signal WRRF (general/semantic/temporal)
  - Mixed: multi-hop with entity bridging (multi-hop intent)
  - Deep: BM25-primary + entity-weighted (entity/factual queries)
````

## module — original line 8 (docstring)

````text
Pure business logic -- no I/O. Takes signals as data.

````

## _instruction_weights — original line 152 (docstring)

````text
    Instructions have distinctive lexical patterns ("always", "never", "must").
    BM25 IDF weighting surfaces rare directive keywords that vector similarity
    misses. Reduced vector weight avoids dilution by topic-adjacent content.
    
````

## module — original line 24 (comment)

````text
# Ranking multiplier applied to a memory whose capture origin is not trusted
# (issue #368). Mirrors the _DECAY_FACTOR_OVERRIDE pattern in
# core/thermodynamics.py: a calibration sweep varies it per cell through the
# environment, and production reads the calibrated default.
#
# source: docs/provenance/trust-factor-calibration.md §Results — the largest
# W defending 4/4 adversarial scenarios while all four gated floors hold.
# Both arms of the pre-registered rule, measured before this value was picked:
#   adversarial (benchmarks/lib/trust_factor_sweep.py, artefact
#     benchmarks/results/trust-factor-sweep/adversarial/adversarial-sweep.json):
#     1.0 -> 0/4, 0.75-0.95 -> 2/4, 0.20-0.70 -> 4/4
#   floors (5 reproduce.sh cells, benchmarks/results/trust-factor-sweep/
#     20260809T085409Z/, git_sha 66d2628f): at W=0.7, LME 0.9820/0.9178 and
#     LoCoMo 0.9329/0.8181 — 4/4 PASS, margins +0.0000/+0.0038/+0.0179/+0.0131
# 0.75 and above defend only 2/4; anything below 0.7 buys no extra defence and
# costs more ranking distortion, which is why the rule asks for the largest.
````

## module — original line 75 (comment)

````text
# strict=True: WRRF requires exactly one weight per signal. Without it,
# zip silently truncates if lengths drift (e.g., upstream removes a
# signal but forgets the weight vector), silently dropping signals or
# weights from the fusion. The paper's WRRF claim depends on this
# invariant; strict surfaces a violation as ValueError instead of
# degrading the score silently.
````

## inline — original line 257 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("retrieval_dispatch.multihop")
````

## inline — original line 264 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("retrieval_dispatch.rerank_wrapper")
````
