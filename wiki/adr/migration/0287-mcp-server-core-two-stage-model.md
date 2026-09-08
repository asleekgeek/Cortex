---
title: "ADR-0287 — mcp_server/core/two_stage_model.py rationale"
status: accepted
source: mcp_server/core/two_stage_model.py
---

# ADR-0287 — mcp_server/core/two_stage_model.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Models the McClelland et al. (1995) Complementary Learning Systems theory:
the hippocampus fast-binds episodic memories that are fragile and capacity-
limited, while the cortex slowly integrates semantic knowledge that is stable
and high-capacity. Transfer happens via replay-driven interleaved training.
````

## module — original line 8 (docstring)

````text
Hippocampal Store:
  - Fast binding (immediate): one-shot encoding
  - High interference: similar memories compete
  - Capacity-limited: only ~N active traces
  - Context-dependent: directory/domain required for retrieval
  - Decays fast without replay (labile -> lost)
````

## module — original line 15 (docstring)

````text
Cortical Store:
  - Slow integration (via SWR replay): many repetitions needed
  - Low interference: interleaved training prevents catastrophic forgetting
  - High capacity: no practical limit
  - Context-free: retrievable from any context
  - Very stable once formed (consolidated)
````

## module — original line 22 (docstring)

````text
Transfer protocol:
  1. Memory enters hippocampal store (fast bind, labile stage)
  2. During SWR replay: hippocampal trace activates cortical target
  3. Repeated replay gradually builds cortical representation
  4. Schema-consistent memories transfer faster (schema acceleration)
  5. Once cortical trace is strong: hippocampal version can release
````

## module — original line 29 (docstring)

````text
The hippocampal_dependency field in Memory tracks this:
  1.0 = fully hippocampal (just encoded, no cortical trace)
  0.5 = transitional (partial cortical trace, hippocampus still needed)
  0.0 = cortically independent (fully consolidated, hippocampus can release)
````

## module — original line 34 (docstring)

````text
Note: hippocampal_dependency is an engineering construct that combines the
qualitative CLS framework (McClelland 1995) with quantitative learning rates
from C-HORSE (Ketz et al., eLife 12:e77185, 2023). The original CLS paper
does not define a scalar "dependency" metric; we model it as the complement
of cortical trace strength, decaying via the cortical learning rate (0.02)
during replay-driven transfer.
````

## module — original line 41 (docstring)

````text
This integrates with:
  - cascade.py: consolidation stages track biochemical maturation
  - oscillatory_clock.py: SWR windows gate replay-driven transfer
  - schema_engine.py: schema match accelerates cortical integration
  - interference.py: hippocampal interference drives need for transfer
````

## module — original line 47 (docstring)

````text
References:
    McClelland JL, McNaughton BL, O'Reilly RC (1995) Why there are
        complementary learning systems. Psychol Rev 102:419-457
    Kumaran D, Hassabis D, McClelland JL (2016) What learning systems
        do intelligent agents need? Neuron 92:1258-1273
    Frankland PW, Bontempi B (2005) The organization of recent and
        remote memories. Nat Rev Neurosci 6:119-130
    Ketz NA, et al. (2023) C-HORSE: A computational model of hippocampal-
        cortical complementary learning. eLife 12:e77185
    Tse D, et al. (2007) Schemas and memory consolidation. Science 316:76-82
````

## module — original line 58 (docstring)

````text
Pure business logic — no I/O.

````

## module — original line 88 (comment)

````text
# Engineering choice. McClelland et al. (1995) discuss hippocampal capacity
# limits as a motivation for CLS but provide no specific number. We use 100
# as a practical bound for active traces in a session-based AI memory system.
````

## module — original line 93 (comment)

````text
# Engineering choice: dependency threshold below which a memory is considered
# cortically independent and no longer needs hippocampal support. No paper
# source (McClelland 1995 gives no scalar dependency metric — see module
# docstring); picked as the midpoint of the "transitional" band between the
# release threshold (0.05) and the "still hippocampal" cutoff (0.7) below.
# source: engineering choice
````

## module — original line 101 (comment)

````text
# Above this dependency a memory is still primarily hippocampal.
# source: the "still hippocampal" cutoff (0.7) named in the
# _CORTICAL_INDEPENDENCE_THRESHOLD comment above — engineering choice
````

## module — original line 106 (comment)

````text
# A trace is only released while the memory is not hot (not actively used).
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 286 (comment)

````text
# strict=True is invariant-safe (both lists derived from the same
# `memories` iteration above) but locks the invariant in: if a future
# edit decouples the lists, strict surfaces the bug as ValueError
# instead of silently classifying a truncated subset.
````
