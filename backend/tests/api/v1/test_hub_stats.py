# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for /api/v1/hub-stats/{hub_slug}.

Covers:
* Known slugs return a list with the expected keys.
* Unknown slugs return empty stats (NOT 404 -- the frontend treats empty as
  \"no chips\").
* library-hub includes emergency_hubs_active + advocacy_awaiting_moderation
  counters when matching data exists.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.emergency_operations import CommunityResourceHub
from app.models.positivity import PositivityEntry
from app.models.user import User, UserRole


@pytest.fixture
async def patron(test_db: AsyncSession) -> User:
    user = User(
        email="patron@hubstats.test",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Patron",
        last_name="Stats",
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
async def test_known_slug_returns_list(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/hub-stats/front-desk-hub")
    assert resp.status_code == 200
    body = resp.json()
    assert body["hub_slug"] == "front-desk-hub"
    assert isinstance(body["stats"], list)
    keys = {s["key"] for s in body["stats"]}
    assert keys == {"holds_ready", "items_overdue", "panic_alerts_active"}
    for stat in body["stats"]:
        assert isinstance(stat["value"], int)
        assert stat["value"] >= 0
        assert isinstance(stat["label"], str)
        assert isinstance(stat["urgent"], bool)


@pytest.mark.asyncio
async def test_report_hub_returns_list(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/hub-stats/report-hub")
    assert resp.status_code == 200
    body = resp.json()
    assert body["hub_slug"] == "report-hub"
    keys = {s["key"] for s in body["stats"]}
    assert "scheduled_reports_overdue" in keys


@pytest.mark.asyncio
async def test_collection_hub_returns_list(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/hub-stats/collection-hub")
    assert resp.status_code == 200
    # Returns [] when feature flag is off; otherwise has items_in_processing.
    body = resp.json()
    assert isinstance(body["stats"], list)
    if body["stats"]:
        assert body["stats"][0]["key"] == "items_in_processing"


@pytest.mark.asyncio
async def test_library_hub_includes_emergency_and_advocacy(
    auth_client: AsyncClient, test_db: AsyncSession
):
    # Seed one active emergency hub.
    hub = CommunityResourceHub(
        hub_name="Test Hub Active",
        branch_id=1,
        location_description="Main floor",
        hub_purposes=["Charging station"],
        emergency_types=["Power outage"],
        max_capacity=50,
        is_active=True,
    )
    # Seed one pending advocacy story.
    story = PositivityEntry(
        organization_id=1,
        entry_type="story",
        text="A patron success story flagged for advocacy.",
        source="patron",
        flagged_for_advocacy=True,
        moderation_status="pending",
    )
    test_db.add_all([hub, story])
    await test_db.commit()

    resp = await auth_client.get("/api/v1/hub-stats/library-hub")
    assert resp.status_code == 200
    by_key = {s["key"]: s for s in resp.json()["stats"]}
    assert by_key["emergency_hubs_active"]["value"] >= 1
    assert by_key["advocacy_awaiting_moderation"]["value"] >= 1


@pytest.mark.asyncio
async def test_unknown_slug_returns_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/hub-stats/not-a-real-hub")
    # Must NOT 404 -- frontend treats empty as \"no chips.\"
    assert resp.status_code == 200
    body = resp.json()
    assert body["hub_slug"] == "not-a-real-hub"
    assert body["stats"] == []
