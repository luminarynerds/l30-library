"""Pre-commit ratchet: warn on internal-helper docstrings.

Reads files passed as arguments, walks each for internal docstrings.
Currently warn-only; exits 0 even when hits found. Flip WARN_ONLY=False
once backfill is complete and team is ready to fail commits.
"""
from __future__ import annotations

import sys
from pathlib import Path

import libcst as cst

# Add worktree root to sys.path so scripts.destyle imports resolve
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.destyle.strip_docstrings import find_internal_docstrings


WARN_ONLY = True


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv if a.endswith(".py")]
    found_any = False
    for p in files:
        if not p.exists():
            continue
        try:
            tree = cst.parse_module(p.read_text())
        except cst.ParserSyntaxError:
            continue
        hits = find_internal_docstrings(tree, file_path=str(p))
        if hits:
            found_any = True
            for h in hits:
                print(
                    f"WARN: {p}: internal-helper docstring on {h.qualified_name}",
                    file=sys.stderr,
                )
    if found_any and not WARN_ONLY:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
