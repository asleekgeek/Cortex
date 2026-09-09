# ADR-0068: benchmarks/lib/blend_weight_sweep.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/blend_weight_sweep.py`; original SHA-256 `d5b410f2c11a8c53ed016be674daa1683c7905316981174681fd648f3f0601a4`.

## Original docstring, lines 1–63

````text
"""Blend-weight calibration sweep for the 6 post-WRRF rerank stages.

Calibrates the engineering-default blend constants in
``mcp_server/core/recall_pipeline.py`` against LongMemEval-S so paper
§6.3 ships with cited optima rather than placeholders.

Methodology
-----------
Two-phase coordinate-descent (Fisher §Move 2):

* **Phase A** — central-composite design over the 4 perception-side knobs
  (HOPFIELD × HDC × SA × DENDRITIC). 17 cells = 1 center + 16 corners.
  Holds the affect-side knobs at their engineering default.
* **Phase B** — full 5×5 grid over the 2 affect-side knobs
  (EMOTIONAL_RETRIEVAL × MOOD_CONGRUENT) with the perception-side knobs
  fixed at the Phase A optimum.

A full 4-D 4-level grid would be 256 cells — infeasible at ~30 s/q × 100 q.
The CCD cuts 4-knob exploration to 17 cells while still admitting all
2-factor interaction effects within the design region. Source for CCD:
Box & Wilson (1951), *On the Experimental Attainment of Optimum
Conditions*, J. Royal Stat. Soc. B 13(1):1-45 — original central-composite
construction. We use the 2-level fractional-factorial face-centered
variant (no axial points beyond the corners) so all 17 cells remain on the
[0.10, 0.40] grid the engineering defaults already span.

Each cell runs in a fresh subprocess so the module-level reads in
``recall_pipeline.py`` pick up that cell's env vars cleanly. Cross-cell
state contamination is avoided by ``BenchmarkDB.clear()`` between
questions (already present in the runner).

Output
------
``benchmarks/results/blend_calibration/<timestamp>/``
  - ``cell_<idx>.json`` — per-cell {weights, mrr, r10, wall_seconds}
  - ``summary.csv``     — flat table for inspection
  - ``analysis.json``   — best cell + plateau width + per-knob marginal effect
  - ``manifest.json``   — code_hash, n_queries, phase, seed, total wall

Usage
-----
.. code-block:: bash

    # Phase A — 17 cells (CCD), n=50 questions
    python -m benchmarks.lib.blend_weight_sweep \\
      --phase a --n-queries 50

    # Phase B — 25 cells (full 5x5), n=30 questions, with Phase A optimum
    python -m benchmarks.lib.blend_weight_sweep \\
      --phase b --n-queries 30 \\
      --hopfield 0.30 --hdc 0.20 --sa 0.25 --dendritic 0.10

    # Smoke test — 3 cells only, n=5 questions
    python -m benchmarks.lib.blend_weight_sweep \\
      --phase smoke --n-queries 5

References
----------
- Box, G. E. P. & Wilson, K. B. (1951). Central-composite designs.
- Cormack, Clarke & Buettcher (2009). RRF blend constant k=60.
- ``docs/provenance/verification-protocol.md`` — Fisher discipline for sweeps.
- ``docs/provenance/blend-weight-calibration.md`` — pre-registration of THIS sweep.
"""
````

## Original comment, lines 95–98

````text
# Phase A central-composite design points.
# Center + 16 face-centered corners on [low, high] for each of 4 knobs.
# DENDRITIC uses a tighter range [0.05, 0.20] per the spec.
# source: docs/provenance/blend-weight-calibration.md §Phase A grid.
````

## Original comment, lines 143–144

````text
# strict=True: keys is a fixed 4-tuple and combo is a
        # repeat=4 itertools.product entry — always 4 elements each.
````

## Original comment, lines 232–233

````text
# Persist the failure log alongside the cell record so a crashed
        # cell is investigated rather than silently averaged in.
````

## Original comment, lines 296–297

````text
# source: structural — a marginal effect needs at least two distinct levels of
# a knob to have a range at all
````

## Original comment, lines 348–353

````text
# Dirtiness measured against TRACKED source files only (matches the
    # pre-registration definition in docs/provenance/blend-weight-calibration.md
    # §Reproducibility manifest). Excluded by design:
    # - Untracked files (benchmark result archives, agent caches, node_modules)
    # - Submodule internal state (.claude/worktrees/agent-* — agent
    #   infrastructure, not benchmark source) via --ignore-submodules=all.
````

