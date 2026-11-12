#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Update the performance benchmark baseline from the latest results.

Run this after verifying that the current benchmark results represent
the expected performance profile (e.g. after landing a performance
improvement or after accepting a known regression).

Usage:
    # Run benchmarks first
    cd backend
    python -m pytest tests/test_benchmark_endpoints.py -v -s --override-ini="addopts="

    # Then update baseline from results
    python scripts/update_benchmark_baseline.py

    # Or specify a custom source
    python scripts/update_benchmark_baseline.py --source benchmarks/results.json
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parent.parent / "benchmarks"
DEFAULT_RESULTS = BENCHMARKS_DIR / "results.json"
BASELINE_FILE = BENCHMARKS_DIR / "baseline.json"


def main():
    parser = argparse.ArgumentParser(
        description="Update the benchmark baseline from the latest results."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_RESULTS,
        help=f"Path to the results file (default: {DEFAULT_RESULTS})",
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"ERROR: Results file not found: {args.source}")
        print("Run the benchmarks first:")
        print('  python -m pytest tests/test_benchmark_endpoints.py -v -s --override-ini="addopts="')
        sys.exit(1)

    # Load and validate the results
    with open(args.source) as f:
        results = json.load(f)

    if not results:
        print("ERROR: Results file is empty.")
        sys.exit(1)

    endpoint_count = len(results)
    successful = sum(1 for r in results.values() if r.get("iterations", 0) > 0)

    print(f"Results: {endpoint_count} endpoints, {successful} with data")

    if successful == 0:
        print("ERROR: No endpoints have measurement data. Aborting.")
        sys.exit(1)

    # Back up current baseline if it exists
    if BASELINE_FILE.exists():
        backup = BASELINE_FILE.with_suffix(
            f".backup-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        shutil.copy2(BASELINE_FILE, backup)
        print(f"Previous baseline backed up to: {backup.name}")

    # Write the new baseline
    BASELINE_FILE.write_text(json.dumps(results, indent=2))
    print(f"Baseline updated: {BASELINE_FILE}")
    print(f"  Endpoints: {endpoint_count}")
    print(f"  Successful measurements: {successful}")

    # Print a summary
    print("\nNew baseline summary:")
    print(f"  {'Endpoint':<45} {'p95_ms':>10}")
    print("  " + "-" * 58)
    for name, data in sorted(results.items()):
        p95 = data.get("p95_ms", 0)
        print(f"  {name:<45} {p95:>9.1f}ms")


if __name__ == "__main__":
    main()
