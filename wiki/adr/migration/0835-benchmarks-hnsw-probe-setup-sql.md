---
title: "ADR-0835 — benchmarks/hnsw_probe/setup.sql rationale"
status: accepted
source: benchmarks/hnsw_probe/setup.sql
---

# ADR-0835 — benchmarks/hnsw_probe/setup.sql

Source rationale preserved verbatim. Identifiers inside historical quotations are not current identities.

## benchmarks/hnsw_probe/setup.sql — original line 1

````text
-- Setup bench table matching Cortex memories schema for HNSW probe.
-- Source: pg_schema.py lines 20-65 (MEMORIES_DDL) and lines 476-477 (HNSW index).
-- HNSW index: USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)
````

## benchmarks/hnsw_probe/setup.sql — original line 15

````text
-- Disable autovacuum on this table to avoid contaminating measurements.
````
