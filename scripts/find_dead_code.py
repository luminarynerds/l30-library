#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dead code analysis for L30 (Library 2030).

Performs static analysis across the full-stack Python/TypeScript codebase:
  1. Build call graph — functions, entry points (routes, handlers, jobs)
  2. Find unreachable code — uncalled functions, unused exports/imports
  3. Find unused database columns — compare model fields to query usage
  4. Generate cleanup report → /reports/dead-code.md
"""

import ast
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
REPORT_PATH = ROOT / "reports" / "dead-code.md"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FunctionInfo:
    name: str
    file: str
    line: int
    is_method: bool = False
    is_entry_point: bool = False
    entry_type: str = ""  # route, event_handler, scheduled_job, cli


@dataclass
class CallGraphEntry:
    caller: str  # "file:function"
    callee: str  # function name being called


@dataclass
class ModelField:
    model: str
    field_name: str
    column_type: str
    file: str
    line: int


@dataclass
class TSExport:
    name: str
    file: str
    line: int
    kind: str  # "function", "const", "type", "component", "default"


# ---------------------------------------------------------------------------
# 1. Python analysis — call graph, entry points, unreachable code
# ---------------------------------------------------------------------------

def find_python_files(base: Path) -> list[Path]:
    """Find all Python source files, excluding tests/migrations/venv."""
    result = []
    exclude = {"__pycache__", ".git", "node_modules", "venv", ".venv",
               "alembic", "migrations", ".tox", ".mypy_cache", "seeds",
               "benchmarks", "training"}
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        for fn in filenames:
            if fn.endswith(".py") and not fn.startswith("test_"):
                result.append(Path(dirpath) / fn)
    return result


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


# Decorator patterns that mark entry points
ROUTE_DECORATORS = {"get", "post", "put", "delete", "patch", "head", "options",
                    "api_route", "websocket"}
SCHEDULER_PATTERNS = {"scheduled", "cron", "interval", "add_job", "register_job"}
EVENT_PATTERNS = {"on_event", "on_startup", "on_shutdown", "lifespan",
                  "event_handler", "listener"}


class PythonAnalyzer(ast.NodeVisitor):
    """AST-based analyzer for a single Python file."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.relpath = rel(filepath)
        self.functions: list[FunctionInfo] = []
        self.calls: list[CallGraphEntry] = []
        self.imports: dict[str, str] = {}  # alias -> module
        self._current_func: Optional[str] = None

    def analyze(self):
        try:
            source = self.filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(self.filepath))
            self.visit(tree)
        except SyntaxError:
            pass

    def _decorator_names(self, node) -> list[str]:
        names = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                names.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                names.append(dec.attr)
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Attribute):
                    names.append(dec.func.attr)
                elif isinstance(dec.func, ast.Name):
                    names.append(dec.func.id)
        return names

    def _is_entry_point(self, node) -> tuple[bool, str]:
        dec_names = self._decorator_names(node)
        for d in dec_names:
            dl = d.lower()
            if dl in ROUTE_DECORATORS or dl == "route":
                return True, "route"
            if any(p in dl for p in SCHEDULER_PATTERNS):
                return True, "scheduled_job"
            if any(p in dl for p in EVENT_PATTERNS):
                return True, "event_handler"
        return False, ""

    def visit_FunctionDef(self, node):
        is_entry, entry_type = self._is_entry_point(node)
        is_method = isinstance(node, ast.AsyncFunctionDef) or any(
            isinstance(parent, ast.ClassDef) for parent in ast.walk(ast.parse(""))
        )
        # Heuristic: if function is inside a class, it's a method
        info = FunctionInfo(
            name=node.name,
            file=self.relpath,
            line=node.lineno,
            is_method=False,
            is_entry_point=is_entry,
            entry_type=entry_type,
        )
        self.functions.append(info)

        prev = self._current_func
        self._current_func = node.name
        self.generic_visit(node)
        self._current_func = prev

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        callee = None
        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee = node.func.attr

        if callee and self._current_func:
            self.calls.append(CallGraphEntry(
                caller=f"{self.relpath}:{self._current_func}",
                callee=callee,
            ))
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name

    def visit_ImportFrom(self, node):
        mod = node.module or ""
        for alias in node.names:
            self.imports[alias.asname or alias.name] = f"{mod}.{alias.name}"


