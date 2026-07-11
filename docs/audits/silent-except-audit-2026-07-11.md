---
title: Silent-except sweep — 2026-07-11
status: complete (inventory + Class A fixes); Class B backlog tracked, not fully logged
owners: engineer
---

# Silent-except audit (2026-07-11)

## Why this audit exists

Two production incidents in one night, same shape: a broad `except
Exception` guarding a component with a legitimate fallback caught a bug
in the mechanism *itself* and silently disabled it, with zero log
signal, for months (case 1) or since introduction (case 2):

1. **FlashRank reranker** (fix `bb1c581f`, 2026-07-11). `_ensure_reranker()`
   instantiated `flashrank.Ranker` without an explicit `cache_dir`,
   falling back to the library default (`/tmp`). macOS purges `/tmp`;
   the resulting `NoSuchFile` was swallowed by a bare `except Exception`,
   permanently disabling production re-ranking for the rest of the
   process. Six LongMemEval benchmark runs were reported under this
   silently-broken instrument (MRR 0.9163 → 0.8636).
2. **Spreading activation** (`mcp_server/core/recall_pipeline.py:441`,
   fixed on the concurrent branch `feat/spread-activation-scoped-activation`
   — **not touched by this sweep**, per explicit mandate). A
   non-recursive `WITH` in the `spread_activation_memories` PL/pgSQL body
   raised a SQL error on every call since the query was introduced;
   masked by `except Exception: return candidates`, invisible because
   the covering tests were 100% mocked (see "Test debt" below).

**Mandate**: exhaustively inventory every silent `except` on critical
paths (recall / fusion / rerank / write gate / consolidation / embedding
/ ingestion) in `mcp_server/core`, `mcp_server/infrastructure`,
`mcp_server/handlers`, `mcp_server/hooks`; classify each; fix Class A
using the `bb1c581f` pattern generalized into a shared module; add tests
proving the failure is now observable.

**Explicitly out of scope for this sweep** (concurrent branches / recent
merges touching the same lines):
- `mcp_server/core/recall_pipeline.py:441` and
  `mcp_server/core/retrieval_signals.py::_compute_sa` (the
  `spread_activation_memories` call sites) — fixed on
  `feat/spread-activation-scoped-activation`.
- `mcp_server/infrastructure/pg_store_memory_reheat.py`,
  `mcp_server/handlers/consolidation/write_class.py` — being merged on
  `fix/reheat-source-filter`.

## Method

AST-walked every `.py` file under `mcp_server/` (excluding tests),
found every `ExceptHandler` whose `type` unparse contains `Exception` or
`BaseException`, and flagged those whose body contains **no** logging
call (`logger.*`, `_log(`, `.warning(`, `.error(`, `.exception(`,
`print(`) and **no** `raise`. **219 sites** matched across 646 total
`except` handlers in the codebase.

## Classification

- **(A) Component silently skipped on a critical path** — recall /
  fusion / rerank / write-gate / consolidation / embedding / ingestion,
  with a documented-or-undocumented fallback that could stay broken
  indefinitely with zero signal, exactly the `bb1c581f` /
  spread_activation shape. **Fixed in this sweep** (30 sites).
- **(B) Legitimate degraded fallback, needs observability** — best-effort
  behavior that is architecturally sound (a broken diagnostic/AP/wiki
  helper must not break the caller) but currently has no log at all.
  Classified in full below; a bounded subset was instrumented in this
  pass (see "Class B: logged in this pass"); the remainder is tracked as
  backlog with rationale, not touched, to keep this diff's blast radius
  proportional to a one-night sweep.
