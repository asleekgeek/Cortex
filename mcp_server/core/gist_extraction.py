"""Deterministic gist extraction for oversized auto-captured tool output.

source: ADR-0183"""

from __future__ import annotations

import re

# source: ADR-0183

# source: ADR-0183
GIST_BUDGET = 3000

# source: ADR-0183


_HEAD_FRACTION = 0.40
_SIGNAL_FRACTION = 0.60

# source: ADR-0183


HIGH_VALUE_PATTERNS = [
    "error",
    "exception",
    "traceback",
    "failed",
    "failure",
    "fixed",
    "resolved",
    "success",
    "deployed",
    "migrated",
    "decided",
    "chose",
    "switched",
    "selected",
    "created",
    "deleted",
    "moved",
    "refactored",
    "test",
    "assert",
    "pass",
    "fail",
    "warning",
    "deprecated",
]


# source: ADR-0183


_ARTIFACT_LABEL = "**Artifact:**"

# source: ADR-0183


_ARTIFACT_POINTER_RE = re.compile(
    r"\*\*Artifact:\*\*\s+`(?P<path>[^`]+)`",
)


def format_artifact_pointer(path: str, char_count: int) -> str:
    """Render the pointer line linking a memory body to its raw artifact.

    Pre: ``path`` is the artifact path as a string; ``char_count`` is the length
    of the full raw output the artifact holds.
    Post: returns a single line that ``parse_artifact_pointer`` recovers
    ``path`` from. This is the ONLY place the format is defined.
    """
    return f"{_ARTIFACT_LABEL} `{path}` ({char_count} chars full output)"


def parse_artifact_pointer(content: str) -> str | None:
    """Recover the artifact path from a memory body, or None when absent.

    source: ADR-0183"""
    if not content:
        return None
    match = _ARTIFACT_POINTER_RE.search(content)
    if match is None:
        return None
    path = match.group("path").strip()
    return path or None


def needs_gist(output: str) -> bool:
    """True when output exceeds the gist budget and should be artifact-backed.

    Pre: output is a string.
    Post: returns ``len(output) > GIST_BUDGET``.
    """
    return len(output) > GIST_BUDGET


def _elision(kept: int, total: int) -> str:
    """Elision marker line recording how much of the output the gist kept."""
    return f"… [gist: {kept} of {total} chars — full output in artifact] …"


def _is_signal_line(line: str) -> bool:
    """True when a line contains any high-value pattern (case-insensitive)."""
    lower = line.lower()
    return any(kw in lower for kw in HIGH_VALUE_PATTERNS)


def extract_gist(output: str, budget: int = GIST_BUDGET) -> str:
    """Deterministic head + signal + tail gist of ``output`` within ``budget``.

    source: ADR-0183"""
    if len(output) <= budget:
        return output

    lines = output.splitlines()
    taken: set[int] = set()

    head_parts, head_end, used = _fill_head(lines, int(budget * _HEAD_FRACTION), taken)
    signal_parts, used = _fill_signal(
        lines, head_end, int(budget * _SIGNAL_FRACTION), used, taken
    )
    tail_parts, used = _fill_tail(lines, head_end, budget, used, taken)

    segments: list[str] = []
    if head_parts:
        segments.append("\n".join(head_parts))
    if signal_parts:
        segments.append("\n".join(signal_parts))
    # One elision marker before the tail records what the gist dropped.
    segments.append(_elision(used, len(output)))
    if tail_parts:
        segments.append("\n".join(tail_parts))
    return "\n".join(segments)


def _fill_head(
    lines: list[str], limit: int, taken: set[int]
) -> tuple[list[str], int, int]:
    """Take leading lines until cumulative length reaches ``limit``.

    Returns (parts, head_end_index, used_chars). Mutates ``taken``.
    """
    parts: list[str] = []
    used = 0
    head_end = 0
    for idx, line in enumerate(lines):
        if used + len(line) + 1 > limit:
            break
        parts.append(line)
        taken.add(idx)
        used += len(line) + 1
        head_end = idx + 1
    return parts, head_end, used


def _fill_signal(
    lines: list[str], start: int, limit: int, used: int, taken: set[int]
) -> tuple[list[str], int]:
    """Take signal lines after the head window until ``limit``. Mutates taken."""
    parts: list[str] = []
    for idx in range(start, len(lines)):
        line = lines[idx]
        if idx in taken or not _is_signal_line(line):
            continue
        if used + len(line) + 1 > limit:
            break
        parts.append(line)
        taken.add(idx)
        used += len(line) + 1
    return parts, used


def _fill_tail(
    lines: list[str], start: int, budget: int, used: int, taken: set[int]
) -> tuple[list[str], int]:
    """Take trailing lines (from the end) until ``budget``. Mutates taken."""
    parts: list[str] = []
    for idx in range(len(lines) - 1, start - 1, -1):
        line = lines[idx]
        if idx in taken:
            continue
        if used + len(line) + 1 > budget:
            break
        parts.append(line)
        taken.add(idx)
        used += len(line) + 1
    parts.reverse()
    return parts, used
