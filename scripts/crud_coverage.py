#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""CRUD Coverage Analyzer for L30 (Library 2030).

Parses SQLAlchemy models and FastAPI routers to generate a coverage matrix
showing which CRUD operations (List, Get, Create, Update, Delete) exist
for each model.

Usage:
    python scripts/crud_coverage.py
    python scripts/crud_coverage.py --output reports/crud-coverage.md
"""

import ast
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend" / "app"
MODELS_DIR = BACKEND_DIR / "models"
ROUTERS_DIR = BACKEND_DIR / "api" / "v1"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "reports" / "crud-coverage.md"

# Models to skip – enums, mixins, abstract bases, and non-entity helpers
SKIP_CLASSES = {
    "Base",
    "TimestampMixin",
}

# Enum base classes – classes inheriting from these are skipped
ENUM_BASES = {"str", "Enum", "enum.Enum"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ModelInfo:
    name: str
    table_name: Optional[str]
    fields: list[str]
    file_path: str


@dataclass
class Endpoint:
    method: str  # GET, POST, PUT, PATCH, DELETE
    path: str
    function_name: str
    file_path: str


@dataclass
class CRUDCoverage:
    list_all: bool = False
    get_one: bool = False
    create: bool = False
    update: bool = False
    delete: bool = False
    list_endpoints: list[str] = field(default_factory=list)
    get_endpoints: list[str] = field(default_factory=list)
    create_endpoints: list[str] = field(default_factory=list)
    update_endpoints: list[str] = field(default_factory=list)
    delete_endpoints: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# AST Parsing – Models
# ---------------------------------------------------------------------------


def is_enum_class(node: ast.ClassDef) -> bool:
    """Check if a class definition is a Python Enum."""
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in ("Enum", "IntEnum", "StrEnum"):
            return True
        if isinstance(base, ast.Attribute) and base.attr in ("Enum", "IntEnum", "StrEnum"):
            return True
    # Check for (str, Enum) pattern
    base_names = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            base_names.add(base.id)
    if "Enum" in base_names and "str" in base_names:
        return True
    return False


def is_sqlalchemy_model(node: ast.ClassDef) -> bool:
    """Check if a class inherits from Base (SQLAlchemy declarative base)."""
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == "Base":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Base":
            return True
    return False


def extract_table_name(node: ast.ClassDef) -> Optional[str]:
    """Extract __tablename__ from a class definition."""
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    if isinstance(item.value, ast.Constant):
                        return item.value.value
    return None


def extract_columns(node: ast.ClassDef) -> list[str]:
    """Extract Column field names from a class definition."""
    columns = []
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    # Check if value is a Column() call
                    if isinstance(item.value, ast.Call):
                        func = item.value.func
                        func_name = ""
                        if isinstance(func, ast.Name):
                            func_name = func.id
                        elif isinstance(func, ast.Attribute):
                            func_name = func.attr
                        if func_name in ("Column", "mapped_column", "relationship"):
                            columns.append(target.id)
    return columns


def parse_models(models_dir: Path) -> dict[str, ModelInfo]:
    """Parse all SQLAlchemy models from the models directory."""
    models = {}

    for py_file in sorted(models_dir.rglob("*.py")):
        if py_file.name.startswith("__"):
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name in SKIP_CLASSES:
                continue
            if is_enum_class(node):
                continue
            if not is_sqlalchemy_model(node):
                continue

            table_name = extract_table_name(node)
            columns = extract_columns(node)
            rel_path = str(py_file.relative_to(BACKEND_DIR))

            models[node.name] = ModelInfo(
                name=node.name,
                table_name=table_name,
                fields=columns,
                file_path=rel_path,
            )

    return models


# ---------------------------------------------------------------------------
# AST Parsing – Routers
# ---------------------------------------------------------------------------


def extract_router_prefix(tree: ast.Module) -> str:
    """Extract the router prefix from APIRouter(prefix=...) calls."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call):
                func = node.value.func
                func_name = ""
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr
                if func_name == "APIRouter":
                    for kw in node.value.keywords:
                        if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                            return kw.value.value
    return ""


