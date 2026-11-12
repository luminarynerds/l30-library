# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for drift_checks.seed_validation helper functions."""

import sys
from pathlib import Path

# Ensure scripts dir is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from drift_checks.seed_validation import extract_table_refs


class TestExtractTableRefs:
    def test_select_from(self):
        code = 'await session.execute(text("SELECT id FROM users"))'
        result = extract_table_refs(code)
        assert "users" in result

    def test_insert_into(self):
        code = 'await session.execute(text("INSERT INTO events (id) VALUES (1)"))'
        result = extract_table_refs(code)
        assert "events" in result

    def test_update(self):
        code = 'await session.execute(text("UPDATE branches SET name = \'x\'"))'
        result = extract_table_refs(code)
        assert "branches" in result

    def test_multiple_tables(self):
        code = (
            'text("SELECT id FROM users")\n'
            'text("INSERT INTO events (id) VALUES (1)")\n'
            'text("UPDATE branches SET name = \'x\'")\n'
        )
        result = extract_table_refs(code)
        assert result == {"users", "events", "branches"}

    def test_excludes_sql_keywords(self):
        code = 'text("SELECT id FROM select WHERE true")'
        result = extract_table_refs(code)
        # "select" and "true" should be excluded as keywords
        assert "select" not in result
        assert "true" not in result

    def test_seq_tables_list(self):
        code = '''
seq_tables = ["users", "events", "branches"]
'''
        result = extract_table_refs(code)
        assert result == {"users", "events", "branches"}

    def test_seq_tables_multiline(self):
        code = '''seq_tables = [
    "users",
    "events",
    "branches",
]'''
        result = extract_table_refs(code)
        assert result == {"users", "events", "branches"}

    def test_empty_code(self):
        assert extract_table_refs("") == set()

    def test_no_sql_patterns(self):
        code = "x = 1\ny = 2\nprint('hello')"
        assert extract_table_refs(code) == set()

    def test_case_insensitive_keywords(self):
        code = 'text("select id from users")'
        result = extract_table_refs(code)
        assert "users" in result

    def test_join_not_captured_as_table(self):
        code = 'text("SELECT id FROM users JOIN events ON users.id = events.user_id")'
        result = extract_table_refs(code)
        assert "users" in result
        # "join" is a SQL keyword and should not be captured
        assert "join" not in result
