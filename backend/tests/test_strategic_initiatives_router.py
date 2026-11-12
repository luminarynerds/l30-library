# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""HTTP-level tests for strategic initiatives endpoints."""

import pytest
from datetime import datetime

from app.models.strategic import StrategicPlan


# ============ Fixtures ============


@pytest.fixture
async def _initiative_staff_user(test_db):
    """A dedicated staff user for initiative tests (unique email, no collision risk)."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="initiative_staff_tester@l30.test",
        password_hash=hash_password("password123"),
        first_name="Init",
        last_name="Tester",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def _initiative_admin_user(test_db):
    """A dedicated admin user for initiative tests."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="initiative_admin_tester@l30.test",
        password_hash=hash_password("password123"),
        first_name="Init",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def initiative_staff_client(test_db, _initiative_staff_user):
    """Async HTTP client authenticated as a staff user (initiative tests)."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return _initiative_staff_user

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
async def initiative_admin_client(test_db, _initiative_admin_user):
    """Async HTTP client authenticated as an admin user (initiative tests)."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return _initiative_admin_user

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
async def test_plan(test_db):
    plan = StrategicPlan(
        title="Test Plan for Initiatives",
        description="Plan used by initiative router tests",
        period_start=datetime(2025, 1, 1),
        period_end=datetime(2028, 12, 31),
        status="active",
    )
    test_db.add(plan)
    await test_db.commit()
    await test_db.refresh(plan)
    return plan


# ============ Tests ============


@pytest.mark.asyncio
async def test_create_initiative_201_and_appears_in_list(initiative_staff_client, test_plan):
    """POST creates initiative (201) and GET list returns it."""
    payload = {
        "title": "Digital Literacy Initiative",
        "description": "Expand digital access",
        "status": "planning",
        "priority": 2,
    }
    create_resp = await initiative_staff_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/initiatives",
        json=payload,
    )
    assert create_resp.status_code == 201, create_resp.text
    data = create_resp.json()
    assert data["title"] == "Digital Literacy Initiative"
    assert data["plan_id"] == test_plan.id
    assert data["status"] == "planning"

    list_resp = await initiative_staff_client.get(
        f"/api/v1/strategic/plans/{test_plan.id}/initiatives"
    )
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()
    assert any(i["id"] == data["id"] for i in items)


@pytest.mark.asyncio
async def test_create_initiative_missing_plan_404(initiative_staff_client):
    """POST to nonexistent plan returns 404."""
    payload = {"title": "Orphan Initiative", "status": "planning"}
    resp = await initiative_staff_client.post(
        "/api/v1/strategic/plans/999999/initiatives",
        json=payload,
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_create_milestone_and_complete(initiative_staff_client, test_plan):
    """POST milestone 201, then complete it."""
    # Create initiative first
    init_resp = await initiative_staff_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/initiatives",
        json={"title": "Milestone Parent", "status": "in_progress"},
    )
    assert init_resp.status_code == 201
    initiative_id = init_resp.json()["id"]

    # Add milestone
    ms_resp = await initiative_staff_client.post(
        f"/api/v1/strategic/initiatives/{initiative_id}/milestones",
        json={"title": "First Deliverable", "deliverables": ["Report"]},
    )
    assert ms_resp.status_code == 201, ms_resp.text
    ms_data = ms_resp.json()
    assert ms_data["title"] == "First Deliverable"
    assert ms_data["completed"] is False

    # Complete milestone without notes (backward-compat)
    complete_resp = await initiative_staff_client.post(
        f"/api/v1/strategic/milestones/{ms_data['id']}/complete",
    )
    assert complete_resp.status_code == 200, complete_resp.text
    completed = complete_resp.json()
    assert completed["completed"] is True
    assert completed["completion_date"] is not None

    # Add a second milestone and complete it with notes
    ms2_resp = await initiative_staff_client.post(
        f"/api/v1/strategic/initiatives/{initiative_id}/milestones",
        json={"title": "Second Deliverable"},
    )
    assert ms2_resp.status_code == 201, ms2_resp.text
    ms2_id = ms2_resp.json()["id"]

    complete2_resp = await initiative_staff_client.post(
        f"/api/v1/strategic/milestones/{ms2_id}/complete",
        json={"completion_notes": "Wrapped up ahead of schedule"},
    )
    assert complete2_resp.status_code == 200, complete2_resp.text
    completed2 = complete2_resp.json()
    assert completed2["completed"] is True
    assert completed2["completion_notes"] == "Wrapped up ahead of schedule"


@pytest.mark.asyncio
async def test_board_decision_approval_flips_board_approved(initiative_staff_client, test_plan):
    """Linking an approval decision sets board_approved on the initiative."""
    init_resp = await initiative_staff_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/initiatives",
        json={"title": "Board Approval Test", "status": "planning"},
    )
    assert init_resp.status_code == 201
    initiative_id = init_resp.json()["id"]

    decision_payload = {
        "meeting_date": "2025-03-15T00:00:00Z",
        "decision_type": "approval",
        "meeting_reference": "Board Meeting March 2025",
        "vote_result": "Unanimous",
    }
    bd_resp = await initiative_staff_client.post(
        f"/api/v1/strategic/initiatives/{initiative_id}/board-decisions",
        json=decision_payload,
    )
    assert bd_resp.status_code == 201, bd_resp.text
    assert bd_resp.json()["decision_type"] == "approval"

    # Verify initiative now shows board_approved in list
    list_resp = await initiative_staff_client.get(
        f"/api/v1/strategic/plans/{test_plan.id}/initiatives"
    )
    assert list_resp.status_code == 200
    initiative = next(i for i in list_resp.json() if i["id"] == initiative_id)
    assert initiative["board_approved"] is True


@pytest.mark.asyncio
async def test_delete_initiative_as_admin_204(initiative_admin_client, test_plan):
    """Admin DELETE returns 204 and initiative is gone."""
    create_resp = await initiative_admin_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/initiatives",
        json={"title": "To Be Deleted", "status": "cancelled"},
    )
    assert create_resp.status_code == 201
    initiative_id = create_resp.json()["id"]

    del_resp = await initiative_admin_client.delete(
        f"/api/v1/strategic/initiatives/{initiative_id}"
    )
    assert del_resp.status_code == 204, del_resp.text

    list_resp = await initiative_admin_client.get(
        f"/api/v1/strategic/plans/{test_plan.id}/initiatives"
    )
    assert list_resp.status_code == 200
    ids = [i["id"] for i in list_resp.json()]
    assert initiative_id not in ids


@pytest.mark.asyncio
async def test_list_serializes_seeded_object_team_members(initiative_staff_client, test_plan, test_db):
    """Prod seed rows store team_members as [{id,name,role}] objects, not bare ints.

    Regression: InitiativeResponse typed List[int] and 500d on every seeded plan.
    """
    from app.models.strategic import StrategicInitiative

    seeded = StrategicInitiative(
        plan_id=test_plan.id,
        title="Seeded-shape initiative",
        team_members=[{"id": 9, "name": "Rachel Kim", "role": "Technical lead"}, 12],
    )
    test_db.add(seeded)
    await test_db.commit()

    resp = await initiative_staff_client.get(
        f"/api/v1/strategic/plans/{test_plan.id}/initiatives"
    )
    assert resp.status_code == 200, resp.text
    row = next(i for i in resp.json() if i["title"] == "Seeded-shape initiative")
    assert row["team_members"][0]["name"] == "Rachel Kim"
    assert row["team_members"][1] == 12
