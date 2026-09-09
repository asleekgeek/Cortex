---
title: "ADR-0833 — benchmarks/hnsw_probe/phase2_c_d.sql rationale"
status: accepted
source: benchmarks/hnsw_probe/phase2_c_d.sql
---

# ADR-0833 — benchmarks/hnsw_probe/phase2_c_d.sql

Source rationale preserved verbatim. Identifiers inside historical quotations are not current identities.

## benchmarks/hnsw_probe/phase2_c_d.sql — original line 13

````text
-- VACUUM to clean up any dead tuples from the previous phase
-- (HNSW-present conditions left bloat because batched UPDATE creates new tuple versions).
````
