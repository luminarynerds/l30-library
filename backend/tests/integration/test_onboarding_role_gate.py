# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Role-gate regression for POST/PATCH /api/v1/onboarding.

Before this fix, `require_staff` allowed STAFF and LEGAL to create/update
staff onboarding records via direct API call even though the
StaffOnboardingPage UI hides the form from those roles. The backend is
now tightened to the same set the UI exposes: admin/director/super_admin.

Higher-privilege roles (super_admin) must keep working — see
feedback_l30_staff_catalog_uncataloged_superadmin_blind_spot.
"""

import uuid
from datetime import date, timedelta

import pytest

from app.models.user import User, UserRole


async def _make_user(test_db, role: UserRole) -> User:
    unique = uuid.uuid4().hex[:8]
    u = User(
        email=f"{role.value}-{unique}@onboarding-test.local",
        password_hash="x",
        first_name=role.value.title(),
        last_name="Tester",
        role=role,
        is_active=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


@pytest.fixture
async def onboarding_payload(test_db):
    """A target user for the onboarding record, plus a valid create payload."""
    target = await _make_user(test_db, UserRole.STAFF)
    start = date.today()
    return {
        "user_id": target.id,
        "department": "Circulation",
        "position": "Circulation Assistant",
        "start_date": start.isoformat(),
        "expected_completion_date": (start + timedelta(days=90)).isoformat(),
    }


@pytest.mark.integration
async def test_legal_cannot_create_onboarding(client, test_db, onboarding_payload):
    from app.api.v1.auth import get_current_user
    from app.main import app

    legal = await _make_user(test_db, UserRole.LEGAL)
    app.dependency_overrides[get_current_user] = lambda: legal
    try:
        resp = await client.post("/api/v1/onboarding", json=onboarding_payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 403, (
        f"LEGAL should not be able to create onboarding; got {resp.status_code} {resp.text}"
    )


@pytest.mark.integration
async def test_admin_can_create_onboarding(client, test_db, onboarding_payload):
    from app.api.v1.auth import get_current_user
    from app.main import app

    admin = await _make_user(test_db, UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        resp = await client.post("/api/v1/onboarding", json=onboarding_payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 201, (
        f"ADMIN should be able to create onboarding; got {resp.status_code} {resp.text}"
    )


@pytest.mark.integration
async def test_legal_cannot_patch_onboarding(client, test_db, onboarding_payload):
    """LEGAL must hit the role gate before the not-found check."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    legal = await _make_user(test_db, UserRole.LEGAL)
    app.dependency_overrides[get_current_user] = lambda: legal
    try:
        # Any path id — gate fires before the lookup.
        resp = await client.patch(
            "/api/v1/onboarding/1",
            json={"notes": "Should never write"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 403, (
        f"LEGAL should not be able to PATCH onboarding; got {resp.status_code} {resp.text}"
    )


@pytest.mark.integration
async def test_admin_can_patch_onboarding(client, test_db, onboarding_payload):
    """ADMIN creates a record, then PATCHes it — full round-trip."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    admin = await _make_user(test_db, UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        created = await client.post("/api/v1/onboarding", json=onboarding_payload)
        assert created.status_code == 201, created.text
        onboarding_id = created.json()["id"]

        resp = await client.patch(
            f"/api/v1/onboarding/{onboarding_id}",
            json={"notes": "Updated by admin"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, (
        f"ADMIN should be able to PATCH onboarding; got {resp.status_code} {resp.text}"
    )
