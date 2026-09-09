---
title: "ADR-0209 — mcp_server/core/neuromodulation_channels.py rationale"
status: accepted
source: mcp_server/core/neuromodulation_channels.py
---

# ADR-0209 — mcp_server/core/neuromodulation_channels.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Computes per-channel updates for the 4 neuromodulatory channels (DA, NE, ACh, 5-HT)
and their cross-coupling interactions.
````

## module — original line 6 (docstring)

````text
What Doya (2002) actually says:
  DA -> temporal discount factor (gamma in RL value estimation)
  NE -> inverse temperature in softmax policy (exploration/exploitation)
  ACh -> learning rate for value function updates
  5-HT -> time scale of reward prediction
````

## module — original line 12 (docstring)

````text
What this module implements (departures from Doya noted):
  DA: Reward prediction error signal (Rescorla & Wagner 1972; Schultz 1997).
      Rescorla-Wagner: delta_V = alpha_cs * beta_us * (lambda - V_total).
      In single-CS form: V(s) := V(s) + alpha*beta * (actual - V(s)).
      Current code uses combined alpha*beta = 0.1 (within standard simulation
      range [0.01-0.25]; Daw 2011, Sutton & Barto 1998).
      DA level = 1.0 + delta, clamped to [0.0, 3.0].
      Floor 0.0: DA neurons cannot fire below zero (Schultz 1997, Fig 1-3).
      Ceiling 3.0: baseline tonic ~5 Hz, phasic burst ~20-30 Hz (~4-6x
      baseline; Schultz 1997; Ljungberg et al. 1992; Mirenowicz & Schultz
      1994). Using 3x as conservative upper bound (full 5-6x would make
      positive RPE dominate downstream effects disproportionately).
      The actual-reward heuristic (0.7+importance*0.3 for positive, etc.) is
      an engineering translation — Schultz used juice rewards, not memory ops.
````

## module — original line 27 (docstring)

````text
  NE: Arousal/urgency with habituation.
      Inspired by Aston-Jones & Cohen (2005) tonic/phasic LC framework,
      simplified to burst/decay for hours timescale. Aston-Jones proposes
      tonic vs phasic LC modes driven by utility monitoring — a full
      implementation would require task-utility tracking. This code captures
      the qualitative behavior: errors trigger phasic bursts (attenuated by
      habituation), absence of errors returns to tonic baseline.
````

## module — original line 35 (docstring)

````text
  ACh: Encoding/retrieval mode from theta phase.
      FAITHFUL to Hasselmo (2005): high ACh during encoding, low during
      retrieval. Theta phase is externally provided.
````

## module — original line 39 (docstring)

````text
  5-HT: Exploration/exploitation from novelty vs schema match.
      Engineering translation of Dayan & Huys (2009) behavioral inhibition
      concept. Dayan & Huys show 5-HT opposes impulsive responding and
      promotes behavioral inhibition / exploitation of known structure.
      The direction is qualitatively correct: high novelty -> exploration
      (high 5-HT), high schema match -> exploitation (low 5-HT). The
      specific formula is an engineering approximation — no paper provides
      an equation mapping novelty/schema to 5-HT level.
````

## module — original line 48 (docstring)

````text
Cross-coupling: Engineering heuristic coupling. The directions are qualitatively
  plausible (high DA dampens NE per success reducing arousal, high NE boosts ACh
  per arousal enhancing encoding, high 5-HT dampens DA per inhibition reducing
  reward sensitivity, high ACh dampens 5-HT per encoding reducing exploration)
  but specific coupling constants are hand-tuned. No paper provides these
  equations or values.
````

## module — original line 55 (docstring)

````text
EMA rates: Ordered to reflect biological response timescales.
  ACH_ALPHA=0.4 — ACh closely tracks theta oscillations (fast, ~200ms cycle)
  DA_ALPHA=0.3  — DA RPE responses are rapid (~100ms phasic bursts, Schultz 1997)
  NE_ALPHA=0.2  — LC phasic responses are moderate (~seconds, Aston-Jones 2005)
  SER_ALPHA=0.15 — 5-HT changes slowly (minutes/hours, tonic modulation)
  The ordering matches biology; absolute values are hand-tuned for this system's
  per-operation update cadence (hours timescale, not milliseconds).
````

## module — original line 63 (docstring)

