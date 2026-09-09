"""Phase 5: admission control for MCP tool handlers.

Per-tool semaphore that bounds concurrency so one client cannot
exhaust the pool or the thread executor by hammering a single tool.

Usage (server registration wraps each handler):

    from mcp_server.handlers.admission import admit

    async def wrapped_handler(args):
        async with admit("recall"):
            return await original_handler(args)

source: ADR-0329"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp_server.handlers.latency_class import DEFAULT_SEMAPHORE, classify

# source: ADR-0329
_OVERRIDES: dict[str, int] = {
    # Higher budget: these tools are read-only / very cheap, safe to
    # run many in parallel.
    "recall": 8,
    "memory_stats": 8,
    "detect_domain": 8,
    "list_domains": 8,
    "query_methodology": 8,
    # Lower budget: mutations need slightly more care.
    "remember": 4,
}

# Process-local semaphore cache. asyncio.Semaphore is not thread-safe,
# but since admission runs on the main asyncio event loop there's only
# ever one of these per process.
_SEMS: dict[str, asyncio.Semaphore] = {}


def _budget_for(tool_name: str) -> int:
    if tool_name in _OVERRIDES:
        return _OVERRIDES[tool_name]
    cls = classify(tool_name)
    return DEFAULT_SEMAPHORE[cls]


def _get_semaphore(tool_name: str) -> asyncio.Semaphore:
    """Lazy-init per-tool semaphore on first use."""
    sem = _SEMS.get(tool_name)
    if sem is None:
        sem = asyncio.Semaphore(_budget_for(tool_name))
        _SEMS[tool_name] = sem
    return sem


@asynccontextmanager
async def admit(tool_name: str) -> AsyncIterator[None]:
    """Acquire the per-tool admission semaphore for the call duration.

    Blocks when the tool's concurrent-call budget is exhausted. No
    timeout — the admission semaphore is the backpressure signal; the
    pool handles DB-level timeout separately.

    Usage:
        async with admit("recall"):
            result = await do_work()
    """
    sem = _get_semaphore(tool_name)
    async with sem:
        yield


def current_budget(tool_name: str) -> int:
    """Return the declared budget for a tool. For tests + observability."""
    return _budget_for(tool_name)


def reset_semaphores() -> None:
    """Drop all cached semaphores. For tests only — next admit() call
    re-initializes from the current budget table."""
    _SEMS.clear()
