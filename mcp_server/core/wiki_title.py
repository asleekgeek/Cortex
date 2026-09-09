"""Wiki page title derivation — pure text transform, no I/O.

source: ADR-0317"""

from __future__ import annotations

import re

from mcp_server.core.wiki_classifier_patterns import (
    PATH_OR_URL_TITLE_PATTERNS,
    YAML_KV_TITLE_PATTERNS,
)

# ── Title prefix stripping ────────────────────────────────────────────

_TITLE_STRIP_PREFIXES = [
    re.compile(r"^#+\s*"),  # Markdown headings
    re.compile(
        r"^(Tool|System|Rule|Decision|Convention|Lesson|Note):\s*", re.IGNORECASE
    ),
    re.compile(r"^Implement the following plan:?\s*", re.IGNORECASE),
    re.compile(r"^Execute the following:?\s*", re.IGNORECASE),
    re.compile(r"^(Here is|Here's|The following)\s+", re.IGNORECASE),
]

# source: ADR-0317


_TITLE_MARKDOWN_UNWRAP = [
    re.compile(r"\*\*([^*]+)\*\*"),  # **bold** → bold
    re.compile(r"`([^`]+)`"),  # `code` → code
    re.compile(r"\*([^*]+)\*"),  # *italic* → italic
    re.compile(r"_([^_]+)_"),  # _italic_ → italic
]


# source: ADR-0317

# source: ADR-0317
_MIN_TITLE_CHARS = 10

# source: ADR-0317

# source: ADR-0317
_MAX_TITLE_CHARS = 80

# source: ADR-0317

_ENTITY_TITLE_PARTS = 2


def _line_is_title_candidate(cleaned: str) -> bool:
    """Return True iff ``cleaned`` is acceptable as a wiki page title.

    Rejects: empty/short, JSON braces, embedded paths/URLs, YAML metadata
    key:value lines, bare timestamps. Callers that get False from every
    candidate line should yield an empty title and let the deterministic
    hash fallback kick in (see ``wiki_sync._sync_to_wiki``).
    """
    if len(cleaned) <= _MIN_TITLE_CHARS:
        return False
    if cleaned.startswith("{") or cleaned.startswith("["):
        return False
    for pat in PATH_OR_URL_TITLE_PATTERNS:
        if pat.search(cleaned):
            return False
    for pat in YAML_KV_TITLE_PATTERNS:
        if pat.search(cleaned):
            return False
    return True


def derive_title(
    content: str,
    kind: str,
    tags: list[str] | None = None,
    entities: list[str] | None = None,
) -> str:
    """Derive a meaningful title for a wiki page.

    source: ADR-0317"""
    lines = content.strip().split("\n")
    first_meaningful = ""
    for line in lines:
        cleaned = line.strip()
        # source: ADR-0317

        for unwrap in _TITLE_MARKDOWN_UNWRAP:
            cleaned = unwrap.sub(r"\1", cleaned).strip()
        for pat in _TITLE_STRIP_PREFIXES:
            cleaned = pat.sub("", cleaned).strip()
        if _line_is_title_candidate(cleaned):
            first_meaningful = cleaned
            break

    # Truncate to reasonable title length
    if len(first_meaningful) > _MAX_TITLE_CHARS:
        first_meaningful = first_meaningful[:77].rsplit(" ", 1)[0] + "..."

    # Kind-specific prefixing for clarity
    prefix_map = {
        "adr": "Decision",
        "lesson": "Lesson",
        "convention": "Convention",
        "spec": "Spec",
    }
    prefix = prefix_map.get(kind, "")

    # If we have entities, use them for a more specific title
    if entities and len(entities) >= _ENTITY_TITLE_PARTS:
        entity_title = " + ".join(entities[:_ENTITY_TITLE_PARTS])
        if prefix:
            return f"{prefix}: {entity_title}"
        return entity_title

    if not first_meaningful:
        return ""

    if prefix and not first_meaningful.lower().startswith(prefix.lower()):
        return f"{prefix}: {first_meaningful}"

    return first_meaningful


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")[:80]
