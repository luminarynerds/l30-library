# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lint: every Pydantic input schema must inherit from StrictInputSchema.

Walks ``backend/app/schemas/**/*.py`` (skipping ``_base.py`` and
``__init__.py``), finds class definitions via ``ast``, and reports any
input-shaped class (``*Create`` / ``*Update`` / ``*Request`` / ``*Filter``
/ ``*Submit`` / ``*Payload`` / ``*Input``) that does NOT inherit from
``StrictInputSchema`` either directly OR via a ``*Base`` that itself
inherits ``StrictInputSchema``.

Output classes (``*Response`` / ``*Read`` / ``*Detail`` / ``*List`` /
``*Summary`` / ``*Stats`` / ``*Out`` / ``*Result``) are skipped.

Exit 1 on violations; prints ``file:line:Class`` for each.

Waves A-E (PRs #848, #857, #860, #862, #865) migrated all existing input
schemas. This script locks the migration in.

Run:
    python backend/scripts/check_strict_input_schema.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

INPUT_RE = re.compile(r"(Create|Update|Request|Filter|Submit|Payload|Input)$")
OUTPUT_RE = re.compile(r"(Response|Read|Detail|List|Summary|Stats|Out|Result)$")
STRICT = "StrictInputSchema"

# Directory layout: <repo>/backend/scripts/<this file>
SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "app" / "schemas"


def _bases(node: ast.ClassDef) -> list[str]:
    names: list[str] = []
    for b in node.bases:
        if isinstance(b, ast.Name):
            names.append(b.id)
        elif isinstance(b, ast.Attribute):
            names.append(b.attr)
    return names


def _collect_classes(root: Path) -> dict[str, tuple[Path, int, list[str]]]:
    """Return {class_name: (file, lineno, [base names])} across all schema files."""
    classes: dict[str, tuple[Path, int, list[str]]] = {}
    for py in root.rglob("*.py"):
        if py.name in {"_base.py", "__init__.py"}:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError as exc:
            print(f"{py}: parse error: {exc}", file=sys.stderr)
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes[node.name] = (py, node.lineno, _bases(node))
    return classes


def _inherits_strict(
    class_name: str,
    classes: dict[str, tuple[Path, int, list[str]]],
    seen: set[str] | None = None,
) -> bool:
    """Walk the (in-tree) MRO to see if class transitively inherits StrictInputSchema."""
    if seen is None:
        seen = set()
    if class_name in seen:
        return False
    seen.add(class_name)
    info = classes.get(class_name)
    if info is None:
        return False
    bases = info[2]
    if STRICT in bases:
        return True
    for b in bases:
        if _inherits_strict(b, classes, seen):
            return True
    return False


def main() -> int:
    if not SCHEMAS_DIR.is_dir():
        print(f"Schemas dir not found: {SCHEMAS_DIR}", file=sys.stderr)
        return 2

    classes = _collect_classes(SCHEMAS_DIR)
    violations: list[tuple[Path, int, str]] = []

    for name, (path, lineno, bases) in classes.items():
        if OUTPUT_RE.search(name):
            continue
        if not INPUT_RE.search(name):
            continue
        if STRICT in bases:
            continue
        # Check via any parent in the same schema tree (not just *Base).
        if any(_inherits_strict(b, classes) for b in bases):
            continue
        violations.append((path, lineno, name))

    if violations:
        print(
            f"Found {len(violations)} input schema(s) NOT inheriting "
            f"{STRICT} (directly or via a *Base):",
            file=sys.stderr,
        )
        for path, lineno, name in sorted(violations):
            try:
                rel = path.relative_to(Path.cwd())
            except ValueError:
                rel = path
            print(f"{rel}:{lineno}:{name}", file=sys.stderr)
        print(
            "\nFix: change the class to inherit StrictInputSchema "
            "(from app.schemas._base import StrictInputSchema), or rename "
            "to a non-input suffix if it's actually an output schema.",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: all input schemas under {SCHEMAS_DIR.relative_to(SCHEMAS_DIR.parent.parent.parent)} "
        f"inherit {STRICT}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