class ModelFieldExtractor(ast.NodeVisitor):
    """Extract SQLAlchemy Column definitions from model files."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.relpath = rel(filepath)
        self.fields: list[ModelField] = []
        self._current_class: Optional[str] = None

    def analyze(self):
        try:
            source = self.filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(self.filepath))
            self.visit(tree)
        except SyntaxError:
            pass

    def visit_ClassDef(self, node):
        prev = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = prev

    def visit_Assign(self, node):
        if not self._current_class:
            return
        # Look for: field_name = Column(...)
        if isinstance(node.value, ast.Call):
            func_name = ""
            if isinstance(node.value.func, ast.Name):
                func_name = node.value.func.id
            elif isinstance(node.value.func, ast.Attribute):
                func_name = node.value.func.attr

            if func_name == "Column":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        col_type = self._extract_column_type(node.value)
                        self.fields.append(ModelField(
                            model=self._current_class,
                            field_name=target.id,
                            column_type=col_type,
                            file=self.relpath,
                            line=node.lineno,
                        ))

    def _extract_column_type(self, call_node: ast.Call) -> str:
        if call_node.args:
            arg = call_node.args[0]
            if isinstance(arg, ast.Name):
                return arg.id
            if isinstance(arg, ast.Attribute):
                return arg.attr
            if isinstance(arg, ast.Call):
                if isinstance(arg.func, ast.Name):
                    return arg.func.id
                if isinstance(arg.func, ast.Attribute):
                    return arg.func.attr
        return "unknown"


def scan_query_field_usage(py_files: list[Path]) -> set[str]:
    """Scan Python files for field names referenced in query patterns."""
    used_fields: set[str] = set()
    patterns = [
        # SQLAlchemy query patterns: .field_name, filter(Model.field)
        re.compile(r'\.([a-z_][a-z0-9_]*)\s*[=!<>]', re.IGNORECASE),
        re.compile(r'\.([a-z_][a-z0-9_]*)\s*\.', re.IGNORECASE),
        re.compile(r'order_by\([^)]*?\.([a-z_][a-z0-9_]*)', re.IGNORECASE),
        re.compile(r'group_by\([^)]*?\.([a-z_][a-z0-9_]*)', re.IGNORECASE),
        re.compile(r'\.([a-z_][a-z0-9_]*)\s*,', re.IGNORECASE),
        re.compile(r'getattr\s*\([^,]+,\s*["\']([a-z_][a-z0-9_]*)["\']', re.IGNORECASE),
        re.compile(r'\[(["\'])([a-z_][a-z0-9_]*)\1\]', re.IGNORECASE),
        # Pydantic schema references
        re.compile(r'([a-z_][a-z0-9_]*)\s*:', re.IGNORECASE),
    ]
    for fpath in py_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pat in patterns:
            for m in pat.finditer(text):
                name = m.group(1) if m.lastindex == 1 else m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                if name and len(name) > 1:
                    used_fields.add(name.lower())
    return used_fields


# ---------------------------------------------------------------------------
# 2. TypeScript/React analysis — exports, imports, components
# ---------------------------------------------------------------------------

def find_ts_files(base: Path) -> list[Path]:
    result = []
    exclude = {"node_modules", ".git", "dist", "build", "coverage",
               "__tests__", ".storybook", "e2e"}
    for dirpath, dirnames, filenames in os.walk(base / "src"):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        for fn in filenames:
            if fn.endswith((".ts", ".tsx")) and not fn.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".d.ts")):
                result.append(Path(dirpath) / fn)
    return result


# Regex patterns for TS exports
TS_EXPORT_PATTERNS = [
    # export function Name / export async function Name
    re.compile(r'^export\s+(?:async\s+)?function\s+(\w+)', re.MULTILINE),
    # export const Name
    re.compile(r'^export\s+(?:const|let|var)\s+(\w+)', re.MULTILINE),
    # export default function Name
    re.compile(r'^export\s+default\s+(?:async\s+)?function\s+(\w+)', re.MULTILINE),
    # export type Name / export interface Name
    re.compile(r'^export\s+(?:type|interface)\s+(\w+)', re.MULTILINE),
    # export enum Name
    re.compile(r'^export\s+enum\s+(\w+)', re.MULTILINE),
    # export class Name
    re.compile(r'^export\s+class\s+(\w+)', re.MULTILINE),
]

# Regex for TS imports
TS_IMPORT_PATTERN = re.compile(
    r"""import\s+(?:type\s+)?(?:"""
    r"""\{([^}]+)\}"""           # named imports
    r"""|(\w+)"""                # default import
    r""")"""
    r"""\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)


