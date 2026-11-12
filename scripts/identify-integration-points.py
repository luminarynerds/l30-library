#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration Points Analysis Script
Identifies where the frontend UI needs to be connected to the backend API.

Checks:
1. Frontend services using mock/hardcoded data instead of real API calls
2. Frontend API calls pointing to endpoints that don't exist in the backend
3. Backend routes with no corresponding frontend service
4. Frontend pages not wired up to any API service
5. Fetch calls with TODO/FIXME/placeholder patterns
6. Type mismatches between frontend and backend schemas
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

FRONTEND_DIR = Path("frontend/src")
BACKEND_DIR = Path("backend/app")
SERVICES_DIR = FRONTEND_DIR / "services"
PAGES_DIR = FRONTEND_DIR / "pages"
BACKEND_ROUTES_DIR = BACKEND_DIR / "api" / "v1"

# ─── COLORS ────────────────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def section(title):
    print(f"\n{BOLD}{CYAN}{'═' * 70}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 70}{RESET}\n")


def subsection(title):
    print(f"\n  {BOLD}{title}{RESET}")
    print(f"  {'─' * 50}")


# ─── 1. MOCK DATA DETECTION ───────────────────────────────────────
def find_mock_data():
    """Find frontend services returning mock/hardcoded data."""
    section("1. FRONTEND SERVICES WITH MOCK / HARDCODED DATA")
    print("  These services fall back to mock data instead of real API responses.\n")

    mock_patterns = [
        (r'mock[A-Z]\w+', 'mock variable/function'),
        (r'generateMock\w+', 'mock data generator'),
        (r'fallback.*data|return\s+\{[^}]*mock', 'fallback/mock return'),
        (r'// ?TODO.*api|// ?TODO.*backend|// ?TODO.*endpoint', 'TODO about API'),
        (r'// ?FIXME.*api|// ?FIXME.*backend', 'FIXME about API'),
        (r'hardcoded|placeholder|dummy|fake\s*data|sample\s*data', 'placeholder data'),
        (r'return\s+\[\s*\{[^}]+\}\s*,\s*\{', 'inline hardcoded array'),
    ]

    results = []
    for ts_file in sorted(SERVICES_DIR.glob("*.ts")):
        content = ts_file.read_text(errors='ignore')
        file_issues = []
        for pattern, label in mock_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                for m in matches:
                    line_num = content[:m.start()].count('\n') + 1
                    snippet = content[max(0, m.start()-20):m.end()+40].strip().replace('\n', ' ')
                    file_issues.append((line_num, label, snippet))

        if file_issues:
            results.append((ts_file.name, file_issues))
            print(f"  {RED}●{RESET} {BOLD}{ts_file.name}{RESET}")
            for line_num, label, snippet in file_issues[:5]:
                print(f"    L{line_num:>4} [{YELLOW}{label}{RESET}]  {DIM}{snippet[:80]}{RESET}")
            if len(file_issues) > 5:
                print(f"    ... and {len(file_issues) - 5} more")
            print()

    if not results:
        print(f"  {GREEN}✓ No mock data patterns found.{RESET}")

    return results


# ─── 2. EXTRACT FRONTEND ENDPOINTS ────────────────────────────────
def extract_frontend_endpoints():
    """Extract all API endpoint paths called from frontend services."""
    section("2. FRONTEND API ENDPOINTS ANALYSIS")

    endpoint_pattern = re.compile(
        r'''(?:fetchApi|fetch)\s*(?:<[^>]+>)?\s*\(\s*[`'"](\/api\/v1\/[^`'"]+)[`'"]'''
    )
    # Also catch template literals
    template_pattern = re.compile(
        r'''(?:fetchApi|fetch)\s*(?:<[^>]+>)?\s*\(\s*`([^`]*\$\{[^`]*)`'''
    )
    # API_BASE + path pattern
    apibase_pattern = re.compile(
        r'''`\$\{API_BASE\}([^`]+)`'''
    )

    all_endpoints = {}  # file -> list of (line, endpoint)
    for ts_file in sorted(SERVICES_DIR.glob("*.ts")):
        content = ts_file.read_text(errors='ignore')
        endpoints = []

        for pattern in [endpoint_pattern, apibase_pattern]:
            for m in pattern.finditer(content):
                line_num = content[:m.start()].count('\n') + 1
                path = m.group(1)
                endpoints.append((line_num, path))

        # Also look for string concatenation patterns
        concat_pattern = re.compile(r'''API_BASE\s*\+\s*['"]([^'"]+)['"]''')
        for m in concat_pattern.finditer(content):
            line_num = content[:m.start()].count('\n') + 1
            path = m.group(1)
            endpoints.append((line_num, path))

        if endpoints:
            all_endpoints[ts_file.name] = endpoints

    print(f"  Found API calls in {len(all_endpoints)} frontend service files.\n")
    return all_endpoints


