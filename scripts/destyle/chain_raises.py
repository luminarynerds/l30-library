from __future__ import annotations

from pathlib import Path

import libcst as cst


def _except_name(handler: cst.ExceptHandler) -> str | None:
    """Return the bound name from `except X as e:`, or None if no name bound."""
    if handler.name is None:
        return None
    if isinstance(handler.name.name, cst.Name):
        return handler.name.name.value
    return None


class _Chainer(cst.CSTTransformer):
    def __init__(self) -> None:
        self._except_stack: list[str | None] = []

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
        self._except_stack.append(_except_name(node))

    def leave_ExceptHandler(
        self,
        _original_node: cst.ExceptHandler,
        updated_node: cst.ExceptHandler,
    ) -> cst.ExceptHandler:
        self._except_stack.pop()
        return updated_node

    def leave_Raise(
        self,
        _original_node: cst.Raise,
        updated_node: cst.Raise,
    ) -> cst.Raise:
        if not self._except_stack:
            return updated_node
        if updated_node.exc is None:
            return updated_node
        if updated_node.cause is not None:
            return updated_node
        name = self._except_stack[-1]
        if name is None:
            cause_node = cst.Name("None")
        else:
            cause_node = cst.Name(name)
        return updated_node.with_changes(cause=cst.From(item=cause_node))


def chain_raises(tree: cst.Module) -> cst.Module:
    return tree.visit(_Chainer())


def _process_file(path: Path, apply: bool) -> int:
    src = path.read_text()
    try:
        tree = cst.parse_module(src)
    except cst.ParserSyntaxError:
        return 0
    new_tree = chain_raises(tree)
    new_src = new_tree.code
    if new_src == src:
        return 0
    if apply:
        path.write_text(new_src)
    return 1


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changed = 0
    for p in args.root.rglob("*.py"):
        delta = _process_file(p, apply=args.apply)
        if delta:
            changed += 1
            print(("CHANGE" if args.apply else "WOULD CHANGE"), p)
    print(f"{changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