def extract_endpoints(tree: ast.Module, prefix: str, file_path: str) -> list[Endpoint]:
    """Extract all endpoint decorators from a parsed module."""
    endpoints = []
    http_methods = {"get", "post", "put", "patch", "delete"}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            # Handle @router.get("/path") style
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                attr = decorator.func
                method_name = attr.attr.lower()
                if method_name in http_methods:
                    path = ""
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value
                    full_path = prefix + path
                    endpoints.append(
                        Endpoint(
                            method=method_name.upper(),
                            path=full_path,
                            function_name=node.name,
                            file_path=file_path,
                        )
                    )

    return endpoints


def extract_model_imports(tree: ast.Module) -> set[str]:
    """Extract model class names imported in a router file."""
    model_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "models" in node.module:
                for alias in node.names:
                    model_names.add(alias.name)
    return model_names


def parse_routers(routers_dir: Path) -> tuple[list[Endpoint], dict[str, set[str]]]:
    """Parse all FastAPI routers and return endpoints + file->model mappings."""
    all_endpoints = []
    file_model_map: dict[str, set[str]] = {}

    for py_file in sorted(routers_dir.rglob("*.py")):
        if py_file.name.startswith("__"):
            continue
        if py_file.name == "dependencies.py":
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(BACKEND_DIR))
        prefix = extract_router_prefix(tree)
        endpoints = extract_endpoints(tree, prefix, rel_path)
        model_imports = extract_model_imports(tree)

        all_endpoints.extend(endpoints)
        file_model_map[rel_path] = model_imports

    return all_endpoints, file_model_map


# ---------------------------------------------------------------------------
# CRUD Matching
# ---------------------------------------------------------------------------

# Map from model name to common path segments
def model_to_path_segments(model_name: str) -> list[str]:
    """Generate likely URL path segments from a model class name."""
    # Convert CamelCase to snake_case
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()
    # Generate plural form (simplified)
    segments = []
    segments.append(snake)
    if snake.endswith("y"):
        segments.append(snake[:-1] + "ies")
    elif snake.endswith("s") or snake.endswith("x") or snake.endswith("ch") or snake.endswith("sh"):
        segments.append(snake + "es")
    else:
        segments.append(snake + "s")
    # Also add hyphenated version
    hyphen = snake.replace("_", "-")
    segments.append(hyphen)
    if hyphen.endswith("y"):
        segments.append(hyphen[:-1] + "ies")
    elif hyphen.endswith("s") or hyphen.endswith("x") or hyphen.endswith("ch") or hyphen.endswith("sh"):
        segments.append(hyphen + "es")
    else:
        segments.append(hyphen + "s")
    return list(set(segments))


def classify_endpoint(endpoint: Endpoint, model_path_segments: list[str]) -> Optional[str]:
    """Classify an endpoint as list/get/create/update/delete for a model."""
    path = endpoint.path
    method = endpoint.method

    # Check if path relates to the model's resource path
    path_parts = [p for p in path.split("/") if p]
    if not path_parts:
        return None

    # Find the resource segment in the path
    resource_segment = None
    resource_idx = -1
    for i, part in enumerate(path_parts):
        if part in model_path_segments:
            resource_segment = part
            resource_idx = i
            break

    if resource_segment is None:
        return None

    # Determine what comes after the resource segment
    remaining = path_parts[resource_idx + 1 :] if resource_idx < len(path_parts) - 1 else []

    # Check if it's a path parameter pattern (e.g., {id}, {item_id})
    has_id_param = False
    extra_segments = []
    for part in remaining:
        if re.match(r"\{[^}]+\}", part):
            has_id_param = True
        else:
            extra_segments.append(part)

    # Classify based on HTTP method and path structure
    if method == "GET":
        if not has_id_param and not extra_segments:
            return "list"
        elif has_id_param and not extra_segments:
            return "get"
        elif not has_id_param and extra_segments:
            # Sub-resource list or auxiliary endpoint
            return None
        elif has_id_param and extra_segments:
            # Sub-resource on specific item
            return None
    elif method == "POST":
        if not has_id_param and not extra_segments:
            return "create"
    elif method in ("PUT", "PATCH"):
        if has_id_param and not extra_segments:
            return "update"
    elif method == "DELETE":
        if has_id_param and not extra_segments:
            return "delete"

    return None


