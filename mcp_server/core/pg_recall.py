"""PG recall: intent-adaptive retrieval via recall_memories() + FlashRank reranking.

source: ADR-0216"""

from __future__ import annotations

from typing import Any

# source: ADR-0216


from mcp_server.core.pg_recall_signals import (  # noqa: F401 — source: ADR-0216
    _get_active_goal,
    _get_titans,
    _get_user_mood,
)
from mcp_server.core.pg_recall_context import RecallContext
from mcp_server.core.pg_recall_stages import (
    _chronological_rerank,  # noqa: F401 — source: ADR-0216
    run_recall_pipeline,
)

# source: ADR-0216

from mcp_server.core.pg_recall_weights import (  # noqa: E402 — source: ADR-0216
    compute_pg_weights,
)


def recall(
    query: str,
    store: Any,
    embeddings: Any,
    *,
    top_k: int = 10,
    domain: str | None = None,
    directory: str | None = None,
    agent_topic: str | None = None,
    min_heat: float = 0.01,
    rerank: bool = True,
    rerank_alpha: float = 0.70,
    wrrf_k: int = 60,
    momentum_state: dict | None = None,
    include_globals: bool = True,
    familiarity_shortcut: bool = False,
    cross_domain: bool = False,
    sa_mode: str = "tail",
) -> list[dict[str, Any]]:
    """Thin recall() wrapper; see pg_recall_context.py for tuning-knob citations."""
    ctx = RecallContext(
        query=query,
        store=store,
        embeddings=embeddings,
        domain=domain,
        directory=directory,
        agent_topic=agent_topic,
        min_heat=min_heat,
        wrrf_k=wrrf_k,
        include_globals=include_globals,
        cross_domain=cross_domain,
        sa_mode=sa_mode,
        rerank=rerank,
        rerank_alpha=rerank_alpha,
        familiarity_shortcut=familiarity_shortcut,
        top_k=top_k,
        momentum_state=momentum_state,
    )
    return run_recall_pipeline(ctx)


# source: ADR-0216


from mcp_server.core.pg_recall_assembly import assemble_context  # noqa: E402 — source: ADR-0216

__all__ = ["assemble_context", "compute_pg_weights", "recall"]
