---
title: "ADR-0803 — .github/workflows/fuzz.yml rationale"
status: accepted
source: .github/workflows/fuzz.yml
---

# ADR-0803 — .github/workflows/fuzz.yml

Source rationale preserved verbatim. Identifiers inside historical quotations are not current identities.

## .github/workflows/fuzz.yml — original line 5

````text
# Two cadences, because they answer different questions:
````

## .github/workflows/fuzz.yml — original line 7

````text
#   * on pull_request — a short batch over the changed tree, so a crash
#     introduced by the diff is caught before merge. Kept to 120s per
#     harness: long enough to exercise the mutated surface, short enough
#     not to become the slowest required check.
#   * on schedule — a longer run from the accumulated corpus, which is
#     where a fuzzer actually finds things. Nothing blocks on it.
````

## .github/workflows/fuzz.yml — original line 14

````text
# Why not a required check on the schedule run: a fuzzer that has run for
# hours will eventually find SOMETHING, and blocking merges on an
# asynchronous discovery would make the queue hostage to an unrelated
# input. The PR batch blocks; the deep run reports.
````

## .github/workflows/fuzz.yml — original line 19

````text
# Findings land as artifacts (crash reproducer + stacktrace). The fix
# workflow is: add the reproducer to fuzz/corpus/<harness>/repro-<name>,
# fix the code, and the committed corpus keeps it fixed forever — that
# corpus is replayed by the ordinary pytest suite
# (tests_py/fuzz/test_corpus_replay.py), on every platform, with no
# atheris needed.
````

## .github/workflows/fuzz.yml — original line 30

````text
# Weekly, Monday 04:17 UTC. Off the hour to avoid the scheduling spike
# that delays every cron firing at :00.
````

## .github/workflows/fuzz.yml — original line 37

````text
# source: W1-7 in tasks/codex-green-remediation-plan.md; superseded PR checks.
````

## .github/workflows/fuzz.yml — original line 47

````text
# source: run 34030977934 (2026-09-06), max 363s; ceil(2 * 363 / 60).
````

## .github/workflows/fuzz.yml — original line 60

````text
# Build the base commit too, so the run only reports crashes this
# PR introduces rather than pre-existing ones. Without it every PR
# inherits the backlog and the check is ignored within a week.
````

## .github/workflows/fuzz.yml — original line 77

````text
# source: run 33384194242 (2026-08-31), max 1144s; ceil(2 * 1144 / 60).
````
