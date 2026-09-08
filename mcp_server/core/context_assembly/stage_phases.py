"""Phase builders for the three-phase stage-aware assembler.

source: ADR-0151"""

from __future__ import annotations

from typing import Any

from mcp_server.core.context_assembly.budget import (
    estimate_tokens,
    proportional_share,
)
from mcp_server.core.context_assembly.condensers import condense_memory_content


def _tags_of(memory: dict[str, Any]) -> list[str]:
    """Tag hints for the condenser dispatch; [] when absent or malformed."""
    tags = memory.get("tags")
    if isinstance(tags, list):
        return [str(t) for t in tags]
    return []


def pack_within_budget(
    memories: list[dict[str, Any]],
    token_budget: int | None,
) -> tuple[list[str], int]:
    """Render ``memories`` as text under ``token_budget``, condensing.

    source: ADR-0151

    Returns ``(texts, tokens_used)`` where ``tokens_used`` is the
    estimated token count of the rendered texts.
    """
    if token_budget is None:
        texts = [str(m.get("content", "")) for m in memories]
        return texts, sum(estimate_tokens(t) for t in texts)

    texts = []
    remaining = max(0, token_budget)
    used = 0
    for i, memory in enumerate(memories):
        content = str(memory.get("content", ""))
        share = proportional_share(remaining, len(memories) - i)
        if estimate_tokens(content) <= share:
            rendered = content
        else:
            rendered = condense_memory_content(content, share, tags=_tags_of(memory))
        texts.append(rendered)
        spent = estimate_tokens(rendered)
        used += spent
        remaining = max(0, remaining - spent)
    return texts, used


def phase_budget(token_budget: int | None, proportion: float) -> int | None:
    """This phase's slice of the total budget; None propagates as None."""
    if token_budget is None:
        return None
    return int(token_budget * proportion)


def render_own_stage(
    selected: list[dict[str, Any]],
    token_budget: int | None,
) -> tuple[str, int, list[dict[str, Any]]]:
    """Phase 1 — own-stage text plus the selected-memory records.

    The records carry the ORIGINAL content: they are the retrieval
    record downstream evaluators score against, and must not inherit the
    reader-facing condensation applied to the text.
    """
    texts, used = pack_within_budget(selected, token_budget)
    records = [
        {
            "memory_id": memory.get("memory_id"),
            "content": memory.get("content", ""),
            "score": memory.get("score", 0.0),
            "phase": 1,
        }
        for memory in selected
    ]
    return "\n\n".join(texts).strip(), used, records


def render_adjacent(
    scored: list[tuple[dict[str, Any], float]],
    token_budget: int | None,
    max_chunks: int,
) -> tuple[str, int, list[dict[str, Any]]]:
    """Phase 2 — cross-stage text for the top ``max_chunks`` PPR hits."""
    top = scored[:max_chunks]
    memories = [memory for memory, _ in top]
    texts, used = pack_within_budget(memories, token_budget)
    records = [
        {
            "memory_id": memory.get("memory_id") or memory.get("id"),
            "content": memory.get("content", ""),
            "score": float(score),
            "phase": 2,
        }
        for memory, score in top
    ]
    return "\n\n".join(texts).strip(), used, records


def render_summaries(
    summaries: list[tuple[str, str]],
    token_budget: int | None,
) -> tuple[str, int, list[str]]:
    """Phase 3 — ``[stage] summary`` lines for the uncovered stages.

    Returns ``(text, tokens_used, stage_ids)``; ``stage_ids`` names the
    stages that reached the output, in order.
    """
    labelled = [
        {"content": f"[{stage_id}] {summary}"} for stage_id, summary in summaries
    ]
    texts, used = pack_within_budget(labelled, token_budget)
    return (
        "\n\n".join(texts).strip(),
        used,
        [stage_id for stage_id, _ in summaries],
    )
