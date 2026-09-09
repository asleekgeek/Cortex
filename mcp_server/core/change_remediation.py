"""Remediation policy for memories impacted by a code change.

source: ADR-0122
"""

from __future__ import annotations

from enum import Enum


class Remediation(str, Enum):
    REINGEST = "reingest"
    FLAG_STALE = "flag_stale"


def is_code_derived(memory: dict) -> bool:
    """True when the memory was produced by codebase ingestion.

    Primary marker: ``agent_context == 'codebase'`` (the scope predicate the
    codebase-analyze read/write paths already use). A codebase content-hash tag
    (``codebase_analyze``'s incremental HASH_TAG) is accepted as a fallback for
    rows written before the context was consistently stamped.
    """
    if str(memory.get("agent_context", "")).strip().lower() == "codebase":
        return True
    tags = {str(t).lower() for t in (memory.get("tags") or [])}
    return "codebase" in tags or any(t.startswith("hash:") for t in tags)


def classify_remediation(memory: dict) -> Remediation:
    """REINGEST a code-derived memory; FLAG_STALE a hand-authored one."""
    return Remediation.REINGEST if is_code_derived(memory) else Remediation.FLAG_STALE
