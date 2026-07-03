# Cortex Neuroscience Implementation Audit

## Methodology

For each module: (1) the paper(s) the current docstring cites, (2) what those papers
describe, (3) what the code actually implements now, (4) whether the correspondence is
faithful. Ratings:

- **FAITHFUL**: Code implements the cited paper's core equation(s) correctly, at an
  adapted timescale where noted.
- **DOCUMENTED**: Honest adaptation — captures the paper's mechanism but simplifies or
  rescales, with the departure explicitly noted in the source.
- **HONEST**: Heuristic labeled as such in the source, with no false citation.
- **APPROXIMATION**: Captures the main idea but materially simplifies or under-models.
- **N/A**: Orchestration module with no independent scientific claim.

> **Regenerated 2026-07-01.** The detailed per-module sections below were rewritten to
> match the *current* code. They had drifted to the pre-2026-04-01 state (old
> METAPHOR/FAKE scheme, superseded citations) while the Summary Table tracked the code;
> each section's verdict now equals its Summary-Table row. No code was changed by that
> regeneration. Verdicts and cited papers are authoritative from the Summary Table; the
> "What the code implements" lines were verified against the current source.

---

### 1. thermodynamics.py

- **Paper(s) cited:** Ebbinghaus 1885, McGaugh 2004
- **What the code implements:** Heat/surprise/decay/importance/valence heuristics. compute_decay = Ebbinghaus h(t)=h0·λ_eff^t with λ_base 0.95 (normal) / 0.998 (important>0.7), valence via time-saturating emotional_mod, plus a confidence modifier (1+0.1·confidence). Importance uses Edmundson (1969) four-feature scoring; valence uses VADER (Hutto & Gilbert 2014).
- **Status:** HONEST
- **Primary note:** Decay cites Ebbinghaus; heuristics documented as such

### 2. coupled_neuromodulation.py

- **Paper(s) cited:** Schultz 1997, Dawes 1979
- **What the code implements:** Orchestrates the 4-channel (DA/NE/ACh/5-HT) cross-coupling cascade and downstream gating; per-channel math lives in neuromodulation_channels.py. Composite modulation uses equal-weight averaging (Dawes 1979) over channels normalized to 1.0=baseline (DA in [0,3], others [0,2]).
- **Status:** HONEST
- **Primary note:** Doya departure documented; downstream functions labeled as heuristics

### 3. neuromodulation_channels.py

- **Paper(s) cited:** Rescorla-Wagner 1972, Schultz 1997
- **What the code implements:** DA channel implements Rescorla-Wagner RPE (Schultz 1997) with firing bounds; NE/ACh/5-HT and cross-coupling are heuristics honestly labeled against 'What Doya (2002) actually says'.
- **Status:** FAITHFUL (DA) / HONEST (NE,ACh,5-HT)
- **Primary note:** DA RPE: R-W equation + Schultz firing bounds [0,3]. NE/ACh/5-HT honestly documented

### 4. emotional_tagging.py

- **Paper(s) cited:** Yerkes-Dodson 1908
- **What the code implements:** Detects emotion via VADER + domain keywords; importance boost is a smooth arousal inverted-U f(a)=c·a·e^{-b·a}+1 (peak 1.57 at a≈0.7). The inverted-U is Hebb's curve (Hebb 1955); Yerkes & Dodson (1908) established the tradeoff but did not plot it against arousal.
- **Status:** FAITHFUL
- **Primary note:** f(a) = c*a*exp(-b*a) smooth inverted-U curve

### 5. synaptic_tagging.py

- **Paper(s) cited:** Frey & Morris 1997, Luboeinski 2021
- **What the code implements:** Synaptic Tagging & Capture: strong events retroactively promote weak entity-sharing memories. Bistable consolidation ODE dz/dt=z(1-z)(z-0.5) from Luboeinski & Tetzlaff (2021, Communications Biology). 48h tag window is a documented hours-timescale adaptation of the biological ~1-6h.
- **Status:** DOCUMENTED
- **Primary note:** Bistable z ODE faithful; 48h window is engineering adaptation

### 6. oscillatory_phases.py

