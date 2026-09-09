"""Value learning — reinforcement-learning value + credit assignment (B2).

source: ADR-0290"""

from __future__ import annotations

from dataclasses import dataclass

# source: ADR-0290


VALUE_ALPHA: float = 0.1

# source: ADR-0290


TRACE_LAMBDA: float = 0.8

# source: ADR-0290

VALUE_MIN: float = 0.0
VALUE_MAX: float = 1.0

# Neutral / prior value for a memory that has never received a reward signal.
# 0.5 = "unknown, assume average" — the same neutral the DA-RPE uses.
VALUE_PRIOR: float = 0.5


# source: ADR-0290


def outcome_to_reward(
    outcome_positive: bool,
    outcome_negative: bool,
    memory_importance: float,
) -> float:
    """Map a session outcome to a scalar reward in [0, 1].

    Mirrors ``compute_dopamine_rpe``'s reward mapping exactly:
      positive -> 0.7 + 0.3·importance
      negative -> 0.2 - 0.1·importance
      neutral  -> 0.5
    """
    if outcome_positive:
        return 0.7 + memory_importance * 0.3
    if outcome_negative:
        return 0.2 - memory_importance * 0.1
    return 0.5


# ── Data model ──────────────────────────────────────────────────────────────
@dataclass
class ValueUpdate:
    """A computed value change for one memory, ready to persist.

    ``memory_id``      — the memory whose value is being updated.
    ``old_value``      — value before the update (VALUE_PRIOR if never seen).
    ``new_value``      — value after the TD update, clamped to [0, 1].
    ``delta``          — the reward-prediction error δ = reward - V (signed).
    ``eligibility``    — the trace weight this memory received (top hit = 1.0).
    ``effective_alpha``— alpha·eligibility, the actual step size applied.

    source: ADR-0290"""

    memory_id: int
    old_value: float
    new_value: float
    delta: float
    eligibility: float
    effective_alpha: float


def value_update_as_dict(update: ValueUpdate) -> dict:
    return {
        "memory_id": update.memory_id,
        "old_value": round(update.old_value, 4),
        "new_value": round(update.new_value, 4),
        "delta": round(update.delta, 4),
        "eligibility": round(update.eligibility, 4),
        "effective_alpha": round(update.effective_alpha, 4),
    }


# source: ADR-0290
def td_update(
    current_value: float,
    reward: float,
    *,
    alpha: float = VALUE_ALPHA,
    eligibility: float = 1.0,
) -> tuple[float, float]:
    """One temporal-difference value update for a single memory.

    source: ADR-0290"""
    delta = reward - current_value
    step = alpha * eligibility
    new_value = current_value + step * delta
    new_value = max(VALUE_MIN, min(VALUE_MAX, new_value))
    return new_value, delta


# ── Credit assignment with eligibility traces ───────────────────────────────
def assign_credit(
    recalled: list[dict],
    outcome_positive: bool,
    outcome_negative: bool,
    *,
    alpha: float = VALUE_ALPHA,
    trace_lambda: float = TRACE_LAMBDA,
) -> list[ValueUpdate]:
    """Distribute credit for a session outcome across the memories it used.

    ``recalled`` is the ordered recall set that produced the session's result —
    most-relevant first — where each entry is a dict with at least:
      - ``id`` / ``memory_id``: the memory id
      - ``value`` (optional): its current learned value (VALUE_PRIOR if absent)
      - ``importance`` (optional): used by the reward mapping (default 0.5)

    source: ADR-0290"""
    updates: list[ValueUpdate] = []
    for rank, mem in enumerate(recalled):
        mem_id = mem.get("memory_id", mem.get("id"))
        if mem_id is None:
            continue
        current = _current_value(mem)
        importance = _clamp01(mem.get("importance", 0.5), default=0.5)
        reward = outcome_to_reward(outcome_positive, outcome_negative, importance)
        eligibility = trace_lambda**rank
        new_value, delta = td_update(
            current, reward, alpha=alpha, eligibility=eligibility
        )
        updates.append(
            ValueUpdate(
                memory_id=mem_id,
                old_value=current,
                new_value=new_value,
                delta=delta,
                eligibility=eligibility,
                effective_alpha=alpha * eligibility,
            )
        )
    return updates


# ── Value as a retention / retrieval priority signal ────────────────────────
def retention_bonus(value: float, *, max_bonus: float = 0.5) -> float:
    """Map a learned value to a multiplicative retention bonus in [1, 1+max].

    A high-value memory (proven to contribute to good outcomes) should resist
    decay. Returns a factor >= 1.0 that a decay/heat computation can multiply in:
    value 0.5 (neutral) -> 1.0 (no effect); value 1.0 -> 1+max_bonus; value 0 ->
    still 1.0 (low value never *accelerates* forgetting here — that is the
    decay/interference machinery's job, not the value layer's).
    """
    v = _clamp01(value, default=VALUE_PRIOR)
    return 1.0 + max_bonus * max(0.0, (v - VALUE_PRIOR) / (VALUE_MAX - VALUE_PRIOR))


def retrieval_priority(
    base_score: float, value: float, *, weight: float = 0.15
) -> float:
    """Blend a learned value into a retrieval relevance score.

    source: ADR-0290"""
    v = _clamp01(value, default=VALUE_PRIOR)
    return base_score * (1.0 + weight * (v - VALUE_PRIOR))


# ── Helpers ─────────────────────────────────────────────────────────────────
def _current_value(mem: dict) -> float:
    raw = mem.get("value")
    if raw is None:
        return VALUE_PRIOR
    return _clamp01(raw, default=VALUE_PRIOR)


def _clamp01(x, *, default: float) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, v))
