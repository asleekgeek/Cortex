"""Measure the tabular-encoding token delta for recall.

source: ADR-0870
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from mcp_server.core.response_budget import serialized_length
from mcp_server.core.tabular_encoding import encode_within_budget

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "benchmarks" / "longmemeval" / "longmemeval_s.json"
OUT_DIR = REPO / "benchmarks" / "results" / "tabular-170"

# source: ADR-0870


MAX_RESULTS = 10
N_QUERIES = 100

# source: ADR-0870

CHARS_PER_TOKEN = 4

# source: ADR-0870


DECISION_THRESHOLD_PCT = 25.0


def _est_tokens(chars: int) -> int:
    return round(chars / CHARS_PER_TOKEN)


def _iter_turn_contents(fixture: dict) -> list[str]:
    """Flatten every haystack turn's text into one ordered content pool."""
    contents: list[str] = []
    for question in fixture:
        for session in question.get("haystack_sessions", []):
            for turn in session:
                if isinstance(turn, dict) and turn.get("content"):
                    contents.append(turn["content"])
    return contents


def _recall_memory(mid: int, content: str) -> dict:
    """A recall-shaped memory dict — the exact field set the recall handler
    emits for a hit (mcp_server/handlers/recall.py outputSchema)."""
    return {
        "id": f"11111111-0000-0000-0000-{mid:012d}",
        "content": content,
        "score": round(0.95 - (mid % 10) * 0.01, 4),
        "heat": round(0.5 - (mid % 5) * 0.05, 4),
        "domain": "cortex",
        "tags": ["decision", "architecture"],
        "created_at": "2026-07-25T12:00:00Z",
        "source": "recall",
    }


def _recall_envelope(memories: list[dict]) -> dict:
    """The recall response envelope around a memories list (schema-aligned
    keys only — the same shape recall._handler_impl assembles)."""
    return {
        "memories": memories,
        "count": len(memories),
        "intent": "semantic",
        "low_signal_dropped": 0,
        "dispatch_tier": "pg",
    }


def measure() -> dict:
    fixture = json.loads(FIXTURE.read_text())
    pool = _iter_turn_contents(fixture)
    if len(pool) < MAX_RESULTS:
        raise SystemExit(f"corpus too small: {len(pool)} turns")

    per_query: list[dict] = []
    total_json = 0
    total_tab = 0
    cursor = 0
    for _ in range(N_QUERIES):
        window = [pool[(cursor + j) % len(pool)] for j in range(MAX_RESULTS)]
        cursor += MAX_RESULTS
        memories = [_recall_memory(i, c) for i, c in enumerate(window)]

        json_resp = encode_within_budget(_recall_envelope(memories), "memories", "json")
        tab_resp = encode_within_budget(
            _recall_envelope(memories), "memories", "tabular"
        )
        json_chars = serialized_length(json_resp)
        tab_chars = serialized_length(tab_resp)
        total_json += json_chars
        total_tab += tab_chars
        per_query.append(
            {
                "json_chars": json_chars,
                "tabular_chars": tab_chars,
                "tabular_is": tab_resp["format"],
                "reduction_pct": round(100 * (json_chars - tab_chars) / json_chars, 2),
            }
        )

    char_reduction = 100 * (total_json - total_tab) / total_json
    tok_json = _est_tokens(total_json)
    tok_tab = _est_tokens(total_tab)
    tok_reduction = 100 * (tok_json - tok_tab) / tok_json
    return {
        "corpus": "longmemeval_s.json haystack turns as recall memory bodies",
        "n_queries": N_QUERIES,
        "max_results": MAX_RESULTS,
        "fields_per_memory": len(_recall_memory(0, "x")),
        "totals": {
            "json_chars": total_json,
            "tabular_chars": total_tab,
            "char_reduction_pct": round(char_reduction, 2),
            "json_tokens_est": tok_json,
            "tabular_tokens_est": tok_tab,
            "token_reduction_pct": round(tok_reduction, 2),
        },
        "decision_threshold_pct": DECISION_THRESHOLD_PCT,
        "default": "tabular" if char_reduction >= DECISION_THRESHOLD_PCT else "json",
        "per_query_reduction_pct_min": min(q["reduction_pct"] for q in per_query),
        "per_query_reduction_pct_max": max(q["reduction_pct"] for q in per_query),
    }


def sensitivity_by_content_length() -> list[dict]:
    """Tabular reduction as a function of memory content length.

    source: ADR-0870"""
    rows: list[dict] = []
    for length in (24, 48, 96, 192, 384, 768):
        memories = [_recall_memory(i, "x" * length) for i in range(MAX_RESULTS)]
        json_chars = serialized_length(
            encode_within_budget(_recall_envelope(memories), "memories", "json")
        )
        tab_chars = serialized_length(
            encode_within_budget(_recall_envelope(memories), "memories", "tabular")
        )
        rows.append(
            {
                "content_chars": length,
                "json_chars": json_chars,
                "tabular_chars": tab_chars,
                "reduction_pct": round(100 * (json_chars - tab_chars) / json_chars, 2),
            }
        )
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        return "unknown"


def main() -> None:
    result = measure()
    result["sensitivity_by_content_length"] = sensitivity_by_content_length()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    manifest = {
        "issue": 170,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": _git_commit(),
        "method": (
            "encode_within_budget(json) vs encode_within_budget(tabular) over "
            "recall-shaped memory dicts built from longmemeval haystack turns; "
            "size via response_budget.serialized_length; tokens via chars/4 "
            "(Claude Code host estimator)."
        ),
        "script": "benchmarks/tabular_170/measure.py",
        "script_sha256": _sha256(Path(__file__).resolve()),
        "fixture": "benchmarks/longmemeval/longmemeval_s.json",
        "fixture_sha256": _sha256(FIXTURE),
        "result": "result.json",
    }
    (OUT_DIR / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    t = result["totals"]
    print(f"queries={result['n_queries']} max_results={result['max_results']}")
    print(f"json_chars={t['json_chars']}  tabular_chars={t['tabular_chars']}")
    print(f"char_reduction={t['char_reduction_pct']}%")
    print(f"token_reduction={t['token_reduction_pct']}%")
    print(
        f"default -> {result['default']} "
        f"(threshold {result['decision_threshold_pct']}%)"
    )


if __name__ == "__main__":
    main()
