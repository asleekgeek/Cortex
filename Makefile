# Benchmark reproduction targets. See benchmarks/README.md for what each
# measures, requirements, and honest wall-clock numbers.

.PHONY: longmemeval longmemeval-smoke

# Full LongMemEval-S run: 500 questions through the production recall
# path. ~40 min on a laptop (CPU embeddings), fully local, no API keys.
longmemeval:
	bash benchmarks/repro_longmemeval.sh

# 10-question sanity run — verifies the whole harness end to end
# (dataset, ephemeral DB, embeddings, recall) in a few minutes.
longmemeval-smoke:
	bash benchmarks/repro_longmemeval.sh --limit 10
