"""Generate stable content identifiers for wiki pages.

source: ADR-0304
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

# Canonical UUID4 hex form, case-insensitive (5 groups separated by hyphens).
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PageIdentity:
    """The stable identity carried in a page's frontmatter.

    Fields:
        page_id: UUID4 string in canonical hex form. Immutable across
            rename, re-classification, and edits.
        memory_id: optional integer memory ID for pages synthesised
            from a stored memory. Preserved for back-compat with
            existing ``wiki_sync`` output.
    """

    page_id: str
    memory_id: int | None = None

    def __post_init__(self) -> None:
        if not is_valid_page_id(self.page_id):
            raise ValueError(
                f"invalid page_id: {self.page_id!r}; expected canonical "
                f"UUID4 hex form (8-4-4-4-12)"
            )


def is_valid_page_id(value: str) -> bool:
    """True iff ``value`` is a canonical UUID4 hex string.

    Accepts both upper and lower case but the canonical form is lower.
    """
    return bool(_UUID_RE.match(value or ""))


def generate_page_id() -> str:
    """Mint a fresh UUID4 in canonical hex form.

    source: ADR-0304"""
    return str(uuid.uuid4())


def extract_page_id(frontmatter: dict[str, object]) -> str | None:
    """Return the existing ``id`` field from frontmatter, if valid.

    source: ADR-0304"""
    raw = frontmatter.get("id")
    if not isinstance(raw, str):
        return None
    if not is_valid_page_id(raw):
        return None
    return raw.lower()


def ensure_page_id(frontmatter: dict[str, object]) -> tuple[str, bool]:
    """Return the page's existing ID or mint a new one.

    Returns ``(page_id, minted)`` where ``minted`` is True if a new ID
    was generated (the caller should persist the updated frontmatter).
    """
    existing = extract_page_id(frontmatter)
    if existing is not None:
        return existing, False
    return generate_page_id(), True


def extract_memory_id(frontmatter: dict[str, object]) -> int | None:
    """Return the ``memory_id`` field if present and integer-coercible.

    Pages synthesised by ``wiki_sync`` carry the originating memory ID
    in their frontmatter. The identity module exposes it for callers
    that want to round-trip the field without re-parsing.
    """
    raw = frontmatter.get("memory_id")
    if not isinstance(raw, (int, float, str)):
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def page_identity_from_frontmatter(
    frontmatter: dict[str, object],
) -> PageIdentity | None:
    """Parse a ``PageIdentity`` from frontmatter, or None if no id present."""
    page_id = extract_page_id(frontmatter)
    if page_id is None:
        return None
    return PageIdentity(page_id=page_id, memory_id=extract_memory_id(frontmatter))
