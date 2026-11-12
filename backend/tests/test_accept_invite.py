# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from datetime import datetime, timedelta, timezone
from app.models.user import User, UserRole
from app.core.security import hash_reset_token

ACCEPT = "/api/v1/auth/accept-invite"
RAW = "raw-invite-value-aaaaaaaaaaaaaaaaaaaaaaaa"
STRONG = "Str0ng-Passphrase-9x!"

async def _pending(db, email, raw=RAW, expires_in=timedelta(hours=72)):
    u = User(email=email, first_name="P", last_name="Q", role=UserRole.STAFF,
             is_active=False, email_verified=False)
    u.invite_token = hash_reset_token(raw)
    u.invite_token_expires = datetime.now(timezone.utc) + expires_in
    setattr(u, "password_hash", "x")
    db.add(u); await db.flush(); return u

@pytest.mark.asyncio
async def test_accept_activates_and_sets_password(client, db):
    u = await _pending(db, "a@x.org")
    resp = await client.post(ACCEPT, json={"token": RAW, "new_password": STRONG})
    assert resp.status_code == 200
    await db.refresh(u)
    assert u.is_active is True and u.email_verified is True and u.invite_token is None

@pytest.mark.asyncio
async def test_accept_expired_400(client, db):
    await _pending(db, "b@x.org", raw="other-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", expires_in=timedelta(hours=-1))
    resp = await client.post(ACCEPT, json={"token": "other-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "new_password": STRONG})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_accept_ignores_role_in_body(client, db):
    u = await _pending(db, "c@x.org", raw="craw-cccccccccccccccccccccccccccccccc")
    resp = await client.post(ACCEPT, json={"token": "craw-cccccccccccccccccccccccccccccccc", "new_password": STRONG, "role": "super_admin"})
    assert resp.status_code == 200
    await db.refresh(u)
    assert u.role == UserRole.STAFF

@pytest.mark.asyncio
async def test_accept_is_single_use(client, db):
    await _pending(db, "d@x.org", raw="draw-dddddddddddddddddddddddddddddddd")
    body = {"token": "draw-dddddddddddddddddddddddddddddddd", "new_password": STRONG}
    r1 = await client.post(ACCEPT, json=body)
    r2 = await client.post(ACCEPT, json=body)
    assert r1.status_code == 200 and r2.status_code == 400

@pytest.mark.asyncio
async def test_accept_writes_audit_log(client, db):
    from sqlalchemy import select
    from app.models.audit_log import AuditLog
    u = await _pending(db, "audit@x.org", raw="auditraw-eeeeeeeeeeeeeeeeeeeeeeeeeeee")
    resp = await client.post(ACCEPT, json={"token": "auditraw-eeeeeeeeeeeeeeeeeeeeeeeeeeee", "new_password": STRONG})
    assert resp.status_code == 200
    rows = (await db.execute(select(AuditLog).where(AuditLog.target_user_id == u.id))).scalars().all()
    assert any((r.details or {}).get("invite_accepted") for r in rows)
