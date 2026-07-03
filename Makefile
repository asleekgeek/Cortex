# Benchmark reproduction targets. See benchmarks/README.md for what each
# measures, requirements, and honest wall-clock numbers.
#
# THE single source of truth is `make reproduce` -> benchmarks/reproduce.sh.
# Everything else here is a thin scope-narrowed shortcut into that one script,
# so any invocation runs the identical clean-DB / production-recall pipeline and
# yields the same numbers. Take it, hit play, reproduce.

.PHONY: reproduce reproduce-smoke longmemeval longmemeval-smoke

# EVERYTHING: all retrieval benchmarks (LongMemEval-S, LoCoMo, BEAM-100K) plus
# the v4.0 ablation sweep, one ephemeral clean pgvector DB, one consolidated
# table + JSON manifest. Fully local, no API keys. Several hours for the full
# run (per-benchmark ~40 min + the ablation sweep).
reproduce:
	bash benchmarks/reproduce.sh

# Same pipeline end to end with tiny limits — verifies dataset, ephemeral DB,
# embeddings, recall, and the ablation runner all work, in minutes.
reproduce-smoke:
	bash benchmarks/reproduce.sh --quick

# ── Scoped shortcuts (all delegate to reproduce.sh) ──────────────────────────

# LongMemEval-S only, no ablation (the historical entry point).
longmemeval:
	bash benchmarks/reproduce.sh --only longmemeval --no-ablation

# 10-question LongMemEval sanity run.
longmemeval-smoke:
	bash benchmarks/reproduce.sh --only longmemeval --no-ablation --limit 10