- **Paper(s) cited:** Hasselmo 2005, Lisman&Jensen 2013, Buzsaki 2015
- **What the code implements:** Theta gating via Hasselmo (2002) sigmoid gate(phase)=1/(1+e^{-k(phase-0.5)}); enc/ret gains sum to 2-X at all phases. Gamma binding capacity 7 (Lisman & Jensen 2013). SWR state-machine constants are engineering choices, flagged as such.
- **Status:** DOCUMENTED
- **Primary note:** Encoding/retrieval separation captured; cosine is engineering

### 7. cascade_stages.py

- **Paper(s) cited:** Kandel 2001, Nader 2000, Bahrick 1984
- **What the code implements:** Four-stage cascade LABILE→EARLY_LTP→LATE_LTP→CONSOLIDATED (+RECONSOLIDATING) with per-stage decay multipliers, interference vulnerability, plasticity, dwell hours, and permastore heat floors (0.0/0.0/0.05/0.10). Floors grounded in Bahrick (1984) permastore + Benna & Fusi (2016); stage timings track Kandel (2001).
- **Status:** DOCUMENTED
- **Primary note:** Stage timings match biology; multipliers hand-tuned

### 8. cascade_advancement.py

- **Paper(s) cited:** Kandel 2001, Tse 2007, Nader 2000
- **What the code implements:** Stage-transition logic: LABILE→EARLY needs DA≥1 or imp>0.3; EARLY→LATE needs replay≥1 or imp>0.4; LATE→CONSOLIDATED needs replay≥3 (or 1 if schema>0.5). Schema acceleration 15^(-schema_match) approximates Tse (2007); reconsolidation on prediction-error mismatch (Nader 2000).
- **Status:** APPROXIMATION
- **Primary note:** Schema acceleration under-modeled (50% vs 15x in Tse)

### 9. separation_core.py

- **Paper(s) cited:** Leutgeb 2007, Rolls 2013
- **What the code implements:** Dentate-gyrus pattern separation: Gram-Schmidt-style orthogonalization of near-duplicate embeddings + sparsification to ~4% active (within Leutgeb 2007 / Rolls 2013 DG range of 2-5%).
- **Status:** FAITHFUL
- **Primary note:** Sparsity 4% from DG data; Gram-Schmidt orthogonalization

### 10. schema_engine.py

- **Paper(s) cited:** Tse 2007, van Kesteren 2012, Piaget
- **What the code implements:** Schema matching (weighted Jaccard), Piaget accommodation via EMA, and revision detection. Connects to predictive coding via prediction-error/free-energy. Tse (2007)/van Kesteren (2012) are experimental, not equation sources — adaptation documented.
- **Status:** DOCUMENTED
- **Primary note:** Tse is experimental only; no equations exist

### 11. schema_extraction.py

- **Paper(s) cited:** Tse 2007, Gilboa&Marlatte 2017
- **What the code implements:** Schema formation from memory clusters via entity/tag frequency analysis, plus schema merging by Jaccard similarity. Gilboa & Marlatte (2017) provide the criteria (multi-episode basis, lack of unit detail), not equations — frequency thresholds are engineering choices.
- **Status:** DOCUMENTED
- **Primary note:** Frequency-based; Gilboa provides criteria not equations

### 12. interference.py

- **Paper(s) cited:** Anderson&Neely 1996, Norman 2007
- **What the code implements:** Resolution side of interference: projection-based orthogonalization, retrieval suppression (RIF, Anderson & Neely 1996), and domain pressure metrics. Linear suppression documented as a simplification of the actual inhibitory-control process.
- **Status:** DOCUMENTED
- **Primary note:** LCA cited; linear suppression documented as simplification

### 13. homeostatic_plasticity.py

- **Paper(s) cited:** Tetzlaff 2011, BCM 1982
- **What the code implements:** Multiplicative synaptic scaling Δw=α·w·(target-actual) (Tetzlaff 2011 Eq. 3, order-preserving) + BCM sliding threshold θ=E[c²] (BCM 1982) with quadratic φ(c,θ)=c(c-θ).
- **Status:** FAITHFUL
- **Primary note:** Tetzlaff Eq.3 multiplicative scaling + BCM quadratic phi

