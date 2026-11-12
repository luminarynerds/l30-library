# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the catalog language facet + filter.

Coverage:
- Language facet counts come from the bibframe_works join, not from
  CatalogItem (which has no language column).
- Items without a BIBFRAME work, or with NULL language on the work, are
  *omitted* from the language facet so we don't surface a misleading
  bucket.
- The ``language=`` filter narrows results to the supplied codes.
- Multi-value language filter is OR-within-group.
- When a language filter is active the language facet still surfaces the
  OTHER languages (so the patron can re-explore) -- this is the
  "facet-minus-own-predicate" rule and is the failure mode the plan
  flagged as load-bearing.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bibframe import BibframeWork
from app.models.catalog import CatalogingStatus, CatalogItem, ItemStatus, ItemType
from app.services.catalog_search_service import catalog_search_service


async def _seed_items_with_languages(
    db: AsyncSession, codes: list[str | None]
) -> list[CatalogItem]:
    """Helper: create N catalog items each linked to a BIBFRAME work
    whose ``language`` is the matching entry from ``codes``.

    ``None`` in ``codes`` means: create a catalog item but no
    bibframe_works row (the "Unknown" case the facet should hide).
    """
    items: list[CatalogItem] = []
    for i, lang in enumerate(codes):
        item = CatalogItem(
            title=f"Title {i}",
            author="Author",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
        )
        db.add(item)
        items.append(item)
    await db.commit()
    for item in items:
        await db.refresh(item)
    for item, lang in zip(items, codes):
        if lang is None:
            continue
        db.add(
            BibframeWork(
                title=item.title,
                language=lang,
                catalog_item_id=item.id,
            )
        )
    await db.commit()
    return items


@pytest.mark.asyncio
async def test_language_facet_counts_match_join(test_db: AsyncSession):
    """3 English, 2 Spanish, 1 with no BIBFRAME work => 3 eng + 2 spa,
    no "unknown" bucket."""
    await _seed_items_with_languages(
        test_db,
        ["eng", "eng", "eng", "spa", "spa", None],
    )

    base_query = select(CatalogItem)
    facets = await catalog_search_service._compute_facets(test_db, base_query)
    lang_counts = {fv.value: fv.count for fv in facets.language}

    assert lang_counts.get("eng") == 3
    assert lang_counts.get("spa") == 2
    # The item without a BibframeWork must not surface as a fake bucket.
    assert "unknown" not in lang_counts
    assert None not in lang_counts


@pytest.mark.asyncio
async def test_language_filter_narrows_results(test_db: AsyncSession):
    """Passing ``language=['eng']`` returns only English items."""
    from app.api.v1.catalog.helpers import _execute_catalog_search

    items = await _seed_items_with_languages(
        test_db, ["eng", "eng", "spa", "fre"]
    )
    eng_ids = {items[0].id, items[1].id}

    result = await _execute_catalog_search(
        test_db, language=["eng"], per_page=50,
    )
    returned = {it["id"] for it in result["items"]}

    assert returned == eng_ids
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_language_filter_or_within_group(test_db: AsyncSession):
    """``language=['eng','spa']`` returns the union -- OR within group."""
    from app.api.v1.catalog.helpers import _execute_catalog_search

    items = await _seed_items_with_languages(
        test_db, ["eng", "eng", "spa", "fre"]
    )
    want = {items[0].id, items[1].id, items[2].id}

    result = await _execute_catalog_search(
        test_db, language=["eng", "spa"], per_page=50,
    )
    returned = {it["id"] for it in result["items"]}

    assert returned == want
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_items_without_bibframe_visible_when_no_language_filter(
    test_db: AsyncSession,
):
    """An item without a BIBFRAME work must still appear in the unfiltered
    result set (it just won't appear under any language facet bucket)."""
    from app.api.v1.catalog.helpers import _execute_catalog_search

    items = await _seed_items_with_languages(test_db, ["eng", None])
    no_bibframe = items[1]

    result = await _execute_catalog_search(test_db, per_page=50)
    returned = {it["id"] for it in result["items"]}

    assert no_bibframe.id in returned
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_facet_still_shows_other_languages_when_language_filter_active(
    test_db: AsyncSession,
):
    """The load-bearing facet-correctness rule:

    Once a patron has selected ``eng``, the language facet should still
    surface ``spa`` and ``fre`` so they can switch -- otherwise the only
    way out is "Clear all filters", which is hostile. Equivalent to how
    ``item_type`` behaves today.
    """
    from app.api.v1.catalog.helpers import _execute_catalog_search

    await _seed_items_with_languages(
        test_db, ["eng", "eng", "spa", "fre"]
    )

    result = await _execute_catalog_search(
        test_db, language=["eng"], include_facets=True, per_page=50,
    )
    facets = result["facets"]
    assert facets is not None
    lang_counts = {fv["value"]: fv["count"] for fv in facets["language"]}

    # Filter is on eng, but spa and fre must still show in the facet.
    assert lang_counts.get("eng") == 2
    assert lang_counts.get("spa") == 1
    assert lang_counts.get("fre") == 1
