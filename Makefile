# source: ADR-0813







.PHONY: reproduce reproduce-smoke longmemeval longmemeval-smoke

# source: ADR-0813



reproduce:
	bash benchmarks/reproduce.sh

# Same pipeline end to end with tiny limits — verifies dataset, ephemeral DB,
# embeddings, recall, and the ablation runner all work, in minutes.
reproduce-smoke:
	bash benchmarks/reproduce.sh --quick

# ── Scoped shortcuts (all delegate to reproduce.sh) ──────────────────────────

# source: ADR-0813
longmemeval:
	bash benchmarks/reproduce.sh --only longmemeval --no-ablation

# 10-question LongMemEval sanity run.
longmemeval-smoke:
	bash benchmarks/reproduce.sh --only longmemeval --no-ablation --limit 10