- **(C) Benign** — cleanup (`conn.close()`, `DEALLOCATE ALL`), parsing
  fallback on genuinely optional/legacy data, or already effectively
  observable (return value surfaces the error to the caller, e.g.
  `doctor.py`'s `Check(..., f"{type(exc).__name__}: {exc}", ...)`).
  Left as-is.

## The fix (Class A)

New shared module: `mcp_server/observability/silent_failure.py`.
`note(component: str, exc: BaseException) -> None` logs a `WARNING` on
the **first** failure of a named component per process (anti-spam on
repeats), unconditionally bumps a
`cortex_silent_failures_total{component=...}` Prometheus counter (so
failure *rate* survives the anti-spam gate), and `status()` exposes
`{component: {last_error, count}}` for a health check / doctor command.
This generalizes the `bb1c581f` pattern (per-mechanism `RerankerStatus`
dataclass + logger.warning) into one reusable primitive instead of
duplicating a status dataclass per mechanism — SRP: one component,
"record + report silent failures", used by ~20 call sites across 5
files rather than invented once per file.

**Behavior is unchanged everywhere** — every fixed site still returns
exactly the same fallback value it did before; only observability
changed (Move 6 contract: reproduction unaffected, only Class A sites
touched, `git diff` shows added `except ... as exc:` + one
`silent_failure.note(...)` line per site, nothing else).

## Class A sites — FIXED (30)

| # | File:Line | Component | Family |
|---|---|---|---|
| 1 | `core/pg_recall.py:59` | `pg_recall.active_goal` — active-goal trigger promotion | recall |
| 2 | `core/pg_recall.py:80` | `pg_recall.user_mood` — mood-congruent recall signal | recall |
| 3 | `core/reranker.py:384` | `reranker.rerank_call` — FlashRank inference call (distinct from `bb1c581f`'s load-failure fix) | rerank |
| 4 | `core/reranker.py:415` | `reranker.raw_ce_score` — Platt-calibration sample collection | rerank |
| 5 | `core/retrieval_dispatch.py:232` | `retrieval_dispatch.multihop` — multi-hop sub-query expansion | fusion |
| 6 | `core/retrieval_dispatch.py:239` | `retrieval_dispatch.rerank_wrapper` — outer rerank call wrapper | fusion/rerank |
| 7 | `core/retrieval_signals.py:50` | `retrieval_signals.hopfield` — Hopfield attention signal | recall |
| 8 | `core/retrieval_signals.py:60` | `retrieval_signals.hdc` — HDC bipolar-vector signal | recall |
| 9 | `core/retrieval_signals.py:103` | `retrieval_signals.successor_representation` — SR/co-access signal | recall |
| 10 | `core/write_gate.py:181` | `write_gate.oscillatory_context` — theta-phase encoding gate | write gate |
| 11 | `core/write_gate.py:216` | `write_gate.neuromodulation` — coupled DA/NE/ACh/5-HT modulation | write gate |
| 12 | `core/write_gate.py:234` | `write_gate.emotional_tagging` — valence/importance tagging | write gate |
| 13 | `core/write_gate.py:282` | `write_gate.pattern_separation` — DG orthogonalization | write gate |
| 14 | `core/write_gate.py:305` | `write_gate.schema_match` — schema-engine matching | write gate |
| 15 | `core/write_gate.py:331` | `write_gate.active_goal_read` — trigger read (write-side mirror of #1) | write gate |
| 16 | `core/write_gate.py:335` | `write_gate.active_goal_build` — goal-vector construction | write gate |
| 17 | `core/write_gate.py:393` | `write_gate.goal_maintenance` — A3 novelty re-weight | write gate |
| 18 | `core/write_gate.py:442` | `write_gate.habituation` — E1 habituation/sensitization | write gate |
| 19 | `core/write_post_store.py:133` | `write_post_store.synaptic_tagging` — Frey & Morris retroactive tagging | consolidation |
| 20 | `core/write_post_store.py:202` | `write_post_store.entity_id_resolution` | consolidation |
| 21 | `core/write_post_store.py:217` | `write_post_store.shared_entities_lookup` | consolidation |
| 22 | `core/write_post_store.py:316` | `write_post_store.engram_allocation` — competitive slot allocation | consolidation |
| 23 | `core/memory_ingest.py:156` | `memory_ingest.entity_extraction` — KG population during ingest | ingestion |
| 24 | `handlers/recall.py:349` | `recall.hebbian_co_activation` — Dragon Hatchling co-activation | recall |
| 25 | `handlers/recall.py:361` | `recall.neuro_symbolic_rules` — production rule application | recall |
| 26 | `infrastructure/pg_store.py:869` | `pg_store.update_memory_value` — B2 RL-value persistence | write gate |
| 27 | `infrastructure/pg_store.py:891` | `pg_store.update_memory_extinction` — E2 extinction persistence | write gate |
| 28 | `handlers/consolidation/cls.py:522` | `cls.causal_edge_persist` — PC-algorithm causal-edge writes | consolidation |
| 29 | `handlers/remember_helpers.py:391` | `remember_helpers.block_supersede_select` — checkpoint/rethink block lookup | write path |
| 30 | `handlers/remember_helpers.py:428` | `remember_helpers.block_supersede_update` — checkpoint/rethink block update | write path |

Sites #29–30 are the same failure shape as the spread_activation
incident: a broken SQL statement is indistinguishable from "no existing
block row", so the caller was silently **inserting a duplicate row**
instead of superseding the checkpoint block — this is the memory
architecture's own `.pending-sync` → Cortex DB replication path.

### DISCOVERY

No site in the Class A list was found to be a **currently broken**
component in production (unlike the spread_activation incident this
audit was triggered by) — every Class A fix is preventive
instrumentation on a mechanism that, as far as this sweep could
determine from static analysis and unit tests, is presently working.
No dead/disabled component requiring a product decision was uncovered
in this pass.

## Tests (caplog, per Class A fix)

New/extended files, all green under `uv run pytest`:

- `tests_py/observability/test_silent_failure.py` — the shared module's
  own contract (first-log, anti-spam, counter, status()). 8 tests.
- `tests_py/core/test_reranker.py` — added
  `TestRerankResultsInferenceFailureIsObservable` (2 tests): proves the
  `rerank_call` and `raw_ce_score` failures fall back exactly as before
  AND are now logged.
- `tests_py/core/test_write_gate.py` — added
  `TestWriteGateFailuresAreObservable` (7 tests): oscillatory context,
  neuromodulation, emotional tagging, schema match, habituation, active
  goal read, and anti-spam-on-repeat.
- `tests_py/core/test_pg_recall_silent_failures.py` (new, 4 tests):
  active-goal and user-mood failure paths, plus the negative case (a
  store missing the optional method is NOT a failure — no log).
- `tests_py/handlers/test_recall_silent_failures.py` (new, 2 tests):
  Hebbian co-activation and neuro-symbolic-rules failures.
- `tests_py/core/test_silent_except_sweep_remaining.py` (new, 9 tests):
  retrieval_dispatch (multihop, rerank wrapper), retrieval_signals
  (hopfield, successor representation), write_post_store (synaptic
  tagging, engram allocation), memory_ingest (entity extraction),
  pg_store (`update_memory_value`, `update_memory_extinction`).
- `tests_py/handlers/consolidation/test_cls_silent_failures.py` (new, 2
  tests): causal-edge persistence, including "one bad edge doesn't
  block the rest of the batch".
- `tests_py/handlers/test_remember_helpers_silent_failures.py` (new, 2
  tests): block-replica SELECT and UPDATE failures.

Total: **36 new/added tests**, all asserting both (a) the pre-existing
fallback value is unchanged and (b) the failure is now present in
`caplog` under `mcp_server.observability.silent_failure`.

## Class B — legitimate fallback, classified in full

Grouped by file. "Logged in this pass" = a `logger.debug`/`warning` was
added; all others are classified but **not modified** in this pass
(scope discipline — see Rationale below the table).

### Diagnostics / doctor (already observable via return value — borderline B/C, left as-is)
`doctor_mcp.py:518`, `doctor.py:125,160,179,261` — every one already
returns a `Check`/`McpCheck` object carrying
`f"{type(exc).__name__}: {exc}"` to the caller (a CLI/handler that
prints it). Not silent in the sense that matters — the exception text
reaches the operator. **C.**

### `tool_error_handler.py`
`:111,181,191` — `181` already calls `metrics.inc_counter` on the
classified error (observable); `111,191` are secondary fallbacks inside
the same classify-and-report path with the primary path already
logging. **B, not re-logged** (would double-log every tool error).

### `mcp_progress.py:70`, `__main__.py:38`
Best-effort progress/signal-handler cleanup at process boundaries. **C.**

### `core/wiki_coverage.py:1274`, `wiki_coverage_dashboard.py:264`, `wiki_schema_loader.py:211,222,243,247,275`, `wiki_classifier.py:463`
Wiki documentation-surface helpers (coverage audit dashboard, schema
cache, user-rule cache). Not on the recall/write/consolidation critical
path; a broken wiki coverage number is visible to a human reading the
dashboard. **B, backlog** — would benefit from a debug log but is not
urgent relative to the named critical families.

### `core/recall_pipeline.py` (excluding the off-limits :441)
`:266,548,969,983,990,1002,1126` — all carry an explicit `# noqa: BLE001`
+ inline comment ("non-load-bearing per-candidate", "never fail a
recall") already documenting the swallow as a deliberate design choice.
**B, backlog** — same shape as the Class A sites fixed above (an
always-firing bug here would be invisible), but recall_pipeline.py is
mid-edit on the concurrent spread_activation branch; touching it risks a
merge conflict on files the mandate explicitly said not to touch.
**Recommendation: re-run this same fix pattern on recall_pipeline.py
once `feat/spread-activation-scoped-activation` merges.**

### `core/streaming/{backpressure_pipeline,adaptive_writer}.py`
`:146,162,170,133,171,185` — already append to `result.errors` (a
returned, caller-visible list). **C** (observable via the return value,
not the log).

### `core/context_assembly/active_retrieval.py:186`
Single site inside the newer structured context assembler
(`assemble_context()`, not the legacy `recall()` path benchmarked in
production). **B, backlog.**

### `shared/redaction.py:60`, `shared/json_native.py:76`, `shared/subprocess_safe.py:81`, `shared/domain_mapping.py:105`
Pure stdlib-only utilities (§2.2 layer rule: shared → stdlib only, so
these cannot import `observability`). All degrade to a safe default on
malformed input (URL redaction, JSON encode, subprocess kill, domain
casing). **C.**

### `hooks/*.py` (`auto_recall.py:136`, `pipeline_impact_bump.py:64,80,98,104,158`, `agent_briefing.py:258`, `session_start.py` ×14, `post_commit_reindex.py:170,185,197`, `preemptive_context.py:89,106,125`)
Session-bootstrap and best-effort background hooks. The majority of
`session_start.py`/`agent_briefing.py`/`auto_recall.py` **already** route
through a local `_log(...)` helper on the important paths (verified: 12
of 26 hook-file sites in the original 219 already had `_log`, hence
excluded from this list already). The remainder here are secondary
fallbacks one level deeper (e.g. a nested `tags = []` default inside an
already-`_log`-wrapped read). **B, backlog** — lower stakes than the
named critical families (a broken hook degrades session bootstrap
quality, not recall/write correctness), and each `hooks/*.py` file
already has an internal `_log` convention that a follow-up pass should
extend to these nested sites rather than introducing a second logging
mechanism (`silent_failure`) into hook code.

### `infrastructure/sqlite_store*.py`, `sqlite_store_mood.py`
The SQLite backend is the **legacy/fallback** store (PgMemoryStore is
production per `infrastructure/pg_store.py`'s docstring: "Single storage
backend for all memory operations"). `sqlite_store_mood.py:53,127`
explicitly document "pre-migration DB, safe no-op". **B, backlog** —
low production exposure.

### `infrastructure/{scanner,viz_client,pipeline_discovery,pipeline_install_lock,pipeline_installer*,mcp_client,file_io,wiki_store,scanner_parse,workflow_graph_source_ast}.py`, `ap_bridge.py`
AP (automatised-pipeline) integration surface and codebase-graph
scanning — optional, feature-detected (`hasattr`-gated) integrations,
not the recall/write/consolidation critical path.
`ap_bridge.py:63` degrades to "AP on by default" on a config-read
failure (documented). **B, backlog.**

### `infrastructure/pg_store.py` (remaining sites, not the 2 fixed)
`:263,270` (`DEALLOCATE ALL` / reconnect cleanup), `:1290,1296` (pool
`.close()` at shutdown), `:321,325` (rollback/deallocate inside the
already-`logger.info`-covered stale-plan retry) — all cleanup/recovery
machinery secondary to an already-observable primary action. **C.**
`:365` (`ddl_hash` read) — schema-drift detection convenience read,
returns `None` (drift check simply skips) on failure. **B, backlog.**

### `handlers/*.py` (bulk)
`backfill_memories.py`, `ingest_findings_resolve.py`,
`ingest_helpers.py`, `ingest_findings_writers.py`,
`ingest_docs_content_writers.py`, `assess_coverage.py`,
`checkpoint.py:241`, `change_impact.py`, `wiki_*.py` (curate, view,
extract, migrate, seed_codebase, compile, adr, write, synthesize,
pipeline), `codebase_analyze*.py`, `rate_memory.py`, `detect_gaps.py`,
`validate_memory.py`, `auto_task_record_writer.py`,
`record_session_end.py:434,455`, `rebuild_profiles.py:82`,
`recall_helpers.py:304` — the large majority (`wiki_curate.py:175`,
`wiki_extract.py:177`, `wiki_migrate.py:203,220`,
`wiki_seed_codebase.py:257,279`, `wiki_compile.py:218`,
`wiki_pipeline.py:73`, `backfill_memories.py:330`) already append to an
`errors: list` or `result["error"]` returned to the caller — same C
pattern as the streaming module above. The rest
(`ingest_helpers.py:122,246`, `assess_coverage.py:147`,
`detect_gaps.py:225`, `validate_memory.py:262`, `rate_memory.py:173`,
`checkpoint.py:241`, `record_session_end.py:434,455`) are per-item
best-effort degradations in bulk/batch handlers (one bad item must not
kill the batch), all outside the 5 named critical families. **B,
backlog.**

### `handlers/consolidation/*.py` (remaining, not the 1 fixed in cls.py)
`cls.py:54,246` (tag JSON parse fallback; diagnostic-only cluster
recount feeding `reason_for_zero` classification — misclassifies the
*reason* on failure but never breaks the actual consolidation mutation
path), `memify_derive.py:119,130,167,184,217,249` (already reviewed in
depth — `119,130,249` already call `logger.exception`, **C**; `167`
benign tag-JSON fallback, **C**; `184,217` explicitly documented
"degrades to empty set, never an error", **B, backlog**),
`memify.py:127,133,234` (per-item prune/strengthen, "one item never
kills the batch" — a pre-existing precedent this codebase already
applies deliberately, see `memify_derive.py`'s own module docstring),
`page_io.py:44`, `drain_operations.py:78,174`, `candidate_scan.py:43,70,93,103`,
`authoring_prompts.py:455`, `cascade.py:197` — all in the **wiki-drain**
subsystem (autonomous wiki-gap authoring), not the CLS/memify mutation
path the "consolidation" family in the mandate names. **B, backlog.**

## Test debt — integration tests masking real SQL behind mocks

Pattern searched: `No real PG is touched` and equivalent "fully mocked
store" comments on tests that exercise a Class A call site.

- `tests_py/core/test_write_gate.py`,
  `tests_py/core/test_pg_recall_silent_failures.py` (new),
  `tests_py/handlers/test_recall_silent_failures.py` (new),
  `tests_py/core/test_silent_except_sweep_remaining.py` (new) — all use
  `MagicMock` stores. This is correct for **unit** tests of the
  fallback/observability contract (the point is to prove the Python-level
  swallow-and-fallback logic, independent of any specific SQL error) —
  but none of these call sites has a companion **integration** test that
  runs the real PL/pgSQL / SQL statement end-to-end and would catch a
  genuine SQL regression the way the spread_activation bug needed to be
  caught. Specifically:
  - `infrastructure/pg_store.py::update_memory_value` /
    `update_memory_extinction` — no test in
    `tests_py/infrastructure/` exercises these against a real
    PostgreSQL connection with the actual `value` /
    `extinction_strength` columns present; `test_pg_user_mood.py` (real
    DB) is the pattern to extend to these two methods.
  - `handlers/remember_helpers.py::try_block_replica_upsert` — the
    `memory-replica` supersede path (checkpoint sync) has no real-DB
    test proving the JSONB containment predicate
    (`tags @> %s::jsonb`) is syntactically valid against the live
    schema; this is exactly the shape of bug the spread_activation
    incident was (a query that is syntactically broken from day one,
    invisible because every covering test mocks `_execute`).
  - `handlers/consolidation/cls.py::_store_causal_edges` — no real-DB
    test proves `store.insert_relationship(...)`'s dict shape matches
    the live `relationships` table schema.

This test debt is **listed, not fixed** — extending unit tests with
real-PG integration coverage for every Class A call site is a separate,
larger chantier (per the mandate: "ne les réécris pas tous, c'est un
chantier séparé; fixe seulement ceux directement liés à tes classes A").
The three items above are the ones directly tied to Class A fixes in
this sweep and are flagged as the highest-priority follow-up (the
`try_block_replica_upsert` JSONB predicate in particular has never been
proven to compile against the live schema by any existing test).

## Summary

| Class | Count | Action |
|---|---|---|
| A (critical path, silently skippable) | 30 | **Fixed** — `silent_failure.note()` wired, 36 new tests, behavior unchanged |
| B (legitimate fallback, needs observability) | ~140 | Classified in full above; ~15 already effectively observable via `errors`/return-value lists; remainder tracked as backlog by subsystem |
| C (benign — cleanup, already observable, stdlib-only shared/) | ~49 | Left as-is |
| Off-limits (concurrent branches) | 2 (+2 files) | Not touched — see "Explicitly out of scope" |

No dead/disabled production component was discovered in this sweep.
