---
title: "ADR-0226 — mcp_server/core/procedural_memory.py rationale"
status: accepted
source: mcp_server/core/procedural_memory.py
---

# ADR-0226 — mcp_server/core/procedural_memory.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Cortex is otherwise a *declarative* memory system (episodic events + semantic
knowledge, retrieved by content similarity). This module adds the missing
*non-declarative* system: procedural memory, the basal-ganglia analog that
stores **how to act** rather than **what is true**, and is retrieved by
*situation* rather than by content.
````

## module — original line 9 (docstring)

````text
Neuroscience basis (all three DOIs verified against Crossref: authors, title,
journal, volume, pages, year confirmed):
  - Graybiel (2008), "Habits, rituals, and the evaluative brain," Annu. Rev.
    Neurosci. 31:359-387 (doi:10.1146/annurev.neuro.29.051605.112851). The
    basal ganglia *chunk* repeated action sequences into unified habit units;
    a behaviour becomes habitual only after repetition. Here: recurring
    contiguous tool-use subsequences are mined into skill "chunks," and a skill
    graduates from goal-directed to habitual after a repetition threshold.
  - Doya (2000), "Complementary roles of basal ganglia and cerebellum in
    learning and motor control," Curr. Opin. Neurobiol. 10:732-739
    (doi:10.1016/S0959-4388(00)00153-7). The basal ganglia implement
    reinforcement learning, distinct from declarative memory.
  - Schultz, Dayan & Montague (1997), "A neural substrate of prediction and
    reward," Science 275:1593-1599 (doi:10.1126/science.275.5306.1593).
    Dopamine encodes a reward-prediction error. Here: each execution of a skill
    carries an outcome (success / failure); proficiency is a reinforced running
    success rate — the reward signal that strengthens or weakens the habit.
````

## module — original line 27 (docstring)

````text
Scope / honesty note (zetetic standard, matching dual_store_cls.py): this is a
frequent-subsequence miner plus a reinforced success-rate estimator. It is
*conceptually aligned* with basal-ganglia chunking and RL, but the mechanism is
sequence mining and running averages, not a neural actor-critic. The papers
motivate the design; they are not implemented as computational models.
````

## module — original line 33 (docstring)

````text
Boundary with declarative memory: procedural skills are stored with
``store_type='procedural'`` (the memories table's ``store_type`` column is free
text, already indexed — no schema migration) and are retrieved by
``match_skills`` against the *current situation* (domain, directory, recent
tools), never by embedding similarity to content. That situational-vs-content
retrieval split is the defining distinction from episodic/semantic memory.
````

## module — original line 40 (docstring)

````text
Pure business logic — no I/O. Handlers pass in already-fetched session
evidence (the same ``tools_used`` that ``auto_task_record`` already collects)
and persist the returned skill records.

````

## ActionStep — original line 96 (docstring)

````text
    ``tool`` is the tool/verb name (e.g. ``"edit_file"``). ``target_kind`` is an
    optional coarse object class (e.g. ``"test"``, ``"config"``) so a skill can
    generalize across specific files while still distinguishing "edit a test"
    from "edit a config". ``None`` means unspecified / any target.
    
````

## action_step_key — original line 109 (docstring)

````text
    A free function, not a method: mutmut categorically excludes the body
    of any `@dataclass`-decorated class (`mutmut/mutation/file_mutation.py:
    236`), so logic placed on `ActionStep` methods would carry zero mutation
    coverage no matter how the test loader names the module (issue #262 3rd
    pass; issue #282).
    
````

## ProceduralSkill — original line 122 (docstring)

````text
    Persistence maps onto the memories table (``store_type='procedural'``):
      - ``occurrences``      -> access_count
      - ``success_count``    -> useful_count
      - ``proficiency``      -> a reinforced running success rate (see update)
      - ``is_habitual``      -> consolidation_stage graduation (label only)
    The record is content-addressed by ``skill_id`` (a hash of the action
    sequence) so the same procedure mined in different sessions merges rather
    than duplicating.
    
````

## procedural_skill_is_habitual — original line 149 (docstring)

````text
    A free function, not a method — see `action_step_key`'s docstring for
    why (issue #282).
    
````

## _skill_priority — original line 339 (docstring)

````text
    Longer chunks that recur and succeed are the most valuable procedures;
    support is dampened (log) so a very common 2-step pair doesn't dominate a
    reliable 5-step routine.
    
````

## reinforce — original line 370 (docstring)

````text
    ``proficiency <- proficiency + alpha * (reward - proficiency)`` — a
    delta-rule / TD(0) update where ``reward - proficiency`` is the
    reward-prediction error (Schultz 1997). Success and failure counters and
    occurrence count are advanced. Returns a new updated skill (skills are
    treated as values; the caller persists the result).
    
````

## match_skills — original line 430 (docstring)

````text
    Scores each stored skill by context overlap x proficiency x support, filters
    out unreliable skills (proficiency below ``min_proficiency``), and returns
    the top ``top_k`` as ``{skill, score, why}`` dicts. This is procedural
    *recall*: "in this situation, the routine that usually works is X."
    
````

## module — original line 70 (comment)

````text
# Reinforcement learning rate for the proficiency running-average update
# (Rescorla-Wagner / TD style: p <- p + alpha * (reward - p)). Small so a
# single bad run doesn't erase an established habit.
````

## module — original line 75 (comment)

````text
# Laplace smoothing prior for the initial proficiency estimate, so a skill seen
# once successfully doesn't read as certain.
````

## module — original line 80 (comment)

````text
# Reward at or above this counts a run as a success.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 85 (comment)

````text
# Context-similarity score at or above this counts as a context match.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 382 (comment)

````text
# On the very first observation, seed from the smoothed prior instead of
# from 0 so a first success lands at a sensible level.
````

## module — original line 451 (comment)

````text
# Context overlap (Jaccard); 0.5 baseline when the skill is context-free
# so a globally useful routine can still surface.
````