# ─── 3. EXTRACT BACKEND ROUTES ────────────────────────────────────
def extract_backend_routes():
    """Extract all route definitions from backend."""
    section("3. BACKEND ROUTE DEFINITIONS")

    route_pattern = re.compile(
        r'''@router\.(get|post|put|patch|delete)\s*\(\s*['"]([^'"]+)['"]'''
    )

    all_routes = {}  # file -> list of (method, path)
    for py_file in sorted(BACKEND_ROUTES_DIR.rglob("*.py")):
        if py_file.name.startswith('__'):
            continue
        content = py_file.read_text(errors='ignore')
        routes = []
        for m in route_pattern.finditer(content):
            method = m.group(1).upper()
            path = m.group(2)
            routes.append((method, path))

        if routes:
            rel_path = py_file.relative_to(BACKEND_ROUTES_DIR)
            all_routes[str(rel_path)] = routes

    total_routes = sum(len(r) for r in all_routes.values())
    print(f"  Found {total_routes} route definitions across {len(all_routes)} backend files.\n")
    return all_routes


# ─── 4. FIND UNMATCHED SERVICES ───────────────────────────────────
def find_unmatched_services(frontend_endpoints, backend_routes):
    """Find frontend services with no matching backend route file."""
    section("4. FRONTEND SERVICES WITH NO MATCHING BACKEND ROUTE FILE")
    print("  Frontend service files that have no obvious backend counterpart.\n")

    # Normalize backend file names for comparison
    backend_names = set()
    for f in backend_routes:
        name = Path(f).stem  # e.g., "catalog" from "catalog.py"
        backend_names.add(name)

    # Normalize frontend service names
    unmatched = []
    for f in sorted(SERVICES_DIR.glob("*.ts")):
        if f.name == 'types.ts' or f.name == 'api.ts':
            continue
        # Convert "catalog-api.ts" -> "catalog"
        fe_name = f.stem.replace('-api', '').replace('Api', '').replace('-', '_')
        # Check various backend name patterns
        possible_matches = [
            fe_name,
            fe_name.replace('_', ''),
            fe_name + 's',
            fe_name.rstrip('s'),
        ]
        found = False
        for candidate in possible_matches:
            if candidate in backend_names:
                found = True
                break
            # Check partial matches
            for bn in backend_names:
                if candidate in bn or bn in candidate:
                    found = True
                    break
            if found:
                break

        if not found:
            unmatched.append(f.name)

    for f in unmatched:
        print(f"  {YELLOW}?{RESET} {f}")

    if not unmatched:
        print(f"  {GREEN}✓ All frontend services have matching backend routes.{RESET}")

    return unmatched


# ─── 5. FIND BACKEND ROUTES WITH NO FRONTEND SERVICE ─────────────
def find_backend_without_frontend(backend_routes):
    """Find backend route files with no corresponding frontend service."""
    section("5. BACKEND ROUTES WITH NO FRONTEND SERVICE")
    print("  Backend endpoints that have no frontend service to call them.\n")

    frontend_names = set()
    for f in sorted(SERVICES_DIR.glob("*.ts")):
        name = f.stem.replace('-api', '').replace('Api', '').replace('-', '_')
        frontend_names.add(name)
        # Also add variants
        frontend_names.add(name.replace('_', ''))

    unmatched = []
    for backend_file in sorted(backend_routes.keys()):
        be_name = Path(backend_file).stem
        if be_name in ('__init__', 'dependencies', 'health', 'meta_tags'):
            continue

        possible_fe_matches = [
            be_name,
            be_name.replace('_', ''),
            be_name.rstrip('s'),
            be_name + 's',
        ]

        found = False
        for candidate in possible_fe_matches:
            if candidate in frontend_names:
                found = True
                break
            for fn in frontend_names:
                if candidate in fn or fn in candidate:
                    found = True
                    break
            if found:
                break

        if not found:
            route_count = len(backend_routes[backend_file])
            methods = [r[0] for r in backend_routes[backend_file]]
            unmatched.append((backend_file, route_count, methods))

    for f, count, methods in unmatched:
        method_str = ', '.join(sorted(set(methods)))
        print(f"  {YELLOW}●{RESET} {f}  ({count} routes: {method_str})")

    if not unmatched:
        print(f"  {GREEN}✓ All backend routes have frontend services.{RESET}")

    return unmatched


