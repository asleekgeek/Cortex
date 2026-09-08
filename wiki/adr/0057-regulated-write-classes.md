---
kind: decision
status: accepted
decision_id: ADR-0057
title: "Regulate automatic writes without suppressing deliberate evidence"
---

# ADR-0057: Regulate automatic writes without suppressing deliberate evidence

Extracted from `mcp_server/handlers/consolidation/homeostatic.py`, original lines 61–91.
Original comment SHA-256: `c05383cef7e642832f36c4d2f0585469b36775dfb3fcd8afbe97ffa3167d7d41`.

M-D3 doctrine — which write classes are subject to target-mean
regulation (scalar update, fold, AND cohort correction; all three are
forms of the same mechanism: pulling a distribution toward
_TARGET_HEAT). No new numeric constants invented (§8 coding standards)
— this set is a class-membership decision, not a numeric one:

  auto        REGULATED. This is the population the mechanism was
              validated for (ROC-AUC / Turrigiano-Tetzlaff assumptions
              both presume an ongoing, high-volume, statistically-
              exchangeable population competing for one heat budget —
              exactly the auto-capture flood, 92% of the corpus by
              volume, I6 audit).
  deliberate  NOT regulated. Individually-meaningful, low-volume
              witnesses (~5-8% of writes, audit) — not exchangeable,
              not flood-like. Regulating their mean toward the SAME
              set-point as the flood is the exact mechanism that
              re-suppressed the class this increment exists to fix
              (module docstring above).
  derived     NOT regulated. Near-empty today (0 rows, design-doc
              audit) and structurally bursty/capped (memify_derive caps
              20 attempts/run) — Welford moments on tiny N are
              statistically unstable, and duplication is already
              judged by the ``derived-rel:`` idempotence marker rather
              than a heat threshold (M-D2's "derived" write-gate row
              makes the same argument; regulation would measure the
              same wrong quantity here).
  mechanical  NOT regulated. One-shot bulk-import passes (backfill,
              seed, ingest, codebase scan) — not an ongoing rate. The
              "target firing rate" doctrine (Turrigiano 2008, Tetzlaff
              2011) has no referent for a single injection event; there
              is no runaway to defend against.
