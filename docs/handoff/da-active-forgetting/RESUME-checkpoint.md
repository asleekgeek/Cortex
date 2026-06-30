---
description: "A2 active-forgetting: benchmark+core GREEN; handler signal-computation Q pending user clarify"
---
## Checkpoint — session 375bf26a — 2026-06-29 (branch feat/da-active-forgetting off main)

### Goals
A2 = DA active forgetting, FAITHFUL to papers (user HARD RULE: no divergence, no
invented numbers; benchmark-first). After A2: task #10 systematic faithfulness
audit of all ~23 mechanisms; open PRs for A1(98313d1)+A3(e305ef9); A4 boundaries;
delete dead core/replay_selection.py compute_sequence_priority.

### DONE this session (NOT committed; user commits only when asked)
Research agent VERIFIED quotes vs raw PMC. Findings drove a full redesign:
- Q1 consolidated = GRADED-resistant NOT immune (Davis&Zhong 2017; ARM forgotten
  by separate Cdc42 path). Q2 transient vs permanent = TWO DISTINCT CIRCUITS, not
  a ladder; Sabandal 2021 TESTED+REJECTED transient→permanent conversion;
  transient is STAGE-INDEPENDENT (acts on consolidated LTM). Q3 salience effect is
  ORDINAL ONLY (no rate law) ⇒ NO (1-heat) term; resistance rides on stage.
- User chose "Two independent circuits" model.
- `benchmarks/active_forgetting/run_benchmark.py` (432 ln) PASSED=True: 15/15
  labels, 7/7 falsifiers. Derived constants from labeled data: Tp=0.3275,
  X(acute_overlap)=0.575, W(acute_age_hrs)=13.0. Imports core directly (A1 style).
- `mcp_server/core/active_forgetting.py` (120 ln): forgetting_pressure(stage,
  chronic_interf)=chronic×cascade_stage_vulnerability; is_permanent_forgetting(
  stage,chronic,is_pinned,recently_active) [pin/sleep gate, pressure≥Tp];
  is_transient_forgetting(acute_overlap,acute_age_hrs,is_pinned,recently_active)
  [stage-INDEPENDENT, overlap≥X AND age≤W]. Constants cite `source: benchmark`.

### File references
- mcp_server/core/active_forgetting.py:1-120 (pure, done)
- benchmarks/active_forgetting/run_benchmark.py:1-432 (POOL P1-8/T1-5/B1/N1; derive_thresholds; fixtures)
- mcp_server/core/cascade_stages.py:135 get_stage_properties_by_name (.interference_vulnerability: labile .9/early_ltp .5/late_ltp .2/consolidated .05 — REUSED, paper-grounded)
- mcp_server/infrastructure/pg_store.py:751 mark_memory_stale (reversible write primitive, EXISTS)
- mcp_server/handlers/consolidation/sleep.py:21 run_deep_sleep (A2 handler mirrors this pattern; store.search_vectors for neighbors)
- /private/tmp scratchpad a2_paper_findings.md (may not survive clear)

### Errors and fixes
- File >500 → pre-commit gate fails. Kept benchmark 432, core 120. Trim prose→ADR.
- pytest tests_py/ HANGS on DB collect → run specific files + DB-free bench only. Use .venv/bin/python3.
- Untracked NOT mine: results/adr015/, results/gate_precision/20260629-090522.json.

### Current state
Pure logic done + GREEN. Core UNWIRED (only benchmark imports it) — wiring is the
remaining high-stakes I/O half of task #2. Was about to ask how the handler
computes signals from PG; user REJECTED the AskUserQuestion to CLARIFY first. I
asked them what to clarify (entity-overlap vs cosine? "newer"=created_at>target?
chronic/acute same query? avoid agg constant? latency). AWAITING their clarify.

