# ADR-0881: fuzz/replay_corpus.py design and historical evidence

Status: accepted; existing test/harness evidence preserved during issue #514.

Source `fuzz/replay_corpus.py`, original SHA-256 `00734aafd5ffd0f3be0e7db40d9f36728aad20e583258f59eb0a4c71d754ce5b`.
Assertions and runtime fixture literals remain unchanged.

## Original docstring, lines 2–28

````text
"""Replay every committed fuzz corpus input through its harness.

Why this exists
---------------
The fuzzers themselves are CI-only: atheris publishes manylinux x86_64
wheels for cpython 3.12-3.14 and nothing else, so a contributor on a Mac
cannot run them at all. That would leave the harnesses' properties unchecked
on every machine except one CI job — and a property nobody can run locally
is one that rots.

This replayer needs no atheris. It imports each harness's `consume` and
feeds it the committed corpus, so:

  * every crash the fuzzer ever found stays fixed (the corpus is the
    regression suite — a reproducer is committed, not just described);
  * the harnesses stay importable and their assertions stay meaningful,
    rather than silently breaking against a renamed field and only failing
    the next time someone runs a fuzz campaign;
  * the properties run in the normal test suite, on every platform.

It is wired into pytest via tests_py/fuzz/test_corpus_replay.py, so this is
executed by the same `pytest` run as everything else.

Usage:
    python3 fuzz/replay_corpus.py            # replay all corpora
    python3 fuzz/replay_corpus.py --list     # show harnesses and counts
"""
````