### 14. dendritic_clusters.py

- **Paper(s) cited:** (none — metaphor documented)
- **What the code implements:** Groups memories onto 'branches' by entity/tag Jaccard similarity. Explicitly a semantic-similarity heuristic (real dendritic clustering is spatiotemporal), labeled as such — no false citation. Nonlinear amplification lives in dendritic_computation.py.
- **Status:** HONEST
- **Primary note:** Jaccard grouping labeled as heuristic

### 15. dendritic_computation.py

- **Paper(s) cited:** Poirazi 2003
- **What the code implements:** Poirazi, Brannon & Mel (2003) two-layer neuron: dendritic subunit s(n)=1/(1+e^{(3.6-n)/2})+0.30n+0.0114n² and soma sigmoid g(x)=0.96x/(1+1509·e^{-0.26x}) — constants from the paper's Fig. 3 fits (soma half-max at x≈28).
- **Status:** FAITHFUL
- **Primary note:** Sigmoid s(n) + soma g(x) from Neuron 37:989-999 Fig 3

### 16. two_stage_model.py

- **Paper(s) cited:** McClelland 1995
- **What the code implements:** McClelland (1995) Complementary Learning Systems: scalar hippocampal_dependency tracks fast-episodic→slow-cortical transfer via replay. CLS defines no scalar dependency metric — the construct is honestly labeled an engineering operationalization.
- **Status:** DOCUMENTED
- **Primary note:** CLS framework qualitative; scalar dependency is engineering

### 17. two_stage_transfer.py

- **Paper(s) cited:** McClelland 1995, Ketz 2023
- **What the code implements:** Per-replay transfer delta with diminishing returns + interleaved replay scheduling (McClelland 1995). Transfer rate 0.02 = C-HORSE (Ketz 2023) hippocampal LR, used as the per-replay rate (engineering choice; cortical 0.002 would be 10× slower than the replay cadence).
- **Status:** FAITHFUL
- **Primary note:** C-HORSE cortical learning rate 0.02

### 18. tripartite_synapse.py

- **Paper(s) cited:** Perea 2009
- **What the code implements:** Astrocyte-territory orchestration over L1 clusters; three-regime (quiescent/facilitation/depression) qualitative model from Perea (2009). Calcium ODEs delegated to tripartite_calcium.py.
- **Status:** DOCUMENTED
- **Primary note:** Three-regime model qualitative; delegates to tripartite_calcium

### 19. tripartite_calcium.py

- **Paper(s) cited:** De Pitta 2009, Pellerin 1994
- **What the code implements:** De Pitta et al. (2009) G-ChI Li-Rinzel calcium ODEs (channel/leak/pump fluxes, m_inf/h_inf gating); resting Ca²⁺≈0.54µM matches the coded steady state. Metabolic 'lactate' rate is an engineering add-on, flagged.
- **Status:** DOCUMENTED
- **Primary note:** De Pitta ODE faithful; metabolic rate is engineering

### 20. synaptic_plasticity.py

- **Paper(s) cited:** Tsodyks-Markram 1997, Hasselmo 2005
- **What the code implements:** Tsodyks-Markram short-term plasticity (u/x resource update, Tsodyks & Markram 1997) + theta-phase gating (Hasselmo 2005). Hours-timescale τ_F=0.5h/τ_D=2.0h INVERTS the biological τ_F/τ_D ordering — a deliberate modeling choice, now documented (was mislabeled 'ratio preserved').
- **Status:** FAITHFUL
- **Primary note:** u_new = u + U*(1-u), x_new = x - u_eff*x

### 21. synaptic_plasticity_hebbian.py

- **Paper(s) cited:** BCM 1982, Bi&Poo 1998
- **What the code implements:** BCM (1982) quadratic φ(c,θ)=c(c-θ) with sliding threshold θ=E[c²], and Bi & Poo (1998) STDP A±·e^{∓Δt/τ±} (timescale adapted to hours). One LTD branch flagged as engineering, not BCM.
- **Status:** FAITHFUL
- **Primary note:** phi(c,theta_m) = c*(c-theta_m) quadratic; STDP A+*exp(-dt/tau+)

