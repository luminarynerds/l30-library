# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public staff-picks endpoints must tolerate NULL user FKs.

created_by_id (list) and added_by_id (item) are nullable FKs with
ondelete=SET NULL. If the creator/adder account is deleted the value goes
NULL; the public picks page must not 500 on that.
"""

import pytest
from httpx import AsyncClient

from app.models.catalog import CatalogItem
from app.models.staff_picks import StaffPicksList, StaffPicksItem


@pytest.mark.asyncio
async def test_public_lists_tolerates_null_created_by(client: AsyncClient, test_db):
    picks = StaffPicksList(title="Orphaned List", is_active=True, display_order=0, created_by_id=None)
    test_db.add(picks)
    await test_db.commit()
    await test_db.refresh(picks)

    resp = await client.get("/api/v1/staff/picks/public/lists?limit=10")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["id"] == picks.id)
    assert row["created_by_id"] is None


@pytest.mark.asyncio
async def test_public_detail_tolerates_null_user_fks(client: AsyncClient, test_db):
    item = CatalogItem(title="Orphan Book", author="A", item_type="book")
    test_db.add(item)
    picks = StaffPicksList(title="Orphaned List", is_active=True, display_order=0, created_by_id=None)
    test_db.add(picks)
    await test_db.commit()
    await test_db.refresh(picks)
    await test_db.refresh(item)
    test_db.add(StaffPicksItem(list_id=picks.id, catalog_item_id=item.id, added_by_id=None))
    await test_db.commit()

    resp = await client.get(f"/api/v1/staff/picks/public/{picks.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created_by_id"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["added_by_id"] is None
