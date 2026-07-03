# Cortex Neuroscience Coverage & Gap Analysis

**Question:** which parts of human-brain memory/cognition are *missing* from
Cortex, that could plausibly apply to an AI memory system?

**Method:** inventoried all 163 `mcp_server/core/*.py` modules and grepped
docstrings for each candidate subsystem. Each row below is marked **Present**
(a module implements it), **Partial** (a related mechanism exists but a
specific piece is absent), or **Missing** (no implementation). "Missing" means
*not found in code* — verified by grep, not asserted from memory.

The headline: Cortex is already an unusually complete brain-inspired stack.
The gaps are real but they are mostly *higher cognitive control* and a few
specific memory phenomena — not the core encoding/consolidation/retrieval
machinery, which is thoroughly covered.

---

## Part 1 — What Cortex already has (so we don't propose it as "missing")

| Human-brain subsystem | Cortex module(s) | Basis |
|---|---|---|
| Sensory/working buffer (pre-consolidation) | `sensory_buffer.py` | bounded ring buffer, drains to LTM |
| Working-memory capacity limit | `metacognition.py` | Cowan's 4±1 chunk limit |
| Forgetting curve / decay | `thermodynamics.py`, `decay_cycle.py` | Ebbinghaus |
| Systems consolidation (hippocampus→cortex) | `two_stage_transfer.py`, `dual_store_cls.py`, `consolidation_engine.py` | C-HORSE / CLS |
| Sleep replay (SWR, dream replay) | `replay.py`, `sleep_compute.py`, `replay_*.py` | hippocampal replay |
| Theta/gamma/SWR oscillatory gating | `oscillatory_phases.py`, `oscillatory_clock.py` | Hasselmo 2002 |
| Pattern separation / completion | `pattern_separation.py`, `separation_core.py`, `hopfield.py` | DG separation, attractor completion |
| Adult neurogenesis (temporal context) | `neurogenesis.py` | DG hyperexcitable young neurons |
| Reconsolidation (labile-on-retrieval) | `reconsolidation.py` | Nader 2000 |
| Synaptic tagging & capture | `synaptic_tagging.py` | Frey & Morris |
| Hebbian / STDP plasticity | `synaptic_plasticity*.py` | Bi & Poo |
| Homeostatic plasticity + metaplasticity | `homeostatic_plasticity.py` | Turrigiano scaling, BCM/Abraham-Bear sliding threshold |
| Tripartite (astrocyte) synapse | `tripartite_synapse.py`, `tripartite_calcium.py` | glial modulation |
| Microglial synaptic pruning | `microglial_pruning.py` | complement-tagged pruning |
| Neuromodulation (DA/NE/ACh/5-HT) | `coupled_neuromodulation.py`, `neuromodulation_channels.py` | Doya 2002, Schultz DA-RPE |
| Emotional tagging (arousal × priority) | `emotional_tagging.py` | Qasim 2023 + Hebb 1955 inverted-U |
| Interference / active forgetting | `interference.py`, `active_forgetting.py` | orthogonalization, DAn forgetting |
| Spreading activation (semantic priming) | `spreading_activation.py` | Collins & Loftus 1975 |
| Cognitive map / spatial navigation | `cognitive_map.py` | Successor Representation |
| Predictive coding / write-gating | `hierarchical_predictive_coding.py`, `predictive_coding_*.py`, `write_gate.py` | Friston free-energy |
| Episodic→semantic gisting | `gist_extraction.py`, `schema_engine.py` | schema abstraction |
| Prospective memory (future intentions) | `prospective.py` | trigger-on-context |
| Metacognition / confidence / abstention | `metacognition.py`, `abstention_gate.py` | coverage + gap detection |
| Engram allocation | `engram.py` | — |
| Hyperdimensional / sparse coding | `hdc_encoder.py`, `sparse_dictionary*.py` | VSA, sparse dictionary |

That is most of the canonical memory neuroscience. The gaps below are what
remains.

