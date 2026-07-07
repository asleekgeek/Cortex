"""try_curation head-check — never merge into a superseded version.

P0 load-bearing bug from the read-path supersession audit
(docs/program/pr2-read-path-supersession-audit.json): search_vectors(top_k=3)
can return a superseded row; the merge branch would then bury the new content
in a version the read path excludes. The head-check skips any candidate whose
superseded_by_id is set — no signal is lost because the chain head, near-
identical in embedding, stays in the candidate set.

Stub store/engine: try_curation only consumes store.search_vectors,
store.get_memory, emb_engine.similarity and the pure curation module, so the
head-check is testable without a live backend.
"""

from __future__ import annotations

from mcp_server.handlers.remember_helpers import try_curation


class _StubEngine:
    def similarity(self, a, b) -> float:  # noqa: ARG002 — stub contract
        return 0.99  # high enough for the merge branch

    def encode(self, text: str):  # pragma: no cover — only hit on merge
        return b"\x00" * 4


class _StubStore:
    """Two near-identical candidates: id=1 superseded by id=2 (the head)."""

    def __init__(self) -> None:
        self.merged_into: list[int] = []
        self._rows = {
            1: {
                "id": 1,
                "content": "deploy target is server alpha",
                "embedding": b"\x01",
                "superseded_by_id": 2,
                "compression_level": 0,
                "heat": 0.5,
            },
            2: {
                "id": 2,
                "content": "deploy target is server alpha",
                "embedding": b"\x01",
                "superseded_by_id": None,
                "compression_level": 0,
                "heat": 0.5,
            },
        }

    def search_vectors(self, embedding, top_k=3, min_heat=0.0):  # noqa: ARG002
        # Superseded row ranked FIRST — the buggy path merged into it.
        return [(1, 0.01), (2, 0.02)]

    def get_memory(self, mid):
        return self._rows.get(mid)

    def update_memory_compression(self, mid, *args, **kwargs):  # noqa: ARG002
        self.merged_into.append(mid)

    def update_memory_heat(self, mid, heat):  # noqa: ARG002
        pass


def test_try_curation_never_merges_into_superseded():
    store = _StubStore()
    action, target = try_curation(
        content="deploy target is server alpha",
        embedding=b"\x01",
        force=False,
        store=store,
        emb_engine=_StubEngine(),
        tags=[],
        heat=0.5,
    )
    assert target != 1, "curation must never target the superseded version"
    assert 1 not in store.merged_into, "merge must never write into a dead row"
    # The chain head remains a legitimate target (merge or supersede,
    # depending on the contradiction heuristic — both act on the head).
    if target is not None:
        assert target == 2
