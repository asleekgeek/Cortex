"""Realistic capture_origin mixture for benchmark corpora.

This module assigns each benchmark memory a capture_origin drawn from the
distribution that ACTUALLY occurs in production Cortex usage, so the gated
arm mixes trusted and untrusted content the way a live store does and can
therefore discriminate W.

source: ADR-0069"""

from __future__ import annotations

import numpy as np

# source: ADR-0069
CAPTURE_ORIGIN_MIX: tuple[tuple[str, float], ...] = (
    ("local_action", 0.966),
    ("network", 0.025),
    ("deliberate", 0.009),
)

_ORIGINS = tuple(o for o, _ in CAPTURE_ORIGIN_MIX)
_WEIGHTS = tuple(w for _, w in CAPTURE_ORIGIN_MIX)
# source: ADR-0069
_SUM_TOLERANCE = 1e-9
assert abs(sum(_WEIGHTS) - 1.0) < _SUM_TOLERANCE, "CAPTURE_ORIGIN_MIX must sum to 1.0"

# source: ADR-0069
DEFAULT_SEED = 368


def assign_capture_origins(n: int, seed: int = DEFAULT_SEED) -> list[str]:
    """Return `n` capture_origin values drawn i.i.d. from CAPTURE_ORIGIN_MIX.

    Pre: n >= 0.
    Post: len(result) == n; each element is one of _ORIGINS; deterministic
    for a given (n, seed): same call, same output, every process.
    """
    rng = np.random.default_rng(seed)
    if n == 0:
        return []
    idx = rng.choice(len(_ORIGINS), size=n, p=_WEIGHTS)
    return [_ORIGINS[i] for i in idx]
