from __future__ import annotations

from pathlib import Path

import libcst as cst


def _is_excluded(file_path: str) -> bool:
    p = Path(file_path)
    if p.name == "__init__.py":
        return True
    parts = set(p.parts)
    if "migrations" in parts or "tests" in parts:
        return True
    if "api" in parts:
        return True
    return False


def strip_module_header(tree: cst.Module, file_path: str) -> cst.Module:
    if _is_excluded(file_path):
        return tree
    body = list(tree.body)
    if not body:
        return tree
    first = body[0]
    if not isinstance(first, cst.SimpleStatementLine):
        return tree
    if not first.body or not isinstance(first.body[0], cst.Expr):
        return tree
    val = first.body[0].value
    if not isinstance(val, (cst.SimpleString, cst.ConcatenatedString)):
        return tree
    return tree.with_changes(body=body[1:])


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changed = 0
    for p in args.root.rglob("*.py"):
        if _is_excluded(str(p)):
            continue
        src = p.read_text()
        try:
            tree = cst.parse_module(src)
        except cst.ParserSyntaxError:
            continue
        new_tree = strip_module_header(tree, file_path=str(p))
        if new_tree.code == src:
            continue
        if args.apply:
            p.write_text(new_tree.code)
        changed += 1
        print(("CHANGE" if args.apply else "WOULD CHANGE"), p)
    print(f"{changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
