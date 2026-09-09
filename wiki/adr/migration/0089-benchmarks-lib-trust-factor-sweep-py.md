# ADR-0089: benchmarks/lib/trust_factor_sweep.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/trust_factor_sweep.py`; original SHA-256 `527a4f37e08e6e68624acd11622b09e8f8b5de392008184b5b72d20f73663e3e`.

## Original docstring, lines 1–21

````text
"""Adversarial arm of the trust-factor calibration (issue #368).

Pre-registration, decision rule and grid:
`docs/provenance/trust-factor-calibration.md`.

The decision rule has two members: "defends 4/4 adversarial scenarios" and
"every gated floor still holds". The floors are measured by the expensive arm
(`benchmarks/trust_factor_sweep.sh`, one `reproduce.sh` per cell). This module
measures the first member — which is cheap (SQLite, in-memory, seconds per
point) and, until this file existed, was the only half of the rule with no
committed artefact behind it: the §Grid table was carried in prose alone.

Montage is the one already asserted by
`tests_py/infrastructure/test_sqlite_trust_ranking.py` — same corpus, same
embedding construction, same recall entry point — so this sweep and that suite
argue about the same passages. A scenario counts as DEFENDED when both
memories are retrieved and the legitimate one outranks the adversarial one:
a demotion, not a filter.

    python -m benchmarks.lib.trust_factor_sweep [OUT_DIR]
"""
````

## Original comment, lines 45–48

````text
# source: docs/provenance/trust-factor-calibration.md §Grid — the prose table
# it reports (1.0 -> 0/4, 0.95-0.80 -> 2/4, 0.70-0.20 -> 4/4) is stated over
# these points, so the sweep re-measures exactly them and can confirm or
# refute the table rather than sampling somewhere else.
````

## Original docstring, lines 68–74

````text
"""384-dim unit vector at `similarity` cosine to the query direction.

    Same Gram-Schmidt construction as the two trust-ranking test modules,
    restated here for the same reason they restate it from each other: those
    helpers are bound to test modules that skip under conditions which do not
    apply to this sweep.
    """
````

## Original docstring, lines 97–104

````text
"""Run one (scenario, W) point on a throwaway in-memory store.

    Post: `defended` is True only when BOTH memories came back and the
    legitimate one ranks ahead. A missing adversarial entry is reported as
    `retrieved_adversarial: false` and NOT counted as a defence — a filtered
    attacker is a different mechanism than a demoted one, and the pre-
    registration asks about demotion.
    """
````

