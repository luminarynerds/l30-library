# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests for /admin/audit/privacy-changes role narrowing.

The endpoint returns surveillance-grade patron privacy history (resource,
old->new value, IP, timestamp) and was previously accessible to the broad
STAFF role - which in a small public library includes shelvers, pages,
and volunteer desk substitutes. This test locks in the narrowing to
ADMIN / SUPER_ADMIN / DIRECTOR.
"""

import pytest


async def _call_privacy_changes(user_override):
    """Hit GET /admin/audit/privacy-changes as the given user. Returns Response."""
    from httpx import AsyncClient, ASGITransport
    from app.api.v1.auth import get_current_user
    from app.main import app

    async def override_get_current_user():
        return user_override

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            return await ac.get("/api/v1/admin/audit/privacy-changes")
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_staff_role_forbidden_on_privacy_audit(test_db, test_staff):
    """A STAFF-role user must be 403 on patron-privacy audit logs."""
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await _call_privacy_changes(test_staff)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403, (
        f"STAFF must not read patron privacy audit; got {response.status_code}: "
        f"{response.text}"
    )


@pytest.mark.asyncio
async def test_admin_role_allowed_on_privacy_audit(test_db, test_admin):
    """An ADMIN-role user must be 200 on patron-privacy audit logs."""
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await _call_privacy_changes(test_admin)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200, (
        f"ADMIN must read patron privacy audit; got {response.status_code}: "
        f"{response.text}"
    )
