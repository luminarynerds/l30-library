#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API Endpoint Coverage Analysis Tool

Automatically discovers and compares:
- Backend API endpoints (FastAPI routes)
- Frontend API calls (TypeScript service functions)

Reports coverage gaps, mismatches, and orphaned endpoints.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import argparse


# ==================== Configuration ====================

@dataclass
class Config:
    """Configuration for the coverage tool."""
    backend_path: Path = Path("/opt/l30/backend/app/api/v1")
    frontend_path: Path = Path("/opt/l30/frontend/src/services")
    output_json: Path = Path("/opt/l30/coverage-report.json")
    output_html: Path = Path("/opt/l30/coverage-report.html")
    coverage_threshold: float = 80.0  # Fail if coverage < this %
    generate_html: bool = False
    verbose: bool = False


# ==================== Data Models ====================

@dataclass
class Endpoint:
    """Represents a backend API endpoint."""
    method: str
    path: str
    file: str
    line: int
    function_name: str
    tags: List[str] = field(default_factory=list)

    @property
    def full_path(self) -> str:
        """Full API path including version prefix."""
        return f"/api/v1{self.path}"

    @property
    def key(self) -> str:
        """Unique identifier for this endpoint."""
        return f"{self.method}:{self.full_path}"


@dataclass
class ApiCall:
    """Represents a frontend API call."""
    method: str
    path: str
    file: str
    line: int
    function_name: str

    @property
    def full_path(self) -> str:
        """Full API path."""
        # Handle both absolute and relative paths
        if self.path.startswith("/api/v1/"):
            return self.path
        elif self.path.startswith("/api/"):
            return self.path
        elif self.path.startswith("/"):
            return f"/api/v1{self.path}"
        else:
            return f"/api/v1/{self.path}"

    @property
    def key(self) -> str:
        """Unique identifier for this API call."""
        return f"{self.method}:{self.full_path}"


@dataclass
class CoverageReport:
    """Final coverage analysis report."""
    backend_endpoints: List[Endpoint]
    frontend_calls: List[ApiCall]
    matched: List[Tuple[Endpoint, ApiCall]]
    uncovered_endpoints: List[Endpoint]  # Backend endpoints not called
    orphaned_calls: List[ApiCall]  # Frontend calls to non-existent endpoints
    coverage_percentage: float
    total_endpoints: int
    total_calls: int
    matched_count: int


# ==================== Backend Parser ====================

