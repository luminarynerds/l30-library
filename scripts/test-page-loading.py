#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Page Loading Validator Script
Tests all frontend pages and their corresponding API endpoints to identify loading issues.
"""

import re
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

class PageValidator:
    def __init__(self, project_root: str = "/opt/l30"):
        self.project_root = Path(project_root)
        self.frontend_root = self.project_root / "frontend"
        self.backend_root = self.project_root / "backend"
        self.issues = defaultdict(list)
        self.pages = {}
        self.api_endpoints = {}

    def extract_routes_from_app_routes(self) -> Dict[str, Dict]:
        """Extract all routes from AppRoutes.tsx"""
        app_routes_file = self.frontend_root / "src" / "components" / "AppRoutes.tsx"

        if not app_routes_file.exists():
            print(f"❌ AppRoutes.tsx not found at {app_routes_file}")
            return {}

        with open(app_routes_file, 'r') as f:
            content = f.read()

        # Extract route paths and their components
        # Pattern: <Route path="..." element={<Component />} />
        pattern = r'<Route\s+path="([^"]+)"\s+element=\{([^}]+)\}'
        matches = re.findall(pattern, content)

        routes = {}
        for path, element in matches:
            # Clean up component references
            component_match = re.search(r'<(\w+)', element)
            component = component_match.group(1) if component_match else "Unknown"

            routes[path] = {
                "path": path,
                "component": component,
                "raw_element": element.strip()
            }

        return routes

    def extract_api_endpoints(self) -> Dict[str, List[str]]:
        """Extract API endpoints from backend code"""
        endpoints = defaultdict(list)
        api_dir = self.backend_root / "app" / "api" / "v1"

        if not api_dir.exists():
            print(f"❌ API directory not found at {api_dir}")
            return endpoints

        for py_file in api_dir.glob("*.py"):
            with open(py_file, 'r') as f:
                content = f.read()

            # Find router prefix
            prefix_match = re.search(r'router\s*=\s*APIRouter\([^)]*prefix="([^"]*)"', content)
            prefix = prefix_match.group(1) if prefix_match else ""

            # Find all route decorators
            # Patterns: @router.get(), @router.post(), etc.
            route_pattern = r'@router\.(get|post|put|delete|patch)\("([^"]*)"'
            matches = re.findall(route_pattern, content)

            for method, path in matches:
                full_path = f"{prefix}{path}".replace("//", "/")
                endpoints[prefix or py_file.stem].append({
                    "method": method.upper(),
                    "path": full_path
                })

        return endpoints

    def check_component_imports(self) -> Dict[str, List[str]]:
        """Check if all imported components exist"""
        issues = defaultdict(list)
        pages_dir = self.frontend_root / "src" / "pages"

        if not pages_dir.exists():
            return issues

        # Get all page files
        page_files = set(f.stem for f in pages_dir.glob("*.tsx") if f.is_file())

        app_routes_file = self.frontend_root / "src" / "components" / "AppRoutes.tsx"
        with open(app_routes_file, 'r') as f:
            content = f.read()

        # Find all imported pages
        import_pattern = r'import\s+(\w+)\s+from\s+["\']([^"\']*)["\']'
        imports = re.findall(import_pattern, content)

        for component, path in imports:
            # Check if component is imported from pages directory
            if "pages" in path:
                # Extract filename
                filename = Path(path).stem
                if filename not in page_files:
                    issues["missing_pages"].append({
                        "component": component,
                        "path": path,
                        "expected_file": f"{filename}.tsx"
                    })

        return issues

    def check_auth_requirements(self) -> Dict[str, List[str]]:
        """Check for pages with RequireAuth that might have permission issues"""
        issues = defaultdict(list)
        app_routes_file = self.frontend_root / "src" / "components" / "AppRoutes.tsx"

        with open(app_routes_file, 'r') as f:
            content = f.read()

        # Find RequireAuth patterns
        auth_pattern = r'<RequireAuth\s+requiredRoles=\{(\[.*?\])\}[^>]*>\s*<(\w+)'
        matches = re.findall(auth_pattern, content, re.DOTALL)

        for roles_str, component in matches:
            issues["auth_required_pages"].append({
                "component": component,
                "required_roles": roles_str
            })

        return issues

    def check_api_dependencies(self) -> Dict[str, List[str]]:
        """Check if pages have corresponding API endpoints"""
        issues = defaultdict(list)

        # Common API endpoint patterns
        endpoint_map = {
            "board": "/api/v1/board",
            "admin": "/api/v1/admin",
            "users": "/api/v1/users",
            "books": "/api/v1/books",
            "inventory": "/api/v1/inventory",
            "patron": "/api/v1/patron",
            "staff": "/api/v1/staff",
            "events": "/api/v1/events",
            "facilities": "/api/v1/facilities",
        }

        pages_dir = self.frontend_root / "src" / "pages"
        for page_file in pages_dir.glob("*.tsx"):
            with open(page_file, 'r') as f:
                page_content = f.read()

            # Find API calls
            api_calls = re.findall(r'["\'](/api/v1/\w+[^"\']*)["\']', page_content)

            for api_call in api_calls:
                endpoint_prefix = "/".join(api_call.split("/")[:4])  # /api/v1/something

                # Check if endpoint file exists
                endpoint_parts = endpoint_prefix.split("/")[-1]
                endpoint_file = self.backend_root / "app" / "api" / "v1" / f"{endpoint_parts}.py"

                if not endpoint_file.exists():
                    issues["missing_endpoints"].append({
                        "page": page_file.name,
                        "api_call": api_call,
                        "expected_file": str(endpoint_file)
                    })

        return issues

    def run_validation(self):
        """Run all validations"""
        print("\n" + "="*60)
        print("🔍 L30 Page Loading Validator")
        print("="*60 + "\n")

        # 1. Extract routes
        print("📋 Extracting routes from AppRoutes.tsx...")
        self.pages = self.extract_routes_from_app_routes()
        print(f"✓ Found {len(self.pages)} routes\n")

        # 2. Extract API endpoints
        print("🔌 Extracting API endpoints from backend...")
        self.api_endpoints = self.extract_api_endpoints()
        print(f"✓ Found {len(self.api_endpoints)} API modules\n")

        # 3. Check component imports
        print("📦 Checking component imports...")
        import_issues = self.check_component_imports()
        if import_issues:
            self.issues.update(import_issues)
            print(f"⚠️  Found {len(import_issues)} import issues")
        else:
            print("✓ All component imports valid\n")

        # 4. Check auth requirements
        print("🔐 Checking authentication requirements...")
        auth_issues = self.check_auth_requirements()
        print(f"ℹ️  {len(auth_issues.get('auth_required_pages', []))} pages require authentication\n")

        # 5. Check API dependencies
        print("🔗 Checking API endpoint dependencies...")
        api_issues = self.check_api_dependencies()
        if api_issues.get("missing_endpoints"):
            self.issues.update(api_issues)
            print(f"⚠️  Found {len(api_issues['missing_endpoints'])} missing endpoints")
        else:
            print("✓ All API endpoints exist\n")

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate validation report"""
        print("\n" + "="*60)
        print("📊 Validation Report")
        print("="*60 + "\n")

        if not self.issues:
            print("✅ No issues found!\n")
            return

        # Report by category
        for category, items in self.issues.items():
            print(f"\n❌ {category.upper()} ({len(items)} issues):")
            print("-" * 60)

            for i, item in enumerate(items, 1):
                print(f"\n  {i}. {item}")

        # Generate summary
        print("\n" + "="*60)
        print("📈 Summary")
        print("="*60)
        total_issues = sum(len(v) for v in self.issues.values())
        print(f"Total Issues Found: {total_issues}")
        print(f"Total Pages: {len(self.pages)}")
        print(f"Total API Modules: {len(self.api_endpoints)}\n")

        # Output JSON for programmatic use
        output_file = self.project_root / "page-validation-report.json"
        with open(output_file, 'w') as f:
            json.dump({
                "total_pages": len(self.pages),
                "total_api_modules": len(self.api_endpoints),
                "total_issues": total_issues,
                "issues": dict(self.issues),
                "pages": self.pages
            }, f, indent=2)
        print(f"📄 Full report saved to: {output_file}\n")

if __name__ == "__main__":
    validator = PageValidator()
    validator.run_validation()
