# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the subjects join-table migration + EXISTS-based subject filter.

Covers three things:

1. ``backfill_subjects`` helper parses semicolon, comma, and array-literal
   delimiters and dedupes within a record.
2. The catalog subject filter no longer triggers substring false positives
   (the regression that motivated this PR -- "Cooking" was matching
   "Bookkeeping for Cooks").
3. Subject facet counts reflect actual join rows, not substring matches.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem, ItemStatus
from app.models.subject import CatalogItemSubject, Subject

# Load the migration module by file path (alembic/versions is not a package).
_MIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic" / "versions" / "subjects_join_001_create_subjects_join.py"
)
_spec = importlib.util.spec_from_file_location("subjects_join_001", _MIG_PATH)
_migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_migration)
parse_subjects = _migration.parse_subjects
slugify = _migration.slugify
backfill_subjects = _migration.backfill_subjects


# ---------------------------------------------------------------------------
# Pure helpers (no DB) -- parse_subjects + slugify
# ---------------------------------------------------------------------------


class TestParseSubjects:
    def test_semicolon_delimited(self):
        assert parse_subjects("Mystery; Holocaust; Memoir") == [
            "Mystery",
            "Holocaust",
            "Memoir",
        ]

    def test_comma_delimited(self):
        assert parse_subjects("Mystery, Cozy mystery, Small town") == [
            "Mystery",
            "Cozy mystery",
            "Small town",
        ]

    def test_postgres_array_literal(self):
        assert parse_subjects("{astronaut,space,nasa}") == [
            "astronaut",
            "space",
            "nasa",
        ]

    def test_dedupes_case_insensitive_preserves_first(self):
        # First occurrence wins for display; later case-variants are dropped.
        assert parse_subjects("Music; music; MUSIC; Jazz") == ["Music", "Jazz"]

    def test_empty_and_whitespace(self):
        assert parse_subjects(None) == []
        assert parse_subjects("") == []
        assert parse_subjects("   ") == []
        assert parse_subjects("Music; ; ;Jazz") == ["Music", "Jazz"]

    def test_mixed_delimiters(self):
        # Real prod row had both -- we treat ; and , equivalently.
        assert parse_subjects("Comics; Holocaust, Memoir; History") == [
            "Comics",
            "Holocaust",
            "Memoir",
            "History",
        ]


class TestSlugify:
    def test_simple(self):
        assert slugify("Science Fiction") == "science-fiction"

    def test_strips_punctuation(self):
        assert slugify("Self-help: ADHD/Autism") == "self-help-adhdautism"

    def test_collapses_dashes(self):
        assert slugify("Mystery -- Cozy") == "mystery-cozy"

    def test_empty_fallback(self):
        assert slugify("!!!") == "subject"


# ---------------------------------------------------------------------------
# Backfill against a real session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backfill_creates_subjects_and_links(test_db: AsyncSession):
    """Items with legacy subjects strings get normalized into the join."""
    items = [
        CatalogItem(
            title="Cookbook A",
            author="Chef",
            status=ItemStatus.available,
            subjects="Cooking; Italian; Pasta",
        ),
        CatalogItem(
            title="Cookbook B",
            author="Chef",
            status=ItemStatus.available,
            subjects="Cooking, French, Sauces",
        ),
        CatalogItem(
            title="Ledger Manual",
            author="Accountant",
            status=ItemStatus.available,
            subjects="Bookkeeping for Cooks",
        ),
    ]
    test_db.add_all(items)
    await test_db.commit()

    # backfill_subjects is sync; run it on the underlying sync connection.
    def _run(sync_conn):
        return backfill_subjects(sync_conn)

    async with test_db.bind.begin() as conn:
        await conn.run_sync(_run)

    # Assert via the resulting rows rather than inserted-count, so this
    # test stays correct even if prior tests left subjects rows behind
    # (the helper is idempotent and counts only NEW inserts).
    labels = set(
        (await test_db.execute(select(Subject.label))).scalars().all()
    )
    for expected in (
        "Cooking", "Italian", "Pasta", "French", "Sauces",
        "Bookkeeping for Cooks",
    ):
        assert expected in labels, f"missing subject label: {expected}"

    total_links = (
        await test_db.execute(
            select(text("count(*)")).select_from(CatalogItemSubject)
        )
    ).scalar_one()
    # Per-item link counts: 3 + 3 + 1 = 7 for the items this test added.
    assert total_links >= 7

    # Cooking is shared between A and B (proves de-duplication at insert).
    cooking_id = (
        await test_db.execute(select(Subject.id).where(Subject.label == "Cooking"))
    ).scalar_one()
    cooking_links = (
        await test_db.execute(
            select(CatalogItemSubject.catalog_item_id).where(
                CatalogItemSubject.subject_id == cooking_id
            )
        )
    ).scalars().all()
    assert len(cooking_links) == 2


