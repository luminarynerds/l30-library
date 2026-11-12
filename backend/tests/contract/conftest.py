# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Contract testing fixtures and helpers.

Provides fixtures that validate API responses against stored JSON Schema
snapshots. Any field addition, removal, or type change that hasn't been
captured by running `python scripts/generate_snapshots.py` will cause a
test failure.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent / "snapshots"


def _load_schema(snapshot_relpath: str) -> dict:
    """Load a JSON Schema snapshot file."""
    path = SNAPSHOTS_DIR / snapshot_relpath
    if not path.exists():
        raise FileNotFoundError(
            f"Snapshot not found: {path}\n"
            "Run 'python scripts/generate_snapshots.py' to generate snapshots."
        )
    return json.loads(path.read_text())


def validate_response_against_snapshot(
    response_data: dict | list,
    snapshot_relpath: str,
    *,
    is_list: bool = False,
) -> None:
    """
    Validate response data against a stored JSON Schema snapshot.

    Args:
        response_data: The parsed JSON response body (dict or list).
        snapshot_relpath: Relative path to the snapshot file under tests/snapshots/.
        is_list: If True, validate each item in the list against the schema.

    Raises:
        jsonschema.ValidationError: If the response doesn't match the schema.
        FileNotFoundError: If the snapshot file is missing.
    """
    schema = _load_schema(snapshot_relpath)
    validator = Draft202012Validator(schema)

    if is_list:
        assert isinstance(response_data, list), (
            f"Expected list response, got {type(response_data).__name__}"
        )
        for i, item in enumerate(response_data):
            errors = list(validator.iter_errors(item))
            if errors:
                msgs = "\n".join(f"  - {e.message} (at {'.'.join(str(p) for p in e.absolute_path)})"
                                 for e in errors)
                raise ValidationError(
                    f"Item [{i}] failed schema validation for {snapshot_relpath}:\n{msgs}"
                )
    else:
        errors = list(validator.iter_errors(response_data))
        if errors:
            msgs = "\n".join(f"  - {e.message} (at {'.'.join(str(p) for p in e.absolute_path)})"
                             for e in errors)
            raise ValidationError(
                f"Response failed schema validation for {snapshot_relpath}:\n{msgs}"
            )


@pytest.fixture
def assert_matches_snapshot():
    """
    Fixture that returns a callable to validate response data against a snapshot.

    Usage in tests:
        def test_checkout(client, assert_matches_snapshot):
            resp = client.post("/api/v1/circulation/checkout", json={"item_id": 1})
            assert resp.status_code == 201
            assert_matches_snapshot(resp.json(), "circulation/CheckoutResponse.json")

        def test_active_checkouts(client, assert_matches_snapshot):
            resp = client.get("/api/v1/circulation/checkouts/active")
            assert resp.status_code == 200
            assert_matches_snapshot(resp.json(), "circulation/CheckoutResponse.json", is_list=True)
    """
    return validate_response_against_snapshot


@pytest.fixture
def load_snapshot():
    """
    Fixture that returns a callable to load a raw snapshot schema dict.

    Useful for custom validation logic.
    """
    return _load_schema
