---
title: "ADR-0131 — mcp_server/core/compression.py rationale"
status: accepted
source: mcp_server/core/compression.py
---

# ADR-0131 — mcp_server/core/compression.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Memories degrade from full content -> gist -> tags as they age,
following information-theoretic optimal forgetting:
  Level 0 (recent): Full fidelity — complete content preserved
  Level 1 (medium): Gist — key sentences + code snippets + entities
  Level 2 (old):    Tag  — one-line summary + semantic tags
````

## module — original line 9 (docstring)

````text
High importance/surprise memories resist compression (get more bits).
Protected and semantic-store memories are never compressed.
````

## module — original line 12 (docstring)

````text
Pure business logic — no I/O. Storage/embedding operations handled by caller.
````

## module — original line 14 (docstring)

````text
Based on Toth et al. (PLoS Comp Bio, 2020), MemFly (2025), Tishby (1999).

````

## _parse_ingested_at — original line 38 (docstring)

````text
    Compression cadence asks "has this memory had time to be revisited
    in MY system" — that is elapsed time since ingest, NOT elapsed time
    since the original event. Backfilled / imported memories carry a
    backdated created_at (e.g. a 2023 conversation imported in 2026);
    using created_at would compress them on the first consolidation
    pass, before retrieval ever runs (see
    docs/benchmarks/e1-v3-locomo-smoke-finding.md).
````

## _parse_ingested_at — original line 46 (docstring)

````text
    Falls back to created_at for legacy rows that predate the
    ingested_at column (the schema migration in pg_schema.py backfills
    ingested_at = created_at in that case anyway, so the fallback only
    matters for in-memory dicts that never round-tripped through PG).
    
````

## _compute_resistance — original line 77 (docstring)

````text
    Each multiplier is an engineering choice — no paper provides exact
    values for these thresholds in a conversational memory system.
    The qualitative direction (important / surprising / frequently accessed
    memories resist compression longer) is grounded in the rate-distortion
    and memory-importance literature (Tishby 1999; Toth et al. 2020) but
    the specific numbers are hand-tuned and need ablation calibration.
````

## _compute_resistance — original line 84 (docstring)

````text
    Sources for individual multipliers:
      2.0 (importance > 0.7): engineering choice — high-importance memories
          warrant 2x longer retention before compression; calibration pending
          — see ablation.
      1.5 (surprise_score > 0.6): engineering choice — high-surprise memories
          resist forgetting (von Restorff 1933 qualitative finding); exact
          factor is hand-tuned; calibration pending — see ablation.
      1.3 (confidence > 0.8): engineering choice — high-confidence memories
          are less likely to be stale; factor is hand-tuned; calibration
          pending — see ablation.
      1.5 (access_count > 10): engineering choice — frequently accessed
          memories should remain at full fidelity longer; calibration
          pending — see ablation.
    
````

## get_compression_schedule — original line 117 (docstring)

````text
    Ablation: when CORTEX_ABLATE_COMPRESSION=1 the compression pass is
    skipped for all memories — returns 0 (full fidelity) unconditionally.
    This mirrors the spreading_activation ablation pattern (inline import
    to avoid a circular-import risk at module-load time).
````

## get_compression_schedule — original line 122 (docstring)

````text
    Age thresholds:
        gist_age_hours=168.0  (7 days)  — engineering choice; calibration
            pending ablation study. Source: engineering choice —
            balances retrieval fidelity vs storage cost at typical session
            cadence; calibration pending — see ablation.
        tag_age_hours=720.0   (30 days) — engineering choice; calibration
            pending ablation study. Source: engineering choice —
            chosen as ~1 month, beyond which gist-level detail is unlikely
            to be recalled verbatim; calibration pending — see ablation.
````

## module — original line 66 (comment)

````text
# source: thresholds documented per-multiplier in the _compute_resistance
# docstring (engineering choices; calibration pending — see ablation)
````

## inline — original line 100 (comment)

````text
# source: engineering choice — see docstring
````

## inline — original line 102 (comment)

````text
# source: engineering choice — see docstring
````

## inline — original line 104 (comment)

````text
# source: engineering choice — see docstring
````

## inline — original line 106 (comment)

````text
# source: engineering choice — see docstring
````

## module — original line 149 (comment)

````text
# Cadence is measured from ingest, not from the original event.
# Source: docs/benchmarks/e1-v3-locomo-smoke-finding.md.
````

## module — original line 189 (comment)

````text
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 250 (comment)

````text
# source: cap documented in the _truncate_tag_repr docstring ("truncate tag
# representation to 200 chars"); tuning provenance not recorded
````

## module — original line 253 (comment)

````text
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## inline — original line 255 (comment)

````text
# below this, fall back to a fixed-width summary
````
