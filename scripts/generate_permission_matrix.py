#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Generate a permission matrix for all API endpoints in the L30 Library System.

Parses all FastAPI route files to extract:
  1. Endpoint method + path
  2. Required permissions (require_permission / require_any_permission / require_all_permissions)
  3. Required roles (require_role / require_staff / require_admin / require_director / etc.)
  4. Auth dependencies (get_current_user / get_optional_user)

Then cross-references against the known role hierarchy to produce a markdown
matrix showing which roles can access which endpoints.

Output: /reports/permission-matrix.md
"""

from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "backend" / "app" / "api" / "v1"
OUTPUT_FILE = PROJECT_ROOT / "reports" / "permission-matrix.md"

# Ordered from most to least privileged
ROLES = ["SUPER_ADMIN", "ADMIN", "DIRECTOR", "LEGAL", "STAFF", "PATRON", "CHILD", "BOOKMOBILE", "HOMEBOND"]

# Display-friendly short names for the table columns
ROLE_DISPLAY = {
    "SUPER_ADMIN": "super_admin",
    "ADMIN": "admin",
    "DIRECTOR": "director",
    "LEGAL": "legal",
    "STAFF": "staff",
    "PATRON": "patron",
    "CHILD": "child",
    "BOOKMOBILE": "bookmobile",
    "HOMEBOND": "home_delivery",
}

# Map dependency function names to the roles they allow.
# "require_staff" allows STAFF, ADMIN, SUPER_ADMIN (based on dependencies.py).
DEPENDENCY_ROLE_MAP: dict[str, set[str]] = {
    "require_super_admin": {"SUPER_ADMIN"},
    "require_admin": {"ADMIN", "SUPER_ADMIN"},
    "require_director": {"DIRECTOR", "ADMIN", "SUPER_ADMIN"},
    "require_staff": {"STAFF", "ADMIN", "SUPER_ADMIN"},
    "require_patron": {"PATRON"},
    "require_authenticated": set(ROLES),  # any authenticated user
    "get_current_user": set(ROLES),  # any authenticated user
    "get_optional_user": set(ROLES),  # optional, but accessible
    "get_age_verified_user": set(ROLES),  # any auth + age check
}

# In-body function calls that enforce authorization.
# These are called inside the endpoint function body (not as Depends()).
BODY_AUTH_CALLS: dict[str, tuple[str, set[str]]] = {
    "check_admin_access": ("ROLE", {"ADMIN", "SUPER_ADMIN"}),
    "check_staff_access": ("ROLE", {"STAFF", "ADMIN", "SUPER_ADMIN"}),
    "check_super_admin_access": ("ROLE", {"SUPER_ADMIN"}),
}

# All role name strings that may appear in code (enum or string literal).
ALL_ROLE_STRINGS = set(ROLES)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class EndpointInfo:
    """Parsed information about a single API endpoint."""
    file_path: str  # relative to project root
    method: str  # GET, POST, PUT, PATCH, DELETE
    path: str  # full path including router prefix
    function_name: str
    auth_type: str = "NONE"  # NONE | AUTH | ROLE | PERMISSION
    auth_detail: str = ""  # e.g. "require_staff" or "view_patrons"
    allowed_roles: set[str] = field(default_factory=set)
    required_permissions: list[str] = field(default_factory=list)
    line_number: int = 0


# ---------------------------------------------------------------------------
# AST-based parser
# ---------------------------------------------------------------------------


def extract_string_value(node: ast.expr) -> Optional[str]:
    """Extract a string value from an AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_string_values(node: ast.expr) -> list[str]:
    """Extract string values from an AST node (handles tuples/lists of strings)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.Tuple, ast.List)):
        results = []
        for elt in node.elts:
            v = extract_string_value(elt)
            if v:
                results.append(v)
        return results
    return []


def resolve_attribute(node: ast.expr) -> str:
    """Resolve a dotted attribute like UserRole.ADMIN to 'ADMIN'."""
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def get_router_prefix(tree: ast.Module) -> str:
    """Extract the router prefix from APIRouter(prefix=...) calls."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            func_name = ""
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr
            if func_name == "APIRouter":
                for kw in node.keywords:
                    if kw.arg == "prefix":
                        val = extract_string_value(kw.value)
                        if val:
                            return val
    return ""


