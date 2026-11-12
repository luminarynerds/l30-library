# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail if backend/alembic/versions/ has more than one head revision.

A "head" is a revision with no children (nothing else has it as
down_revision). Multi-head divergence silently hides migrations: prod
`alembic upgrade head` only advances one lineage, so the other branch's
DDL never runs. See PR #820 / #869 for the incident this guards against.

Usage:
    python backend/scripts/check_alembic_heads.py
    python backend/scripts/check_alembic_heads.py --versions-dir path/to/versions

Exit codes:
    0 = exactly one head
    1 = multiple heads (drift) OR parse error
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable


def _literal(node: ast.AST):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def parse_migration(path: Path) -> tuple[str | None, tuple[str, ...]]:
    """Return (revision, down_revisions) for a migration file.

    down_revisions is always a tuple: () for None, (x,) for str, or the
    full tuple for merge migrations.
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    revision: str | None = None
    down: tuple[str, ...] = ()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            name = node.targets[0].id
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            value = node.value
            if value is None:
                continue
        else:
            continue
        if name == "revision":
            val = _literal(value)
            if isinstance(val, str):
                revision = val
        elif name == "down_revision":
            val = _literal(value)
            if val is None:
                down = ()
            elif isinstance(val, str):
                down = (val,)
            elif isinstance(val, (list, tuple)):
                down = tuple(v for v in val if isinstance(v, str))
    return revision, down


def find_heads(versions_dir: Path) -> tuple[list[tuple[str, Path]], list[str]]:
    """Return (heads, errors). heads is list of (revision, path)."""
    errors: list[str] = []
    rev_to_path: dict[str, Path] = {}
    children: dict[str, set[str]] = defaultdict(set)

    for path in sorted(versions_dir.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            rev, downs = parse_migration(path)
        except SyntaxError as e:
            errors.append(f"{path}: {e}")
            continue
        if rev is None:
            # Not a migration file (no revision = ...); skip silently.
            continue
        if rev in rev_to_path:
            errors.append(
                f"duplicate revision id {rev!r} in {path} and {rev_to_path[rev]}"
            )
            continue
        rev_to_path[rev] = path
        for d in downs:
            children[d].add(rev)

    heads = [
        (rev, path) for rev, path in rev_to_path.items() if not children.get(rev)
    ]
    heads.sort()
    return heads, errors


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    parser.add_argument("--versions-dir", type=Path, default=default_dir)
    args = parser.parse_args(list(argv) if argv is not None else None)

    versions_dir: Path = args.versions_dir
    if not versions_dir.is_dir():
        print(f"ERROR: versions dir not found: {versions_dir}", file=sys.stderr)
        return 1

    heads, errors = find_heads(versions_dir)

    for err in errors:
        print(f"ERROR: {err}", file=sys.stderr)
    if errors:
        return 1

    if len(heads) <= 1:
        if heads:
            print(f"OK: 1 alembic head ({heads[0][0]})")
        else:
            print("WARNING: no alembic heads found (empty versions dir?)")
        return 0

    print(f"FAIL: alembic has {len(heads)} heads (expected 1):", file=sys.stderr)
    for rev, path in heads:
        print(f"  - {rev}  {path}", file=sys.stderr)
    print(file=sys.stderr)
    print("Fix: create a mergepoint migration that joins these heads.", file=sys.stderr)
    print("  cd backend && alembic merge -m 'merge heads' " + " ".join(r for r, _ in heads), file=sys.stderr)
    print("Then commit the new file in backend/alembic/versions/.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
