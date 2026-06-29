# Handoff — A2 DA active forgetting (WIP)

Cross-machine continuation bundle. This branch (`wip/da-active-forgetting`) is a
**work-in-progress snapshot**, not for merge. It carries the checkpoint and the
verified research that normally live outside the repo (`~/.claude/memories/` and
the session scratchpad), so the work can resume on another computer.

## Files here
- `RESUME-checkpoint.md` — the session resume contract (goals, decisions,
  progress, next steps). **Read this first.**
- `a2-paper-findings.md` — research-agent findings verified against raw PMC that
  drove the two-independent-circuits design (Davis & Zhong 2017; Sabandal 2021;
  Berry 2018; Cervantes-Sandoval 2017).

## State at snapshot
Step 1 of the resume contract is **DONE and GREEN on all DB-free checks**, NOT
yet verified against live PostgreSQL, NOT reviewed, NOT merged.

Implemented this branch:
- `mcp_server/core/active_forgetting.py` — pure two-circuit decisions
  (permanent Rac1 pressure ≥ Tp; transient DAMB overlap ≥ X AND age ≤ W).
- `mcp_server/handlers/consolidation/forgetting.py` — composition root:
  per-memory chronic noisy-OR `1−∏(1−simᵢ)` over newer overlapping neighbors,
  acute interferer, pin/sleep gates; permanent → `mark_memory_stale(True)`,
  transient → `heat × (1 − acute_overlap)` (magnitude rides measured salience,
  no invented constant).
- `mcp_server/infrastructure/pg_store.py::search_newer_neighbors` — the
  `created_at > target` KNN (I/O half; aggregation stays in the handler, SRP).
- `mcp_server/handlers/consolidation/sleep.py` — `run_deep_sleep` returns
  `replayed_ids` (the sleep-protection / `recently_active` signal).
- `mcp_server/handlers/consolidate.py` — runs the forgetting cycle AFTER replay.
- `mcp_server/core/ablation.py` + `ablation_report.py` — `ACTIVE_FORGETTING`
  ablation unit (28 → 29).
- `tests_py/handlers/test_forgetting_cycle.py` — 17 DB-free tests (noisy-OR
  maths + fake-store wiring). All pass; `active_forgetting` benchmark PASSED.

## Next steps (from the checkpoint)
1. Verify against live PostgreSQL: the `search_newer_neighbors` SQL, the
   `consolidate(deep=True)` wiring, and the heat/stale writes.
2. Benchmark gates: re-run `benchmarks/active_forgetting` (green) + LongMemEval
   on/off (knowledge-update sub-score ↑, R@10/MRR ≥ baseline) + LoCoMo/BEAM
   no-regression.
3. ADR-017 (full rationale) + `docs/provenance/paper-implementation-audit.md`
   entry.

## To resume on the other machine
```bash
git fetch origin && git checkout wip/da-active-forgetting
# read docs/handoff/da-active-forgetting/RESUME-checkpoint.md, then continue
```
Run DB-free checks with the project venv:
```bash
.venv/bin/python3 -m pytest tests_py/handlers/test_forgetting_cycle.py -q
.venv/bin/python3 benchmarks/active_forgetting/run_benchmark.py
```
