# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the shared catalog-subjects parser."""
from __future__ import annotations

from app.services.catalog_subjects import parse_subjects_field


def test_empty_inputs_return_empty_list():
    assert parse_subjects_field(None) == []
    assert parse_subjects_field("") == []
    assert parse_subjects_field("   ") == []


def test_comma_delimited():
    assert parse_subjects_field("Fiction, Memoir, History") == [
        "Fiction", "Memoir", "History",
    ]


def test_semicolon_delimited():
    """Prod has semicolons mixed in with commas across the same table."""
    assert parse_subjects_field("Fiction; Memoir; History") == [
        "Fiction", "Memoir", "History",
    ]


def test_mixed_comma_and_semicolon():
    assert parse_subjects_field("Fiction, Memoir; History,Science") == [
        "Fiction", "Memoir", "History", "Science",
    ]


def test_python_array_literal_single_quote():
    """A few rows from an older import landed in the table as Python repr."""
    assert parse_subjects_field("['Fiction', 'Memoir', 'History']") == [
        "Fiction", "Memoir", "History",
    ]


def test_python_array_literal_double_quote():
    assert parse_subjects_field('["Fiction", "Memoir"]') == ["Fiction", "Memoir"]


def test_python_array_literal_empty():
    assert parse_subjects_field("[]") == []


def test_python_array_literal_with_whitespace():
    assert parse_subjects_field("[ 'Fiction' , 'Memoir' ]") == ["Fiction", "Memoir"]


def test_malformed_array_falls_through_to_delimiter_split():
    """Unterminated quotes shouldn't raise; we get *something* useful."""
    result = parse_subjects_field("['Fiction, 'Memoir']")
    # Doesn't matter exactly what split returns -- only that it doesn't raise.
    assert isinstance(result, list)
    assert all(isinstance(s, str) for s in result)


def test_drops_empty_substrings():
    assert parse_subjects_field("Fiction,,Memoir,;,History") == [
        "Fiction", "Memoir", "History",
    ]


def test_strips_whitespace():
    assert parse_subjects_field("   Fiction   ;   Memoir   ") == ["Fiction", "Memoir"]


def test_single_subject_no_delimiter():
    assert parse_subjects_field("Fiction") == ["Fiction"]


def test_lcsh_subdivisions_preserved():
    """LCSH headings use ``--`` for subdivisions; parser must keep them."""
    assert parse_subjects_field("Cooking -- Italian; Fiction -- Psychological") == [
        "Cooking -- Italian", "Fiction -- Psychological",
    ]


def test_non_list_array_literal_falls_through():
    """A dict literal shouldn't be misread as a subject list."""
    result = parse_subjects_field("{'a': 1}")
    # Falls through to delimiter split -- result depends on raw characters
    # but must remain a list of strings.
    assert isinstance(result, list)
