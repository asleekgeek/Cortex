---
title: "ADR-0817 — benchmarks/beam/data.py rationale"
status: accepted
source: benchmarks/beam/data.py
---

# ADR-0817 — benchmarks/beam/data.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## extract_10m_chat — original line 51 (docstring)

````text
    This function re-numbers each message's ``id`` field to the global
    scheme so the benchmark scoring loop can match source_chat_ids to
    the flattened turn list. It also tags each message with a
    ``plan_id`` field so `turns_to_memories` can propagate it into
    memory ``agent_context`` for stage-aware retrieval.
````

## turns_to_memories — original line 163 (docstring)

````text
    BEAM conversations have 3 time_anchors marking session boundaries.
    Propagate each time_anchor forward to subsequent turns in the same
    session — if a session starts on March-15-2024, all turns in that
    session are from March-15-2024.  This gives the temporal/recency
    retrieval signals meaningful values instead of defaulting to NOW().
    
````

## inline — original line 33 (directive-rationale)

````text
# noqa: PLC0415 — optional dependency ([benchmarks] extra); imported where used so environments without it keep working
````

## inline — original line 38 (directive-rationale)

````text
# noqa: BLE001 — bench harness is fail-soft — failure is printed and the run continues or exits with a report
````

## module — original line 198 (comment)

````text
# Only include [Date:] in content if this turn pair originally had
# a time_anchor — avoids diluting embeddings with repeated dates.
# The propagated `last_anchor` still feeds `created_at` for recency.
````

## module — original line 217 (comment)

````text
# Stage ID = time_anchor when present, fallback to "stage-0".
# For 100K/500K/1M splits the BEAM conversations have 3 time
# anchors marking session boundaries, so each conversation
# naturally decomposes into 3 stages. For 10M we also set
# plan_id per (user,assistant) pair from the plan index.
# Stage ID: for 10M, prefer plan_id (from extract_10m_chat);
# for 100K/500K/1M, fall back to time_anchor session.
````

## module — original line 234 (comment)

````text
# Also propagate into agent_context so the stage
# survives ingest (memory_ingest passes agent_context
# through to the DB). The assembler reads stages
# from this field at benchmark time.
````
