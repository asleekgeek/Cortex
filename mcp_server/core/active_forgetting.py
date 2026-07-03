"""Core: active_forgetting — two independent dopaminergic forgetting circuits.

The *Drosophila* dopaminergic active-forgetting literature describes TWO
anatomically and molecularly DISTINCT forgetting circuits — not two points on a
single severity axis. This module implements both as independent decisions over
a memory's offline (consolidation-time) signals; neither influences the other.

  PERMANENT circuit — Rac1/cofilin trace erosion (PPL1-γ2α'1).
    An "ongoing" dopaminergic forgetting signal gradually erodes the trace. It is
    "increased robustly with locomotor activity" and sensory input — i.e. by
    interference from newer activity — and "inhibit[ed]" by "sleep and rest"
    (Davis & Zhong 2017, Neuron 95:490-503, PMC5657245; Cervantes-Sandoval 2017,
    PMC6168074). Stronger/consolidated memories are "much more resistant … not
    immune" (Davis & Zhong 2017) — a GRADED resistance, modelled by reusing the
    cascade interference_vulnerability curve (Kandel 2001 / Bahrick 1984 / Benna &
    Fusi 2016). Faithful operationalization for an offline pass:

        pressure = chronic_interference × stage_vulnerability(stage)
        permanent ⟺ pressure ≥ Tp, and the memory is neither pinned nor sleep-
                    protected (recently replayed/accessed).

    Effect = mark is_stale (reversible soft-delete: the row persists as a residual
    engram and is reinstated when the trace is reactivated).

  TRANSIENT circuit — DAMB retrieval block (PPL1-α2α'2).
    "Triggered by interfering stimuli presented just prior to retrieval", it
    "blocks retrieval" of an otherwise intact trace, recovering spontaneously /
    with time (Sabandal, Berry & Davis 2021, Nature 591:426-430, PMC8522469). It
    acts even on consolidated PSD-LTM, so it is STAGE-INDEPENDENT. Faithful
    operationalization:

        transient ⟺ an acute interferer exists (acute_overlap ≥ X) that is recent
                    (acute_age_hours ≤ W), and the memory is neither pinned nor
                    just re-accessed.

    Effect = reduce heat (lower recall rank), reversible: recovers on re-access.

Independence is load-bearing. Sabandal (2021) found "two separate DA-based
circuits", and directly tested and REJECTED conversion of transient into
permanent ("returned to normal … by day 14"). The two functions therefore read
DISJOINT signals (chronic_interference vs acute_overlap/age) and share no state.

No salience term: the papers give "stronger resists / weaker vulnerable" only
ordinally — no rate law (Berry, Phan & Davis 2018, PMC6239218; confirmed silent
across all four papers). Salience-resistance is expressed solely through the
consolidation stage (the documented escape from default forgetting), never an
invented (1 - heat) factor. No phasic-DA reuse: the coupled_neuromodulation DA
channel is encoding-reward; conflating it would invert the effect.

All three thresholds are calibrated from the by-construction labeled benchmark
(no biological rate constant exists at the hours/days timescale); see the source
comments below. Pure business logic — no I/O.
"""

from __future__ import annotations

from mcp_server.core.cascade_stages import get_stage_properties_by_name

# Permanent-circuit pressure threshold: maximum-margin separator between the
# retain and is_stale label classes in (chronic_interference × stage_vulnerability)
# space (retain ≤ 0.1800 | stale ≥ 0.4750; margin 0.2950).
# source: benchmark benchmarks/active_forgetting/run_benchmark.py
PERMANENT_PRESSURE_THRESHOLD = 0.3275

# Transient-circuit acute-interferer thresholds: maximum-margin separators for
# the overlap (margin 0.5500) and recency (margin 22.0h) dimensions of the
# transient label class.
# source: benchmark benchmarks/active_forgetting/run_benchmark.py
ACUTE_OVERLAP_THRESHOLD = 0.575
ACUTE_RECENCY_WINDOW_HOURS = 13.0


def forgetting_pressure(stage: str, chronic_interference: float) -> float:
    """Permanent-circuit pressure = chronic_interference × stage_vulnerability(stage).

    ``chronic_interference`` (>= 0) is the ongoing aggregate overlap from newer
    memories. ``stage_vulnerability`` is the paper-grounded cascade
    interference_vulnerability (labile 0.9 → consolidated 0.05): a graded
    resistance, so consolidated memories resist strongly but are never zeroed by
    fiat. The transient circuit deliberately does NOT use this term.
    """
    vuln = get_stage_properties_by_name(stage).interference_vulnerability
    return max(0.0, chronic_interference) * vuln