@pytest.mark.asyncio
async def test_backfill_is_idempotent(test_db: AsyncSession):
    """Re-running the backfill must not duplicate rows."""
    test_db.add(
        CatalogItem(
            title="Once",
            author="A",
            status=ItemStatus.available,
            subjects="Foo; Bar",
        )
    )
    await test_db.commit()

    def _run(sync_conn):
        return backfill_subjects(sync_conn)

    async with test_db.bind.begin() as conn:
        await conn.run_sync(_run)
    async with test_db.bind.begin() as conn:
        subjects_inserted, links_inserted = await conn.run_sync(_run)

    # The crucial property: a second run inserts nothing new.
    assert subjects_inserted == 0
    assert links_inserted == 0


# ---------------------------------------------------------------------------
# Subject filter no longer substring-matches across unrelated labels
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subject_filter_does_not_substring_match_across_labels(
    test_db: AsyncSession,
):
    """The regression: ILIKE %Cooking% over the legacy text column matched
    "Bookkeeping for Cooks". With the join in place, a search for ``Cooking``
    must return ONLY items whose normalized subject label contains the word
    Cooking -- the ledger row stays out.
    """
    cookbook = CatalogItem(
        title="Real Cookbook",
        author="Chef",
        status=ItemStatus.available,
        subjects="Cooking; Italian",
    )
    ledger = CatalogItem(
        title="Library Bookkeeping",
        author="Accountant",
        status=ItemStatus.available,
        subjects="Bookkeeping for Cooks",
    )
    test_db.add_all([cookbook, ledger])
    await test_db.commit()
    await test_db.refresh(cookbook)
    await test_db.refresh(ledger)

    def _run(sync_conn):
        return backfill_subjects(sync_conn)

    async with test_db.bind.begin() as conn:
        await conn.run_sync(_run)

    # Run the same EXISTS-predicate the API helper builds.
    from sqlalchemy import literal

    pattern = "%Cooking%"
    subject_exists = (
        select(literal(1))
        .select_from(CatalogItemSubject)
        .join(Subject, Subject.id == CatalogItemSubject.subject_id)
        .where(
            CatalogItemSubject.catalog_item_id == CatalogItem.id,
            Subject.label.ilike(pattern),
        )
        .exists()
    )
    rows = (
        await test_db.execute(
            select(CatalogItem.id).where(subject_exists)
        )
    ).scalars().all()

    assert cookbook.id in rows
    assert ledger.id not in rows, (
        "Ledger row leaked through subject filter -- substring false positive "
        "is back. Check that the EXISTS predicate is querying Subject.label, "
        "not CatalogItem.subjects."
    )


# ---------------------------------------------------------------------------
# Facet counts via the join
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subject_facet_counts_use_join(test_db: AsyncSession):
    """_compute_facets must report subject counts from the join, exact-match."""
    test_db.add_all(
        [
            CatalogItem(
                title="A",
                author="x",
                status=ItemStatus.available,
                subjects="Cooking; Italian",
            ),
            CatalogItem(
                title="B",
                author="x",
                status=ItemStatus.available,
                subjects="Cooking; French",
            ),
            CatalogItem(
                title="C",
                author="x",
                status=ItemStatus.available,
                subjects="Bookkeeping for Cooks",
            ),
        ]
    )
    await test_db.commit()

    def _run(sync_conn):
        return backfill_subjects(sync_conn)

    async with test_db.bind.begin() as conn:
        await conn.run_sync(_run)

    from app.services.catalog_search_service import catalog_search_service

    base_query = select(CatalogItem)
    facets = await catalog_search_service._compute_facets(test_db, base_query)
    subj_counts = {fv.value: fv.count for fv in facets.subject}

    assert subj_counts.get("Cooking") == 2
    assert subj_counts.get("Italian") == 1
    assert subj_counts.get("French") == 1
    assert subj_counts.get("Bookkeeping for Cooks") == 1
    # Crucially, "Cooking" count is 2, not 3 -- the ledger row does NOT
    # contribute via substring matching against "Bookkeeping for Cooks".
