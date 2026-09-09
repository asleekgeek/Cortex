---
title: "ADR-0871 — benchmarks/trust_factor_sweep.sh rationale"
status: accepted
source: benchmarks/trust_factor_sweep.sh
---

# ADR-0871 — benchmarks/trust_factor_sweep.sh

Source rationale preserved verbatim. Identifiers inside historical quotations are not current identities.

## benchmarks/trust_factor_sweep.sh — original line 1

````text
#!/usr/bin/env bash
# Trust-factor calibration sweep (issue #368).
````

## benchmarks/trust_factor_sweep.sh — original line 3

````text
#
# Pre-registration, decision rule and grid: docs/provenance/trust-factor-calibration.md
# Read it before changing anything here — the grid is derived from a cheap
# adversarial sweep, and the decision rule is fixed in advance on purpose.
````

## benchmarks/trust_factor_sweep.sh — original line 7

````text
#
#   benchmarks/trust_factor_sweep.sh              # run ONE pending cell, then exit
#   benchmarks/trust_factor_sweep.sh --quick      # smoke the plumbing (NOT gated)
````

## benchmarks/trust_factor_sweep.sh — original line 10

````text
#
# 2026-08-10 architecture change: this script used to loop over the whole
# grid in one process. Five campaigns died mid-grid over one session, each
# attributed to a different cause after the fact (contention, a native
# crash, a missing dataset, a session gap, a noisy neighbor) — five
# explanations for one symptom, which was itself the signal: a long job
# driven from a sub-agent's own foreground loop does not survive whatever
# ends that sub-agent's turn, regardless of which resource happened to be
# short at the time. The fix is not preventing the death (it cannot be, from
# here) but making it cost one cell instead of the whole grid: this script
# now resumes from `benchmarks/lib/sweep_progress.py`'s PROGRESS.json (which
# W values already completed), runs exactly the next PENDING cell, records
# its result — including machine-load/disk-space snapshots at cell start
# AND end (`benchmarks/lib/machine_load_snapshot.py`,
# `benchmarks/lib/disk_space_snapshot.py`) — and returns control. A kill or
# crash mid-cell leaves that cell's PROGRESS.json entry absent, so the next
# invocation retries exactly that cell, never the ones already recorded.
````

## benchmarks/trust_factor_sweep.sh — original line 27

````text
#
# Still true, unchanged: one reproduce.sh invocation per cell, against its
# own ephemeral container. No parallelism: a fan-out on this machine on
# 2026-08-08 drove load to 37 and swapped 11.9 GB.
````

## benchmarks/trust_factor_sweep.sh — original line 36

````text
# source: docs/provenance/trust-factor-calibration.md §Grid — brackets the
# 0.8 -> 0.7 transition found by the adversarial pre-sweep. 1.0 is the control.
````

## benchmarks/trust_factor_sweep.sh — original line 40

````text
# Empty-array expansion under `set -u` is an "unbound variable" error on the
# bash 3.2 that ships with macOS, so the flag is carried as a plain string and
# left unquoted at the call site (word-split on purpose: zero args when empty).
````

## benchmarks/trust_factor_sweep.sh — original line 46

````text
# Fixed location, not a fresh timestamp per invocation: resume needs the
# NEXT call to find the SAME PROGRESS.json the previous one wrote.
````

## benchmarks/trust_factor_sweep.sh — original line 86

````text
# Exported, not inlined: reproduce.sh spawns the benchmark processes, and
# retrieval_dispatch.py reads the value at import in each of them.
````

## benchmarks/trust_factor_sweep.sh — original line 106

````text
# reproduce.sh writes into benchmarks/results/repro/<its own stamp>/;
# record which one belongs to this cell so the summary can be rebuilt
# without guessing from timestamps.
````
