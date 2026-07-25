"""Measure the per-session token cost of the initialize + tools/list exchange,
per tool profile (issue #177 criterion 6).

This is the fixed cost a client pays before the user types anything: the
`initialize.instructions` string plus every advertised tool's schema in
`tools/list`. The profile filter reduces the tool set; this benchmark quantifies
the reduction so the claim "reduces bytes per session" is measured, not asserted.

Token estimate: characters / 4. source: OpenAI tokenizer rule of thumb for
English text (~4 chars/token), https://platform.openai.com/tokenizer — used
only as an order-of-magnitude estimate; the exact serialized byte count (also
reported) is unambiguous and tokenizer-independent.

Run: `python -m benchmarks.mcp_profile_tokens` (from repo root, in the venv).
"""

from __future__ import annotations

import asyncio
import json

from fastmcp import Client, FastMCP

from mcp_server import mcp_prompts, tool_profiles
from mcp_server.__main__ import merged_schemas, register_all
from mcp_server.tool_profile_middleware import ToolProfileMiddleware
from mcp_server.tool_profiles import ToolProfile

_CHARS_PER_TOKEN = 4  # source: OpenAI tokenizer rule of thumb (see module docstring)


def _build(profile: ToolProfile) -> FastMCP:
    server = FastMCP(
        name="bench", version="0", instructions=tool_profiles.instructions(profile)
    )
    register_all(server, codebase=False, prd=False)
    mcp_prompts.register_prompts(server, merged_schemas())
    server.add_middleware(ToolProfileMiddleware(profile))
    return server


async def _list_tools_payload(server: FastMCP) -> tuple[int, str]:
    async with Client(server) as client:
        tools = await client.list_tools()
        return len(tools), json.dumps([t.model_dump(mode="json") for t in tools])


def _measure(profile: ToolProfile) -> dict[str, int]:
    # Build the server on the main thread first: register_all internally calls
    # asyncio.run (apply_param_docs), which cannot run inside a live loop.
    server = _build(profile)
    tool_count, tools_payload = asyncio.run(_list_tools_payload(server))
    instructions = tool_profiles.instructions(profile)
    chars = len(tools_payload) + len(instructions)
    return {
        "tools": tool_count,
        "instructions_chars": len(instructions),
        "tools_list_chars": len(tools_payload),
        "total_chars": chars,
        "est_tokens": chars // _CHARS_PER_TOKEN,
    }


def main() -> None:
    rows = {p.value: _measure(p) for p in (ToolProfile.FULL, ToolProfile.LEAN)}
    full, lean = rows["full"], rows["lean"]
    print("initialize + tools/list per-session cost by profile")
    print("-" * 60)
    for name, r in rows.items():
        print(
            f"{name:5} tools={r['tools']:2d} "
            f"instructions={r['instructions_chars']:5d}c "
            f"tools/list={r['tools_list_chars']:6d}c "
            f"total={r['total_chars']:6d}c ~{r['est_tokens']:5d} tok"
        )
    saved = full["total_chars"] - lean["total_chars"]
    pct = 100 * saved / full["total_chars"] if full["total_chars"] else 0
    print("-" * 60)
    print(
        f"lean saves {saved} chars (~{saved // _CHARS_PER_TOKEN} tokens), "
        f"{pct:.1f}% of the full initialize+tools/list cost"
    )


if __name__ == "__main__":
    main()
