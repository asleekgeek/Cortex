# ADR-0060: benchmarks/lib/_e2_conditions.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/_e2_conditions.py`; original SHA-256 `eb94748ef69c5398cc92b92d60c3f80f6783572e91f12796b4ecfab3213d94cd`.

## Original docstring, lines 1–11

````text
"""Shared E2 condition primitives — env-var toggles for cortex_full vs cortex_flat.

Extracted from n_scan_runner.py so the latency runner (synthetic, formerly
n_scan) and the new E2 retrieval runners (subsample, zipf) share a single
source of truth for the ablation condition. Production write paths read
the env vars; this module only sets/restores them.

Per E2 falsifiability protocol (docs/provenance/verification-protocol.md §E2):
- cortex_full:  no env overrides; production defaults active.
- cortex_flat:  decay disabled, heat constant 0.5, consolidation disabled.
"""
````

## Original comment, lines 17–17

````text
# source: docs/provenance/verification-protocol.md §E2 flat-baseline definition.
````

## Original docstring, lines 61–66

````text
"""Heat for inserted memories under ``condition``.

    cortex_flat forces heat=0.5 so the flat-importance condition is
    observable even when downstream code does not yet read CORTEX_HEAT_CONSTANT.
    source: docs/provenance/verification-protocol.md §E2 flat-baseline definition.
    """
````

