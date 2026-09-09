"""Truncation warning banner.

source: ADR-0152"""

from __future__ import annotations

from mcp_server.core.context_assembly.budget import AssemblyMetrics


# source: ADR-0152

_SIGNIFICANT_REDUCTION = 0.9


def build_truncation_banner(
    metrics: AssemblyMetrics,
    reduction_threshold: float = _SIGNIFICANT_REDUCTION,
) -> str:
    """Build a ⚠️ banner listing placeholders that were materially condensed.

    Returns an empty string when no placeholder was reduced below the
    threshold (i.e. the prompt fits without loss).

    Args:
        metrics: the AssemblyMetrics populated during prompt assembly.
        reduction_threshold: a placeholder is flagged when its surviving
            fraction is below this value. Default 0.9 (10% reduction).
    """
    truncated: list[tuple[str, int, int]] = []
    for key, original in metrics.original_tokens.items():
        if original <= 0:
            continue
        final = metrics.final_tokens.get(key, 0)
        if final < original and (final / original) < reduction_threshold:
            truncated.append((key, original, final))

    if not truncated:
        return ""

    lines = [
        "⚠️ CONTEXT TRUNCATION WARNING",
        "The following sections were truncated to fit the context window.",
        "You may be missing information. Prioritize the content you CAN see.",
        "",
    ]
    for key, original, final in truncated:
        pct = int(100 * final / original) if original else 0
        lines.append(f"- {key}: {pct}% retained ({final}/{original} tokens)")
    return "\n".join(lines)
