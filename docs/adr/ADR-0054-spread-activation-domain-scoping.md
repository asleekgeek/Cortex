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

---

## Addendum A (2026-07-11, post-merge): candidate-field-contract crash

The garde x3 bench's FIRST live exercise of this changeset (LongMemEval,
PID 99074) crashed on the very first EVENT_ORDER query:
`TypeError: '<' not supported between instances of 'str' and
'datetime.datetime'` at `pg_recall.py::_chronological_rerank`'s
`sorted(candidates, key=lambda c: c.get("created_at", ""))`.

**Root cause, verified against real psycopg types** (empirically, not
inferred from the log — `type(store.recall_memories(...)[0]["created_at"])`
vs `type(store.get_memory(...)["created_at"])` on a live connection):
`store.recall_memories()` (the WRRF path, `pg_store.py`) had NEVER
normalized `created_at` — it returned raw `dict(r)` rows, leaving it a
psycopg `datetime.datetime` object. This was already inconsistent with the
`recall` tool's own response schema (`handlers/recall.py`:
`"created_at": {"type": "string", "format": "date-time"}`), but it never
surfaced because every candidate in a given `recall()` call came from
exactly one source before this changeset made the SA channel alive.
`store.get_memory()` (used to build SA-injected candidates) already
normalized via `_normalize_memory_row`. Once SA started actually injecting
rows, a single candidate list held both types and `sorted()` raised on the
first type-sensitive comparison.