---

## Part 2 — Missing / partial subsystems (the actual deliverable)

Ordered by how directly each maps onto an AI memory system's function —
most actionable first.

### A. Higher cognitive control (the biggest genuine gap)

**A1. Central executive / attentional control — MISSING.**
Cortex has a working-memory *buffer* (`sensory_buffer`) and a *capacity limit*
(Cowan 4±1), but no **central executive** — no top-down attentional weighting
that decides *what in the buffer to operate on now*. Biologically this is the
prefrontal-parietal attention network (Baddeley's central executive, Posner's
attentional spotlight). For AI: an explicit attention-allocation layer over the
working set — which retrieved memories get "focused" and amplified for the
current step vs. held in the background. Note: `hopfield.py` *does* use softmax
**attention** — but as a content-addressable *retrieval* mechanism (Modern
Hopfield: `softmax(β·Xᵀq)`), not as top-down attentional *control* over a
working set. The gap is the executive/control function, not attention as a
compute primitive.

**A2. Cognitive control / conflict monitoring — PARTIAL.**
`claim_resolver.py` *resolves* contradictions among claims (conflict
resolution), and `interference.py` orthogonalizes overlapping memories — so
conflict *handling* exists. What is missing is the anterior-cingulate–style
*monitoring* half: a metric that continuously scores conflict/entropy over the
retrieved set and *triggers* extra control when it is high, the way ACC signals
PFC. For AI: a conflict-monitor pass that computes retrieval-set disagreement
and escalates to the existing resolver. The resolver is present; the monitor
that gates it is the gap.

**A3. Goal/task-set maintenance — PARTIAL.**
`prospective.py` fires intentions on context match, but there is no
*sustained goal representation* that biases retrieval and gating toward the
current task the way PFC task-sets do. For AI: a task-set vector that
re-weights the write gate and retrieval fusion while a goal is active.

### B. Procedural / non-declarative memory (a whole memory system, largely absent)

**B1. Procedural memory / habit learning — MISSING.**
Cortex is almost entirely a **declarative** (episodic+semantic) system. The
basal-ganglia / corticostriatal **procedural** system — skills and habits
learned by repetition, stored as action policies rather than facts — has no
analog. `coupled_neuromodulation.py` has DA-RPE (the *signal* that would drive
it) but no actor-critic / policy structure that consumes it. For AI: learning
*procedures* (recurring successful action sequences / tool-use patterns) as
reusable skills, distinct from remembering facts. This is arguably the single
most useful missing piece for an agent memory system.

**B2. Reinforcement-learning value layer — PARTIAL.**
DA prediction-error is computed (`compute_dopamine_rpe`) but only modulates LTP
*rate*. There is no **value function / credit assignment** that learns which
memories or actions led to good outcomes and biases future retrieval toward
them. For AI: an outcome-tagged value signal so memories that contributed to
successful sessions are preferentially retained and surfaced.

**B3. Cerebellar forward models — MISSING.**
No supervised error-correction / internal-forward-model analog (cerebellum).
Less obviously applicable to a text-memory system; listed for completeness.

### C. Specific declarative-memory phenomena not yet modelled

**C1. Source monitoring / reality monitoring — MISSING.**
No tracking of *where a memory came from* (self-generated vs. external, which
session, inferred vs. observed) as a first-class retrieval-time check. The
memory store has provenance fields, but there is no **source-monitoring
decision** that guards against confabulation — attributing an inferred fact to
an observed source. For AI this is directly valuable: it is the mechanism that
separates "the user told me X" from "I concluded X," reducing hallucinated
provenance. High-value, low-cost gap.

