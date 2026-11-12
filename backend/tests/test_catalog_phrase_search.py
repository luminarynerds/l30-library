# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""End-to-end tests for catalog phrase + fielded search.

Drives the helper directly so we exercise the parser + websearch_to_tsquery
plumbing without standing up the FastAPI app. Requires Postgres -- the
``search_tsv`` column is a STORED GENERATED column and ``websearch_to_tsquery``
is a Postgres-specific function, so these tests skip cleanly under SQLite.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.catalog.helpers import _execute_catalog_search
from app.models.catalog import CatalogingStatus, CatalogItem, ItemStatus, ItemType
from app.models.subject import CatalogItemSubject, Subject


def _require_postgres(test_db: AsyncSession) -> None:
    """Skip the test when the active engine is SQLite.

    These tests rely on PG-only features (search_tsv generated column,
    websearch_to_tsquery, the subjects join). SQLite would silently pass
    for the wrong reasons.
    """
    bind = test_db.bind
    if bind.dialect.name != "postgresql":
        pytest.skip("phrase search requires Postgres (search_tsv + websearch_to_tsquery)")


async def _make_item(
    test_db: AsyncSession,
    *,
    title: str,
    author: str = "Anon",
    isbn: str | None = None,
    series: str | None = None,
    description: str | None = None,
    subjects: list[str] | None = None,
) -> CatalogItem:
    """Insert one CatalogItem plus its normalized subject rows.

    Subjects are written through the join table so the parser's
    ``subject:`` predicate (EXISTS over CatalogItemSubject) can match.
    Returns the item with id populated.
    """
    item = CatalogItem(
        title=title,
        author=author,
        isbn=isbn,
        series_name=series,
        description=description,
        status=ItemStatus.available,
        item_type=ItemType.book,
        # Anonymous patron searches filter to CATALOGED only; default is
        # UNCATALOGED which would hide all fixture items.
        cataloging_status=CatalogingStatus.CATALOGED,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    for label in subjects or []:
        # Reuse Subject rows across items so the join carries the right
        # patron-facing label (the EXISTS predicate matches Subject.label).
        existing = await test_db.execute(
            select(Subject).where(Subject.label == label)
        )
        subj = existing.scalar_one_or_none()
        if subj is None:
            subj = Subject(label=label, slug=label.lower().replace(" ", "-"))
            test_db.add(subj)
            await test_db.commit()
            await test_db.refresh(subj)
        test_db.add(
            CatalogItemSubject(catalog_item_id=item.id, subject_id=subj.id)
        )
    await test_db.commit()
    return item


async def _search(test_db: AsyncSession, q: str) -> list[dict]:
    """Run the catalog search helper with patron defaults."""
    result = await _execute_catalog_search(test_db, q=q, per_page=50)
    return result["items"]


def _titles(items: list[dict]) -> set[str]:
    return {it["title"] for it in items}


# ---------------------------------------------------------------------------
# Bag-of-words still works (no regression to the existing path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bag_of_words_matches_title(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(test_db, title="To Kill a Mockingbird", author="Harper Lee")
    await _make_item(test_db, title="The Great Gatsby", author="F. Scott Fitzgerald")

    items = await _search(test_db, "mockingbird")

    assert "To Kill a Mockingbird" in _titles(items)
    assert "The Great Gatsby" not in _titles(items)


@pytest.mark.asyncio
async def test_bag_of_words_order_does_not_matter(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(test_db, title="To Kill a Mockingbird", author="Harper Lee")

    items = await _search(test_db, "mockingbird kill")

    assert "To Kill a Mockingbird" in _titles(items)


# ---------------------------------------------------------------------------
# Quoted phrase: words must appear in order (this is the new capability)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quoted_phrase_matches_consecutive_words(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(test_db, title="To Kill a Mockingbird", author="Harper Lee")

    items = await _search(test_db, '"to kill a mockingbird"')

    assert "To Kill a Mockingbird" in _titles(items)


@pytest.mark.asyncio
async def test_quoted_phrase_excludes_scattered_words(test_db: AsyncSession):
    """The key win of phrase search: scattered words must NOT match."""
    _require_postgres(test_db)
    # Two books, neither contains the phrase "ocean blue" -- but the
    # bag-of-words ``ocean blue`` would match both.
    await _make_item(
        test_db,
        title="The Blue Whale",
        description="A documentary about life in the ocean.",
    )
    await _make_item(
        test_db,
        title="Ocean Currents",
        description="The blue tint of deep water explained.",
    )
    # Control: an item that actually contains the consecutive phrase.
    await _make_item(
        test_db,
        title="Ocean Blue Adventures",
        description="Tales of the sea.",
    )

    items = await _search(test_db, '"ocean blue"')
    titles = _titles(items)

    assert "Ocean Blue Adventures" in titles
    assert "The Blue Whale" not in titles
    assert "Ocean Currents" not in titles


# ---------------------------------------------------------------------------
# Fielded search: title:, author:, subject:, series:
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_author_field_with_quoted_value(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(test_db, title="Teaching to Transgress", author="bell hooks")
    await _make_item(test_db, title="Outliers", author="Malcolm Gladwell")

    items = await _search(test_db, 'author:"bell hooks"')

    assert _titles(items) == {"Teaching to Transgress"}


@pytest.mark.asyncio
async def test_title_and_subject_fields_combined(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(
        test_db,
        title="Teaching to Transgress",
        author="bell hooks",
        subjects=["Pedagogy", "Education"],
    )
    await _make_item(
        test_db,
        title="Teaching Math",
        author="Other",
        subjects=["Mathematics"],
    )
    await _make_item(
        test_db,
        title="Critical Pedagogy",
        author="Paulo Freire",
        subjects=["Pedagogy"],
    )

    items = await _search(test_db, "title:teaching subject:pedagogy")

    # Both fields must match (AND) -- "Teaching to Transgress" qualifies.
    titles = _titles(items)
    assert "Teaching to Transgress" in titles
    assert "Teaching Math" not in titles  # subject mismatch
    assert "Critical Pedagogy" not in titles  # title mismatch


@pytest.mark.asyncio
async def test_series_field(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(test_db, title="Dune", series="Dune Chronicles")
    await _make_item(test_db, title="Hyperion", series="Hyperion Cantos")

    items = await _search(test_db, "series:dune")

    assert _titles(items) == {"Dune"}


# ---------------------------------------------------------------------------
# ISBN routing: bare and explicit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bare_isbn13_finds_by_isbn(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(
        test_db,
        title="To Kill a Mockingbird",
        author="Harper Lee",
        isbn="9780446310789",
    )
    await _make_item(test_db, title="Outliers", author="Gladwell", isbn="9780316017930")

    items = await _search(test_db, "9780446310789")

    assert _titles(items) == {"To Kill a Mockingbird"}


@pytest.mark.asyncio
async def test_explicit_isbn_field_finds_by_isbn(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(test_db, title="Mockingbird", author="Lee", isbn="0446310786")
    await _make_item(test_db, title="Outliers", author="Gladwell", isbn="0316017930")

    items = await _search(test_db, "isbn:0446310786")

    assert _titles(items) == {"Mockingbird"}


@pytest.mark.asyncio
async def test_hyphenated_isbn_normalizes(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(
        test_db, title="Mockingbird", author="Lee", isbn="9780446310789"
    )

    items = await _search(test_db, "978-0-446-31078-9")

    assert _titles(items) == {"Mockingbird"}


# ---------------------------------------------------------------------------
# websearch_to_tsquery operators flow through unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_negation_excludes_term(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(
        test_db, title="Dracula", author="Stoker", description="A vampire novel."
    )
    await _make_item(
        test_db, title="Dracula's Guest", author="Stoker", description="Ghost story."
    )

    items = await _search(test_db, "-vampire dracula")
    titles = _titles(items)

    assert "Dracula's Guest" in titles
    assert "Dracula" not in titles


@pytest.mark.asyncio
async def test_or_operator_matches_either(test_db: AsyncSession):
    _require_postgres(test_db)
    await _make_item(test_db, title="Science Today", description="An overview.")
    await _make_item(test_db, title="Fiction Anthology", description="Stories.")
    await _make_item(test_db, title="Cookbook", description="Recipes.")

    items = await _search(test_db, "science OR fiction")
    titles = _titles(items)

    assert "Science Today" in titles
    assert "Fiction Anthology" in titles
    assert "Cookbook" not in titles


# ---------------------------------------------------------------------------
# Stopword detection path is preserved (PR #605)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_stopword_query_still_sets_flag(test_db: AsyncSession):
    """The pre-existing stopword detection path must not regress.

    Patrons typing ``the`` get the browse list + a flag the UI can use
    to explain why. The parser is bypassed for this case.
    """
    _require_postgres(test_db)
    await _make_item(test_db, title="Anything")

    result = await _execute_catalog_search(test_db, q="the", per_page=50)

    assert result["query_was_all_stopwords"] is True
    # And we don't filter to zero results.
    assert result["total"] >= 1
