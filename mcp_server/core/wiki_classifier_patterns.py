"""Wiki classifier pattern tables — pure data, no logic.

source: ADR-0296"""

from __future__ import annotations

import re

# ── Rejection patterns ────────────────────────────────────────────────

REJECT_PREFIXES = (
    "# Tool:",
    "Tool:",
    "tool:",
    "# tool:",
    "System:",
    "system:",
    "<tool_result>",
    "<result>",
    "<command-message>",
    "<command-name>",
    "# <command-message>",
    "# <command-name>",
)

REJECT_TITLES = {
    "tool-edit",
    "tool-bash",
    "tool-read",
    "tool-write",
    "tool-grep",
    "tool-glob",
    "tool-search",
}

REJECT_PATTERNS = [
    # Leading `#+\s*` tolerates markdown heading prefix before the keyword
    re.compile(r"^#*\s*Implement the following plan", re.IGNORECASE),
    re.compile(r"^#*\s*Execute the following", re.IGNORECASE),
    re.compile(r"^#*\s*You must respond with only", re.IGNORECASE),
    re.compile(r"^#*\s*Perform all verification", re.IGNORECASE),
    re.compile(r"^#*\s*Take the code and split", re.IGNORECASE),
    re.compile(r"^\s*\{[\s\S]*\}\s*$"),  # Pure JSON object
    re.compile(r"^\s*\[[\s\S]*\]\s*$"),  # Pure JSON array
    # Slash-command invocations — only Claude Code UI framing, no knowledge content
    re.compile(r"<command-(message|name|args)>", re.IGNORECASE),
    # source: ADR-0296
    re.compile(r"^#*\s*Spell:\s*\w+", re.IGNORECASE),
    # Test content shape markers
    re.compile(r"^#*\s*Shape test content", re.IGNORECASE),
]

# ── Classification patterns ───────────────────────────────────────────

ADR_PATTERNS = [
    re.compile(
        r"\b(decided to|decision:|the decision is|"
        r"chose .+ because|rejected .+ (due to|because)|"
        r"we will use|selected .+ over)\b",
        re.IGNORECASE,
    ),
]

LESSON_PATTERNS = [
    re.compile(
        r"\b(the bug was|root cause|lesson learned|mistake was|"
        r"never again|fix:|fixed by|"
        r"the issue was|the problem was|turned out)\b",
        re.IGNORECASE,
    ),
]

CONVENTION_PATTERNS = [
    re.compile(
        r"\b(always use|never |the canonical|convention:|rule:|standard:|"
        r"must follow|naming convention|coding standard)\b",
        re.IGNORECASE,
    ),
]

SPEC_TAGS = {"spec", "design", "specification", "feature"}

# source: ADR-0296


# Imperative verbs in title/first line (task-shaped, not knowledge-shaped)
IMPERATIVE_TITLE_PATTERNS = [
    re.compile(
        r"^\s*#*\s*(let'?s|lets)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*#*\s*("
        r"use|fetch|take|give|look at|verify|audit|check|make|do|run|"
        r"push|remove|rename|adapt|implement|execute|perform|replace|"
        r"add|delete|update|modify|fix|install|setup|configure|"
        r"create|build|write|test|sync|import|export|move|copy|ensure|"
        r"try|go|start|stop|open|close|clean|restart|refactor|migrate|"
        r"enable|disable|apply|reset|rebuild|regenerate|analyze"
        r")\b",
        re.IGNORECASE,
    ),
    # Second-person imperative directed at the AI
    re.compile(r"^\s*#*\s*you (must|should|need|will|can)\b", re.IGNORECASE),
    # Questions-as-titles (without resolution body)
    re.compile(r"^\s*#*\s*(how|what|why|when|where|can|should|is|does)\b[^.]*\?\s*$"),
]

# First-person narration ("we pushed", "I tried", "we did")
FIRST_PERSON_PATTERNS = [
    re.compile(
        r"^\s*#*\s*(we|i)\s+"
        r"(pushed|pulled|did|have|did|tried|ran|found|saw|noticed|got|made|"
        r"created|added|removed|fixed|broke|updated|changed|deleted|merged|"
        r"re?-?started|tested|benchmarked|think|need|want|should|re)",
        re.IGNORECASE,
    ),
]

# Status / progress register — NOT knowledge, but work-log entries
STATUS_PATTERNS = [
    re.compile(
        r"^\s*#*\s*("
        r"successfully|done|failing|failed|broken|working|not working|"
        r"finished|completed|in progress|wip|todo|pending"
        r")\b",
        re.IGNORECASE,
    ),
    # Command/tool output framing
    re.compile(r"local[-_]command[-_](stdout|stderr|stdin|output)", re.IGNORECASE),
    # Test harness metadata
    re.compile(r"session[-_]test[-_]session", re.IGNORECASE),
    re.compile(r"in domain unknown", re.IGNORECASE),
]