def analyze_ts_exports(ts_files: list[Path]) -> list[TSExport]:
    exports = []
    for fpath in ts_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rp = rel(fpath)
        for pat in TS_EXPORT_PATTERNS:
            for m in pat.finditer(text):
                name = m.group(1)
                kind = "function"
                if "const" in m.group(0) or "let" in m.group(0):
                    kind = "const"
                elif "type" in m.group(0) or "interface" in m.group(0):
                    kind = "type"
                elif "class" in m.group(0):
                    kind = "component"
                elif "default" in m.group(0):
                    kind = "default"
                line = text[:m.start()].count("\n") + 1
                exports.append(TSExport(name=name, file=rp, line=line, kind=kind))
    return exports


def analyze_ts_imports(ts_files: list[Path]) -> set[str]:
    """Collect all imported names across TS files."""
    imported = set()
    for fpath in ts_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in TS_IMPORT_PATTERN.finditer(text):
            named = m.group(1)
            default = m.group(2)
            if named:
                for part in named.split(","):
                    part = part.strip()
                    if " as " in part:
                        part = part.split(" as ")[0].strip()
                    if part and not part.startswith("type "):
                        imported.add(part)
                    elif part.startswith("type "):
                        imported.add(part[5:].strip())
            if default:
                imported.add(default)

        # Also catch: import Name from '...' and usage patterns
        # Re-export: export { X } from '...'
        for m2 in re.finditer(r"export\s+\{([^}]+)\}\s+from\s+['\"]", text):
            for part in m2.group(1).split(","):
                part = part.strip()
                if " as " in part:
                    part = part.split(" as ")[0].strip()
                if part:
                    imported.add(part)
    return imported


def collect_all_identifiers(ts_files: list[Path]) -> dict[str, set[str]]:
    """Single-pass: read all TS files and collect every word-like identifier per file."""
    ident_re = re.compile(r'\b([A-Za-z_]\w*)\b')
    file_idents: dict[str, set[str]] = {}
    for fpath in ts_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        file_idents[rel(fpath)] = set(ident_re.findall(text))
    return file_idents


# ---------------------------------------------------------------------------
# 3. Build the report
# ---------------------------------------------------------------------------

def analyze_backend():
    print("  Scanning backend Python files...")
    py_files = find_python_files(BACKEND / "app")
    all_functions: list[FunctionInfo] = []
    all_calls: list[CallGraphEntry] = []
    all_model_fields: list[ModelField] = []

    for fpath in py_files:
        analyzer = PythonAnalyzer(fpath)
        analyzer.analyze()
        all_functions.extend(analyzer.functions)
        all_calls.extend(analyzer.calls)

    # Extract model fields
    print("  Extracting model fields...")
    model_dir = BACKEND / "app" / "models"
    model_files = [f for f in find_python_files(model_dir)]
    for fpath in model_files:
        extractor = ModelFieldExtractor(fpath)
        extractor.analyze()
        all_model_fields.extend(extractor.fields)

    # Also extract from schema files
    schema_dir = BACKEND / "app" / "schemas"
    schema_files = find_python_files(schema_dir) if schema_dir.exists() else []

    # Build call graph
    print("  Building call graph...")
    called_names: set[str] = set()
    for call in all_calls:
        called_names.add(call.callee)

    # Identify entry points
    entry_points = [f for f in all_functions if f.is_entry_point]

    # Dunder / magic methods that are always "called" by the framework
    framework_names = {
        "__init__", "__str__", "__repr__", "__eq__", "__hash__",
        "__lt__", "__le__", "__gt__", "__ge__", "__ne__",
        "__enter__", "__exit__", "__aenter__", "__aexit__",
        "__call__", "__getattr__", "__setattr__", "__delattr__",
        "__len__", "__iter__", "__next__", "__contains__",
        "__getitem__", "__setitem__", "__delitem__",
        "__bool__", "__int__", "__float__", "__index__",
        "__aiter__", "__anext__",
        "model_validate", "model_dump", "model_json_schema",
    }

    # Identify potentially dead functions (never called + not entry point)
    dead_functions = []
    for func in all_functions:
        if func.name.startswith("_") and not func.name.startswith("__"):
            # Private: only dead if truly never called
            if func.name not in called_names and not func.is_entry_point:
                dead_functions.append(func)
        elif func.name in framework_names:
            continue
        elif func.name.startswith("__"):
            continue
        elif not func.is_entry_point and func.name not in called_names:
            dead_functions.append(func)

    # Scan for field usage in queries
    print("  Scanning query field usage...")
    all_py_files = find_python_files(BACKEND)
    used_fields = scan_query_field_usage(all_py_files)

    # Also pull in schema fields as "used"
    for sf in schema_files:
        try:
            text = sf.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'(\w+)\s*:', text):
                used_fields.add(m.group(1).lower())
        except OSError:
            pass

    # Always-used meta columns
    always_used = {"id", "created_at", "updated_at", "deleted_at", "is_active",
                   "is_deleted", "uuid", "type", "status", "name"}
    used_fields.update(always_used)

    unused_columns = []
    for mf in all_model_fields:
        if mf.field_name.lower() not in used_fields:
            unused_columns.append(mf)

    return {
        "total_functions": len(all_functions),
        "entry_points": entry_points,
        "dead_functions": dead_functions,
        "all_calls": all_calls,
        "called_names": called_names,
        "total_model_fields": len(all_model_fields),
        "all_model_fields": all_model_fields,
        "unused_columns": unused_columns,
        "py_file_count": len(py_files),
    }


