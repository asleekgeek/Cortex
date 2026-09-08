---
title: "ADR-0095 — mcp_server/core/ablation.py rationale"
status: accepted
source: mcp_server/core/ablation.py
---

# ADR-0095 — mcp_server/core/ablation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
In neuroscience, ablation studies remove or disable brain regions to measure
their contribution. This module applies the same methodology to Cortex:
disable individual neuroscience mechanisms and measure the impact on
system-level behavior.
````

## module — original line 8 (docstring)

````text
Each mechanism has an enable/disable flag. When disabled:
- The mechanism returns neutral/identity values (no modulation)
- Other mechanisms continue operating normally
- System-level metrics are tracked for comparison
````

## module — original line 13 (docstring)

````text
Pure business logic -- no I/O (the env-var read is a single os.environ
lookup, performed only when an E1 verification campaign sets it; in
production the var is never set so the lookup is a constant-time miss).

````

## is_mechanism_disabled — original line 28 (docstring)

````text
    Production hot-paths call this at the entry point and short-circuit to
    a no-op when True. Used by the E1 verification campaign
    (benchmarks/lib/ablation_runner.py) to produce per-mechanism causal
    deltas; in production the env var is never set so every check is a
    single dict lookup.
````

## Mechanism — original line 49 (docstring)

````text
Enumeration of the ablatable units (the neuroscience-grounded
    mechanisms plus retrieval/maintenance flags; some mechanisms expose more
    than one ablation flag). CONFABULATION_GATE (C1 source/reality-monitoring
    read-side enforcement — gates the consolidation-time confabulation check
    that flags an episodic->semantic promotion whose combined source evidence is
    INFERRED with zero perceptual grounding, plus the per-hit recall
    confabulation_risk annotation; disabled makes both a no-op, so a promotion is
    annotated exactly as it was pre-C1-read-side and recall hits carry no risk
    flag — with no change to recall ordering/membership either way).
    ATTENTIONAL_CONTROL (A1 central-executive read-side — a soft attentional
    re-weight over the FULL recall candidate set:
    recall_pipeline.attentional_focus_rerank runs the same allocate_attention
    pass A1 already provides, using the recall query as the top-down cue plus
    bottom-up salience, and applies a small multiplicative nudge
    ``score·(1 + weight·(attn − 1/n))`` to each candidate; uniform/no-signal
    attention gives a per-candidate factor of exactly 1.0 so recall ordering is
    unchanged, and the candidate set is NEVER truncated to the Cowan working-set
    ceiling; disabled returns the candidate list untouched) is the most recent
    addition.
````

## AblationConfig — original line 116 (docstring)

````text
    Data only — mutmut skips the body of any `@dataclass`-decorated class
    (`mutmut/mutation/file_mutation.py:236`; issue #262 3rd pass, #282).
    `ablation_config_is_enabled/disable/enable/disable_all_except` below
    carry the logic as free functions instead.
    
````

## ablation_config_disable_all_except — original line 154 (docstring)

````text
    ``config`` is unread — kept for a uniform ``(config, ...)`` call shape;
    the result always replaces ``disabled`` wholesale (matches the
    pre-extraction method's own behavior of ignoring prior state).
    
````

## module — original line 200 (comment)

````text
# source: pre-existing tuned values, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## Additional source rationale — is_mechanism_disabled

````text
    """True iff CORTEX_ABLATE_<NAME>=1 is set for this mechanism.

    source: ADR-0095

    Reads os.environ on every call -- callers are not in a tight loop;
    test env varies per-run; production env never changes mid-process.
    DO NOT memoize.

    Accepts either a Mechanism enum (uses .name -> e.g. "OSCILLATORY_CLOCK")
    or a string (upper-cased, hyphens normalized).
    """

````
