# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the catalog search ?available_for_hold filter and the
CatalogItemResponse.available_for_hold computed field.

The signal is derived server-side from CatalogItem.status (no DB column);
mirrors schemas.catalog.NON_HOLDABLE_STATUSES.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)


@pytest.fixture
async def holdability_fixture_items(test_db: AsyncSession):
    """One item per holdability bucket, all otherwise publicly visible."""
    items = [
        # Holdable bucket
        CatalogItem(
            title='Holdable Available Title',
            author='A',
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
        CatalogItem(
            title='Holdable Checked Out Title',
            author='B',
            item_type=ItemType.book,
            status=ItemStatus.checked_out,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
        # Non-holdable bucket
        CatalogItem(
            title='Non Holdable Lost Title',
            author='C',
            item_type=ItemType.book,
            status=ItemStatus.lost,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
        CatalogItem(
            title='Non Holdable Reference Title',
            author='D',
            item_type=ItemType.book,
            status=ItemStatus.reference,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
        CatalogItem(
            title='Non Holdable Missing Title',
            author='E',
            item_type=ItemType.book,
            status=ItemStatus.missing,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
    ]
    for it in items:
        test_db.add(it)
    await test_db.commit()
    return items


def _titles(payload):
    return {row['title'] for row in payload['items']}


@pytest.mark.asyncio
class TestAvailableForHoldFilter:
    async def test_search_filter_available_for_hold_true_excludes_unholdable(
        self, client, holdability_fixture_items
    ):
        resp = await client.get('/api/v1/catalog/search?available_for_hold=true')
        assert resp.status_code == 200
        titles = _titles(resp.json())
        assert 'Holdable Available Title' in titles
        assert 'Holdable Checked Out Title' in titles
        assert 'Non Holdable Lost Title' not in titles
        assert 'Non Holdable Reference Title' not in titles
        assert 'Non Holdable Missing Title' not in titles

    async def test_search_filter_available_for_hold_false_excludes_holdable(
        self, client, holdability_fixture_items
    ):
        # Note: 'withdrawn' is filtered out for public users by visibility
        # rules, so we exercise 'lost' / 'reference' / 'missing' here.
        resp = await client.get('/api/v1/catalog/search?available_for_hold=false')
        assert resp.status_code == 200
        titles = _titles(resp.json())
        assert 'Holdable Available Title' not in titles
        assert 'Holdable Checked Out Title' not in titles
        assert 'Non Holdable Lost Title' in titles
        assert 'Non Holdable Reference Title' in titles
        assert 'Non Holdable Missing Title' in titles

    async def test_search_no_filter_returns_all(
        self, client, holdability_fixture_items
    ):
        resp = await client.get('/api/v1/catalog/search')
        assert resp.status_code == 200
        titles = _titles(resp.json())
        # All 5 fixture items are public + cataloged, so all visible.
        for t in (
            'Holdable Available Title',
            'Holdable Checked Out Title',
            'Non Holdable Lost Title',
            'Non Holdable Reference Title',
            'Non Holdable Missing Title',
        ):
            assert t in titles, f'missing {t} in {titles}'

    async def test_search_response_includes_available_for_hold(
        self, client, holdability_fixture_items
    ):
        resp = await client.get('/api/v1/catalog/search')
        assert resp.status_code == 200
        items = resp.json()['items']
        by_title = {row['title']: row for row in items}
        assert by_title['Holdable Available Title']['available_for_hold'] is True
        assert by_title['Holdable Checked Out Title']['available_for_hold'] is True
        assert by_title['Non Holdable Lost Title']['available_for_hold'] is False
        assert by_title['Non Holdable Reference Title']['available_for_hold'] is False
        assert by_title['Non Holdable Missing Title']['available_for_hold'] is False
