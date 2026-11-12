# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the one-off promotion of ban-matched items to CATALOGED."""

import pytest

from app.models.ban_tracker import BanReport, BanSource, BanType
from app.models.catalog import CatalogingStatus, CatalogItem, SensitivityLevel
from scripts.catalog_banned_matches import find_targets


async def _item(session, title, status, sensitivity=SensitivityLevel.PUBLIC):
    item = CatalogItem(
        title=title,
        author="A",
        item_type="book",
        cataloging_status=status,
        sensitivity_level=sensitivity,
    )
    session.add(item)
    await session.flush()
    return item


async def _match(session, item):
    session.add(
        BanReport(
            title=item.title,
            author="A",
            state="IA",
            source=BanSource.PEN_AMERICA,
            ban_type=BanType.BANNED,
            catalog_match_id=item.id,
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_targets_an_uncataloged_matched_item(db_session):
    item = await _item(db_session, "Matched Uncataloged", CatalogingStatus.UNCATALOGED)
    await _match(db_session, item)

    assert item.id in [t[0] for t in await find_targets(db_session)]


@pytest.mark.asyncio
async def test_ignores_an_uncataloged_item_no_ban_report_points_at(db_session):
    """Scope guard: this must not promote the whole catalog."""
    item = await _item(db_session, "Unmatched Uncataloged", CatalogingStatus.UNCATALOGED)

    assert item.id not in [t[0] for t in await find_targets(db_session)]


@pytest.mark.asyncio
async def test_ignores_an_already_cataloged_item(db_session):
    item = await _item(db_session, "Already Cataloged", CatalogingStatus.CATALOGED)
    await _match(db_session, item)

    assert item.id not in [t[0] for t in await find_targets(db_session)]


@pytest.mark.asyncio
async def test_targets_an_in_progress_matched_item(db_session):
    item = await _item(db_session, "In Progress", CatalogingStatus.IN_PROGRESS)
    await _match(db_session, item)

    assert item.id in [t[0] for t in await find_targets(db_session)]


@pytest.mark.asyncio
async def test_a_matched_item_appears_once_not_per_ban_report(db_session):
    """Several states banning one book must not queue it several times."""
    item = await _item(db_session, "Banned Widely", CatalogingStatus.UNCATALOGED)
    await _match(db_session, item)
    await _match(db_session, item)
    await _match(db_session, item)

    assert [t[0] for t in await find_targets(db_session)].count(item.id) == 1
