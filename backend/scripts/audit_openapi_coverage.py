#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static OpenAPI coverage audit for FastAPI routers.

This script checks active routers from app/api/v1/registry.py and extracts
route declarations from each active router module to identify endpoints that
should be included in FastAPI OpenAPI docs. It also flags routes explicitly
excluded with include_in_schema=False and router modules that look routable but
are not registered in register_all_routers.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "backend" / "app" / "api" / "v1" / "registry.py"
API_ROOT = REPO_ROOT / "backend" / "app" / "api" / "v1"
OUTPUT_PATH = REPO_ROOT / "backend" / "OPENAPI_COVERAGE_REPORT.md"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


@dataclass(frozen=True)
class Endpoint:
    module: str
    method: str
    path: str
    include_in_schema: bool


def _parse_registry(tree: ast.AST) -> tuple[list[str], dict[str, list[str]]]:
    register_calls: list[str] = []
    module_map: dict[str, list[str]] = {}

    for node in tree.body:  # type: ignore[attr-defined]
        if not isinstance(node, ast.FunctionDef):
            continue

        if node.name == "register_all_routers":
            for stmt in node.body:
                if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
                    continue
                fn = stmt.value.func
                if isinstance(fn, ast.Name) and fn.id.startswith("register_"):
                    register_calls.append(fn.id)
            continue

        if node.name.startswith("register_"):
            mods: list[str] = []
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == "_lazy_import"
                    and child.args
                    and isinstance(child.args[0], ast.Constant)
                    and isinstance(child.args[0].value, str)
                ):
                    mods.append(child.args[0].value)
            if mods:
                module_map[node.name] = mods

    return register_calls, module_map


def _module_to_path(module: str) -> Path:
    parts = module.split(".")
    if parts[:3] != ["app", "api", "v1"]:
        raise ValueError(f"Unexpected module path: {module}")
    return API_ROOT / ("/".join(parts[3:]) + ".py")


def _literal_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_router_names(tree: ast.AST) -> set[str]:
    """Collect variables assigned from APIRouter(...)."""
    router_names: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue

        func = node.value.func
        is_api_router_ctor = (
            isinstance(func, ast.Name) and func.id == "APIRouter"
        ) or (
            isinstance(func, ast.Attribute) and func.attr == "APIRouter"
        )

        if not is_api_router_ctor:
            continue

        for target in node.targets:
            if isinstance(target, ast.Name):
                router_names.add(target.id)

    return router_names


def _route_methods_from_api_route(call: ast.Call) -> list[str]:
    for kw in call.keywords:
        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)):
            methods: list[str] = []
            for item in kw.value.elts:
                method = _literal_str(item)
                if method:
                    methods.append(method.upper())
            return methods
    return []


def _extract_endpoints(module: str, file_path: Path) -> list[Endpoint]:
    if not file_path.exists():
        return []

    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    endpoints: list[Endpoint] = []
    router_names = _collect_router_names(tree)
    if not router_names:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue

            fn = dec.func
            if not (
                isinstance(fn, ast.Attribute)
                and isinstance(fn.value, ast.Name)
                and fn.value.id in router_names
            ):
                continue

            route_path = _literal_str(dec.args[0]) if dec.args else None
            if route_path is None:
                continue

            include_in_schema = True
            for kw in dec.keywords:
                if kw.arg == "include_in_schema" and isinstance(kw.value, ast.Constant):
                    include_in_schema = bool(kw.value.value)

            attr = fn.attr.lower()
            methods: list[str] = []
            if attr in HTTP_METHODS:
                methods = [attr.upper()]
            elif attr == "api_route":
                methods = _route_methods_from_api_route(dec)
            elif attr == "route":
                # route() defaults to all methods at runtime; keep as synthetic marker
                methods = ["ANY"]

            for method in methods:
                endpoints.append(
                    Endpoint(
                        module=module,
                        method=method,
                        path=route_path,
                        include_in_schema=include_in_schema,
                    )
                )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (
            isinstance(fn, ast.Attribute)
            and isinstance(fn.value, ast.Name)
            and fn.value.id in router_names
            and fn.attr == "add_api_route"
        ):
            continue

        route_path = _literal_str(node.args[0]) if node.args else None
        if route_path is None:
            continue

        include_in_schema = True
        methods: list[str] = []
        for kw in node.keywords:
            if kw.arg == "include_in_schema" and isinstance(kw.value, ast.Constant):
                include_in_schema = bool(kw.value.value)
            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)):
                for item in kw.value.elts:
                    method = _literal_str(item)
                    if method:
                        methods.append(method.upper())

        if not methods:
            methods = ["GET"]

        for method in methods:
            endpoints.append(
                Endpoint(
                    module=module,
                    method=method,
                    path=route_path,
                    include_in_schema=include_in_schema,
                )
            )

    return endpoints


