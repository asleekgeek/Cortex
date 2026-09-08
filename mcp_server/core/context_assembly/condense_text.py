"""Condensers for free-text conversational content.

source: ADR-0144
"""

from __future__ import annotations

import re

from mcp_server.core.context_assembly.budget import (
    estimate_tokens,
    truncate_to_budget,
)

# source: ADR-0144

_FIRST_PLUS_LAST_SENTENCES = 2


# ── User message condenser ──────────────────────────────────────────────
# Strategy: keep the first sentence (establishes intent), any questions
# (explicit interrogatives), and the last sentence (final state of
# thought), dropping middle filler.


def condense_user_message(text: str, token_budget: int) -> str:
    """Keep first sentence + questions + last sentence, within budget."""
    if estimate_tokens(text) <= token_budget:
        return text
    sentences = _split_sentences(text)
    if len(sentences) <= _FIRST_PLUS_LAST_SENTENCES:
        return truncate_to_budget(text, token_budget)

    kept: list[str] = [sentences[0]]
    for s in sentences[1:-1]:
        if "?" in s:
            kept.append(s)
    kept.append(sentences[-1])
    result = " ".join(kept).strip()
    # source: ADR-0144

    if estimate_tokens(result) <= token_budget:
        return result
    return truncate_to_budget(result, token_budget)


# source: ADR-0144


def condense_timeline_event(text: str, token_budget: int) -> str:
    """Extract when/what/who into a fixed-slot format within budget.

    source: ADR-0144
    """
    if estimate_tokens(text) <= token_budget:
        return text

    date_match = re.search(
        r"\[Date:\s*([^\]]+)\]|(\d{4}-\d{2}-\d{2})|"
        r"(\w+\s+\d{1,2},?\s+\d{4})",
        text,
    )
    date = (
        date_match.group(1) or date_match.group(2) or date_match.group(3)
        if date_match
        else ""
    )

    first = _first_sentence(text)
    compressed = f"[{date}] {first}" if date else first
    # source: ADR-0144

    if estimate_tokens(compressed) <= token_budget:
        return compressed
    return truncate_to_budget(compressed, token_budget)


# ── Helpers ─────────────────────────────────────────────────────────────


def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter; good enough for condensers."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def _first_sentence(text: str) -> str:
    sents = _split_sentences(text)
    return sents[0] if sents else text
