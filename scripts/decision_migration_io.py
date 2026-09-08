"""Apply a reviewed decision extraction and restore its files on failure."""

from __future__ import annotations

from pathlib import Path

from mcp_server.infrastructure.project_wiki import contained_file, register_project_page
from mcp_server.infrastructure.wiki_decision_index import write_decision_index
from mcp_server.infrastructure.wiki_decision_mirror import check_mirror, generate_mirror


def _restore(root: Path, before: dict[Path, bytes | None]) -> list[str]:
    """Restore authored bytes, then refresh filesystem-local directory evidence."""
    errors = []
    for path, content in before.items():
        try:
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    index = root / "wiki" / ".generated" / "decision-index.json"
    if before.get(index) is not None:
        try:
            # Removing the attempted page changes directory ctime/mtime. The
            # old map is restored, but its local freshness proof must be rebuilt.
            write_decision_index(root / "wiki")
        except (OSError, ValueError) as exc:
            errors.append(f"decision index refresh: {exc}")
    return errors


def persist_extraction(
    root: Path, relative: str, updated: bytes, page_relative: str, page_content: str
) -> None:
    """Only a clean mirror may be extended; rollback only the operation's paths."""
    errors = check_mirror(root)
    if errors:
        raise ValueError(
            "repair the existing mirror before migration: " + "; ".join(errors)
        )
    page = contained_file(root, page_relative)
    mirror = "docs/adr/ADR-" + page.name
    relatives = [
        relative,
        page_relative,
        mirror,
        "wiki/manifest.json",
        "wiki/.generated/decision-index.json",
        "wiki/.generated/decision-index-state.json",
    ]
    paths = [contained_file(root, name) for name in relatives]
    before = {path: path.read_bytes() if path.exists() else None for path in paths}
    if before[page] is not None:
        raise ValueError("canonical page already exists")
    try:
        page.parent.mkdir(parents=True, exist_ok=True)
        with page.open("x", encoding="utf-8", newline="") as output:
            output.write(page_content)
        register_project_page(root, page.relative_to(root / "wiki").as_posix())
        write_decision_index(root / "wiki")
        generate_mirror(root)
        contained_file(root, relative).write_bytes(updated)
    except Exception as original:
        errors = _restore(root, before)
        if errors:
            raise original from RuntimeError(
                "Migration rollback incomplete: " + "; ".join(errors)
            )
        raise
