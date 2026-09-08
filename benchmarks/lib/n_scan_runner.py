"""DEPRECATED stub — superseded by ``benchmarks.lib.latency_runner``.

This stub re-exports the public surface so existing callers and any
in-flight processes (e.g. ``python -m benchmarks.lib.n_scan_runner``
already running) continue working without breakage.

source: ADR-0081"""

from __future__ import annotations

from benchmarks.lib.latency_runner import (  # noqa: F401
    CorpusItem,
    DEFAULT_DB_URL,
    LATENCY_ONLY,
    MIN_QUERIES,
    RESULTS_DIR,
    TEMPLATES_PATH,
    TrialResult,
    main,
    run_trial,
    synth_corpus,
)


if __name__ == "__main__":
    raise SystemExit(main())
