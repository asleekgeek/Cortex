"""Falsifiable acceptance criteria for the forgetting-curve benchmark.

source: ADR-0828

Pure logic over already-probed h(t) trajectories — no I/O, no DB. Ground
truth is EXTERNAL (published curve forms), never Cortex's own signals.
"""

from __future__ import annotations

from benchmarks.forgetting_curve import curve_fit

# source: ADR-0828


PROFILES = {
    "A_labile": {
        "importance": 0.2,
        "access": 0,
        "schema": 0.0,
        "terminal_stage": "labile",
        "expected_floor": 0.0,
    },
    "B_consolidated": {
        "importance": 0.6,
        "access": 3,
        "schema": 0.0,
        "terminal_stage": "consolidated",
        "expected_floor": 0.10,
    },
    "early_ltp": {
        "importance": 0.35,
        "access": 0,
        "schema": 0.0,
        "terminal_stage": "early_ltp",
        "expected_floor": 0.0,
    },
    "late_ltp": {
        "importance": 0.5,
        "access": 0,
        "schema": 0.0,
        "terminal_stage": "late_ltp",
        "expected_floor": 0.05,
    },
}

# source: ADR-0828
PERMASTORE_FLOOR = 0.10
# source: ADR-0828

COLLAPSE_THRESHOLD = 0.01
# source: ADR-0828

PLAUSIBLE_B_LOW, PLAUSIBLE_B_HIGH = 0.1, 0.6
# source: ADR-0828


SQRT_T_B_LOW, SQRT_T_B_HIGH = 0.4, 0.6


# source: ADR-0828


# source: ADR-0828
HEAT_BASE_EXCLUSIVE_CEIL = 0.9999


def transient_points(traj: list[dict], floor: float) -> list[tuple[float, float]]:
    """Strictly-decaying regime: heat in (floor·1.05, heat_base).

    source: ADR-0828
    """
    low = max(floor * 1.05, 1e-3)
    return [
        (p["age_hours"], p["heat"])
        for p in traj
        if low < p["heat"] < HEAT_BASE_EXCLUSIVE_CEIL
    ]


def criterion_power_over_exp(traj_b: list[dict]) -> dict:
    """Criterion 1: matured (B) transient fit at least as well by power law as
    by a single exponential. CAN FAIL — if B's post-maturation regime is a
    pure single exponential (constant α), exponential wins and this falsifies
    the power-law-from-cascade claim."""
    pts = transient_points(traj_b, PERMASTORE_FLOOR)
    power = curve_fit.fit_power_law(pts)
    expo = curve_fit.fit_exponential(pts)
    cmp = curve_fit.compare_models(power, expo)
    return {
        "name": "power_law_over_exponential",
        "source": "Wixted&Ebbesen 1991; Benna&Fusi 2016",
        "n_points": len(pts),
        "power_law_fit": power,
        "exponential_fit": expo,
        "comparison": cmp,
        "passed": cmp["power_law_at_least_as_good"],
        "margin_delta_aic": cmp["delta_aic_exp_minus_power"],
    }


def criterion_permastore(traj_a: list[dict], traj_b: list[dict]) -> dict:
    """Criterion 2 (Bahrick): matured B asymptotes ≥ floor and does NOT
    collapse, while labile A DOES collapse to ~0 (forgetting preserved)."""
    b_365 = traj_b[-1]["heat"]
    a_365 = traj_a[-1]["heat"]
    b_holds = b_365 >= PERMASTORE_FLOOR - 1e-4
    a_collapses = a_365 <= COLLAPSE_THRESHOLD
    return {
        "name": "permastore_bahrick",
        "source": "Bahrick 1984; pg_schema consolidated floor=0.10",
        "b_heat_at_365d": round(b_365, 6),
        "a_heat_at_365d": a_365,
        "permastore_floor": PERMASTORE_FLOOR,
        "collapse_threshold": COLLAPSE_THRESHOLD,
        "b_holds_floor": bool(b_holds),
        "a_collapses": bool(a_collapses),
        "passed": bool(b_holds and a_collapses),
        "margin_b_above_floor": round(b_365 - PERMASTORE_FLOOR, 6),
        "margin_a_below_collapse": round(COLLAPSE_THRESHOLD - a_365, 6),
    }


