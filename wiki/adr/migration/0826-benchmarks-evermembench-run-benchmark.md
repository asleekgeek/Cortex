---
title: "ADR-0826 — benchmarks/evermembench/run_benchmark.py rationale"
status: accepted
source: benchmarks/evermembench/run_benchmark.py
---

# ADR-0826 — benchmarks/evermembench/run_benchmark.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
EverMemBench benchmark for Cortex memory system.
````

## module — original line 3 (docstring)

````text
Tests long-horizon memory for multi-party collaborative dialogues
(Hu et al., 2026). 5 projects, 170 employees, 365 simulated days,
2,400 QA pairs across 3 evaluation dimensions.
````

## module — original line 7 (docstring)

````text
Dimensions:
  F — Fine-grained Recall (SH: single-hop, Multi: multi-hop, Temp: temporal)
  MA — Memory Awareness (Const: constraint, Proact: proactivity, U: update)
  P — Profile Understanding (Style, Skill, Role)
````

## module — original line 12 (docstring)

````text
Evaluation: Retrieval-based — check if correct evidence is in top-K.
Full QA requires claude -p as judge.
````

## module — original line 15 (docstring)

````text
Dataset: HuggingFace "EverMind-AI/EverMemBench-Dynamic"
````

## module — original line 17 (docstring)

````text
Run:
    python3 benchmarks/evermembench/run_benchmark.py [--limit N]

````

## EverMemRetriever — original line 143 (docstring)

````text
Adapter wrapping shared BenchmarkRetriever for EverMemBench.
````

## module — original line 60 (comment)

````text
# source: structural — a question ID carries a major and a minor prefix,
# e.g. "F_SH_Top004_001" splits on "_" into at least those two fields
````

## inline — original line 80 (directive-rationale)

````text
# noqa: PLC0415 — optional dependency ([benchmarks] extra); imported where used so environments without it keep working
````

## module — original line 191 (comment)

````text
# Multiple choice — check if correct answer's content is retrievable
````
