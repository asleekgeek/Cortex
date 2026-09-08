---
title: "ADR-0821 — benchmarks/energy/run.sh rationale"
status: accepted
source: benchmarks/energy/run.sh
---

# ADR-0821 — benchmarks/energy/run.sh

Source rationale preserved verbatim. Identifiers inside historical quotations are not current identities.

## benchmarks/energy/run.sh — original line 43

````text
# source: macOS sudo(8), Signal handling: user-sent SIGINT is relayed
# to the command. Signal the existing sudo parent; no fresh ticket needed.
````

## benchmarks/energy/run.sh — original line 52

````text
# source: zsh exit status for SIGINT is 128 + signal 2; powermetrics(1)
# specifies SIGINT as its normal stop-sampling-and-exit signal.
````

## benchmarks/energy/run.sh — original line 81

````text
# source: powermetrics(1): 0 samples means continuous capture; buffer-size 1
# flushes each sample. The EXIT trap stops the sensor after the Python run.
````