def is_permanent_forgetting(
    stage: str,
    chronic_interference: float,
    is_pinned: bool,
    recently_active: bool,
) -> bool:
    """Decide the Rac1 (permanent) circuit: mark the memory is_stale?

    ``is_pinned`` is user protection or an anchor (heat == 1.0); ``recently_active``
    means replayed/accessed this cycle (sleep quiets the ongoing forgetting signal).
    Either exempts the memory. Otherwise it is forgotten when the chronic-
    interference pressure overcomes its stage resistance.
    """
    if is_pinned or recently_active:
        return False
    return forgetting_pressure(stage, chronic_interference) >= PERMANENT_PRESSURE_THRESHOLD


def is_transient_forgetting(
    acute_overlap: float,
    acute_age_hours: float,
    is_pinned: bool,
    recently_active: bool,
) -> bool:
    """Decide the DAMB (transient) circuit: transiently suppress retrieval?

    Stage-independent (Sabandal 2021): fires whenever an acute interferer is both
    strong enough (``acute_overlap`` ≥ threshold) and recent enough
    (``acute_age_hours`` ≤ window). ``is_pinned`` exempts; ``recently_active`` means
    the memory was just retrieved successfully, so it is not currently blocked.
    """
    if is_pinned or recently_active:
        return False
    return (acute_overlap >= ACUTE_OVERLAP_THRESHOLD
            and acute_age_hours <= ACUTE_RECENCY_WINDOW_HOURS)


# ── E2 reversible extinction: an inhibitory alternative to deletion ─────────
#
# The two circuits above are subtractive: the permanent circuit marks a memory
# is_stale (soft-delete — hides the whole row from recall) and the transient
# circuit lowers heat. Extinction (Bouton 2004, Learn. Mem. 11:485-494,
# doi:10.1101/lm.78804; Milad & Quirk 2012, Annu. Rev. Psychol. 63:129-151,
# doi:10.1146/annurev.psych.121208.131631) is DIFFERENT in kind: it is new
# inhibitory learning laid OVER a retained association, not erasure. The
# original trace is left fully intact and a reversible inhibitory tag suppresses
# its effective retrieval weight, so the association returns on its own over
# time (spontaneous recovery) and snaps back in full on reinstatement.
#
# This function offers extinction as the REVERSIBLE alternative to the permanent
# (is_stale) circuit: when a memory is under chronic forgetting pressure but is
# NOT a good candidate for hard soft-delete — because it may be needed again —
# a caller can deprecate it (grow the inhibitory tag) instead of deleting it.
# The decision here is deliberately conservative and orthogonal to the two
# dopaminergic circuits: it never sets is_stale and never touches heat; it only
# reports whether an extinction (reversible deprecate) is warranted. Tag
# arithmetic and the ablation guard live in `mcp_server.core.extinction`.


def should_extinguish(
    stage: str,
    chronic_interference: float,
    is_pinned: bool,
    recently_active: bool,
    *,
    already_stale: bool = False,
) -> bool:
    """Decide whether to reversibly EXTINGUISH (deprecate) rather than delete.

    Returns True when the memory is under enough chronic-interference pressure
    to warrant suppression but should be kept recoverable rather than
    soft-deleted — the reversible inhibitory route (Bouton 2004). Mirrors
    `is_permanent_forgetting`'s pressure test and exemptions (pinned /
    recently-active memories are never extinguished), but is a SEPARATE decision:
    it produces a reversible tag, not an is_stale erasure. Already-stale memories
    are skipped (deletion already won). Honors ``CORTEX_ABLATE_EXTINCTION=1``
    (returns False when the mechanism is lesioned, so no extinction tag is ever
    grown → no behaviour change).
    """
    from mcp_server.core.ablation import Mechanism, is_mechanism_disabled

    if is_mechanism_disabled(Mechanism.EXTINCTION):
        return False
    if is_pinned or recently_active or already_stale:
        return False
    return forgetting_pressure(stage, chronic_interference) >= PERMANENT_PRESSURE_THRESHOLD
