# ADR-0073: benchmarks/lib/decay_sweep_runner.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/decay_sweep_runner.py`; original SHA-256 `494ac39772576b5394c9176387d4d671dd2c79a0d1ecbbae08dbee3b359830b1`.

## Original docstring, lines 59–64

````text
"""Re-emit canonical EFFECTIVE_HEAT_FN with overridden p_factor default.

    We substitute the DEFAULT clause on the canonical DDL string from
    pg_schema.py rather than duplicating the function body — this avoids
    semantic drift if the production formula ever changes.
    """
````

## Original comment, lines 120–121

````text
# source: structural — a BEAM table row is
# "<ability> <mrr> <r5> <r10> <n_questions>"
````

## Original comment, lines 205–205

````text
# ── Provenance ───────────────────────────────────────────────────────────
````

## Original docstring, lines 209–215

````text
"""Record what produced this artefact: commit, DB, environment.

    Added after the 2026-06-11 dirty-DB confound forensics: the
    20260430T111134Z artefact carried no record of which database or
    commit produced it, which cost a day of factor isolation.
    Credentials are stripped from the DB URL before recording.
    """
````

