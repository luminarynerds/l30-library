# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests: staff-picks list endpoints must report a real items_count.

Both the public and staff list endpoints previously hardcoded items_count=0
in the response, so every collection reported 0 items even when populated.
"""

import pytest
from httpx import AsyncClient

from app.models.catalog import CatalogItem
from app.models.staff_picks import StaffPicksList, StaffPicksItem


async def _seed_list_with_items(
    test_db, *, title: str, n_items: int, created_by_id: int, display_order: int = 0
) -> int:
    items = [CatalogItem(title=f"{title} Book {i}", author="A", item_type="book") for i in range(n_items)]
    for it in items:
        test_db.add(it)
    picks = StaffPicksList(
        title=title, is_active=True, display_order=display_order, created_by_id=created_by_id
    )
    test_db.add(picks)
    await test_db.commit()
    await test_db.refresh(picks)
    for it in items:
        await test_db.refresh(it)
        test_db.add(StaffPicksItem(list_id=picks.id, catalog_item_id=it.id))
    await test_db.commit()
    return picks.id


@pytest.mark.asyncio
async def test_public_lists_items_count_reflects_actual_items(client: AsyncClient, test_db, test_staff):
    list_id = await _seed_list_with_items(
        test_db, title="Camping Reads", n_items=3, created_by_id=test_staff.id
    )

    resp = await client.get("/api/v1/staff/picks/public/lists?limit=10")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["id"] == list_id)
    assert row["items_count"] == 3, resp.text


@pytest.mark.asyncio
async def test_public_lists_items_count_zero_for_empty_list(client: AsyncClient, test_db, test_staff):
    picks = StaffPicksList(title="Empty", is_active=True, display_order=1, created_by_id=test_staff.id)
    test_db.add(picks)
    await test_db.commit()
    await test_db.refresh(picks)

    resp = await client.get("/api/v1/staff/picks/public/lists?limit=10")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["id"] == picks.id)
    assert row["items_count"] == 0, resp.text


@pytest.mark.asyncio
async def test_staff_lists_items_count_reflects_actual_items(staff_client: AsyncClient, test_db, test_staff):
    list_id = await _seed_list_with_items(
        test_db, title="Staff View", n_items=2, created_by_id=test_staff.id
    )

    resp = await staff_client.get("/api/v1/staff/picks?limit=10")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["id"] == list_id)
    assert row["items_count"] == 2, resp.text
