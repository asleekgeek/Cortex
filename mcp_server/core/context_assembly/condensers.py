"""Domain-aware condensers per Cortex memory type.

source: ADR-0145"""

from __future__ import annotations

from mcp_server.core.context_assembly.condense_code import (
    _has_code_blocks as _has_code_blocks,
)
from mcp_server.core.context_assembly.condense_code import (
    _split_by_code_blocks as _split_by_code_blocks,
)
from mcp_server.core.context_assembly.condense_code import (
    condense_assistant_message,
    condense_code_block,
)
from mcp_server.core.context_assembly.condense_dispatch import condense_memory_content
from mcp_server.core.context_assembly.condense_stage import condense_assembled_context
from mcp_server.core.context_assembly.condense_structured import (
    condense_entity_triples,
)
from mcp_server.core.context_assembly.condense_text import (
    _first_sentence as _first_sentence,
)
from mcp_server.core.context_assembly.condense_text import (
    _split_sentences as _split_sentences,
)
from mcp_server.core.context_assembly.condense_text import (
    condense_timeline_event,
    condense_user_message,
)

__all__ = [
    "condense_assembled_context",
    "condense_assistant_message",
    "condense_code_block",
    "condense_entity_triples",
    "condense_memory_content",
    "condense_timeline_event",
    "condense_user_message",
]
