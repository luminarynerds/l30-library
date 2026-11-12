#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Audit Log Verification Utility

Verifies the integrity of the immutable audit log by checking:
1. Each entry has a valid HMAC signature
2. The hash chain is intact
3. No entries have been tampered with

Usage:
    python verify_audit_log.py [--log-path /path/to/audit.log] [--signing-key KEY] [--verbose]
    python verify_audit_log.py --check-syntax /path/to/audit.log  # Just validate JSON format
    python verify_audit_log.py --summary /path/to/audit.log       # Show summary stats
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.audit_log import verify_audit_log


def print_verification_results(is_valid: bool, errors: list, verbose: bool = False) -> int:
    """Pretty-print verification results."""
    if is_valid:
        print("\n✓ Audit log verification PASSED")
        if errors:
            for msg in errors:
                print(f"  {msg}")
        return 0
    else:
        print("\n✗ Audit log verification FAILED")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        if verbose:
            print("\nTo investigate further:")
            print("  - Review the audit log file directly: less +F {log_path}")
            print("  - Check application logs for write errors")
            print("  - Verify the signing key hasn't been changed")
        return 1


def check_syntax(log_path: str) -> int:
    """Just check JSON syntax, don't verify signatures."""
    try:
        with open(log_path, "r") as f:
            valid_lines = 0
            invalid_lines = 0
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                    valid_lines += 1
                except json.JSONDecodeError as e:
                    print(f"  Line {line_num}: {e}")
                    invalid_lines += 1

        if invalid_lines == 0:
            print(f"✓ JSON syntax valid ({valid_lines} entries)")
            return 0
        else:
            print(f"✗ Found {invalid_lines} invalid JSON lines out of {valid_lines + invalid_lines} total")
            return 1

    except FileNotFoundError:
        print(f"✗ Log file not found: {log_path}")
        return 1
    except Exception as e:
        print(f"✗ Error reading log file: {e}")
        return 1


def print_summary(log_path: str) -> int:
    """Print summary statistics about the audit log."""
    try:
        if not Path(log_path).exists():
            print("No audit log file found yet")
            return 0

        event_counts = {}
        severity_counts = {}
        user_ids = set()
        earliest = None
        latest = None
        total_size = Path(log_path).stat().st_size

        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    event_type = entry.get("event_type", "UNKNOWN")
                    severity = entry.get("severity", "UNKNOWN")
                    timestamp = entry.get("timestamp")

                    event_counts[event_type] = event_counts.get(event_type, 0) + 1
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1

                    if entry.get("user_id"):
                        user_ids.add(entry["user_id"])

                    if timestamp:
                        if earliest is None or timestamp < earliest:
                            earliest = timestamp
                        if latest is None or timestamp > latest:
                            latest = timestamp

                except json.JSONDecodeError:
                    pass

        print("\nAudit Log Summary")
        print("=" * 60)
        print(f"File: {log_path}")
        print(f"Size: {total_size:,} bytes")

        if earliest:
            print(f"Earliest entry: {earliest}")
        if latest:
            print(f"Latest entry: {latest}")

        total_entries = sum(event_counts.values())
        print(f"Total entries: {total_entries}")

        if user_ids:
            print(f"Unique user IDs: {len(user_ids)}")

        if event_counts:
            print("\nEvent types:")
            for event_type in sorted(event_counts.keys()):
                count = event_counts[event_type]
                pct = (count / total_entries * 100) if total_entries > 0 else 0
                print(f"  {event_type}: {count} ({pct:.1f}%)")

        if severity_counts:
            print("\nSeverity breakdown:")
            for severity in ["CRITICAL", "ERROR", "WARNING", "INFO"]:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    pct = (count / total_entries * 100) if total_entries > 0 else 0
                    print(f"  {severity}: {count} ({pct:.1f}%)")

        return 0

    except Exception as e:
        print(f"✗ Error reading log file: {e}")
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify the integrity of the L30 audit log",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full verification (uses config values from .env)
  python verify_audit_log.py

  # Verify specific log file
  python verify_audit_log.py --log-path /var/log/l30/audit.log

  # Verify with specific signing key
  python verify_audit_log.py --signing-key "my-secret-key" --log-path /var/log/l30/audit.log

  # Check only JSON syntax
  python verify_audit_log.py --check-syntax /var/log/l30/audit.log

  # Show summary statistics
  python verify_audit_log.py --summary /var/log/l30/audit.log
        """,
    )

    parser.add_argument(
        "--log-path",
        help="Path to audit log file (default: from config)",
    )
    parser.add_argument(
        "--signing-key",
        help="HMAC signing key (default: from config)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with investigation tips",
    )
    parser.add_argument(
        "--check-syntax",
        action="store_true",
        help="Only check JSON syntax, don't verify signatures",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary statistics instead of full verification",
    )

    args = parser.parse_args()

    # Get config values
    settings = get_settings()
    log_path = args.log_path or settings.audit_log_path
    signing_key = args.signing_key or settings.audit_log_signing_key or settings.secret_key

    # Handle different modes
    if args.check_syntax:
        return check_syntax(log_path)

    if args.summary:
        return print_summary(log_path)

    # Default: full verification
    print(f"Verifying audit log: {log_path}")
    if args.verbose:
        print(f"Using signing key: {signing_key[:20]}...")

    is_valid, errors = verify_audit_log(signing_key, log_path)
    return print_verification_results(is_valid, errors, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