def criterion_exponent(traj_a: list[dict], traj_b: list[dict]) -> dict:
    """Criterion 3 (descriptive): fitted exponent / half-life vs published
    ranges. Plausibility, not pass/fail unless wildly off (negative HL)."""
    out = {
        "name": "exponent_half_life_plausibility",
        "source": "Wixted&Ebbesen 1991; Anderson&Schooler 1991; Benna&Fusi 2016",
        "plausible_b_band": [PLAUSIBLE_B_LOW, PLAUSIBLE_B_HIGH],
        "profiles": {},
    }
    sane = True
    for label, traj, floor in (
        ("A_labile", traj_a, 0.0),
        ("B_consolidated", traj_b, PERMASTORE_FLOOR),
    ):
        pts = transient_points(traj, floor)
        power = curve_fit.fit_power_law(pts)
        expo = curve_fit.fit_exponential(pts)
        b = power["b_exponent"]
        in_band = PLAUSIBLE_B_LOW <= b <= PLAUSIBLE_B_HIGH
        hl_sane = expo["half_life_hours"] is not None and expo["half_life_hours"] > 0
        sane = sane and hl_sane
        out["profiles"][label] = {
            "power_b": b,
            "power_b_in_band": bool(in_band),
            "power_b_fit_r2": power["r2_hspace"],
            "power_half_life_hours": power["half_life_hours"],
            "exp_b_per_hour": expo["b_per_hour"],
            "exp_half_life_hours": expo["half_life_hours"],
        }
    out["passed"] = bool(sane)
    return out


def criterion_benna_fusi_sqrt_t(
    trajs: dict[str, list[dict]], ages: list[float]
) -> dict:
    """Criterion 4 (Benna&Fusi law-family): does the model reproduce the
    cascade √t law, h ∝ 1/√t?

    source: ADR-0828"""
    curve = []
    for i, age in enumerate(ages):
        heats = [trajs[name][i]["heat"] for name in PROFILES]
        curve.append((age, sum(heats) / len(heats)))
    mixture_floor = sum(p["expected_floor"] for p in PROFILES.values()) / len(PROFILES)
    mixture_traj = [{"age_hours": t, "heat": h} for t, h in curve]
    pts = transient_points(mixture_traj, mixture_floor)
    power = curve_fit.fit_power_law(pts)
    expo = curve_fit.fit_exponential(pts)
    cmp = curve_fit.compare_models(power, expo)
    b = power["b_exponent"]
    in_band = SQRT_T_B_LOW <= b <= SQRT_T_B_HIGH
    return {
        "name": "benna_fusi_sqrt_t_law_family",
        "source": "Benna&Fusi 2016 (Nat.Neurosci. 19:1697 — SNR∝1/√t)",
        "n_transient_points": len(pts),
        "mixture_floor": round(mixture_floor, 6),
        "mean_curve": [[t, round(h, 6)] for t, h in curve],
        "power_law_fit": power,
        "exponential_fit": expo,
        "comparison": cmp,
        "sqrt_t_band": [SQRT_T_B_LOW, SQRT_T_B_HIGH],
        "power_b_exponent": b,
        "power_b_in_sqrt_t_band": bool(in_band),
        "passed": bool(cmp["winner"] == "power_law" and in_band),
    }


def verdict(c1: dict, c2: dict, bf: dict) -> str:
    """One-line overall verdict. overall_passed tracks the two gating criteria
    (C1 single-trace power law, C2 permastore); the Benna&Fusi √t law-family
    finding (bf) is appended as an explicit clause but does not gate."""
    if c1["passed"] and c2["passed"]:
        base = (
            "DEMONSTRATED: matured decay is power-law-compatible AND "
            "permastore holds while labile forgetting is preserved."
        )
    elif c2["passed"] and not c1["passed"]:
        base = (
            "PARTIALLY FALSIFIED: permastore (Bahrick) reproduced, but the "
            "α-ladder does NOT produce power-law decay for a matured trace "
            "— a single exponential fits at least as well. The cascade is "
            "piecewise/single-exponential + floor, not heavy-tailed."
        )
    elif c1["passed"] and not c2["passed"]:
        base = (
            "PARTIALLY FALSIFIED: power-law form present but permastore "
            "floor / labile-collapse contract violated."
        )
    else:
        base = (
            "FALSIFIED: neither the power-law form nor the permastore "
            "contract is reproduced by effective_heat over published "
            "curve forms."
        )
    b = bf["power_b_exponent"]
    win = bf["comparison"]["winner"]
    if bf["passed"]:
        base += (
            f" Benna&Fusi √t law-family CONFIRMED: the stage mixture "
            f"decays as a power law with b={b:.3f}≈0.5 (1/√t)."
        )
    else:
        base += (
            f" Benna&Fusi √t law-family NOT reproduced: the 4-level "
            f"α-ladder mixture (fit b={b:.3f}, winner={win}) is not the "
            f"1/√t continuum — too few levels over too narrow a rate range."
        )
    return base
