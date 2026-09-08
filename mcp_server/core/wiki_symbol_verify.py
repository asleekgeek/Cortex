"""Pure staleness verdict for wiki pages over AST.

source: ADR-0313
"""

from __future__ import annotations

from dataclasses import dataclass

# source: ADR-0313


MIN_SYMBOL_REFS = 3

# source: ADR-0313


STALE_THRESHOLD = 0.5


@dataclass(frozen=True)
class SymbolStalenessDecision:
    """Per-page symbol-staleness verdict."""

    page_id: int | str
    symbol_refs: list[str]
    missing_refs: list[str]
    is_symbol_stale_now: bool
    is_symbol_stale_was: bool
    transitioned: bool
    rationale: str


def evaluate_symbol_staleness(
    *,
    page_id: int | str,
    is_symbol_stale_was: bool,
    symbol_refs: list[str],
    existence: dict[str, bool],
) -> SymbolStalenessDecision:
    """Decide whether a wiki page is symbol-stale.

    Inputs:
      page_id               — page key (row id or wiki path)
      is_symbol_stale_was   — prior flag, for transition detection
      symbol_refs           — qualnames the page cites (see
                              ``wiki_symbol_extract.harvest_page_symbols``)
      existence             — {qualname: True if AP resolved it}

    A page is stale iff:
      - len(symbol_refs) >= MIN_SYMBOL_REFS, AND
      - missing / total   >= STALE_THRESHOLD.

    The verdict is deterministic — given the same inputs it always
    returns the same output — which lets the handler re-run it after
    any AST change without coordinating state.
    """
    if len(symbol_refs) < MIN_SYMBOL_REFS:
        return SymbolStalenessDecision(
            page_id=page_id,
            symbol_refs=symbol_refs,
            missing_refs=[],
            is_symbol_stale_now=False,
            is_symbol_stale_was=is_symbol_stale_was,
            transitioned=is_symbol_stale_was,  # un-staling counts
            rationale=(f"too few symbol refs ({len(symbol_refs)} < {MIN_SYMBOL_REFS})"),
        )
    missing = [q for q in symbol_refs if not existence.get(q, False)]
    fraction = len(missing) / len(symbol_refs)
    is_now = fraction >= STALE_THRESHOLD
    return SymbolStalenessDecision(
        page_id=page_id,
        symbol_refs=symbol_refs,
        missing_refs=missing,
        is_symbol_stale_now=is_now,
        is_symbol_stale_was=is_symbol_stale_was,
        transitioned=is_now != is_symbol_stale_was,
        rationale=(
            f"{len(missing)}/{len(symbol_refs)} symbols missing "
            f"({fraction * 100:.0f}% — threshold "
            f"{int(STALE_THRESHOLD * 100)}%)"
        ),
    )


__all__ = [
    "MIN_SYMBOL_REFS",
    "STALE_THRESHOLD",
    "SymbolStalenessDecision",
    "evaluate_symbol_staleness",
]