# source: ADR-0296

DEIXIS_PATTERNS = [
    re.compile(
        r"^\s*#*\s*("
        r"just now|just did|previous|earlier|last session|new wip|"
        r"the one we|like (we|i) (said|did)|yesterday|today|tomorrow|"
        r"a while ago|recent(ly)?"
        r")\b",
        re.IGNORECASE,
    ),
]

# Path- or URL-shaped titles — these are file/URL access audit records,
# not curated knowledge. Keep them as memories (for recall), refuse
# promotion to the wiki.
PATH_OR_URL_TITLE_PATTERNS = [
    # Absolute POSIX / Windows path as title
    re.compile(r"^\s*#*\s*[/~]"),
    re.compile(r"^\s*#*\s*[A-Za-z]:[\\/]"),  # Windows drive letter
    # URL as title
    re.compile(r"^\s*#*\s*(https?|ftp|file|ssh|git)://", re.IGNORECASE),
    # Lone filename as the bulk of the title
    re.compile(
        r"^\s*#*\s*[\w.-]+\.(pdf|png|jpg|jpeg|svg|gif|zip|tar\.gz|docx?|xlsx?|csv|log|yaml|yml)\b",
        re.IGNORECASE,
    ),
    # source: ADR-0296
    re.compile(r"(?:^|\s)/(Users|home|root|opt|var|etc|tmp)/", re.IGNORECASE),
    re.compile(r"(?:^|\s)[A-Za-z]:[\\/]"),
]

# source: ADR-0296


YAML_KV_TITLE_PATTERNS = [
    # source: ADR-0296
    re.compile(
        r"^\s*(created|updated|date|timestamp|time|id|uuid|version)\s*:\s*\S",
        re.IGNORECASE,
    ),
    # source: ADR-0296
    re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}[:-]\d{2}[:-]\d{2}", re.IGNORECASE),
]

# source: ADR-0296


AUDIT_TAGS = frozenset(
    {
        "_backfill",
        "imported",
        "session-summary",
        "tool-output",
        "auto-captured",
        "tool:bash",
        "tool:edit",
        "tool:write",
        "tool:multiedit",
        "tool:notebookedit",
        "tool:read",
        "tool:notebookread",
        "tool:glob",
        "tool:grep",
        "tool:webfetch",
        "tool:websearch",
        # source: ADR-0296
        "seeded",
        "codebase",
        "code-review",
        "stage-1",
        "stage-2",
        "stage-3",
        "stage-4",
        "stage-5",
        "stage-6",
        "stage-7",
        "stage-8",
        "stage-9",
        "stage-10",
        "stage-11",
        "audit",
        "automated",
        "wip",
        "progress",
    }
)

# Audit/review-shaped title patterns — "stage N:", "code review", "audit:",
# "session N" — these are work-product reports, not durable knowledge.
AUDIT_TITLE_PATTERNS = [
    re.compile(r"\bstage[ -]?\d+\b", re.IGNORECASE),
    re.compile(
        r"\b(code[ -]?review|audit[ -]?report|review[ -]?notes?)\b", re.IGNORECASE
    ),
    re.compile(r"\bsession[ -]?(summary|log|report|\d+)\b", re.IGNORECASE),
]

# ── Positive quality signals (admit only if ≥ threshold) ──────────────

STRUCTURE_HEADING = re.compile(r"^#{1,4}\s+\S", re.MULTILINE)
STRUCTURE_LIST = re.compile(r"^\s*[-*+]\s+\S", re.MULTILINE)
STRUCTURE_CODE = re.compile(r"```\w*\n", re.MULTILINE)
CITATION = re.compile(
    r"\b("
    r"ADR-?\d+|paper|arxiv|doi:|https?://|"
    r"\b[A-Z][a-z]+ (et al\.|&) \d{4}|"
    r"\b[A-Z][a-z]+ \d{4}\b"
    r")",
)
DECLARATIVE = re.compile(
    r"\b(is|are|means|causes?|because|implies|requires?|enables?|prevents?|"
    r"produces?|results? in|leads? to|defined? as|consists of)\b",
    re.IGNORECASE,
)
FILE_OR_ENTITY_REF = re.compile(
    r"\b[a-zA-Z_]\w*\.(py|js|ts|md|json|yaml|sql|go|rs|rb|java)\b|"
    r"\b[a-z_]+\(\)|"
    r"\bclass\s+[A-Z]\w+|"
    r"\bdef\s+[a-z_]\w+"
)

# source: ADR-0296

KNOWLEDGE_TAGS = {
    "decision",
    "adr",
    "architecture",
    "spec",
    "design",
    "lesson",
    "convention",
    "rule",
    "standard",
    "paper",
    "research",
    "reference",
}

# source: ADR-0296

POSITIVE_SCORE_THRESHOLD = 4
