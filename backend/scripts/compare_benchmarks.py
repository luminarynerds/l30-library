#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Compare benchmark results against a baseline and fail if any of the top 20
endpoints regressed by more than the allowed threshold.

Exit codes:
    0 - No regressions detected (or baseline missing for an endpoint)
    1 - One or more endpoints regressed beyond threshold
    2 - Invalid arguments or missing files

Usage:
    python scripts/compare_benchmarks.py \
        --baseline benchmarks/baseline.json \
        --current  benchmarks/results.json \
        --threshold 20 \
        --metric p95_ms

    The --metric flag controls which latency metric is compared.
    Supported values: mean_ms, median_ms, p95_ms, p99_ms

    The --threshold flag sets the maximum allowed regression percentage.
"""

import argparse
import json
import sys
from pathlib import Path


VALID_METRICS = ("mean_ms", "median_ms", "p95_ms", "p99_ms")


def load_json(path: Path) -> dict:
    """Load and return a JSON file."""
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(2)
    with open(path) as f:
        return json.load(f)


def compare(
    baseline: dict,
    current: dict,
    metric: str,
    threshold_pct: float,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Compare current benchmark results against the baseline.

    Returns (regressions, improvements, unchanged) where each item is a dict
    with endpoint name, baseline value, current value, and change percentage.
    """
    regressions = []
    improvements = []
    unchanged = []

    for name, baseline_data in baseline.items():
        if name not in current:
            continue

        current_data = current[name]
        base_val = baseline_data.get(metric, 0)
        curr_val = current_data.get(metric, 0)

        # Skip endpoints where baseline is zero (no meaningful comparison)
        if base_val == 0:
            unchanged.append({
                "name": name,
                "baseline": base_val,
                "current": curr_val,
                "change_pct": 0.0,
            })
            continue

        change_pct = ((curr_val - base_val) / base_val) * 100

        entry = {
            "name": name,
            "baseline": round(base_val, 2),
            "current": round(curr_val, 2),
            "change_pct": round(change_pct, 1),
        }

        if change_pct > threshold_pct:
            regressions.append(entry)
        elif change_pct < -threshold_pct:
            improvements.append(entry)
        else:
            unchanged.append(entry)

    return regressions, improvements, unchanged


def print_report(
    regressions: list[dict],
    improvements: list[dict],
    unchanged: list[dict],
    metric: str,
    threshold_pct: float,
) -> None:
    """Print a formatted comparison report."""
    total = len(regressions) + len(improvements) + len(unchanged)

    print()
    print("=" * 90)
    print(f"PERFORMANCE BENCHMARK COMPARISON  (metric={metric}, threshold={threshold_pct}%)")
    print("=" * 90)

    if regressions:
        print(f"\n  REGRESSIONS ({len(regressions)} endpoints exceeded +{threshold_pct}% threshold):")
        print(f"  {'Endpoint':<45} {'Baseline':>10} {'Current':>10} {'Change':>10}")
        print("  " + "-" * 78)
        for r in sorted(regressions, key=lambda x: x["change_pct"], reverse=True):
            print(
                f"  {r['name']:<45} "
                f"{r['baseline']:>9.1f}ms "
                f"{r['current']:>9.1f}ms "
                f"{r['change_pct']:>+8.1f}%"
            )

    if improvements:
        print(f"\n  IMPROVEMENTS ({len(improvements)} endpoints):")
        print(f"  {'Endpoint':<45} {'Baseline':>10} {'Current':>10} {'Change':>10}")
        print("  " + "-" * 78)
        for r in sorted(improvements, key=lambda x: x["change_pct"]):
            print(
                f"  {r['name']:<45} "
                f"{r['baseline']:>9.1f}ms "
                f"{r['current']:>9.1f}ms "
                f"{r['change_pct']:>+8.1f}%"
            )

    if unchanged:
        print(f"\n  WITHIN THRESHOLD ({len(unchanged)} endpoints):")
        print(f"  {'Endpoint':<45} {'Baseline':>10} {'Current':>10} {'Change':>10}")
        print("  " + "-" * 78)
        for r in sorted(unchanged, key=lambda x: x["change_pct"], reverse=True):
            baseline_str = f"{r['baseline']:.1f}ms" if r["baseline"] else "N/A"
            current_str = f"{r['current']:.1f}ms" if r["current"] else "N/A"
            print(
                f"  {r['name']:<45} "
                f"{baseline_str:>10} "
                f"{current_str:>10} "
                f"{r['change_pct']:>+8.1f}%"
            )

    print()
    print("=" * 90)
    print(f"  SUMMARY: {total} endpoints compared | "
          f"{len(regressions)} regressed | "
          f"{len(improvements)} improved | "
          f"{len(unchanged)} within threshold")
    print("=" * 90)


