# ADR-0053: Deliberate Re-heat CAS Writer — I2 Canonical-Writer Exception

**Status:** Accepted
**Date:** 2026-07-10
**Decision-makers:** cdeust
**Related:** Invariant I2 (`docs/invariants/cortex-invariants.md` §I2,
`tests_py/invariants/test_I2_canonical_writer.py`); I6-D5 campaign
(`docs/campaigns/i6d5_memory_reheat_summary_20260710.md`); precedent
exception `infrastructure/pg_store.py:685` (`_transfer_anchor_on`).

## Context

I6-D5 (INC6.6, `mcp_server/infrastructure/pg_store_memory_reheat.py::apply_reheat`)
introduced a second `UPDATE memories SET heat_base = ...` call site. Invariant
I2 requires every `heat_base` writer to either route through the canonical
single-row writer (`pg_store.py::bump_heat_raw`) or be added to
`test_I2_canonical_writer.py::_ALLOWED_WRITERS` with a cited justification.
`apply_reheat` was left off the allow-list at merge time — CI run 29109251545
caught the omission (I2 fails deterministically: it is a static AST/grep
scan, not flaky).

## Decision

`apply_reheat` is added to `_ALLOWED_WRITERS`
(`infrastructure/pg_store_memory_reheat.py:157`) rather than routed through
`bump_heat_raw`. Routing through the canonical writer would silently
denature two guarantees this campaign depends on:

1. **CAS-guarded write.** `apply_reheat`'s `WHERE id = %(memory_id)s AND
   heat_base = %(old_heat_base)s::REAL` only writes if `heat_base` is
   still exactly the value the scan observed — a concurrent writer
   (decay tick, another campaign run, a user `rate_memory`) between scan
   and write causes a no-op, counted as `skipped_race`
   (`tests_py/handlers/consolidation/test_memory_reheat_pass.py`, "CAS
   race rejection" case). `bump_heat_raw` is an unconditional overwrite
   with no CAS clause — routing through it would turn every race into a
   silent overwrite of a concurrent change, which I6-D5 explicitly
   requires to detect and skip.
2. **Decay clock preserved.** `apply_reheat` deliberately does **not**
   touch `heat_base_set_at` (see its docstring, `pg_store_memory_reheat.py:136-142`)
   — the recalibrated row keeps decaying from its existing timeline,
   which is what the campaign's J+30 re-measurement (2026-08-09,
   `docs/campaigns/i6d5_memory_reheat_summary_20260710.md` "Re-mesure
   programmée") is designed to observe. `bump_heat_raw` unconditionally
   stamps `heat_base_set_at = NOW()` on every call — routing through it
   would reset the decay clock on 540+ rows and invalidate the J+30
   measurement's premise.

Both properties are structural to the campaign's design (I6-D5,
`scratchpad/inc6-design-campagne-memoire.md`), not implementation
convenience — this is the same class of exception already accepted for
`_transfer_anchor_on` (`pg_store.py:685`, "cannot route through
bump_heat_raw, which commits on its own connection while this transfer
must stay inside the supersede transaction").

## Consequences

- `test_I2_canonical_writer.py::_ALLOWED_WRITERS` gains one entry:
  `("infrastructure/pg_store_memory_reheat.py", 157)`, citing this ADR.
- Any future one-shot recalibration campaign against a `REAL` heat_base
  column needing race-detection + decay-clock preservation should follow
  the same pattern (CAS-guarded, allow-listed writer) rather than
  routing through `bump_heat_raw`.
- No change to `apply_reheat`'s behavior — this ADR documents an
  already-shipped, already-tested (19/19, INC6.6) design decision; it
  closes the CI gap between the code and the invariant's allow-list.
