"""Condensers for code-shaped content.

source: ADR-0140
"""

from __future__ import annotations

from mcp_server.core.context_assembly.budget import (
    estimate_tokens,
    truncate_to_budget,
)
from mcp_server.core.context_assembly.condense_text import _first_sentence

# source: ADR-0140
# source: ADR-0140
_MIN_INDENT_RUNS_FOR_CODE = 3


# ── Code block condenser ────────────────────────────────────────────────
# Strategy: signatures only (function/class/imports), same spirit as the
# Swift condenseContracts.


def condense_code_block(text: str, token_budget: int) -> str:
    """Keep imports, class, function, protocol, and method signatures only."""
    if estimate_tokens(text) <= token_budget:
        return text

    kept: list[str] = []
    used = 0
    signature_prefixes = (
        "import ",
        "from ",
        "class ",
        "def ",
        "async def ",
        "struct ",
        "enum ",
        "protocol ",
        "func ",
        "interface ",
        "@",  # decorators
        "//",  # comments
        "#",  # comments
    )
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in signature_prefixes):
            t = estimate_tokens(line)
            if used + t > token_budget:
                break
            kept.append(line)
            used += t
    if kept:
        return "\n".join(kept)
    return truncate_to_budget(text, token_budget)


# ── Assistant message condenser ─────────────────────────────────────────
# Strategy: keep code blocks verbatim (they're high-density facts that
# don't survive summarization), summarize prose by keeping topic
# sentences.


def condense_assistant_message(text: str, token_budget: int) -> str:
    """Preserve code blocks verbatim, compress prose between them."""
    if estimate_tokens(text) <= token_budget:
        return text

    parts = _split_by_code_blocks(text)
    # Parts alternate: prose, code, prose, code, ...
    # Priority: keep all code, compress prose.
    code_parts = [p for is_code, p in parts if is_code]
    prose_parts = [p for is_code, p in parts if not is_code]

    code_tokens = sum(estimate_tokens(p) for p in code_parts)
    if code_tokens >= token_budget:
        return _keep_leading_code_blocks(code_parts, token_budget, text)

    # source: ADR-0140

    prose_budget = token_budget - code_tokens
    compressed_prose = _compress_prose_parts(prose_parts, prose_budget)
    joined = _reassemble_in_order(parts, code_parts, compressed_prose)
    return joined if joined else truncate_to_budget(text, token_budget)


def _keep_leading_code_blocks(
    code_parts: list[str], token_budget: int, text: str
) -> str:
    """Even the code exceeds budget — keep first N code blocks that fit.

    source: ADR-0140"""
    kept: list[str] = []
    used = 0
    for p in code_parts:
        t = estimate_tokens(p)
        if used + t > token_budget:
            break
        kept.append(p)
        used += t
    if not kept:
        return truncate_to_budget(text, token_budget)
    return "\n\n".join(kept)


def _compress_prose_parts(prose_parts: list[str], prose_budget: int) -> list[str]:
    """Cut each prose segment to its first sentence, floored per-segment."""
    per_prose = max(20, prose_budget // len(prose_parts))
    return [_first_sentence(p)[: per_prose * 3] for p in prose_parts]


def _reassemble_in_order(
    parts: list[tuple[bool, str]],
    code_parts: list[str],
    compressed_prose: list[str],
) -> str:
    """Interleave verbatim code and compressed prose back into source order."""
    out: list[str] = []
    pi = ci = 0
    for is_code, _ in parts:
        if is_code:
            # source: ADR-0140

            if ci < len(code_parts):
                out.append(code_parts[ci])
                ci += 1
        else:
            if pi < len(compressed_prose):
                out.append(compressed_prose[pi])
                pi += 1
    return "\n\n".join(s for s in out if s.strip())


# ── Helpers ─────────────────────────────────────────────────────────────


def _has_code_blocks(text: str) -> bool:
    return "```" in text or text.count("    ") >= _MIN_INDENT_RUNS_FOR_CODE


def _split_by_code_blocks(text: str) -> list[tuple[bool, str]]:
    """Split markdown-style text into (is_code, chunk) segments."""
    segments: list[tuple[bool, str]] = []
    in_code = False
    buf: list[str] = []
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            if buf:
                segments.append((in_code, "\n".join(buf)))
                buf = []
            in_code = not in_code
            buf.append(line)
        else:
            buf.append(line)
    if buf:
        segments.append((in_code, "\n".join(buf)))
    return segments
