# ADR-0052: AP↔Cortex Flow Direction, Ingestion Precedence, and the ap_bridge Contract

**Status:** Accepted
**Date:** 2026-07-09
**Decision-makers:** cdeust
**Related:** ADR-0046 (automatised-pipeline integration), ADR-0051 (wiki page-source schema); Incrément 5 design (`inc5-design-decouverte-documentation.md`, decisions D1, D5, D12); cartography reports `inc4-ap-cartographie.md`, `inc4-ap-cortex-interface.md`

## Context

Incrément 4's cartography of the automatised-pipeline (AP) ↔ Cortex boundary
established two facts that this ADR now acts on, plus one piece of unmanaged
technical debt it bounds:

1. **AP has no network or PostgreSQL client.** `grep -rn "postgres\|reqwest\|
   http://" automatised-pipeline/src --include="*.rs"` returns empty (carto
   §4.2-4.3; iface Q1, "AP→Cortex: NON, avec preuve d'absence"). AP only ever
   writes files: the LadybugDB graph, `meta.json`, and `runs/<run_id>/`
   artifacts. The Cortex→AP direction, by contrast, is programmatic and
   enabled by default: `APBridge` (ADR-0046, 11 allowlisted tools) plus a
   second client path via `mcp_client_pool`/`codebase` (iface Q1).

