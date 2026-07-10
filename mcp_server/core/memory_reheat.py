"""One-shot heat recalibration for deliberate memories below the measured
retrieval cliff (I6-D5, INC6.6 campaign).

The I6 audit (``scratchpad/inc6-audit-outils-memoire.md``, "Effet heat
pur" point 4) measured, on families of byte-identical content competing
only on ``effective_heat``, that the top-10-on-exact-match cliff sits at
``effective_heat`` in ``[0.20, 0.25]``: a family at eh~=0.43 ranked 1-3,
eh~=0.24 ranked 1-4, eh~=0.19 ranked 22/57/23. Deliberate memories (source
NOT IN the auto-capture/mechanical set) are the only category that
populates the WRRF heat/recency pools (F2 de-bias, ``pg_schema.py``
``recall_memories()``) — heat is their sole fusion advantage, and their
measured median ``effective_heat`` (0.199) sits BELOW that cliff while
auto-captures sit at 0.458 (design doc I6-D5, "Fait source").

This module computes, for one row, the minimal ``heat_base`` that brings
its *current* ``effective_heat`` to at least the target (0.25, the
cliff's measured upper bound) without ever lowering an existing value —
"one-shot recalibration", not a policy change to the decay curve itself
(explicitly rejected alternative in I6-D5: "changement structurel
immédiat de la thermodynamique... exige une source qui n'existe pas
encore, c'est exactement le genre de constante qu'on n'invente pas §8").

Derivation (not an invented formula — verified against the real
``effective_heat()`` PL/pgSQL function, not reimplemented): for a given
row, ``effective_heat(heat_base, ...)`` equals ``heat_base * factor *
decay_multiplier`` clamped to ``[stage_floor, 1.0]`` (the protected branch
is ``heat_base * factor`` directly — same linear-then-clamp shape). Both
the multiplicative term and the clamp bounds are independent of
``heat_base`` itself (``pg_schema.py::effective_heat``, verified by
reading the function body — see ``docs/campaigns/`` artifact for the
exact line citation). The caller therefore probes the row's own real
``effective_heat`` twice — once at its current ``heat_base``
(``effective_heat_before``) and once with ``heat_base`` temporarily
overridden to 1.0 (``effective_heat_at_max``, computed by the actual
PostgreSQL function on a ``jsonb_populate_record``-cloned row, see
``infrastructure/pg_store_memory_reheat.py``) — this module only does the
algebra on those two already-correct, DB-computed outputs: ``needed =
target / effective_heat_at_max``. The ratio cancels the shared
multiplicative term exactly, so this is exact (not an approximation)
whenever the target is reachable within the row's own ``[0, 1]`` range.

Pure logic, no I/O — mirrors ``core/memory_dedup_exact.py``'s DI split
(coding-standards.md §2, Dependency Rule: core imports stdlib only).
"""

from __future__ import annotations

from typing import NamedTuple

# I6-D5's target: the measured cliff's upper bound, not an aesthetic
# choice ("la cible vient de la mesure, pas d'un choix esthétique",
# design doc). source: scratchpad/inc6-audit-outils-memoire.md, "Effet
# heat pur" point 4 (families eh~=0.19 -> rangs 22-57, eh~=0.24 -> rangs
# 1-4; cliff between 0.20 and 0.25).
DEFAULT_REHEAT_TARGET: float = 0.25

# Below this, effective_heat_at_max is considered numerically zero (a row
# whose own probe at heat_base=1.0 still rounds to ~0 cannot be reasoned
# about via the heat_base/target ratio without risking a division blow-up
# from float noise, not from a real reachable-vs-unreachable distinction).
_EPSILON: float = 1e-9

# Relative overshoot applied to the target ONLY when computing a row's
# raised heat_base (never to the "already above target" check, which
# stays exact) — compensates for round-trip precision loss through the
# `heat_base` column's REAL (float4) storage: the exact `target /
# effective_heat_at_max` ratio is computed in Python double precision,
# but is then (a) truncated to float4 on write, (b) re-read and (c) fed
# back through the PL/pgSQL `effective_heat()` function's own float4
# input/output boundary. Without this margin, the campaign's first apply
# run left the majority of "reheated" rows landing ~2.7e-5 relative UNDER
# the target (still failing `effective_heat < 0.25`, defeating the
# campaign's own re-run idempotence check).
# source: measured on 2026-07-10 in dev DB during the INC6.6 apply run
# (docs/campaigns/i6d5_memory_reheat_apply_20260710T151041Z.json showed
# 540/544 previously-"reheated" rows still below target on immediate
# re-scan); 1e-4 is ~4x that measured deficit, chosen as a round,
# comfortable margin rather than the exact measured value.
_FLOAT32_ROUNDTRIP_MARGIN: float = 1e-4


