# ADR-0331: mcp_server/handlers/assess_coverage.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/assess_coverage.py`; original SHA-256 `b3211bc54142b3f7b96847fababbdab0f8390aa32f3ff259edca0a98af6f61f6`.

## Original docstring, lines 1–17

````text
"""Handler: assess_coverage — memory-store completeness evaluation.

Scores the memory store itself (scoped by directory or domain). There
is no axis that enumerates which source files have been seen/remembered:
  1. Quantity: memory count relative to a 100-memory reference
  2. Age distribution: how fresh vs stale the scoped memories are
  3. Entity density: total-store entity count / scoped memory count
     (biased — see _entity_density; not per-memory density)
  4. Domain balance: distribution of the scoped memories across domains
  5. Compression ratio: how much scoped content has been compressed
     (penalty signal, not a positive axis)

Returns a 0-100 coverage score and actionable recommendations. The
weighting constants in `_compute_coverage_score` (0.30/0.25/0.20/0.15/0.10)
are hand-picked, not sourced from a paper or benchmark — coding-standards
§8 debt, flagged here rather than left silent.
"""
````

## Original comment, lines 221–224

````text
# Recommendation thresholds. Like the weighting constants flagged in the
# module docstring, these are hand-picked — coding-standards §8 debt.
# source: pre-existing tuned values, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## Reviewed remaining docstring (mcp_server/handlers/assess_coverage.py, interim lines 1–8)

````text
Handler: assess_coverage — memory-store completeness evaluation.

Returns a 0-100 coverage score and actionable recommendations. The
weighting constants in `_compute_coverage_score` (0.30/0.25/0.20/0.15/0.10)
are hand-picked, not sourced from a paper or benchmark — coding-standards
§8 debt, flagged here rather than left silent.

source: ADR-0331
````

## Original schema description, interim lines 24–41

````text
Score the memory store itself across five signals: quantity (scoped memory count vs a 100-memory reference), age distribution (fresh vs stale), entity density (total store entities / scoped memory count — a corpus-wide ratio, not a true per-memory measure), domain balance (distribution of scoped memories across domains), and compression ratio (penalty for compressed content). There is no axis scoring which project source files are remembered. The weighting constants combining these into the 0-100 score are hand-picked, not paper- or benchmark-sourced (coding-standards §8 debt). Emits actionable recommendations (e.g., `run validate_memory`, `run consolidate`). Use this as a memory-store health check. Distinct from `detect_gaps` (lists specific missing connections, no aggregate score), `memory_stats` (raw counts, no scoring), and `narrative` (prose summary, no numeric coverage). Read-only. Latency ~500ms-1s. Returns {coverage_score, total_memories, age_distribution, entity_density, compression, domain_balance, recommendations, directory, domain}.
````