class FastAPIParser:
    """Parses FastAPI route definitions from Python files."""

    def __init__(self, config: Config):
        self.config = config
        self.endpoints: List[Endpoint] = []

    def parse_directory(self) -> List[Endpoint]:
        """Parse all Python files in the backend directory."""
        python_files = list(self.config.backend_path.rglob("*.py"))

        for file_path in python_files:
            if file_path.name.startswith("__"):
                continue
            self._parse_file(file_path)

        if self.config.verbose:
            print(f"Discovered {len(self.endpoints)} backend endpoints")

        return self.endpoints

    def _parse_file(self, file_path: Path) -> None:
        """Parse a single Python file for FastAPI routes."""
        try:
            content = file_path.read_text(encoding='utf-8')

            # Use regex fallback for reliability
            endpoints = self._parse_with_regex(file_path, content)
            self.endpoints.extend(endpoints)

        except Exception as e:
            if self.config.verbose:
                print(f"Warning: Failed to parse {file_path}: {e}")

    def _parse_with_regex(self, file_path: Path, content: str) -> List[Endpoint]:
        """Parse endpoints using regex (more reliable for FastAPI patterns)."""
        endpoints = []
        lines = content.split('\n')

        # Find router prefix
        router_prefix = ""
        router_tags = []
        for line in lines:
            router_match = re.search(r'router\s*=\s*APIRouter\s*\((.*?)\)', line)
            if router_match:
                args = router_match.group(1)
                prefix_match = re.search(r'prefix\s*=\s*["\']([^"\']+)["\']', args)
                if prefix_match:
                    router_prefix = prefix_match.group(1)
                tags_match = re.search(r'tags\s*=\s*\[([^\]]+)\]', args)
                if tags_match:
                    tags_str = tags_match.group(1)
                    router_tags = [t.strip(' "\'') for t in tags_str.split(',')]

        # Find route decorators
        i = 0
        while i < len(lines):
            line = lines[i]

            # Match @router.METHOD(...) or @router.METHOD(...)
            route_match = re.match(r'@router\.(get|post|put|delete|patch|options|head)\s*\((.*?)\)', line)
            if route_match:
                method = route_match.group(1).upper()
                args = route_match.group(2)

                # Extract path (first argument or path= kwarg)
                path = ""
                path_match = re.search(r'^["\']([^"\']+)["\']', args.strip())
                if path_match:
                    path = path_match.group(1)
                else:
                    path_match = re.search(r'path\s*=\s*["\']([^"\']+)["\']', args)
                    if path_match:
                        path = path_match.group(1)

                # Extract tags if specified
                tags = router_tags.copy()
                tags_match = re.search(r'tags\s*=\s*\[([^\]]+)\]', args)
                if tags_match:
                    tags_str = tags_match.group(1)
                    tags = [t.strip(' "\'') for t in tags_str.split(',')]

                # Find function name on next non-decorator line
                func_name = "unknown"
                func_line = i + 1
                for j in range(i + 1, min(i + 5, len(lines))):
                    if not lines[j].strip().startswith('@'):
                        func_match = re.match(r'(?:async\s+)?def\s+(\w+)', lines[j].strip())
                        if func_match:
                            func_name = func_match.group(1)
                            func_line = j + 1
                            break

                if path:
                    full_path = router_prefix + path
                    try:
                        rel_path = file_path.relative_to(self.config.backend_path.parent.parent)
                    except:
                        rel_path = file_path.name

                    endpoints.append(Endpoint(
                        method=method,
                        path=full_path,
                        file=str(rel_path),
                        line=i + 1,
                        function_name=func_name,
                        tags=tags
                    ))

            i += 1

        return endpoints


# ==================== Frontend Parser ====================

