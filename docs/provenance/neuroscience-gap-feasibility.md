# Cortex Gap → Paper → Feasibility Mapping

Companion to `neuroscience-gap-analysis.md`. For each missing/partial
subsystem, this maps: **(1)** the neuroscience that establishes the mechanism,
**(2)** a computational/AI result showing it is *already implementable*, and
**(3)** the concrete build path using existing Cortex hooks.

**Citation discipline:** every DOI below was verified against Crossref in this
session (author, title, journal, year, volume, pages all confirmed). No
bibliographic field is written from memory. Where a claim is an engineering
inference rather than a cited result, it is marked *(design inference)*.

Legend: 🧠 = neuroscience basis · 🤖 = computational feasibility · 🔧 = Cortex build path

---

## A. Higher cognitive control

### A1 — Central executive / attentional control  *(MISSING)*
🧠 Baddeley (2003), "Working memory: looking back and looking forward,"
*Nat. Rev. Neurosci.* 4:829–839, doi:10.1038/nrn1201 — the central executive
as an attentional-control system over working memory. Posner & Petersen (1990),
"The attention system of the human brain," *Annu. Rev. Neurosci.* 13:25–42,
doi:10.1146/annurev.ne.13.030190.000325 — attention as a separable network with
a selective "spotlight."
🤖 Feasibility is essentially settled: content-based attention over a memory
set is the transformer mechanism itself (query-weighted soft selection). A
learned top-down weighting over the working set is a softmax over
relevance scores — standard, cheap, deterministic.
🔧 Add an attention-allocation pass over `sensory_buffer` contents: score each
buffered item against the current task/query, softmax-weight, and expose the
top-weighted subset as "in focus" to retrieval fusion. Capacity ceiling
(Cowan 4±1) already lives in `metacognition.py`. *(design inference for the
Cortex wiring; the mechanism itself is standard.)*

### A2 — Conflict monitoring / cognitive control  *(MISSING)*
🧠 Botvinick, Braver, Barch, Carter & Cohen (2001), "Conflict monitoring and
cognitive control," *Psychol. Rev.* 108:624–652, doi:10.1037/0033-295X.108.3.624
— ACC detects response conflict and signals PFC to raise control. Miller &
Cohen (2001), "An integrative theory of prefrontal cortex function,"
*Annu. Rev. Neurosci.* 24:167–202, doi:10.1146/annurev.neuro.24.1.167.
🤖 Conflict = measurable disagreement among retrieved items; the Botvinick
model operationalizes it as Hopfield-energy/entropy over competing units — a
scalar you can compute directly from retrieval scores.
🔧 A conflict-monitor pass over the retrieved set: compute score entropy /
pairwise contradiction, and when high, route to `claim_resolver.py` (already
present) and down-weight the losing memory. The monitor is new; the resolver
exists.

### A3 — Goal / task-set maintenance  *(PARTIAL)*
🧠 Miller & Cohen (2001) (above) — PFC holds an active task-set that biases
processing in posterior regions toward goal-relevant information.
🤖 A persistent goal/task embedding that conditions downstream weighting is
standard practice (task-conditioned retrieval, prompt/goal vectors).
🔧 Promote `prospective.py`'s trigger model into a sustained goal vector that
re-weights the write gate and fusion weights while active. *(design inference.)*

---

## B. Procedural / non-declarative memory  — the largest functional gap

### B1 — Procedural memory / habit learning  *(MISSING)*
🧠 Graybiel (2008), "Habits, rituals, and the evaluative brain,"
*Annu. Rev. Neurosci.* 31:359–387, doi:10.1146/annurev.neuro.29.051605.112851 —
basal-ganglia chunking of action sequences into habits. Doya (2000),
"Complementary roles of basal ganglia and cerebellum in learning and motor
control," *Curr. Opin. Neurobiol.* 10:732–739,
doi:10.1016/S0959-4388(00)00153-7 — BG = reinforcement learning, distinct from
declarative memory.
🤖 Reinforcement learning is a mature computational field; sequence-chunking
into reusable skills (options / hierarchical RL) is well established. An
agent-memory instantiation: mine recurring successful tool-use sequences and
store them as callable procedures.
🔧 `auto_task_record.py` already logs task executions — add a miner that
extracts recurring successful action sequences and stores them as
procedural entries retrievable by context, separate from the declarative
store. DA-RPE (below) supplies the reinforcement signal. *(design inference on
the Cortex path; RL/chunking itself is standard.)*

