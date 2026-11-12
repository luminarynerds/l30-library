# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.user import User, UserRole
from app.core.security import hash_reset_token, hash_password

BASE = "/api/v1/staff-invites"


def admin_headers(admin_user):
    """Override get_current_user to return admin_user; returns empty headers dict."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    return {}


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


async def _pending(db, email):
    """Create a pending invite user (is_active=False, invite_token set)."""
    raw = secrets.token_urlsafe(32)
    u = User(
        email=email,
        first_name="Pending",
        last_name="User",
        role=UserRole.STAFF,
        is_active=False,
        email_verified=False,
    )
    setattr(u, "password_hash", hash_password(secrets.token_urlsafe(32)))
    db.add(u)
    await db.flush()
    setattr(u, "invite_token", hash_reset_token(raw))
    setattr(u, "invite_token_expires", datetime.now(timezone.utc) + timedelta(hours=72))
    await db.flush()
    await db.commit()
    await db.refresh(u)
    return u


@pytest.mark.asyncio
async def test_resend_rotates_token_and_returns_200(client, db, test_admin):
    u = await _pending(db, "r@x.org")
    old_hash = u.invite_token
    with patch("app.api.v1.staff_invites.send_staff_invite_email", new=AsyncMock(return_value=True)):
        resp = await client.post(f"{BASE}/{u.id}/resend", headers=admin_headers(test_admin))
    assert resp.status_code == 200
    await db.refresh(u)
    assert u.invite_token is not None and u.invite_token != old_hash   # rotated


@pytest.mark.asyncio
async def test_revoke_deletes_pending_user_200(client, db, test_admin):
    u = await _pending(db, "v@x.org")
    uid = u.id
    resp = await client.delete(f"{BASE}/{uid}", headers=admin_headers(test_admin))
    assert resp.status_code == 200
    assert (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_resend_on_active_user_rejected_400(client, db, test_admin):
    u = await _pending(db, "act@x.org")
    setattr(u, "is_active", True)
    setattr(u, "invite_token", None)
    await db.flush()
    resp = await client.post(f"{BASE}/{u.id}/resend", headers=admin_headers(test_admin))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_revoke_on_active_user_rejected_400(client, db, test_admin):
    u = await _pending(db, "act2@x.org")
    setattr(u, "is_active", True)
    setattr(u, "invite_token", None)
    await db.flush()
    resp = await client.delete(f"{BASE}/{u.id}", headers=admin_headers(test_admin))
    assert resp.status_code == 400
