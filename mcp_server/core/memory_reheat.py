"""Recalibrate deliberate-memory heat without lowering existing values.

source: ADR-0201
"""

from __future__ import annotations

from typing import NamedTuple

# source: ADR-0201


DEFAULT_REHEAT_TARGET: float = 0.25

# Below this, effective_heat_at_max is considered numerically zero (a row
# whose own probe at heat_base=1.0 still rounds to ~0 cannot be reasoned
# about via the heat_base/target ratio without risking a division blow-up
# from float noise, not from a real reachable-vs-unreachable distinction).
_EPSILON: float = 1e-9

# source: ADR-0201

# source: ADR-0201
_FLOAT32_ROUNDTRIP_MARGIN: float = 1e-4


class ReheatDecision(NamedTuple):
    """Outcome of recalibrating one row's ``heat_base``.

    source: ADR-0201"""

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

    source: ADR-0201
    """
    if effective_heat_before >= target:
        return ReheatDecision(heat_base_before, False, True)

    if effective_heat_at_max < target - _EPSILON:
        return ReheatDecision(heat_base_before, False, False)

    needed = (target * (1.0 + _FLOAT32_ROUNDTRIP_MARGIN)) / effective_heat_at_max
    new_heat_base = min(1.0, max(heat_base_before, needed))
    return ReheatDecision(new_heat_base, new_heat_base > heat_base_before, True)


__all__ = ["DEFAULT_REHEAT_TARGET", "ReheatDecision", "compute_reheat_target"]