````text
References:
    Rescorla RA, Wagner AR (1972) A theory of Pavlovian conditioning:
        Variations in the effectiveness of reinforcement and nonreinforcement.
        In: Black AH, Prokasy WF (Eds.), Classical Conditioning II, pp. 64-99.
        (RPE equation: delta_V = alpha * beta * (lambda - V_total))
    Schultz W (1997) A neural substrate of prediction and reward.
        Science 275:1593-1599 (DA firing rate data: ~5 Hz tonic, ~20-30 Hz burst)
    Schultz W, Dayan P, Montague PR (1997) A neural substrate of prediction
        and reward. Science 275:1593-1599 (TD error: delta = r + gamma*V(s') - V(s);
        this code uses R-W not TD — appropriate for discrete memory operations)
    Doya K (2002) Metalearning and neuromodulation.
        Neural Networks 15:495-506 (framework inspiration, not faithfully implemented)
    Aston-Jones G, Cohen JD (2005) An integrative theory of locus
        coeruleus-norepinephrine function. Annu Rev Neurosci 28:403-450
        (tonic/phasic concept; full model not implemented)
    Hasselmo ME (2005) What is the function of hippocampal theta rhythm?
        Hippocampus 15:936-949
    Dayan P, Huys QJM (2009) Serotonin in affective control.
        Annu Rev Neurosci 32:95-126 (behavioral inhibition concept;
        no specific equation implemented)
````

## module — original line 84 (docstring)

````text
Pure business logic — no I/O.

````

## compute_dopamine_rpe — original line 122 (docstring)

````text
Rescorla-Wagner RPE (Rescorla & Wagner 1972; Schultz 1997).
````

## compute_dopamine_rpe — original line 129 (docstring)

````text
    Combined alpha*beta = 0.1 — hand-tuned within standard simulation
    range [0.01-0.25] (Daw 2011, Sutton & Barto 1998). In R-W theory,
    alpha = CS salience, beta = US intensity; here they are merged since
    each memory operation has a single stimulus context.
````

## compute_dopamine_rpe — original line 134 (docstring)

````text
    Clamped to [0.0, 3.0]:
      Floor 0.0 — DA neurons cannot fire below zero (Schultz 1997).
      Ceiling 3.0 — conservative bound. Biology: baseline ~5 Hz, burst
      ~20-30 Hz = ~4-6x (Schultz 1997, Ljungberg et al. 1992). Using
      3x to avoid positive RPE dominating downstream modulation.
````

## compute_dopamine_rpe — original line 140 (docstring)

````text
    The actual-reward mapping (positive/negative/neutral -> numeric value)
    is an engineering translation of Schultz's juice/airpuff paradigm.
````

## compute_norepinephrine_arousal — original line 172 (docstring)

````text
Arousal model inspired by Aston-Jones & Cohen (2005) tonic/phasic LC framework.
````

## compute_norepinephrine_arousal — original line 178 (docstring)

````text
    Errors trigger phasic NE burst (attenuated by habituation, modeling
    repeated-stressor adaptation). Absence of errors decays NE toward tonic
    baseline (1.0). All numeric constants are hand-tuned.
````

## compute_serotonin_exploration — original line 202 (docstring)

````text
Exploration/exploitation signal — engineering translation of Dayan & Huys (2009).
````

## compute_serotonin_exploration — original line 204 (docstring)

````text
    Dayan & Huys show 5-HT opposes impulsive responding and promotes behavioral
    inhibition. This translates to: high schema match promotes exploitation
    (lower 5-HT), high novelty promotes exploration (higher 5-HT). The
    direction is qualitatively consistent with the paper; the specific formula
    and coefficients are engineering approximations.
````

## apply_cross_coupling — original line 230 (docstring)

````text
Linear additive cross-coupling — engineering heuristic.
````

## apply_cross_coupling — original line 232 (docstring)

````text
    Coupling directions are qualitatively plausible:
      DA dampens NE — success reduces arousal.
      NE boosts ACh — arousal enhances encoding.
      5-HT dampens DA — inhibition reduces reward sensitivity.
      ACh dampens 5-HT — encoding reduces exploration.
    Specific coupling constants are hand-tuned. No paper provides these
    equations or values.
````

## module — original line 89 (comment)

````text
# ── EMA rates for each channel ──────────────────────────────────────────
# Ordered by biological response speed. See module docstring for rationale.
````

## module — original line 97 (comment)

````text
# ── Cross-coupling strengths ────────────────────────────────────────────
# Engineering heuristic. Directions are qualitatively plausible but specific
# values are hand-tuned. No paper provides these coupling equations.
````

## module — original line 106 (comment)

````text
# ── Habituation constants ──────────────────────────────────────────────
# Engineering values for NE habituation (repeated stressors reduce response).
````

## module — original line 146 (comment)

````text
# Hand-tuned reward mapping — no paper provides this translation.
````

## module — original line 159 (comment)

````text
# Rescorla-Wagner: V(s) := V(s) + alpha*beta * (actual - V(s))
# Combined alpha*beta = 0.1 (hand-tuned, within standard range)
````

## inline — original line 249 (comment)

````text
# DA: asymmetric [0, 3] per Schultz 1997
````

## Additional source rationale — compute_norepinephrine_arousal

````text
    """Update arousal and adaptation from error feedback.
    
    source: ADR-0209
    
    Simplified to burst/decay for hours timescale. Aston-Jones proposes tonic vs
    phasic LC modes driven by utility monitoring — this code captures the
    qualitative behavior without the full utility-tracking model.
    
    source: ADR-0209
    
    Returns:
        (ne_level, updated_adaptation).
    """

````