### PROGRESS 2026-06-29 (step 1 DONE, NOT committed)
Handler built + wired + GREEN. All DB-FREE checks pass:
- mcp_server/handlers/consolidation/forgetting.py (147 ln): _noisy_or(sims)=
  1−∏(1−clamp(s)) pure+tested; _evaluate_memory (chronic noisy-OR, acute=
  strongest newer neighbor, is_pinned=is_protected|heat≥1, recently_active from
  replay); run_forgetting_cycle streams iter_memories_for_decay, ablation-gated
  Mechanism.ACTIVE_FORGETTING, hasattr-guards SQLite. Permanent→mark_memory_stale;
  transient→update_memory_heat(heat×(1−acute_overlap)) — magnitude from MEASURED
  interferer salience (Berry 2018 ordinal), NO invented constant. NEIGHBOR_K=10
  (I/O bound, cites search_vectors default).
- pg_store.py:832 search_newer_neighbors(emb,after,exclude_id,top_k)→[(sim,age_h)]
  (created_at>%s::timestamptz, NOT is_stale; 1−(<=>) sim; EXTRACT hrs). The
  "newer" SQL filter is the I/O half; noisy-OR aggregation stays in handler (SRP).
- sleep.py: _apply_dream_replay now returns replayed ids; run_deep_sleep adds
  "replayed_ids" (the recently_active/sleep-protect signal).
- consolidate.py: deep block pops replayed_ids (plumbing, kept out of MCP resp),
  runs run_forgetting_cycle AFTER replay, skips if replay errored.
- ablation.py +ACTIVE_FORGETTING (28→29); ablation_report.py order +entry;
  CLAUDE.md count + module line updated.
- tests_py/handlers/test_forgetting_cycle.py (17 tests, DB-free): noisy-OR maths
  (empty/single/closed-form/grows-with-count/monotone/bounded/clamp±/order) +
  fake-store wiring (transient scales heat, permanent stale, pin/sleep exempt,
  old-acute no-fire, ablation, unsupported-store). ALL PASS. test_ablation GREEN.
  active_forgetting benchmark PASSED=True (15/15 labels, 7/7 falsifiers).
NOT YET verified (needs live PG): the SQL itself + consolidate deep wiring +
heat/stale writes. That is the benchmark-gate step below.

### Next steps (DECIDED — no cheap-then-replace; build the faithful design ONCE)
Signal-computation decision settled with user: chronic must ACCUMULATE with count
AND strength (Davis&Zhong "ongoing" signal). MEAN cosine = WRONG (no growth w/
count). count-above-FLOOR = invented constant. CHOSEN: chronic_interference =
noisy-OR 1−∏(1−sim_i) over NEWER overlapping neighbors (Pearl 1988; param-free,
[0,1], monotone in count+strength). acute_overlap=max sim to newer; acute_age=hrs.
Benchmark UNCHANGED (chronic is by-construction [0,1] stand-in like A1 _gain; Tp
transfers; aggregation lives in HANDLER w/ own test — SRP). Two separate gates:
FAITHFUL + EARNS-ITS-PLACE. Return metric = LongMemEval knowledge-update sub-score
↑ while R@10/MRR flat (forgetting can only be neutral/negative on pure-recall
benchmarks, so no-regression alone proves nothing — must show the update upside).
1. Build handlers/consolidation/forgetting.py ONCE: per memory compute chronic
   (noisy-OR over newer neighbors via store.search_vectors restricted created_at>
   target), acute_overlap+acute_age_hours (strongest recent newer), recently_active
   (replayed/accessed this cycle), is_pinned (is_protected OR heat>=1.0); call core;
   effects permanent→mark_memory_stale(True), transient→reduce heat. Handler-level
   test for the noisy-OR computation. Wire into consolidate() AFTER replay
   (sleep-protect order) + ablation unit.
2. ADR-017 (full rationale — benchmark docstring was trimmed for it) +
   docs/provenance/paper-implementation-audit.md entry.
3. Benchmark gates: re-run active_forgetting (green) + LongMemEval on/off (update
   sub-score ↑, R@10/MRR ≥ baseline) + LoCoMo/BEAM no-regression.

### Resume contract
Read this + ≤1 targeted search. Do NOT re-read files summarized above.
