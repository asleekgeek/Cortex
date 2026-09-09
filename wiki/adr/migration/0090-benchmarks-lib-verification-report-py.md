# ADR-0090: benchmarks/lib/verification_report.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/verification_report.py`; original SHA-256 `036d6e21041d2573936daf015a15b706718afb68282589e491b8e840d62e7d1f`.

## Original docstring, lines 1–27

````text
"""Master verification-report aggregator.

Reads JSON results from all 6 verification experiments and emits a single
Markdown report — the artifact that updates the paper's Limitations section.

Sources:
    E1 ablation       → benchmarks/results/ablation/<run>/result.json
    E2 N-scan         → benchmarks/results/n_scan/<run>/result.json
    E3 decay sweep    → benchmarks/results/decay_sweep/<run>/result.json
    E4 longitudinal   → benchmarks/results/longitudinal/<run>/result.json
    E5 cross-benchmark →
        benchmarks/results/cross_benchmark/<run>/{calibration,evaluation,reference}.json
    E6 telemetry      → ~/.claude/methodology/telemetry.jsonl

Critical contract:
    - Numbers come straight from the JSON files. The aggregator does NO
      computation other than rounding for display + 95% CIs from per-question
      raw data when present.
    - Missing experiments render as `// TODO: not yet run`. They are NEVER
      filled with placeholders.

CLI:
    python -m benchmarks.lib.verification_report
        [--out docs/papers/verification-results.md]
        [--results-dir benchmarks/results]
        [--telemetry ~/.claude/methodology/telemetry.jsonl]
"""
````

## Original comment, lines 40–41

````text
# Pre-registered hypotheses + thresholds (locked at protocol-write time).
# Source: docs/provenance/verification-protocol.md §1-6.
````

## Original docstring, lines 103–110

````text
"""Data only — deliberately no methods. mutmut's mutation generator
    categorically excludes the body of any `@dataclass`-decorated class
    (`mutmut/mutation/file_mutation.py:236`), so logic placed on methods
    here would carry zero mutation coverage no matter how the test loader
    names the module (issue #262 3rd pass; issue #282). `exp_result_name` /
    `exp_result_threshold` / `exp_result_verdict` below carry the same
    logic as free functions instead.
    """
````

## Original comment, lines 149–151

````text
# source: contract stated in the _bootstrap_ci docstring ("None if <10
# values"); the 10-sample minimum is a pre-existing tuned value, extracted
# unchanged (#197 family 3), provenance not recorded at introduction
````

## Original comment, lines 269–271

````text
# Minimum telemetry samples before a p95 recall latency is reported at all.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## Original comment, lines 340–342

````text
# Claim-column width in the Markdown summary table; longer claims are elided.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

