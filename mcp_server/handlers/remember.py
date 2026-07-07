"""Handler: remember — store a memory through the flat 4-signal predictive coding gate.

Composition root: wires core modules + infrastructure storage + embeddings.
"""

from __future__ import annotations

from typing import Any

from mcp_server.core import thermodynamics, write_gate
from mcp_server.handlers._telemetry_wrap import instrument
from mcp_server.core.domain_detector import detect_domain
from mcp_server.core.global_detector import detect_global
from mcp_server.handlers._tool_meta import IDEMPOTENT_WRITE
from mcp_server.handlers.remember_helpers import (
    apply_modulations,
    evaluate_gate,
    insert_and_post_process,
    try_block_replica_upsert,
    try_curation,
    update_user_mood_ema,
    validate_supersede_target,
)
from mcp_server.handlers.remember_response import build_merge_response
from mcp_server.infrastructure import wiki_store
from mcp_server.infrastructure.config import WIKI_ROOT
from mcp_server.infrastructure.embedding_engine import get_embedding_engine
from mcp_server.infrastructure.memory_config import (
    get_memory_settings,
    root_agent_topic,
)
from mcp_server.infrastructure.memory_store import MemoryStore, get_shared_store
from mcp_server.infrastructure.profile_store import load_profiles

schema = {
    "title": "Remember (store a memory)",
    "annotations": IDEMPOTENT_WRITE,
    "outputSchema": {
        "type": "object",
        "required": ["stored", "action"],
        "properties": {
            "stored": {
                "type": "boolean",
                "description": "True if content landed in the memory store (as new row or a merge into an existing one).",
            },
            "memory_id": {
                "type": "integer",
                "description": "ID of the resulting memory row (PG bigint). Present when stored=true.",
            },
            "action": {
                "type": "string",
                "enum": [
                    "stored",
                    "merged",
                    "rejected",
                    "superseded",
                    "superseded_conflict",
                ],
                "description": "stored=new row; merged=folded into the most-similar existing memory; rejected=redundant per the predictive-coding gate; superseded=new row replaces an older version (append-only edge posted); superseded_conflict=another writer superseded the target first — nothing was kept, rebase and retry.",
            },
            "reason": {
                "type": "string",
                "description": "Human-readable explanation of the gate decision (e.g. 'low surprise', 'high entity overlap').",
            },
            "merged_with": {
                "type": "integer",
                "description": "ID of the existing memory (PG bigint) when action=merged.",
            },
            "superseded_id": {
                "type": "integer",
                "description": "ID of the replaced memory when action=superseded.",
            },
            "supersede_target_id": {
                "type": "integer",
                "description": "Requested supersession target when the supersede path rejected or conflicted.",
            },
            "current_superseded_by_id": {
                "type": ["integer", "null"],
                "description": "The version that currently supersedes the target (present on supersede rejection/conflict so the caller can rebase).",
            },
            "heat": {
                "type": "number",
                "description": "Final heat assigned to the new/merged memory.",
            },
        },
    },
    "description": (
        "Store a memory through the flat 4-signal predictive-coding write "
        "gate (embedding, entity, temporal, and structural novelty — "
        "Friston-inspired prediction-error gating). Novel surprising "
        "content passes; "
        "redundant content is rejected or merged with the most-similar "
        "existing memory via active curation. After write: thermodynamic "
        "tagging, knowledge-graph entity extraction, neuromodulation "
        "(DA/NE/ACh/5-HT), engram allocation. Use this after any "
        "non-trivial discovery, fix, decision, or lesson — if it would "
        "surprise a future session, store it. Distinct from `anchor` "
        "(pins an EXISTING memory, doesn't create), `wiki_write` "
        "(creates an .md page, not a memory row), and `add_rule` "
        "(recall-time filter, not stored content). Mutates memories + "
        "entities + relationships tables. Latency ~50-100ms. Returns "
        "{stored, memory_id, action: stored|merged|rejected, reason}."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["content"],
        "properties": {
            "content": {
                "type": "string",
                "description": (
                    "The memory content to store. Plain prose works; markdown "
                    "is preserved. Aim for a single fact, decision, or lesson "
                    "with enough context to be intelligible standalone."
                ),
                "examples": [
                    "Recall regression on 2026-03-12 traced to FlashRank ONNX cache; clearing fixed it.",
                    "Decided to use pgvector HNSW (m=16, ef_construction=64) for ANN — 3x faster than IVFFlat.",
                ],
            },
            "tags": {
                "type": "array",
                "description": (
                    "Free-form tags for filtering and rules. Convention: use "
                    "lowercase, hyphenated, and include at least one category "
                    "(e.g., 'bug-fix', 'decision', 'lesson')."
                ),
                "items": {"type": "string"},
                "default": [],
                "examples": [["bug-fix", "recall"], ["decision", "embeddings"]],
            },
            "directory": {
                "type": "string",
                "description": (
                    "Absolute project directory the memory belongs to. Defaults "
                    "to the current working directory; resolved against git-root "
                    "for stable domain mapping."
                ),
                "examples": ["/Users/alice/code/cortex"],
            },
            "domain": {
                "type": "string",
                "description": (
                    "Cognitive-domain override. Auto-detected from directory if "
                    "omitted; only set this when crossing project boundaries."
                ),
                "examples": ["cortex", "ai-architect"],
            },
            "source": {
                "type": "string",
                "description": "Origin tag for provenance and replay scoring.",
                "enum": ["session", "tool", "user", "consolidation", "import"],
                "default": "user",
                "examples": ["session", "tool"],
            },
            "force": {
                "type": "boolean",
                "description": (
                    "Bypass the predictive-coding write gate and always insert. "
                    "Use sparingly — anchored facts and curated lessons only. "
                    "Combined with supersedes_id this is the sovereign human "
                    "correction: the gate is bypassed but the supersession "
                    "edge is still posted."
                ),
                "default": False,
            },
            "supersedes_id": {
                "type": "integer",
                "minimum": 1,
                "description": (
                    "ID of the memory this content replaces (append-only "
                    "correction). A new row is inserted, the target's "
                    "superseded_by_id is compare-and-set to it, and recall "
                    "demotes the old version. Rejected when the target is "
                    "missing or already superseded — an existing version "
                    "chain is never forked silently. Bypasses automatic "
                    "curation (the intent is explicit); the write gate "
                    "still applies unless force=true."
                ),
                "examples": [4255039],
            },
            "agent_topic": {
                "type": "string",
                "description": (
                    "Subagent context tag for topic isolation; recall can scope "
                    "to a single agent persona."
                ),
                "examples": ["engineer", "researcher", "reviewer"],
            },
            "is_global": {
                "type": "boolean",
                "description": (
                    "If true, the memory is visible across all projects/domains. "
                    "Use for genuinely global facts (e.g., user identity, "
                    "operating principles)."
                ),
                "default": False,
            },
            "created_at": {
                "type": "string",
                "description": (
                    "Original ISO-8601 timestamp for imported/backfilled memories. "
                    "Omit for live captures (server timestamps the row)."
                ),
                "format": "date-time",
                "examples": ["2026-04-14T10:23:00Z"],
            },
            "initial_heat": {
                "type": "number",
                "description": (
                    "Initial heat override [0.0, 1.0] used by backfill and "
                    "import paths to reflect historical memory age. Defaults "
                    "to 1.0 for live writes. Surprise boost still applies on "
                    "top. Setting this below 1.0 keeps old memories out of "
                    "the hot cohort so homeostatic scaling can rebalance "
                    "the distribution (issue #14 P1)."
                ),
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 1.0,
                "examples": [0.3, 0.65, 0.88, 1.0],
            },
        },
    },
}