2. **Two Cortex handlers write the same PostgreSQL rows from two different
   sources.** `ingest_codebase` pulls the AP graph (via APBridge) into
   memories + entities + wiki pages. `codebase_analyze` walks the repo
   in-process (tree-sitter, 7 languages) and writes the same shape of rows
   when AP is unreachable. The distinction is documented at the call site
   ("Distinct from […] ingest_codebase", `ap_bridge.py:12-14`: "fallback to
   the native in-process AST source") but there is no enforced precedence,
   no version-parity check between the two client paths, and no marker on
   the resulting memories saying which engine produced them. A live
   divergence was observed between the two client paths (symlinked AP
   binary at 0.4.0 vs. manifest-declared 0.6.0 — iface angle-mort 5); a
   memory written today cannot say which binary version shaped it.

3. **`ap_bridge.py` is duplicated verbatim between the Cortex and
   cortex-viz plugins** (iface angle-mort 6) — two independent copies of
   the same AP-facing contract (graph-path resolution, tool call shapes,
   health-check parsing), each requiring its own edit when AP's tool
   surface changes.

None of these are new architecture — they are the *as-built* shape of the
Cortex↔AP boundary, made explicit so future increments (INC5.1-INC5.7) build
on a stated contract instead of an implicit one.

## Decision

### 1. Flow direction: Cortex pulls, AP never pushes (D1)

Every mechanism added in Incrément 5 is a **Cortex-side consumer** of AP's
file artifacts — reached via the existing `APBridge` (ADR-0046) or by
reading `runs/<run_id>/` directly off disk. No incrément-5 work adds a
network or database client to the AP binary.

**Acceptance invariant:** `grep -rn "postgres\|reqwest\|http://"
automatised-pipeline/src --include="*.rs"` stays empty after every
increment in this series.

**Alternatives rejected:**
- *AP writes to PostgreSQL directly.* Would add a network client to a
  binary whose out-of-network posture is a deliberate, verified property
  (fact 1 above) — infrastructure scope creep and an AP refactor, both
  explicit non-goals of this program.
- *Push via shell hooks.* The existing Cortex hooks (`post_tool_capture`,
  `activity_capture`) drop `mcp__*` tool args and results by construction
  (see ADR-0052 §3 note below and the Incrément 5 design T6) — building a
  push channel would mean rebuilding hook capture from scratch for this
  one purpose.

### 2. Ingestion precedence: `ingest_codebase` primary, `codebase_analyze` explicit fallback (D5)

`ingest_codebase` (via APBridge, when AP is reachable) is the **primary**
path for turning a codebase into Cortex memories/entities/wiki pages.
`codebase_analyze` (native in-process AST, tree-sitter) is the **explicit
fallback**, used only when AP is unreachable. The two are never run against
the same repo in the same ingestion pass — precedence is sequential, not a
merge.

Both requirements below are contract obligations for whichever increment
implements the ingestion handlers (D5's writer-level work is scoped to
INC5.2, tracked separately); this ADR fixes the *rule*, not the code:

- Every memory written by either path carries a provenance tag —
  `src:ap` or `src:native` — plus the AP binary version when `src:ap`
  applies, obtained via the already-allowlisted `health_check` tool
  (iface Q1). A memory describing code structure is not verifiable
  without knowing which engine, and which version of that engine,
  produced it.
- `ingest_codebase` checks version parity between the `APBridge` client
  path and the `mcp-connections.json` client path at the start of a run,
  and surfaces (warns or refuses) on divergence — closing the concrete gap
  observed in iface angle-mort 5 (0.4.0 symlink vs. 0.6.0 manifest).

**Alternatives rejected:**
- *Merge the two handlers into one.* The fallback exists because AP can be
  absent; merging would either lose the degraded mode or require refactoring
  both handlers into a single abstraction disproportionate to Incrément 5's
  scope.
- *Delete `codebase_analyze`.* Breaks the documented degraded-mode
  contract (AP-absent installs still need codebase ingestion).

### 3. `ap_bridge.py` duplication: debt accepted and bounded, not refactored here (D12)

**Fact:** near-identical copies of the AP bridge contract (`resolve_graph_paths`,
tool-call shaping, `health_check` response parsing) live in both the Cortex
plugin and the cortex-viz plugin (iface angle-mort 6). The correct fix — a
shared package importable by both plugins — touches the packaging boundary
of two independently-versioned plugins and is out of scope for Incrément 5
(a packaging refactor, not a documentation/discovery increment).

**Decision:** accept the duplication as bounded technical debt under this
contract:

- **Shared contract surface** (must stay identical in both copies until the
  debt is repaid): the resolved-graph-path shape returned by
  `resolve_graph_paths()`, the tool-call JSON shape sent to AP's 11
  allowlisted tools (ADR-0046), and the `health_check` response fields
  consumed for version parity (§2 above).
- **Obligation:** any change to the shared contract surface in one copy
  (Cortex `ap_bridge.py` or cortex-viz's copy) must be ported to the other
  copy in the same change set. A PR touching one without the other is
  incomplete.
- **Repayment condition:** the debt is repaid when a shared package
  (published or path-referenced) replaces both copies — tracked as a
  packaging-refactor candidate, not scheduled by this ADR.
- **Risk this bounds:** silent divergence between the two copies is exactly
  the failure mode that produced the version-parity gap in §2 (iface
  angle-mort 5) — one copy resolving a stale roster entry the other has
  already corrected. The version-parity check in §2 is the concrete
  mitigation available today; full elimination of the risk requires
  repayment.

## Consequences

- Positive: the Cortex↔AP boundary now has one written rule for flow
  direction and one for ingestion precedence; a memory can be traced to the
  engine and version that produced it (once INC5.2 implements the tagging
  this ADR specifies); the `ap_bridge.py` duplication is a named, bounded
  liability instead of an undocumented one.
- Negative: the duplication itself is not fixed — every future AP tool
  surface change still requires editing two files, and until the
  version-parity check (§2) ships, retroactive memories written before this
  ADR remain untagged and their producing engine/version is unrecoverable
  ("I don't know" — no speculative backfill, per the Incrément 5 design's
  risk 5).
- This ADR does not implement `ingest_findings`, the provenance tags, the
  version-parity check, or the `meta.json` wiring — those are INC5.1, INC5.2,
  and INC5.6 respectively. This ADR fixes the rules those increments must
  satisfy.

## References

- `automatised-pipeline/src/main.rs:2038-2048` (`meta.json` write, "for
  cortex-viz")
- `automatised-pipeline/src/clustering/impact.rs:177-216` (single reverse-hop
  traversal, no network/PG client anywhere in `src/`)
- `Cortex/mcp_server/infrastructure/ap_bridge.py:12-14` ("fallback to the
  native in-process AST source")
- `Cortex/mcp_server/handlers/tool_registry_ingest.py` (conditional tool
  registration on AP reachability)
- ADR-0046 (`automatised-pipeline-integration.md`) — APBridge, 11 allowlisted
  tools, hooks `pipeline_impact_bump` + `post_commit_reindex`
- `inc4-ap-cartographie.md` §1.4, §4.2-4.3, §5; `inc4-ap-cortex-interface.md`
  Q1, Q2, angle-mort 5, angle-mort 6
