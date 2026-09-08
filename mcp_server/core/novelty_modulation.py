"""Captured novelty gain, retaining unrounded arithmetic across gate phases.

The existing habituation and goal passes both apply clamp(score * gain).
Keeping the raw gain separate from rounded diagnostic dictionaries lets a
pre-embedding bound and the later exact score use the same observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NoveltyModulation:
    gain: float | None = None
    details: dict[str, Any] | None = None


def apply_modulation(
    score: float, observed: NoveltyModulation
) -> tuple[float, dict | None]:
    """Apply the original multiply/clamp order; absent mechanisms are identity."""
    if observed.gain is None:
        return score, None
    # source: write_gate.apply_goal_maintenance and habituate_novelty at a284e473.
    modulated = max(0.0, min(1.0, score * observed.gain))
    return modulated, {
        **(observed.details or {}),
        "modulated_novelty": round(modulated, 4),
    }
