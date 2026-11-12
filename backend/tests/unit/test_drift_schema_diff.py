# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for drift_checks.schema_diff helper functions."""

import sys
from pathlib import Path

# Ensure scripts dir is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from drift_checks.schema_diff import (
    _normalize_type,
    compare_columns,
    load_deferred_tables,
)


class TestLoadDeferredTables:
    def test_parses_table_names(self, tmp_path):
        f = tmp_path / "deferred_tables.txt"
        f.write_text(
            "# comment\n"
            "ada_compliance\n"
            "agent_analytics\n"
            "\n"
            "# another comment\n"
            "alarm_system_integrations\n"
        )
        result = load_deferred_tables(str(f))
        assert result == {"ada_compliance", "agent_analytics", "alarm_system_integrations"}

    def test_skips_double_hash_lines(self, tmp_path):
        f = tmp_path / "deferred_tables.txt"
        f.write_text(
            "ada_compliance\n"
            "## eod_sessions  # needed by scheduler\n"
            "agent_analytics\n"
        )
        result = load_deferred_tables(str(f))
        assert result == {"ada_compliance", "agent_analytics"}
        assert "eod_sessions" not in result

    def test_missing_file(self):
        result = load_deferred_tables("/nonexistent/deferred_tables.txt")
        assert result == set()

    def test_empty_file(self, tmp_path):
        f = tmp_path / "deferred_tables.txt"
        f.write_text("# only comments\n\n")
        result = load_deferred_tables(str(f))
        assert result == set()


class TestNormalizeType:
    def test_character_varying(self):
        assert _normalize_type("CHARACTER VARYING") == "VARCHAR"

    def test_timestamp_with_tz(self):
        assert _normalize_type("TIMESTAMP WITH TIME ZONE") == "TIMESTAMPTZ"

    def test_timestamp_without_tz(self):
        assert _normalize_type("TIMESTAMP WITHOUT TIME ZONE") == "TIMESTAMP"

    def test_double_precision(self):
        assert _normalize_type("DOUBLE PRECISION") == "FLOAT"

    def test_boolean(self):
        assert _normalize_type("BOOLEAN") == "BOOL"

    def test_integer(self):
        assert _normalize_type("INTEGER") == "INT"

    def test_strips_length_specifier(self):
        assert _normalize_type("VARCHAR(255)") == "VARCHAR"

    def test_preserves_unknown_types(self):
        assert _normalize_type("TEXT") == "TEXT"

    def test_case_insensitive_input(self):
        assert _normalize_type("character varying") == "VARCHAR"

    def test_strips_whitespace(self):
        assert _normalize_type("  BOOLEAN  ") == "BOOL"


class TestCompareColumns:
    def test_identical_columns(self):
        model = {"id": "INTEGER", "name": "VARCHAR(255)"}
        db = {"id": "integer", "name": "character varying"}
        missing, mismatches = compare_columns("test_table", model, db)
        assert missing == []
        assert mismatches == []

    def test_missing_column(self):
        model = {"id": "INTEGER", "name": "VARCHAR", "email": "VARCHAR"}
        db = {"id": "integer", "name": "character varying"}
        missing, mismatches = compare_columns("test_table", model, db)
        assert missing == ["email"]

    def test_type_mismatch(self):
        model = {"id": "INTEGER", "score": "TEXT"}
        db = {"id": "integer", "score": "double precision"}
        missing, mismatches = compare_columns("test_table", model, db)
        assert missing == []
        assert len(mismatches) == 1
        assert mismatches[0][0] == "score"

    def test_empty_model(self):
        missing, mismatches = compare_columns("test_table", {}, {"id": "integer"})
        assert missing == []
        assert mismatches == []

    def test_all_missing(self):
        model = {"x": "INT", "y": "INT"}
        missing, mismatches = compare_columns("test_table", model, {})
        assert set(missing) == {"x", "y"}
