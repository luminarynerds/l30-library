# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the catalog query parser.

Pure-Python tests (no DB). Pin the grammar described in
``catalog_query_parser.py``.
"""
from __future__ import annotations

import pytest

from app.services.catalog_query_parser import ParsedQuery, parse


# ---------------------------------------------------------------------------
# Empty / passthrough
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("q", [None, "", "   "])
def test_empty_input_returns_empty(q):
    parsed = parse(q)
    assert parsed.is_empty
    assert parsed.residue == ""
    assert parsed.scoped == {}
    assert parsed.isbn is None


def test_bare_term_lands_in_residue():
    parsed = parse("mockingbird")
    assert parsed.residue == "mockingbird"
    assert parsed.scoped == {}
    assert parsed.isbn is None


def test_multiple_bare_terms_preserved_in_residue():
    parsed = parse("kill a mockingbird")
    assert parsed.residue == "kill a mockingbird"
    assert parsed.scoped == {}


# ---------------------------------------------------------------------------
# Quoted phrases pass through verbatim -- websearch_to_tsquery handles them.
# ---------------------------------------------------------------------------


def test_quoted_phrase_passes_through_to_residue():
    parsed = parse('"to kill a mockingbird"')
    # Residue keeps the quotes so websearch_to_tsquery sees the phrase op.
    assert parsed.residue == '"to kill a mockingbird"'
    assert parsed.scoped == {}


def test_quoted_phrase_with_bare_term_outside():
    parsed = parse('"kill a mockingbird" lee')
    assert '"kill a mockingbird"' in parsed.residue
    assert "lee" in parsed.residue


# ---------------------------------------------------------------------------
# Field-scoped tokens
# ---------------------------------------------------------------------------


def test_title_field_bare_value():
    parsed = parse("title:teaching")
    assert parsed.scoped == {"title": ["teaching"]}
    assert parsed.residue == ""


def test_author_field_quoted_value():
    parsed = parse('author:"bell hooks"')
    assert parsed.scoped == {"author": ["bell hooks"]}
    assert parsed.residue == ""


def test_multiple_fields_combined():
    parsed = parse("title:teaching subject:pedagogy")
    assert parsed.scoped == {"title": ["teaching"], "subject": ["pedagogy"]}
    assert parsed.residue == ""


def test_field_and_bare_term_coexist():
    parsed = parse("teaching subject:pedagogy")
    assert parsed.scoped == {"subject": ["pedagogy"]}
    assert parsed.residue == "teaching"


def test_series_field():
    parsed = parse("series:dune")
    assert parsed.scoped == {"series": ["dune"]}


def test_repeated_field_accumulates():
    parsed = parse("subject:pedagogy subject:literacy")
    assert parsed.scoped == {"subject": ["pedagogy", "literacy"]}


def test_field_name_is_case_insensitive():
    parsed = parse("Author:hooks TITLE:teaching")
    assert parsed.scoped == {"author": ["hooks"], "title": ["teaching"]}


# ---------------------------------------------------------------------------
# Unknown fields degrade to bare term (don't surprise patrons)
# ---------------------------------------------------------------------------


def test_unknown_field_falls_through_to_residue():
    parsed = parse("xyz:abc")
    assert parsed.scoped == {}
    # The literal token survives -- websearch_to_tsquery will treat it
    # as bag-of-words. (PG will tokenize on ':'.)
    assert "xyz:abc" in parsed.residue


# ---------------------------------------------------------------------------
# ISBN handling: bare digits and explicit isbn:
# ---------------------------------------------------------------------------


def test_bare_isbn13_routed_to_isbn_bucket():
    parsed = parse("9780446310789")
    assert parsed.isbn == "9780446310789"
    assert parsed.residue == ""
    assert parsed.scoped == {}


def test_bare_isbn10_routed_to_isbn_bucket():
    parsed = parse("0446310786")
    assert parsed.isbn == "0446310786"


def test_isbn10_with_x_check_digit():
    parsed = parse("097522980X")
    assert parsed.isbn == "097522980X"


def test_hyphenated_isbn_normalizes():
    parsed = parse("978-0-446-31078-9")
    assert parsed.isbn == "9780446310789"


def test_explicit_isbn_field():
    parsed = parse("isbn:0446310786")
    assert parsed.isbn == "0446310786"
    assert parsed.residue == ""


def test_explicit_isbn_with_hyphens():
    parsed = parse("isbn:978-0-446-31078-9")
    assert parsed.isbn == "9780446310789"


def test_explicit_isbn_overrides_bare_isbn_in_same_query():
    # Patron typed both; explicit field wins.
    parsed = parse("9780000000000 isbn:9780446310789")
    assert parsed.isbn == "9780446310789"


# ---------------------------------------------------------------------------
# websearch_to_tsquery operators pass through unchanged
# ---------------------------------------------------------------------------


def test_negation_passes_through():
    parsed = parse("-vampire dracula")
    assert "-vampire" in parsed.residue
    assert "dracula" in parsed.residue


def test_or_operator_passes_through():
    parsed = parse("science OR fiction")
    assert parsed.residue == "science OR fiction"


def test_lowercase_or_passes_through():
    parsed = parse("science or fiction")
    # We don't normalize -- websearch_to_tsquery accepts both, and we
    # want to preserve patron intent.
    assert parsed.residue == "science or fiction"


# ---------------------------------------------------------------------------
# is_empty semantics
# ---------------------------------------------------------------------------


def test_only_unknown_field_is_not_empty():
    # Falls through to residue, so it's still a real query.
    parsed = parse("foo:bar")
    assert not parsed.is_empty


def test_only_scoped_is_not_empty():
    parsed = parse("title:teaching")
    assert not parsed.is_empty


def test_only_isbn_is_not_empty():
    parsed = parse("9780446310789")
    assert not parsed.is_empty


def test_parsed_query_dataclass_defaults():
    pq = ParsedQuery()
    assert pq.residue == ""
    assert pq.scoped == {}
    assert pq.isbn is None
    assert pq.is_empty
