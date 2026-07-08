"""Curation-backlog count for ``run_wiki_maintenance``.

Split out of ``wiki_maintenance.py`` to keep both files under the
300-line cap (coding-standards.md §4.1) — no logic changed from what
previously lived inline in that module's "Curation backlog" block.

Composition root — wires ``core.auto_curator`` / ``core.wiki_coverage`` /
``core.wiki_drift`` (pure logic) to the memory store's decay-chunk
iterator and the filesystem wiki root.
"""

from __future__ import annotations

from typing import Any


async def run_backlog_pass(store: Any) -> dict[str, Any]:
    """Count pending coverage/cluster/drift jobs across the whole wiki.

    Pre-condition:  ``store`` exposes ``iter_memories_for_decay`` (or,
                    failing that, ``get_all_memories_for_decay``).
    Post-condition: returned dict carries ``cluster_jobs``,
                    ``coverage_gaps``, ``uncovered_files``,
                    ``file_coverage_by_domain``, ``drifted_pages``, and
                    ``pending_total`` (the sum of the first four count
                    fields) — read-only, no rows written.
    """
    from mcp_server.core.auto_curator import count_pending_clusters_streamed
    from mcp_server.core.wiki_coverage import (
        _project_source_root,
        audit_all_domains,
        audit_all_file_coverage,
    )
    from mcp_server.core.wiki_drift import audit_wiki_drift
    from mcp_server.infrastructure.config import WIKI_ROOT

    out: dict[str, Any] = {}
    chunks = (
        store.iter_memories_for_decay()
        if hasattr(store, "iter_memories_for_decay")
        else [store.get_all_memories_for_decay()]
    )
    out["cluster_jobs"] = count_pending_clusters_streamed(
        chunks, wiki_root=str(WIKI_ROOT)
    )

    coverages = audit_all_domains(str(WIKI_ROOT))
    out["coverage_gaps"] = sum(c.missing_count for c in coverages)

    # File-level coverage: count files that aren't referenced anywhere
    # in the wiki. Aggregated across every domain that has a resolvable
    # source root. This is "nothing left uncovered" measured at the
    # file granularity.
    file_rolls = audit_all_file_coverage(str(WIKI_ROOT))
    out["uncovered_files"] = sum(
        r.source_file_count - r.covered_file_count for r in file_rolls
    )
    out["file_coverage_by_domain"] = [
        {
            "domain": r.domain,
            "covered": r.covered_file_count,
            "total": r.source_file_count,
            "ratio": round(r.coverage_ratio, 3),
        }
        for r in file_rolls
    ]

    # Drift: existing pages out of sync with the code or off-template.
    # Capped at 1000 entries — a wide-open drift backlog doesn't need
    # to materialise in full here; the curate_wiki call can
    # re-enumerate when it needs the actual job set.
    drifts = audit_wiki_drift(str(WIKI_ROOT), _project_source_root, limit=1000)
    out["drifted_pages"] = len(drifts)

    out["pending_total"] = (
        out["cluster_jobs"]
        + out["coverage_gaps"]
        + out["uncovered_files"]
        + out["drifted_pages"]
    )
    return out
