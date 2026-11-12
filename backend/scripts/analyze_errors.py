#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Library 2030 Library - Error Analysis Script
Analyzes Docker container logs to find 404s and 500-level HTTP errors
"""

import re
import subprocess
import json
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Tuple
import sys


class ErrorAnalyzer:
    """Analyzes HTTP errors from Docker container logs"""

    # Regex patterns for different log formats
    NGINX_PATTERN = r'(\d+\.\d+\.\d+\.\d+).*?"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+([^\s]+)\s+HTTP/[\d.]+"\s+(\d+)'
    BACKEND_PATTERN = r'INFO:\s+[\d.]+:[\d]+ - "(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+([^\s]+)\s+HTTP/[\d.]+"\s+(\d+)'

    def __init__(self, tail_lines: int = 5000):
        self.tail_lines = tail_lines
        self.errors = {
            '404': [],
            '500': [],
            '501': [],
            '502': [],
            '503': [],
            '504': [],
            '505': []
        }
        self.error_details = []

    def get_docker_logs(self, service: str = None) -> str:
        """Get logs from docker-compose containers"""
        try:
            cmd = ['docker-compose', 'logs', '--tail', str(self.tail_lines)]
            if service:
                cmd.append(service)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd='/opt/l30-library'
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error getting docker logs: {e}", file=sys.stderr)
            return ""

    def parse_nginx_logs(self, logs: str):
        """Parse nginx format logs"""
        for line in logs.split('\n'):
            match = re.search(self.NGINX_PATTERN, line)
            if match:
                ip, method, path, status = match.groups()
                if status in self.errors:
                    self.errors[status].append({
                        'source': 'nginx',
                        'ip': ip,
                        'method': method,
                        'path': path,
                        'status': status,
                        'line': line
                    })
                    self.error_details.append({
                        'timestamp': self._extract_timestamp(line),
                        'status': status,
                        'endpoint': path,
                        'method': method,
                        'source': 'nginx'
                    })

    def parse_backend_logs(self, logs: str):
        """Parse FastAPI/Uvicorn format logs"""
        for line in logs.split('\n'):
            match = re.search(self.BACKEND_PATTERN, line)
            if match:
                method, path, status = match.groups()
                if status in self.errors:
                    self.errors[status].append({
                        'source': 'backend',
                        'method': method,
                        'path': path,
                        'status': status,
                        'line': line
                    })
                    self.error_details.append({
                        'timestamp': self._extract_timestamp(line),
                        'status': status,
                        'endpoint': path,
                        'method': method,
                        'source': 'backend'
                    })

    def _extract_timestamp(self, line: str) -> str:
        """Extract timestamp from log line"""
        # Try to find timestamp in various formats
        timestamp_patterns = [
            r'\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})',
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
        ]

        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)

        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def analyze(self):
        """Run complete analysis"""
        print("🔍 Analyzing Library 2030 Library error logs...")
        print(f"📊 Scanning last {self.tail_lines} log lines from all containers\n")

        # Get logs from different sources
        _ = self.get_docker_logs()
        nginx_logs = self.get_docker_logs('nginx')
        backend_logs = self.get_docker_logs('backend')

        # Parse logs
        self.parse_nginx_logs(nginx_logs)
        self.parse_backend_logs(backend_logs)

        # Generate report
        self.print_summary()
        self.print_detailed_errors()

        return self.generate_json_report()

    def print_summary(self):
        """Print summary statistics"""
        print("=" * 80)
        print("📈 ERROR SUMMARY")
        print("=" * 80)

        total_404 = len(self.errors['404'])
        total_5xx = sum(len(self.errors[code]) for code in ['500', '501', '502', '503', '504', '505'])

        print(f"\n🔴 404 Not Found Errors: {total_404}")
        print(f"🔥 5xx Server Errors: {total_5xx}")
        print(f"📊 Total Errors Found: {total_404 + total_5xx}\n")

        # Breakdown by status code
        print("Breakdown by Status Code:")
        print("-" * 40)
        for code in sorted(self.errors.keys()):
            count = len(self.errors[code])
            if count > 0:
                print(f"  {code}: {count} occurrences")
        print()

    def print_detailed_errors(self):
        """Print detailed error information"""

        # 404 Analysis
        if self.errors['404']:
            print("=" * 80)
            print("🔍 404 NOT FOUND ERRORS - Detailed Analysis")
            print("=" * 80)

            # Count by endpoint
            endpoint_counter = Counter(err['path'] for err in self.errors['404'])

            print("\nMost Common 404 Endpoints (Top 20):")
            print("-" * 40)
            for endpoint, count in endpoint_counter.most_common(20):
                print(f"  {count:3d}x  {endpoint}")

            print(f"\n📝 All Unique 404 Endpoints ({len(endpoint_counter)} unique):")
            print("-" * 40)
            for endpoint in sorted(endpoint_counter.keys()):
                print(f"  • {endpoint}")

        # 5xx Analysis
        fivehundred_errors = []
        for code in ['500', '501', '502', '503', '504', '505']:
            fivehundred_errors.extend(self.errors[code])

        if fivehundred_errors:
            print("\n" + "=" * 80)
            print("🔥 5XX SERVER ERRORS - Detailed Analysis")
            print("=" * 80)

            # Count by endpoint
            endpoint_counter = Counter(err['path'] for err in fivehundred_errors)

            print("\nMost Common 5xx Endpoints:")
            print("-" * 40)
            for endpoint, count in endpoint_counter.most_common(20):
                status_codes = [err['status'] for err in fivehundred_errors if err['path'] == endpoint]
                status_str = ', '.join(set(status_codes))
                print(f"  {count:3d}x  {endpoint} (Status: {status_str})")

            # Group by status code
            print("\n📋 Endpoints by Error Type:")
            print("-" * 40)
            for code in ['500', '501', '502', '503', '504', '505']:
                if self.errors[code]:
                    endpoints = set(err['path'] for err in self.errors[code])
                    print(f"\n  {code} Errors ({len(self.errors[code])} total):")
                    for endpoint in sorted(endpoints):
                        count = sum(1 for err in self.errors[code] if err['path'] == endpoint)
                        print(f"    • {endpoint} ({count}x)")

        print("\n" + "=" * 80)

    def generate_json_report(self) -> Dict:
        """Generate JSON report for programmatic use"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_404': len(self.errors['404']),
                'total_5xx': sum(len(self.errors[code]) for code in ['500', '501', '502', '503', '504', '505']),
                'by_status_code': {code: len(errors) for code, errors in self.errors.items() if errors}
            },
            'errors_404': [],
            'errors_5xx': [],
            'all_errors': self.error_details
        }

        # Unique 404 endpoints
        endpoints_404 = {}
        for err in self.errors['404']:
            endpoint = err['path']
            if endpoint not in endpoints_404:
                endpoints_404[endpoint] = {'count': 0, 'methods': set()}
            endpoints_404[endpoint]['count'] += 1
            endpoints_404[endpoint]['methods'].add(err['method'])

        report['errors_404'] = [
            {
                'endpoint': endpoint,
                'count': data['count'],
                'methods': list(data['methods'])
            }
            for endpoint, data in sorted(endpoints_404.items(), key=lambda x: -x[1]['count'])
        ]

        # Unique 5xx endpoints
        endpoints_5xx = {}
        for code in ['500', '501', '502', '503', '504', '505']:
            for err in self.errors[code]:
                endpoint = err['path']
                if endpoint not in endpoints_5xx:
                    endpoints_5xx[endpoint] = {'count': 0, 'methods': set(), 'status_codes': set()}
                endpoints_5xx[endpoint]['count'] += 1
                endpoints_5xx[endpoint]['methods'].add(err['method'])
                endpoints_5xx[endpoint]['status_codes'].add(code)

        report['errors_5xx'] = [
            {
                'endpoint': endpoint,
                'count': data['count'],
                'methods': list(data['methods']),
                'status_codes': sorted(list(data['status_codes']))
            }
            for endpoint, data in sorted(endpoints_5xx.items(), key=lambda x: -x[1]['count'])
        ]

        return report


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Analyze HTTP errors in Library 2030 Library logs'
    )
    parser.add_argument(
        '--tail',
        type=int,
        default=5000,
        help='Number of log lines to analyze (default: 5000)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path for JSON report'
    )

    args = parser.parse_args()

    analyzer = ErrorAnalyzer(tail_lines=args.tail)
    report = analyzer.analyze()

    if args.json or args.output:
        json_output = json.dumps(report, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(json_output)
            print(f"\n✅ JSON report saved to: {args.output}")
        else:
            print("\n" + "=" * 80)
            print("📄 JSON REPORT")
            print("=" * 80)
            print(json_output)


if __name__ == '__main__':
    main()
