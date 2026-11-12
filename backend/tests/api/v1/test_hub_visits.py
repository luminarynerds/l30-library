# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for /api/v1/hub-visits.

Covers:
* POST returns 204 and writes a row to user_hub_visits.
* Auth is required.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.user_hub import UserHubVisit


@pytest.fixture
async def patron(test_db: AsyncSession) -> User:
    user = User(
        email="patron@hubvisits.test",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Patron",
        last_name="Visits",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def auth_client(test_db: AsyncSession, patron: User) -> AsyncClient:
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return patron

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


@pytest.mark.asyncio
async def test_post_visit_returns_204(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/hub-visits",
        json={"hub_slug": "report-hub", "item_path": "/staff/reports/circulation"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_post_visit_writes_row(
    auth_client: AsyncClient, test_db: AsyncSession, patron: User
):
    resp = await auth_client.post(
        "/api/v1/hub-visits",
        json={"hub_slug": "library-hub", "item_path": "/staff/library/branches"},
    )
    assert resp.status_code == 204

    result = await test_db.execute(
        select(UserHubVisit).where(UserHubVisit.user_id == patron.id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].hub_slug == "library-hub"
    assert rows[0].item_path == "/staff/library/branches"
    assert rows[0].visited_at is not None


@pytest.mark.asyncio
async def test_post_visit_no_dedup(auth_client: AsyncClient, test_db: AsyncSession):
    payload = {"hub_slug": "report-hub", "item_path": "/staff/reports/x"}
    for _ in range(3):
        resp = await auth_client.post("/api/v1/hub-visits", json=payload)
        assert resp.status_code == 204

    result = await test_db.execute(select(UserHubVisit))
    assert len(result.scalars().all()) == 3


@pytest.mark.asyncio
async def test_auth_required(test_db: AsyncSession):
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/hub-visits",
                json={"hub_slug": "report-hub", "item_path": "/x"},
            )
            assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)


# ============================================================================
# GET /api/v1/hub-shortcuts/{hub_slug}
# ============================================================================


import asyncio
from datetime import datetime, timedelta, timezone


async def _make_visit(
    db: AsyncSession,
    *,
    user_id,
    hub_slug: str,
    item_path: str,
    visited_at: datetime,
) -> UserHubVisit:
    """Insert a visit with an explicit visited_at to avoid SQLite second-resolution ties."""
    visit = UserHubVisit(
        user_id=user_id,
        hub_slug=hub_slug,
        item_path=item_path,
        visited_at=visited_at,
    )
    db.add(visit)
    await db.commit()
    return visit


@pytest.mark.asyncio
async def test_shortcuts_empty_for_user_with_no_visits(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/hub-shortcuts/library-hub")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["hub_slug"] == "library-hub"
    assert payload["shortcuts"] == []


@pytest.mark.asyncio
async def test_shortcuts_returns_top_n_by_count(
    auth_client: AsyncClient, test_db: AsyncSession, patron: User
):
    now = datetime.now(timezone.utc)
    # /a: 3 visits, /b: 1, /c: 2, /d: 1
    paths_and_counts = {"/a": 3, "/b": 1, "/c": 2, "/d": 1}
    for path, count in paths_and_counts.items():
        for i in range(count):
            await _make_visit(
                test_db,
                user_id=patron.id,
                hub_slug="library-hub",
                item_path=path,
                visited_at=now - timedelta(hours=i + 1),
            )

    resp = await auth_client.get("/api/v1/hub-shortcuts/library-hub?limit=3")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["hub_slug"] == "library-hub"
    shortcuts = payload["shortcuts"]
    assert len(shortcuts) == 3
    # Top by count: /a (3), /c (2), then either /b or /d (1) by recency
    assert shortcuts[0]["item_path"] == "/a"
    assert shortcuts[0]["visit_count"] == 3
    assert shortcuts[1]["item_path"] == "/c"
    assert shortcuts[1]["visit_count"] == 2


@pytest.mark.asyncio
async def test_shortcuts_tie_break_by_recency(
    auth_client: AsyncClient, test_db: AsyncSession, patron: User
):
    now = datetime.now(timezone.utc)
    # Both have 1 visit -- /newer should sort first
    await _make_visit(
        test_db,
        user_id=patron.id,
        hub_slug="library-hub",
        item_path="/older",
        visited_at=now - timedelta(days=5),
    )
    await _make_visit(
        test_db,
        user_id=patron.id,
        hub_slug="library-hub",
        item_path="/newer",
        visited_at=now - timedelta(minutes=10),
    )

    resp = await auth_client.get("/api/v1/hub-shortcuts/library-hub")
    assert resp.status_code == 200
    shortcuts = resp.json()["shortcuts"]
    assert [s["item_path"] for s in shortcuts] == ["/newer", "/older"]


@pytest.mark.asyncio
async def test_shortcuts_14_day_window_excludes_older(
    auth_client: AsyncClient, test_db: AsyncSession, patron: User
):
    now = datetime.now(timezone.utc)
    # /old has 5 visits but ALL > 14 days ago; /recent has 1 visit in window
    for i in range(5):
        await _make_visit(
            test_db,
            user_id=patron.id,
            hub_slug="library-hub",
            item_path="/old",
            visited_at=now - timedelta(days=20 + i),
        )
    await _make_visit(
        test_db,
        user_id=patron.id,
        hub_slug="library-hub",
        item_path="/recent",
        visited_at=now - timedelta(days=1),
    )

    resp = await auth_client.get("/api/v1/hub-shortcuts/library-hub")
    assert resp.status_code == 200
    shortcuts = resp.json()["shortcuts"]
    paths = [s["item_path"] for s in shortcuts]
    assert "/old" not in paths
    assert paths == ["/recent"]


@pytest.mark.asyncio
async def test_shortcuts_auth_required(test_db: AsyncSession):
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/hub-shortcuts/library-hub")
            assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_shortcuts_user_isolation(
    auth_client: AsyncClient, test_db: AsyncSession, patron: User
):
    # Insert visits owned by a DIFFERENT user. They must not leak to `patron`.
    other = User(
        email="other@hubvisits.test",
        password_hash=hash_password("OtherPassword123!"),
        first_name="Other",
        last_name="User",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(other)
    await test_db.commit()
    await test_db.refresh(other)

    now = datetime.now(timezone.utc)
    for i in range(3):
        await _make_visit(
            test_db,
            user_id=other.id,
            hub_slug="library-hub",
            item_path="/other-only",
            visited_at=now - timedelta(hours=i + 1),
        )

    resp = await auth_client.get("/api/v1/hub-shortcuts/library-hub")
    assert resp.status_code == 200
    assert resp.json()["shortcuts"] == []


@pytest.mark.asyncio
async def test_shortcuts_filters_by_hub_slug(
    auth_client: AsyncClient, test_db: AsyncSession, patron: User
):
    now = datetime.now(timezone.utc)
    await _make_visit(
        test_db,
        user_id=patron.id,
        hub_slug="library-hub",
        item_path="/library-thing",
        visited_at=now - timedelta(minutes=5),
    )
    await _make_visit(
        test_db,
        user_id=patron.id,
        hub_slug="report-hub",
        item_path="/report-thing",
        visited_at=now - timedelta(minutes=5),
    )

    resp = await auth_client.get("/api/v1/hub-shortcuts/library-hub")
    paths = [s["item_path"] for s in resp.json()["shortcuts"]]
    assert paths == ["/library-thing"]

    resp = await auth_client.get("/api/v1/hub-shortcuts/report-hub")
    paths = [s["item_path"] for s in resp.json()["shortcuts"]]
    assert paths == ["/report-thing"]
