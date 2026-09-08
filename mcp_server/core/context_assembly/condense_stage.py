"""Stage-assembler integration point.

source: ADR-0142
"""

from __future__ import annotations

from mcp_server.core.context_assembly.budget import Placeholder, estimate_tokens
from mcp_server.core.context_assembly.condense_dispatch import condense_memory_content
from mcp_server.core.context_assembly.decomposer import assemble_prompt

# source: ADR-0142


_Section = tuple[str, str, int, str]


def condense_assembled_context(
    own_stage_context: str,
    adjacent_stage_context: str,
    stage_summaries: str,
    current_stage: str,
    token_budget: int,
) -> str:
    """Fit stage_assembler's three raw text blocks into ``token_budget``.

    Precondition: ``token_budget > 0``; the three text args are the raw
    (uncondensed) own/adjacent/summary blocks ``StageAwareContextAssembler
    .assemble()`` produced (``StageContextResult.own_stage_context`` etc.,
    not the already-headered ``assembled_context``).

    Postcondition: returns a single string with the same ``"## <Section>"``
    headers ``StageAwareContextAssembler`` uses, sections with empty
    content omitted. Within budget: byte-identical to the assembler's own
    concatenation (zero behavior change for the already-common case). Over
    budget: each section is priority-condensed (own > adjacent >
    summaries) via ``_condense_sections_over_budget`` — see that helper's
    docstring for the condensation caveats it inherits from
    ``decomposer.assemble_prompt``.
    """
    sections = _build_present_sections(
        own_stage_context, adjacent_stage_context, stage_summaries, current_stage
    )
    total = sum(estimate_tokens(c) for _h, c, _pr, _k in sections)
    if total <= token_budget:
        return "\n\n".join(f"{h}\n\n{c}" for h, c, _pr, _k in sections)
    return _condense_sections_over_budget(sections, token_budget)


def _build_present_sections(
    own_stage_context: str,
    adjacent_stage_context: str,
    stage_summaries: str,
    current_stage: str,
) -> list[_Section]:
    """Strip inputs and keep only the non-empty (header, content, priority,
    key) rows, in own/adjacent/summaries emphasis order."""
    own = own_stage_context.strip()
    adjacent = adjacent_stage_context.strip()
    summaries = stage_summaries.strip()

    # source: ADR-0142

    sections: list[_Section] = [
        (f"## Current Stage Context ({current_stage})", own, 1, "{{OWN_STAGE}}"),
        ("## Related Prior Context", adjacent, 2, "{{ADJACENT_STAGE}}"),
        ("## Stage Summaries", summaries, 3, "{{STAGE_SUMMARIES}}"),
    ]
    return [(h, c, pr, k) for h, c, pr, k in sections if c]


def _condense_sections_over_budget(sections: list[_Section], token_budget: int) -> str:
    """Route over-budget sections through assemble_prompt's priority
    condensation.

    source: ADR-0142"""
    template = "\n\n".join(f"{h}\n\n{k}" for h, _c, _pr, k in sections)
    placeholders = [
        Placeholder(k, c, priority=pr, condenser=condense_memory_content)
        for _h, c, pr, k in sections
    ]
    prompt, _metrics = assemble_prompt(
        template, placeholders, context_window=token_budget, headroom=1.0
    )
    return prompt