### 22. synaptic_plasticity_stochastic.py

- **Paper(s) cited:** Hebb, BCM, Markram
- **What the code implements:** Novel composition of faithful components: Tsodyks-Markram stochastic release × BCM Hebbian LTP/LTD × additive noise × Hasselmo theta gating. No single paper prescribes the composition — documented as such.
- **Status:** DOCUMENTED
- **Primary note:** Novel composition of faithful components

### 23. microglial_pruning.py

- **Paper(s) cited:** (none — metaphor documented)
- **What the code implements:** Knowledge-graph edge pruning via the Serrano-Boguna-Vespignani (2009) disparity filter α_ij=(1-p_ij)^{k_i-1} (keep if α<0.05 at either endpoint) + 7-day temporal half-life. 'Microglial' is a metaphor for the pruning; the algorithm is the network-backbone one, honestly named.
- **Status:** HONEST
- **Primary note:** Threshold rules labeled as heuristic

### 24. dual_store_cls.py

- **Paper(s) cited:** (none — heuristic documented)
- **What the code implements:** Regex classifier tagging memories episodic vs semantic to weight retrieval. Labeled a heuristic — does NOT implement CLS learning; no false CLS citation.
- **Status:** HONEST
- **Primary note:** Regex classifier labeled honestly

### 25. spreading_activation.py

- **Paper(s) cited:** Collins & Loftus 1975
- **What the code implements:** Collins & Loftus (1975) semantic priming: BFS from seed nodes, activation × edge_weight × distance-decay, convergent summation at receiving nodes, with depth/threshold/node caps as engineering defaults.
- **Status:** FAITHFUL
- **Primary note:** BFS with decay and convergent summation

### 26. engram.py

- **Paper(s) cited:** Rashid 2016, Josselyn 2007
- **What the code implements:** Josselyn & Frankland (2007) / Rashid (2016) competitive allocation: slots compete via CREB-like excitability decaying with a 6h half-life (E(t)=E0·2^{-t/6}), temporally close memories share slots, lateral inhibition prevents collapse. boost/inhibition constants hand-tuned.
- **Status:** DOCUMENTED
- **Primary note:** 6h half-life faithful; inhibition + boost hand-tuned

### 27. decay_cycle.py

- **Paper(s) cited:** ACT-R (Anderson & Lebiere 1998)
- **What the code implements:** Stage-gated periodic decay with permastore floors. Default exponential heat(t)=heat(0)·λ^t (Ebbinghaus), stage-adjusted; adaptive path uses ACT-R base-level B_i=ln(Σt^{-d}), d=0.5, logistic activation (Anderson & Lebiere 1998), s=1.0 flagged as a deviation from the paper's ~0.4.
- **Status:** FAITHFUL
- **Primary note:** B_i = ln(n) - d*ln(L), d=0.5

### 28. replay.py

- **Paper(s) cited:** Foster&Wilson 2006, Diba&Buzsaki 2007
- **What the code implements:** SWR-gated replay for context restoration and consolidation. Forward/reverse directions (Foster & Wilson 2006; Diba & Buzsaki 2007) correct; sequences built from entity overlap/relationships (an engineering analog of place-cell reactivation), documented.
- **Status:** DOCUMENTED
- **Primary note:** Forward/reverse correct; entity-based documented

### 29. replay_execution.py

- **Paper(s) cited:** Foster&Wilson 2006, Davidson 2009
- **What the code implements:** Builds temporal & causal replay sequences and extracts STDP pairs. 15-20× compression matches biological SWR (Davidson 2009); 20× upper bound used. Sequence building from entity overlap is engineering, flagged.
- **Status:** DOCUMENTED
- **Primary note:** Compression 15-20x correct; sequence building is engineering

### 30. replay_selection.py