def write_github_summary(
    regressions: list[dict],
    improvements: list[dict],
    unchanged: list[dict],
    metric: str,
    threshold_pct: float,
) -> None:
    """Write a markdown summary to $GITHUB_STEP_SUMMARY if available."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    lines = []
    lines.append("## Performance Benchmark Results\n")

    total = len(regressions) + len(improvements) + len(unchanged)
    if regressions:
        lines.append(
            f"**{len(regressions)} of {total} endpoints regressed "
            f"beyond the {threshold_pct}% threshold ({metric})**\n"
        )
        lines.append("### Regressions\n")
        lines.append("| Endpoint | Baseline | Current | Change |")
        lines.append("|----------|----------|---------|--------|")
        for r in sorted(regressions, key=lambda x: x["change_pct"], reverse=True):
            lines.append(
                f"| `{r['name']}` | {r['baseline']:.1f}ms | "
                f"{r['current']:.1f}ms | **+{r['change_pct']:.1f}%** |"
            )
        lines.append("")
    else:
        lines.append(
            f"All {total} endpoints are within the {threshold_pct}% "
            f"regression threshold ({metric}).\n"
        )

    if improvements:
        lines.append("### Improvements\n")
        lines.append("| Endpoint | Baseline | Current | Change |")
        lines.append("|----------|----------|---------|--------|")
        for r in sorted(improvements, key=lambda x: x["change_pct"]):
            lines.append(
                f"| `{r['name']}` | {r['baseline']:.1f}ms | "
                f"{r['current']:.1f}ms | {r['change_pct']:.1f}% |"
            )
        lines.append("")

    with open(summary_path, "a") as f:
        f.write("\n".join(lines) + "\n")


import os  # noqa: E402 (needed for write_github_summary, placed here to keep imports grouped)


def main():
    parser = argparse.ArgumentParser(
        description="Compare performance benchmarks against a baseline."
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to the baseline JSON file",
    )
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to the current benchmark results JSON file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="Maximum allowed regression percentage (default: 20)",
    )
    parser.add_argument(
        "--metric",
        type=str,
        default="p95_ms",
        choices=VALID_METRICS,
        help="Latency metric to compare (default: p95_ms)",
    )

    args = parser.parse_args()

    if args.metric not in VALID_METRICS:
        print(f"ERROR: Invalid metric '{args.metric}'. Must be one of: {VALID_METRICS}")
        sys.exit(2)

    baseline = load_json(args.baseline)
    current = load_json(args.current)

    regressions, improvements, unchanged = compare(
        baseline, current, args.metric, args.threshold
    )

    print_report(regressions, improvements, unchanged, args.metric, args.threshold)
    write_github_summary(regressions, improvements, unchanged, args.metric, args.threshold)

    if regressions:
        print(
            f"\nFAILED: {len(regressions)} endpoint(s) regressed by more than "
            f"{args.threshold}% on {args.metric}."
        )
        sys.exit(1)
    else:
        print(f"\nPASSED: No regressions beyond {args.threshold}% detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
