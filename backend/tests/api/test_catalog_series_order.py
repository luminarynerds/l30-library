# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API tests for numeric series_position derivation + reading-order endpoint."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _cache_mocks():
    import contextlib

    stack = contextlib.ExitStack()
    for target in (
        "app.api.v1.catalog.crud.invalidate_catalog_cache",
        "app.api.v1.catalog.crud.invalidate_collection_reports",
        "app.api.v1.catalog.helpers.get_cached",
        "app.api.v1.catalog.helpers.set_cached",
        "app.api.v1.catalog.browse.get_cached",
        "app.api.v1.catalog.browse.set_cached",
    ):
        stack.enter_context(patch(target, new=AsyncMock(return_value=None)))
    stack.enter_context(
        patch("app.api.v1.catalog.crud._sync_to_bibframe_background", new=AsyncMock())
    )
    stack.enter_context(
        patch("app.api.v1.catalog.crud._update_bibframe_background", new=AsyncMock())
    )
    return stack


async def _create(client: AsyncClient, **fields) -> dict:
    payload = {"title": "Untitled", "item_type": "book", "cataloging_status": "cataloged"}
    payload.update(fields)
    with _cache_mocks():
        r = await client.post("/api/v1/catalog/", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_derives_series_position_from_freeform_number(staff_client):
    body = await _create(staff_client, title="Leviathan Wakes", series_name="The Expanse", series_number="Book 1")
    assert body["series_number"] == "Book 1"
    assert body["series_position"] == 1


async def test_create_leaves_position_null_when_unparseable(staff_client):
    body = await _create(staff_client, title="Omnibus", series_name="The Expanse", series_number="Omnibus")
    assert body["series_position"] is None


async def test_update_rederives_position_when_series_number_changes(staff_client):
    body = await _create(staff_client, title="X", series_name="S", series_number="1")
    assert body["series_position"] == 1
    with _cache_mocks():
        r = await staff_client.patch(
            f"/api/v1/catalog/{body['id']}", json={"series_number": "Vol. 4"}
        )
    assert r.status_code == 200, r.text
    assert r.json()["series_position"] == 4


async def test_update_clears_position_when_series_number_cleared(staff_client):
    body = await _create(staff_client, title="X", series_name="S", series_number="3")
    with _cache_mocks():
        r = await staff_client.patch(
            f"/api/v1/catalog/{body['id']}", json={"series_number": None}
        )
    assert r.status_code == 200, r.text
    assert r.json()["series_position"] is None


async def test_series_endpoint_orders_by_position_with_prev_next(staff_client):
    b1 = await _create(staff_client, title="Book One", series_name="Reading Order Test", series_number="1")
    b4 = await _create(staff_client, title="Book Four", series_name="Reading Order Test", series_number="4")
    b7 = await _create(staff_client, title="Book Seven", series_name="Reading Order Test", series_number="7")

    with _cache_mocks():
        r = await staff_client.get(f"/api/v1/catalog/{b4['id']}/series")
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["series_name"] == "Reading Order Test"
    assert data["total_held"] == 3
    assert data["current_position"] == 4
    # Sparse holdings: 4's neighbours are 1 and 7 by ordered position.
    assert data["prev_id"] == b1["id"]
    assert data["next_id"] == b7["id"]
    positions = [m["series_position"] for m in data["items"]]
    assert positions == [1, 4, 7]


async def test_series_endpoint_sorts_unparseable_last(staff_client):
    a = await _create(staff_client, title="A", series_name="NullsLast", series_number="2")
    b = await _create(staff_client, title="B", series_name="NullsLast", series_number="Special")  # null position
    with _cache_mocks():
        r = await staff_client.get(f"/api/v1/catalog/{a['id']}/series")
    data = r.json()
    ids = [m["id"] for m in data["items"]]
    # Parsed position 2 comes before the NULL-position member.
    assert ids.index(a["id"]) < ids.index(b["id"])
    # The current item (position 2) is first, so it has no prev and a next.
    assert data["prev_id"] is None
    assert data["next_id"] == b["id"]


async def test_series_endpoint_excludes_uncataloged_for_anon(client, staff_client):
    visible = await _create(staff_client, title="Visible", series_name="VisTest", series_number="1")
    # Sibling left uncataloged -- should be hidden from the public rail.
    await _create(
        staff_client,
        title="Hidden",
        series_name="VisTest",
        series_number="2",
        cataloging_status="uncataloged",
    )
    with _cache_mocks():
        r = await client.get(f"/api/v1/catalog/{visible['id']}/series")
    assert r.status_code == 200, r.text
    data = r.json()
    titles = [m["title"] for m in data["items"]]
    assert titles == ["Visible"]
    assert data["total_held"] == 1
    assert data["next_id"] is None
