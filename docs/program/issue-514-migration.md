# Issue #514 — decision extraction audit

The foundation is PR #515 (`37243cb8`). This dependent change moves source
rationale into canonical wiki pages and exposes the same text in generated
`docs/adr/` mirrors. Historical identifiers inside quoted excerpts are archival
text, not current decision identities. Source pointers resolve through the
project wiki manifest.

## Scope and preservation

The review covered 736 initial runtime/tool files, 99 additional runtime/build
files, and 632 test/fuzz files. The latter produced 181 candidates for closer
review; ordinary test-purpose, fixture and assertion explanations were retained.
There are 822 extraction pages and 850 canonical pages including the historical
ADRs, the foundation decision, and two initial reviewed extractions.

Original rationale and citations are preserved as excerpts with their source
locations. Operational API contracts, complete tool descriptions, licenses,
tooling directives and executable behavior are retained. A final audit also
checks report headings and tool examples for obsolete decision identifiers.
Canonical lookup was verified against the exact path and content of all 850
pages. No production `source:` comment uses a competing citation namespace.

The adjacent JSON records 1,002 inspected source files with base blob IDs,
before/after SHA-256 digests, line counts and Python AST comparisons against
the foundation. Files that had no rationale to extract can remain unchanged.
The extraction removes approximately 20,000 source lines; this is documentation
movement, not a runtime-performance claim.

## Explicit AST differences

Python AST comparisons exclude actual module/class/function docstrings. The
remaining differences are listed rather than hidden by a broad string exemption:

- Handler schema descriptions, response explanations and three examples replace
  historical decision references with operational text or valid canonical IDs.
- PostgreSQL/SQLite DDL and query strings change comments only. SQL token streams
  were compared, including 97 PostgreSQL and 52 SQLite DDL statements; f-string
  interpolations remain unchanged.
- A generated pilot-report heading now cites ADR-0793 instead of an obsolete ID.
- The I2 test retains the same eleven allowed heat writers with updated line
  locations, after comparing writer bodies. The DDL semicolon test checks all
  DDL comment lines instead of locating a deleted prose heading.

Shell executable text/heredocs, parsed YAML/TOML values, and Docker/SQL structures
were checked separately. Python embedded in configuration was checked as Python.
Assertions and literal identity fixtures remain unchanged except the explicitly
listed test maintenance above.

The legacy `_SUM_TOLERANCE` in the capture-origin benchmark is retained unchanged;
its original numerical justification is unknown. ADR-0069 records this limitation
and the decision to preserve behavior, without claiming a new calibration.

## Validation

- Full isolated SQLite run: 8,143 passed, 257 skipped, 459 subtests passed.
  PostgreSQL-dependent tests are covered by CI; the local run deliberately uses
  an unreachable private PostgreSQL socket and private SQLite/lock paths.
- Canonical filename registration/index parity: 86 focused tests passed in both
  foundation and migration worktrees.
- Ruff 0.16.6, Pyright 1.1.411 and the craftsmanship check cover the actual changed
  files, including untracked files before commit. Baseline exemptions only shrink.
- Generated mirror bytes are checked without site packages; every source ID is
  checked against the canonical index.
- The committed known-item benchmark reports recall@1 and MRR@10 from 0 to 1 for
  five wiki-only boundary IDs, with no backend calls. This is source coverage,
  not a claim about semantic ranking quality.
- Full LongMemEval/LoCoMo comparison against unchanged `main` is pending.

For reproduction, install the locked test/typecheck/lint dependencies, use an
isolated test backend, then run `python -m pytest tests_py`, `ruff check .`,
`ruff format --check .`, `python -m pyright mcp_server/`, and
`python scripts/check_project_wiki.py`. The benchmark driver is
`benchmarks/reproduce.sh`; use separate clean runs of the baseline and candidate.
