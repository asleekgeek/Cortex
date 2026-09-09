"""Normalize capture boilerplate for write-gate novelty scoring without changing stored
content or embeddings.

source: ADR-0115
"""

from __future__ import annotations

import re

# ── Auto-capture template markers
# (hooks/post_tool_capture.py::_build_memory_content) ──

_AUTO_CAPTURE_HEADER_RE = re.compile(r"^# Tool: \S")

_TOOL_HEADER_LINE_RE = re.compile(r"^# Tool: \S+[ \t]*$\n?", re.MULTILINE)
# source: ADR-0115


_LABELED_REF_PREFIX_RE = re.compile(
    r"^\*\*(?:File|Command|Read|Glob|Grep):\*\*[ \t]*", re.MULTILINE
)
_OUTPUT_SECTION_HEADER_RE = re.compile(r"^## Output[ \t]*$\n?", re.MULTILINE)
_OUTPUT_LABEL_LINE_RE = re.compile(r"^\*\*Output:\*\*[ \t]*$\n?", re.MULTILINE)
# The artifact pointer line is pure boilerplate (content-addressed path +
# char count) with no fact-level payload — dropped entirely.
_ARTIFACT_POINTER_LINE_RE = re.compile(r"^\*\*Artifact:\*\*.*$\n?", re.MULTILINE)
_FENCE_DELIMITER_LINE_RE = re.compile(r"^```[\w-]*[ \t]*$\n?", re.MULTILINE)
_BLANK_RUN_RE = re.compile(r"\n{3,}")

# ── Derived-fact template marker (core/curation.py::identify_derivable_facts) ──

_DERIVED_FACT_RE = re.compile(
    r"^(?P<src>.+?) and (?P<tgt>.+?) are strongly linked "
    r"\((?P<rel_type>[^,]+), weight=(?P<weight>[\d.]+)\)$"
)


def is_auto_capture_template(content: str) -> bool:
    """True when ``content`` was built by ``_build_memory_content``.

    Precondition: none. Postcondition: True iff the FIRST non-blank line
    matches the fixed ``# Tool: <name>`` header emitted by the PostToolUse
    hook — the one structural invariant every auto-capture shares
    regardless of tool kind or payload.
    """
    if not content:
        return False
    return bool(_AUTO_CAPTURE_HEADER_RE.match(content.lstrip()))


def is_derived_fact_template(content: str) -> bool:
    """True when ``content`` is a memify-derive relationship sentence."""
    if not content:
        return False
    return bool(_DERIVED_FACT_RE.match(content.strip()))


def _normalize_auto_capture(content: str) -> str:
    text = _TOOL_HEADER_LINE_RE.sub("", content)
    text = _ARTIFACT_POINTER_LINE_RE.sub("", text)
    text = _OUTPUT_SECTION_HEADER_RE.sub("", text)
    text = _OUTPUT_LABEL_LINE_RE.sub("", text)
    text = _LABELED_REF_PREFIX_RE.sub("", text)
    text = _FENCE_DELIMITER_LINE_RE.sub("", text)
    text = _BLANK_RUN_RE.sub("\n\n", text)
    return text.strip()


def _normalize_derived_fact(content: str) -> str:
    m = _DERIVED_FACT_RE.match(content.strip())
    assert m is not None  # caller already checked is_derived_fact_template
    return (
        f"{m.group('src')} {m.group('tgt')} {m.group('rel_type')} {m.group('weight')}"
    )


def capture_template_normalize(content: str) -> str:
    """Strip auto-capture / derived-fact template skeleton before embedding.

    source: ADR-0115"""
    if not content:
        return content
    if is_derived_fact_template(content):
        return _normalize_derived_fact(content)
    if not is_auto_capture_template(content):
        return content
    normalized = _normalize_auto_capture(content)
    return normalized if normalized else content