def _discover_router_modules() -> set[str]:
    """Find modules that define APIRouter variables and routes."""
    modules: set[str] = set()

    for py in API_ROOT.rglob("*.py"):
        if py.name == "__init__.py":
            continue

        module = "app.api.v1." + ".".join(py.relative_to(API_ROOT).with_suffix("").parts)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        router_names = _collect_router_names(tree)
        if not router_names:
            continue

        has_routes = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id in router_names:
                    if node.func.attr in HTTP_METHODS or node.func.attr in {"api_route", "route", "add_api_route"}:
                        has_routes = True
                        break

        if has_routes:
            modules.add(module)

    return modules


def _format_endpoint(e: Endpoint) -> str:
    return f"- `{e.method} {e.path}` ({e.module})"


def main() -> int:
    registry_tree = ast.parse(REGISTRY_PATH.read_text(encoding="utf-8"))
    register_calls, module_map = _parse_registry(registry_tree)

    active_modules: list[str] = []
    for fn in register_calls:
        active_modules.extend(module_map.get(fn, []))

    # Unique, stable order.
    seen: set[str] = set()
    active_modules_unique = [m for m in active_modules if not (m in seen or seen.add(m))]

    all_router_modules = _discover_router_modules()
    inactive_modules = sorted(all_router_modules - set(active_modules_unique))

    endpoints: list[Endpoint] = []
    for module in active_modules_unique:
        endpoints.extend(_extract_endpoints(module, _module_to_path(module)))

    excluded = [e for e in endpoints if not e.include_in_schema]
    included = [e for e in endpoints if e.include_in_schema]

    lines: list[str] = []
    lines.append("# OpenAPI Coverage Report (Static Audit)\n")
    lines.append("This report is generated by `backend/scripts/audit_openapi_coverage.py`.\n")
    lines.append("## Summary\n")
    lines.append(f"- Active router modules (from registry): **{len(active_modules_unique)}**")
    lines.append(f"- Discovered endpoints in active modules: **{len(endpoints)}**")
    lines.append(f"- Endpoints included in schema by default: **{len(included)}**")
    lines.append(f"- Endpoints explicitly excluded (`include_in_schema=False`): **{len(excluded)}**")
    lines.append(f"- Router modules present but not active in `register_all_routers`: **{len(inactive_modules)}**\n")

    if excluded:
        lines.append("## Endpoints excluded from OpenAPI\n")
        lines.extend(
            _format_endpoint(e)
            for e in sorted(excluded, key=lambda x: (x.module, x.path, x.method))
        )
        lines.append("")

    lines.append("## Inactive router modules (present but not registered)\n")
    if inactive_modules:
        lines.extend(f"- `{m}`" for m in inactive_modules)
    else:
        lines.append("- None")
    lines.append("")

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote report: {OUTPUT_PATH}")
    print(f"Active modules: {len(active_modules_unique)}")
    print(f"Endpoints total: {len(endpoints)}")
    print(f"Excluded from schema: {len(excluded)}")
    print(f"Inactive modules: {len(inactive_modules)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
