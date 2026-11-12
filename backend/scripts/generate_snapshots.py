#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Generate JSON Schema snapshots from Pydantic response models.

Usage:
    python scripts/generate_snapshots.py          # Generate all snapshots
    python scripts/generate_snapshots.py --check   # Check if snapshots are up-to-date (for CI)
    python scripts/generate_snapshots.py --diff     # Show diff of changed snapshots

Snapshots are stored in tests/snapshots/ as JSON files named after the
schema class (e.g., CheckoutResponse.json). These snapshots are used by
contract tests to validate that API responses match the expected schema.
"""

import json
import os
import sys
from pathlib import Path

# Add backend to path so we can import app modules
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Set minimal env vars so app modules can be imported without a running database.
# These are only used during import-time Settings validation - no actual DB
# connections are made. Existing env vars take precedence.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/snapshot_gen_dummy.db")
os.environ.setdefault("SECRET_KEY", "snapshot-generation-key")
os.environ.setdefault("ENVIRONMENT", "test")

SNAPSHOTS_DIR = backend_dir / "tests" / "snapshots"

# Registry of all response schemas to snapshot.
# Format: (module_path, class_name, snapshot_filename)
SCHEMA_REGISTRY: list[tuple[str, str, str]] = [
    # === Circulation Schemas ===
    ("app.schemas.circulation", "CheckoutResponse", "circulation/CheckoutResponse.json"),
    ("app.schemas.circulation", "HoldResponse", "circulation/HoldResponse.json"),
    ("app.schemas.circulation", "CirculationStats", "circulation/CirculationStats.json"),
    ("app.schemas.circulation", "HoldAgingBracket", "circulation/HoldAgingBracket.json"),
    ("app.schemas.circulation", "HoldAgingReport", "circulation/HoldAgingReport.json"),
    ("app.schemas.circulation", "PullListItem", "circulation/PullListItem.json"),
    ("app.schemas.circulation", "LocationGroup", "circulation/LocationGroup.json"),
    ("app.schemas.circulation", "PullListResponse", "circulation/PullListResponse.json"),
    # === Fine Schemas (used by circulation endpoints) ===
    ("app.schemas.fine", "FineResponse", "circulation/FineResponse.json"),
    ("app.schemas.fine", "PatronFineResponse", "circulation/PatronFineResponse.json"),
    ("app.schemas.fine", "FineListResponse", "circulation/FineListResponse.json"),
    ("app.schemas.fine", "FineSummary", "circulation/FineSummary.json"),
    ("app.schemas.fine", "PaymentHistoryResponse", "circulation/PaymentHistoryResponse.json"),
    ("app.schemas.fine", "PaymentPlanResponse", "circulation/PaymentPlanResponse.json"),
    ("app.schemas.fine", "FineAnalyticsResponse", "circulation/FineAnalyticsResponse.json"),
    ("app.schemas.fine", "FineHistoryResponse", "circulation/FineHistoryResponse.json"),
    # === Patron/User Schemas ===
    ("app.schemas.user", "UserResponse", "patron/UserResponse.json"),
    ("app.schemas.user", "UserListResponse", "patron/UserListResponse.json"),
    ("app.schemas.user", "Token", "patron/Token.json"),
    ("app.schemas.user", "SessionInfo", "patron/SessionInfo.json"),
    ("app.schemas.user", "SessionList", "patron/SessionList.json"),
    # === Common Response Schemas ===
    ("app.schemas.common", "JobResponse", "common/JobResponse.json"),
    ("app.schemas.common", "ErrorResponse", "common/ErrorResponse.json"),
    ("app.schemas.common", "MessageResponse", "common/MessageResponse.json"),
    ("app.schemas.common", "BulkOperationResponse", "common/BulkOperationResponse.json"),
]


def import_schema(module_path: str, class_name: str):
    """Dynamically import a Pydantic model class."""
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def generate_snapshot(module_path: str, class_name: str) -> dict:
    """Generate a JSON Schema snapshot from a Pydantic model."""
    model_class = import_schema(module_path, class_name)
    schema = model_class.model_json_schema()
    # Add metadata for tracking
    schema["$comment"] = (
        f"Auto-generated from {module_path}.{class_name}. "
        "Do not edit manually - run: python scripts/generate_snapshots.py"
    )
    return schema


def write_snapshot(snapshot_path: Path, schema: dict) -> None:
    """Write a schema snapshot to disk."""
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


def load_snapshot(snapshot_path: Path) -> dict | None:
    """Load an existing snapshot from disk, or None if missing."""
    if not snapshot_path.exists():
        return None
    return json.loads(snapshot_path.read_text())


def generate_all(check_only: bool = False, show_diff: bool = False) -> bool:
    """
    Generate (or check) all schema snapshots.

    Returns True if all snapshots are up-to-date, False otherwise.
    """
    all_current = True
    changes: list[str] = []

    for module_path, class_name, filename in SCHEMA_REGISTRY:
        snapshot_path = SNAPSHOTS_DIR / filename
        try:
            new_schema = generate_snapshot(module_path, class_name)
        except Exception as e:
            print(f"ERROR: Failed to generate schema for {module_path}.{class_name}: {e}")
            all_current = False
            continue

        existing = load_snapshot(snapshot_path)
        new_text = json.dumps(new_schema, indent=2, sort_keys=True) + "\n"
        existing_text = json.dumps(existing, indent=2, sort_keys=True) + "\n" if existing else ""

        if new_text != existing_text:
            all_current = False
            if existing is None:
                changes.append(f"  NEW: {filename}")
            else:
                changes.append(f"  CHANGED: {filename}")

            if show_diff and existing is not None:
                import difflib
                diff = difflib.unified_diff(
                    existing_text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile=f"a/{filename}",
                    tofile=f"b/{filename}",
                )
                print("".join(diff))

            if not check_only:
                write_snapshot(snapshot_path, new_schema)
                print(f"  Generated: {filename}")
        else:
            if not check_only:
                print(f"  Up-to-date: {filename}")

    if check_only and not all_current:
        print("\nSnapshot check FAILED. The following snapshots are out of date:\n")
        for change in changes:
            print(change)
        print(
            "\nRun 'python scripts/generate_snapshots.py' to update snapshots, "
            "then commit the changes."
        )
    elif check_only:
        print("All snapshots are up-to-date.")

    return all_current


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate or check API response schema snapshots."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if snapshots are up-to-date without writing (exit 1 if stale).",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show unified diff of changed snapshots.",
    )
    args = parser.parse_args()

    up_to_date = generate_all(check_only=args.check, show_diff=args.diff)

    if args.check and not up_to_date:
        sys.exit(1)


if __name__ == "__main__":
    main()