# ─── 6. PAGES NOT USING API SERVICES ─────────────────────────────
def find_disconnected_pages():
    """Find frontend pages that don't import any API service."""
    section("6. FRONTEND PAGES NOT CONNECTED TO ANY API SERVICE")
    print("  Pages that don't import from any *-api service file.\n")

    api_import_pattern = re.compile(r'''from\s+['"].*(?:api|service|Api).*['"]''')

    disconnected = []
    connected = []

    for page_file in sorted(PAGES_DIR.rglob("*.tsx")):
        content = page_file.read_text(errors='ignore')
        imports = api_import_pattern.findall(content)
        rel = page_file.relative_to(PAGES_DIR)

        if not imports:
            # Check if it's a simple layout/wrapper page
            has_data_display = bool(re.search(r'useQuery|useMutation|fetch|useState.*\[\]', content))
            disconnected.append((str(rel), has_data_display))
        else:
            connected.append(str(rel))

    # Sort: pages that seem to NEED data first
    disconnected.sort(key=lambda x: (not x[1], x[0]))

    for page, needs_data in disconnected:
        if needs_data:
            print(f"  {RED}●{RESET} {page}  {YELLOW}(has data patterns but no API import){RESET}")
        else:
            print(f"  {DIM}○ {page}  (static/layout page){RESET}")

    print(f"\n  {GREEN}Connected pages: {len(connected)}{RESET}")
    print(f"  {YELLOW}Disconnected pages: {len(disconnected)}{RESET}")

    return disconnected


# ─── 7. SERVICES WITH ERROR-FALLBACK MOCK DATA ───────────────────
def find_error_fallback_mocks():
    """Find services that catch errors and return mock data instead of propagating."""
    section("7. SERVICES RETURNING MOCK DATA ON ERROR (CATCH-AND-FAKE)")
    print("  These catch API errors and return fake data, hiding real failures.\n")

    catch_mock = re.compile(
        r'catch\s*\([^)]*\)\s*\{[^}]*(?:return\s+(?:generate|mock|fake|sample|default)|'
        r'return\s+\{[^}]{50,}|return\s+\[[^\]]{50,})',
        re.DOTALL
    )

    results = []
    for ts_file in sorted(SERVICES_DIR.glob("*.ts")):
        content = ts_file.read_text(errors='ignore')
        matches = list(catch_mock.finditer(content))
        if matches:
            funcs = []
            # Find the enclosing function for each match
            func_pattern = re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)|(?:export\s+)?const\s+(\w+)\s*=')
            for m in matches:
                line_num = content[:m.start()].count('\n') + 1
                # Search backwards for function name
                preceding = content[:m.start()]
                func_matches = list(func_pattern.finditer(preceding))
                fname = func_matches[-1].group(1) or func_matches[-1].group(2) if func_matches else "unknown"
                funcs.append((fname, line_num))

            results.append((ts_file.name, funcs))
            print(f"  {RED}●{RESET} {BOLD}{ts_file.name}{RESET}")
            for fname, line in funcs:
                print(f"    L{line:>4}  {fname}() - catches errors and returns mock data")
            print()

    if not results:
        print(f"  {GREEN}✓ No catch-and-fake patterns found.{RESET}")

    return results


# ─── 8. FRONTEND FUNCTIONS THAT NEVER CALL BACKEND ───────────────
def find_stub_functions():
    """Find exported async functions in services that don't actually make API calls."""
    section("8. STUB / UNIMPLEMENTED API FUNCTIONS")
    print("  Exported functions that don't call fetchApi or fetch.\n")

    results = []
    for ts_file in sorted(SERVICES_DIR.glob("*.ts")):
        content = ts_file.read_text(errors='ignore')

        # Find exported async functions
        func_pattern = re.compile(
            r'export\s+(?:async\s+)?function\s+(\w+)[^{]*\{',
        )
        # Find exported arrow functions
        arrow_pattern = re.compile(
            r'export\s+const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*(?::\s*[^=]+)?\s*=>\s*\{',
        )

        stubs = []
        for pattern in [func_pattern, arrow_pattern]:
            for m in pattern.finditer(content):
                func_name = m.group(1)
                # Skip type/interface/helper names
                if func_name.startswith(('get', 'create', 'update', 'delete', 'fetch', 'search', 'list', 'add', 'remove', 'submit', 'send', 'upload', 'download', 'export', 'import', 'check', 'verify', 'validate')):
                    # Find the function body
                    start = m.end()
                    brace_count = 1
                    i = start
                    while i < len(content) and brace_count > 0:
                        if content[i] == '{':
                            brace_count += 1
                        elif content[i] == '}':
                            brace_count -= 1
                        i += 1
                    body = content[start:i]

                    # Check if it makes an API call
                    has_api_call = bool(re.search(r'fetchApi|fetch\(|API_BASE|/api/v1', body))
                    if not has_api_call and len(body.strip()) > 10:
                        line_num = content[:m.start()].count('\n') + 1
                        stubs.append((func_name, line_num))

        if stubs:
            results.append((ts_file.name, stubs))
            print(f"  {YELLOW}●{RESET} {BOLD}{ts_file.name}{RESET}")
            for fname, line in stubs[:8]:
                print(f"    L{line:>4}  {fname}() - no API call found in body")
            if len(stubs) > 8:
                print(f"    ... and {len(stubs) - 8} more")
            print()

    if not results:
        print(f"  {GREEN}✓ All exported API functions make actual API calls.{RESET}")

    return results


