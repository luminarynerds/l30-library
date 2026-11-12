from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import libcst as cst


ROUTER_DECORATORS = {
    "router.get", "router.post", "router.put",
    "router.patch", "router.delete", "router.options",
    "router.head",
    "app.get", "app.post", "app.put",
    "app.patch", "app.delete",
}


@dataclass
class DocstringHit:
    qualified_name: str


class _Finder(cst.CSTVisitor):
    def __init__(self) -> None:
        self.hits: list[DocstringHit] = []
        self._scope: list[str] = []

    def _is_router_decorated(self, node: cst.FunctionDef) -> bool:
        for dec in node.decorators:
            try:
                rendered = cst.Module(body=[]).code_for_node(dec.decorator)
            except Exception:
                continue
            for marker in ROUTER_DECORATORS:
                if rendered.startswith(marker):
                    return True
        return False

    def _has_docstring(self, node: cst.FunctionDef | cst.ClassDef) -> bool:
        body = node.body
        if not isinstance(body, cst.IndentedBlock):
            return False
        first = body.body[0] if body.body else None
        if not isinstance(first, cst.SimpleStatementLine):
            return False
        if not first.body or not isinstance(first.body[0], cst.Expr):
            return False
        val = first.body[0].value
        return isinstance(val, (cst.SimpleString, cst.ConcatenatedString))

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if self._is_router_decorated(node):
            self._scope.append(node.name.value)
            return True
        if self._has_docstring(node):
            qname = ".".join([*self._scope, node.name.value])
            self.hits.append(DocstringHit(qualified_name=qname))
        self._scope.append(node.name.value)
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._scope.pop()

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if self._has_docstring(node):
            qname = ".".join([*self._scope, node.name.value])
            self.hits.append(DocstringHit(qualified_name=qname))
        self._scope.append(node.name.value)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._scope.pop()


def _is_excluded_path(file_path: str) -> bool:
    p = Path(file_path)
    parts = set(p.parts)
    if "migrations" in parts or "tests" in parts or "test" in parts:
        return True
    return p.name.startswith("test_")


def find_internal_docstrings(tree: cst.Module, file_path: str) -> list[DocstringHit]:
    if _is_excluded_path(file_path):
        return []
    finder = _Finder()
    tree.visit(finder)
    return finder.hits


class _Stripper(cst.CSTTransformer):
    def _is_router_decorated(self, node: cst.FunctionDef) -> bool:
        for dec in node.decorators:
            try:
                rendered = cst.Module(body=[]).code_for_node(dec.decorator)
            except Exception:
                continue
            for marker in ROUTER_DECORATORS:
                if rendered.startswith(marker):
                    return True
        return False

    def _remove_docstring(
        self, body: cst.IndentedBlock
    ) -> cst.IndentedBlock:
        stmts = list(body.body)
        if not stmts:
            return body
        first = stmts[0]
        if not isinstance(first, cst.SimpleStatementLine):
            return body
        if not first.body or not isinstance(first.body[0], cst.Expr):
            return body
        val = first.body[0].value
        if not isinstance(val, (cst.SimpleString, cst.ConcatenatedString)):
            return body
        new_stmts = stmts[1:]
        if not new_stmts:
            new_stmts = [
                cst.SimpleStatementLine(body=[cst.Pass()])
            ]
        return body.with_changes(body=new_stmts)

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if self._is_router_decorated(original_node):
            return updated_node
        if isinstance(updated_node.body, cst.IndentedBlock):
            new_body = self._remove_docstring(updated_node.body)
            return updated_node.with_changes(body=new_body)
        return updated_node

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if isinstance(updated_node.body, cst.IndentedBlock):
            new_body = self._remove_docstring(updated_node.body)
            return updated_node.with_changes(body=new_body)
        return updated_node


def strip_docstrings(tree: cst.Module, file_path: str) -> cst.Module:
    if _is_excluded_path(file_path):
        return tree
    return tree.visit(_Stripper())


def _process_file(path: Path, apply: bool) -> int:
    src = path.read_text()
    try:
        tree = cst.parse_module(src)
    except cst.ParserSyntaxError:
        return 0
    new_tree = strip_docstrings(tree, file_path=str(path))
    new_src = new_tree.code
    if new_src == src:
        return 0
    if apply:
        path.write_text(new_src)
    return 1


def _walk(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if not _is_excluded_path(str(p))]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changed = 0
    for p in _walk(args.root):
        delta = _process_file(p, apply=args.apply)
        if delta:
            changed += 1
            print(("CHANGE" if args.apply else "WOULD CHANGE"), p)
    print(f"{changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
