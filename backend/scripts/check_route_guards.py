# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Lint rule: every mutating route (@router.post/put/patch/delete) must have
an authorization dependency from the allow-list set, either as a function
parameter Depends() or via the router-level `dependencies=[...]`.

Use `# noqa: role-check` on the route function line, or add the router to
the INTENTIONAL_PUBLIC_ROUTERS list, to suppress for public endpoints
(login, password reset, NCIP, etc.).

Exit 1 with file:line:function violations; exit 0 if clean.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "backend" / "app" / "api"

# Functions that count as a role guard
ROLE_GUARDS = {
    "require_role",
    "require_staff",
    "require_admin",
    "require_director",
    "require_super_admin",
    "require_director_or_super_admin",  # admin_data_export bundle/export gate
    "require_patron",
    "require_authenticated",
    # Authentication-only deps. Routes using these do their own in-body
    # ownership/role checks; the lint catches the *unauthenticated* case.
    "get_current_user",
    "get_age_verified_user",
    # Module-local custom guards that wrap one of the above are listed here
    # to avoid false positives. Keep this list tight.
    "_verify_admin_access",
    "require_staff_role",  # rfid_simulator alias
    "require_legal_access",  # legal/dependencies
    "require_legal_admin",
    "require_board_member",
    "get_current_staff_or_admin",
    "require_setup_token",
    "require_library_admin",  # parent-onboarding admin gate
    "require_teacher_of_school",  # school_reading teacher gate
    "require_director_or_super_admin",  # dependencies.py director/super-admin gate
}

MUTATING_METHODS = {"post", "put", "patch", "delete"}

# Routers whose ALL routes are intentionally public (auth flows, webhooks).
# Path-suffix match on the file relative to backend/app/api.
INTENTIONAL_PUBLIC_FILES = {
    "v1/auth/login.py",
    "v1/auth/password.py",
    "v1/auth/registration.py",
    "v1/auth/magic_link.py",
    "v1/auth/oauth.py",
    "v1/patron_requests.py",  # MetisLib proxy, intentionally public
    "v1/public_positivity.py",
    "v1/translate.py",  # public translation utility
    "v1/site_search.py",  # public click logging
    "v1/sparql.py",  # public SPARQL endpoint
    "v1/offline_sync.py",  # uses signed sync tokens, not session auth
    "v1/account_security.py",  # 2FA verify flows pre-auth
    "v1/privacy/children.py",  # parental consent flows via signed tokens
    "v1/legal/guides.py",
    "v1/legal/wizard.py",
    "v1/legal/calculators.py",
    "v1/legal/providers.py",
    "v1/legal/forms.py",
    "v1/legal/collections.py",
    "v1/board/public_comments.py",  # public comment intake
    "v1/setup/router.py",  # first-run setup wizard, gated by setup-token
    "v1/kiosk.py",  # gated by kiosk-token middleware
}


def _depends_target_name(call: ast.Call) -> str | None:
    """Given a Depends(X) Call node, return the X name (handles X() too)."""
    if not (isinstance(call.func, ast.Name) and call.func.id == "Depends"):
        return None
    if not call.args:
        return None
    arg = call.args[0]
    if isinstance(arg, ast.Name):
        return arg.id
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
        return arg.func.id
    if isinstance(arg, ast.Attribute):
        return arg.attr
    return None


def _router_level_guards(module: ast.Module) -> dict[str, bool]:
    """Map router var name -> has-role-guard-in-dependencies?"""
    result: dict[str, bool] = {}
    for node in ast.walk(module):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if not (
                isinstance(call.func, ast.Name) and call.func.id == "APIRouter"
            ):
                continue
            has_guard = False
            for kw in call.keywords:
                if kw.arg != "dependencies":
                    continue
                if isinstance(kw.value, ast.List):
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Call):
                            name = _depends_target_name(elt)
                            if name in ROLE_GUARDS:
                                has_guard = True
                                break
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    result[tgt.id] = has_guard
    return result


def _module_local_guards(module: ast.Module) -> set[str]:
    """Module-local functions that look like auth/role guards (heuristic)."""
    names: set[str] = set()
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            n = node.name
            if (
                n.startswith("require_")
                or n.startswith("_verify_")
                or n.startswith("_check_")
                or n.startswith("get_current_")
                or n.startswith("_authorize")
            ):
                names.add(n)
    return names


def _function_has_guard(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    extra: set[str],
) -> bool:
    defaults = list(fn.args.defaults) + list(fn.args.kw_defaults)
    for d in defaults:
        if isinstance(d, ast.Call):
            name = _depends_target_name(d)
            if name and (name in ROLE_GUARDS or name in extra):
                return True
    return False


def _decorator_router_and_method(
    dec: ast.expr,
) -> tuple[str, str] | None:
    """Return (router_var_name, method) for @router.post(...) decorators."""
    call = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(call, ast.Attribute) and isinstance(call.value, ast.Name):
        if call.attr in MUTATING_METHODS:
            return call.value.id, call.attr
    return None


def check_file(py: Path, source: str) -> list[str]:
    tree = ast.parse(source, filename=str(py))
    router_guards = _router_level_guards(tree)
    local_guards = _module_local_guards(tree)
    source_lines = source.splitlines()
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            hit = _decorator_router_and_method(dec)
            if not hit:
                continue
            router_var, _method = hit
            # noqa suppression: any line of the function header or decorators
            start = min(
                (d.lineno for d in node.decorator_list),
                default=node.lineno,
            )
            end = node.lineno
            window = source_lines[start - 1 : end]
            if any("noqa: role-check" in line for line in window):
                break
            if router_guards.get(router_var, False):
                break
            if _function_has_guard(node, local_guards):
                break
            # Per-decorator dependencies=[Depends(require_*), ...]
            dec_has_guard = False
            if isinstance(dec, ast.Call):
                for kw in dec.keywords:
                    if kw.arg != "dependencies":
                        continue
                    if isinstance(kw.value, ast.List):
                        for elt in kw.value.elts:
                            if isinstance(elt, ast.Call):
                                nm = _depends_target_name(elt)
                                if nm and (nm in ROLE_GUARDS or nm in local_guards):
                                    dec_has_guard = True
                                    break
            if dec_has_guard:
                break
            violations.append(f"{py}:{node.lineno}:{node.name}")
            break
    return violations


def main(argv: list[str]) -> int:
    positional = [a for a in argv[1:] if not a.startswith("-")]
    targets = [Path(p) for p in positional] if positional else [API_ROOT]
    files: list[Path] = []
    for t in targets:
        if t.is_dir():
            files.extend(t.rglob("*.py"))
        elif t.suffix == ".py":
            files.append(t)
    violations: list[str] = []
    for py in files:
        rel = py.resolve().relative_to(REPO_ROOT / "backend" / "app" / "api")
        if str(rel).replace("\\", "/") in INTENTIONAL_PUBLIC_FILES:
            continue
        if "/tests/" in str(py):
            continue
        try:
            src = py.read_text()
        except OSError:
            continue
        violations.extend(check_file(py, src))
    warn_only = "--warn" in argv
    if violations:
        print(
            "Route-guard lint: unguarded mutating routes "
            "(add Depends(require_role(...)) / require_staff / "
            "require_admin / require_super_admin, or '# noqa: role-check'):",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print(f"\nTotal violations: {len(violations)}", file=sys.stderr)
        if warn_only:
            print(
                "(--warn mode: not failing the build; "
                "drain remaining violations before flipping to error)",
                file=sys.stderr,
            )
            return 0
        return 1
    print("Route-guard lint: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