### B2 — Reinforcement-learning value layer / credit assignment  *(PARTIAL)*
🧠 Schultz, Dayan & Montague (1997), "A neural substrate of prediction and
reward," *Science* 275:1593–1599, doi:10.1126/science.275.5306.1593 — dopamine
encodes a temporal-difference reward-prediction error.
🤖 Mnih et al. (2015), "Human-level control through deep reinforcement
learning," *Nature* 518:529–533, doi:10.1038/nature14236 — TD-error learning of
a value function at scale; the exact signal Cortex already computes
(`compute_dopamine_rpe`) but does not yet use for value.
🔧 Cortex computes DA-RPE but only modulates LTP rate. Add an outcome-tagged
value term: memories/actions that contributed to successful sessions accrue
value and get retention/retrieval priority. The signal exists in
`coupled_neuromodulation.py`; the value store is new.

### B3 — Cerebellar forward models  *(MISSING; low AI priority)*
🧠 Wolpert, Miall & Kawato (1998), "Internal models in the cerebellum,"
*Trends Cogn. Sci.* 2:338–347, doi:10.1016/S1364-6613(98)01221-2.
🤖 Forward/inverse models are standard in control/model-based RL, but the
mapping to a text-memory system is weak. Listed for completeness; recommend
deferring.

---

## C. Specific declarative-memory phenomena

### C1 — Source / reality monitoring  *(MISSING — high value, low cost)*
🧠 Johnson, Hashtroudi & Lindsay (1993), "Source monitoring," *Psychol. Bull.*
114:3–28, doi:10.1037/0033-2909.114.1.3 — remembering *where* a memory came
from is a distinct, decision-based attribution process; its failure produces
confabulation.
🤖 Directly implementable as a classifier/gate over provenance features — the
same decision the human system makes ("perceived vs. imagined") maps onto
"observed vs. inferred," which Cortex already stores as an evidence tag.
🔧 A source-monitoring check at retrieval and write time that guards against
promoting an inferred memory to observed-source status. Provenance/evidence
fields already exist in the store; the decision layer is new. This directly
attacks hallucinated provenance — the highest-leverage cheap win.

### C2 — Recollection vs. familiarity (dual-process)  *(MISSING)*
🧠 Yonelinas (2002), "The nature of recollection and familiarity: a review,"
*J. Mem. Lang.* 46:441–517, doi:10.1006/jmla.2002.2864. Diana, Yonelinas &
Ranganath (2007), "Imaging recollection and familiarity in the medial temporal
lobe," *Trends Cogn. Sci.* 11:379–386, doi:10.1016/j.tics.2007.08.001 —
familiarity (perirhinal, fast, a-contextual) vs. recollection (hippocampal,
slow, contextual).
🤖 Two-stage retrieval is standard IR (cheap recall + expensive rerank).
Familiarity = a fast a-contextual similarity gate; recollection = full
contextual reconstruction — already the shape of Cortex's retrieve→rerank
pipeline.
🔧 Expose a lightweight familiarity signal (max vector similarity, no context
assembly) as an early triage before full recall in `recall_pipeline.py`.

### C3 — Retrieval-induced forgetting  *(PARTIAL)*
🧠 Anderson, Bjork & Bjork (1994), "Remembering can cause forgetting,"
*J. Exp. Psychol. Learn. Mem. Cogn.* 20:1063–1087,
doi:10.1037/0278-7393.20.5.1063 — retrieving one item suppresses related
competitors.
🤖 A retrieval event applying inhibition to neighbours is a local heat-field
update — computationally trivial given an existing neighbour graph.
🔧 On retrieval, apply a small heat penalty to non-retrieved neighbours in the
knowledge graph. `interference.py` handles encoding-side suppression; extend it
to the retrieval side. *(design inference.)*

