"""Condenser for structured (subject, predicate, object) content.

source: ADR-0143
"""

from __future__ import annotations

import re

from mcp_server.core.context_assembly.budget import (
    estimate_tokens,
    truncate_to_budget,
)

# source: ADR-0143

_MIN_ARROWS_FOR_TRIPLES = 2


# ── Entity-triple condenser ─────────────────────────────────────────────
# Strategy: keep (subject, predicate, object) triples verbatim, drop
# anything else. Triples are already maximally compressed.


def condense_entity_triples(text: str, token_budget: int) -> str:
    """Keep only lines matching triple patterns, in budget order."""
    if estimate_tokens(text) <= token_budget:
        return text
    triple_re = re.compile(
        r"^\s*([^→\->:]+?)\s*(?:→|->|:)\s*([^→\->:]+?)\s*(?:→|->|:)\s*(.+?)\s*$"
    )
    kept_lines: list[str] = []
    used = 0
    for line in text.split("\n"):
        if triple_re.match(line):
            t = estimate_tokens(line)
            if used + t > token_budget:
                break
            kept_lines.append(line)
            used += t
    if kept_lines:
        return "\n".join(kept_lines)
    return truncate_to_budget(text, token_budget)