def discover_local_auth_deps(tree: ast.Module) -> dict[str, tuple[str, set[str]]]:
    """
    Find locally-defined dependency functions that perform role checks.

    Scans for functions that:
      1. Accept a Depends(get_current_user) parameter
      2. Check current_user.role against a set of UserRole values
      3. Raise HTTPException(403) on failure

    Returns a mapping of function_name -> (auth_type, allowed_roles).
    """
    local_deps: dict[str, tuple[str, set[str]]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Must have a user-related parameter (either Depends(get_current_user) or
        # a typed User param, or a param named current_user/user/admin_user/staff_user)
        has_user_dep = False
        user_param_names = {"current_user", "user", "admin_user", "staff_user"}
        for arg in node.args.args:
            if arg.arg in user_param_names:
                has_user_dep = True
                break
            # Check type annotation for User
            if arg.annotation:
                ann = arg.annotation
                ann_name = ""
                if isinstance(ann, ast.Name):
                    ann_name = ann.id
                elif isinstance(ann, ast.Attribute):
                    ann_name = ann.attr
                if ann_name == "User":
                    has_user_dep = True
                    break
        if not has_user_dep:
            for default in node.args.defaults + [d for d in node.args.kw_defaults if d]:
                if isinstance(default, ast.Call):
                    func = default.func
                    name = ""
                    if isinstance(func, ast.Name):
                        name = func.id
                    elif isinstance(func, ast.Attribute):
                        name = func.attr
                    if name in ("get_current_user", "Depends"):
                        has_user_dep = True
                        break

        if not has_user_dep:
            continue

        # Look for role checks in function body: current_user.role not in (...)
        roles_found: set[str] = set()
        has_403 = False

        # First pass: collect local variable assignments that hold role lists
        local_role_vars = _collect_role_vars(node)

        for child in ast.walk(node):
            # Detect: current_user.role not in (...) or current_user.role in (...)
            if isinstance(child, ast.Compare):
                roles_found |= _extract_role_compare(child, local_role_vars)

            # Detect HTTPException with 403
            if isinstance(child, ast.Call):
                call_name = ""
                if isinstance(child.func, ast.Name):
                    call_name = child.func.id
                elif isinstance(child.func, ast.Attribute):
                    call_name = child.func.attr
                if call_name == "HTTPException":
                    for kw in child.keywords:
                        if kw.arg == "status_code":
                            if isinstance(kw.value, ast.Constant) and kw.value.value == 403:
                                has_403 = True
                            elif isinstance(kw.value, ast.Attribute) and kw.value.attr == "HTTP_403_FORBIDDEN":
                                has_403 = True
                    # Also check positional arg
                    if child.args:
                        arg0 = child.args[0]
                        if isinstance(arg0, ast.Constant) and arg0.value == 403:
                            has_403 = True
                        elif isinstance(arg0, ast.Attribute) and arg0.attr == "HTTP_403_FORBIDDEN":
                            has_403 = True

        if roles_found and has_403:
            local_deps[node.name] = ("ROLE", roles_found)

    return local_deps


def _collect_role_vars(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, set[str]]:
    """Collect local variable assignments that hold role lists/tuples.

    E.g.: valid_roles = [UserRole.DIRECTOR, UserRole.STAFF, UserRole.ADMIN]
    """
    role_vars: dict[str, set[str]] = {}
    for child in ast.walk(func_node):
        if isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name):
                    roles = _extract_roles_from_collection(child.value)
                    if roles:
                        role_vars[target.id] = roles
    return role_vars


def _extract_role_compare(node: ast.Compare, local_vars: dict[str, set[str]] | None = None) -> set[str]:
    """Extract role names from a comparison like `user.role not in [UserRole.ADMIN, ...]`."""
    roles: set[str] = set()

    # We want: <something>.role [not] in <collection>
    left = node.left
    is_role_attr = (
        isinstance(left, ast.Attribute) and left.attr == "role"
    )
    if not is_role_attr:
        return roles

    for comparator in node.comparators:
        # Try to resolve local variable references
        if isinstance(comparator, ast.Name) and local_vars and comparator.id in local_vars:
            roles |= local_vars[comparator.id]
        else:
            roles |= _extract_roles_from_collection(comparator)

    return roles


def _extract_roles_from_collection(node: ast.expr) -> set[str]:
    """Extract role names from a tuple/list/set of UserRole.X or string literals."""
    roles: set[str] = set()

    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for elt in node.elts:
            r = _extract_single_role(elt)
            if r:
                roles.add(r)
    else:
        # Single value comparison
        r = _extract_single_role(node)
        if r:
            roles.add(r)

    return roles


def _extract_single_role(node: ast.expr) -> Optional[str]:
    """Extract a single role name from UserRole.ADMIN or 'ADMIN'."""
    if isinstance(node, ast.Attribute) and node.attr in ALL_ROLE_STRINGS:
        return node.attr
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in ALL_ROLE_STRINGS:
        return node.value
    return None


def detect_body_auth(func_node: ast.FunctionDef | ast.AsyncFunctionDef,
                     local_deps: dict[str, tuple[str, set[str]]]) -> tuple[str, str, set[str]]:
    """
    Detect authorization enforced inside the function body (not via Depends).

    Patterns detected:
      1. check_admin_access(current_user) — known auth call
      2. if current_user.role not in [...]: raise HTTPException(403)
      3. Calls to locally-defined auth functions
    """
    auth_type = "NONE"
    auth_detail = ""
    allowed_roles: set[str] = set()

    for child in ast.walk(func_node):
        # Pattern 1: Known body auth calls (check_admin_access, etc.)
        if isinstance(child, ast.Call):
            call_name = ""
            if isinstance(child.func, ast.Name):
                call_name = child.func.id
            elif isinstance(child.func, ast.Attribute):
                call_name = child.func.attr

            if call_name in BODY_AUTH_CALLS:
                ba_type, ba_roles = BODY_AUTH_CALLS[call_name]
                auth_type = ba_type
                auth_detail = call_name
                allowed_roles |= ba_roles

            # Pattern 3: Calls to locally-defined auth deps
            if call_name in local_deps:
                ld_type, ld_roles = local_deps[call_name]
                if ld_type == "ROLE":
                    auth_type = "ROLE"
                    auth_detail = auth_detail or call_name
                    allowed_roles |= ld_roles

        # Pattern 2: Inline role checks — if current_user.role not in [...]
        if isinstance(child, ast.Compare):
            inline_roles = _extract_role_compare(child)
            if inline_roles:
                # Check if this compare is inside an if-block that raises 403
                # We do a simpler heuristic: if roles were found in a comparison
                # in this function, and the function also raises 403, it's a role check.
                pass  # handled below

    # Pattern 2 (second pass): if we found role comparisons + 403 raises in body
    body_roles: set[str] = set()
    has_403 = False
    body_role_vars = _collect_role_vars(func_node)
    for child in ast.walk(func_node):
        if isinstance(child, ast.Compare):
            body_roles |= _extract_role_compare(child, body_role_vars)
        if isinstance(child, ast.Call):
            call_name = ""
            if isinstance(child.func, ast.Name):
                call_name = child.func.id
            elif isinstance(child.func, ast.Attribute):
                call_name = child.func.attr
            if call_name == "HTTPException":
                for kw in child.keywords:
                    if kw.arg == "status_code":
                        if isinstance(kw.value, ast.Constant) and kw.value.value == 403:
                            has_403 = True
                        elif isinstance(kw.value, ast.Attribute) and kw.value.attr == "HTTP_403_FORBIDDEN":
                            has_403 = True
                if child.args:
                    arg0 = child.args[0]
                    if isinstance(arg0, ast.Constant) and arg0.value == 403:
                        has_403 = True
                    elif isinstance(arg0, ast.Attribute) and arg0.attr == "HTTP_403_FORBIDDEN":
                        has_403 = True

    if body_roles and has_403 and auth_type == "NONE":
        auth_type = "ROLE"
        auth_detail = f"body_check({', '.join(sorted(body_roles))})"
        allowed_roles |= body_roles

    return auth_type, auth_detail, allowed_roles


# Module-level state set by parse_route_file for the current file being parsed.
# Used by analyze_depends_call to recognize locally-defined auth dependencies.
_current_local_deps: dict[str, tuple[str, set[str]]] = {}


def analyze_depends_call(node: ast.expr) -> tuple[str, str, set[str], list[str]]:
    """
    Analyze a Depends(...) call and return:
      (auth_type, auth_detail, allowed_roles, required_permissions)
    """
    auth_type = "NONE"
    auth_detail = ""
    allowed_roles: set[str] = set()
    required_permissions: list[str] = []

    if not isinstance(node, ast.Call):
        return auth_type, auth_detail, allowed_roles, required_permissions

    # Check if it's Depends(something)
    func = node.func
    func_name = ""
    if isinstance(func, ast.Name):
        func_name = func.id
    elif isinstance(func, ast.Attribute):
        func_name = func.attr

    if func_name != "Depends" or not node.args:
        return auth_type, auth_detail, allowed_roles, required_permissions

    dep_arg = node.args[0]

    # Case 1: Depends(require_staff) - direct name reference
    if isinstance(dep_arg, ast.Name):
        dep_name = dep_arg.id
        if dep_name in DEPENDENCY_ROLE_MAP:
            allowed_roles = DEPENDENCY_ROLE_MAP[dep_name].copy()
            auth_type = "ROLE" if dep_name not in ("get_current_user", "get_optional_user", "require_authenticated", "get_age_verified_user") else "AUTH"
            auth_detail = dep_name
        elif dep_name in _current_local_deps:
            # Locally-defined auth dependency in this file
            ld_type, ld_roles = _current_local_deps[dep_name]
            auth_type = ld_type
            auth_detail = dep_name
            allowed_roles = ld_roles.copy()

    # Case 2: Depends(require_permission("view_patrons")) - function call
    elif isinstance(dep_arg, ast.Call):
        inner_func = dep_arg.func
        inner_name = ""
        if isinstance(inner_func, ast.Name):
            inner_name = inner_func.id
        elif isinstance(inner_func, ast.Attribute):
            inner_name = inner_func.attr

        if inner_name == "require_permission":
            if dep_arg.args:
                perm = extract_string_value(dep_arg.args[0])
                if perm:
                    required_permissions.append(perm)
                    auth_type = "PERMISSION"
                    auth_detail = perm

        elif inner_name == "require_any_permission":
            perms = []
            for arg in dep_arg.args:
                v = extract_string_value(arg)
                if v:
                    perms.append(v)
            if perms:
                required_permissions.extend(perms)
                auth_type = "PERMISSION"
                auth_detail = f"any({', '.join(perms)})"

        elif inner_name == "require_all_permissions":
            perms = []
            for arg in dep_arg.args:
                v = extract_string_value(arg)
                if v:
                    perms.append(v)
            if perms:
                required_permissions.extend(perms)
                auth_type = "PERMISSION"
                auth_detail = f"all({', '.join(perms)})"

        elif inner_name == "require_role":
            for arg in dep_arg.args:
                role_name = resolve_attribute(arg)
                if role_name in ROLES:
                    allowed_roles.add(role_name)
            auth_type = "ROLE"
            auth_detail = f"require_role({', '.join(sorted(allowed_roles))})"

        elif inner_name in DEPENDENCY_ROLE_MAP:
            # e.g. Depends(require_staff()) - called with parens
            allowed_roles = DEPENDENCY_ROLE_MAP[inner_name].copy()
            auth_type = "ROLE" if inner_name not in ("get_current_user", "get_optional_user", "require_authenticated") else "AUTH"
            auth_detail = inner_name

        elif inner_name == "_get_current_user":
            # Lazy import wrapper
            allowed_roles = set(ROLES)
            auth_type = "AUTH"
            auth_detail = "get_current_user"

    # Case 3: Depends(attribute access like _get_current_user())
    elif isinstance(dep_arg, ast.Attribute):
        attr_name = dep_arg.attr
        if attr_name in DEPENDENCY_ROLE_MAP:
            allowed_roles = DEPENDENCY_ROLE_MAP[attr_name].copy()
            auth_type = "ROLE" if attr_name not in ("get_current_user", "get_optional_user", "require_authenticated") else "AUTH"
            auth_detail = attr_name

    return auth_type, auth_detail, allowed_roles, required_permissions


def analyze_dependencies_list(dep_list: ast.expr) -> tuple[str, str, set[str], list[str]]:
    """Analyze a dependencies=[...] list for authorization checks."""
    best_auth_type = "NONE"
    best_auth_detail = ""
    combined_roles: set[str] = set()
    combined_perms: list[str] = []

    if not isinstance(dep_list, ast.List):
        return best_auth_type, best_auth_detail, combined_roles, combined_perms

    for elt in dep_list.elts:
        at, ad, roles, perms = analyze_depends_call(elt)
        if at != "NONE":
            if at == "PERMISSION" or (at == "ROLE" and best_auth_type != "PERMISSION"):
                best_auth_type = at
                best_auth_detail = ad
            elif best_auth_type == "NONE":
                best_auth_type = at
                best_auth_detail = ad
            combined_roles.update(roles)
            combined_perms.extend(perms)

    return best_auth_type, best_auth_detail, combined_roles, combined_perms


def parse_route_file(filepath: Path) -> list[EndpointInfo]:
    """Parse a single route file and extract endpoint info."""
    endpoints: list[EndpointInfo] = []
    rel_path = str(filepath.relative_to(PROJECT_ROOT))

    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"  WARNING: Could not parse {rel_path}: {e}", file=sys.stderr)
        return endpoints

    router_prefix = get_router_prefix(tree)

    # Discover locally-defined auth dependency functions in this file
    local_auth_deps = discover_local_auth_deps(tree)

    # Set module-level state so analyze_depends_call can see local deps
    global _current_local_deps
    _current_local_deps = local_auth_deps

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Look at decorators for @router.get/post/put/patch/delete
        for decorator in node.decorator_list:
            method = None
            route_path = ""

            if isinstance(decorator, ast.Call):
                dec_func = decorator.func
                if isinstance(dec_func, ast.Attribute) and dec_func.attr in (
                    "get", "post", "put", "patch", "delete", "api_route",
                ):
                    method = dec_func.attr.upper()
                    if method == "API_ROUTE":
                        method = "MULTI"
                    if decorator.args:
                        route_path = extract_string_value(decorator.args[0]) or ""

                    # Check for dependencies=[] in decorator kwargs
                    dec_auth_type = "NONE"
                    dec_auth_detail = ""
                    dec_roles: set[str] = set()
                    dec_perms: list[str] = []

                    for kw in decorator.keywords:
                        if kw.arg == "dependencies":
                            dec_auth_type, dec_auth_detail, dec_roles, dec_perms = analyze_dependencies_list(kw.value)

                    # Also check function parameters for Depends(...)
                    func_auth_type = "NONE"
                    func_auth_detail = ""
                    func_roles: set[str] = set()
                    func_perms: list[str] = []

                    for arg in node.args.args:
                        # Check default values
                        pass

                    # Check defaults (positional defaults)
                    all_defaults = node.args.defaults
                    # defaults align to the LAST N args
                    num_args = len(node.args.args)
                    num_defaults = len(all_defaults)
                    for i, default in enumerate(all_defaults):
                        arg_idx = num_args - num_defaults + i
                        at, ad, roles, perms = analyze_depends_call(default)
                        if at != "NONE":
                            if at == "PERMISSION" or (at == "ROLE" and func_auth_type != "PERMISSION"):
                                func_auth_type = at
                                func_auth_detail = ad
                            elif func_auth_type == "NONE":
                                func_auth_type = at
                                func_auth_detail = ad
                            func_roles.update(roles)
                            func_perms.extend(perms)

                    # Check keyword-only defaults
                    for default in node.args.kw_defaults:
                        if default is not None:
                            at, ad, roles, perms = analyze_depends_call(default)
                            if at != "NONE":
                                if at == "PERMISSION" or (at == "ROLE" and func_auth_type != "PERMISSION"):
                                    func_auth_type = at
                                    func_auth_detail = ad
                                elif func_auth_type == "NONE":
                                    func_auth_type = at
                                    func_auth_detail = ad
                                func_roles.update(roles)
                                func_perms.extend(perms)

                    # Merge: decorator-level auth takes precedence, but combine roles
                    final_auth_type = dec_auth_type if dec_auth_type != "NONE" else func_auth_type
                    final_auth_detail = dec_auth_detail if dec_auth_detail else func_auth_detail
                    final_roles = dec_roles | func_roles
                    final_perms = list(set(dec_perms + func_perms))

                    # If still only AUTH or NONE, check function body for
                    # in-body auth patterns (check_admin_access, role checks)
                    if final_auth_type in ("NONE", "AUTH"):
                        body_type, body_detail, body_roles = detect_body_auth(node, local_auth_deps)
                        if body_type == "ROLE":
                            final_auth_type = "ROLE"
                            final_auth_detail = body_detail
                            # Body role check narrows access — use body roles
                            # instead of the broad "any authenticated user" set
                            final_roles = body_roles

                    # Build full path
                    full_path = router_prefix + route_path
                    # Normalize double slashes
                    full_path = "/" + full_path.strip("/") if full_path else "/"

                    endpoints.append(EndpointInfo(
                        file_path=rel_path,
                        method=method,
                        path=full_path,
                        function_name=node.name,
                        auth_type=final_auth_type,
                        auth_detail=final_auth_detail,
                        allowed_roles=final_roles,
                        required_permissions=final_perms,
                        line_number=node.lineno,
                    ))

            elif isinstance(decorator, ast.Attribute):
                # Bare decorator like @router.get (no arguments)
                if decorator.attr in ("get", "post", "put", "patch", "delete"):
                    method = decorator.attr.upper()
                    full_path = router_prefix or "/"

                    # Check function params for auth
                    func_auth_type = "NONE"
                    func_auth_detail = ""
                    func_roles: set[str] = set()
                    func_perms: list[str] = []

                    all_defaults = node.args.defaults
                    num_args = len(node.args.args)
                    num_defaults = len(all_defaults)
                    for i, default in enumerate(all_defaults):
                        at, ad, roles, perms = analyze_depends_call(default)
                        if at != "NONE":
                            if at == "PERMISSION" or (at == "ROLE" and func_auth_type != "PERMISSION"):
                                func_auth_type = at
                                func_auth_detail = ad
                            elif func_auth_type == "NONE":
                                func_auth_type = at
                                func_auth_detail = ad
                            func_roles.update(roles)
                            func_perms.extend(perms)

                    for default in node.args.kw_defaults:
                        if default is not None:
                            at, ad, roles, perms = analyze_depends_call(default)
                            if at != "NONE":
                                if at == "PERMISSION" or (at == "ROLE" and func_auth_type != "PERMISSION"):
                                    func_auth_type = at
                                    func_auth_detail = ad
                                elif func_auth_type == "NONE":
                                    func_auth_type = at
                                    func_auth_detail = ad
                                func_roles.update(roles)
                                func_perms.extend(perms)

                    # If still only AUTH or NONE, check function body
                    if func_auth_type in ("NONE", "AUTH"):
                        body_type, body_detail, body_roles = detect_body_auth(node, local_auth_deps)
                        if body_type == "ROLE":
                            func_auth_type = "ROLE"
                            func_auth_detail = body_detail
                            func_roles = body_roles

                    endpoints.append(EndpointInfo(
                        file_path=rel_path,
                        method=method,
                        path=full_path,
                        function_name=node.name,
                        auth_type=func_auth_type,
                        auth_detail=func_auth_detail,
                        allowed_roles=func_roles,
                        required_permissions=list(set(func_perms)),
                        line_number=node.lineno,
                    ))

    return endpoints


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def discover_route_files() -> list[Path]:
    """Find all Python files in the API directory that contain route definitions."""
    route_files = []
    for py_file in sorted(API_DIR.rglob("*.py")):
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
            continue
        # Skip test files, schemas, helpers
        name_lower = py_file.name.lower()
        if any(skip in name_lower for skip in ("schema", "helper", "test_")):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            if "router" in content and ("@router." in content or "APIRouter" in content):
                route_files.append(py_file)
        except (UnicodeDecodeError, OSError):
            continue
    return route_files