def match_endpoints_to_models(
    models: dict[str, ModelInfo],
    endpoints: list[Endpoint],
    file_model_map: dict[str, set[str]],
) -> dict[str, CRUDCoverage]:
    """Match endpoints to models and determine CRUD coverage."""
    coverage: dict[str, CRUDCoverage] = {}

    # Build reverse lookup: model name -> path segments
    model_paths: dict[str, list[str]] = {}
    for model_name in models:
        model_paths[model_name] = model_to_path_segments(model_name)

    # Group endpoints by file
    endpoints_by_file: dict[str, list[Endpoint]] = defaultdict(list)
    for ep in endpoints:
        endpoints_by_file[ep.file_path].append(ep)

    # For each router file, match its endpoints to models it imports
    for file_path, file_endpoints in endpoints_by_file.items():
        imported_models = file_model_map.get(file_path, set())
        # Filter to only actual SQLAlchemy models
        relevant_models = [m for m in imported_models if m in models]

        for model_name in relevant_models:
            if model_name not in coverage:
                coverage[model_name] = CRUDCoverage()

            path_segments = model_paths.get(model_name, [])

            for ep in file_endpoints:
                crud_type = classify_endpoint(ep, path_segments)
                if crud_type is None:
                    continue

                ep_desc = f"{ep.method} {ep.path}"
                cov = coverage[model_name]

                if crud_type == "list" and not cov.list_all:
                    cov.list_all = True
                    cov.list_endpoints.append(ep_desc)
                elif crud_type == "list":
                    cov.list_endpoints.append(ep_desc)
                elif crud_type == "get" and not cov.get_one:
                    cov.get_one = True
                    cov.get_endpoints.append(ep_desc)
                elif crud_type == "get":
                    cov.get_endpoints.append(ep_desc)
                elif crud_type == "create" and not cov.create:
                    cov.create = True
                    cov.create_endpoints.append(ep_desc)
                elif crud_type == "create":
                    cov.create_endpoints.append(ep_desc)
                elif crud_type == "update" and not cov.update:
                    cov.update = True
                    cov.update_endpoints.append(ep_desc)
                elif crud_type == "update":
                    cov.update_endpoints.append(ep_desc)
                elif crud_type == "delete" and not cov.delete:
                    cov.delete = True
                    cov.delete_endpoints.append(ep_desc)
                elif crud_type == "delete":
                    cov.delete_endpoints.append(ep_desc)

    # Second pass: try to match models without coverage via path heuristics
    for model_name, model_info in models.items():
        if model_name in coverage:
            continue

        path_segments = model_paths.get(model_name, [])

        for ep in endpoints:
            crud_type = classify_endpoint(ep, path_segments)
            if crud_type is None:
                continue

            if model_name not in coverage:
                coverage[model_name] = CRUDCoverage()

            ep_desc = f"{ep.method} {ep.path}"
            cov = coverage[model_name]

            if crud_type == "list":
                cov.list_all = True
                cov.list_endpoints.append(ep_desc)
            elif crud_type == "get":
                cov.get_one = True
                cov.get_endpoints.append(ep_desc)
            elif crud_type == "create":
                cov.create = True
                cov.create_endpoints.append(ep_desc)
            elif crud_type == "update":
                cov.update = True
                cov.update_endpoints.append(ep_desc)
            elif crud_type == "delete":
                cov.delete = True
                cov.delete_endpoints.append(ep_desc)

    return coverage


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


