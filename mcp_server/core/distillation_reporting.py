"""Distillation reporting — authoring prompts + memify_derive usage stats.

source: ADR-0160"""

from __future__ import annotations

from typing import Any

from mcp_server.core.distillation import DistillDossier


def build_distill_prompt(
    dossier: DistillDossier, memory_previews: list[dict[str, Any]]
) -> str:
    """Structured authoring prompt for the in-session LLM (M-D8 point 2).

    Precondition: memory_previews contains id, content, and tags for
    exactly dossier.memory_ids, with caller-truncated content.
    Postcondition: text names the required remember call with deliberate
    write_class, lesson and derived-src:<id> tags, and the dossier marker.
    source: ADR-0160"""
    lines = [
        f"Distillation dossier ({dossier.kind}) — "
        f"topic: {dossier.topic or '(untitled)'}",
        "",
        "Sources (read these, then write the WHY, not the WHAT):",
    ]
    for mem in memory_previews:
        preview = (mem.get("content") or "")[:200].replace("\n", " ")
        lines.append(f"  - id={mem['id']} tags={mem.get('tags') or []}: {preview}")
    src_tags = " ".join(f"'derived-src:{mid}'" for mid in dossier.memory_ids)
    lines += [
        "",
        "Write ONE distilled lesson via `remember` if — and only if — these",
        "sources actually justify a durable, situated lesson (a root cause, a",
        "rule, a decision and its rationale). If they don't, skip this dossier.",
        "",
        "Required call shape:",
        "  remember(",
        "    content=<the lesson — WHY it happened / WHY the decision, not a",
        "             restatement of the source events>,",
        f"    tags=['lesson', '{dossier.marker}', {src_tags}],",
        "    write_class='deliberate',",
        "    source='distillation',",
        "  )",
        "",
        "The tag list MUST include this dossier's marker "
        f"('{dossier.marker}') so a future run does not re-offer the same "
        "dossier (idempotence), and one 'derived-src:<id>' per source "
        "memory above (provenance) — both conventions are read back by "
        "`curate_distill` and by the M-D6 lesson-promotion / M-D7 "
        "wiki-citation passes.",
    ]
    return "\n".join(lines)


def summarize_derived_usage(derived_memories: list[dict[str, Any]]) -> dict[str, Any]:
    """Day-0 usage baseline for ``memify_derive``'s machine-synthesized
    facts (M-D8 point 3: "conditionner son maintien à la mesure d'usage à
    30 jours").

    Precondition: ``derived_memories`` contains every active row carrying
    the ``derived`` tag, excluding LLM-authored ``distilled`` lessons.
    Postcondition: returns aggregate useful/access counts and raw count;
    computes one snapshot without persistence or a keep/retire verdict.
    source: ADR-0160"""
    n = len(derived_memories)
    if n == 0:
        return {
            "count": 0,
            "total_access_count": 0,
            "total_useful_count": 0,
            "mean_useful_ratio": None,
        }
    total_access = sum(int(m.get("access_count") or 0) for m in derived_memories)
    total_useful = sum(int(m.get("useful_count") or 0) for m in derived_memories)
    return {
        "count": n,
        "total_access_count": total_access,
        "total_useful_count": total_useful,
        "mean_useful_ratio": (total_useful / total_access) if total_access else 0.0,
    }