# ---------------------------------------------------------------------------
# Matrix generation
# ---------------------------------------------------------------------------


def compute_role_access(ep: EndpointInfo) -> dict[str, str]:
    """
    Determine access for each role. Returns a dict of role -> symbol.

    Symbols:
      ✓  = role has access
      ✗  = role does NOT have access
      ?  = permission-based (cannot determine statically without DB)
      ~  = public / optional auth
    """
    access: dict[str, str] = {}

    if ep.auth_type == "NONE":
        # No auth at all — public endpoint
        for r in ROLES:
            access[r] = "~"
        return access

    if ep.auth_type == "AUTH":
        # Authenticated but no specific role requirement
        for r in ROLES:
            access[r] = "✓"
        return access

    if ep.auth_type == "ROLE":
        for r in ROLES:
            access[r] = "✓" if r in ep.allowed_roles else "✗"
        return access

    if ep.auth_type == "PERMISSION":
        # Permission-based — we can't fully resolve without DB seed data
        # but we mark as "?" for permission-gated
        for r in ROLES:
            if r in ep.allowed_roles:
                access[r] = "✓"
            else:
                access[r] = "?"
        return access

    for r in ROLES:
        access[r] = "?"
    return access


def generate_matrix(endpoints: list[EndpointInfo]) -> str:
    """Generate the markdown permission matrix."""
    lines: list[str] = []

    # Header
    lines.append("# L30 Permission Matrix")
    lines.append("")
    lines.append(f"*Auto-generated by `scripts/generate_permission_matrix.py`*")
    lines.append("")
    lines.append("## Legend")
    lines.append("")
    lines.append("| Symbol | Meaning |")
    lines.append("|--------|---------|")
    lines.append("| ✓ | Role has access |")
    lines.append("| ✗ | Role does NOT have access |")
    lines.append("| ? | Permission-based (requires DB role-permission mapping) |")
    lines.append("| ~ | Public / no authentication required |")
    lines.append("")

    # Summary stats
    total = len(endpoints)
    no_auth = sum(1 for ep in endpoints if ep.auth_type == "NONE")
    auth_only = sum(1 for ep in endpoints if ep.auth_type == "AUTH")
    role_based = sum(1 for ep in endpoints if ep.auth_type == "ROLE")
    perm_based = sum(1 for ep in endpoints if ep.auth_type == "PERMISSION")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total endpoints | {total} |")
    lines.append(f"| No auth (public) | {no_auth} |")
    lines.append(f"| Auth required (any role) | {auth_only} |")
    lines.append(f"| Role-based access | {role_based} |")
    lines.append(f"| Permission-based access | {perm_based} |")
    lines.append("")

    # Group by file for organization
    grouped: dict[str, list[EndpointInfo]] = {}
    for ep in endpoints:
        grouped.setdefault(ep.file_path, []).append(ep)

    # --- Full matrix table ---
    lines.append("## Permission Matrix")
    lines.append("")

    # Table header
    role_headers = " | ".join(ROLE_DISPLAY[r] for r in ROLES)
    lines.append(f"| Endpoint | Auth | {role_headers} |")
    separator = "|----------|------|" + "|".join("-" * (len(ROLE_DISPLAY[r]) + 2) for r in ROLES) + "|"
    lines.append(separator)

    for file_path in sorted(grouped.keys()):
        eps = sorted(grouped[file_path], key=lambda e: (e.path, e.method))
        for ep in eps:
            access = compute_role_access(ep)
            endpoint_str = f"`{ep.method} {ep.path}`"
            auth_str = ep.auth_detail or ep.auth_type
            role_cells = " | ".join(
                f"{access[r]:^{len(ROLE_DISPLAY[r])}}" for r in ROLES
            )
            lines.append(f"| {endpoint_str} | {auth_str} | {role_cells} |")

    lines.append("")

    # --- Gaps: No permission check ---
    lines.append("## Gaps: Endpoints with No Permission Check")
    lines.append("")
    lines.append("These endpoints have **no authentication or authorization** applied.")
    lines.append("They are publicly accessible. Verify this is intentional.")
    lines.append("")

    no_auth_eps = [ep for ep in endpoints if ep.auth_type == "NONE"]
    if no_auth_eps:
        lines.append("| Endpoint | Function | File |")
        lines.append("|----------|----------|------|")
        for ep in sorted(no_auth_eps, key=lambda e: (e.path, e.method)):
            lines.append(f"| `{ep.method} {ep.path}` | `{ep.function_name}` | `{ep.file_path}:{ep.line_number}` |")
    else:
        lines.append("*No gaps found — all endpoints have auth checks.*")
    lines.append("")

    # --- Gaps: Auth-only (no specific role/permission) ---
    lines.append("## Gaps: Endpoints with Auth but No Role Restriction")
    lines.append("")
    lines.append("These endpoints require authentication but allow **any authenticated user**")
    lines.append("(including patrons). Verify that patrons should have access.")
    lines.append("")

    auth_only_eps = [ep for ep in endpoints if ep.auth_type == "AUTH"]
    if auth_only_eps:
        lines.append("| Endpoint | Function | File |")
        lines.append("|----------|----------|------|")
        for ep in sorted(auth_only_eps, key=lambda e: (e.path, e.method)):
            lines.append(f"| `{ep.method} {ep.path}` | `{ep.function_name}` | `{ep.file_path}:{ep.line_number}` |")
    else:
        lines.append("*No gaps found.*")
    lines.append("")

    # --- Gaps: Potentially wrong role access ---
    lines.append("## Review: Sensitive Endpoints Accessible to Non-Staff Roles")
    lines.append("")
    lines.append("Endpoints under staff/admin/board paths that are accessible to non-staff roles.")
    lines.append("")

    sensitive_prefixes = ("/admin", "/staff", "/board", "/strategic", "/audit", "/operations-audit")
    suspect_eps = []
    for ep in endpoints:
        path_lower = ep.path.lower()
        if any(path_lower.startswith(prefix) for prefix in sensitive_prefixes):
            access = compute_role_access(ep)
            non_staff_access = any(
                access.get(r) in ("✓", "~")
                for r in ("PATRON", "CHILD", "BOOKMOBILE", "HOMEBOND")
            )
            if non_staff_access:
                suspect_eps.append(ep)

    if suspect_eps:
        lines.append("| Endpoint | Auth | Concern |")
        lines.append("|----------|------|---------|")
        for ep in sorted(suspect_eps, key=lambda e: (e.path, e.method)):
            concern = "Public" if ep.auth_type == "NONE" else "Open to all authenticated users"
            lines.append(f"| `{ep.method} {ep.path}` | {ep.auth_type} | {concern} |")
    else:
        lines.append("*No issues found.*")
    lines.append("")

    # --- Per-file breakdown ---
    lines.append("## Detailed Breakdown by File")
    lines.append("")

    for file_path in sorted(grouped.keys()):
        eps = sorted(grouped[file_path], key=lambda e: (e.path, e.method))
        short_name = Path(file_path).stem
        lines.append(f"### {short_name}")
        lines.append(f"*File: `{file_path}`*")
        lines.append("")
        lines.append("| Method | Path | Auth | Detail |")
        lines.append("|--------|------|------|--------|")
        for ep in eps:
            detail = ep.auth_detail or "—"
            lines.append(f"| {ep.method} | `{ep.path}` | {ep.auth_type} | {detail} |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("L30 Permission Matrix Generator")
    print("=" * 50)

    # Discover route files
    route_files = discover_route_files()
    print(f"\nFound {len(route_files)} route files to analyze")

    # Parse all endpoints
    all_endpoints: list[EndpointInfo] = []
    for rf in route_files:
        eps = parse_route_file(rf)
        if eps:
            print(f"  {rf.relative_to(PROJECT_ROOT)}: {len(eps)} endpoints")
        all_endpoints.extend(eps)

    print(f"\nTotal endpoints discovered: {len(all_endpoints)}")

    # Categorize
    no_auth = sum(1 for ep in all_endpoints if ep.auth_type == "NONE")
    auth_only = sum(1 for ep in all_endpoints if ep.auth_type == "AUTH")
    role_based = sum(1 for ep in all_endpoints if ep.auth_type == "ROLE")
    perm_based = sum(1 for ep in all_endpoints if ep.auth_type == "PERMISSION")

    print(f"  Public (no auth):     {no_auth}")
    print(f"  Auth required:        {auth_only}")
    print(f"  Role-based:           {role_based}")
    print(f"  Permission-based:     {perm_based}")

    # Generate output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    matrix_md = generate_matrix(all_endpoints)
    OUTPUT_FILE.write_text(matrix_md, encoding="utf-8")

    print(f"\nPermission matrix saved to: {OUTPUT_FILE}")
    print(f"  Total lines: {len(matrix_md.splitlines())}")

    # Summary warnings
    if no_auth > 0:
        print(f"\n  WARNING: {no_auth} endpoints have NO authentication!")

    sensitive_prefixes = ("/admin", "/staff", "/board", "/strategic", "/audit")
    suspect = 0
    for ep in all_endpoints:
        if ep.auth_type == "NONE" and any(ep.path.lower().startswith(p) for p in sensitive_prefixes):
            suspect += 1
    if suspect > 0:
        print(f"  CRITICAL: {suspect} sensitive endpoints have NO auth!")


if __name__ == "__main__":
    main()