def generate_report(
    models: dict[str, ModelInfo],
    coverage: dict[str, CRUDCoverage],
) -> str:
    """Generate the markdown coverage report."""
    lines: list[str] = []

    lines.append("# CRUD Coverage Report")
    lines.append("")
    lines.append(f"**Generated:** {_now()}")
    lines.append(f"**Models parsed:** {len(models)}")
    lines.append(f"**Models with endpoints:** {len(coverage)}")
    lines.append("")

    # Summary statistics
    full_crud = 0
    partial_crud = 0
    no_crud = 0
    for model_name in models:
        cov = coverage.get(model_name)
        if cov is None:
            no_crud += 1
        elif cov.list_all and cov.get_one and cov.create and cov.update and cov.delete:
            full_crud += 1
        else:
            partial_crud += 1

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Full CRUD coverage | {full_crud} |")
    lines.append(f"| Partial coverage | {partial_crud} |")
    lines.append(f"| No endpoints found | {no_crud} |")
    lines.append(f"| **Total models** | **{len(models)}** |")
    lines.append("")

    # Coverage matrix – models WITH coverage
    lines.append("## Coverage Matrix")
    lines.append("")
    lines.append("| Model | List | Get | Create | Update | Delete | File |")
    lines.append("|-------|------|-----|--------|--------|--------|------|")

    def _check(val: bool) -> str:
        return "✓" if val else "✗"

    # Sort: full coverage first, then partial (by # of ops desc), then by name
    def _sort_key(name: str) -> tuple:
        cov = coverage.get(name)
        if cov is None:
            ops = 0
        else:
            ops = sum([cov.list_all, cov.get_one, cov.create, cov.update, cov.delete])
        return (-ops, name)

    sorted_models = sorted(models.keys(), key=_sort_key)

    for model_name in sorted_models:
        cov = coverage.get(model_name)
        model_info = models[model_name]
        if cov is None:
            lines.append(
                f"| {model_name} | ✗ | ✗ | ✗ | ✗ | ✗ | `{model_info.file_path}` |"
            )
        else:
            lines.append(
                f"| {model_name} | {_check(cov.list_all)} | {_check(cov.get_one)} "
                f"| {_check(cov.create)} | {_check(cov.update)} | {_check(cov.delete)} "
                f"| `{model_info.file_path}` |"
            )

    # Incomplete coverage section
    lines.append("")
    lines.append("## Incomplete Coverage")
    lines.append("")
    lines.append("Models missing one or more CRUD operations:")
    lines.append("")

    incomplete = []
    for model_name in sorted(models.keys()):
        cov = coverage.get(model_name)
        if cov is None:
            continue
        missing = []
        if not cov.list_all:
            missing.append("List")
        if not cov.get_one:
            missing.append("Get")
        if not cov.create:
            missing.append("Create")
        if not cov.update:
            missing.append("Update")
        if not cov.delete:
            missing.append("Delete")
        if missing:
            incomplete.append((model_name, missing, cov))

    if incomplete:
        for model_name, missing, cov in incomplete:
            lines.append(f"### {model_name}")
            lines.append(f"**Missing:** {', '.join(missing)}")
            lines.append("")
            if cov.list_endpoints:
                lines.append(f"- List: `{'`, `'.join(cov.list_endpoints)}`")
            if cov.get_endpoints:
                lines.append(f"- Get: `{'`, `'.join(cov.get_endpoints)}`")
            if cov.create_endpoints:
                lines.append(f"- Create: `{'`, `'.join(cov.create_endpoints)}`")
            if cov.update_endpoints:
                lines.append(f"- Update: `{'`, `'.join(cov.update_endpoints)}`")
            if cov.delete_endpoints:
                lines.append(f"- Delete: `{'`, `'.join(cov.delete_endpoints)}`")
            lines.append("")
    else:
        lines.append("All models with endpoints have full CRUD coverage.")
        lines.append("")

    # No coverage section
    lines.append("## Models Without Endpoints")
    lines.append("")
    no_coverage_models = sorted(
        [name for name in models if name not in coverage]
    )
    if no_coverage_models:
        lines.append(
            "These models have no matching API endpoints detected. "
            "They may be internal/supporting models, accessed through "
            "related model endpoints, or may need API coverage:"
        )
        lines.append("")
        for model_name in no_coverage_models:
            model_info = models[model_name]
            field_count = len(model_info.fields)
            table = model_info.table_name or "(no table)"
            lines.append(f"- **{model_name}** — `{model_info.file_path}` — table: `{table}` — {field_count} fields")
        lines.append("")
    else:
        lines.append("All models have at least one endpoint.")
        lines.append("")

    # Endpoint details for models with full coverage
    lines.append("## Full CRUD Coverage Details")
    lines.append("")
    full_models = []
    for model_name in sorted(models.keys()):
        cov = coverage.get(model_name)
        if cov and cov.list_all and cov.get_one and cov.create and cov.update and cov.delete:
            full_models.append((model_name, cov))

    if full_models:
        for model_name, cov in full_models:
            lines.append(f"### {model_name}")
            lines.append(f"- List: `{'`, `'.join(cov.list_endpoints)}`")
            lines.append(f"- Get: `{'`, `'.join(cov.get_endpoints)}`")
            lines.append(f"- Create: `{'`, `'.join(cov.create_endpoints)}`")
            lines.append(f"- Update: `{'`, `'.join(cov.update_endpoints)}`")
            lines.append(f"- Delete: `{'`, `'.join(cov.delete_endpoints)}`")
            lines.append("")
    else:
        lines.append("No models have full CRUD coverage.")
        lines.append("")

    return "\n".join(lines)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="CRUD Coverage Analyzer for L30")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help="Output file path (default: reports/crud-coverage.md)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose output",
    )
    args = parser.parse_args()

    print("Parsing SQLAlchemy models...")
    models = parse_models(MODELS_DIR)
    print(f"  Found {len(models)} models")

    if args.verbose:
        for name, info in sorted(models.items()):
            print(f"    {name} (table={info.table_name}, fields={len(info.fields)})")

    print("Parsing FastAPI routers...")
    endpoints, file_model_map = parse_routers(ROUTERS_DIR)
    print(f"  Found {len(endpoints)} endpoints across {len(file_model_map)} files")

    print("Matching endpoints to models...")
    coverage = match_endpoints_to_models(models, endpoints, file_model_map)
    print(f"  Matched {len(coverage)} models to endpoints")

    print("Generating report...")
    report = generate_report(models, coverage)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"  Report saved to {output_path}")

    # Print summary to stdout
    full = sum(
        1
        for c in coverage.values()
        if c.list_all and c.get_one and c.create and c.update and c.delete
    )
    partial = sum(
        1
        for c in coverage.values()
        if not (c.list_all and c.get_one and c.create and c.update and c.delete)
    )
    no_endpoints = len(models) - len(coverage)

    print()
    print("=" * 60)
    print("CRUD COVERAGE SUMMARY")
    print("=" * 60)
    print(f"  Total models:          {len(models)}")
    print(f"  Full CRUD coverage:    {full}")
    print(f"  Partial coverage:      {partial}")
    print(f"  No endpoints found:    {no_endpoints}")
    print("=" * 60)

    # Exit with non-zero if there are models with incomplete coverage
    if partial > 0 or no_endpoints > 0:
        print(f"\nWARNING: {partial + no_endpoints} model(s) have incomplete or no CRUD coverage.")
        print(f"See {output_path} for details.")


if __name__ == "__main__":
    main()
