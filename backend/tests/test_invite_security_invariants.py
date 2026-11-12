# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import BackgroundTasks
from app.api.v1.auth import password as password_mod
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import ForgotPasswordRequest


def _make_request():
    # app/core/rate_limit.py:client_ip (used by forgot_password to log/rate
    # -limit by real client IP behind Cloudflare) reads request.headers
    # before falling back to request.client.host, so the fake Request needs
    # a headers mapping too.
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})


def _make_db_with(user):
    db = type("DB", (), {})()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(scalar_one_or_none=lambda: user)
    )
    db.commit = AsyncMock()
    return db


def _ensure_routers():
    # Importing app.main runs its module-level `register_all_routers(app,
    # debug=settings.debug)` exactly once (Python caches the module), so
    # routers are already registered by the time this runs. Calling
    # register_all_routers() again here would double every route: fastapi
    # >=0.139's lazy `_IncludedRouter` wrappers don't expose `.path` at the
    # top level of app.routes, so the old "is /api/v1/auth/login already
    # registered" check can no longer detect prior registration and always
    # re-fired, silently doubling app.routes on every import of this module.
    from app.main import app  # noqa: F401
    from app.core.rate_limit import limiter
    limiter.enabled = False


_ensure_routers()


@pytest.mark.asyncio
async def test_pending_staff_cannot_login(client, db):
    """Pending invite (is_active=False) must be rejected at login with 401."""
    pw = "Invite!Pass1"
    u = User(
        email="pending.staff@x.org",
        first_name="Pending",
        last_name="Staff",
        role=UserRole.STAFF,
        email_verified=True,
        failed_login_attempts=0,
        locked_until=None,
    )
    u.password_hash = hash_password(pw)
    u.is_active = False
    db.add(u)
    await db.flush()
    payload = {"email": "pending.staff@x.org", "password": pw, "turnstile_token": "x"}
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code in (401, 403), (
        f"Expected 401/403 for inactive user, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_forgot_password_no_reset_for_unverified_pending_user():
    """Forgot-password for email_verified=False must not set a reset token.

    Uses direct handler call with mocked DB (mirrors test_forgot_password_timing.py).
    """
    pending_user = SimpleNamespace(
        id=99,
        email="pending.invite@x.org",
        email_verified=False,
        first_name="Pending",
    )
    pending_user.reset_token = None
    pending_user.reset_token_expires = None
    bg = BackgroundTasks()
    req_kwargs = {"email": "pending.invite@x.org"}
    req_kwargs["turnstile_token"] = "x"
    req_body = ForgotPasswordRequest(**req_kwargs)

    with patch.object(password_mod, "verify_turnstile", new=AsyncMock(return_value=True)):
        resp = await password_mod.forgot_password(
            request=_make_request(),
            forgot_request=req_body,
            background_tasks=bg,
            db=_make_db_with(pending_user),
        )

    assert resp.message
    assert bg.tasks == []
    assert pending_user.reset_token is None
