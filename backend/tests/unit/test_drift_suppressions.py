# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import sys
from pathlib import Path

# Ensure scripts dir is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from drift_checks.suppressions import load_suppressions, is_suppressed


def test_load_suppressions_parses_rules(tmp_path):
    ignore = tmp_path / ".driftignore"
    ignore.write_text(
        "# comment line\n"
        "\n"
        "schema_diff:ignore_table:apscheduler_jobs\n"
        "enum_sync:ignore_type:backdate_mode_enum\n"
    )
    rules = load_suppressions(str(ignore))
    assert len(rules) == 2
    assert rules[0] == ("schema_diff", "ignore_table", "apscheduler_jobs")
    assert rules[1] == ("enum_sync", "ignore_type", "backdate_mode_enum")


def test_load_suppressions_empty_file(tmp_path):
    ignore = tmp_path / ".driftignore"
    ignore.write_text("# only comments\n\n")
    rules = load_suppressions(str(ignore))
    assert rules == []


def test_load_suppressions_missing_file():
    rules = load_suppressions("/nonexistent/.driftignore")
    assert rules == []


def test_is_suppressed_matches():
    rules = [("enum_sync", "ignore_type", "backdate_mode_enum")]
    assert is_suppressed(rules, "enum_sync", "ignore_type", "backdate_mode_enum") is True
    assert is_suppressed(rules, "enum_sync", "ignore_type", "other") is False
    assert is_suppressed(rules, "schema_diff", "ignore_table", "foo") is False
