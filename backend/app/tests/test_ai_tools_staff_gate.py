# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""AI tool chat is staff-only while the program is in pilot.

Enforced with Depends(require_staff) so the gate lives in the framework layer
and cannot be switched off via a toggleable guardrail.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.api.v1.auth.helpers import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.user import User, UserRole


def _user(role):
    return User(
        email="gate-test@l30.org",
        first_name="Gate",
        last_name="Test",
        password_hash="x",
        role=role,
        is_active=True,
    )


@pytest.fixture
def _override_db(db):
    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.state.setup_complete = True
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


async def _post_chat():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.post(
            "/api/v1/ai-tools/cataloging_helper/chat",
            json={"message": "hello"},
        )


@pytest.mark.asyncio
async def test_patron_is_blocked(_override_db):
    async def _patron():
        return _user(UserRole.PATRON)

    app.dependency_overrides[get_current_user] = _patron
    resp = await _post_chat()
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_is_blocked(_override_db):
    # No auth override: the real require_staff -> get_current_user chain runs
    # and rejects an unauthenticated caller before any tool work.
    resp = await _post_chat()
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_staff_passes_the_gate(_override_db):
    # Staff clear the gate. With no such tool seeded they then hit 404, which
    # proves the gate let them through rather than blocking with 401/403.
    async def _staff():
        return _user(UserRole.STAFF)

    app.dependency_overrides[get_current_user] = _staff
    resp = await _post_chat()
    assert resp.status_code not in (401, 403)
