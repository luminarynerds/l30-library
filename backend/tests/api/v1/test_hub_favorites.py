# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for /api/v1/hub-favorites.

Covers:
* GET returns empty when user has no favorites
* POST adds a favorite (idempotent on duplicate POST)
* DELETE is idempotent (no 404 on missing favorite)
* hub_slug filter restricts the list
* Auth required (401 without credentials)
* User isolation (user A cannot see user B's favorites)

Uses real PostgreSQL via the project conftest (no mocks per project policy).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole


# ---------- Local fixtures ----------


@pytest.fixture
async def patron_a(test_db: AsyncSession) -> User:
    user = User(
        email="patronA@hubfav.test",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Patron",
        last_name="A",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_b(test_db: AsyncSession) -> User:
    user = User(
        email="patronB@hubfav.test",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Patron",
        last_name="B",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_a_client(test_db: AsyncSession, patron_a: User) -> AsyncClient:
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return patron_a

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def patron_b_client(test_db: AsyncSession, patron_b: User) -> AsyncClient:
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return patron_b

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


# ---------- Tests ----------


@pytest.mark.asyncio
async def test_get_hub_favorites_empty(patron_a_client: AsyncClient):
    resp = await patron_a_client.get("/api/v1/hub-favorites")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_post_hub_favorite_adds(patron_a_client: AsyncClient):
    payload = {"hub_slug": "report-hub", "item_path": "/staff/reports/circulation/overdues"}
    resp = await patron_a_client.post("/api/v1/hub-favorites", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["hub_slug"] == payload["hub_slug"]
    assert body["item_path"] == payload["item_path"]
    assert "id" in body and body["id"]
    assert "created_at" in body


@pytest.mark.asyncio
async def test_post_hub_favorite_duplicate_is_idempotent(patron_a_client: AsyncClient):
    payload = {"hub_slug": "report-hub", "item_path": "/staff/reports/circulation/overdues"}
    first = await patron_a_client.post("/api/v1/hub-favorites", json=payload)
    assert first.status_code == 200

    second = await patron_a_client.post("/api/v1/hub-favorites", json=payload)
    assert second.status_code == 200
    # Same id -- duplicate add returned the existing row, did not create a new one.
    assert second.json()["id"] == first.json()["id"]

    listing = await patron_a_client.get("/api/v1/hub-favorites")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_delete_missing_favorite_is_idempotent(patron_a_client: AsyncClient):
    payload = {"hub_slug": "report-hub", "item_path": "/never/added"}
    resp = await patron_a_client.request(
        "DELETE", "/api/v1/hub-favorites", json=payload
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_existing_favorite_removes(patron_a_client: AsyncClient):
    payload = {"hub_slug": "library-hub", "item_path": "/staff/library/branches"}
    await patron_a_client.post("/api/v1/hub-favorites", json=payload)

    listing = await patron_a_client.get("/api/v1/hub-favorites")
    assert len(listing.json()) == 1

    resp = await patron_a_client.request(
        "DELETE", "/api/v1/hub-favorites", json=payload
    )
    assert resp.status_code == 204

    listing = await patron_a_client.get("/api/v1/hub-favorites")
    assert listing.json() == []


@pytest.mark.asyncio
async def test_filter_by_hub_slug(patron_a_client: AsyncClient):
    await patron_a_client.post(
        "/api/v1/hub-favorites",
        json={"hub_slug": "report-hub", "item_path": "/staff/reports/a"},
    )
    await patron_a_client.post(
        "/api/v1/hub-favorites",
        json={"hub_slug": "report-hub", "item_path": "/staff/reports/b"},
    )
    await patron_a_client.post(
        "/api/v1/hub-favorites",
        json={"hub_slug": "library-hub", "item_path": "/staff/library/c"},
    )

    report_only = await patron_a_client.get(
        "/api/v1/hub-favorites", params={"hub_slug": "report-hub"}
    )
    assert report_only.status_code == 200
    assert {f["item_path"] for f in report_only.json()} == {
        "/staff/reports/a",
        "/staff/reports/b",
    }

    all_favs = await patron_a_client.get("/api/v1/hub-favorites")
    assert len(all_favs.json()) == 3


@pytest.mark.asyncio
async def test_auth_required(test_db: AsyncSession):
    """Without a current user, the endpoint should refuse the request."""
    from app.main import app
    from app.core.database import get_db

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/hub-favorites")
            assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_user_isolation(
    test_db: AsyncSession, patron_a: User, patron_b: User
):
    """Patron A and patron B should not see each other's favorites.

    Uses inline dep-overrides one user at a time because the two-client
    fixture pattern races on the shared app.dependency_overrides dict.
    """
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.state.setup_complete = True
    transport = ASGITransport(app=app)

    try:
        # Patron A: add one favorite, confirm visible.
        app.dependency_overrides[get_current_user] = lambda: patron_a
        async with AsyncClient(transport=transport, base_url="http://test") as a_client:
            await a_client.post(
                "/api/v1/hub-favorites",
                json={"hub_slug": "report-hub", "item_path": "/A/secret"},
            )
            a_favs = await a_client.get("/api/v1/hub-favorites")
            assert len(a_favs.json()) == 1

        # Patron B: should see none of patron A's favorites.
        app.dependency_overrides[get_current_user] = lambda: patron_b
        async with AsyncClient(transport=transport, base_url="http://test") as b_client:
            b_favs = await b_client.get("/api/v1/hub-favorites")
            assert b_favs.json() == []
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