class TypeScriptParser:
    """Parses API calls from TypeScript service files."""

    def __init__(self, config: Config):
        self.config = config
        self.calls: List[ApiCall] = []

    def parse_directory(self) -> List[ApiCall]:
        """Parse all TypeScript files in the frontend directory."""
        ts_files = list(self.config.frontend_path.glob("*-api.ts"))

        for file_path in ts_files:
            if file_path.name == "types.ts" or file_path.name == "api.ts":
                continue
            self._parse_file(file_path)

        if self.config.verbose:
            print(f"Discovered {len(self.calls)} frontend API calls")

        return self.calls

    def _parse_file(self, file_path: Path) -> None:
        """Parse a single TypeScript file for fetch/axios calls."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            for i, line in enumerate(lines, 1):
                calls = self._extract_api_calls(line, i, file_path)
                self.calls.extend(calls)

        except Exception as e:
            if self.config.verbose:
                print(f"Warning: Failed to parse {file_path}: {e}")

    def _extract_api_calls(self, line: str, line_num: int, file_path: Path) -> List[ApiCall]:
        """Extract API calls from a line of code."""
        calls = []

        # Pattern 1: fetch(`${API_BASE}/path`, {method: 'POST'})
        # Pattern 2: fetch(`/api/v1/path`, {method: 'POST'})
        # Pattern 3: await fetch(url, {method})

        # Match fetch calls with template literals
        fetch_pattern = r"fetch\s*\(\s*`\s*\$\{(?:API_BASE|apiBase)\}([^`]+)`"
        matches = re.finditer(fetch_pattern, line)
        for match in matches:
            path = match.group(1).strip()
            method = self._extract_method(line)

            # Find the enclosing function name
            function_name = self._find_function_context(file_path, line_num)

            calls.append(ApiCall(
                method=method,
                path=path,
                file=str(file_path.relative_to(self.config.frontend_path.parent.parent)),
                line=line_num,
                function_name=function_name
            ))

        # Match absolute path fetch calls
        abs_pattern = r"fetch\s*\(\s*`\s*(/api/v1/[^`]+)`"
        matches = re.finditer(abs_pattern, line)
        for match in matches:
            path = match.group(1).strip()
            method = self._extract_method(line)
            function_name = self._find_function_context(file_path, line_num)

            calls.append(ApiCall(
                method=method,
                path=path,
                file=str(file_path.relative_to(self.config.frontend_path.parent.parent)),
                line=line_num,
                function_name=function_name
            ))

        return calls

    def _extract_method(self, line: str) -> str:
        """Extract HTTP method from fetch call."""
        # Look for method: 'POST', method: "DELETE", etc.
        method_match = re.search(r"method:\s*['\"](\w+)['\"]", line, re.IGNORECASE)
        if method_match:
            return method_match.group(1).upper()

        # Default to GET if no method specified
        return "GET"

    def _find_function_context(self, file_path: Path, target_line: int) -> str:
        """Find the function name containing the given line."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            # Look backwards for function declaration
            for i in range(target_line - 1, -1, -1):
                line = lines[i]
                # Match: export async function functionName
                # Match: export function functionName
                # Match: async function functionName
                match = re.search(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", line)
                if match:
                    return match.group(1)

                # Match: const functionName = async
                match = re.search(r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async)?", line)
                if match:
                    return match.group(1)

            return "unknown"
        except:
            return "unknown"


# ==================== Coverage Analyzer ====================

class CoverageAnalyzer:
    """Analyzes coverage between backend and frontend."""

    def __init__(self, config: Config):
        self.config = config

    def analyze(self, endpoints: List[Endpoint], calls: List[ApiCall]) -> CoverageReport:
        """Perform coverage analysis."""

        # Create lookup maps
        endpoint_map = {e.key: e for e in endpoints}
        call_map = defaultdict(list)
        for call in calls:
            call_map[call.key].append(call)

        matched = []
        uncovered_endpoints = []
        orphaned_calls = []

        # Find matches and uncovered endpoints
        for endpoint in endpoints:
            if endpoint.key in call_map:
                # Match found
                matched.append((endpoint, call_map[endpoint.key][0]))
            else:
                # Check for fuzzy matches (different methods, trailing slashes, etc.)
                fuzzy_match = self._find_fuzzy_match(endpoint, call_map)
                if fuzzy_match:
                    matched.append((endpoint, fuzzy_match))
                else:
                    uncovered_endpoints.append(endpoint)

        # Find orphaned calls
        for call_key, call_list in call_map.items():
            if call_key not in endpoint_map:
                # Check for fuzzy matches
                if not self._find_fuzzy_endpoint_match(call_list[0], endpoint_map):
                    orphaned_calls.extend(call_list)

        # Calculate coverage
        total_endpoints = len(endpoints)
        matched_count = len(matched)
        coverage_percentage = (matched_count / total_endpoints * 100) if total_endpoints > 0 else 0

        return CoverageReport(
            backend_endpoints=endpoints,
            frontend_calls=calls,
            matched=matched,
            uncovered_endpoints=uncovered_endpoints,
            orphaned_calls=orphaned_calls,
            coverage_percentage=coverage_percentage,
            total_endpoints=total_endpoints,
            total_calls=len(calls),
            matched_count=matched_count
        )

    def _find_fuzzy_match(self, endpoint: Endpoint, call_map: Dict) -> Optional[ApiCall]:
        """Find fuzzy matches for endpoints (handles trailing slashes, etc.)."""
        path_variants = [
            endpoint.full_path,
            endpoint.full_path.rstrip('/'),
            endpoint.full_path + '/',
        ]

        for variant in path_variants:
            key = f"{endpoint.method}:{variant}"
            if key in call_map:
                return call_map[key][0]

        return None

    def _find_fuzzy_endpoint_match(self, call: ApiCall, endpoint_map: Dict) -> bool:
        """Check if call has a fuzzy match in endpoints."""
        path_variants = [
            call.full_path,
            call.full_path.rstrip('/'),
            call.full_path + '/',
        ]

        for variant in path_variants:
            key = f"{call.method}:{variant}"
            if key in endpoint_map:
                return True

        return False


# ==================== Report Generators ====================

class ConsoleReporter:
    """Generates console output with color coding."""

    COLORS = {
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
        'END': '\033[0m'
    }

    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and sys.stdout.isatty()

    def color(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if self.use_colors and color in self.COLORS:
            return f"{self.COLORS[color]}{text}{self.COLORS['END']}"
        return text

    def generate(self, report: CoverageReport) -> None:
        """Print coverage report to console."""

        # Header
        print("\n" + "=" * 80)
        print(self.color("API ENDPOINT COVERAGE REPORT", 'BOLD'))
        print("=" * 80 + "\n")

        # Summary
        print(self.color("SUMMARY", 'BOLD'))
        print("-" * 80)
        print(f"Total Backend Endpoints:  {report.total_endpoints}")
        print(f"Total Frontend API Calls: {report.total_calls}")
        print(f"Matched Endpoints:        {report.matched_count}")
        print(f"Uncovered Endpoints:      {len(report.uncovered_endpoints)}")
        print(f"Orphaned Calls:           {len(report.orphaned_calls)}")

        # Coverage percentage
        coverage_color = 'GREEN' if report.coverage_percentage >= 80 else 'YELLOW' if report.coverage_percentage >= 60 else 'RED'
        print(f"\nCoverage: {self.color(f'{report.coverage_percentage:.1f}%', coverage_color)}")
        print()

        # Uncovered endpoints
        if report.uncovered_endpoints:
            print(self.color("UNCOVERED ENDPOINTS (Backend endpoints not called by frontend)", 'YELLOW'))
            print("-" * 80)
            for endpoint in sorted(report.uncovered_endpoints, key=lambda e: (e.method, e.path)):
                print(f"  {self.color(endpoint.method, 'CYAN'):6} {endpoint.full_path}")
                print(f"         File: {endpoint.file}:{endpoint.line}")
                print()

        # Orphaned calls
        if report.orphaned_calls:
            print(self.color("ORPHANED API CALLS (Frontend calls to non-existent endpoints)", 'RED'))
            print("-" * 80)
            for call in sorted(report.orphaned_calls, key=lambda c: (c.method, c.path)):
                print(f"  {self.color(call.method, 'MAGENTA'):6} {call.full_path}")
                print(f"         File: {call.file}:{call.line} (in {call.function_name})")
                print()

        # Coverage by tag
        if report.backend_endpoints:
            print(self.color("COVERAGE BY TAG", 'BOLD'))
            print("-" * 80)
            tag_stats = self._calculate_tag_stats(report)
            for tag, stats in sorted(tag_stats.items()):
                coverage = stats['covered'] / stats['total'] * 100 if stats['total'] > 0 else 0
                color = 'GREEN' if coverage >= 80 else 'YELLOW' if coverage >= 60 else 'RED'
                print(f"  {tag:25} {stats['covered']:3}/{stats['total']:3} = {self.color(f'{coverage:.1f}%', color)}")
            print()

        print("=" * 80 + "\n")

    def _calculate_tag_stats(self, report: CoverageReport) -> Dict[str, Dict[str, int]]:
        """Calculate coverage statistics by tag."""
        tag_stats = defaultdict(lambda: {'total': 0, 'covered': 0})

        # Count all endpoints by tag
        for endpoint in report.backend_endpoints:
            for tag in endpoint.tags:
                tag_stats[tag]['total'] += 1

        # Count covered endpoints by tag
        matched_endpoints = {e.key for e, _ in report.matched}
        for endpoint in report.backend_endpoints:
            if endpoint.key in matched_endpoints:
                for tag in endpoint.tags:
                    tag_stats[tag]['covered'] += 1

        return dict(tag_stats)


class JSONReporter:
    """Generates JSON report."""

    def generate(self, report: CoverageReport, output_path: Path) -> None:
        """Generate JSON report file."""
        data = {
            'summary': {
                'total_endpoints': report.total_endpoints,
                'total_calls': report.total_calls,
                'matched': report.matched_count,
                'uncovered': len(report.uncovered_endpoints),
                'orphaned': len(report.orphaned_calls),
                'coverage_percentage': round(report.coverage_percentage, 2)
            },
            'uncovered_endpoints': [
                {
                    'method': e.method,
                    'path': e.full_path,
                    'file': e.file,
                    'line': e.line,
                    'function': e.function_name,
                    'tags': e.tags
                }
                for e in report.uncovered_endpoints
            ],
            'orphaned_calls': [
                {
                    'method': c.method,
                    'path': c.full_path,
                    'file': c.file,
                    'line': c.line,
                    'function': c.function_name
                }
                for c in report.orphaned_calls
            ],
            'matched': [
                {
                    'method': e.method,
                    'path': e.full_path,
                    'backend_file': e.file,
                    'frontend_file': c.file
                }
                for e, c in report.matched
            ]
        }

        output_path.write_text(json.dumps(data, indent=2))
        print(f"JSON report saved to: {output_path}")


class HTMLReporter:
    """Generates HTML report with charts."""

    def generate(self, report: CoverageReport, output_path: Path) -> None:
        """Generate HTML report file."""
        html = self._generate_html(report)
        output_path.write_text(html)
        print(f"HTML report saved to: {output_path}")

    def _generate_html(self, report: CoverageReport) -> str:
        """Generate HTML content."""
        coverage_color = '#4CAF50' if report.coverage_percentage >= 80 else '#FFC107' if report.coverage_percentage >= 60 else '#F44336'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Coverage Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; background: #f9f9f9; }}
        .metric {{ background: white; padding: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #333; margin-bottom: 5px; }}
        .metric-label {{ color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .coverage-circle {{ width: 150px; height: 150px; margin: 20px auto; position: relative; }}
        .coverage-text {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 36px; font-weight: bold; color: {coverage_color}; }}
        .section {{ padding: 30px; border-top: 1px solid #eee; }}
        .section h2 {{ font-size: 20px; color: #333; margin-bottom: 20px; }}
        .endpoint {{ background: #f9f9f9; padding: 15px; margin-bottom: 10px; border-radius: 4px; border-left: 4px solid #667eea; }}
        .endpoint .method {{ display: inline-block; padding: 4px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; margin-right: 10px; }}
        .method-get {{ background: #4CAF50; color: white; }}
        .method-post {{ background: #2196F3; color: white; }}
        .method-put {{ background: #FF9800; color: white; }}
        .method-delete {{ background: #F44336; color: white; }}
        .method-patch {{ background: #9C27B0; color: white; }}
        .endpoint .path {{ font-family: monospace; font-size: 14px; color: #333; }}
        .endpoint .info {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .orphaned {{ border-left-color: #F44336; }}
        .empty-state {{ text-align: center; padding: 40px; color: #999; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>API Endpoint Coverage Report</h1>
            <p>Generated on {self._get_timestamp()}</p>
        </div>

        <div class="summary">
            <div class="metric">
                <div class="metric-value">{report.total_endpoints}</div>
                <div class="metric-label">Backend Endpoints</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report.total_calls}</div>
                <div class="metric-label">Frontend Calls</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report.matched_count}</div>
                <div class="metric-label">Matched</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: {coverage_color};">{report.coverage_percentage:.1f}%</div>
                <div class="metric-label">Coverage</div>
            </div>
        </div>

        {self._generate_uncovered_section(report)}
        {self._generate_orphaned_section(report)}
    </div>
</body>
</html>"""

    def _generate_uncovered_section(self, report: CoverageReport) -> str:
        """Generate uncovered endpoints section."""
        if not report.uncovered_endpoints:
            return '<div class="section"><h2>Uncovered Endpoints</h2><div class="empty-state">All endpoints are covered!</div></div>'

        items = []
        for endpoint in sorted(report.uncovered_endpoints, key=lambda e: (e.method, e.path)):
            items.append(f'''
            <div class="endpoint">
                <span class="method method-{endpoint.method.lower()}">{endpoint.method}</span>
                <span class="path">{endpoint.full_path}</span>
                <div class="info">File: {endpoint.file}:{endpoint.line} | Function: {endpoint.function_name}</div>
            </div>
            ''')

        return f'<div class="section"><h2>Uncovered Endpoints ({len(report.uncovered_endpoints)})</h2>{"".join(items)}</div>'

    def _generate_orphaned_section(self, report: CoverageReport) -> str:
        """Generate orphaned calls section."""
        if not report.orphaned_calls:
            return '<div class="section"><h2>Orphaned API Calls</h2><div class="empty-state">No orphaned calls detected!</div></div>'

        items = []
        for call in sorted(report.orphaned_calls, key=lambda c: (c.method, c.path)):
            items.append(f'''
            <div class="endpoint orphaned">
                <span class="method method-{call.method.lower()}">{call.method}</span>
                <span class="path">{call.full_path}</span>
                <div class="info">File: {call.file}:{call.line} | Function: {call.function_name}</div>
            </div>
            ''')

        return f'<div class="section"><h2>Orphaned API Calls ({len(report.orphaned_calls)})</h2>{"".join(items)}</div>'

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ==================== Main Application ====================

def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze API endpoint coverage between backend and frontend',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  %(prog)s

  # Generate HTML report
  %(prog)s --html

  # Verbose output
  %(prog)s -v

  # Custom paths
  %(prog)s --backend /path/to/backend --frontend /path/to/frontend

  # Fail if coverage below 80%%
  %(prog)s --threshold 80
        """
    )

    parser.add_argument('--backend', type=Path, help='Backend API directory path')
    parser.add_argument('--frontend', type=Path, help='Frontend services directory path')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--threshold', type=float, default=80.0, help='Coverage threshold (default: 80%%)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--json-output', type=Path, help='JSON output path (default: /opt/l30/coverage-report.json)')
    parser.add_argument('--html-output', type=Path, help='HTML output path (default: /opt/l30/coverage-report.html)')

    args = parser.parse_args()

    # Create configuration
    config = Config(
        coverage_threshold=args.threshold,
        generate_html=args.html,
        verbose=args.verbose
    )

    if args.backend:
        config.backend_path = args.backend
    if args.frontend:
        config.frontend_path = args.frontend
    if args.json_output:
        config.output_json = args.json_output
    if args.html_output:
        config.output_html = args.html_output

    # Validate paths
    if not config.backend_path.exists():
        print(f"Error: Backend path does not exist: {config.backend_path}", file=sys.stderr)
        return 1
    if not config.frontend_path.exists():
        print(f"Error: Frontend path does not exist: {config.frontend_path}", file=sys.stderr)
        return 1

    try:
        # Parse backend endpoints
        if config.verbose:
            print("Scanning backend endpoints...")
        backend_parser = FastAPIParser(config)
        endpoints = backend_parser.parse_directory()

        # Parse frontend API calls
        if config.verbose:
            print("Scanning frontend API calls...")
        frontend_parser = TypeScriptParser(config)
        calls = frontend_parser.parse_directory()

        # Analyze coverage
        if config.verbose:
            print("Analyzing coverage...")
        analyzer = CoverageAnalyzer(config)
        report = analyzer.analyze(endpoints, calls)

        # Generate reports
        console_reporter = ConsoleReporter()
        console_reporter.generate(report)

        json_reporter = JSONReporter()
        json_reporter.generate(report, config.output_json)

        if config.generate_html:
            html_reporter = HTMLReporter()
            html_reporter.generate(report, config.output_html)

        # Exit with appropriate code
        if report.coverage_percentage < config.coverage_threshold:
            print(f"\nCoverage {report.coverage_percentage:.1f}% is below threshold {config.coverage_threshold}%")
            return 1

        if report.orphaned_calls:
            print(f"\nFound {len(report.orphaned_calls)} orphaned API calls (calls to non-existent endpoints)")
            return 1

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if config.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