### C4 — Context-dependent memory / encoding specificity  *(PARTIAL)*
🧠 Tulving & Thomson (1973), "Encoding specificity and retrieval processes in
episodic memory," *Psychol. Rev.* 80:352–373, doi:10.1037/h0020071 — retrieval
succeeds when cues overlap the encoding context.
🤖 Multi-dimensional context match is a straightforward feature addition to a
fusion scorer.
🔧 Add non-temporal context dimensions (project, tool, file, session valence)
as match features in retrieval fusion. `cognitive_map.py` already captures the
temporal dimension; generalize the context vector.

---

## D. Affective / physiological modulation

### D1 — Stress-hormone (glucocorticoid) modulation  *(MISSING)*
🧠 Roozendaal & McGaugh (2011), "Memory modulation," *Behav. Neurosci.*
125:797–824, doi:10.1037/a0026187 — adrenal stress hormones modulate
consolidation via the basolateral amygdala, an inverted-U on strength.
McGaugh (2000), "Memory — a century of consolidation," *Science* 287:248–251,
doi:10.1126/science.287.5451.248.
🤖 A scalar "stress" gain on consolidation strength is a one-parameter
modulation of the write/consolidation path.
🔧 Derive a session-stress signal (error rate, urgency markers, deadline
language) and scale consolidation strength/scope in `consolidation_engine.py`
along an inverted-U. Emotional-tagging arousal machinery is the template.
*(design inference.)*

### D2 — Mood-congruent retrieval  *(MISSING)*
🧠 Bower (1981), "Mood and memory," *Am. Psychol.* 36:129–148,
doi:10.1037/0003-066X.36.2.129 — current mood biases retrieval toward
similarly-valenced memories.
🤖 A valence prior on retrieval scoring is a single additive term.
🔧 Feed current-session valence (already computable via `emotional_tagging.py`)
as a soft retrieval prior. *(design inference.)*

---

## E. Non-associative & inhibitory learning

### E1 — Habituation & sensitization  *(MISSING — cheap, immediate payoff)*
🧠 Rankin et al. (2009), "Habituation revisited: an updated and revised
description of the behavioral characteristics of habituation," *Neurobiol.
Learn. Mem.* 92:135–138, doi:10.1016/j.nlm.2008.09.012 — the defining criteria
of the simplest form of learning (response decrement to repeated stimuli, plus
dishabituation/sensitization).
🤖 Habituation = a decaying novelty/response gain per repeated stimulus; a
few lines over a repeat counter. The Rankin criteria give a validated spec.
🔧 Add a habituation term to the write gate: progressively suppress repeated
low-salience identical inputs; a salient event transiently sensitizes the gate
for related inputs. `write_gate.py` + the novelty signal in
`predictive_coding_*` are the hosts. Directly reduces memory bloat.

### E2 — Fear extinction / inhibitory learning  *(MISSING)*
🧠 Bouton (2004), "Context and behavioral processes in extinction,"
*Learn. Mem.* 11:485–494, doi:10.1101/lm.78804 — extinction is *new inhibitory
learning*, not erasure (hence spontaneous recovery/renewal). Milad & Quirk
(2012), "Fear extinction as a model for translational neuroscience,"
*Annu. Rev. Psychol.* 63:129–151, doi:10.1146/annurev.psych.121208.131631 —
vmPFC-driven inhibitory control over the amygdala.
🤖 An inhibitory overlay that suppresses-without-deleting and can be reinstated
is a masking layer — standard, and it preserves reversibility.
🔧 "Deprecate" a learned association with a reversible inhibitory tag rather
than deleting it; `reconsolidation.py` + `active_forgetting.py` are the natural
hosts. *(design inference.)*

---

## F. Sleep architecture

### F1 — NREM/REM two-phase consolidation  *(PARTIAL)*
🧠 Diekelmann & Born (2010), "The memory function of sleep," *Nat. Rev.
Neurosci.* 11:114–126, doi:10.1038/nrn2762 — active systems consolidation:
NREM slow-wave replay transfers hippocampal→cortical; REM supports
integration/schema and emotional processing.
🤖 van de Ven, Siegelmann & Tolias (2020), "Brain-inspired replay for continual
learning with artificial neural networks," *Nat. Commun.* 11, art. 4069,
doi:10.1038/s41467-020-17866-2 — generative replay as an offline consolidation
phase in an ANN prevents catastrophic forgetting. Direct precedent that a
sleep-like replay phase is buildable and beneficial. McClelland, McNaughton &
O'Reilly (1995), "Why there are complementary learning systems…," *Psychol.
Rev.* 102:419–457, doi:10.1037/0033-295X.102.3.419 — the CLS rationale Cortex
already builds on.
🔧 Split the single `sleep_compute.py` pass into an NREM-like exact-replay
consolidation and a REM-like recombination/abstraction phase (host the latter
in `schema_engine.py`). The single pass already exists; this is a phase split.