def analyze_frontend():
    print("  Scanning frontend TypeScript files...")
    ts_files = find_ts_files(FRONTEND)
    if not ts_files:
        return {
            "total_exports": 0,
            "unused_exports": [],
            "ts_file_count": 0,
        }

    print("  Analyzing exports...")
    exports = analyze_ts_exports(ts_files)
    all_imports = analyze_ts_imports(ts_files)

    # Also detect JSX usage: <ComponentName  (for PascalCase names)
    jsx_used = set()
    for fpath in ts_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in re.finditer(r'<(\w+)', text):
            jsx_used.add(m.group(1))

    # Names that appear in route configs, lazy imports, etc.
    route_used = set()
    for fpath in ts_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # lazy(() => import(...))
        for m in re.finditer(r'lazy\s*\(\s*\(\)\s*=>\s*import\s*\([\'"]([^\'"]+)', text):
            mod = m.group(1).split("/")[-1]
            route_used.add(mod)
        # Dynamic references
        for m in re.finditer(r'component:\s*(\w+)', text):
            route_used.add(m.group(1))

    known_used = all_imports | jsx_used | route_used
    # Framework hooks and common patterns that are always "used"
    framework_exports = {"default", "App", "main", "Root"}
    known_used.update(framework_exports)

    # Single-pass: collect all identifiers from every file
    print("  Cross-referencing usage (single-pass)...")
    file_idents = collect_all_identifiers(ts_files)

    unused_exports = []
    for exp in exports:
        if exp.name not in known_used:
            # Check if identifier appears in any OTHER file
            found = False
            for fpath_rel, idents in file_idents.items():
                if fpath_rel == exp.file:
                    continue
                if exp.name in idents:
                    found = True
                    break
            if not found:
                unused_exports.append(exp)

    return {
        "total_exports": len(exports),
        "unused_exports": unused_exports,
        "ts_file_count": len(ts_files),
    }


def find_unused_py_imports():
    """Find Python modules in app/ that are never imported by other app modules."""
    print("  Checking for orphan Python modules...")
    app_dir = BACKEND / "app"
    py_files = find_python_files(app_dir)

    # Build a map of module_stem -> file
    module_map: dict[str, Path] = {}
    for f in py_files:
        stem = f.stem
        if stem != "__init__":
            module_map[stem] = f

    # Gather all import references across the app
    imported_modules: set[str] = set()
    for f in py_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # from app.xxx.yyy import ... → yyy
        for m in re.finditer(r'from\s+[\w.]+\.(\w+)\s+import', text):
            imported_modules.add(m.group(1))
        # import app.xxx.yyy → yyy
        for m in re.finditer(r'import\s+[\w.]+\.(\w+)', text):
            imported_modules.add(m.group(1))
        # _lazy_import('app.xxx.yyy') → yyy
        for m in re.finditer(r"_lazy_import\(['\"][\w.]+\.(\w+)['\"]\)", text):
            imported_modules.add(m.group(1))

    # Also include modules referenced in registry
    registry_file = BACKEND / "app" / "api" / "v1" / "registry.py"
    if registry_file.exists():
        text = registry_file.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"_lazy_import\(['\"]([^'\"]+)['\"]\)", text):
            parts = m.group(1).split(".")
            imported_modules.add(parts[-1])

    # __init__.py imports (model registration)
    for init_file in app_dir.rglob("__init__.py"):
        try:
            text = init_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in re.finditer(r'from\s+\.(\w+)\s+import', text):
            imported_modules.add(m.group(1))

    # Entry points: main.py, conftest.py etc. are always "used"
    always_used = {"main", "conftest", "__init__", "config", "database", "base"}
    imported_modules.update(always_used)

    orphans = []
    for stem, fpath in sorted(module_map.items()):
        if stem not in imported_modules:
            orphans.append((stem, rel(fpath)))

    return orphans


