# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for drift_checks.enum_sync helper functions."""

import sys
from pathlib import Path

# Ensure scripts dir is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
# Ensure app.* is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from drift_checks.enum_sync import diff_enum_values, get_python_enums


class TestGetPythonEnums:
    def test_returns_list(self):
        result = get_python_enums()
        assert isinstance(result, list)

    def test_all_are_str_enum_subclasses(self):
        from enum import Enum

        result = get_python_enums()
        for cls in result:
            assert issubclass(cls, str), f"{cls.__name__} is not a str subclass"
            assert issubclass(cls, Enum), f"{cls.__name__} is not an Enum subclass"

    def test_includes_known_enums(self):
        result = get_python_enums()
        names = {cls.__name__ for cls in result}
        # These should exist in any L30 models package
        assert "ItemType" in names or "UserRole" in names, (
            f"Expected at least one known enum, got: {sorted(names)[:10]}"
        )


class TestDiffEnumValues:
    def test_identical_sets(self):
        result = diff_enum_values("status", {"a", "b"}, {"a", "b"})
        assert result["missing_in_db"] == set()
        assert result["extra_in_db"] == set()
        assert result["case_mismatches"] == []

    def test_missing_in_db(self):
        result = diff_enum_values("status", {"a", "b", "c"}, {"a", "b"})
        assert result["missing_in_db"] == {"c"}
        assert result["extra_in_db"] == set()

    def test_extra_in_db(self):
        result = diff_enum_values("status", {"a"}, {"a", "b"})
        assert result["extra_in_db"] == {"b"}
        assert result["missing_in_db"] == set()

    def test_case_mismatches(self):
        result = diff_enum_values("status", {"Active", "pending"}, {"active", "pending"})
        assert result["missing_in_db"] == {"Active"}
        assert result["extra_in_db"] == {"active"}
        assert ("Active", "active") in result["case_mismatches"]

    def test_completely_disjoint(self):
        result = diff_enum_values("status", {"x", "y"}, {"a", "b"})
        assert result["missing_in_db"] == {"x", "y"}
        assert result["extra_in_db"] == {"a", "b"}

    def test_empty_python(self):
        result = diff_enum_values("status", set(), {"a"})
        assert result["extra_in_db"] == {"a"}
        assert result["missing_in_db"] == set()

    def test_empty_db(self):
        result = diff_enum_values("status", {"a"}, set())
        assert result["missing_in_db"] == {"a"}
        assert result["extra_in_db"] == set()
