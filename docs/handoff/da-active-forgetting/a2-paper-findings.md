# A2 — DA-gated reversible active forgetting: paper findings (for ADR-017)

## Primary sources (all open-access via PMC)
- Davis & Zhong 2017, *Neuron* 95:490–503 — "The Biology of Forgetting—A Perspective" (PMC5657245)
- Berry, Phan & Davis 2018, *Cell Reports* 25:651–662.e4 — "Dopamine Neurons Mediate Learning and Forgetting through Bidirectional Modulation of a Memory Trace" (PMC6239218)
- Cervantes-Sandoval et al. 2017, *Cell Reports* 21:2074–2081 — DAMB→Gq forgetting (PMC6168074)
- Sabandal, Berry & Davis 2021, *Nature* 591:426–430 — "Dopamine-based mechanism for transient forgetting" (PMC8522469)  [NOTE: correct cite — Berry is 2nd author, not "Berry 2021"]
- PNAS 2022 (PMC9499536) — Sickie / dedicated DA circuit for active forgetting
- Shuai et al. 2018, *Front. Syst. Neurosci.* 12:3 — review

## 6 answers (each paper-cited)
1. **DIRECTION**: DA *accelerates* forgetting. Tonic (ongoing) DA via **DAMB** receptor (Gq) drives forgetting; **dDA1** (Gs) drives learning. Blocking DA release ~doubles 3h retention. Signal is TONIC/ongoing, not phasic.
2. **REVERSIBILITY**: TWO modes. *Transient* = retrieval block, trace intact, spontaneous recovery ~1h (Sabandal 2021). *Permanent* = Rac1/Cofilin actin remodeling erodes trace BUT residual engram can remain; reinstatement by reminders/context/stimulants possible (Berry 2018, Davis&Zhong 2017).
3. **SALIENCE RESISTS**: stronger memories resist DAn forgetting; weak/labile vulnerable (Berry 2018). Consolidation is the escape route — "forgetting is the default… unless consolidation intervenes and solidifies memories deemed valuable" (Davis&Zhong 2017).
4. **INTERFERENCE**: new learning retroactively interferes via same DAMB/Rac1 pathway (Berry 2018); ongoing sensory/locomotor activity increases the forgetting DA signal (Davis&Zhong 2017).
5. **RATE**: NO usable rate constant. All quant is Drosophila ms-to-hour or in-vitro receptor kinetics (DAMB Gq 2.71 s⁻¹, EC50 56.7nM — NOT forgetting rates). Labile STM "a few hours"; ARM ">24h"; Rac1 inhibition extends STM "from hours to >1 day". => thresholds MUST come from our own labeled benchmark.
6. **CONSOLIDATION GATE**: Rac1/DAMB forgets ASM (labile), NOT ARM (consolidated). Sickie knockdown enhances labile only. => active forgetting applies ONLY to labile/early stages.

## Design constraints these impose on A2 (new consolidation pass, scope already approved)
- **GATE by stage**: apply only to labile / early_ltp. EXCLUDE consolidated / late_ltp. (paper-strong)
- **SALIENCE INVERSE**: high heat/salience RESISTS; low heat is vulnerable. (paper-strong; functional form NOT paper-given → benchmark)
- **INTERFERENCE driver**: candidate must be interfered/redundant (high entity overlap with newer memories). (paper-strong)
- **REVERSIBLE soft-delete**: mark `is_stale=TRUE` (row persists, excluded from recall, recoverable) = permanent-mode analog kept recoverable, matches residual-engram/reinstatement. (paper-supported)
- **CRITICAL — do NOT reuse phasic DA**: coupled_neuromodulation DA is phasic/encoding-reward. Tonic forgetting-DA is a different channel. Conflating inverts the effect (high encoding DA = salient = should RESIST). So salience resists; do not multiply decay by phasic DA.
- **EXCLUDE**: anchored (heat=1.0), is_protected, consolidated stage.
- **Thresholds**: every numeric threshold (heat cutoff, interference cutoff, cold-period) → `source: benchmark <path>`, derived, never invented.

## CORRECTED FAITHFUL DESIGN (user: NO divergence allowed — 2026-06-29)
Both earlier "divergences" are ELIMINABLE. Faithful two-mode design:
- DRIVER = interference from NEWER memories (retroactive interference, Berry 2018 Pt4b). Not a detached offline timer.
- SLEEP PROTECTS: sleep replay runs FIRST (boosts heat/advances stage of reactivated memories); forgetting step then EXCLUDES anything recently replayed/accessed. => sleep-suppression honored by exclusion (Davis&Zhong 2017; Shuai 2018). NOT forgetting-during-sleep.
- TWO MODES (Sabandal 2021), modeled separately, NOT collapsed:
  * TRANSIENT = retrieval suppression, trace intact, spontaneous recovery → reduce HEAT (lower rank, recovers on access).
  * PERMANENT = Rac1 erosion, residual+reinstatable engram → is_stale=TRUE only after SUSTAINED pressure (row persists=residual; recoverable=reinstatement).
- STAGE GATE: labile/early_ltp only; consolidated/late_ltp IMMUNE (ASM vs ARM).
- SALIENCE RESISTS (inverse heat). Do NOT reuse phasic DA channel.
- Ordering inside consolidate(): replay(protect) → forgetting-settlement(transient heat-down → permanent is_stale). Coherent: replay-protected memories have higher heat/advanced stage and are spared.

## Remaining honest notes (NOT divergences — discretization/measurement)
- Ongoing tonic process is evaluated as a periodic settlement pass = discretization of a continuous process (same as lazy read-time decay). Faithful as long as driver=interference and sleep-protected excluded.
- No biological rate constant exists at hours/days → all constants benchmark-measured. This is honest measurement, not divergence.

## METHOD LESSON (applies to A1/A3 audits too)
Watch for proxy-substitution that silently changes the paper's quantity (e.g. Need=expected-future-occupancy replaced by past access_count). If a proxy diverges from the paper's quantity, it is a divergence to fix, not an acceptable simplification.