- **Paper(s) cited:** (none — heuristic documented)
- **What the code implements:** Selects/orders SWR replay sequences by a priority score (avg_heat·0.4 + √var·0.6)·DA. Labeled a heuristic; not the exact Schultz TD-RPE — no false citation.
- **Status:** HONEST
- **Primary note:** Priority score labeled as heuristic

### 31. reranker.py

- **Paper(s) cited:** Joren ICLR 2025, FlashRank
- **What the code implements:** FlashRank (ms-marco-MiniLM-L-12-v2) cross-encoder reranking, blended with WRRF via α=0.70. The 'Sufficient Context' (Joren 2025) analog is a binary confidence gate, not the paper's calibrated autorater — deliberate simplification, with rejected Platt/adaptive variants kept opt-in and their regressions reported.
- **Status:** APPROXIMATION
- **Primary note:** Binary gate instead of calibrated confidence

### 32. query_decomposition.py

- **Paper(s) cited:** (none — heuristic documented)
- **What the code implements:** Intent routing + regex entity-extraction sub-queries. Previously cited IRCoT/HippoRAG; those false citations were removed — now honestly labeled a regex heuristic (no LLM decomposition, no PageRank).
- **Status:** HONEST
- **Primary note:** Regex extraction labeled honestly

### 33. write_post_store.py

- **Paper(s) cited:** (delegates)
- **What the code implements:** Orchestration/composition root wiring entity persistence, synaptic tagging, and engram allocation. No independent scientific claim of its own; delegates to the relevant core modules.
- **Status:** N/A
- **Primary note:** Orchestration module, no independent claims

---

## Summary Table

| Module | Paper(s) Cited | Status | Primary Issue |
|---|---|---|---|
| thermodynamics.py | Ebbinghaus 1885, McGaugh 2004 | HONEST | Decay cites Ebbinghaus; heuristics documented as such |
| coupled_neuromodulation.py | Schultz 1997, Dawes 1979 | HONEST | Doya departure documented; downstream functions labeled as heuristics |
| neuromodulation_channels.py | Rescorla-Wagner 1972, Schultz 1997 | FAITHFUL (DA) / HONEST (NE,ACh,5-HT) | DA RPE: R-W equation + Schultz firing bounds [0,3]. NE/ACh/5-HT honestly documented |
| emotional_tagging.py | Yerkes-Dodson 1908 | FAITHFUL | f(a) = c*a*exp(-b*a) smooth inverted-U curve |
| synaptic_tagging.py | Frey & Morris 1997, Luboeinski 2021 | DOCUMENTED | Bistable z ODE faithful; 48h window is engineering adaptation |
| oscillatory_phases.py | Hasselmo 2005, Lisman&Jensen 2013, Buzsaki 2015 | DOCUMENTED | Encoding/retrieval separation captured; cosine is engineering |
| cascade_stages.py | Kandel 2001, Nader 2000, Bahrick 1984 | DOCUMENTED | Stage timings match biology; multipliers hand-tuned |
| cascade_advancement.py | Kandel 2001, Tse 2007, Nader 2000 | APPROXIMATION | Schema acceleration under-modeled (50% vs 15x in Tse) |
| separation_core.py | Leutgeb 2007, Rolls 2013 | FAITHFUL | Sparsity 4% from DG data; Gram-Schmidt orthogonalization |
| schema_engine.py | Tse 2007, van Kesteren 2012, Piaget | DOCUMENTED | Tse is experimental only; no equations exist |
| schema_extraction.py | Tse 2007, Gilboa&Marlatte 2017 | DOCUMENTED | Frequency-based; Gilboa provides criteria not equations |
| interference.py | Anderson&Neely 1996, Norman 2007 | DOCUMENTED | LCA cited; linear suppression documented as simplification |
| homeostatic_plasticity.py | Tetzlaff 2011, BCM 1982 | FAITHFUL | Tetzlaff Eq.3 multiplicative scaling + BCM quadratic phi |
| dendritic_clusters.py | (none — metaphor documented) | HONEST | Jaccard grouping labeled as heuristic |
| dendritic_computation.py | Poirazi 2003 | FAITHFUL | Sigmoid s(n) + soma g(x) from Neuron 37:989-999 Fig 3 |
| two_stage_model.py | McClelland 1995 | DOCUMENTED | CLS framework qualitative; scalar dependency is engineering |
| two_stage_transfer.py | McClelland 1995, Ketz 2023 | FAITHFUL | C-HORSE cortical learning rate 0.02 |
| tripartite_synapse.py | Perea 2009 | DOCUMENTED | Three-regime model qualitative; delegates to tripartite_calcium |
| tripartite_calcium.py | De Pitta 2009, Pellerin 1994 | DOCUMENTED | De Pitta ODE faithful; metabolic rate is engineering |
| synaptic_plasticity.py | Tsodyks-Markram 1997, Hasselmo 2005 | FAITHFUL | u_new = u + U*(1-u), x_new = x - u_eff*x |
| synaptic_plasticity_hebbian.py | BCM 1982, Bi&Poo 1998 | FAITHFUL | phi(c,theta_m) = c*(c-theta_m) quadratic; STDP A+*exp(-dt/tau+) |
| synaptic_plasticity_stochastic.py | Hebb, BCM, Markram | DOCUMENTED | Novel composition of faithful components |
| microglial_pruning.py | (none — metaphor documented) | HONEST | Threshold rules labeled as heuristic |
| dual_store_cls.py | (none — heuristic documented) | HONEST | Regex classifier labeled honestly |
| spreading_activation.py | Collins & Loftus 1975 | FAITHFUL | BFS with decay and convergent summation |
| titans_memory.py | Behrouz et al. (NeurIPS 2025) | FAITHFUL | M_t = M_{t-1} - S_t, S_t = eta*S_{t-1} - theta*grad |
| engram.py | Rashid 2016, Josselyn 2007 | DOCUMENTED | 6h half-life faithful; inhibition + boost hand-tuned |
| decay_cycle.py | ACT-R (Anderson & Lebiere 1998) | FAITHFUL | B_i = ln(n) - d*ln(L), d=0.5 |
| replay.py | Foster&Wilson 2006, Diba&Buzsaki 2007 | DOCUMENTED | Forward/reverse correct; entity-based documented |
| replay_execution.py | Foster&Wilson 2006, Davidson 2009 | DOCUMENTED | Compression 15-20x correct; sequence building is engineering |
| replay_selection.py | (none — heuristic documented) | HONEST | Priority score labeled as heuristic |
| reranker.py | Joren ICLR 2025, FlashRank | APPROXIMATION | Binary gate instead of calibrated confidence |
| query_decomposition.py | (none — heuristic documented) | HONEST | Regex extraction labeled honestly |
| write_post_store.py | (delegates) | N/A | Orchestration module, no independent claims |

