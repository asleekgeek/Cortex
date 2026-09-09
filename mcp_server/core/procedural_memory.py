"""Procedural memory — skills learned as recurring successful action sequences.

source: ADR-0226"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
import math

# ── Tuning constants ────────────────────────────────────────────────────────
# Minimum number of distinct sessions a subsequence must appear in to count as
# a recurring skill (frequent-subsequence support). Below this it is treated as
# incidental, not a habit.
MIN_SKILL_SUPPORT: int = 3

# Chunk length bounds. A skill is a contiguous action subsequence of length in
# [MIN, MAX]. Single actions are not skills; very long chains are rarely
# reproducible verbatim.
MIN_SKILL_LEN: int = 2
MAX_SKILL_LEN: int = 6

# Repetitions of successful execution after which a goal-directed skill is
# considered *habitual* (Graybiel: habits form with repetition). Purely a
# label / retrieval-priority threshold; it does not gate execution.
HABITUAL_THRESHOLD: int = 5

# source: ADR-0226


PROFICIENCY_ALPHA: float = 0.2

# source: ADR-0226

_PRIOR_SUCCESS: float = 1.0
_PRIOR_TOTAL: float = 2.0

# source: ADR-0226

# source: ADR-0226
_SUCCESS_REWARD: float = 0.5

# source: ADR-0226

# source: ADR-0226
_CONTEXT_MATCH_THRESHOLD: float = 0.5


# ── Data model ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ActionStep:
    """One normalized action in a procedure.

    source: ADR-0226"""

    tool: str
    target_kind: str | None = None


def action_step_key(step: "ActionStep") -> str:
    """Stable identity key for one action step.

    source: ADR-0226"""
    return step.tool if step.target_kind is None else f"{step.tool}:{step.target_kind}"


@dataclass
class ProceduralSkill:
    """A learned procedure: a recurring action sequence with a success record.

    source: ADR-0226"""

    sequence: tuple[ActionStep, ...]
    context_signature: str = ""
    occurrences: int = 0  # times this sequence has been observed
    success_count: int = 0  # observations whose session outcome was good
    failure_count: int = 0
    proficiency: float = 0.0  # reinforced running success rate in [0, 1]
    last_seen: str = ""  # ISO timestamp of most recent observation
    skill_id: str = ""

    def __post_init__(self) -> None:
        if not self.skill_id:
            self.skill_id = skill_id_for(self.sequence)


def procedural_skill_is_habitual(skill: "ProceduralSkill") -> bool:
    """A skill is habitual once it has enough *successful* repetitions.

    source: ADR-0226"""
    return skill.success_count >= HABITUAL_THRESHOLD


def procedural_skill_length(skill: "ProceduralSkill") -> int:
    return len(skill.sequence)


def procedural_skill_as_dict(skill: "ProceduralSkill") -> dict:
    return {
        "skill_id": skill.skill_id,
        "sequence": [action_step_key(s) for s in skill.sequence],
        "context_signature": skill.context_signature,
        "occurrences": skill.occurrences,
        "success_count": skill.success_count,
        "failure_count": skill.failure_count,
        "proficiency": round(skill.proficiency, 4),
        "is_habitual": procedural_skill_is_habitual(skill),
        "last_seen": skill.last_seen,
    }


def skill_id_for(sequence: tuple[ActionStep, ...]) -> str:
    """Stable content hash of an action sequence (12 hex chars)."""
    joined = ">".join(action_step_key(s) for s in sequence)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]


# ── Action normalization ────────────────────────────────────────────────────
# Coarse target-kind inference from a tool-call target string. Keeps skills
# general ("edit a test") without exploding on specific paths.
_TARGET_KIND_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"test|spec|_test\.|\.test\.", re.IGNORECASE), "test"),
    (
        re.compile(r"\.(ya?ml|toml|ini|cfg|conf|json)$|config|settings", re.IGNORECASE),
        "config",
    ),
    (re.compile(r"readme|\.md$|docs?/", re.IGNORECASE), "doc"),
    (re.compile(r"\.sql$|schema|migration", re.IGNORECASE), "schema"),
    (re.compile(r"\.(py|js|ts|go|rs|java|rb|c|cpp|h)$", re.IGNORECASE), "code"),
]


def infer_target_kind(target: str | None) -> str | None:
    """Map a concrete target (path/arg) to a coarse object class, or None."""
    if not target:
        return None
    for pattern, kind in _TARGET_KIND_PATTERNS:
        if pattern.search(target):
            return kind
    return None


def normalize_actions(
    tool_calls: list[dict] | list[str],
) -> list[ActionStep]:
    """Turn a session's raw tool usage into a normalized action sequence.

    Accepts either the rich form (list of ``{"tool": str, "target": str}``
    dicts — as available from tool-call logs) or the lightweight form (list of
    tool-name strings, as ``auto_task_record`` already collects in
    ``tools_used``). Consecutive identical actions are collapsed to a single
    step (a run of three ``read_file`` calls is one "read" action in the
    procedure), matching how habits chunk repeated sub-actions.
    """
    steps: list[ActionStep] = []
    for call in tool_calls:
        if isinstance(call, str):
            step = ActionStep(tool=call, target_kind=None)
        else:
            step = ActionStep(
                tool=call.get("tool", "") or "",
                target_kind=infer_target_kind(call.get("target")),
            )
        if not step.tool:
            continue
        if steps and action_step_key(steps[-1]) == action_step_key(step):
            continue  # collapse consecutive duplicates
        steps.append(step)
    return steps


# ── Chunking / frequent-subsequence mining (Graybiel) ───────────────────────
def _contiguous_subsequences(
    seq: list[ActionStep], min_len: int, max_len: int
) -> list[tuple[ActionStep, ...]]:
    """All contiguous windows of length in [min_len, max_len]."""
    out: list[tuple[ActionStep, ...]] = []
    n = len(seq)
    for length in range(min_len, min(max_len, n) + 1):
        for start in range(0, n - length + 1):
            out.append(tuple(seq[start : start + length]))
    return out


def mine_skills(
    sessions: list[dict],
    *,
    min_support: int = MIN_SKILL_SUPPORT,
    min_len: int = MIN_SKILL_LEN,
    max_len: int = MAX_SKILL_LEN,
) -> list[ProceduralSkill]:
    """Mine recurring successful action sequences into skill chunks.

    Each session dict provides:
      - ``tools_used`` / ``tool_calls``: the action evidence (either form
        accepted by ``normalize_actions``).
      - ``outcome``: ``"success"`` | ``"failure"`` (or a bool / float in [0,1]);
        the session-level reward. Missing outcome is treated as neutral and does
        not count toward success or failure.
      - ``domain`` / ``cwd`` (optional): used to build the context signature.

    A candidate sequence becomes a skill when it appears (contiguously) in at
    least ``min_support`` distinct sessions. Its ``success_count`` /
    ``failure_count`` aggregate the outcomes of the sessions it appeared in, and
    ``proficiency`` is the smoothed success rate. Skills are returned sorted by
    a combined support x proficiency priority, strongest first.
    """
    # skill_id -> aggregate accumulator
    acc: dict[str, dict] = {}

    for session in sessions:
        raw = session.get("tool_calls") or session.get("tools_used") or []
        actions = normalize_actions(raw)
        if len(actions) < min_len:
            continue
        reward = _outcome_to_reward(session.get("outcome"))
        ctx = context_signature(session)
        seen_ids: set[str] = set()
        for sub in _contiguous_subsequences(actions, min_len, max_len):
            sid = skill_id_for(sub)
            if sid in seen_ids:
                continue  # count a sequence once per session (session support)
            seen_ids.add(sid)
            slot = acc.setdefault(
                sid,
                {
                    "sequence": sub,
                    "sessions": 0,
                    "succ": 0,
                    "fail": 0,
                    "contexts": {},
                    "last_seen": "",
                },
            )
            slot["sessions"] += 1
            if reward is not None:
                if reward >= _SUCCESS_REWARD:
                    slot["succ"] += 1
                else:
                    slot["fail"] += 1
            if ctx:
                slot["contexts"][ctx] = slot["contexts"].get(ctx, 0) + 1
            ts = session.get("timestamp") or session.get("ended_at") or ""
            if ts > slot["last_seen"]:
                slot["last_seen"] = ts

    skills: list[ProceduralSkill] = []
    for sid, slot in acc.items():
        if slot["sessions"] < min_support:
            continue
        succ, fail = slot["succ"], slot["fail"]
        proficiency = (succ + _PRIOR_SUCCESS) / (succ + fail + _PRIOR_TOTAL)
        dominant_ctx = (
            max(slot["contexts"].items(), key=lambda kv: kv[1])[0]
            if slot["contexts"]
            else ""
        )
        skills.append(
            ProceduralSkill(
                sequence=slot["sequence"],
                context_signature=dominant_ctx,
                occurrences=slot["sessions"],
                success_count=succ,
                failure_count=fail,
                proficiency=proficiency,
                last_seen=slot["last_seen"],
                skill_id=sid,
            )
        )

    skills.sort(key=lambda s: _skill_priority(s), reverse=True)
    return skills


def _skill_priority(skill: ProceduralSkill) -> float:
    """Retrieval priority: reinforced proficiency x log-support x length bonus.

    source: ADR-0226"""

    support = math.log1p(skill.occurrences)
    length_bonus = 1.0 + 0.1 * (procedural_skill_length(skill) - MIN_SKILL_LEN)
    return skill.proficiency * support * length_bonus


# ── Reinforcement / proficiency update (Doya, Schultz) ──────────────────────
def _outcome_to_reward(outcome) -> float | None:
    """Normalize a session outcome to a reward in [0,1], or None if unknown."""
    if outcome is None:
        return None
    if isinstance(outcome, bool):
        return 1.0 if outcome else 0.0
    if isinstance(outcome, (int, float)):
        return max(0.0, min(1.0, float(outcome)))
    if isinstance(outcome, str):
        o = outcome.strip().lower()
        if o in {"success", "ok", "pass", "passed", "good"}:
            return 1.0
        if o in {"failure", "fail", "failed", "error", "bad"}:
            return 0.0
    return None


def reinforce(skill: ProceduralSkill, outcome) -> ProceduralSkill:
    """Apply one execution outcome to a skill (the RPE-style update).

    source: ADR-0226"""
    reward = _outcome_to_reward(outcome)
    occurrences = skill.occurrences + 1
    success_count = skill.success_count
    failure_count = skill.failure_count
    proficiency = skill.proficiency
    if reward is not None:
        # source: ADR-0226

        if skill.occurrences == 0 and proficiency == 0.0:
            proficiency = _PRIOR_SUCCESS / _PRIOR_TOTAL
        proficiency = proficiency + PROFICIENCY_ALPHA * (reward - proficiency)
        proficiency = max(0.0, min(1.0, proficiency))
        if reward >= _SUCCESS_REWARD:
            success_count += 1
        else:
            failure_count += 1
    return ProceduralSkill(
        sequence=skill.sequence,
        context_signature=skill.context_signature,
        occurrences=occurrences,
        success_count=success_count,
        failure_count=failure_count,
        proficiency=proficiency,
        last_seen=datetime.now(timezone.utc).isoformat(),
        skill_id=skill.skill_id,
    )


# ── Context signature + situational retrieval ───────────────────────────────
def context_signature(session: dict) -> str:
    """Compact signature of the situation a procedure was used in.

    Built from domain + the leaf directory of cwd. This is the retrieval key
    for procedural memory — procedures are recalled by *situation*, not by
    content similarity.
    """
    domain = (session.get("domain") or "").strip().lower()
    cwd = (session.get("cwd") or "").strip()
    leaf = ""
    if cwd:
        leaf = re.split(r"[\\/]", cwd.rstrip("/\\"))[-1].lower()
    parts = [p for p in (domain, leaf) if p]
    return "|".join(parts)


def match_skills(
    current_context: dict,
    skills: list[ProceduralSkill],
    *,
    top_k: int = 5,
    min_proficiency: float = 0.5,
) -> list[dict]:
    """Retrieve applicable procedures for the current situation.

    source: ADR-0226"""
    target = context_signature(current_context)
    target_tokens = set(target.split("|")) if target else set()
    recent = normalize_actions(
        current_context.get("tool_calls") or current_context.get("tools_used") or []
    )
    recent_keys = {action_step_key(s) for s in recent}

    scored: list[dict] = []
    for skill in skills:
        if skill.proficiency < min_proficiency:
            continue
        skill_tokens = (
            set(skill.context_signature.split("|"))
            if skill.context_signature
            else set()
        )
        # source: ADR-0226

        if skill_tokens and target_tokens:
            inter = len(skill_tokens & target_tokens)
            union = len(skill_tokens | target_tokens)
            ctx_score = inter / union if union else 0.0
        else:
            ctx_score = 0.3
        # Small bonus if the procedure's opening action matches what the agent
        # just did (the habit is "primed" by the current action).
        prime = 0.0
        if (
            recent_keys
            and skill.sequence
            and action_step_key(skill.sequence[0]) in recent_keys
        ):
            prime = 0.15
        score = (ctx_score + prime) * _skill_priority(skill)
        if score <= 0.0:
            continue
        why = _explain_match(skill, ctx_score, prime)
        scored.append(
            {
                "skill": procedural_skill_as_dict(skill),
                "score": round(score, 4),
                "why": why,
            }
        )

    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:top_k]


def _explain_match(skill: ProceduralSkill, ctx_score: float, prime: float) -> str:
    bits = [
        f"{procedural_skill_length(skill)}-step routine",
        f"{skill.proficiency:.0%} success over {skill.occurrences} uses",
    ]
    if procedural_skill_is_habitual(skill):
        bits.append("habitual")
    if ctx_score >= _CONTEXT_MATCH_THRESHOLD:
        bits.append(f"matches context '{skill.context_signature}'")
    if prime:
        bits.append("primed by current action")
    return "; ".join(bits)