**C2. Recollection vs. familiarity (dual-process retrieval) — MISSING.**
Retrieval returns scored hits but does not distinguish **recollection**
(vivid, contextual, hippocampal) from **familiarity** (a-contextual "I've seen
this" signal, perirhinal). For AI: a fast familiarity gate ("have I seen
anything like this?") before a full contextual recall — cheaper triage.

**C3. Retrieval-induced forgetting / retrieval competition — PRESENT
(correction).** An earlier draft listed this as partial; a corrected grep
shows `interference.py` explicitly cites Anderson (Psychological Review
114:887–953) and implements competitor suppression via contrastive Hebbian
learning ("strong competitors suppress weak ones"). RIF is implemented. Any
residual work is tuning the retrieval-side neighbour penalty, not building the
mechanism.

**C4. Context-dependent memory / encoding specificity — PARTIAL.**
`cognitive_map.py` (Successor Representation) captures temporal co-access, and
recency signals exist, but there is no explicit **encoding-specificity /
context-reinstatement** mechanism (Tulving) — retrieval boosted when the
current context matches the encoding context along non-temporal dimensions
(project, tool, file, mood). For AI: multi-dimensional context match at
retrieval, beyond vector+recency.

### D. Affective/physiological depth (thin, but the hooks exist)

**D1. Stress-hormone (glucocorticoid) modulation — MISSING.**
Emotional tagging models arousal×priority, but not the **cortisol/adrenaline
inverted-U on consolidation** (McGaugh): acute stress *strengthens*
consolidation of central details while impairing peripheral ones, and chronic
stress impairs retrieval. For AI: a session-level "stress" signal (error rate,
urgency, deadline pressure) that modulates consolidation strength and scope.

**D2. Mood-congruent retrieval — PRESENT (correction).**
An earlier draft listed this as missing; a corrected grep shows `pg_recall.py`
implements a `MOOD_CONGRUENT_RERANK` / `EMOTIONAL_RETRIEVAL` stage explicitly
citing "Bower 1981 mood-congruent recall," with an ablation switch
(`Mechanism.MOOD_CONGRUENT_RERANK`). Current-session valence already biases
retrieval toward similarly-valenced memories. Implemented.

**D3. Dimensional vs. discrete emotion — PARTIAL/known.**
`emotional_tagging.py` reduces to valence+arousal from a fixed 6-emotion
backend set. A richer appraisal-theory model (not just valence/arousal) is a
possible extension; already noted in the audit as an intentional scoping choice.

### E. Non-associative & developmental learning

**E1. Habituation & sensitization — PARTIAL (correction).**
An earlier draft listed this as missing; a corrected grep shows
`neuromodulation_channels.py` implements **NE-channel habituation** (repeated
stressors reduce response, `NE_HABITUATION_RATE = 0.05`, tonic-baseline
return). So habituation *of the noradrenergic arousal signal* exists. What is
not yet present is habituation applied at the **write gate** — progressively
suppressing repeated identical low-value *content* (memory-bloat reduction) —
nor an explicit sensitization/dishabituation term. For AI: extend the existing
habituation concept from the NE channel to the write gate over repeated inputs.

**E2. Fear extinction / inhibitory learning — PARTIAL (correction).**
An earlier draft listed this as missing; a corrected grep shows
`reconsolidation.py` has an **EXTINCTION regime** (on high prediction-mismatch:
"archive old memory, create new one"). So an extinction *pathway* exists — but
it is modelled as **archive-and-replace**, not as Bouton's *new inhibitory
learning* that suppresses-without-deleting and permits spontaneous
recovery/renewal. For AI: add a reversible inhibitory overlay so a deprecated
association is masked (and can reinstate) rather than archived. The regime hook
exists; the inhibitory-learning semantics are the gap.

**E3. Critical/sensitive periods — MISSING (likely N/A).**
Developmental plasticity windows; little obvious AI mapping. Listed for
completeness.

### F. Sleep architecture depth

**F1. Sleep stages (NREM/REM cycling) — PARTIAL.**
`sleep_compute.py` does a single "dream replay" consolidation pass. Biology
cycles **NREM** (slow-wave: systems consolidation, sharp-wave ripples) and
**REM** (schema integration, creative recombination, emotional
depotentiation). For AI: a two-phase offline cycle — an NREM-like exact-replay
consolidation and a REM-like recombination/abstraction phase — rather than one
pass. `sleep_compute` + `schema_engine` are the natural hosts.

**F2. Sleep spindles / targeted memory reactivation — MISSING.**
No spindle-analog gating of *which* memories replay, nor cue-triggered targeted
reactivation. For AI: cue-directed replay (reconsolidate memories related to a
flagged topic on the next offline pass).

### G. Binding & multi-modal (structural)

**G1. Feature binding / the binding problem — PRESENT (correction).**
An earlier draft listed this as missing; a corrected grep shows
`oscillatory_phases.py` implements **gamma binding** explicitly
(`gamma_binding_strength()`, "7-item binding per theta cycle," citing Lisman &
Jensen 2013), on top of the knowledge graph's relational binding. Both the
synchrony-analog and the structural binding exist. No gap.

---

## Part 3 — Recommended priority (for an AI memory system specifically)

Ranked by value-to-AI × implementability, using existing Cortex hooks:

1. **Procedural memory / skill learning (B1)** — biggest functional gap;
   turns an episodic store into one that also learns *how to act*. Hooks:
   `auto_task_record.py`, DA-RPE already present.
2. **Source/reality monitoring (C1)** — directly attacks confabulated
   provenance; cheap; provenance fields already exist.
3. **Central executive / attentional control (A1)** — focus weighting over the
   working set; buffer + capacity limit already there.
4. **Outcome-value / RL credit assignment (B2)** — retain what *worked*; DA-RPE
   signal already computed, needs a value layer.
5. **Habituation at the write gate (E1, extend)** — NE-channel habituation
   already exists; extend it to suppress repeated low-value *content*. Cheap
   bloat reduction.
6. **NREM/REM two-phase sleep (F1)** — split the existing single consolidation
   pass; `sleep_compute` + `schema_engine` host it.
7. **Recollection/familiarity triage (C2)** and **conflict monitoring (A2,
   the monitor half)** — retrieval-quality and safety refinements.
8. Stress modulation (D1), context reinstatement (C4), extinction
   *inhibitory-learning semantics* (E2, extend the existing archive regime),
   spindle-TMR (F2) — second wave.
9. Cerebellar forward models (B3), critical periods (E3) — low AI
   applicability; optional.

*Already implemented (removed from the gap list after a corrected grep):
mood-congruent retrieval (D2, Bower 1981 in `pg_recall.py`), retrieval-induced
forgetting (C3, Anderson in `interference.py`), gamma feature-binding (G1,
Lisman & Jensen 2013 in `oscillatory_phases.py`).*

---

*Grounding note & correction history: "Present" rows were confirmed against
actual modules. The first draft of the "Missing" rows used a grep whose
alternation was mis-escaped (`\|` inside `grep -E`, which matches a literal
pipe), so several concepts returned false "0 hits." A corrected re-grep (real
`-E` alternation, then reading the matched lines for context) reclassified five
items: **mood-congruent retrieval (D2), retrieval-induced forgetting (C3), and
gamma feature-binding (G1) are in fact PRESENT**; **habituation (E1) and
extinction (E2) are PARTIAL** (NE-channel habituation and an archive-style
extinction regime exist). The A1 note that "no attention" appears in core was
also wrong — `hopfield.py` uses softmax attention as a retrieval primitive; the
genuine A1 gap is attentional *control*, not attention as a primitive. The
remaining genuine gaps — procedural/skill store (B1), RL value layer (B2),
source monitoring (C1), central executive (A1), stress modulation (D1),
recollection/familiarity triage (C2), conflict-monitor (A2), context
reinstatement (C4), NREM/REM split (F1), spindle-TMR (F2), cerebellum (B3) —
were each confirmed absent by reading the matched lines, not by trusting a raw
hit count. This is a coverage map of the current `wip/da-active-forgetting`
branch, not a critique — the system is already more neuroscientifically
complete than most published memory architectures.*
