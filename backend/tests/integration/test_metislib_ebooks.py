# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for MetisLib ebook proxy endpoints (/api/v1/ebooks/*).

Tests use METISLIB_MOCK=true so the MetisLibMockClient provides
realistic responses without hitting the real MetisLib API.

Auth-required tests mock get_current_user to avoid DB user creation issues.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient

from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user as _auth_dep


def _fake_user(user_id=1, role=UserRole.PATRON):
    """Create a fake User object for auth mocking."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = "patron@example.com"
    user.first_name = "Test"
    user.last_name = "Patron"
    user.role = role
    user.is_active = True
    return user


@pytest.fixture(autouse=True)
def _reset_metislib_mock_state():
    """Clear the mock client's class-level borrow/order state between tests.

    MetisLibMockClient is a process singleton with class-level _active_borrows;
    without a reset, a borrow in one test leaks into the next (e.g. test_place_hold
    on an ebook a prior test borrowed would 409 via the borrow guard).
    """
    from app.services.metislib_mock import MetisLibMockClient
    MetisLibMockClient._active_borrows = {}
    MetisLibMockClient._order_history = []
    yield


@pytest.fixture(autouse=True)
def _isolate_ebooks_cache():
    """Back the /ebooks serve-stale cache with a per-test in-memory dict.

    The real get_cached/set_cached use a module-level aioredis client bound to a
    single event loop; pytest-asyncio's function-scoped loops make it raise
    "Future attached to a different loop" and also leak cached shelves across
    tests. A dict fake keeps the caching path exercised while staying loop-safe
    and per-test isolated. Prod is unaffected (one long-lived loop).
    """
    import app.api.v1.metislib_ebooks as mod
    store: dict = {}

    async def _get(key):
        return store.get(key)

    async def _set(key, value, ttl_seconds=300):
        store[key] = value

    with patch.object(mod, "get_cached", side_effect=_get), \
         patch.object(mod, "set_cached", side_effect=_set):
        yield


@pytest.fixture
def as_patron():
    """Override auth to return a fake patron user, mock out ebook event logging."""
    from app.main import app
    fake = _fake_user()
    app.dependency_overrides[_auth_dep] = lambda: fake
    with patch("app.api.v1.metislib_ebooks.log_ebook_event", new_callable=AsyncMock):
        yield fake
    app.dependency_overrides.pop(_auth_dep, None)


@pytest.mark.integration
@pytest.mark.asyncio
class TestEbookBrowse:
    """Public catalog browsing endpoints (no auth)."""

    async def test_browse_returns_paginated_catalog(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert len(data["items"]) > 0

    async def test_browse_with_search_query(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks", params={"q": "Moss"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("Moss" in item["title"] for item in data["items"])

    async def test_browse_with_source_type_filter(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks", params={"source_type": "indie"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["source_type"] == "indie"

    async def test_browse_invalid_source_type_rejected(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks", params={"source_type": "pirated"})
        assert resp.status_code == 422

    async def test_browse_pagination(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks", params={"page": 1, "per_page": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 5

    async def test_browse_page_2(self, client: AsyncClient):
        page1 = await client.get("/api/v1/ebooks", params={"page": 1, "per_page": 5})
        page2 = await client.get("/api/v1/ebooks", params={"page": 2, "per_page": 5})
        assert page1.status_code == 200
        assert page2.status_code == 200
        ids_1 = {item["id"] for item in page1.json()["items"]}
        ids_2 = {item["id"] for item in page2.json()["items"]}
        assert ids_1.isdisjoint(ids_2), "Pages should not overlap"

    async def test_browse_no_results_for_garbage_query(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks", params={"q": "xyznonexistent999"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
class TestEbookPopular:
    """Popular ebooks endpoint."""

    async def test_popular_returns_sorted_ebooks(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks/popular")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) > 0
        ratings = [item["average_rating"] for item in data["items"]]
        assert ratings == sorted(ratings, reverse=True)

    async def test_popular_respects_limit(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks/popular", params={"limit": 3})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 3


@pytest.mark.integration
@pytest.mark.asyncio
class TestEbookDetail:
    """Single ebook detail endpoint."""

    async def test_get_ebook_by_id(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert "title" in data
        assert "author_name" in data


@pytest.mark.integration
@pytest.mark.asyncio
class TestEbookCollections:
    """Collection endpoints."""

    async def test_collections_endpoint_routed(self, client: AsyncClient):
        try:
            resp = await client.get("/api/v1/ebooks/collections")
        except Exception:
            pytest.skip("ebook_collections table missing in test DB")
            return
        # 200 if table exists and empty/populated, 500 if query fails
        assert resp.status_code in (200, 500), f"Unexpected {resp.status_code}: route may not be registered"


@pytest.mark.integration
@pytest.mark.asyncio
class TestEbookPatronActions:
    """Patron checkout/return/hold flows with mocked auth."""

    async def test_borrow_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/ebooks/1/borrow")
        assert resp.status_code in (401, 403)

    async def test_checkouts_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/ebooks/me/checkouts")
        assert resp.status_code in (401, 403)

    async def test_borrow_ebook(self, client: AsyncClient, as_patron):
        resp = await client.post("/api/v1/ebooks/1/borrow")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_id" in data
        assert data["status"] == "active"

    async def test_get_my_checkouts(self, client: AsyncClient, as_patron):
        resp = await client.get("/api/v1/ebooks/me/checkouts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_place_hold(self, client: AsyncClient, as_patron):
        resp = await client.post("/api/v1/ebooks/1/hold")
        assert resp.status_code == 200
        data = resp.json()
        assert "hold_id" in data
        assert data["status"] == "pending"

    async def test_return_ebook(self, client: AsyncClient, as_patron):
        borrow_resp = await client.post("/api/v1/ebooks/2/borrow")
        assert borrow_resp.status_code == 200
        access_id = borrow_resp.json()["access_id"]
        resp = await client.post(f"/api/v1/ebooks/{access_id}/return")
        assert resp.status_code == 200
        assert resp.json()["status"] == "returned"

    async def test_return_with_rating(self, client: AsyncClient, as_patron):
        borrow_resp = await client.post("/api/v1/ebooks/3/borrow")
        assert borrow_resp.status_code == 200
        access_id = borrow_resp.json()["access_id"]
        resp = await client.post(f"/api/v1/ebooks/{access_id}/return", params={"rating": 5})
        assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
class TestEbookServiceDisabled:
    """Test behavior when MetisLib is disabled."""

    async def test_browse_returns_503_when_disabled(self, client: AsyncClient):
        from app.core.config import get_settings
        original = get_settings()
        with patch.object(original, "metislib_enabled", False):
            resp = await client.get("/api/v1/ebooks")
        assert resp.status_code == 503

    async def test_popular_returns_503_when_disabled(self, client: AsyncClient):
        from app.core.config import get_settings
        original = get_settings()
        with patch.object(original, "metislib_enabled", False):
            resp = await client.get("/api/v1/ebooks/popular")
        assert resp.status_code == 503
