"""Validate or regenerate the tracked decision mirror. # source: ADR-0056"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_server.infrastructure.wiki_decision_index import write_decision_index
from mcp_server.infrastructure.wiki_decision_mirror import check_mirror, generate_mirror


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        print(generate_mirror(args.root))
        write_decision_index(args.root / "wiki")
    errors = check_mirror(args.root)
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print("Project wiki mirrors match their canonical sources.")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
