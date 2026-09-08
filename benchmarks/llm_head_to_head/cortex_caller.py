"""Condition C — Cortex-assembled context.

source: ADR-0837

precondition: the production memory store has been seeded with the BEAM
  conversation's memories under ``domain="beam"`` (the orchestrator does
  this via the production ``remember`` handler, not a benchmark shortcut).
postcondition: returns the same memory dicts the production handler would
  return for an interactive call with the same query — same ranking, same
  enrichments (PL/pgSQL WRRF + FlashRank + prospective + co-activation +
  rules + strategic ordering + replay tracking).
invariant: this module's import of ``handler`` is the SOLE link between
  the benchmark and the production stack. Removing this import and
  re-running condition C must produce a clean ImportError, not a silent
  fallback path.
"""

from __future__ import annotations

import asyncio
from typing import Any

# THE LOAD-BEARING IMPORT. Do not change without filing a protocol addendum.
from mcp_server.handlers.recall import handler  # noqa: E402


# source: ADR-0837

CORTEX_MAX_RESULTS = 20


def cortex_recall(question: str, domain: str = "beam") -> list[dict[str, Any]]:
    """Call the production recall handler — exactly as production does.

    pre: ``question`` is non-empty; ``domain`` matches what the orchestrator
      seeded via the production remember handler.
    post: returns a list of memory dicts (possibly empty) — whatever the
      production handler returned. We do NOT post-process, re-rank, or
      filter; the handler IS the production behaviour.
    """
    if not question or not question.strip():
        return []

    # source: ADR-0837

    args = {
        "query": question,
        "domain": domain,
        "max_results": CORTEX_MAX_RESULTS,
    }
    response = asyncio.run(handler(args))

    # The production handler returns {"memories": [...], "count": N, ...}
    # per ``recall.py::_handler_impl``. We pull the ``memories`` list and
    # return it verbatim.
    if isinstance(response, dict):
        results = response.get("memories", [])
        if isinstance(results, list):
            return results
    return []


def passages_to_context(memories: list[dict[str, Any]], separator: str = "\n\n") -> str:
    """Concatenate Cortex-returned memories into the answer prompt.

    pre: memories is already ranked best-first by the production handler
      (FlashRank + strategic ordering already applied).
    post: returns a string; empty when memories is empty. The format
      preserves the production ranking — caller does NOT shuffle.
    """
    return separator.join(m.get("content", "") for m in memories if m.get("content"))
