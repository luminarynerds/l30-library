# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Contract tests for the public RA-shelves discover endpoints."""

import pytest
from httpx import AsyncClient

from app.models.staff_shelves import ShelfAudience, StaffShelf
from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)


pytestmark = pytest.mark.asyncio


async def _mk_item(session, *, id_hint, title, item_type=None):
    ci = CatalogItem(
        title=title,
        item_type=item_type or ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        share_count=0,
        total_checkouts=0,
        is_large_print=False,
    )
    session.add(ci)
    await session.flush()
    return ci


async def _mk_shelf(session, **kw):
    shelf = StaffShelf(
        slug=kw["slug"],
        title=kw["title"],
        description=kw.get("description"),
        item_ids=kw.get("item_ids", []),
        audience=kw.get("audience"),
        is_active=kw.get("is_active", True),
        display_order=kw.get("display_order", 0),
    )
    session.add(shelf)
    await session.flush()
    return shelf


async def test_list_shelves_returns_active_in_display_order(client: AsyncClient, test_db):
    await _mk_shelf(test_db, slug="b-second", title="Second", display_order=20)
    await _mk_shelf(test_db, slug="a-first", title="First", display_order=10)
    await _mk_shelf(test_db, slug="z-hidden", title="Hidden", display_order=5, is_active=False)
    await test_db.commit()

    r = await client.get("/api/v1/discover/shelves")
    assert r.status_code == 200, r.text
    body = r.json()
    slugs = [s["slug"] for s in body]
    assert slugs == ["a-first", "b-second"]


async def test_list_shelves_audience_filter_includes_all(client: AsyncClient, test_db):
    await _mk_shelf(test_db, slug="k", title="Kids only", audience=ShelfAudience.kids, display_order=10)
    await _mk_shelf(test_db, slug="t", title="Teens only", audience=ShelfAudience.teens, display_order=20)
    await _mk_shelf(test_db, slug="a", title="All", audience=ShelfAudience.all, display_order=30)
    await test_db.commit()

    r = await client.get("/api/v1/discover/shelves?audience=kids")
    assert r.status_code == 200, r.text
    slugs = {s["slug"] for s in r.json()}
    assert slugs == {"k", "a"}


async def test_get_shelf_populates_items_in_order(client: AsyncClient, test_db):
    a = await _mk_item(test_db, id_hint=1, title="Alpha")
    b = await _mk_item(test_db, id_hint=2, title="Beta")
    c = await _mk_item(test_db, id_hint=3, title="Gamma")
    await _mk_shelf(
        test_db,
        slug="cozy-mysteries",
        title="Cozy mysteries",
        description="small-town sleuths",
        item_ids=[c.id, a.id, b.id],
        audience=ShelfAudience.adults,
    )
    await test_db.commit()

    r = await client.get("/api/v1/discover/shelves/cozy-mysteries")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == "cozy-mysteries"
    assert body["title"] == "Cozy mysteries"
    assert body["item_count"] == 3
    titles = [item["title"] for item in body["items"]]
    assert titles == ["Gamma", "Alpha", "Beta"]


async def test_get_shelf_404_when_inactive(client: AsyncClient, test_db):
    await _mk_shelf(test_db, slug="hidden", title="Hidden", is_active=False)
    await test_db.commit()
    r = await client.get("/api/v1/discover/shelves/hidden")
    assert r.status_code == 404


async def test_get_shelf_404_when_missing(client: AsyncClient):
    r = await client.get("/api/v1/discover/shelves/nope-not-here")
    assert r.status_code == 404


async def test_get_shelf_handles_stale_item_id(client: AsyncClient, test_db):
    a = await _mk_item(test_db, id_hint=1, title="Alpha")
    await _mk_shelf(
        test_db,
        slug="with-stale",
        title="Stale ref",
        item_ids=[a.id, 999999],
    )
    await test_db.commit()
    r = await client.get("/api/v1/discover/shelves/with-stale")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["item_count"] == 2
    assert [it["id"] for it in body["items"]] == [a.id]
