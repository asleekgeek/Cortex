# ADR-0054: Domain-scope the spread_activation_memories read channel

**Status:** Accepted
**Date:** 2026-07-11
**Decision-makers:** cdeust
**Related:** `mcp_server/core/pg_recall.py::recall` (Memory Read Path, CLAUDE.md);
ADR-0013 (thermodynamic memory model); precedent
`mcp_server/core/pg_recall.py::_memories_by_entity_fn` (existing `m.domain`
filter on the same entity->memory join); the `include_globals` pattern on
`recall_memories()` (`RECALL_MEMORIES_LAZY_FN`, `pg_schema.py`).

## Context

`spread_activation_memories` (`mcp_server/infrastructure/pg_schema.py`), the
graph-expansion channel of `recall()` (`pg_recall.py::recall`, called at the
SPREADING_ACTIVATION stage), had two coupled defects, discovered together
during a scoping investigation (`scratchpad/spread-activation-scoping-design.md`)
and fixed together in this changeset — never one without the other:

1. **Dead since introduction.** The PL/pgSQL function's `spread` CTE
   self-references (`FROM spread s`) but was declared with a plain `WITH`
   instead of `WITH RECURSIVE`. Every single call raised `relation "spread"
   does not exist`, and the exception was silently swallowed by
   `recall_pipeline.py::spreading_activation_expand`'s bare
   `except Exception: return candidates` — no log, no telemetry. The channel
   has been 100% dead in production since its introduction (`8228a0d2`, the
   PostgreSQL migration commit). This went undetected for 3+ months because
   the unit test suite (`tests_py/core/test_pg_recall_pipeline.py`) mocks the
   store entirely (`_FakeStore`, "No real PG is touched", line 13) — the
   mock's Python-native `spread_activation_memories` diverges from the real
   PL/pgSQL function's contract, and nothing detected the divergence.

2. **No domain filter, ever.** Neither the PL/pgSQL function nor the Python
   wrapper (`pg_store.py::spread_activation_memories`) nor the call from
   `recall_pipeline.py::spreading_activation_expand` ever threaded a domain
   parameter, although `domain` is known and available at every layer
   (`recall()`'s own `domain` param, unused at the SPREADING_ACTIVATION call
   site). Measured on the dev database `cortex`: 11.7% of entities linked to
   >=1 memory touch >=2 distinct domains. A topological replay of the
   corrected (WITH RECURSIVE) function against 88 realistic (domain, query
   term) pairs across 8 real domains, `min_heat=0` (isolating the scoping
   defect from the independent heat-floor bottleneck), showed:
   - 52.8% of injected candidates are explicitly cross-domain
   - 87.5% of queries have >=1 cross-domain injection
   - 52.3% of queries see cross-domain volume EXCEED own-domain volume

   Fixing defect (1) alone would have reactivated this measured
   contamination silently — the two fixes are shipped as a single atomic
   changeset for exactly that reason.

## Decision

1. `spread_activation_memories`: `WITH` -> `WITH RECURSIVE` (the fix
   `spread_activation()`, the function's twin over entities only, already
   had correctly).
2. Add `p_domain TEXT DEFAULT NULL` and `p_include_globals BOOLEAN DEFAULT
   TRUE` to the function signature (`DROP FUNCTION IF EXISTS` + `CREATE OR
   REPLACE`, mirroring the existing `RECALL_MEMORIES_LAZY_FN` migration
   pattern). Filter is applied ONLY in the final `entity_memories` CTE, on
   `m.domain`/`m.is_global` — never on `entities.domain` or
   `relationships`. Two reasons: (a) `entities.domain` reflects only the
   entity's *first creator*, not every domain that legitimately shares it
   (`mcp_server/handlers/codebase_analyze_helpers.py::_get_or_create_entity`,
   `remember_helpers.py::compute_entity_info`, and
   `pg_store_entities.py::get_entity_by_name` all resolve entities globally
   by name, case-insensitive, with no domain gate — filtering on
   `entities.domain` would starve legitimately shared entities); (b)
   `relationships` carries no domain column by design (edges are global).
   The precedent for filtering on `m.domain` at this exact join already
   exists in the same codebase:
   `pg_recall.py::_memories_by_entity_fn` (`if domain and m.get("domain")
   != domain: continue`).
3. Thread `domain`/`include_globals` from `pg_recall.py::recall()` (both
   already known/available at that call site) through
   `recall_pipeline.py::spreading_activation_expand()` to
   `store.spread_activation_memories()`.
4. Add `cross_domain: bool = False` to `recall()`, the `spreading_activation_expand`
   stage, and the `recall` MCP tool's schema — an explicit opt-out that
   disables ONLY the SA-stage domain filter (passes `domain=None` to that
   one call; the primary WRRF stage stays scoped to `domain` regardless).
   Mirrors the `include_globals` shape already established on
   `recall_memories()`. `unified_search` inherits the flag automatically
   (it forwards all `recall` args except `k`) and documents it in its own
   schema for discoverability.
5. Extend the same `domain`/`include_globals` parameters to
   `SqliteMemoryStore`'s `spread_activation_memories` (Liskov
   substitutability: `memory_store.py::_construct_store` can silently route
   real (inspection/sandbox-mode) traffic to the SQLite fallback, so the two
   store implementations must honor the same domain-scoping contract or the
   fallback reopens exactly the gap this ADR closes).
6. Replace the swallowing `except Exception: return candidates` in
   `spreading_activation_expand` with a first-failure-logged warning
   (mirrors the reranker fix, commit `bb1c581f`, same night: durable
   cache_dir + non-silent failure + `RerankerStatus`). Adds
   `spreading_activation_status()` for external introspection
   (bench/health-check preflight), logged once per process to avoid
   spamming a per-query stage, state stays queryable regardless.

