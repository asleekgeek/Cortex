# ADR-0082: benchmarks/lib/noise_floor.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/noise_floor.py`; original SHA-256 `0f6e22aa497fc3adaf3bed8064b998dd42a654db46a9ec4b8a129378bc0929ef`.

## Original docstring, lines 1–12

````text
"""Empirical noise-floor measurement for verification thresholds.

Runs the SAME benchmark config N times from the SAME DB snapshot and
reports per-metric mean, std, p95, range. The measured σ becomes the
'smallest detectable effect' threshold for ablation / N-scan / decay-
sweep experiments — anything within σ is statistical noise.

Source: Curie verification audit — "the smallest reportable effect must
exceed the empirical noise floor of the measurement apparatus" (Fisher,
*The Design of Experiments*, 1935; restated for benchmark harnesses in
docs/program/n-scan-spec.md §noise_floor).
"""
````

## Original comment, lines 42–43

````text
# source: spec §Deliverable 3 — "smallest detectable effect" defined as
# 2σ following the standard 95% confidence threshold (Fisher 1935).
````

## Original comment, lines 57–58

````text
# source: structural — a sample standard deviation is undefined below two
# samples
````

