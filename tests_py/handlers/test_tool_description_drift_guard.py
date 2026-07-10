"""Anti-recidive guard: tool descriptions must not promise what the code
does not do (I6-D8, INC6 "mémoire solide" campaign).

Each entry below pins a locution that was found (2026-07-10 audit,
``scratchpad/inc6-audit-outils-memoire.md``) to be FALSE relative to the
handler's actual behavior, and was removed/corrected in increment 6.1.
If a future edit reintroduces the same false promise, this test fails —
that is the point.

Scope note (behavior-preserving, I6-D8): this guard covers only the
handlers whose descriptions were corrected in 6.1 — validate_memory,
backfill_memories, detect_gaps, assess_coverage, navigate_memory — plus
recall, recall_hierarchical, drill_down (corrected in the follow-up
honesty batch, same pattern as navigate_memory: READ_ONLY was false
because ``track_replay_event`` mutates ``access_count``/``replay_count``/
``hippocampal_dependency`` on every call).
``consolidation/memify.py`` / ``handlers/consolidate.py`` still promise
"extract reusable lessons and rules" that the code does not implement
(``consolidate.py:93-95`` vs ``memify.py:36-74``) — that drift is a
DELIBERATE exclusion from this increment (a parallel increment is making
the promise true rather than lowering the doc to match the code, per
explicit user decision) and is intentionally NOT guarded here. Do not
add memify/consolidate to BANNED_PHRASES without re-checking that
decision is still in force.
"""

from __future__ import annotations

import importlib

import pytest

# (module path, banned substring, why it's banned)
BANNED_PHRASES: list[tuple[str, str, str]] = [
    (
        "mcp_server.handlers.detect_gaps",
        "low-heat",
        "detect_gaps computes 4 real axes (isolated entities, sparse "
        "domains, temporal drift, cognitive blind spots) — it has never "
        "computed low-heat topic clusters (audit detect_gaps.py:8).",
    ),
    (
        "mcp_server.handlers.assess_coverage",
        "file coverage",
        "assess_coverage scores the memory store, not the codebase's "
        "files — there is no per-file coverage axis (audit "
        "assess_coverage.py:5).",
    ),
    (
        "mcp_server.handlers.backfill_memories",
        "re-runs only process new sessions",
        "the old blanket-idempotence claim ignored that "
        "force_reprocess=true + remember(force=True) bypasses the write "
        "gate and can create duplicate rows (audit backfill_memories.py:"
        "35 vs :44-46).",
    ),
]

# (module path, required substring, why it must be present)
REQUIRED_PHRASES: list[tuple[str, str, str]] = [
    (
        "mcp_server.handlers.backfill_memories",
        "NOT idempotent overall",
        "the NON_IDEMPOTENT_WRITE annotation must be backed by an "
        "explicit, unqualified-free statement in the description, not "
        "just the annotation dict.",
    ),
    (
        "mcp_server.handlers.navigate_memory",
        "Not read-only",
        "navigate_memory writes replay-tracking state on every call "
        "(track_replay_event) — the description must say so, matching "
        "the NON_IDEMPOTENT_WRITE annotation.",
    ),
    (
        "mcp_server.handlers.validate_memory",
        "FILE PATHS ONLY",
        "validate_memory checks file-path existence only — URLs, "
        "commits, and papers are not verified; the description must not "
        "let a reader assume broader provenance checking.",
    ),
    (
        "mcp_server.handlers.recall",
        "Not read-only",
        "recall writes replay-tracking state on every returned memory "
        "(_track_recall_replay -> track_replay_event) — the description "
        "must say so, matching the NON_IDEMPOTENT_WRITE annotation "
        "(honesty batch, same pattern as navigate_memory a8d52838).",
    ),
    (
        "mcp_server.handlers.recall_hierarchical",
        "Not read-only",
        "recall_hierarchical writes replay-tracking state on every "
        "surfaced memory (track_replay_event) — the description must say "
        "so, matching the NON_IDEMPOTENT_WRITE annotation.",
    ),
    (
        "mcp_server.handlers.drill_down",
        "Not read-only",
        "drill_down writes replay-tracking state on every surfaced "
        "memory (track_replay_event) — the description must say so, "
        "matching the NON_IDEMPOTENT_WRITE annotation.",
    ),
]


def _full_text(module_path: str) -> str:
    """Concatenate a handler's module docstring + schema description."""
    mod = importlib.import_module(module_path)
    doc = mod.__doc__ or ""
    desc = mod.schema.get("description", "")
    return f"{doc}\n{desc}"


@pytest.mark.parametrize(
    "module_path,banned,reason",
    BANNED_PHRASES,
    ids=[f"{m}::{p!r}" for m, p, _ in BANNED_PHRASES],
)
def test_banned_phrase_absent(module_path: str, banned: str, reason: str) -> None:
    text = _full_text(module_path).lower()
    assert banned.lower() not in text, (
        f"{module_path} reintroduced the false promise {banned!r}: {reason}"
    )


@pytest.mark.parametrize(
    "module_path,required,reason",
    REQUIRED_PHRASES,
    ids=[f"{m}::{p!r}" for m, p, _ in REQUIRED_PHRASES],
)
def test_required_phrase_present(module_path: str, required: str, reason: str) -> None:
    text = _full_text(module_path)
    assert required in text, (
        f"{module_path} lost the honest qualifier {required!r}: {reason}"
    )


def test_backfill_memories_annotation_is_non_idempotent_write() -> None:
    """The annotation dict, not just prose, must reflect force_reprocess
    duplication risk — flags checked directly, not by re-deriving the
    NON_IDEMPOTENT_WRITE preset (avoids a tautological identity check)."""
    mod = importlib.import_module("mcp_server.handlers.backfill_memories")
    ann = mod.schema["annotations"]
    assert ann["readOnlyHint"] is False
    assert ann["idempotentHint"] is False


def test_navigate_memory_annotation_is_non_idempotent_write() -> None:
    mod = importlib.import_module("mcp_server.handlers.navigate_memory")
    ann = mod.schema["annotations"]
    assert ann["readOnlyHint"] is False
    assert ann["idempotentHint"] is False


@pytest.mark.parametrize(
    "module_path",
    [
        "mcp_server.handlers.recall",
        "mcp_server.handlers.recall_hierarchical",
        "mcp_server.handlers.drill_down",
    ],
)
def test_replay_tracking_handler_annotation_is_non_idempotent_write(
    module_path: str,
) -> None:
    """Same drift as navigate_memory (a8d52838): every handler that calls
    ``track_replay_event`` on its results is not read-only — repeat calls
    mutate access_count/replay_count/hippocampal_dependency. Flags checked
    directly, not by re-deriving the NON_IDEMPOTENT_WRITE preset."""
    mod = importlib.import_module(module_path)
    ann = mod.schema["annotations"]
    assert ann["readOnlyHint"] is False
    assert ann["idempotentHint"] is False
