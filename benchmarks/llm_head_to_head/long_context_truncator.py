"""Condition A — naive long-context with recency truncation.

source: ADR-0841

precondition: ``input_token_budget`` is a positive integer = (model context
  window) − 4_000 (output headroom).
postcondition: returned context fits in ``input_token_budget`` (counted by
  the supplied ``token_counter``); when the full conversation is shorter
  than the budget, the full conversation is returned verbatim; otherwise
  the SUFFIX of the concatenated conversation is returned (recency-keep).
invariant: token_count(returned) ≤ input_token_budget. Loop invariant in
  the truncation step: ``kept_text`` is a suffix of ``full_text`` and
  token_count(kept_text) ≤ budget at every step.

source: ADR-0841"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from benchmarks.llm_head_to_head.data_loader import BeamItem


# source: ADR-0841


MODEL_INPUT_BUDGETS: dict[str, int] = {
    # source: ADR-0841
    "claude-haiku-4-5-20251001": 196_000,
    # source: ADR-0841
    "gpt-4o-mini-2024-07-18": 124_000,
    # source: ADR-0841
    "gemini-2.0-flash": 996_000,
}

OUTPUT_HEADROOM_TOKENS = 4_000


@dataclass(frozen=True)
class TruncationResult:
    text: str
    input_tokens: int
    truncated: bool  # True iff conversation exceeded the budget and was cut


def _heuristic_token_count(text: str) -> int:
    """Conservative word→token ratio = 0.75 (1 word ≈ 1.33 tokens).

    source: ADR-0841

    pre: ``text`` is a Python str.
    post: returns int ≥ 0; for empty string returns 0.

    source: ADR-0841
    """
    if not text:
        return 0
    return int(len(text.split()) * 1.33) + 1


def format_turn(turn: dict) -> str:
    """Render one BEAM turn as plain text. Mirrors ``data.turns_to_memories``.

    pre: ``turn`` has at least ``role`` and ``content`` keys.
    post: returns a non-empty string when content is non-empty.
    """
    role = turn.get("role", "user")
    content = (turn.get("content") or "").strip()
    if not content:
        return ""
    anchor = turn.get("time_anchor", "")
    if anchor:
        return f"[Date: {anchor}] [{role}]: {content}"
    return f"[{role}]: {content}"


def build_naive_long_context(
    item: BeamItem,
    input_token_budget: int,
    token_counter: Callable[[str], int] = _heuristic_token_count,
    separator: str = "\n",
) -> TruncationResult:
    """Build condition-A context: full conversation, recency-truncated.

    source: ADR-0841"""
    if input_token_budget <= 0:
        raise ValueError(
            f"input_token_budget must be positive, got {input_token_budget}"
        )

    turn_strings = [s for t in item.turns if (s := format_turn(t))]

    # Fast path: full conversation fits.
    full_text = separator.join(turn_strings)
    full_tokens = token_counter(full_text)
    if full_tokens <= input_token_budget:
        return TruncationResult(
            text=full_text, input_tokens=full_tokens, truncated=False
        )

    # source: ADR-0841

    accepted_suffix_start = len(turn_strings)  # empty suffix
    accepted_token_count = 0
    sep_tokens = token_counter(separator) if separator else 0

    for idx in range(len(turn_strings) - 1, -1, -1):
        candidate = turn_strings[idx]
        cand_tokens = token_counter(candidate)
        # source: ADR-0841
        addition = cand_tokens + (
            sep_tokens if accepted_suffix_start < len(turn_strings) else 0
        )
        if accepted_token_count + addition > input_token_budget:
            break
        accepted_suffix_start = idx
        accepted_token_count += addition

    kept = turn_strings[accepted_suffix_start:]
    text = separator.join(kept)
    # source: ADR-0841
    final_tokens = token_counter(text)
    return TruncationResult(text=text, input_tokens=final_tokens, truncated=True)


def input_budget_for(model_id: str) -> int:
    """Lookup the input-token budget for a model, falling back to a safe default.

    pre: model_id is a vendor-specific model pin string.
    post: returns int > 0; raises KeyError on unknown pin (protocol freeze
      requires explicit pins in the manifest).
    """
    if model_id not in MODEL_INPUT_BUDGETS:
        raise KeyError(
            f"Unknown model pin {model_id!r}; protocol §10 manifest requires "
            "all model pins to be enumerated. Add to MODEL_INPUT_BUDGETS with "
            "a citation source."
        )
    return MODEL_INPUT_BUDGETS[model_id]
