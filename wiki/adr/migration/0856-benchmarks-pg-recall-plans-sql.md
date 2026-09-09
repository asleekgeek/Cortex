---
title: "ADR-0856 — benchmarks/pg_recall_plans/sql.py rationale"
status: accepted
source: benchmarks/pg_recall_plans/sql.py
---

# ADR-0856 — benchmarks/pg_recall_plans/sql.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## experiment_sql — original line 72 (docstring)

````text
One transaction fixes NOW() for both versions and all heat calculations.
````

## module — original line 10 (comment)

````text
# source: W4-1 adds only these two indexes; the baseline phase excludes them.
````

## module — original line 15 (comment)

````text
# source: remediation plan §3's four/first-discarded protocol, explicitly
# extended to this PG experiment by the W4-1 harness review request.
````

## inline — original line 47 (directive-rationale)

````text
# noqa: S608 — phase allowlist, fixed mode/scope and query grammar
````

## module — original line 84 (comment)

````text
# source: PostgreSQL 16 auto_explain documentation. Zero logs all
# statements, including nested function plans; NOTICE returns them
# to psql stderr as well as the container log.
````
