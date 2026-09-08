"""Fear extinction / inhibitory learning (E2) — reversible suppression of a
learned association, not its erasure.

source: ADR-0179"""

from __future__ import annotations

from dataclasses import dataclass
from mcp_server.core.ablation import Mechanism, is_mechanism_disabled

# source: ADR-0179

# source: ADR-0179


EXTINCTION_TRIAL_GAIN = 0.35

# Inhibition ceiling. A fully-extinguished association is suppressed but the tag
# is capped at 1.0 (effective strength floored at 0).
MAX_EXTINCTION = 1.0

# source: ADR-0179


RECOVERY_HALF_LIFE_HOURS = 72.0

# source: ADR-0179

RECOVERY_FLOOR = 0.02

# source: ADR-0179


REINSTATE_RESIDUAL = 0.0


def apply_extinction(
    current_extinction: float,
    trials: int = 1,
    *,
    gain: float = EXTINCTION_TRIAL_GAIN,
) -> float:
    """Grow the inhibitory tag by ``trials`` unreinforced extinction trials.

    source: ADR-0179

    Preconditions: ``0 <= current_extinction <= 1``; ``trials >= 0``.
    Postconditions: returns a value in [current_extinction, MAX_EXTINCTION].
    ``trials == 0`` returns ``current_extinction`` unchanged.
    """
    e = max(0.0, min(MAX_EXTINCTION, current_extinction))
    g = max(0.0, min(1.0, gain))
    for _ in range(max(0, trials)):
        e = e + g * (MAX_EXTINCTION - e)
    return min(MAX_EXTINCTION, e)


def spontaneous_recovery(
    current_extinction: float,
    hours_elapsed: float,
    *,
    half_life_hours: float = RECOVERY_HALF_LIFE_HOURS,
) -> float:
    """Decay the inhibitory tag over elapsed time — the association returns.

    source: ADR-0179

    Preconditions: ``0 <= current_extinction <= 1``; ``hours_elapsed >= 0``;
    ``half_life_hours > 0``.
    Postconditions: returns a value in [0, current_extinction];
    ``hours_elapsed == 0`` returns ``current_extinction`` unchanged.
    """
    e = max(0.0, min(MAX_EXTINCTION, current_extinction))
    if e <= 0.0 or hours_elapsed <= 0.0 or half_life_hours <= 0.0:
        return e
    decayed = e * (2.0 ** (-hours_elapsed / half_life_hours))
    return 0.0 if decayed < RECOVERY_FLOOR else decayed


def reinstate(
    current_extinction: float, *, residual: float = REINSTATE_RESIDUAL
) -> float:
    """Collapse the inhibitory tag in one step — original association restored.

    source: ADR-0179

    Preconditions: ``0 <= current_extinction <= 1``; ``0 <= residual <= 1``.
    Postconditions: returns ``min(current_extinction, residual)`` clamped to
    [0, 1] — never increases the tag.
    """
    e = max(0.0, min(MAX_EXTINCTION, current_extinction))
    r = max(0.0, min(MAX_EXTINCTION, residual))
    return min(e, r)


def effective_strength(base_strength: float, extinction_strength: float) -> float:
    """Effective (inhibited) retrieval strength = base * (1 - extinction).

    The masking read: the inhibitory tag suppresses how strongly the memory is
    retrieved WITHOUT changing ``base_strength`` on the row. ``extinction = 0``
    returns ``base_strength`` unchanged (no behaviour change — the default);
    ``extinction = 1`` drives the effective strength to 0 while the base value
    is preserved for later recovery / reinstatement.

    Preconditions: ``base_strength >= 0``; ``0 <= extinction_strength <= 1``.
    Postconditions: returns a value in [0, base_strength].
    """
    b = max(0.0, base_strength)
    e = max(0.0, min(MAX_EXTINCTION, extinction_strength))
    return b * (1.0 - e)


def is_extinguished(extinction_strength: float, *, threshold: float = 0.5) -> bool:
    """True iff the inhibitory tag is strong enough to count as suppressed.

    A reporting/gating convenience (used by the deprecate-and-count surfacing):
    a memory is "extinguished" (deprecated-but-retained) once its tag reaches
    ``threshold``. Below it the residual inhibition is treated as negligible.
    """
    return max(0.0, min(MAX_EXTINCTION, extinction_strength)) >= threshold


@dataclass
class ExtinctionOutcome:
    """Result of an extinction operation the caller persists to the store.

    Fields:
      new_extinction_strength: the updated tag to write to the memory's
        ``extinction_strength`` column (in [0, 1]).
      effective_strength: the base strength after applying the new tag, for the
        caller's convenience / diagnostics (base is NOT written).
      operation: which route produced this — "extinguish" / "recover" /
        "reinstate" / "noop".
    """

    new_extinction_strength: float
    effective_strength: float
    operation: str = "noop"


def deprecate(
    base_strength: float,
    current_extinction: float,
    *,
    trials: int = 1,
) -> ExtinctionOutcome:
    """Deprecate an association: strengthen inhibition, leave base intact.

    source: ADR-0179

    Preconditions: ``base_strength >= 0``; ``0 <= current_extinction <= 1``;
    ``trials >= 1`` for a real deprecation.
    Postconditions: returns an ExtinctionOutcome; when ablated,
    ``new_extinction_strength == current_extinction`` and ``operation ==
    "noop"``.
    """

    if is_mechanism_disabled(Mechanism.EXTINCTION):
        return ExtinctionOutcome(
            new_extinction_strength=max(0.0, min(MAX_EXTINCTION, current_extinction)),
            effective_strength=effective_strength(base_strength, current_extinction),
            operation="noop",
        )
    new_tag = apply_extinction(current_extinction, trials)
    return ExtinctionOutcome(
        new_extinction_strength=new_tag,
        effective_strength=effective_strength(base_strength, new_tag),
        operation="extinguish",
    )
