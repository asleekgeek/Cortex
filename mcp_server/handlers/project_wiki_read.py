"""Read project pages without publishing branch citations. # source: ADR-0056"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_server.core.wiki_redirect import (
    parse_frontmatter,
    parse_redirect,
    resolve_chain,
)
from mcp_server.infrastructure.project_wiki import contained_file, resolve_wiki_root


def read(args: dict[str, Any]) -> dict[str, Any]:
    root = resolve_wiki_root(args["project_root"], Path("."))
    relative = str(args["path"])

    def content_at(path: str) -> str | None:
        target = contained_file(root, path)
        return target.read_text(encoding="utf-8") if target.is_file() else None

    def frontmatter_at(path: str) -> dict[str, object]:
        content = content_at(path)
        return parse_frontmatter(content) if content is not None else {}

    content = content_at(relative)
    if content is None:
        return {"error": f"page not found: {relative}"}
    chain: list[str] = []
    if args.get("follow_redirects", True) and parse_redirect(
        parse_frontmatter(content)
    ):
        resolved = resolve_chain(relative, frontmatter_at)
        if resolved is None:
            return {"error": f"redirect chain from {relative} could not be resolved"}
        relative = resolved.final_path
        chain = list(resolved.chain)
        content = content_at(relative)
        if content is None:
            return {"error": f"redirect target missing: {relative}"}
    return {
        "path": relative,
        "content": content,
        "root": str(root),
        "redirect_chain": chain,
        "memory_sync": "project-files-only",
    }
