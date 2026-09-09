# ADR-0358: mcp_server/handlers/consolidation/embedding_upgrade.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidation/embedding_upgrade.py`; original SHA-256 `e804e4666a76614ca4ba9b2fbfdbbf64bd5ef7ccb164b05d26e095ea7cc7c671`.

## Original docstring, lines 1–14

````text
"""Embedding-upgrade cycle: re-embed fallback memories once the model arrives.

The scheduled other half of the #169 zero-download fallback. When a session ran
on the download-free algorithmic provider (``embedding_model = 'fallback'``) and
a later session finds the neural model present, this maintenance cycle re-embeds
those memories with the neural encoder and restamps them 'neural' — so the
store transparently upgrades to full-fidelity vectors over time instead of
leaving two incompatible spaces side by side forever.

Bounded per run (``_MAX_UPGRADE_PER_CYCLE``) so a large backlog is drained
across several consolidations rather than in one blocking pass, mirroring the
other streaming cycles. No-op when the current encoder is still fallback (no
neural model to upgrade to) or when the store has no fallback worklist.
"""
````

## Original comment, lines 26–28

````text
# source: matches sleep_compute.run_sleep_compute_streamed's max_reembed=100
# bound (mcp_server/core/sleep_compute.py) — the same per-cycle re-embed budget
# already used for stale/compressed embeddings, reused here for parity.
````

