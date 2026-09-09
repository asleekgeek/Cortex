"""Detect wiki kind, lifecycle, audience, and provenance.

source: ADR-0305
"""

from __future__ import annotations

from mcp_server.core.wiki_axis_registry import (
    AXIS_AUDIENCE,
    AXIS_LIFECYCLE,
    AXIS_PROVENANCE,
    axis_registry_default_for,
    axis_registry_values,
    get_registry,
    match_axis,
)
from mcp_server.core.wiki_axis_registry import AXIS_KIND

# source: ADR-0305


LEGACY_KIND_MAP: dict[str, str] = {
    "adr": "adr",
    "lesson": "explanation",
    "convention": "explanation",
    "spec": "rfc",
    "note": "explanation",
    "reference": "reference",
}


def detect_modern_kind(
    content: str,
    tags: list[str] | None,
    legacy_kind: str,
) -> str:
    """Pick a modern kind for a content+tags pair.

    source: ADR-0305"""

    matches = match_axis(content, tags, AXIS_KIND, get_registry())
    if matches:
        return matches[0]
    return LEGACY_KIND_MAP.get(legacy_kind, "explanation")


def detect_provenance(tags: list[str] | None) -> str:
    """Pick a provenance value via the registry.

    Falls back to the default-flagged provenance value (``human`` in the
    bootstrap seed) when no pattern or tag matches. Users register new
    provenances by writing ``wiki/_schema/provenances/<name>.md``.
    """
    reg = get_registry()
    matches = match_axis("", tags, AXIS_PROVENANCE, reg)
    if matches:
        return matches[0]
    default = axis_registry_default_for(reg, AXIS_PROVENANCE)
    return default.name if default is not None else "human"


def detect_audiences(
    content: str, tags: list[str] | None, kind: str
) -> tuple[str, ...]:
    """Pick one or more audience values via the registry.

    source: ADR-0305"""
    reg = get_registry()
    matches = list(match_axis(content, tags, AXIS_AUDIENCE, reg))
    if not matches:
        default = axis_registry_default_for(reg, AXIS_AUDIENCE)
        if default is not None:
            matches.append(default.name)
        else:
            matches.append("developer")
    # Deduplicate preserving order.
    seen: set[str] = set()
    return tuple(x for x in matches if not (x in seen or seen.add(x)))


def pick_lifecycle(kind: str) -> str:
    """Pick the default lifecycle for a new page of the given kind.

    source: ADR-0305"""
    reg = get_registry()
    for v in axis_registry_values(reg, AXIS_LIFECYCLE):
        if v.default and (
            (kind == "adr" and "adr" in v.applies_to_kinds)
            or (kind != "adr" and not v.applies_to_kinds)
        ):
            return v.name
    # source: ADR-0305

    return "proposed" if kind == "adr" else "seedling"
