# W3-5: memories storage policy and fillfactor calibration

## Symptôme

The remediation contract records F6 as approximately 1.4 GB/month of growth,
19× amplification, 3,140 HOT updates among 24,838 updates (12.6%), 23 indexes,
and a current vacuum scale factor of 0.2. These are prior observations supplied
by the plan, not measurements repeated in this patch. The plan explicitly
selects `autovacuum_vacuum_scale_factor=0.05`; it provides no measured fillfactor.

## Cause racine

PostgreSQL's update/delete vacuum threshold depends on the base threshold plus
the scale factor times `pg_class.reltuples`. Lowering the factor can make the
table eligible earlier; it does not immediately reclaim disk space or guarantee
that a worker starts at that threshold. Insert-triggered vacuuming uses separate
settings. This patch changes only the prescribed update/delete scale factor.
[PostgreSQL 16 vacuum scheduling](https://www.postgresql.org/docs/16/routine-vacuuming.html).

HOT requires room on the old tuple's page and no changed column referenced by
ordinary indexes (PostgreSQL 16 exempts summarizing indexes such as BRIN).
`heat_base` has B-tree indexes, so the canonical heat writer cannot become HOT
when its heat value changes, regardless of fillfactor. `replay_count` provides
a separate existing writer whose HOT eligibility is checked against the actual
catalog before calibration. A fillfactor change alone cannot establish a gain
for F6's aggregate traffic. [HOT conditions](https://www.postgresql.org/docs/16/storage-hot.html).

## Changement

`MEMORIES_STORAGE_OPTIONS_DDL` is a separate literal DDL block in `pg_schema.py`,
dispatched after table creation and migrations:

```sql
ALTER TABLE memories SET (autovacuum_vacuum_scale_factor = 0.05);
```

It does not set or reset fillfactor, alter indexes, or perform maintenance.
The value 0.05 comes from W3-5's explicit instruction. It is not derived from
the HOT ratio. **Fillfactor selection and complete W3-5 acceptance remain pending.**

The SQL generator `scripts.pg_storage_calibration` has no DB driver or connection.
Its output checks `current_database()='cortex_w3_5_calibration'` before mutations
and creates a fresh schema with an ASCII `w3_5_` name. Schema reuse fails visibly;
no existing schema is dropped. `--migration-only` needs no corpus and applies
the actual migration twice to a private table initially carrying factor 0.2 and
fillfactor 100. Sorted catalog options must remain equal and retain fillfactor.

The experiment creates fresh logged clones using `LIKE public.memories INCLUDING
ALL`. It preserves the fixture's indexes and column definitions, excluding
generated columns from explicit insertion. IDs are copied explicitly; parent
serial sequences are not advanced. LIKE does not copy triggers or foreign keys,
so this is a controlled heap/index experiment, not a complete application replay.
Each candidate is applied before loading the same rows in ID order. Fillfactor's
documented domain is 10–100, default 100; the CLI requires explicit candidates
including 100. No 90/80 recommendation or empirical margin is supplied.
[CREATE TABLE storage and LIKE semantics](https://www.postgresql.org/docs/16/sql-createtable.html).

Two workloads run separately, each on fresh clones for four repetitions
(`r0` discarded; `r1`–`r3` retained, following plan §3):

- `eligible`: `replay_count = replay_count + 1`, from
  `pg_store_consolidation_stage.increment_replay_count`. Catalog dependencies,
  including expression-index references, must not include replay_count.
- `indexed`: changes `heat_base` and `heat_base_set_at`, the columns written by
  `pg_store_heat.bump_heat_raw`. Alternation between the CHECK bounds 0 and 1
  forces a real heat change. A B-tree on heat_base must exist, and any HOT count
  on this control raises an error. These endpoint changes are synthetic;
  neither their magnitude nor a traffic frequency is inferred from F6.

Each pass is a separate transaction. The UPDATE is measured using EXPLAIN
ANALYZE/BUFFERS/WAL, then HOT and update counts are read in that same transaction
through `pg_stat_xact_user_tables`. These counters update continuously, avoiding
the lag and transaction snapshots of cumulative statistics. Heap, index and
total bytes are captured before updates, before manual vacuum, and after it.
Normal VACUUM VERBOSE ANALYZE runs only on clones; psql records elapsed time and
vacuum diagnostics. [Statistics semantics](https://www.postgresql.org/docs/16/monitoring-stats.html).

## Preuve

Final calibration on 2026-09-07, source
`2a7b78b21c872a1f140fb7800bf55953b9cb2618`, after the final main rebase:
PG16.15 ARM64 / pgvector0.8.6; 30,000 public LongMemEval turns, real 384D
vectors, 28,735 distinct untruncated contents. All stored content and vector
bytes were read back and matched. Median physical row size was 2,780 bytes.
This is a controlled public fixture, not a measured production traffic mix.

The 24 independent clones use four repetitions per workload/candidate and
one UPDATE pass; repetition zero is discarded. Total run: 1,120.827 s;
host load 3.20→2.44; free space 41.605→34.009 GB. Retained medians:

| Writer | fillfactor | HOT % | Execution ms | WAL bytes | Heap before | Total after VACUUM |
|---|---:|---:|---:|---:|---:|---:|
| eligible | 100 | 0.930 | 14522.213 | 614573949 | 39657472 | 312049664 |
| eligible | 90 | 17.127 | 12813.265 | 569785465 | 44072960 | 315129856 |
| eligible | 80 | 25.133 | 11236.398 | 473679913 | 49913856 | 314261504 |
| indexed | 100 | 0.000 | 14803.618 | 624916066 | 39657472 | 312811520 |
| indexed | 90 | 0.000 | 15220.108 | 658408553 | 44072960 | 318849024 |
| indexed | 80 | 0.000 | 15372.534 | 635429690 | 49913856 | 319627264 |

All twelve indexed-heat trials had zero HOT. Lower fillfactor improves the
eligible writer, but indexed writes have larger final storage and longer median
execution here. No production weighting is available, so no lower fillfactor
is selected. Applying the exact autovacuum DDL twice preserved fillfactor100
and identical reloptions after the first application. No production maintenance
was performed; the owned container and its anonymous volume were removed after
all measurements completed and no client backend remained.

Evidence: `/private/tmp/cortex-green-w3-5-dense-calibration-final/` contains
manifest, generated SQL, complete stdout/stderr and summary; SQL SHA-256
`50094bb5605ac8f604ca59d65ee343c49069a01e82ec7774f34258997d4b0518`.
The dense fixture manifest/readback proof remains under
`/private/tmp/cortex-green-w3-5-dense-fixture/`. No calibration SQL, schema
storage DDL or fixture bytes changed in the subsequent scalar-scoring merge.
Full retrieval floors are not established by these storage measurements.

## Conformité

Final integration base: `6ec76a0e0f9851893c39396a5f59ddaa329abfd5`. Only the targeted schema block,
calibration generator, tests and this runbook change. The existing large schema
file and `get_all_ddl` method remain declared debt; no baseline entry is added.
No partial index is introduced before W4-1. No lower fillfactor is chosen.

The experiment disables autovacuum on its clones to compare controlled manual
vacuum work. It therefore does not measure production autovacuum frequency.
Normal vacuum makes space reusable and may trim empty end pages; it is not a
general table rewrite. [VACUUM behavior](https://www.postgresql.org/docs/16/sql-vacuum.html).

## Candidats issues

The candidate decision must weigh HOT counts, update time/WAL, heap and index
bytes, and vacuum time for both writer shapes. Reject candidates dominated on
all relevant observations; do not invent a weighted score or extrapolate a
production percentage from these isolated bulk passes. A final choice also
needs the measured production distribution of indexed/non-indexed updates and
representative row/TOAST sizes. If this evidence does not identify a useful
lower value, retain 100 and record that W3-5's fillfactor requirement is unmet.

Each candidate creates eight copies (two workloads × four repetitions), with
their indexes, retained for inspection. Budget disk/time before execution.
The generator's minimum 30,000 rows follows the plan's isolated PG scale; the
passes and candidates are explicit experiment inputs. It does not choose them
for the owner. Persist the fixture hash, server version/settings, source index
definitions, command, machine load and complete psql stdout/stderr with results.

## Runbook

First run the local wiring checks:

```sh
python3 -S -m unittest tests_py.infrastructure.test_pg_storage_policy -v
python3 -S -m scripts.pg_storage_calibration --schema w3_5_options --fillfactors 100 --passes 1 --migration-only > migration.sql
```

For the orchestrator's PG check, provision the named disposable database in the
isolated `reproduce.sh` container (the repository uses PG16), and run
`psql -X --dbname="$W3_5_ISOLATED_DSN" --file=migration.sql`. Check the script's
catalog assertion and `\d+ w3_5_options.memories`. Then load a representative
`public.memories` fixture with its actual indexes and at least 30,000 rows.
Generate a new schema for each experiment, supplying the candidate(s) and pass
count explicitly, and execute the SQL with the same psql invocation. Keep the
fixture immutable and run the experiment without concurrent writers. Start with
the baseline 100 to inspect the workload; do not call that a calibrated choice.
Keep both stdout and stderr because VACUUM VERBOSE reports through notices.

After measurements select a lower value, add that value and its exact evidence
reference to the migration and rerun the live idempotence/catalog check. On a
deployed table, inspect effective options before and after with:

```sql
SELECT c.oid::regclass, c.reloptions
FROM pg_class c WHERE c.oid = 'public.memories'::regclass;
```

**Production maintenance belongs to the owner.** Setting storage parameters
takes a SHARE UPDATE EXCLUSIVE lock and does not immediately rearrange existing
rows. Apply any measured fillfactor before a separately scheduled rewrite if
the owner wants existing pages repacked. [ALTER TABLE storage parameters](https://www.postgresql.org/docs/16/sql-altertable.html).

The owner can choose `VACUUM (FULL, ANALYZE) public.memories` during an approved
maintenance window; it needs extra disk space and an ACCESS EXCLUSIVE lock.
Alternatively, after checking the installed pg_repack version/extension, key
eligibility and disk capacity, the owner can use pg_repack's table-scoped dry
run, followed by table-scoped execution with `--no-kill-backend`. This option
skips a table when locks cannot be obtained rather than cancelling other
sessions. Full repack requires a primary key or suitable NOT NULL unique key
and about twice the target table-plus-index size in additional free space.
[pg_repack's official runbook](https://reorg.github.io/pg_repack/).

No maintenance command is invoked by the migration or generator on production.
Rollback restores the recorded prior reloption values (or RESET when absent),
and removes the new policy from schema initialization before reconnecting, so
initialization does not reapply it. Rollback of settings does not undo a physical
rewrite. Keep production observations separate from the disposable experiments.
