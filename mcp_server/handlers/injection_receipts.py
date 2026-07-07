"""Injection-receipt emission for context-injecting channels.

Blame path T1 (decision Cortex 4255039): every channel that injects
memory content into a context emits an append-only receipt at injection
time — the presence-in-context evidence the blame path resolves against.
T1 wires the recall channel only; the hook channels (session_start,
agent_briefing) follow in T2.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def emit_injection_receipt(
    store: Any,
    memories: list[dict[str, Any]],
    *,
    channel: str = "recall",
    session_id: str | None = None,
) -> int | None:
    """Persist a receipt mirroring the bound payload; return receipt_id.

    Must be called AFTER bound_payload (transcript↔DB parity invariant,
    decision 4255039): entries dropped by the response budget were never
    injected; truncated entries keep their id and ARE in context.
    ``rank`` = index in the injected payload (0 = top result), persisted
    verbatim — blame ordering replays recorded facts only.

    Returns None — without failing the recall read path — when nothing
    was injected or when the receipt write fails (I/O is the only named
    degradation mode).

    Internal contract, trusted here: every bound-payload entry carries an
    int-coercible ``memory_id`` — pg_recall projects it on every candidate
    (typed injection gated by ``if mid:``), inject_triggered_memories
    builds items from a just-fetched ``mid``, and bound_payload preserves
    ids on truncation. A missing id is an upstream programming bug and
    MUST raise here, loudly: swallowing it would silently drop receipts
    in production and hide the regression.
    """
    if not memories:
        return None
    items = [
        {
            "memory_id": int(m["memory_id"]),
            "rank": rank,
            "score": None if m.get("score") is None else float(m["score"]),
        }
        for rank, m in enumerate(memories)
    ]
    try:
        return store.insert_injection_receipt(
            channel=channel, items=items, session_id=session_id
        )
    except Exception:
        logger.warning("injection receipt emission failed", exc_info=True)
        return None
