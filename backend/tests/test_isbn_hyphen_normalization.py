# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression test: check_catalog_existence / lookup_single_isbn must match
hyphenated stored ISBNs.

Production stores ISBNs in mixed format -- some hyphenated
(e.g. "978-0-13-110412-9"), some not. Before the fix, the catalog
existence query stripped hyphens from the incoming ISBN but compared
against CatalogItem.isbn via literal .in_(), so hyphenated rows were
silently invisible to duplicate-purchase detection.
"""

import pytest

from app.api.v1.acquisition.external import check_catalog_existence
from app.models.catalog import CatalogItem


@pytest.mark.asyncio
async def test_check_catalog_existence_matches_hyphenated_isbn(db_session):
    """Hyphenated stored ISBN should match an unhyphenated lookup ISBN."""
    item = CatalogItem(
        title="Test Book For Hyphen Normalization",
        isbn="978-0-13-110412-9",
    )
    db_session.add(item)
    await db_session.flush()

    # Lookup with the unhyphenated form
    in_catalog, catalog_item_id = await check_catalog_existence(
        db_session, "9780131104129"
    )
    assert in_catalog is True
    assert catalog_item_id == item.id


@pytest.mark.asyncio
async def test_check_catalog_existence_matches_unhyphenated_isbn(db_session):
    """Unhyphenated stored ISBN should still match (no regression)."""
    item = CatalogItem(
        title="Test Book For Unhyphenated",
        isbn="9780062742469",
    )
    db_session.add(item)
    await db_session.flush()

    in_catalog, catalog_item_id = await check_catalog_existence(
        db_session, "9780062742469"
    )
    assert in_catalog is True
    assert catalog_item_id == item.id


@pytest.mark.asyncio
async def test_check_catalog_existence_hyphenated_lookup_matches_hyphenated_stored(
    db_session,
):
    """Hyphenated lookup ISBN must also match (normalize_isbn strips them first)."""
    item = CatalogItem(
        title="Test Book Both Hyphenated",
        isbn="978-0-13-110419-8",
    )
    db_session.add(item)
    await db_session.flush()

    in_catalog, catalog_item_id = await check_catalog_existence(
        db_session, "978-0-13-110419-8"
    )
    assert in_catalog is True
    assert catalog_item_id == item.id


@pytest.mark.asyncio
async def test_check_catalog_existence_returns_false_for_unknown(db_session):
    """Unknown ISBN must still return (False, None)."""
    in_catalog, catalog_item_id = await check_catalog_existence(
        db_session, "9999999999999"
    )
    assert in_catalog is False
    assert catalog_item_id is None
