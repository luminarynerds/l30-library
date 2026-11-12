# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.multi_branch import LibrarySystem
from app.models.user import User, UserRole

INVITE = "/api/v1/staff-invites"


def admin_headers(admin_user):
    """Override get_current_user to return admin_user; returns empty headers dict."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    return {}


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def library_system(db):
    sys = LibrarySystem(code="INV1", name="Invite Test Library")
    db.add(sys)
    await db.flush()
    await db.commit()
    await db.refresh(sys)
    return sys


@pytest.fixture
async def test_admin_with_org(test_admin, db, library_system):
    """Ensure test_admin has a home_library_system_id."""
    test_admin.home_library_system_id = library_system.id
    db.add(test_admin)
    await db.commit()
    await db.refresh(test_admin)
    return test_admin


@pytest.mark.asyncio
async def test_invite_creates_inactive_user_stamped_with_inviter_org(client, db, test_admin_with_org):
    body = {"email": "newstaff@x.org", "first_name": "New", "last_name": "Staff", "role": "staff"}
    with patch("app.api.v1.staff_invites.send_staff_invite_email", new=AsyncMock(return_value=True)):
        resp = await client.post(INVITE, json=body, headers=admin_headers(test_admin_with_org))
    assert resp.status_code == 201
    row = (await db.execute(select(User).where(User.email == "newstaff@x.org"))).scalar_one()
    assert row.is_active is False
    assert row.invite_token is not None
    assert row.home_library_system_id == test_admin_with_org.home_library_system_id


@pytest.mark.asyncio
async def test_invite_duplicate_email_409(client, test_admin_with_org):
    body = {"email": test_admin_with_org.email, "first_name": "Dup", "last_name": "E", "role": "staff"}
    with patch("app.api.v1.staff_invites.send_staff_invite_email", new=AsyncMock(return_value=True)):
        resp = await client.post(INVITE, json=body, headers=admin_headers(test_admin_with_org))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_invite_non_superadmin_cannot_invite_superadmin_403(client, test_admin_with_org):
    assert test_admin_with_org.role != UserRole.SUPER_ADMIN
    body = {"email": "sa@x.org", "first_name": "S", "last_name": "A", "role": "super_admin"}
    resp = await client.post(INVITE, json=body, headers=admin_headers(test_admin_with_org))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_invite_rejects_non_staff_role_422(client, test_admin_with_org):
    body = {"email": "p@x.org", "first_name": "P", "last_name": "Q", "role": "patron"}
    resp = await client.post(INVITE, json=body, headers=admin_headers(test_admin_with_org))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invite_succeeds_even_if_email_send_fails(client, db, test_admin_with_org):
    body = {"email": "evenif@x.org", "first_name": "E", "last_name": "F", "role": "staff"}
    with patch("app.api.v1.staff_invites.send_staff_invite_email", new=AsyncMock(side_effect=RuntimeError("smtp down"))):
        resp = await client.post(INVITE, json=body, headers=admin_headers(test_admin_with_org))
    assert resp.status_code == 201
    assert (await db.execute(select(User).where(User.email == "evenif@x.org"))).scalar_one_or_none() is not None
