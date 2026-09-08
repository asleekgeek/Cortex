"""Build redirect stubs for renamed wiki pages.

source: ADR-0307
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Final

from mcp_server.core.wiki_identity import is_valid_page_id


MAX_REDIRECT_DEPTH: Final[int] = 5


@dataclass(frozen=True)
class Redirect:
    """A parsed redirect declaration from a stub page's frontmatter.

    source: ADR-0307"""

    target_path: str = ""
    target_id: str | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.target_path and not self.target_id:
            raise ValueError(
                "Redirect requires at least one of target_path or target_id"
            )
        if self.target_id is not None and not is_valid_page_id(self.target_id):
            raise ValueError(f"invalid redirect_id: {self.target_id!r}; expected UUID4")


def redirect_is_id_based(redirect: "Redirect") -> bool:
    """True if the redirect points at a stable ID (preferred form).

    source: ADR-0307"""
    return redirect.target_id is not None


def parse_redirect(frontmatter: dict[str, object]) -> Redirect | None:
    """Extract a ``Redirect`` from frontmatter, or None if the page is not a stub.

    Recognises ``redirect_to`` (path) and ``redirect_id`` (UUID). Either
    one is sufficient. Other frontmatter fields are ignored. Returns
    None when neither field is present or both are empty.
    """
    raw_path = frontmatter.get("redirect_to", "")
    raw_id = frontmatter.get("redirect_id", "")
    target_path = str(raw_path).strip() if isinstance(raw_path, str) else ""
    target_id_str = str(raw_id).strip() if isinstance(raw_id, str) else ""

    if not target_path and not target_id_str:
        return None

    target_id = target_id_str if target_id_str else None
    if target_id is not None and not is_valid_page_id(target_id):
        # Malformed ID — treat as path-only redirect if a path is present,
        # else as no redirect (corrupt stub).
        target_id = None
        if not target_path:
            return None

    reason_raw = frontmatter.get("redirect_reason", "")
    reason = str(reason_raw).strip() if isinstance(reason_raw, str) else ""

    return Redirect(target_path=target_path, target_id=target_id, reason=reason)


def is_redirect(frontmatter: dict[str, object]) -> bool:
    """True iff this frontmatter declares a redirect."""
    return parse_redirect(frontmatter) is not None


# ── Chain resolution ───────────────────────────────────────────────────


@dataclass(frozen=True)
class ResolvedTarget:
    """Outcome of following a redirect chain to its end.

    Fields:
        final_path: wiki-relative path of the terminal (non-redirect) page.
        hops: number of redirect pages traversed (0 = the input was not a
            redirect).
        chain: ordered list of paths visited (first = input, last = final).
    """

    final_path: str
    hops: int
    chain: tuple[str, ...]


# A frontmatter reader callable: given a wiki-relative path, return its
# parsed frontmatter dict (empty dict if file missing or malformed).
FrontmatterReader = Callable[[str], dict[str, object]]


def resolve_chain(
    start_path: str,
    reader: FrontmatterReader,
    *,
    max_depth: int = MAX_REDIRECT_DEPTH,
) -> ResolvedTarget | None:
    """Walk redirect frontmatter until we reach a non-redirect page.

    Returns:
        ResolvedTarget when the chain terminates at a real page within
        ``max_depth`` hops, or None on cycle / depth exhaustion / missing
        target. The chain itself is always recorded so callers can
        report which paths were visited.

    Note: this resolver is path-based. ID-based redirects require an
    index from ID → path that this module does not maintain (the caller
    can pass an ID-aware reader if needed).
    """
    chain: list[str] = [start_path]
    seen: set[str] = {start_path}
    current = start_path

    for _ in range(max_depth):
        fm = reader(current)
        redirect = parse_redirect(fm)
        if redirect is None:
            return ResolvedTarget(
                final_path=current, hops=len(chain) - 1, chain=tuple(chain)
            )
        next_path = redirect.target_path
        if not next_path:
            # ID-only redirect — caller must resolve IDs externally.
            return None
        if next_path in seen:
            # Cycle. Don't loop forever.
            return None
        chain.append(next_path)
        seen.add(next_path)
        current = next_path

    # source: ADR-0307
    return None


# ── Stub authoring ─────────────────────────────────────────────────────


def build_redirect_stub(
    *,
    target_path: str = "",
    target_id: str | None = None,
    target_title: str = "",
    reason: str = "",
    created_at: str = "",
) -> str:
    """Render the markdown for a redirect stub.

    source: ADR-0307

    Args:
        target_path: Wiki-relative new-home path.
        target_id: Stable new-home page ID, preferred when known.
        target_title: Human-readable link title.
        reason: Optional explanatory text.
        created_at: ISO-8601 UTC timestamp; blank if omitted.
    source: ADR-0307

    Returns the complete markdown content. The caller is responsible
    for writing it to disk.
    """
    if not target_path and not target_id:
        raise ValueError("build_redirect_stub requires target_path or target_id")

    lines: list[str] = ["---"]
    if target_path:
        lines.append(f"redirect_to: {target_path}")
    if target_id is not None:
        if not is_valid_page_id(target_id):
            raise ValueError(f"invalid target_id: {target_id!r}")
        lines.append(f"redirect_id: {target_id}")
    if reason:
        lines.append(f"redirect_reason: {reason}")
    if created_at:
        lines.append(f"created: {created_at}")
    lines.append("---")
    lines.append("")
    lines.append("# Moved")
    lines.append("")
    if target_path:
        link_text = target_title or target_path
        lines.append(f"This page has moved to [{link_text}]({target_path}).")
    elif target_id is not None:
        link_text = target_title or f"page id:{target_id}"
        lines.append(f"This page has moved to **{link_text}**.")
    lines.append("")
    return "\n".join(lines)


# ── Frontmatter parser shim ────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<fm>.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, object]:
    """Lightweight YAML-ish frontmatter parser shared with the pilot.

    source: ADR-0307"""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}

    fm: dict[str, object] = {}
    current_list_key: str | None = None
    current_list: list[str] = []

    def _close_list() -> None:
        nonlocal current_list_key, current_list
        if current_list_key is not None:
            fm[current_list_key] = current_list
            current_list_key = None
            current_list = []

    for raw in m.group("fm").splitlines():
        stripped = raw.strip()
        if not stripped:
            _close_list()
            continue
        if (
            current_list_key is not None
            and raw.startswith(" ")
            and stripped.startswith("- ")
        ):
            current_list.append(stripped[2:].strip().strip("'\""))
            continue
        _close_list()
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            current_list_key = key
            current_list = []
            continue
        if value.startswith("[") and value.endswith("]"):
            fm[key] = [
                t.strip().strip("'\"") for t in value[1:-1].split(",") if t.strip()
            ]
            continue
        fm[key] = value.strip("'\"")

    _close_list()
    return fm
