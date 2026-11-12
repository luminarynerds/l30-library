#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drift detection entry point for L30.

Usage:
    python check_drift.py --mode startup       # fast checks only
    python check_drift.py --mode full           # all checks
    python check_drift.py --check enum_sync     # single check
    python check_drift.py --mode full --json    # JSON output to stdout
"""

import argparse
import asyncio
import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Registry: name -> (module, function, modes)
# ---------------------------------------------------------------------------
CHECK_REGISTRY: Dict[str, Tuple[str, str, Set[str]]] = {
    "enum_sync":       ("drift_checks.enum_sync",       "check_enum_sync",       {"startup", "full"}),
    "import_health":   ("drift_checks.import_health",   "check_import_health",   {"startup", "full"}),
    "schema_diff":     ("drift_checks.schema_diff",     "check_schema_diff",     {"full"}),
    "seed_validation": ("drift_checks.seed_validation", "check_seed_validation", {"full"}),
    "alembic_chain":   ("drift_checks.alembic_chain",   "check_alembic_chain",   {"full"}),
}

REPORT_PATH = "/tmp/drift_report.json"


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------
async def run_checks(
    mode: str,
    single_check: Optional[str] = None,
    suppressions_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Run selected drift checks and return a report dict."""
    from drift_checks.suppressions import load_suppressions

    if suppressions_path is None:
        suppressions_path = str(
            Path(__file__).parent / "drift_checks" / ".driftignore"
        )
    rules = load_suppressions(suppressions_path)

    results: List[Dict[str, Any]] = []
    checks_to_run = {}

    if single_check:
        if single_check not in CHECK_REGISTRY:
            print(f"Unknown check: {single_check}", file=sys.stderr)
            sys.exit(2)
        checks_to_run[single_check] = CHECK_REGISTRY[single_check]
    else:
        for name, (mod, func, modes) in CHECK_REGISTRY.items():
            if mode in modes:
                checks_to_run[name] = (mod, func, modes)

    for name, (mod_path, func_name, _modes) in checks_to_run.items():
        t0 = time.monotonic()
        try:
            mod = importlib.import_module(mod_path)
            check_fn = getattr(mod, func_name)
            findings = await check_fn(rules)
        except ImportError as exc:
            findings = [{"level": "error", "msg": f"Check module not found: {exc}"}]
        except Exception as exc:
            findings = [{"level": "error", "msg": f"Check failed: {exc}"}]
        elapsed = round(time.monotonic() - t0, 3)

        results.append(
            {
                "check": name,
                "findings": findings,
                "elapsed_s": elapsed,
            }
        )

    total_findings = sum(len(r["findings"]) for r in results)
    total_errors = sum(1 for r in results for f in r["findings"] if f.get("level") == "error")
    report = {
        "mode": mode,
        "total_findings": total_findings,
        "total_errors": total_errors,
        "results": results,
    }
    return report


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def print_summary(report: Dict[str, Any]) -> None:
    """Print a human-readable summary to stderr."""
    mode = report["mode"]
    total = report["total_findings"]
    print(f"\n=== Drift Report (mode={mode}) ===", file=sys.stderr)
    for r in report["results"]:
        status = "PASS" if not r["findings"] else f"DRIFT ({len(r['findings'])})"
        print(
            f"  {r['check']:<20s} {status:<16s} ({r['elapsed_s']:.3f}s)",
            file=sys.stderr,
        )
    print(f"\nTotal findings: {total}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="L30 drift detection")
    parser.add_argument(
        "--mode",
        choices=["startup", "full"],
        default="startup",
        help="Which set of checks to run (default: startup)",
    )
    parser.add_argument(
        "--check",
        type=str,
        default=None,
        help="Run a single named check",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Write JSON to stdout instead of summary",
    )
    args = parser.parse_args()

    # Ensure drift_checks package is importable
    scripts_dir = str(Path(__file__).parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    # Ensure app.* imports work
    backend_dir = str(Path(__file__).parent.parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    report = asyncio.run(run_checks(mode=args.mode, single_check=args.check))

    # Write JSON report to disk
    Path(REPORT_PATH).write_text(json.dumps(report, indent=2))

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print_summary(report)

    sys.exit(1 if report["total_errors"] > 0 else 0)


if __name__ == "__main__":
    main()
