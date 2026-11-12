#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Coverage Threshold Checker for LSC Library System

This script enforces the two-tier coverage model:
- Global threshold: 85% (enforced by pytest --cov-fail-under=85)
- Critical domains: 90-95% (enforced by this script)

Usage:
    pytest --cov=app --cov-report=json --cov-report=term-missing
    python scripts/check_coverage_thresholds.py

Exit codes:
    0 - All thresholds met
    1 - One or more thresholds not met
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Critical domain thresholds
CRITICAL_THRESHOLDS = {
    # Authentication & Authorization (95%)
    "app/api/v1/auth.py": 95,
    "app/core/security.py": 95,
    "app/core/authorization.py": 95,

    # Privacy & Data Protection (95%)
    "app/api/v1/privacy.py": 95,
    "app/services/privacy_audit.py": 95,

    # Financial & Payment Workflows (90%)
    "app/services/fine_service.py": 90,
    "app/services/fine_reversal_service.py": 90,
    "app/services/fine_policy_service.py": 90,
    "app/services/stripe_connect_service.py": 90,
    "app/services/financial_reports_service.py": 90,
    "app/services/payout_notification_service.py": 90,
    "app/services/payout_scheduler_service.py": 90,
    "app/services/tax_compliance_service.py": 90,
    "app/services/tax_reporting_service.py": 90,
    "app/services/consortium_billing_service.py": 90,
    "app/services/consortium_invoice_export_service.py": 90,

    # Patron Account Security (90%)
    "app/services/suspension_service.py": 90,
    "app/services/patron_recovery_service.py": 90,
}


def load_coverage_data() -> Dict:
    """Load coverage data from coverage.json."""
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        print("Error: coverage.json not found. Run pytest with --cov-report=json first.")
        sys.exit(1)

    with open(coverage_file) as f:
        return json.load(f)


def get_file_coverage(coverage_data: Dict, file_path: str) -> float:
    """Get coverage percentage for a specific file."""
    files = coverage_data.get("files", {})

    # Try exact match first
    if file_path in files:
        summary = files[file_path].get("summary", {})
        return summary.get("percent_covered", 0.0)

    # Try with different path variations
    for key in files.keys():
        if key.endswith(file_path):
            summary = files[key].get("summary", {})
            return summary.get("percent_covered", 0.0)

    return None


def check_thresholds() -> Tuple[List[str], List[str]]:
    """
    Check if all critical modules meet their coverage thresholds.

    Returns:
        Tuple of (passing_modules, failing_modules)
    """
    coverage_data = load_coverage_data()
    passing = []
    failing = []

    for file_path, threshold in CRITICAL_THRESHOLDS.items():
        coverage = get_file_coverage(coverage_data, file_path)

        if coverage is None:
            print(f"Warning: {file_path} not found in coverage report")
            failing.append(f"{file_path}: NOT FOUND (required: {threshold}%)")
        elif coverage >= threshold:
            passing.append(f"{file_path}: {coverage:.1f}% (required: {threshold}%)")
        else:
            failing.append(f"{file_path}: {coverage:.1f}% (required: {threshold}%)")

    return passing, failing


def main():
    """Main entry point."""
    print("=" * 80)
    print("LSC Library System - Coverage Threshold Checker")
    print("=" * 80)
    print()

    passing, failing = check_thresholds()

    if passing:
        print("PASSING MODULES:")
        for module in passing:
            print(f"  ✓ {module}")
        print()

    if failing:
        print("FAILING MODULES:")
        for module in failing:
            print(f"  ✗ {module}")
        print()
        print("=" * 80)
        print(f"Coverage check FAILED: {len(failing)} module(s) below threshold")
        print("=" * 80)
        sys.exit(1)
    else:
        print("=" * 80)
        print("Coverage check PASSED: All critical modules meet their thresholds")
        print("=" * 80)
        sys.exit(0)


if __name__ == "__main__":
    main()
