#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Store performance benchmark results in a historical JSONL file.

Each run appends a timestamped entry so trends are visible over time.
The history file lives at benchmarks/history.jsonl and is committed to the
repository so it persists across CI runs.

Usage:
    python scripts/store_perf_history.py \
        --results benchmarks/results.json \
        --history benchmarks/history.jsonl \
        [--branch main] [--commit abc123] [--run-id 12345]

Each line in the JSONL file is a JSON object:
{
    "timestamp": "2025-01-15T10:30:00Z",
    "branch": "main",
    "commit_sha": "abc1234",
    "run_id": "12345",
    "endpoints": { ... results dict ... }
}
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_results(path: Path) -> dict:
    """Load benchmark results JSON."""
    if not path.exists():
        print(f"ERROR: Results file not found: {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def append_history(
    history_path: Path,
    results: dict,
    branch: str,
    commit_sha: str,
    run_id: str,
) -> int:
    """Append results to the JSONL history file. Returns total entry count."""
    history_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "branch": branch,
        "commit_sha": commit_sha,
        "run_id": run_id,
        "endpoints": results,
    }

    with open(history_path, "a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    # Count entries
    with open(history_path) as f:
        count = sum(1 for _ in f)

    return count


def trim_history(history_path: Path, max_entries: int = 500) -> None:
    """Keep only the most recent max_entries lines to prevent unbounded growth."""
    if not history_path.exists():
        return

    with open(history_path) as f:
        lines = f.readlines()

    if len(lines) <= max_entries:
        return

    # Keep the last max_entries lines
    trimmed = lines[-max_entries:]
    with open(history_path, "w") as f:
        f.writelines(trimmed)

    print(f"  Trimmed history from {len(lines)} to {len(trimmed)} entries")


def print_trend(history_path: Path, metric: str = "p95_ms", last_n: int = 10) -> None:
    """Print a simple trend summary for each endpoint over the last N runs."""
    if not history_path.exists():
        return

    with open(history_path) as f:
        entries = [json.loads(line) for line in f]

    recent = entries[-last_n:]
    if len(recent) < 2:
        print("  Not enough history for trend analysis.")
        return

    # Gather endpoint names from the most recent run
    latest = recent[-1]
    endpoint_names = list(latest.get("endpoints", {}).keys())

    print(f"\n  PERFORMANCE TRENDS (last {len(recent)} runs, metric={metric})")
    print(f"  {'Endpoint':<45} {'Oldest':>10} {'Latest':>10} {'Trend':>10}")
    print("  " + "-" * 78)

    for ep_name in endpoint_names:
        values = []
        for entry in recent:
            ep_data = entry.get("endpoints", {}).get(ep_name)
            if ep_data and metric in ep_data:
                values.append(ep_data[metric])

        if len(values) < 2:
            continue

        oldest = values[0]
        latest_val = values[-1]
        if oldest > 0:
            change_pct = ((latest_val - oldest) / oldest) * 100
            trend = f"{change_pct:+.1f}%"
        else:
            trend = "N/A"

        print(
            f"  {ep_name:<45} "
            f"{oldest:>9.1f}ms "
            f"{latest_val:>9.1f}ms "
            f"{trend:>10}"
        )


def generate_summary_markdown(history_path: Path, metric: str = "p95_ms") -> str:
    """Generate a markdown summary table for the GitHub step summary."""
    if not history_path.exists():
        return ""

    with open(history_path) as f:
        entries = [json.loads(line) for line in f]

    if not entries:
        return ""

    latest = entries[-1]
    previous = entries[-2] if len(entries) >= 2 else None

    lines = ["## Performance Trend Summary\n"]
    lines.append(f"**Metric:** `{metric}` | **History entries:** {len(entries)}\n")
    lines.append("| Endpoint | Current | Previous | Change |")
    lines.append("|----------|---------|----------|--------|")

    for ep_name, ep_data in latest.get("endpoints", {}).items():
        curr = ep_data.get(metric, 0)
        if previous:
            prev_data = previous.get("endpoints", {}).get(ep_name, {})
            prev = prev_data.get(metric, 0)
            if prev > 0:
                change = ((curr - prev) / prev) * 100
                change_str = f"{change:+.1f}%"
            else:
                change_str = "N/A"
        else:
            prev = 0
            change_str = "baseline"

        lines.append(
            f"| `{ep_name}` | {curr:.1f}ms | "
            f"{f'{prev:.1f}ms' if prev else 'N/A'} | {change_str} |"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Store performance benchmark results in history."
    )
    parser.add_argument(
        "--results", type=Path, required=True,
        help="Path to the current benchmark results JSON",
    )
    parser.add_argument(
        "--history", type=Path, default=Path("benchmarks/history.jsonl"),
        help="Path to the JSONL history file (default: benchmarks/history.jsonl)",
    )
    parser.add_argument("--branch", default=os.environ.get("GITHUB_REF_NAME", "unknown"))
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "unknown")[:8])
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    parser.add_argument("--max-entries", type=int, default=500,
                        help="Max history entries to keep (default: 500)")

    args = parser.parse_args()

    results = load_results(args.results)

    count = append_history(
        args.history, results, args.branch, args.commit, args.run_id
    )
    print(f"  Stored results ({count} total entries in history)")

    trim_history(args.history, args.max_entries)
    print_trend(args.history)

    # Write GitHub summary if available
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        md = generate_summary_markdown(args.history)
        if md:
            with open(summary_path, "a") as f:
                f.write("\n" + md + "\n")


if __name__ == "__main__":
    main()
