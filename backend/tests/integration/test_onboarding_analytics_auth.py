# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Auth gate regression for GET /api/v1/admin/onboarding/analytics.

Before the fix the endpoint had no auth dependency and returned 200 to
anonymous and patron-level callers, leaking aggregate funnel counts.
"""

import uuid

import pytest

from app.models.user import User, UserRole

ENDPOINT = "/api/v1/admin/onboarding/analytics"


async def _make_user(test_db, role: UserRole) -> User:
    u = User(
        email=f"{role.value}-{uuid.uuid4().hex[:8]}@analytics-gate-test.local",
        password_hash="x",
        first_name=role.value.title(),
        last_name="Tester",
        role=role,
        is_active=True,
        email_verified=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


@pytest.mark.integration
async def test_anon_gets_401_on_analytics(client):
    """No token at all must be rejected."""
    resp = await client.get(ENDPOINT)
    assert resp.status_code == 401, f"expected 401 anon, got {resp.status_code}: {resp.text}"


@pytest.mark.integration
async def test_patron_gets_403_on_analytics(client, test_db):
    """Authenticated patron must be forbidden (not admin)."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    patron = await _make_user(test_db, UserRole.PATRON)
    app.dependency_overrides[get_current_user] = lambda: patron
    try:
        resp = await client.get(ENDPOINT)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 403, (
        f"PATRON should be forbidden from analytics; got {resp.status_code}: {resp.text}"
    )


@pytest.mark.integration
async def test_staff_gets_403_on_analytics(client, test_db):
    """Plain staff (not admin) must also be forbidden."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, UserRole.STAFF)
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        resp = await client.get(ENDPOINT)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 403, (
        f"STAFF should be forbidden from analytics; got {resp.status_code}: {resp.text}"
    )


@pytest.mark.integration
async def test_admin_gets_200_on_analytics(client, test_db):
    """Admin must be able to reach the endpoint (empty data is fine)."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    admin = await _make_user(test_db, UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        resp = await client.get(ENDPOINT)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, (
        f"ADMIN should reach analytics; got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "total_started" in body
    assert "completion_rate" in body
    assert "drop_off_by_step" in body