## Overall Assessment

**Updated count (2026-04-03):** 12 FAITHFUL, 12 DOCUMENTED, 8 HONEST, 1 APPROXIMATION, 1 N/A.

### FAITHFUL implementations (exact paper equations):

| Module | Paper | Equation |
|---|---|---|
| spreading_activation.py | Collins & Loftus 1975 | BFS spreading + convergent summation |
| titans_memory.py | Behrouz et al. NeurIPS 2025 | M_t = M_{t-1} - S_t, S_t = eta*S_{t-1} - theta*grad |
| synaptic_plasticity_hebbian.py | BCM 1982, Bi&Poo 1998 | phi(c, theta_m) = c*(c-theta_m); A+*exp(-dt/tau+) |
| synaptic_plasticity.py | Tsodyks-Markram 1997 | u_new = u + U*(1-u), x_new = x - u_eff*x |
| decay_cycle.py | ACT-R (Anderson & Lebiere 1998) | B_i = ln(n) - d*ln(L), d=0.5 |
| emotional_tagging.py | Yerkes-Dodson 1908 | f(a) = c*a*exp(-b*a) smooth inverted-U |
| dendritic_computation.py | Poirazi 2003 | Sigmoid s(n) + soma g(x) from Neuron Fig 3 |
| homeostatic_plasticity.py | Tetzlaff 2011, BCM 1982 | Eq.3 multiplicative + quadratic phi |
| separation_core.py | Leutgeb 2007, Rolls 2013 | Sparsity 4% from DG granule cell data |
| two_stage_transfer.py | Ketz 2023 (C-HORSE) | Cortical learning rate 0.02 |
| neuromodulation_channels.py (DA) | Rescorla-Wagner 1972, Schultz 1997 | delta = actual - V(s); DA = 1+delta in [0,3] |
| engram.py (half-life) | Rashid et al. 2016 | E(t) = E0 * 2^(-t/6h) |

