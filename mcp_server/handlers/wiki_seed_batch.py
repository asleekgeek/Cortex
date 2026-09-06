"""Prepare independent wiki-seed reads; replay per-file writes/errors in order."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from mcp_server.handlers.remember_bulk import (
    file_reads_are_independent,
    prepare_bulk,
    store_prepared,
)
from mcp_server.handlers.remember_prepared import InputFailure


@dataclass
class SeedOptions:
    root: Path
    max_bytes: int
    kind: Callable
    remember: Callable


def _seed_args(path: Path, relative: str, options: SeedOptions) -> dict:
    root, max_bytes = options.root, options.max_bytes
    content = path.read_text(encoding="utf-8", errors="replace")
    if len(content) > max_bytes:
        content = content[:max_bytes] + "\n\n[...truncated]"
    return {
        "content": content,
        # ADR-2244 Phase 6.2: aliases preserve routing and imported provenance.
        "tags": [
            "seed:codebase",
            "imported",
            options.kind(relative),
            f"file:{relative}",
        ],
        "domain": root.name or "seed",
        "source": f"seed:{relative}",
        "write_class": "mechanical",
        "force": True,
    }


def _seed_inputs(files: list, options: SeedOptions):
    for path, relative in files:
        try:
            yield _seed_args(path, relative, options)
        except Exception as exc:  # noqa: BLE001 — keep this file's read/preparation error in original order
            yield InputFailure(exc)


async def import_files(files: list, options: SeedOptions) -> tuple[int, list]:
    pending = None
    if file_reads_are_independent([path for path, _ in files]):
        pending = iter(prepare_bulk(_seed_inputs(files, options)))
    imported, errors = 0, []
    for path, relative in files:
        try:
            result = (
                await store_prepared(next(pending))
                if pending is not None
                else await options.remember(_seed_args(path, relative, options))
            )
            if result.get("stored") or result.get("memory_id"):
                imported += 1
        except Exception as exc:  # noqa: BLE001 — retain per-file diagnostics/counts and continue
            errors.append(f"{relative}: {exc}")
    return imported, errors