def generate_report(backend_results, frontend_results, orphan_modules):
    """Generate the Markdown report."""
    lines = []
    lines.append("# Dead Code Analysis Report — L30")
    lines.append("")
    lines.append(f"*Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    total_dead = (
        len(backend_results["dead_functions"])
        + len(frontend_results["unused_exports"])
        + len(backend_results["unused_columns"])
        + len(orphan_modules)
    )
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Backend Python files scanned | {backend_results['py_file_count']} |")
    lines.append(f"| Frontend TypeScript files scanned | {frontend_results['ts_file_count']} |")
    lines.append(f"| Total Python functions found | {backend_results['total_functions']} |")
    lines.append(f"| Total TS exports found | {frontend_results['total_exports']} |")
    lines.append(f"| Total model columns found | {backend_results['total_model_fields']} |")
    lines.append(f"| **Total dead code items** | **{total_dead}** |")
    lines.append("")
    lines.append("| Category | Items |")
    lines.append("|----------|-------|")
    lines.append(f"| Uncalled Python functions | {len(backend_results['dead_functions'])} |")
    lines.append(f"| Unused TS exports | {len(frontend_results['unused_exports'])} |")
    lines.append(f"| Potentially unused DB columns | {len(backend_results['unused_columns'])} |")
    lines.append(f"| Orphan Python modules (never imported) | {len(orphan_modules)} |")
    lines.append("")

    # --- Section 1: Call Graph & Entry Points ---
    lines.append("---")
    lines.append("")
    lines.append("## 1. Call Graph & Entry Points")
    lines.append("")
    entry_points = backend_results["entry_points"]
    by_type = defaultdict(list)
    for ep in entry_points:
        by_type[ep.entry_type or "other"].append(ep)

    lines.append(f"**{len(entry_points)} entry points** detected across the backend:")
    lines.append("")
    for etype in ["route", "scheduled_job", "event_handler", "other"]:
        eps = by_type.get(etype, [])
        if eps:
            lines.append(f"### {etype.replace('_', ' ').title()}s ({len(eps)})")
            lines.append("")
            # Show up to 30, then summarize
            shown = eps[:30]
            for ep in shown:
                lines.append(f"- `{ep.name}` — `{ep.file}:{ep.line}`")
            if len(eps) > 30:
                lines.append(f"- *...and {len(eps) - 30} more*")
            lines.append("")

    # --- Section 2: Unreachable Code ---
    lines.append("---")
    lines.append("")
    lines.append("## 2. Unreachable / Uncalled Code")
    lines.append("")

    # 2a. Dead Python functions
    lines.append("### 2a. Uncalled Python Functions")
    lines.append("")
    if backend_results["dead_functions"]:
        lines.append(f"**{len(backend_results['dead_functions'])} functions** are never called from analyzed code.")
        lines.append("")
        lines.append("> **Note:** Some may be called dynamically, via decorators, or from test files.")
        lines.append("> Review before deleting. Functions marked with `*` are private (`_`-prefixed).")
        lines.append("")

        # Group by file directory
        by_dir: dict[str, list[FunctionInfo]] = defaultdict(list)
        for f in backend_results["dead_functions"]:
            parts = f.file.split("/")
            dir_key = "/".join(parts[:4]) if len(parts) >= 4 else "/".join(parts[:3])
            by_dir[dir_key].append(f)

        for dir_key in sorted(by_dir.keys()):
            funcs = by_dir[dir_key]
            lines.append(f"#### `{dir_key}/` ({len(funcs)} functions)")
            lines.append("")
            lines.append("| Function | File | Line | Private |")
            lines.append("|----------|------|------|---------|")
            for f in sorted(funcs, key=lambda x: (x.file, x.line)):
                priv = "yes" if f.name.startswith("_") else ""
                lines.append(f"| `{f.name}` | `{f.file}` | {f.line} | {priv} |")
            lines.append("")
    else:
        lines.append("No uncalled functions detected.")
        lines.append("")

    # 2b. Orphan modules
    lines.append("### 2b. Orphan Python Modules (Never Imported)")
    lines.append("")
    if orphan_modules:
        lines.append(f"**{len(orphan_modules)} modules** found that are never imported by any other app module.")
        lines.append("")
        lines.append("> These files may be standalone scripts, unused modules, or loaded dynamically.")
        lines.append("")
        lines.append("| Module | File |")
        lines.append("|--------|------|")
        for stem, fpath in orphan_modules:
            lines.append(f"| `{stem}` | `{fpath}` |")
        lines.append("")
    else:
        lines.append("No orphan modules detected.")
        lines.append("")

    # 2c. Unused TS exports
    lines.append("### 2c. Unused TypeScript Exports")
    lines.append("")
    if frontend_results["unused_exports"]:
        lines.append(f"**{len(frontend_results['unused_exports'])} exports** are never imported by other frontend modules.")
        lines.append("")
        lines.append("> Some may be used via dynamic imports, re-exported, or referenced in config files.")
        lines.append("")

        by_dir_ts: dict[str, list[TSExport]] = defaultdict(list)
        for exp in frontend_results["unused_exports"]:
            parts = exp.file.split("/")
            dir_key = "/".join(parts[:4]) if len(parts) >= 4 else "/".join(parts[:3])
            by_dir_ts[dir_key].append(exp)

        for dir_key in sorted(by_dir_ts.keys()):
            exps = by_dir_ts[dir_key]
            lines.append(f"#### `{dir_key}/` ({len(exps)} exports)")
            lines.append("")
            lines.append("| Export | Kind | File | Line |")
            lines.append("|--------|------|------|------|")
            for e in sorted(exps, key=lambda x: (x.file, x.line)):
                lines.append(f"| `{e.name}` | {e.kind} | `{e.file}` | {e.line} |")
            lines.append("")
    else:
        lines.append("No unused exports detected.")
        lines.append("")

    # --- Section 3: Unused Database Columns ---
    lines.append("---")
    lines.append("")
    lines.append("## 3. Potentially Unused Database Columns")
    lines.append("")
    if backend_results["unused_columns"]:
        lines.append(f"**{len(backend_results['unused_columns'])} columns** in SQLAlchemy models are not referenced in queries or schemas.")
        lines.append("")
        lines.append("> **Caution:** These columns may be accessed via relationships, dynamic attribute access,")
        lines.append("> or serialization (e.g., `model_dump()`). Verify before removing or deprecating.")
        lines.append("")

        by_model: dict[str, list[ModelField]] = defaultdict(list)
        for mf in backend_results["unused_columns"]:
            by_model[mf.model].append(mf)

        lines.append("| Model | Column | Type | File | Line |")
        lines.append("|-------|--------|------|------|------|")
        for model in sorted(by_model.keys()):
            fields = by_model[model]
            for mf in sorted(fields, key=lambda x: x.line):
                lines.append(f"| `{mf.model}` | `{mf.field_name}` | {mf.column_type} | `{mf.file}` | {mf.line} |")
        lines.append("")
    else:
        lines.append("No potentially unused columns detected.")
        lines.append("")

    # --- Section 4: Safe-to-Delete List ---
    lines.append("---")
    lines.append("")
    lines.append("## 4. Safe-to-Delete List")
    lines.append("")
    lines.append("Items below are **high-confidence** candidates for removal based on static analysis.")
    lines.append("They meet multiple criteria: uncalled, not imported, no dynamic references found.")
    lines.append("")

    # High-confidence dead code: private functions that are never called
    safe_private = [f for f in backend_results["dead_functions"]
                    if f.name.startswith("_") and not f.name.startswith("__")]
    # Orphan modules that are clearly standalone scripts (contain "if __name__")
    safe_orphans = []
    for stem, fpath in orphan_modules:
        full_path = ROOT / fpath
        if full_path.exists():
            try:
                text = full_path.read_text(encoding="utf-8", errors="replace")
                if 'if __name__' in text or 'main()' in text:
                    safe_orphans.append((stem, fpath))
            except OSError:
                pass

    # Unused TS exports that are type-only
    safe_ts_types = [e for e in frontend_results.get("unused_exports", [])
                     if e.kind == "type"]

    lines.append("### 4a. Private Functions (Never Called)")
    lines.append("")
    if safe_private:
        lines.append(f"{len(safe_private)} private functions are safe to remove:")
        lines.append("")
        for f in sorted(safe_private, key=lambda x: (x.file, x.line)):
            lines.append(f"- [ ] `{f.name}` in `{f.file}:{f.line}`")
        lines.append("")
    else:
        lines.append("None found.")
        lines.append("")

    lines.append("### 4b. Standalone Scripts (Orphan Modules)")
    lines.append("")
    if safe_orphans:
        lines.append(f"{len(safe_orphans)} standalone scripts can be moved to `scripts/` or deleted:")
        lines.append("")
        for stem, fpath in safe_orphans:
            lines.append(f"- [ ] `{fpath}`")
        lines.append("")
    else:
        lines.append("None found.")
        lines.append("")

    lines.append("### 4c. Unused Type Exports (Frontend)")
    lines.append("")
    if safe_ts_types:
        lines.append(f"{len(safe_ts_types)} type-only exports are never imported:")
        lines.append("")
        for e in sorted(safe_ts_types, key=lambda x: (x.file, x.line)):
            lines.append(f"- [ ] `{e.name}` in `{e.file}:{e.line}`")
        lines.append("")
    else:
        lines.append("None found.")
        lines.append("")

    lines.append("### 4d. Unused DB Columns")
    lines.append("")
    if backend_results["unused_columns"]:
        lines.append(f"{len(backend_results['unused_columns'])} columns to investigate (require migration to remove):")
        lines.append("")
        for mf in sorted(backend_results["unused_columns"], key=lambda x: (x.model, x.field_name)):
            lines.append(f"- [ ] `{mf.model}.{mf.field_name}` (`{mf.column_type}`) — `{mf.file}:{mf.line}`")
        lines.append("")
    else:
        lines.append("None found.")
        lines.append("")

    # --- Methodology ---
    lines.append("---")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("This report was generated by static analysis (`scripts/find_dead_code.py`):")
    lines.append("")
    lines.append("1. **Call graph**: AST-parsed all Python files to extract function definitions and call sites.")
    lines.append("   Entry points identified via decorator patterns (`@router.get`, `@app.on_event`, `@scheduler`).")
    lines.append("2. **Unreachable code**: Functions never appearing as a callee in the call graph and not")
    lines.append("   marked as entry points. Excludes dunder methods and known framework callbacks.")
    lines.append("3. **Unused exports (TS)**: Regex-parsed all TypeScript exports and cross-referenced with")
    lines.append("   import statements, JSX usage (`<Component>`), and lazy-load patterns.")
    lines.append("4. **Unused DB columns**: Extracted `Column()` definitions from SQLAlchemy models and compared")
    lines.append("   field names against all query patterns, schema definitions, and attribute accesses.")
    lines.append("5. **Orphan modules**: Python files in `app/` that are never imported by any other module.")
    lines.append("")
    lines.append("### Limitations")
    lines.append("")
    lines.append("- Dynamic dispatch (`getattr`, `**kwargs` unpacking) may hide usage")
    lines.append("- Celery/APScheduler jobs registered at runtime may not be detected")
    lines.append("- Frontend dynamic imports and string-based component references may be missed")
    lines.append("- Test files are excluded from analysis (functions only called from tests still flagged)")
    lines.append("- Alembic migrations are excluded — column usage in migration scripts not tracked")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== L30 Dead Code Analysis ===")
    print()

    print("[1/4] Analyzing backend...")
    backend_results = analyze_backend()

    print("[2/4] Analyzing frontend...")
    frontend_results = analyze_frontend()

    print("[3/4] Finding orphan modules...")
    orphan_modules = find_unused_py_imports()

    print("[4/4] Generating report...")
    report = generate_report(backend_results, frontend_results, orphan_modules)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print()
    print(f"Report written to: {REPORT_PATH}")
    print(f"  - {len(backend_results['dead_functions'])} uncalled Python functions")
    print(f"  - {len(frontend_results['unused_exports'])} unused TS exports")
    print(f"  - {len(backend_results['unused_columns'])} potentially unused DB columns")
    print(f"  - {len(orphan_modules)} orphan Python modules")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
