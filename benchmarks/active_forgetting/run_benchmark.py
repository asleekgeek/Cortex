"""Active-forgetting benchmark — two independent DA forgetting circuits (A2).

Acceptance instrument for Tier-A item A2: a NEW consolidation settlement pass
that, faithful to the *Drosophila* dopaminergic active-forgetting literature,
applies TWO anatomically/molecularly DISTINCT forgetting circuits — not a
severity ladder. Full design rationale lives in ADR-017; this docstring fixes
only the testable contract.

Primary sources (open-access via PMC; quotes verified against raw text):
  - Sabandal, Berry & Davis (2021), Nature 591:426-430 (PMC8522469): transient
    and permanent forgetting are "two separate DA-based circuits"; transient
    (DAMB / PPL1-α2α'2) "blocks retrieval" and is "triggered by interfering
    stimuli presented just prior to retrieval", recovering spontaneously;
    permanent (PPL1-γ2α'1 / Rac1) erodes the trace. Sustained transient
    stimulation did NOT convert to permanent loss ("returned to normal by day 14").
    Transient forgetting acts on consolidated PSD-LTM ⇒ it is STAGE-INDEPENDENT.
  - Davis & Zhong (2017), Neuron 95:490-503 (PMC5657245): "This does not
    necessarily mean that consolidated memories are immune … just much more
    resistant" ⇒ GRADED resistance, not a hard immunity gate. The intrinsic
    forgetting DA signal is "ongoing", "increased robustly with locomotor
    activity"/sensory input (interference) and "inhibit[ed]" by "sleep and rest".
  - Berry, Phan & Davis (2018), Cell Reports 25:651-662.e4 (PMC6239218): "strong
    memories … more resistant … weaker memories … more vulnerable" — ordinal
    ONLY; no quantitative strength→rate law exists in any of these papers.

Contract (each clause is a fixture below):
  PERMANENT circuit (Rac1 erosion → reversible is_stale):
    P1 DRIVER = chronic interference from NEWER memories; zero ⇒ no permanent.
    P2 STAGE-GRADED via the cascade interference_vulnerability (Kandel 2001 /
       Bahrick 1984 / Benna & Fusi 2016) — REUSED. Consolidated (0.05) resists
       strongly but is NOT hard-gated immune.
    P3 SLEEP PROTECTS: recently replayed/accessed ⇒ excluded (sleep quiets the
       ongoing forgetting cells).
    permanent ⟺ (chronic_interference × stage_vulnerability) >= Tp, not pinned/slept.
  TRANSIENT circuit (DAMB retrieval-block → reversible heat reduction):
    T1 TRIGGER = an acute recent interferer: acute_overlap >= X AND acute_age <= W.
    T2 STAGE-INDEPENDENT: fires even on consolidated memory (Sabandal's finding).
    T3 REVERSIBLE: recovers on re-access.
  INDEPENDENCE: the two circuits read different signals and never interact —
    a memory may receive neither, one, or both; transient never causes permanent.
  No (1-heat) salience term (no paper functional form); resistance rides on stage.
  No phasic-DA reuse (would invert: salient = high encoding DA = should resist).

Benchmark-FIRST rationale: no biological rate constant exists at hours/days
(literature is ms *Drosophila* / in-vitro kinetics), so every threshold must
trace to "source: benchmark <path>". This file IS that source — the labeled POOL
fixes ground truth and ``derive_thresholds`` reads Tp / X / W off it; the core
(mcp_server/core/active_forgetting.py) bakes them and is verified here.

Run:
    Cortex/.venv/bin/python3 benchmarks/active_forgetting/run_benchmark.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# The core under test (the same functions production calls). forgetting_pressure
# is the single source of the permanent-pressure formula; the derivation below
# reads the thresholds off the labeled POOL using it.
from mcp_server.core.active_forgetting import (  # noqa: E402
    forgetting_pressure,
    is_permanent_forgetting,
    is_transient_forgetting,
)

RESULTS_DIR = REPO / "benchmarks" / "results" / "active_forgetting"

# ── Labeled pool ───────────────────────────────────────────────────────────────
# Signals (explicit, DB-free stand-ins for the handler's embedding/entity queries,
# exactly as A1 uses explicit _gain for the vector query):
#   consolidation_stage — PERMANENT circuit's graded resistance (transient ignores it).
#   heat                — anchor detection (>=1.0) + the quantity transient reduces.
#   chronic_interference— ongoing aggregate overlap from NEWER memories (permanent driver).
#   acute_overlap       — overlap with the single strongest recent interferer (transient).
#   acute_age_hours     — age of that interferer (transient recency).
#   is_protected        — user-pinned hard exclusion (both circuits).
#   recently_active     — sleep/just-accessed: excludes permanent; transient recovers.
#   exp_permanent / exp_transient — by-construction ground-truth labels (the spec).
POOL = [
    # ── PERMANENT axis: chronic interference × graded stage resistance ─────────
    # (acute_overlap 0 ⇒ transient NO for all of these).
    {"id": "P1", "consolidation_stage": "labile", "heat": 0.30,
     "chronic_interference": 0.70, "acute_overlap": 0.0, "acute_age_hours": 999.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": True, "exp_transient": False,
     "note": "labile×0.70 eff 0.630 ⇒ permanent"},
    {"id": "P2", "consolidation_stage": "early_ltp", "heat": 0.25,
     "chronic_interference": 0.95, "acute_overlap": 0.0, "acute_age_hours": 999.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": True, "exp_transient": False,
     "note": "early_ltp×0.95 eff 0.475 ⇒ permanent"},
    {"id": "P3", "consolidation_stage": "consolidated", "heat": 0.20,
     "chronic_interference": 0.95, "acute_overlap": 0.0, "acute_age_hours": 999.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": False, "exp_transient": False,
     "note": "consolidated×0.95 eff 0.0475 ⇒ resists (graded, NOT immune-gated)"},
    {"id": "P4", "consolidation_stage": "late_ltp", "heat": 0.20,
     "chronic_interference": 0.60, "acute_overlap": 0.0, "acute_age_hours": 999.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": False, "exp_transient": False,
     "note": "late_ltp×0.60 eff 0.120 ⇒ resists"},
    {"id": "P5", "consolidation_stage": "labile", "heat": 0.30,
     "chronic_interference": 0.20, "acute_overlap": 0.0, "acute_age_hours": 999.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": False, "exp_transient": False,
     "note": "labile×0.20 eff 0.180 ⇒ weak driver, retain"},
    {"id": "P6", "consolidation_stage": "labile", "heat": 0.30,
     "chronic_interference": 0.80, "acute_overlap": 0.0, "acute_age_hours": 999.0,
     "is_protected": False, "recently_active": True,
     "exp_permanent": False, "exp_transient": False,
     "note": "eff 0.72 BUT recently_active ⇒ sleep-protected (load-bearing)"},
    {"id": "P7", "consolidation_stage": "labile", "heat": 0.30,
     "chronic_interference": 0.80, "acute_overlap": 0.0, "acute_age_hours": 999.0,
     "is_protected": True, "recently_active": False,
     "exp_permanent": False, "exp_transient": False,
     "note": "eff 0.72 BUT is_protected ⇒ retain"},
    {"id": "P8", "consolidation_stage": "labile", "heat": 0.30,
     "chronic_interference": 0.0, "acute_overlap": 0.0, "acute_age_hours": 999.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": False, "exp_transient": False,
     "note": "zero chronic interference ⇒ no permanent (driver falsifier)"},
    # ── TRANSIENT axis: acute recent interferer, stage-INDEPENDENT ─────────────
    # (chronic 0 ⇒ permanent NO for all of these).
    {"id": "T1", "consolidation_stage": "consolidated", "heat": 0.40,
     "chronic_interference": 0.0, "acute_overlap": 0.90, "acute_age_hours": 1.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": False, "exp_transient": True,
     "note": "consolidated + acute recent interferer ⇒ transient (STAGE-INDEPENDENT)"},
    {"id": "T2", "consolidation_stage": "labile", "heat": 0.40,
     "chronic_interference": 0.0, "acute_overlap": 0.85, "acute_age_hours": 2.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": False, "exp_transient": True,
     "note": "acute recent interferer ⇒ transient (reversibility tested)"},
    {"id": "T3", "consolidation_stage": "labile", "heat": 0.40,
     "chronic_interference": 0.0, "acute_overlap": 0.85, "acute_age_hours": 24.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": False, "exp_transient": False,
     "note": "strong overlap but interferer too OLD ⇒ no transient (isolates W)"},
    {"id": "T4", "consolidation_stage": "labile", "heat": 0.40,
     "chronic_interference": 0.0, "acute_overlap": 0.30, "acute_age_hours": 1.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": False, "exp_transient": False,
     "note": "recent but overlap too LOW ⇒ no transient (isolates X)"},
    {"id": "T5", "consolidation_stage": "consolidated", "heat": 0.40,
     "chronic_interference": 0.0, "acute_overlap": 0.90, "acute_age_hours": 1.0,
     "is_protected": True, "recently_active": False,
     "exp_permanent": False, "exp_transient": False,
     "note": "acute interferer but pinned ⇒ no transient"},
    # ── BOTH (independence) and NEITHER ────────────────────────────────────────
    {"id": "B1", "consolidation_stage": "labile", "heat": 0.30,
     "chronic_interference": 0.75, "acute_overlap": 0.90, "acute_age_hours": 1.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": True, "exp_transient": True,
     "note": "chronic eff 0.675 AND acute recent interferer ⇒ BOTH (independent)"},
    {"id": "N1", "consolidation_stage": "late_ltp", "heat": 0.30,
     "chronic_interference": 0.30, "acute_overlap": 0.20, "acute_age_hours": 5.0,
     "is_protected": False, "recently_active": False,
     "exp_permanent": False, "exp_transient": False,
     "note": "eff 0.06 and weak/old acute ⇒ neither"},
]


# Benchmark adapter: map a POOL row to the core's is_pinned argument.
def _pinned(mem: dict) -> bool:
    """User-pinned exclusion for BOTH circuits: is_protected or anchored (heat>=1.0)."""
    return bool(mem.get("is_protected")) or mem["heat"] >= 1.0


def _permanent_candidate(mem: dict) -> bool:
    """Passes the PERMANENT gates (not pinned, not sleep-protected)."""
    return not _pinned(mem) and not mem.get("recently_active")


def _transient_candidate(mem: dict) -> bool:
    """Passes the TRANSIENT gates (not pinned, not just-accessed/recovered)."""
    return not _pinned(mem) and not mem.get("recently_active")


# ── Constant derivation (this benchmark IS the source for the core constants) ───


def derive_thresholds() -> dict:
    """Read the three separating constants off the labeled POOL.

    Tp  permanent-pressure threshold (chronic × stage_vuln space).
    X   acute-overlap threshold; W acute-recency window (hours) for transient.
    Each is the midpoint between adjacent label classes — the maximum-margin 1-D
    separator, the standard read-off for a by-construction labeled set.
    """
    perm = [m for m in POOL if _permanent_candidate(m)]
    perm_yes = [forgetting_pressure(m["consolidation_stage"], m["chronic_interference"])
                for m in perm if m["exp_permanent"]]
    perm_no = [forgetting_pressure(m["consolidation_stage"], m["chronic_interference"])
               for m in perm if not m["exp_permanent"]]
    tp = (max(perm_no) + min(perm_yes)) / 2.0

    tr = [m for m in POOL if _transient_candidate(m)]
    tr_yes = [m for m in tr if m["exp_transient"]]
    # X: separate overlap among interferers recent enough to matter.
    yes_overlap_min = min(m["acute_overlap"] for m in tr_yes)
    recent_no_overlap = [m["acute_overlap"] for m in tr
                         if not m["exp_transient"] and m["acute_age_hours"] <= 12.0]
    x = (max(recent_no_overlap) + yes_overlap_min) / 2.0
    # W: separate age among interferers strong enough to matter (overlap >= x).
    yes_age_max = max(m["acute_age_hours"] for m in tr_yes)
    strong_no_age = [m["acute_age_hours"] for m in tr
                     if not m["exp_transient"] and m["acute_overlap"] >= x]
    w = (yes_age_max + min(strong_no_age)) / 2.0

    return {
        "Tp": tp, "X": x, "W": w,
        "perm_no_max": max(perm_no), "perm_yes_min": min(perm_yes),
        "perm_margin": min(perm_yes) - max(perm_no),
        "overlap_margin": yes_overlap_min - max(recent_no_overlap),
        "age_margin": min(strong_no_age) - yes_age_max,
    }


# ── Decisions (call the core) ───────────────────────────────────────────────────


def _decide_permanent(mem: dict) -> bool:
    return is_permanent_forgetting(
        mem["consolidation_stage"], mem["chronic_interference"],
        _pinned(mem), mem.get("recently_active", False),
    )


def _decide_transient(mem: dict) -> bool:
    return is_transient_forgetting(
        mem["acute_overlap"], mem["acute_age_hours"],
        _pinned(mem), mem.get("recently_active", False),
    )


def labels_reproduced() -> dict:
    """Core reproduces every (permanent, transient) label pair."""
    mismatches = []
    for m in POOL:
        gp, gt = _decide_permanent(m), _decide_transient(m)
        if gp != m["exp_permanent"] or gt != m["exp_transient"]:
            mismatches.append({"id": m["id"],
                               "expected": (m["exp_permanent"], m["exp_transient"]),
                               "got": (gp, gt)})
    return {"passed": not mismatches, "mismatches": mismatches, "n": len(POOL)}


# ── Falsifier fixtures (paper predictions; require the core) ─────────────────────


def fixture_consolidated_graded_not_immune() -> dict:
    """Consolidated RESISTS permanent (graded) yet is NOT globally immune: the
    transient circuit still fires on it (Davis&Zhong 2017 + Sabandal 2021)."""
    perm = [is_permanent_forgetting("consolidated", c, False, False)
            for c in (0.5, 0.95, 1.0)]
    # transient fires on consolidated with an acute recent interferer:
    trans = is_transient_forgetting(0.90, 1.0, False, False)
    return {"passed": not any(perm) and trans,
            "consolidated_permanent": perm, "consolidated_transient": trans}


def fixture_sleep_protects_permanent() -> dict:
    """recently_active ⇒ no permanent regardless of chronic interference (Davis&Zhong)."""
    failures = [c for c in (0.7, 0.9, 1.0)
                if is_permanent_forgetting("labile", c, False, True)]
    return {"passed": not failures, "failures": failures}


def fixture_zero_chronic_no_permanent() -> dict:
    """No chronic driver ⇒ no permanent, any stage (interference-driven falsifier)."""
    failures = [s for s in ("labile", "early_ltp", "late_ltp", "consolidated")
                if is_permanent_forgetting(s, 0.0, False, False)]
    return {"passed": not failures, "failures": failures}


def fixture_transient_stage_independent() -> dict:
    """An acute recent interferer triggers transient at EVERY stage (Sabandal 2021)."""
    failures = [s for s in ("labile", "early_ltp", "late_ltp", "consolidated")
                if not is_transient_forgetting(0.90, 1.0, False, False)]
    return {"passed": not failures, "failures": failures, "note": "stage not an arg"}


def fixture_transient_needs_recency_and_overlap() -> dict:
    """Transient requires BOTH overlap>=X AND age<=W (the AND, not either)."""
    old = is_transient_forgetting(0.90, 48.0, False, False)   # strong but old
    weak = is_transient_forgetting(0.20, 1.0, False, False)   # recent but weak
    fires = is_transient_forgetting(0.90, 1.0, False, False)  # both ⇒ fires
    return {"passed": (not old) and (not weak) and fires,
            "old": old, "weak": weak, "both": fires}


def fixture_circuits_independent() -> dict:
    """Four quadrants realised; transient never induces permanent (no conversion)."""
    both = (_decide_permanent(_m("B1")), _decide_transient(_m("B1")))
    perm_only = (_decide_permanent(_m("P1")), _decide_transient(_m("P1")))
    trans_only = (_decide_permanent(_m("T2")), _decide_transient(_m("T2")))
    # transient-only memory (acute strong, chronic 0) is never permanent:
    no_conversion = not is_permanent_forgetting("labile", 0.0, False, False)
    return {"passed": both == (True, True) and perm_only == (True, False)
            and trans_only == (False, True) and no_conversion,
            "both": both, "permanent_only": perm_only, "transient_only": trans_only,
            "no_conversion": no_conversion}


def fixture_reversibility() -> dict:
    """Transient recovers on re-access; permanent is reinstated on re-access.

    Both modes are reversible: a re-accessed (recently_active) memory escapes
    both circuits — transient spontaneously recovers (Sabandal 2021); permanent
    is_stale is a recoverable soft-delete reinstated when the trace is reactivated.
    """
    t2 = _m("T2")
    transient_recovers = _decide_transient(t2) and not is_transient_forgetting(
        t2["acute_overlap"], t2["acute_age_hours"], False, True)
    p1 = _m("P1")
    permanent_reinstated = _decide_permanent(p1) and not is_permanent_forgetting(
        p1["consolidation_stage"], p1["chronic_interference"], False, True)
    return {"passed": transient_recovers and permanent_reinstated,
            "transient_recovers": transient_recovers,
            "permanent_reinstated": permanent_reinstated}


def _m(mem_id: str) -> dict:
    return next(m for m in POOL if m["id"] == mem_id)


# ── Discriminating baseline ─────────────────────────────────────────────────────


def baseline_would_miss() -> dict:
    """Coldness != forgettability. A naive 'is_stale the coldest-N' (LRU/decay)
    baseline retires cold memories that are protected/consolidated/un-interfered,
    which the faithful permanent circuit retains. Heat is not even a permanent
    input here, so the baseline mis-fires by construction."""
    faithful = {m["id"] for m in POOL if m["exp_permanent"]}
    coldest = sorted(POOL, key=lambda m: m["heat"])[:len(faithful)]
    baseline = {m["id"] for m in coldest}
    return {"baseline_stale": sorted(baseline), "faithful_stale": sorted(faithful),
            "baseline_wrongly_staled": sorted(baseline - faithful),
            "baseline_wrong_count": len(baseline - faithful)}


def main() -> int:
    th = derive_thresholds()
    baseline = baseline_would_miss()

    print("=" * 78)
    print("ACTIVE-FORGETTING BENCHMARK  (two independent DA circuits)")
    print("=" * 78)
    print("\n[derived constants — SOURCE for mcp_server/core/active_forgetting.py]")
    print(f"  PERMANENT_PRESSURE_THRESHOLD = {th['Tp']:.5f}"
          f"   (retain≤{th['perm_no_max']:.4f} | stale≥{th['perm_yes_min']:.4f}; "
          f"margin {th['perm_margin']:.4f})")
    print(f"  ACUTE_OVERLAP_THRESHOLD      = {th['X']:.5f}   (margin {th['overlap_margin']:.4f})")
    print(f"  ACUTE_RECENCY_WINDOW_HOURS   = {th['W']:.5f}   (margin {th['age_margin']:.4f}h)")
    print("\n[baseline 'is_stale the coldest' vs faithful permanent]")
    print(f"  baseline stales {baseline['baseline_stale']}")
    print(f"  faithful stales {baseline['faithful_stale']}")
    print(f"  baseline WRONGLY stales {baseline['baseline_wrongly_staled']} "
          f"({baseline['baseline_wrong_count']} of {len(POOL)})")

    report = {
        "benchmark": "active_forgetting",
        "date": datetime.now(timezone.utc).isoformat(),
        "derived_thresholds": {
            "PERMANENT_PRESSURE_THRESHOLD": round(th["Tp"], 5),
            "ACUTE_OVERLAP_THRESHOLD": round(th["X"], 5),
            "ACUTE_RECENCY_WINDOW_HOURS": round(th["W"], 5),
        },
        "margins": {"permanent": round(th["perm_margin"], 5),
                    "overlap": round(th["overlap_margin"], 5),
                    "age_hours": round(th["age_margin"], 5)},
        "baseline_wrongly_staled": baseline["baseline_wrongly_staled"],
    }

    repro = labels_reproduced()
    f_graded = fixture_consolidated_graded_not_immune()
    f_sleep = fixture_sleep_protects_permanent()
    f_zero = fixture_zero_chronic_no_permanent()
    f_stageind = fixture_transient_stage_independent()
    f_recency = fixture_transient_needs_recency_and_overlap()
    f_indep = fixture_circuits_independent()
    f_rev = fixture_reversibility()

    print(f"\n[labels reproduced]  passed={repro['passed']}  "
          f"mismatches={repro['mismatches']}")
    print("\n[falsifiers]")
    print(f"  consolidated graded-resistant, not immune   passed={f_graded['passed']}")
    print(f"  sleep protects permanent                    passed={f_sleep['passed']}")
    print(f"  zero chronic ⇒ no permanent                 passed={f_zero['passed']}")
    print(f"  transient stage-independent                 passed={f_stageind['passed']}")
    print(f"  transient needs recency AND overlap         passed={f_recency['passed']}")
    print(f"  circuits independent (no conversion)        passed={f_indep['passed']}")
    print(f"  both modes reversible on re-access          passed={f_rev['passed']}")

    passed = all([repro["passed"], f_graded["passed"], f_sleep["passed"],
                  f_zero["passed"], f_stageind["passed"], f_recency["passed"],
                  f_indep["passed"], f_rev["passed"]])
    report.update({
        "labels_reproduced": repro["passed"],
        "fixture_consolidated_graded_not_immune": f_graded["passed"],
        "fixture_sleep_protects_permanent": f_sleep["passed"],
        "fixture_zero_chronic_no_permanent": f_zero["passed"],
        "fixture_transient_stage_independent": f_stageind["passed"],
        "fixture_transient_needs_recency_and_overlap": f_recency["passed"],
        "fixture_circuits_independent": f_indep["passed"],
        "fixture_reversibility": f_rev["passed"],
        "passed": passed,
    })
    _write(report)
    print(f"\nPASSED={passed}")
    return 0 if passed else 1


def _write(report: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"{stamp}.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nresults written to {out}")


if __name__ == "__main__":
    raise SystemExit(main())
