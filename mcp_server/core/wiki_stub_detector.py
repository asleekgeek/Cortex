"""Stub detector for wiki pages — pure logic, no I/O.

source: ADR-0311"""

from __future__ import annotations

import re
from typing import Final

# ── Recognised placeholder markers ────────────────────────────────────


PLACEHOLDER_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # Groomer placeholders.
    re.compile(r"^_\(none identified\)_\s*$"),
    re.compile(r"^_\(to be filled\)_\s*$"),
    re.compile(r"^_To be written\._\s*$"),
    re.compile(r"^_TBD_\s*$", re.IGNORECASE),
    # Looser variants (no surrounding underscores).
    re.compile(r"^\(none identified\)\s*$"),
    re.compile(r"^\(to be filled\)\s*$"),
    re.compile(r"^To be written\.?\s*$"),
    re.compile(r"^TBD\s*$"),
    # Boilerplate "(to be filled)" embedded in headings ("# Foo (to be filled)").
    re.compile(r".*\(to be filled\)\s*$", re.IGNORECASE),
)


_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_BLANK_RE = re.compile(r"^\s*$")


def _is_placeholder_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    for pat in PLACEHOLDER_PATTERNS:
        if pat.match(stripped):
            return True
    return False


def _is_content_line(line: str) -> bool:
    """A content line is one that contributes meaning — not a heading,
    not blank, not a horizontal rule, not a fence marker.

    source: ADR-0311"""
    if _BLANK_RE.match(line):
        return False
    stripped = line.strip()
    if _HEADING_RE.match(stripped):
        return False
    if stripped in ("---", "***", "```"):
        return False
    if stripped.startswith("```"):
        return False
    return True


def stub_score(body: str) -> float:
    """Fraction of content lines that are placeholder markers.

    Returns 0.0 when the body has no placeholder content (or no content
    at all — see ``is_stub`` for the empty-body case). 1.0 when every
    non-heading non-blank line is a placeholder marker.
    """
    if not body:
        return 0.0
    content_lines = [ln for ln in body.splitlines() if _is_content_line(ln)]
    if not content_lines:
        return 0.0
    placeholder_count = sum(1 for ln in content_lines if _is_placeholder_line(ln))
    return placeholder_count / len(content_lines)


# source: ADR-0311
DEFAULT_STUB_THRESHOLD: Final[float] = 0.5


def is_stub(body: str, threshold: float = DEFAULT_STUB_THRESHOLD) -> bool:
    """True iff the body's stub score meets or exceeds ``threshold``.

    Also returns True for a body that contains *any* content lines and
    *all* of them are placeholder markers, regardless of threshold — a
    page whose entire authored content is placeholders is unambiguously
    a stub.
    """
    score = stub_score(body)
    if score >= 1.0:
        return True
    return score >= threshold


def placeholder_count(body: str) -> int:
    """Total placeholder marker lines in the body. Useful for reporting
    aggregate noise across the wiki without re-deriving the score.
    """
    if not body:
        return 0
    return sum(1 for ln in body.splitlines() if _is_placeholder_line(ln))


# source: ADR-0311


_KV_METADATA_LINE = re.compile(
    r"^[A-Z][a-zA-Z _\-]{0,30}:\s*\S",  # source: ADR-0311
)
_LIST_BULLET = re.compile(r"^(?:[-*+]\s|\d+\.\s)")


def prose_char_count(body: str) -> int:
    """Count characters of actual prose in ``body``.

    source: ADR-0311"""
    if not body:
        return 0
    total = 0
    in_fence = False
    for ln in body.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if s.startswith("#"):
            continue
        if _LIST_BULLET.match(s):
            continue
        if _KV_METADATA_LINE.match(s):
            continue
        total += len(s)
    return total


# source: ADR-0311


DEFAULT_SHALLOW_THRESHOLD: Final[int] = 500


def is_shallow(body: str, threshold: int = DEFAULT_SHALLOW_THRESHOLD) -> bool:
    """True when the body has fewer than ``threshold`` prose chars.

    A shallow page isn't a stub (it doesn't have placeholder markers),
    isn't a classifier-reject (the content is on-topic), but it isn't
    an *explanation* either — it's metadata dressed up as a page.
    """
    return prose_char_count(body) < threshold