## Consequences

**Positive:**
- Closes 100% of the measured cross-domain injection risk (52.8% +
  the ~10% domain-blank slice) without any intra-domain recall loss — the
  filter is on `m.domain`, the exact key `recall_memories()` already scopes
  the WRRF stage on for the same corpus.
- Adds the missing real-PG integration test layer
  (`tests_py/infrastructure/test_pg_spread_activation_scoping.py`) that
  would have caught the `WITH RECURSIVE` bug on day one — closes the
  3+-month blind spot documented in Context (1).
- The channel can no longer die silently: any future regression (e.g. a
  schema migration that breaks the function again) surfaces as a WARNING
  log line and a queryable status, not a silent no-op.
- API surface consistent with the existing `include_globals` idiom —
  no new shape introduced.

**Negative / accepted trade-offs:**
- The SA channel remains inert for the large majority of real queries
  regardless of this fix: only 0.051% of entities in the dev DB clear the
  default `min_heat=0.05` floor (measured: 42/82547), and only 3.3% of 90
  realistic query-term samples had even one seed entity above that floor.
  This is a SEPARATE, independent bottleneck (thermodynamic decay of the
  entity graph) — out of scope for this ADR, which only addresses domain
  scoping and the SQL bug.
- `cross_domain=True` is currently unused by any caller in this codebase.
  `bridge_finder.py` (the actual product mechanism for cross-domain
  connections, surfaced via `query_methodology`/cognitive profiling) does
  not use this channel and is unaffected by this decision either way.

**Risks (Feynman, top-3 invalidators to re-check periodically):**
1. If a future product mechanism wants legitimate cross-domain retrieval
   through THIS channel specifically (beyond `bridge_finder.py`, which
   doesn't use it), `cross_domain` must be re-verified against a real
   consumer before being called "used" — until then it is a single-purpose
   opt-out with no live caller, which is an accepted, explicitly-flagged
   exception to the "no abstraction without a second use case" default.
2. If `entities.domain` is ever promoted to a trusted signal elsewhere in
   the codebase, a future edit must NOT reuse it as the filter column here
   by analogy — the filter must stay on `m.domain` (memories), not
   `entities.domain`, or intra-domain recall silently regresses.
3. The 52.8% cross-domain figure is a topological measurement on one
   snapshot of the `cortex` dev database (82547 entities, 11011 memories,
   17572 relationships, 8 real domains). As the number of projects/domains
   grows, the entity-sharing rate (11.7% today) may grow with it (more
   common tokens) — the number should be re-measured periodically, not
   assumed stable, before it is cited again.

## Alternatives considered

**(a) Filter domain hard, no opt-out.** Rejected in favor of (c): loses the
explicit escape hatch a future legitimate cross-domain consumer would need,
for a marginal implementation cost saving.

**(b) RRF-soft cross-domain score penalty instead of a hard filter.**
Rejected: not robust bench-neutral by construction (a penalty changes the
fused score even on a mono-domain corpus unless carefully conditioned, which
must be re-verified on every corpus change — more fragile than a binary
filter); introduces a penalty constant with no empirical source
(`rules/coding-standards.md` §8, "No invented constants"); would preserve a
cross-domain signal with no demonstrated product consumer via this specific
channel.

**(d) Statu quo — document only, ship no code change.** Rejected: leaves a
trivially tempting `WITH RECURSIVE` fix (the SQL bug alone looks unrelated to
domain scoping) available to reactivate the measured 52.8-62.7% contamination
without anyone consciously deciding to accept that risk. This ADR exists
specifically to foreclose that failure mode.

## Bench-neutrality verification (pre-merge, mandatory per project convention)

`benchmarks/lib/bench_db.py::BenchmarkDB.recall()` calls
`mcp_server.core.pg_recall.recall()` directly — no custom retriever. Expected
**neutral by construction**:
- `cortex_ts_lme` / `cortex_ts_beam` (dedicated per-benchmark databases): 0
  entities, 0 relationships today — `spread_activation_memories`, even fixed,
  returns an empty set regardless of scoping (no seed entity possible).
- `cortex_bench` (shared multi-family sandbox): 3859 entities across 3
  benchmark families (`longmemeval` 3230, `beam` 623, `locomo` 6) sharing one
  database WITHOUT a domain filter today. This is exactly the same
  contamination mechanism measured in production, symmetric across benchmark
  families instead of projects — this ADR's default scoping closes it
  automatically because every benchmark runner already threads its own
  `domain=` through `BenchmarkDB.recall()` (`longmemeval/run_benchmark.py`
  lines 269, 283 and equivalents). Shipping the SQL fix WITHOUT this ADR's
  scoping would have reopened cross-benchmark-family contamination on
  `cortex_bench` specifically.

Any measured score delta on this changeset (LongMemEval / LoCoMo / BEAM) is
a signal to investigate before merge, not to wave through.

## Reversibility

Type-2 (reversible gate): behavior change on an internal read path, no
schema/data migration beyond adding two DEFAULT-valued function parameters
(backward compatible — existing callers that don't pass `p_domain` get
`NULL`, i.e. today's unfiltered behavior, until the Python layer threads a
real value, which this changeset does at every call site). `cross_domain`
provides an immediate escape hatch with no redeploy. Classification stays
**High stakes** for the rigor applied to this decision (touches the
production `recall`/`unified_search` read path, the sole channel that was
untested against a real PL/pgSQL function for 3+ months) independent of the
change's own reversibility.