### Critical architectural fix: Permastore (2026-04-01)

**Problem**: All memories decayed to zero heat and were marked `is_stale=TRUE` permanently — destroying the persistent memory system.

**Root cause**: `cascade_stages.py` defined decay multipliers and stages, but `decay_cycle.py` never used them. The PG `decay_memories()` function marked ALL low-heat memories as stale regardless of consolidation stage.

**Fix**: Three changes grounded in published research:

1. **Heat floor by consolidation stage** (cascade_stages.py):
   - CONSOLIDATED: floor = 0.10 (Bahrick 1984, Benna & Fusi 2016, Kandel 2001)
   - LATE_LTP: floor = 0.05
   - LABILE/EARLY_LTP: floor = 0.0

2. **Stage-adjusted decay wired into decay_cycle.py**:
   - `compute_stage_adjusted_decay()` now called for every memory
   - Consolidated memories decay at 0.5x rate

3. **PG `decay_memories()` respects consolidation stage**:
   - Only LABILE/EARLY_LTP memories can be marked stale
   - CONSOLIDATED/LATE_LTP memories enforce heat floor in SQL

### Changelog

**2026-07-01 (Doc reconciliation):**
- Detailed per-module sections regenerated to match current code. They had drifted to the
  pre-2026-04-01 state (old METAPHOR/FAKE labels, superseded citations e.g. Titans-only
  thermodynamics, piecewise-linear Yerkes-Dodson, cascade imp>0.6) while the Summary Table
  tracked the code. Each section's verdict now equals its Summary-Table row. **No code was
  changed by this regeneration.**
- Companion doc-alignment fixes applied same day (code docstrings + `.bib` + cortex-viz),
  logged in `docs/provenance/reconciliation-report.md`: half-life figures (14.9h/380.9h at
  default confidence), Yerkes-Dodson→Hebb 1955 attribution, Tsodyks-Markram τ-ratio
  inversion, DA [0,3] range comment, C-HORSE transfer-rate label, Luboeinski venue, and
  LongMemEval/LoCoMo `.bib` metadata.

**2026-04-03 (Wave 2):**
- `neuromodulation_channels.py` DA channel: R-W equation verified faithful. Schultz firing
  rate claim fixed (was "40Hz baseline, 80Hz burst" → now "5Hz baseline, 20-30Hz burst").
  DA ceiling widened [0,2]→[0,3] for asymmetric biology. NE/ACh/5-HT remain HONEST.
- Summary table fully synchronized with code state (was stale since 2026-04-01).
- Reclassified: 12 FAITHFUL, 12 DOCUMENTED, 8 HONEST, 1 APPROXIMATION, 1 N/A.

**2026-04-01 (Wave 1):**
- All 12 METAPHOR modules addressed: false citations removed, honest documentation added.
- 5 new FAITHFUL: titans_memory, BCM quadratic, Tsodyks-Markram, ACT-R, Yerkes-Dodson.
- 4 promoted: dendritic_computation, homeostatic_plasticity, separation_core, two_stage_transfer.
- Permastore fix: consolidated memories no longer decay to zero (Bahrick 1984).

**2026-03-31 (Initial audit):**
- First complete audit of 33 modules: 1 FAITHFUL, 19 APPROXIMATION, 9 METAPHOR.

### Remaining work

- `reranker.py`: Platt sigmoid attempted and REJECTED (2026-04-03). Hand-tuned sigmoid
  regressed BEAM -0.148 MRR and LoCoMo -5.1pp R@10. Proper calibration would require
  collecting (max_CE, is_correct) pairs from benchmarks and fitting via logistic regression.
  Binary gate is empirically optimal for now.
