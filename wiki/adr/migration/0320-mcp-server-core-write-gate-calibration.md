---
title: "ADR-0320 — mcp_server/core/write_gate_calibration.py rationale"
status: accepted
source: mcp_server/core/write_gate_calibration.py
---

# ADR-0320 — mcp_server/core/write_gate_calibration.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Write-gate threshold auto-calibration.
````

## module — original line 3 (docstring)

````text
Per Taleb antifragile audit AF-5: the write-gate threshold should respond
to observed traffic. If too many submissions pass (90%+ acceptance), the
gate is too loose — most "novel" attempts aren't actually novel and we
are storing noise. If too few pass (<10%), the gate is too tight and we
lose real signal.
````

## module — original line 9 (docstring)

````text
Target acceptance rate: 50%. The accept/reject outcome is a binary
(Bernoulli) signal; its Shannon entropy H(p) = -p·log₂p - (1-p)·log₂(1-p)
is maximised at p = 0.5, so a balanced acceptance rate maximises the
information content of each gate decision. This is the most informative
operating point: the gate is maximally discriminative when acceptance is
balanced.
````

## module — original line 16 (docstring)

````text
Control mechanism: the calibrator holds an exponential moving average
(EMA) of the accept signal over the last ~N gate decisions, and nudges
the threshold by a fixed step when |acceptance - target| exceeds a
tolerance band. EMA decay 0.95 means ~20-sample memory; step 0.02 gives
convergence in ~50 corrections at the worst case, which is fast enough
to respond to regime changes but slow enough to not oscillate.
````

## module — original line 23 (docstring)

````text
Pure business logic — no I/O. The state lives in-process; persistence
is optional and gated on the A3 schema migration landing.
````

## module — original line 26 (docstring)

````text
References:
    Shannon, C. E. (1948). "A Mathematical Theory of Communication."
        *Bell System Technical Journal* 27. The binary entropy function
        H(p) is maximised at p = 0.5, so 50% acceptance maximises the
        information carried by each accept/reject decision.
    Taleb, N. N. (2012). *Antifragile: Things That Gain from Disorder*.
        Random House. — systems that calibrate from their own rejection
        signal are antifragile to distribution shift.

````

## CalibrationState — original line 53 (docstring)

````text
Per-domain write-gate calibration state.
````

## update_acceptance_ema — original line 76 (docstring)

````text
Update the accept-rate EMA after one gate decision.
````

## compute_threshold_adjustment — original line 117 (docstring)

````text
    The direction rule: high acceptance means gate is too permissive ->
    raise threshold. Low acceptance means gate is too strict -> lower
    threshold. Sign is fixed by the gate predicate ``novelty >= threshold``
    (see ``predictive_coding_gate.gate_decision``).
    
````

## observe_gate_decision — original line 139 (docstring)

````text
Record one gate decision and (possibly) adjust the threshold.
````

## observe_gate_decision — original line 141 (docstring)

````text
    Contract:
      pre:  state is a valid CalibrationState.
      post: returned state has total_observations = prev + 1, EMA updated
            via ``update_acceptance_ema``, and threshold adjusted IFF
            total_observations >= min_samples AND |EMA - target| >
            tolerance. When adjusted, last_adjustment_at is set to the
            new total_observations.
````

## observe_gate_decision — original line 149 (docstring)

````text
    The ``min_samples`` guard prevents adjusting on cold-start noise:
    with EMA decay 0.95 and seed EMA=0.5, the first ~20 observations
    carry most of the initial-condition bias.
    
````

## get_state — original line 184 (docstring)

````text
Fetch or lazily-initialise the calibration state for a domain.
````

## get_state — original line 186 (docstring)

````text
    Pure-ish: the module-level dict is process-local state; safe because
    calibration is monotonically tolerant of restarts (seed back to the
    default threshold -> converges again in ~50 observations).
    
````

## record — original line 205 (docstring)

````text
Convenience: observe a decision and store the updated state.
````

## reset_all_states — original line 213 (docstring)

````text
Test hook: clear the in-process calibration registry.
````

## effective_threshold — original line 221 (docstring)

````text
Return the calibration-adjusted threshold for a domain.
````

## effective_threshold — original line 223 (docstring)

````text
    Falls back to ``default_threshold`` when no calibration state exists
    (cold start — first write ever for this domain).
    
````

## module — original line 40 (comment)

````text
# ── Control constants (source: operational defaults, see module docstring) ──
````

## inline — original line 48 (comment)

````text
# Avoid adjusting on noise.
````

## inline — original line 62 (comment)

````text
# Default matches WRITE_GATE_THRESHOLD seed.
````