_store: MemoryStore | None = None


def _get_store() -> MemoryStore:
    global _store
    if _store is None:
        s = get_memory_settings()
        _store = get_shared_store(s.DB_PATH, s.EMBEDDING_DIM)
    return _store


def _resolve_domain(directory: str, domain: str) -> str:
    from mcp_server.shared.domain_mapping import (
        resolve_cwd,
        resolve_domain as resolve_hint,
    )

    # Shannon: cwd is the minimum sufficient statistic for domain identity.
    # Try git-root resolution first (most reliable), then profile detection fallback.
    if directory:
        resolved = resolve_cwd(directory)
        if resolved:
            return resolved
    if domain:
        return resolve_hint(domain)
    if directory:
        # Fallback to profile-based detection
        profiles = load_profiles()
        detection = detect_domain({"cwd": directory}, profiles)
        detected = detection.get("domain", "") or ""
        return resolve_hint(detected) if detected else ""
    return ""


def _enrich_mod_with_gate(mod: dict, gate: dict) -> None:
    """Copy gate signals into the modulation dict for response building."""
    mod.update(
        {
            "gate_reason": gate["gate_reason"],
            "emb_nov": gate["emb_nov"],
            "ent_nov": gate["ent_nov"],
            "temp_nov": gate["temp_nov"],
            "struct_nov": gate["struct_nov"],
        }
    )


