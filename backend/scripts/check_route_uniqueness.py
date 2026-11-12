#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static guard for duplicate router prefixes and operation IDs."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parents[1] / "app" / "api" / "v1"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def parse_file(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    router_prefixes: list[tuple[str, str]] = []
    operation_ids: list[tuple[str, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "APIRouter":
                prefix = ""
                for kw in call.keywords:
                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        prefix = kw.value.value
                        break
                router_prefixes.append((str(path), prefix))

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                    continue
                if dec.func.attr not in HTTP_METHODS:
                    continue
                for kw in dec.keywords:
                    if kw.arg == "operation_id" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        operation_ids.append((kw.value.value, str(path)))

    return router_prefixes, operation_ids


def main() -> int:
    prefix_to_files: defaultdict[str, set[str]] = defaultdict(set)
    op_id_to_files: defaultdict[str, set[str]] = defaultdict(set)

    for py_file in API_ROOT.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        prefixes, operation_ids = parse_file(py_file)
        for file_path, prefix in prefixes:
            prefix_to_files[prefix].add(file_path)
        for operation_id, file_path in operation_ids:
            op_id_to_files[operation_id].add(file_path)

    duplicate_prefixes = {p: files for p, files in prefix_to_files.items() if p and len(files) > 1}
    duplicate_operation_ids = {op: files for op, files in op_id_to_files.items() if len(files) > 1}

    if duplicate_prefixes:
        print("Duplicate APIRouter prefixes found:")
        for prefix, files in sorted(duplicate_prefixes.items()):
            print(f"  {prefix}")
            for file_path in sorted(files):
                print(f"    - {file_path}")

    if duplicate_operation_ids:
        print("Duplicate route operation_id values found:")
        for op_id, files in sorted(duplicate_operation_ids.items()):
            print(f"  {op_id}")
            for file_path in sorted(files):
                print(f"    - {file_path}")

    if duplicate_prefixes or duplicate_operation_ids:
        return 1

    print("No duplicate APIRouter prefixes or operation_id values found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