### F2 — Sleep spindles / targeted memory reactivation  *(MISSING)*
🧠 Rasch, Büchel, Gais & Born (2007), "Odor cues during slow-wave sleep prompt
declarative memory consolidation," *Science* 315:1426–1429,
doi:10.1126/science.1138581 — cueing during sleep selectively reactivates and
strengthens the cued memories (TMR).
🤖 Cue-directed replay = filter the replay set by a cue before the offline
pass; trivial given an existing replay selector.
🔧 Let a flagged topic/cue bias `replay_selection.py` so related memories
preferentially reconsolidate on the next offline pass.

---

## G. Binding

### G1 — Feature binding  *(MISSING; mostly handled structurally)*
🧠 Treisman (1996), "The binding problem," *Curr. Opin. Neurobiol.* 6:171–178,
doi:10.1016/S0959-4388(96)80070-5.
🤖 Relational binding is already provided by the knowledge graph's typed edges;
a synchrony-based binding mechanism adds little for a text store. Low priority.

---

## Priority table (feasibility × AI value)

| Rank | Gap | Neuro anchor | Feasibility anchor | Cortex host |
|---|---|---|---|---|
| 1 | B1 Procedural/skill | Graybiel 2008; Doya 2000 | RL/options (mature) | `auto_task_record.py` |
| 2 | C1 Source monitoring | Johnson 1993 | provenance classifier | evidence fields (exist) |
| 3 | A1 Central executive | Baddeley 2003; Posner 1990 | attention softmax | `sensory_buffer` + `metacognition` |
| 4 | B2 RL value layer | Schultz 1997 | Mnih 2015 (DQN) | `coupled_neuromodulation` (DA-RPE) |
| 5 | E1 Habituation | Rankin 2009 | repeat-gain decay | `write_gate.py` |
| 6 | F1 NREM/REM sleep | Diekelmann 2010; McClelland 1995 | van de Ven 2020 (replay) | `sleep_compute` + `schema_engine` |
| 7 | C2 Recollection/familiarity | Yonelinas 2002; Diana 2007 | 2-stage IR | `recall_pipeline.py` |
| 7 | A2 Conflict monitoring | Botvinick 2001 | entropy/energy over scores | `claim_resolver.py` |
| 8 | D1 Stress modulation | Roozendaal 2011; McGaugh 2000 | scalar gain | `consolidation_engine.py` |
| 8 | D2 Mood-congruent | Bower 1981 | valence prior | `emotional_tagging.py` |
| 8 | C3 Retrieval-induced forgetting | Anderson 1994 | neighbour heat penalty | `interference.py` |
| 8 | C4 Context reinstatement | Tulving & Thomson 1973 | context-match features | `cognitive_map.py` |
| 8 | E2 Extinction | Bouton 2004; Milad 2012 | reversible inhibitory tag | `reconsolidation.py` |
| 8 | F2 Spindle/TMR | Rasch 2007 | cue-filtered replay | `replay_selection.py` |
| 9 | B3 Cerebellar models | Wolpert 1998 | model-based control | (defer — weak AI mapping) |
| 9 | G1 Feature binding | Treisman 1996 | graph edges (present) | knowledge graph (defer) |

---

*All DOIs verified against Crossref in-session. One initially-considered
reference (a Kumaran/Hassabis CLS-update paper) was dropped because the DOI I
had resolved to an unrelated article — the CLS rationale is instead anchored to
the verified McClelland et al. 1995. AI-feasibility anchors are cited where a
published computational result exists (Mnih 2015 for RL value; van de Ven 2020
for replay); items marked "design inference" are engineering paths where the
underlying mechanism is standard practice rather than a single citable result.*
