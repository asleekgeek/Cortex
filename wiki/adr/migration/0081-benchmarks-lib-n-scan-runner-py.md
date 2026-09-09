# ADR-0081: benchmarks/lib/n_scan_runner.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/n_scan_runner.py`; original SHA-256 `9a3d6a30446f7e4d982615bc40c8ee5f538ab6d309b4119c427c8860a0d6e0ca`.

## Original docstring, lines 1–16

````text
"""DEPRECATED stub — superseded by ``benchmarks.lib.latency_runner``.

The synthetic-corpus N-scan harness was renamed to ``latency_runner``
because retrieval metrics on the synthetic corpus produced identical
scores for cortex_full vs cortex_flat at N>=10k (the corpus has no
thermodynamic structure for heat to discriminate). The harness is now
the latency-only sibling; claim-bearing E2 retrieval lives in
``e2_subsample_runner`` (real benchmark subsample) and
``e2_zipf_runner`` (Zipf access pattern). See module docstring of
``latency_runner`` and ``docs/provenance/verification-protocol.md`` §E2 for
detail.

This stub re-exports the public surface so existing callers and any
in-flight processes (e.g. ``python -m benchmarks.lib.n_scan_runner``
already running) continue working without breakage.
"""
````

