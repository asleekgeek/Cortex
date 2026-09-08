# W4-4 response-budget audit and measurement protocol

Status: partial implementation; no new response ceiling, safety factor or
per-item fraction is adopted. The 100-response calibration has not run.
Reference: `d0f7c19bf64a2d994b2e9a2a9818244c994bc972`, audited 2026-09-06.

## Symptom

The W4-4 review reported `query_methodology` at 78,163 characters and a
62,503-character documentation memory occupying most of a recall response.
Those are review observations, not measurements reproduced by this patch.
The existing 75,000-character policy does not establish compliance with the
current Claude Code token or text-result limits.

## Root cause

Three contracts differ: the allocator measures compact Python JSON code
points, the locked MCP SDK emits indented text JSON, and the host uses UTF-16
string length plus a model-dependent token-counting path. The per-item policy
only runs when the whole payload exceeds its budget; an otherwise-fitting
62,503-character item is not condensed by the existing default.

`query_methodology` also injected tier-1 noise excluded from the session banner.
Finally, recall's direct-ID handler existed but the MCP registry did not expose
or transmit `memory_id` / `content_offset`. Publishing those parameters required
closing a direct-ID scope gap first.

### Primary sources and exact local evidence

- [Claude Code MCP limits](https://code.claude.com/docs/en/mcp#mcp-output-limits-and-warnings)
  and [environment variables](https://code.claude.com/docs/en/env-vars): documented
  default `MAX_MCP_OUTPUT_TOKENS=25000`; text tools declaring
  `anthropic/maxResultSizeChars` use their declared character limit instead.
  This patch adds no such annotation and does not raise a host limit.
- Installed Claude Code binary: version `2.1.263`, SHA256
  `ef5d2909c8af49f31ab6d5487e90316777bc2fac170adfe8160716caa8aaf4f9`,
  `/Users/cdeust/.local/share/claude/versions/2.1.263`. Its embedded module
  `chunk-xvyb4e66.js` defines a default 25000, then resolves a positive environment
  override first and a positive remote `tengu_velvet_ibis.mcp_tool` value second.
  The effective remote override was not fetched.
- The same module's `ice` sums `vc(text)` for text blocks. Scoped `vc` in
  `chunk-wmzgeczq.js` computes `Math.round(text.length / 4)`; JS length counts
  [UTF-16 code units](https://tc39.es/ecma262/multipage/ecmascript-data-types-and-values.html#sec-ecmascript-language-types-string-type).
  `G3e` skips the provider count only when that estimate is
  at most half the effective limit. Otherwise it invokes `Ute` and compares the
  returned count against the full limit, falling back to the estimate on failure.
  These numbers describe the inspected host, not a new application policy.
- `Ute` invokes the configured provider's count API, including
  `beta.messages.countTokens` on the Anthropic branch. A gateway fallback can
  call `messages.create`; therefore this work does not invoke the CLI counting
  path. The local byte offsets and short excerpts are archived in
  `/private/tmp/cortex-green-w4-4-cli-evidence.json`.
- [Anthropic token-counting documentation](https://platform.claude.com/docs/en/build-with-claude/token-counting)
  describes a model-dependent API estimate, including possible system-added
  tokens, and documents count-only requests as free. This does not supply an
  offline Claude tokenizer. No API request or credential inspection occurred.
- Locked MCP SDK source: `mcp/server/mcpserver/utilities/func_metadata.py`,
  `_convert_to_content`, converts non-string results with
  `pydantic_core.to_json(..., fallback=str, indent=2)`. `safe_handler` first
  applies `shared/json_native.py::to_json_native`. `MCPServer.call_tool` executes
  the registered wrapper and performs that SDK conversion. The collector uses
  that runtime path instead of approximating its serializer.

A ratio measured with tiktoken would not be a Claude count. Neither the legacy
4-character estimate nor 100 observed payloads proves a universal bound for
arbitrary future Unicode/content. A chosen budget and item fraction still need
explicit empirical support and held-out validation.

## Change

- `query_methodology` excludes exact tags `auto-captured` and `memory-replica`
  after normalizing list/JSON tags, on domain, directory and fallback branches.
  The tag set is asserted equal to the existing SQLite banner set. Protected
  rows have no exception; unrelated prefixes and differently-cased tags survive.
- Filtering occurs after the existing selection, matching the SQLite banner.
  A noise-dominated selection can under-fill the response. The shared
  `get_memories_for_domain` primitive and maintenance callers are unchanged.
- Both MCP recall wrappers expose and forward optional `memory_id` and default
  `content_offset=0`; query remains required as in the existing handler schema.
  Existing handler conversion, formatting and offset behavior stay in place.
- For a nonempty connection root, direct-ID reads now require exact
  `stored.agent_context == root`. Cross-scope, missing-scope and global rows
  belonging to another scope yield the same empty response as a missing ID.
  Unrooted direct-ID behavior remains unchanged.
- The allocator's documentation now identifies its legacy code-point measure
  accurately. Its numerical constants and water-filling algorithm are unchanged.
- The collector and report utility capture actual registered-handler SDK
  responses, attach request/content SHA256s, record code points/UTF-8/UTF-16 and
  the inspected host's heuristic separately, and optionally join externally
  supplied provider-count observations. No budget is generated automatically.

## Proof

Focused stdlib unittest runs block sqlite3/psycopg connections and imports of
Torch, sentence_transformers, ONNX Runtime and FlashRank. Tests cover exact tag
parity, all retrieval branches, malformed tags, real handler output, registered
MCP schema/defaults, actual returned/refused memories, and direct-ID paging of a
62,503-character synthetic document without changing stored content.

The large-document tests distinguish preparation from acceptance: an explicit
fixture budget causes truncation and preserves the ID; the existing default
still leaves a fitting large item intact. A separate synthetic emoji payload
shows compact code points below the legacy budget while the actual SDK text
exceeds the legacy UTF-16 host-character cap. This is not a production sample or
a claim about the API token count of that payload.

Ruff, format, craftsmanship delta and patch-application checks accompany the
handoff. The 100-response session, provider counts, quality floors and host
acceptance have not been executed here. No production profile/database was read.

## Conformity

- Private worktree and minimal ownership only; no commit, push, PR or issue.
- No paid AI call, model load, DB connection, benchmark or heavy test by this
  agent. The prepared collector is intended for the parent's later serialized
  measurement slot and may load the existing local embedding model then.
- Core retains stdlib dependencies only. New functions/files respect the caps;
  existing over-cap handler/registry files are not broadly refactored and no
  baseline entry is added.
- No new numerical production budget/fraction. 100 is sourced from W4-4; UTF-16
  unit width and JS rounding come from their definitions/the inspected host.
- Full quality and performance acceptance remains pending measurement.

## Candidates for later work

1. Root propagation in normal search is not an isolation guarantee. At this
   reference, PG `pg_schema.py`'s `agent_boosted` and SQLite
   `sqlite_store_search.py::_apply_agent_boost` add ranking weight for matching
   `agent_context`; they do not exclude other scopes. Existing rooted tests
   checked argument transmission, despite their stronger explanatory text.
   This patch does not alter search or claim to repair that independent gap.
2. Post-selection noise filtering can under-fill `query_methodology` results.
   Moving filtering into a context-specific store query needs separate interface
   work; applying it globally would change maintenance/query consumers.
3. Compact-vs-SDK serialization, metadata-only overflow and an unmeasured
   per-item share remain budget-calibration work. `memory_config.py` retains the
   legacy 75,000 default; no new current-host guarantee is implied.

## Runbook: 100 runtime payloads, then provider observations

Prepare a throwaway root containing `claude/methodology/memory.db`, an isolated
`profiles.json`, and a representative request manifest `cases.jsonl`. Use a
seeded fixture/session with explicit provenance; never label 100 invented text
strings as production measurements. Exactly 100 actual handler invocations are
required. Include both affected tools and relevant language/content shapes;
report duplicate request/content counts instead of hiding repeated cases.

Each request line has this shape (illustration only, not a calibration corpus):

```json
{"tool":"query_methodology","arguments":{"cwd":"/private/tmp/cortex-budget-fixture/project","first_message":"review the fixture project"}}
{"tool":"recall","arguments":{"query":"fixture architecture","domain":"fixture"}}
```

Execute later from the integrated checkout, with the exact locked Python and
one heavy job at a time. Preserve the durable HOME/model cache; never copy
weights into the fixture. The collector refuses a mismatched backend, root,
resolved data path, PostgreSQL override or a preexisting socket location.

```sh
W4_ROOT=/private/tmp/cortex-budget-fixture
W4_DSN=postgresql://%2Fprivate%2Ftmp%2Fcortex-budget-fixture%2Fno-postgres/cortex_budget_fixture
uptime
df -h /
env -i HOME="$HOME" PATH=/usr/bin:/bin LC_ALL=C \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  CORTEX_CLAUDE_DIR="$W4_ROOT/claude" CORTEX_MEMORY_STORE_BACKEND=sqlite \
  DATABASE_URL="$W4_DSN" CORTEX_MEMORY_DATABASE_URL="$W4_DSN" \
  CORTEX_EMBEDDING_ZERO_DOWNLOAD=1 CORTEX_RERANKER_OFFLINE=1 \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  /Users/cdeust/Developments/anthropic-partnership/Cortex/.venv/bin/python \
  scripts/collect_response_budget_payloads.py \
  --isolated-root "$W4_ROOT" --cases "$W4_ROOT/cases.jsonl" \
  --output "$W4_ROOT/responses.jsonl" --report "$W4_ROOT/report.json"
df -h /
```

The capture file contains the real text needed for any later token-count request;
it remains local. The report contains measurements/hashes and no response text.
Capture uses exclusive file creation so a previous run cannot be overwritten.
Before/after runs need separate equivalently seeded fixture roots because recall
access/replay and prospective triggers mutate the fixture; preserve their request
order. This is a handler+SDK experiment, not a real Claude Code session, and does
not itself prove absence of host truncation warnings.

Provider observations, obtained separately with authorization, use JSONL:

```json
{"content_sha256":"<captured SDK content digest>","input_tokens":123,"model":"<actual model ID>","method":"messages.countTokens","source":"<dated response artifact/command>"}
```

`123` above is a format example, not a measured ratio. Count the corresponding
`[{role:"user",content:<captured text blocks>}]` with `tools:[]`, matching the
inspected CLI branch and actual configured model/provider. Do not use a fallback
that creates a model response. An API count is an observed provider estimate,
not an exact billing count or a local tokenizer. Proprietary runtime overrides,
provider/model configuration and genuine count observations remain required.

Rerun the collector command with `--existing-captures "$W4_ROOT/responses.jsonl"`
and `--counts "$W4_ROOT/counts.jsonl"`; this aggregates without rerunning handlers.
Every request digest/tool must match the original manifest. Counts must cover
exactly the distinct content digests and one model; mixed models are rejected.
Each capture retains its original source/SDK hashes; later aggregation records
its own provenance separately and refuses mixed capture provenance.
Publish the raw observations, min/median/max UTF-16-units-per-input-token, largest
payloads and duplicate counts. Select and validate the final budget and per-item
fraction only from those results, then run the required isolated quality gate
and actual-host acceptance. None of those completion criteria is claimed here.
