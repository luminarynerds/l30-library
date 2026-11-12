#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Audit script to identify orphaned API endpoints.
Compares backend endpoint definitions with frontend usage.
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
import datetime

def get_all_backend_endpoints():
    """Extract all FastAPI endpoints from backend modules."""
    endpoints = {}
    api_dir = Path("/opt/l30/backend/app/api/v1")

    for py_file in sorted(api_dir.glob("**/*.py")):
        if py_file.name.startswith("_") or py_file.name == "registry.py":
            continue

        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"Warning: Could not read {py_file}: {e}")
            continue

        # Find all @router patterns with different prefix styles
        # Pattern 1: @router.get("/path")
        # Pattern 2: @router.post('/path')
        # Pattern 3: @app.get("/path")
        patterns = [
            r'@router\.(\w+)\(["\']([^"\']+)["\']',  # @router.get("/path")
            r'@app\.(\w+)\(["\']([^"\']+)["\']',      # @app.get("/path")
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for method, path in matches:
                # Normalize path
                path = path.rstrip('/')
                if not path:
                    path = "/"
                key = f"{method.upper():6s} {path}"

                if key not in endpoints:
                    endpoints[key] = {
                        "method": method.upper(),
                        "path": path,
                        "file": str(py_file),
                        "used_in_frontend": False
                    }

    return endpoints

def get_frontend_endpoints():
    """Extract all API endpoints called from frontend code."""
    used_endpoints = set()
    frontend_dir = Path("/opt/l30/frontend/src")

    if not frontend_dir.exists():
        print(f"Warning: Frontend directory not found at {frontend_dir}")
        return used_endpoints

    # Handle .ts and .tsx files separately since glob doesn't support braces
    for pattern in ["**/*.ts", "**/*.tsx"]:
        for js_file in frontend_dir.glob(pattern):
            try:
                content = js_file.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                print(f"Warning: Could not read {js_file}: {e}")
                continue

            # Find all /api/v1 calls with various patterns
            # Pattern: "/api/v1/..." in strings
            patterns = [
                r'["\'](/api/v1/[^"\']*)["\']',  # "/api/v1/..." or '/api/v1/...'
                r'`(/api/v1/[^`]*)`',             # `/api/v1/...`
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                for path in matches:
                    # Normalize path (remove query parameters)
                    path = path.split('?')[0].split('#')[0]
                    path = path.rstrip('/')
                    if not path:
                        path = "/api/v1"
                    used_endpoints.add(path)

    return used_endpoints

def categorize_orphaned_endpoint(endpoint_def, module_name):
    """Determine the category of an orphaned endpoint."""

    keywords_by_category = {
        "dead_code": [
            "debug", "test_", "old_", "deprecated",
            "experimental", "poc", "prototype", "temp", "temporary"
        ],
        "incomplete_feature": [
            "draft", "wip", "pending", "todo",
            "stub", "placeholder", "incomplete"
        ],
        "legacy": [
            "legacy", "v1_", "v2_", "v3_", "migrate",
            "compat", "backwards", "deprecated"
        ],
        "internal_only": [
            "internal", "private", "_internal",
            "system", "utility"
        ],
        "unclear": []
    }

    path = endpoint_def["path"].lower()
    file = endpoint_def["file"].lower()

    for category, keywords in keywords_by_category.items():
        if category == "unclear":
            continue
        for keyword in keywords:
            if keyword in path or keyword in file:
                return category

    return "unclear"

def main():
    """Run the audit."""
    print("Starting endpoint audit...")

    print("  Scanning backend endpoints...")
    backend_endpoints = get_all_backend_endpoints()
    print(f"    Found {len(backend_endpoints)} backend endpoints")

    print("  Scanning frontend usage...")
    frontend_endpoints = get_frontend_endpoints()
    print(f"    Found {len(frontend_endpoints)} frontend endpoints called")

    # Mark used endpoints
    used_count = 0
    for key, endpoint in backend_endpoints.items():
        # Check if this endpoint pattern is used in frontend
        endpoint_path = endpoint["path"]

        for fe_endpoint in frontend_endpoints:
            # Match if frontend endpoint contains the backend path
            # or vice versa (for parameterized endpoints)
            if (endpoint_path in fe_endpoint or
                fe_endpoint in endpoint_path or
                endpoint_path.replace("{", ":").replace("}", "") in fe_endpoint):
                endpoint["used_in_frontend"] = True
                used_count += 1
                break

    print(f"  Matched {used_count} endpoints as used")

    # Find orphaned endpoints
    orphaned = {
        k: v for k, v in backend_endpoints.items()
        if not v["used_in_frontend"]
    }

    print(f"  Found {len(orphaned)} orphaned endpoints")

    # Categorize
    categorized = defaultdict(list)
    for key, endpoint in orphaned.items():
        module = Path(endpoint["file"]).stem
        category = categorize_orphaned_endpoint(endpoint, module)
        endpoint["category"] = category
        categorized[category].append(endpoint)

    # Generate report
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_endpoints": len(backend_endpoints),
        "used_endpoints": used_count,
        "orphaned_endpoints": len(orphaned),
        "coverage_percentage": round((used_count / len(backend_endpoints) * 100), 1) if len(backend_endpoints) > 0 else 0,
        "categorized": {}
    }

    for category in sorted(categorized.keys()):
        endpoints = categorized[category]
        report["categorized"][category] = {
            "count": len(endpoints),
            "endpoints": [
                {
                    "path": e["path"],
                    "method": e["method"],
                    "file": e["file"]
                }
                for e in sorted(endpoints, key=lambda x: x["path"])
            ]
        }

    # Save report
    output_file = "/opt/l30/PHASE_2_ORPHANED_ENDPOINTS_AUDIT.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\nAudit complete!")
    print(f"  Total endpoints: {report['total_endpoints']}")
    print(f"  Used endpoints: {report['used_endpoints']}")
    print(f"  Orphaned endpoints: {report['orphaned_endpoints']}")
    print(f"  Coverage: {report['coverage_percentage']:.1f}%")
    print(f"\nReport saved to: {output_file}")
    print(f"\nOrphaned by category:")
    for category in sorted(report["categorized"].keys()):
        count = report["categorized"][category]["count"]
        print(f"  {category}: {count}")

    return report

if __name__ == "__main__":
    main()
