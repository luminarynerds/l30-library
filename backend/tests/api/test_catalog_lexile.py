# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API tests for Lexile reading-level fields on catalog endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_CACHE_PATCH_TARGETS = [
    "app.api.v1.catalog.crud.invalidate_catalog_cache",
    "app.api.v1.catalog.crud.invalidate_collection_reports",
    "app.api.v1.catalog.helpers.get_cached",
    "app.api.v1.catalog.helpers.set_cached",
]


def _no_cache():
    """Context manager: disable Redis cache calls for test isolation."""
    patches = [
        patch(t, new=AsyncMock(return_value=None))
        for t in _CACHE_PATCH_TARGETS
    ]
    # Also patch the BIBFRAME background tasks to prevent DB access on a
    # separate connection that lacks the test-session context.
    patches += [
        patch("app.api.v1.catalog.crud._sync_to_bibframe_background", new=AsyncMock()),
        patch("app.api.v1.catalog.crud._update_bibframe_background", new=AsyncMock()),
    ]
    import contextlib
    return contextlib.ExitStack


async def _with_mocks(coro):
    """Run a coroutine with cache + bibframe mocked out."""
    with (
        patch("app.api.v1.catalog.crud.invalidate_catalog_cache", new=AsyncMock(return_value=0)),
        patch("app.api.v1.catalog.crud.invalidate_collection_reports", new=AsyncMock(return_value=0)),
        patch("app.api.v1.catalog.helpers.get_cached", new=AsyncMock(return_value=None)),
        patch("app.api.v1.catalog.helpers.set_cached", new=AsyncMock(return_value=None)),
        patch("app.api.v1.catalog.crud.CatalogBibframeSync.create_from_catalog", new=AsyncMock()),
        patch("app.api.v1.catalog.crud.CatalogBibframeSync.update_from_catalog", new=AsyncMock()),
    ):
        return await coro


async def test_create_item_with_lexile_persists_both_columns(staff_client: AsyncClient):
    with (
        patch("app.api.v1.catalog.crud.invalidate_catalog_cache", new=AsyncMock(return_value=0)),
        patch("app.api.v1.catalog.crud.invalidate_collection_reports", new=AsyncMock(return_value=0)),
    ):
        payload = {"title": "Frog and Toad", "item_type": "book", "lexile_measure": "ad650l"}
        r = await staff_client.post("/api/v1/catalog/", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["lexile_measure"] == "AD650L"
    assert body["lexile_number"] == 650


async def test_create_item_with_invalid_lexile_returns_422(staff_client: AsyncClient):
    payload = {"title": "Bad", "item_type": "book", "lexile_measure": "L750"}
    r = await staff_client.post("/api/v1/catalog/", json=payload)
    assert r.status_code == 422


async def test_update_item_clears_lexile_when_null(staff_client, sample_book_with_lexile):
    with (
        patch("app.api.v1.catalog.crud.invalidate_catalog_cache", new=AsyncMock(return_value=0)),
        patch("app.api.v1.catalog.crud.invalidate_collection_reports", new=AsyncMock(return_value=0)),
        patch("app.api.v1.catalog.helpers.get_cached", new=AsyncMock(return_value=None)),
        patch("app.api.v1.catalog.helpers.set_cached", new=AsyncMock(return_value=None)),
    ):
        r = await staff_client.patch(
            f"/api/v1/catalog/{sample_book_with_lexile.id}",
            json={"lexile_measure": None},
        )
    assert r.status_code == 200, r.text
    assert r.json()["lexile_measure"] is None
    assert r.json()["lexile_number"] is None


async def test_search_filters_by_lexile_range(staff_client, books_across_lexile_range):
    with (
        patch("app.api.v1.catalog.helpers.get_cached", new=AsyncMock(return_value=None)),
        patch("app.api.v1.catalog.helpers.set_cached", new=AsyncMock(return_value=None)),
    ):
        r = await staff_client.get("/api/v1/catalog/search?min_lexile=400&max_lexile=700")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert all(it["lexile_number"] is not None for it in items)
    assert all(400 <= it["lexile_number"] <= 700 for it in items)