class ReheatDecision(NamedTuple):
    """Outcome of recalibrating one row's ``heat_base``.

    ``new_heat_base`` is the value to write (``heat_base_before`` when
    ``changed`` is False — the caller writes nothing in that case).
    ``reachable`` is False when even ``heat_base=1.0`` (the maximum legal
    value) could not bring ``effective_heat`` to the target for this row
    — the row's consolidation-stage decay math caps it below the target
    regardless of ``heat_base`` (a genuine structural ceiling, not a
    solvable-by-more-heat case). Unreachable rows are left untouched
    (raising ``heat_base`` for them would have zero effect on
    ``effective_heat`` while falsely implying "recently very hot" —
    §8 zetetic discipline: don't write a value that produces no verified
    functional effect).
    """

    new_heat_base: float
    changed: bool
    reachable: bool


def compute_reheat_target(
    heat_base_before: float,
    effective_heat_before: float,
    effective_heat_at_max: float,
    target: float = DEFAULT_REHEAT_TARGET,
) -> ReheatDecision:
    """Decide the new ``heat_base`` for one deliberate memory, never lowering.

    Pre-condition:  ``heat_base_before`` in ``[0, 1]`` (the column's legal
                    range); ``effective_heat_before`` and
                    ``effective_heat_at_max`` are the row's own
                    ``effective_heat()`` outputs computed by the caller
                    against the real DB function — at the row's current
                    ``heat_base`` and with ``heat_base`` overridden to
                    1.0, respectively (same homeostatic ``factor`` and
                    ``t_now`` used for both probes, so they are directly
                    comparable). ``effective_heat_at_max >=
                    effective_heat_before`` (``effective_heat`` is
                    monotonically non-decreasing in ``heat_base`` — a
                    caller-side invariant this function does not
                    re-verify, matching ``elect_survivor``'s contract
                    style of trusting caller-supplied, DB-derived inputs).
    Post-condition: if ``effective_heat_before >= target``, returns
                    ``(heat_base_before, changed=False, reachable=True)``
                    — never touches a row already at or above the cliff
                    (I6-D5: "ne jamais BAISSER une heat" generalizes to
                    "never touch what doesn't need it"). If
                    ``effective_heat_at_max < target``, the row cannot
                    reach the target via ``heat_base`` alone (its
                    consolidation-stage floor/decay caps ``effective_heat``
                    below the target even at maximum ``heat_base``) —
                    returns ``(heat_base_before, changed=False,
                    reachable=False)``. Otherwise returns
                    ``(new_heat_base, changed=True, reachable=True)``
                    where ``new_heat_base = min(1.0, max(heat_base_before,
                    (target * (1 + _FLOAT32_ROUNDTRIP_MARGIN)) /
                    effective_heat_at_max))`` — the ``heat_base`` that
                    makes this row's recomputed ``effective_heat`` reach
                    ``target`` WITH a small overshoot margin so the value
                    survives the round-trip through the ``heat_base``
                    column's REAL (float4) storage and back through
                    ``effective_heat()``'s own float4 boundary without
                    landing fractionally under ``target`` (empirically
                    required — see ``_FLOAT32_ROUNDTRIP_MARGIN``'s
                    module-level comment; clamped never below the
                    original value and never above the column's legal
                    ceiling of 1.0).
    """
    if effective_heat_before >= target:
        return ReheatDecision(heat_base_before, False, True)

    if effective_heat_at_max < target - _EPSILON:
        return ReheatDecision(heat_base_before, False, False)

    needed = (target * (1.0 + _FLOAT32_ROUNDTRIP_MARGIN)) / effective_heat_at_max
    new_heat_base = min(1.0, max(heat_base_before, needed))
    return ReheatDecision(new_heat_base, new_heat_base > heat_base_before, True)


__all__ = ["DEFAULT_REHEAT_TARGET", "ReheatDecision", "compute_reheat_target"]
