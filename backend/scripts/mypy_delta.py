"""Pre-commit/CI ratchet: block only NEW mypy errors vs a committed baseline.

Signature = "file::error-code" (line numbers excluded, same rationale as
frontend/scripts/tsc-delta.mjs — unrelated edits shift line numbers).

Usage:
    python backend/scripts/mypy_delta.py              # block on new errors
    python backend/scripts/mypy_delta.py --warn        # report, exit 0
    python backend/scripts/mypy_delta.py --rebaseline  # write current baseline
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
BASELINE_PATH = BACKEND_DIR / ".mypy-baseline.json"
ERROR_RE = re.compile(r"^(?P<file>[^:]+):\d+: error: .+?\[(?P<code>[\w-]+)\]$")


def run_mypy() -> str:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "app", "--no-error-summary"],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise RuntimeError(f"Unable to launch mypy: {exc}") from exc
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"mypy exited {result.returncode}: {result.stderr or result.stdout}"
        )
    malformed = [
        line for line in result.stdout.splitlines()
        if "error:" in line and not ERROR_RE.match(line)
    ]
    if malformed or (result.returncode == 1 and not parse_signatures(result.stdout)):
        raise RuntimeError(f"Unrecognized mypy failure output: {result.stdout}")
    return result.stdout


def parse_signatures(output: str) -> set[str]:
    sigs = set()
    for line in output.splitlines():
        m = ERROR_RE.match(line)
        if m:
            sigs.add(f"{m.group('file')}::{m.group('code')}")
    return sigs


def main(argv: list[str]) -> int:
    warn = "--warn" in argv
    rebaseline = "--rebaseline" in argv

    try:
        current = parse_signatures(run_mypy())
    except RuntimeError as exc:
        print(f"mypy_delta: {exc}", file=sys.stderr)
        return 2

    if rebaseline:
        BASELINE_PATH.write_text(json.dumps(sorted(current), indent=2) + "\n")
        print(f"mypy_delta: baseline written to {BASELINE_PATH} ({len(current)} known signatures)")
        return 0

    if not BASELINE_PATH.exists():
        print(f"mypy_delta: baseline missing at {BASELINE_PATH}; run with --rebaseline first.", file=sys.stderr)
        return 2

    baseline = set(json.loads(BASELINE_PATH.read_text()))
    added = sorted(current - baseline)

    if added:
        print(f"mypy_delta: {len(added)} NEW mypy signature(s) not in baseline:", file=sys.stderr)
        for s in added:
            print(f"  {s}", file=sys.stderr)
        if not warn:
            return 1
    print(f"mypy_delta: {len(current)} total signatures, {len(added)} new vs baseline" + (f" (warn-only, {len(added)} ignored)" if added else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