A second, non-crashing defect was found auditing the injection site:
`spreading_activation_expand` built its candidate dict from a curated
6-field subset of `store.get_memory()`'s row instead of the full WRRF
contract (`recall_memories()`'s RETURNS TABLE: memory_id, content, score,
heat, domain, created_at, store_type, tags, importance, surprise_score,
emotional_valence, source, value, source_attribution). `store_type`,
`source`, `source_attribution`, `importance`, `surprise_score`,
`emotional_valence`, `value` were silently ABSENT — e.g.
`recall_helpers.py`'s low-signal filter keys on `mem.get("source") ==
"post_tool_capture"`; a missing key always reads `None`, so an SA-injected
auto-capture could never be filtered as low-signal regardless of its real
source.

**Fix**, at the source, not the sort site: `pg_store.py::_isoformat_datetime_fields()`
(new shared static helper) is now applied by BOTH memory-row readers
(`_normalize_memory_row` and `recall_memories()`) — `created_at` is always
ISO text regardless of origin. `recall_pipeline.py::_sa_candidate_from_memory()`
rebuilds the injected candidate as an explicit whitelist mirroring
`recall_memories()`'s full RETURNS TABLE (not `dict(mem)` wholesale either —
`get_memory()` is `SELECT * FROM memories`, a much larger superset including
internal state like `compression_level`/`write_class`/`superseded_by_id`
that must not leak into a candidate dict).

**Test**: `tests_py/integration/test_spread_activation_candidate_contract.py`
— real-PG contract test comparing a genuine WRRF candidate against a genuine
SA-injected candidate (built via the actual PL/pgSQL + `recall_pipeline`
code): key-set equality, type-for-type comparison, an explicit
`created_at`-is-never-`datetime` assertion, and an inventory of every
downstream consumer between SPREADING_ACTIVATION and the final response
(`_chronological_rerank` — the crash site — `value_priority_rerank`,
`emotional_retrieval_rerank`, `dendritic_modulate`) exercised against the
real mixed candidate list. Verified falsifiable: reverting the two source
files (`git stash`) reproduces the exact same `TypeError` at the exact same
site in 5/9 tests.

**Lesson for §0's blind-spot analysis**: the original mock-only test gap
(`_FakeStore`, "No real PG is touched") hid not only the `WITH RECURSIVE`
bug but this contract mismatch too — a mock that returns whatever shape the
test author hand-writes cannot catch a divergence between two REAL store
methods' output shapes. Real-PG integration tests remain mandatory for this
channel going forward.

---

## Addendum B (2026-07-11, post-merge): garde x3 bench first live measurement — augment mode is NOT benchmark-neutral; default changed to tail-fill

The garde x3 bench's first successful full run against this changeset
(after Addendum A's fix) produced the first-ever live measurement of the
SA channel:

| Metric | Pre-SA baseline (v4.10.0 release) | With SA channel alive (augment mode, domain-scoped) | Floor |
|---|---|---|---|
| LongMemEval MRR | 0.9166 | **0.9009** | 0.914 |
| LongMemEval R@10 | 0.982 | **0.984** (+0.002) | — |

**This breached the floor.** The §2.4/§3(c) "bench-neutral by construction"
argument in this ADR's original body was **wrong for LongMemEval specifically**,
for a reason distinct from the cross-project contamination this ADR already
closes: LongMemEval's OWN ingestion legitimately creates entities INSIDE the
`longmemeval` domain (8469 counted at autopsy) — domain scoping (§3(a),
Decision above) correctly keeps SA within-domain, but within-domain is
exactly where LongMemEval's dense entity graph lives. The live "augment"
mode (pre-fusion RRF blend, `spreading_activation_expand`) does not just add
missing candidates — on a corpus this dense, it can and did reorder
already-correct top-ranked documents, trading +0.002 R@10 for -0.016 MRR:
a net regression under the project's evaluation metric (MRR is the primary
LongMemEval floor gate).

**Rule that resolves this** (user-graved, `bench-before-release` memory):
*"the guard wins; we look for a benchmark-neutral-by-construction mechanism,
we never lower the threshold."* Lowering the MRR floor to accommodate the
regression was refused by construction — instead, the injection mechanism
itself was redesigned to be neutral BY CONSTRUCTION rather than neutral by
measurement-that-turned-out-wrong.

### Decision (Addendum B)

1. **New default mode: `sa_mode="tail"`.** `spreading_activation_tail_fill()`
   (`recall_pipeline.py`) runs as the LAST stage of `pg_recall.py::recall()`
   — after FlashRank, VALUE_PRIORITY, CONFLICT_MONITOR, GOAL_MAINTENANCE,
   ATTENTIONAL_CONTROL, and the EVENT_ORDER chronological rerank — and does
   exactly one thing: if the fully-reranked pipeline returned fewer than
   `top_k` candidates, append SA-reachable memories (same field contract,
   Addendum A) until `top_k` is reached or the graph is exhausted. It NEVER
   reorders, rescores, or removes an existing candidate.
2. **Benchmark-neutral by construction, not by measurement.** The
   `len(candidates) >= top_k` branch returns before any store call — zero
   I/O, zero effect, on any corpus dense enough to already fill `top_k`
   (LongMemEval, LoCoMo, BEAM all are, by construction of a MRR/R@10
   retrieval benchmark with a reasonable `top_k`). The guarantee no longer
   depends on domain scoping alone, or on any property of a specific corpus'
   entity density — it depends only on list length, which is corpus-agnostic
   and trivially auditable per query.
3. **The prior default (pre-fusion full injection, `spreading_activation_expand`,
   the mode that produced 0.9009/0.984 above) becomes opt-in via
   `sa_mode="augment"`** — same shape as the existing `include_globals`/
   `cross_domain` opt-in pattern. Available for a future dedicated tuning
   campaign (e.g. a `unified_search`-specific blend-weight sweep, mirroring
   `benchmarks/lib/blend_weight_sweep.py`'s existing methodology for other
   RRF blend constants) — NOT a default change without its own bench
   campaign and floor-gate sign-off.
4. **`sa_mode="off"`** disables the channel entirely (same effect as
   `CORTEX_ABLATE_SPREADING_ACTIVATION=1`, exposed as an explicit mode for
   callers that want it without an env var).
5. `cross_domain` (§3(c)/Decision above) stays orthogonal — it governs
   WHICH memories the SA channel is allowed to reach (domain-scoped vs not);
   `sa_mode` governs WHERE/HOW those reachable memories affect the response
   (tail-only append vs pre-fusion reorder vs disabled). The two dimensions
   compose independently at every call site.

### Consequences (Addendum B)

Positive: closes the measured MRR regression by construction, with a
falsifiable proof (`tests_py/integration/test_recall_sa_mode_wiring.py`'s
`test_tail_and_off_are_identical_when_wrrf_fills_top_k` — `sa_mode="tail"`
and `sa_mode="off"` produce bit-for-bit identical output, modulo the
unrelated `reconsolidation_apply` heat bump, whenever WRRF already fills
`top_k`); preserves the channel's actual value proposition — sparse/cold
recalls (small domains, thin corpora) that WRRF alone cannot fill to
`top_k` — exactly where a benchmark corpus built to have dense ground-truth
coverage will never exercise it, and exactly where a real, thin personal
project domain will.

Negative: `augment` mode's potential value (if any exists beyond what
`tail` captures) is now unmeasured in production — no default traffic
exercises it. This is intentional (§ decision 3) until a dedicated campaign
justifies re-enabling it as a default for a specific caller.

**Risks (Feynman, top-3 invalidators, revised)**:
1. `tail`'s neutrality argument depends on `top_k` being reasonable for the
   benchmark's ground truth (`R@10`-style benchmarks use small `top_k`,
   which WRRF alone reliably fills on a corpus with enough same-domain
   memories per query). A future benchmark or product surface with a much
   larger `top_k` (e.g. `top_k=100` for a coverage-style eval) could see
   WRRF legitimately return fewer than `top_k` candidates even on a dense
   corpus — re-verify neutrality empirically whenever `top_k` changes
   significantly, don't assume it transfers.
2. `sa_mode="augment"` remains reachable via the MCP tool schema
   (`handlers/recall.py`) — if a caller sets it without understanding the
   measured MRR regression, they reproduce today's incident. The schema
   description names the regression explicitly; this is a documentation
   safeguard, not a code-level guard rail (Move 3: no runtime warning is
   emitted for `sa_mode="augment"`, matching the project's existing
   pattern of trusting explicit opt-ins like `cross_domain`/`include_globals`
   without redundant runtime nagging).
3. This addendum's MRR/R@10 numbers are a single LongMemEval run
   (post-Addendum-A-fix, pre-Addendum-B-fix) — re-measure `tail` mode's own
   LongMemEval/LoCoMo/BEAM scores once the guard reruns on this commit,
   and treat any non-neutral delta on `tail` (there should be none, per the
   construction argument) as a signal the construction argument itself has
   a bug, not as noise to wave through.