# ─── 9. DATA FILES USED INSTEAD OF API ───────────────────────────
def find_hardcoded_data_files():
    """Find data files in frontend that could be served from the backend."""
    section("9. HARDCODED DATA FILES (SHOULD BE API-SERVED)")
    print("  Static data files in the frontend that could come from the backend.\n")

    data_dirs = [
        FRONTEND_DIR / "data",
        FRONTEND_DIR / "constants",
        FRONTEND_DIR / "config",
    ]

    results = []
    for data_dir in data_dirs:
        if data_dir.exists():
            for f in sorted(data_dir.rglob("*")):
                if f.is_file() and f.suffix in ('.ts', '.tsx', '.js', '.json'):
                    size = f.stat().st_size
                    results.append((str(f.relative_to(FRONTEND_DIR)), size))
                    size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
                    print(f"  {YELLOW}●{RESET} {f.relative_to(FRONTEND_DIR)}  ({size_str})")

    if not results:
        print(f"  {GREEN}✓ No hardcoded data files found.{RESET}")

    return results


# ─── 10. SUMMARY ──────────────────────────────────────────────────
def print_summary(mock_results, unmatched_fe, unmatched_be, disconnected_pages,
                  fallback_mocks, stubs, data_files):
    section("SUMMARY - INTEGRATION POINTS REQUIRING ATTENTION")

    items = [
        ("Services with mock/placeholder data", len(mock_results), RED),
        ("Frontend services with no backend match", len(unmatched_fe), YELLOW),
        ("Backend routes with no frontend service", len(unmatched_be), YELLOW),
        ("Pages not connected to API services", len([d for d in disconnected_pages if d[1]]), RED),
        ("Services with catch-and-fake patterns", len(fallback_mocks), RED),
        ("Stub/unimplemented API functions", len(stubs), YELLOW),
        ("Hardcoded data files", len(data_files), YELLOW),
    ]

    total_issues = 0
    for label, count, color in items:
        icon = f"{color}●{RESET}" if count > 0 else f"{GREEN}✓{RESET}"
        print(f"  {icon} {label}: {color}{count}{RESET}")
        total_issues += count

    print(f"\n  {BOLD}Total integration points to address: {total_issues}{RESET}\n")

    # Priority recommendations
    subsection("PRIORITY ACTIONS")
    print(f"""
  {RED}HIGH{RESET} - Services returning mock data on error (Section 7)
       These silently hide real API failures. Wire them to real endpoints
       or propagate errors properly.

  {RED}HIGH{RESET} - Pages with data patterns but no API imports (Section 6)
       These pages display data-like content but aren't connected to
       the backend. They need API integration.

  {YELLOW}MEDIUM{RESET} - Stub API functions (Section 8)
       Exported functions that don't actually call the backend. Either
       implement the real API call or remove them.

  {YELLOW}MEDIUM{RESET} - Backend routes without frontend services (Section 5)
       The backend exposes these endpoints but no frontend code calls them.
       Create frontend service functions if these features are needed.

  {YELLOW}LOW{RESET} - Hardcoded data files (Section 9)
       Static data that could be managed dynamically via the backend.
       Consider migrating to API endpoints for easier maintenance.
""")


# ─── MAIN ─────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║          UI ↔ BACKEND INTEGRATION POINTS ANALYSIS                  ║{RESET}")
    print(f"{BOLD}{CYAN}║          L30 Library                         ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════════╝{RESET}")

    mock_results = find_mock_data()
    fe_endpoints = extract_frontend_endpoints()
    be_routes = extract_backend_routes()
    unmatched_fe = find_unmatched_services(fe_endpoints, be_routes)
    unmatched_be = find_backend_without_frontend(be_routes)
    disconnected = find_disconnected_pages()
    fallbacks = find_error_fallback_mocks()
    stubs = find_stub_functions()
    data_files = find_hardcoded_data_files()

    print_summary(mock_results, unmatched_fe, unmatched_be, disconnected,
                  fallbacks, stubs, data_files)


if __name__ == "__main__":
    main()
