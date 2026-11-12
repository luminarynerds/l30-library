# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The public catalog-matches list must only offer items the public can open.

/catalog/items/{id} 404s anything not CATALOGED for anonymous visitors
(api/v1/catalog/browse.py), and 404s non-PUBLIC items too. get_all_catalog_matches
filtered only on catalog_match_id IS NOT NULL, so the ban tracker rendered jacket
covers linking to items nobody could view: 38 of 40 in production.
"""

import pytest

from app.models.ban_tracker import BanReport, BanSource, BanType
from app.models.catalog import CatalogingStatus, CatalogItem, SensitivityLevel
from app.services.ban_tracker_service import BanTrackerService


async def _item(session, title, status, sensitivity=SensitivityLevel.PUBLIC):
    item = CatalogItem(
        title=title,
        author="Test Author",
        item_type="book",
        cataloging_status=status,
        sensitivity_level=sensitivity,
    )
    session.add(item)
    await session.flush()
    return item


async def _report(session, title, item):
    report = BanReport(
        title=title,
        author="Test Author",
        state="IA",
        source=BanSource.PEN_AMERICA,
        ban_type=BanType.BANNED,
        catalog_match_id=item.id,
    )
    session.add(report)
    await session.flush()
    return report


@pytest.mark.asyncio
async def test_uncataloged_match_is_not_offered_publicly(db_session):
    """The exact production bug: an uncataloged match becomes a dead link."""
    item = await _item(db_session, "Dead Link Book", CatalogingStatus.UNCATALOGED)
    await _report(db_session, "Dead Link Book", item)

    matches = await BanTrackerService.get_all_catalog_matches(db_session)

    assert all(m.catalog_match_id != item.id for m in matches)


@pytest.mark.asyncio
async def test_cataloged_match_is_offered(db_session):
    """Positive control: the filter must not swallow legitimate matches."""
    item = await _item(db_session, "Working Book", CatalogingStatus.CATALOGED)
    await _report(db_session, "Working Book", item)

    matches = await BanTrackerService.get_all_catalog_matches(db_session)

    assert any(m.catalog_match_id == item.id for m in matches)


@pytest.mark.asyncio
async def test_in_progress_match_is_not_offered(db_session):
    item = await _item(db_session, "Half Done Book", CatalogingStatus.IN_PROGRESS)
    await _report(db_session, "Half Done Book", item)

    matches = await BanTrackerService.get_all_catalog_matches(db_session)

    assert all(m.catalog_match_id != item.id for m in matches)


@pytest.mark.asyncio
async def test_non_public_sensitivity_is_not_offered(db_session):
    """Cataloged but CONFIDENTIAL still 404s for anonymous visitors."""
    item = await _item(
        db_session,
        "Confidential Book",
        CatalogingStatus.CATALOGED,
        SensitivityLevel.CONFIDENTIAL,
    )
    await _report(db_session, "Confidential Book", item)

    matches = await BanTrackerService.get_all_catalog_matches(db_session)

    assert all(m.catalog_match_id != item.id for m in matches)


@pytest.mark.asyncio
async def test_every_offered_match_resolves_to_a_public_item(db_session):
    """The property that actually matters: nothing offered can be a dead link."""
    good = await _item(db_session, "Public Book", CatalogingStatus.CATALOGED)
    bad = await _item(db_session, "Hidden Book", CatalogingStatus.UNCATALOGED)
    await _report(db_session, "Public Book", good)
    await _report(db_session, "Hidden Book", bad)

    matches = await BanTrackerService.get_all_catalog_matches(db_session)

    for m in matches:
        assert m.catalog_match is not None
        assert m.catalog_match.cataloging_status == CatalogingStatus.CATALOGED
        assert m.catalog_match.sensitivity_level == SensitivityLevel.PUBLIC
