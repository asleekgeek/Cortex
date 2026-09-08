"""Phase 5.1 — User-editable classifier rule engine.

source: ADR-0308"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from mcp_server.shared.wiki_schema_loader import ClassifierRule

REJECT_TARGETS = {"reject", "-", "", None, "none"}


@dataclass(frozen=True)
class RuleMatch:
    """Outcome of rule application against a single memory."""

    matched_rule: ClassifierRule | None
    target_kind: str | None  # None means rejection
    rationale: str


def _matches(rule: ClassifierRule, content: str, tags: set[str]) -> bool:
    """Return True if a single rule matches the input.

    source: ADR-0308"""
    pattern = rule.pattern or ""
    kind = (rule.pattern_kind or "").lower()
    if not pattern:
        return False
    if kind == "prefix":
        return content.lstrip().lower().startswith(pattern.lower())
    if kind == "substring":
        return pattern.lower() in content.lower()
    if kind == "regex":
        try:
            return bool(re.search(pattern, content, re.IGNORECASE))
        except re.error:
            return False
    if kind == "tag":
        return pattern.lower() in tags
    return False


def apply_rules(
    content: str,
    tags: list[str] | None,
    rules: list[ClassifierRule],
) -> RuleMatch:
    """Evaluate rules in order; return first match (weight-broken tie).

    Returns RuleMatch with:
      - target_kind set to the rule's target (str), or None if rejected
      - matched_rule None if no rule matched (caller falls back to
        default behaviour)
    """
    if not content or not rules:
        return RuleMatch(
            matched_rule=None,
            target_kind=None,
            rationale="no content or no rules loaded",
        )

    tag_set = {t.lower() for t in (tags or []) if isinstance(t, str)}

    # First-match-wins with tie-break: collect every match, pick by
    # (file_order, -weight) — earliest+heaviest wins.
    candidates: list[tuple[int, float, ClassifierRule]] = []
    for idx, rule in enumerate(rules):
        if _matches(rule, content, tag_set):
            candidates.append((idx, -float(rule.weight or 1.0), rule))
    if not candidates:
        return RuleMatch(
            matched_rule=None,
            target_kind=None,
            rationale="no rule matched",
        )

    # Earliest first; among ties, highest weight wins
    candidates.sort(key=lambda x: (x[0], x[1]))
    best = candidates[0][2]
    target_norm: Optional[str] = None
    if best.target_kind not in REJECT_TARGETS:
        target_norm = best.target_kind
    return RuleMatch(
        matched_rule=best,
        target_kind=target_norm,
        rationale=(
            f"rule [{best.pattern_kind}] {best.pattern!r} → "
            f"{best.target_kind or 'reject'}"
        ),
    )


__all__ = ["RuleMatch", "apply_rules"]
