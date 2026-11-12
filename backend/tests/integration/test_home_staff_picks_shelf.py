# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The home 'staff_picks' shelf must aggregate staff-picks lists.

Before this change it filtered the orphaned CatalogItem.staff_pick flag
(no UI sets it), so the home shelf and /picks showed disjoint titles.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.catalog import CatalogingStatus, CatalogItem, SensitivityLevel
from app.models.home import HomeShelf, HomeShelfQueryKind
from app.models.staff_picks import StaffPicksItem, StaffPicksList
from app.services.home_page import resolve_home_page

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def _catalog_item(db, title, *, cataloged=True, staff_pick_flag=False):
    item = CatalogItem(
        title=title,
        author="Test Author",
        cataloging_status=(
            CatalogingStatus.CATALOGED if cataloged else CatalogingStatus.UNCATALOGED
        ),
        sensitivity_level=SensitivityLevel.PUBLIC,
        staff_pick=staff_pick_flag,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _picks_list(db, title, *, active=True):
    lst = StaffPicksList(title=title, is_active=active)
    db.add(lst)
    await db.commit()
    await db.refresh(lst)
    return lst


async def _add_to_list(db, lst, item, *, added_at):
    row = StaffPicksItem(
        list_id=lst.id, catalog_item_id=item.id, added_at=added_at
    )
    db.add(row)
    await db.commit()
    return row


@pytest.fixture
async def staff_picks_shelf(test_db):
    shelf = HomeShelf(
        slug="staff-picks",
        heading="Staff picks",
        description="Test shelf",
        query_kind=HomeShelfQueryKind.staff_picks,
        query_params={},
        max_items=6,
        sort_order=1,
        is_active=True,
    )
    test_db.add(shelf)
    await test_db.commit()
    return shelf


@pytest.mark.integration
class TestStaffPicksShelfAggregation:
    async def test_shelf_shows_active_list_items_newest_first_deduped(
        self, test_db, staff_picks_shelf
    ):
        oldest = await _catalog_item(test_db, "Oldest Pick")
        newest = await _catalog_item(test_db, "Newest Pick")
        shared = await _catalog_item(test_db, "Shared Pick")
        uncat = await _catalog_item(test_db, "Uncataloged Pick", cataloged=False)
        inactive_only = await _catalog_item(test_db, "Inactive List Pick")
        flagged = await _catalog_item(
            test_db, "Legacy Flagged Item", staff_pick_flag=True
        )

        list_a = await _picks_list(test_db, "Summer Picks")
        list_b = await _picks_list(test_db, "Camping Reads")
        list_off = await _picks_list(test_db, "Old List", active=False)

        await _add_to_list(test_db, list_a, oldest, added_at=T0)
        await _add_to_list(test_db, list_a, shared, added_at=T0 + timedelta(days=1))
        await _add_to_list(test_db, list_b, shared, added_at=T0 + timedelta(days=2))
        await _add_to_list(test_db, list_b, newest, added_at=T0 + timedelta(days=3))
        await _add_to_list(test_db, list_a, uncat, added_at=T0 + timedelta(days=4))
        await _add_to_list(test_db, list_off, inactive_only, added_at=T0 + timedelta(days=5))

        payload = await resolve_home_page(test_db, use_cache=False)
        shelves = {s.slug: s for s in payload.shelves}
        assert "staff-picks" in shelves, payload
        titles = [i.title for i in shelves["staff-picks"].items]

        # Newest-added first, deduped (shared appears once), uncataloged and
        # inactive-list items excluded, legacy flag ignored.
        assert titles == ["Newest Pick", "Shared Pick", "Oldest Pick"]
        assert "Legacy Flagged Item" not in titles

    async def test_shelf_hidden_when_no_active_lists(self, test_db, staff_picks_shelf):
        await _catalog_item(test_db, "Legacy Flagged Item", staff_pick_flag=True)
        payload = await resolve_home_page(test_db, use_cache=False)
        assert all(s.slug != "staff-picks" for s in payload.shelves)

    async def test_shelf_respects_max_items(self, test_db, staff_picks_shelf):
        lst = await _picks_list(test_db, "Big List")
        for n in range(8):  # shelf max_items is 6
            item = await _catalog_item(test_db, f"Pick {n}")
            await _add_to_list(test_db, lst, item, added_at=T0 + timedelta(days=n))
        payload = await resolve_home_page(test_db, use_cache=False)
        shelves = {s.slug: s for s in payload.shelves}
        assert len(shelves["staff-picks"].items) == 6
        assert shelves["staff-picks"].items[0].title == "Pick 7"