def _parse_args(
    args: dict[str, Any],
) -> tuple[str, list, str, str, bool, str, bool, str | None, float | None]:
    """Extract and default handler arguments.

    Last element `initial_heat` is the optional age-adjusted baseline used
    by backfill / import paths (issue #14 P1). None = legacy 1.0 baseline.
    Defensive clamp to [0, 1] — schema validation enforces the same bounds.
    """
    raw_initial = args.get("initial_heat")
    initial_heat: float | None = None
    if raw_initial is not None:
        try:
            initial_heat = max(0.0, min(1.0, float(raw_initial)))
        except (TypeError, ValueError):
            initial_heat = None
    return (
        args["content"],
        args.get("tags", []),
        args.get("directory", ""),
        args.get("source", "user"),
        args.get("force", False),
        args.get("agent_topic", ""),
        args.get("is_global", False),
        args.get("created_at"),
        initial_heat,
    )


async def _handler_impl(args: dict[str, Any] | None = None) -> dict[str, Any]:
    """Store a memory with thermodynamic properties and predictive coding gate."""
    if not args or not args.get("content"):
        return {"stored": False, "action": "rejected", "reason": "no_content"}

    # Phase 7: harden user-controlled content at the ingestion boundary
    # (NFC normalization, control/bidi strip, byte cap).
    from mcp_server.shared.content_hardening import harden_content

    args["content"] = harden_content(args["content"])
    if not args["content"]:
        return {"stored": False, "action": "rejected", "reason": "no_content"}

    # Connection-rooted scoping: a server launched with
    # CORTEX_ROOT_AGENT_TOPIC forces that scope on every write, so the
    # model cannot store into (or omit) another agent's scope. Mirrors
    # the recall-side force; covers all callers, not just the tool surface.
    _root = root_agent_topic()
    if _root is not None:
        args["agent_topic"] = _root

    (
        content,
        tags,
        directory,
        source,
        force,
        agent_topic,
        is_global,
        created_at,
        initial_heat,
    ) = _parse_args(args)
    store, emb_engine = _get_store(), get_embedding_engine()

    # Explicit supersession target (PRD dual-access increment 1, item ①):
    # fail fast before any embedding/gate work when the target is missing
    # or already superseded — an existing chain is never forked silently.
    supersedes_id, supersede_rejection = validate_supersede_target(
        args.get("supersedes_id"), store
    )
    if supersede_rejection is not None:
        return supersede_rejection

    domain = _resolve_domain(directory, args.get("domain", ""))
    embedding = emb_engine.encode(content)
    valence = thermodynamics.compute_valence(content)

    gate = evaluate_gate(
        content, tags, embedding, force, store, emb_engine, domain=domain
    )
    if not gate["should_store"]:
        return write_gate.build_rejection_response(
            gate["emb_nov"],
            gate["ent_nov"],
            gate["temp_nov"],
            gate["struct_nov"],
            gate["score"],
            gate["gate_reason"],
            gate["importance"],
        )

    # Baseline heat defaults to 1.0. Callers may pass an explicit initial_heat
    # to set a different baseline; age-based decay is NOT applied here — it is
    # the read-time job of effective_heat() via the heat_base_set_at anchor
    # (A3 decay clock), keeping a single canonical age-decay path. Surprise
    # boost applies on top.
    baseline_heat = initial_heat if initial_heat is not None else 1.0
    heat = thermodynamics.apply_surprise_boost(
        baseline_heat, gate["score"], get_memory_settings().SURPRISE_BOOST
    )
    mod = apply_modulations(
        content,
        tags,
        heat,
        gate["importance"],
        valence,
        domain,
        gate["ent_names"],
        gate["known"],
        store,
    )
    _enrich_mod_with_gate(mod, gate)

    # Auto-detect global when not explicitly set
    if not is_global:
        is_global, _global_score, global_reason = detect_global(content, tags)
    else:
        global_reason = "explicit"

    mid: int | None
    if supersedes_id is not None:
        # Explicit supersession: the caller's intent overrides automatic
        # curation (no merge/link second-guessing) and the block-replica
        # upsert. force=True composes with it — the gate was bypassed
        # above, yet the edge is still posted below (sovereign human
        # correction; previously force and supersede were exclusive
        # because force early-returned "create" inside try_curation).
        action, mid = "supersede", supersedes_id
    else:
        # Block-replica upsert: if the incoming memory is a system-memory block
        # snapshot (tagged 'memory-replica' + 'vpath:…'), refresh the existing row
        # in-place rather than inserting a new one (one row per block file).
        # Normal writes are completely unaffected — this branch exits early on
        # any write that isn't a replica. contract: zetetic-team-subagents memory/contract.md §8b
        upserted, upsert_id = try_block_replica_upsert(
            content, embedding, tags, source, store
        )
        if upserted and upsert_id is not None:
            return {
                "stored": True,
                "memory_id": upsert_id,
                "action": "stored",
                "reason": "block-replica-refreshed",
            }

        action, mid = try_curation(
            content, embedding, force, store, emb_engine, tags, mod["heat"]
        )
        if action == "merge":
            # Mood signal still updates on merge — the user authored the content,
            # whether we keep it as a new row or fold it into an existing one.
            update_user_mood_ema(content, source, store)
            return build_merge_response(mid, domain, mod, gate)

    result = insert_and_post_process(
        content,
        embedding,
        tags,
        source,
        domain,
        directory,
        action,
        mid,
        gate["sims"],
        gate["vec_hits"],
        gate["ent_names"],
        gate["extracted"],
        mod,
        gate["score"],
        store,
        emb_engine,
        agent_context=agent_topic,
        is_global=is_global,
        created_at=created_at,
    )
    if is_global and result.get("stored"):
        result["is_global"] = True
        result["global_reason"] = global_reason

    # MOOD_CONGRUENT_RERANK signal-feed (Bower 1981 mood-congruent recall):
    # EMA-update user_mood.valence from VADER compound on user-authored
    # content. Non-user sources are ignored to keep the signal faithful
    # to the user's affective state. See remember_helpers.update_user_mood_ema
    # for the contract and source-discipline notes.
    if result.get("stored"):
        update_user_mood_ema(content, source, store)

    # Promote decision-shaped memories to the authored wiki layer.
    #
    # Contract (E8, post-Taleb fragility audit):
    #   - On success: ``result["wiki_page"]`` is the relative path.
    #   - On classifier rejection: no field added (memory didn't qualify).
    #   - On wiki I/O failure: memory write is already committed; we log
    #     the failure to ``result["warnings"]`` so the caller can observe
    #     the partial failure rather than silently losing the signal.
    #
    # The store write has succeeded by this point; a failure here is a
    # partial-failure, not a total one. Documented in the schema.
    if result.get("stored") and result.get("memory_id") is not None:
        try:
            wiki_path = wiki_store.sync_memory_strict(
                WIKI_ROOT,
                memory_id=result["memory_id"],
                content=content,
                tags=tags,
                domain=domain,
            )
            if wiki_path:
                result["wiki_page"] = wiki_path
        except Exception as exc:
            # Partial failure — memory is stored but wiki sync failed.
            # Surfacing the exception type + message preserves the ability
            # to diagnose recurring failures (e.g., disk full, path escape).
            warnings = result.setdefault("warnings", [])
            warnings.append(
                {
                    "scope": "wiki_sync",
                    "memory_id": result["memory_id"],
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    return result


# Telemetry-instrumented public entry. Records latency, byte volume,
# and write success/fail per call (Popper C6 read/write ratio audit).
handler = instrument("remember", _handler_impl, result_count_key=None)
