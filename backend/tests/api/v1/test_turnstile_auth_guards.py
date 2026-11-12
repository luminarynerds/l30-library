# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Turnstile guard on three auth endpoints:
  - POST /api/v1/auth/magic-link
  - POST /api/v1/auth/resend-verification
  - POST /api/v1/account/security/2fa/recovery
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _captcha_detail(resp) -> str:
    """Extract the error message from either FastAPI detail or the app's error envelope."""
    body = resp.json()
    # App wraps HTTPException as {"error": {"message": "...", ...}}
    if isinstance(body.get("error"), dict):
        return body["error"].get("message", "")
    # Fallback: plain FastAPI {"detail": "..."}
    return body.get("detail", "")


# ---------------------------------------------------------------------------
# /auth/magic-link
# ---------------------------------------------------------------------------

async def test_magic_link_turnstile_failure_returns_400(client: AsyncClient):
    """Turnstile failure on /auth/magic-link returns 400 before any DB lookup."""
    with patch(
        "app.api.v1.auth.login.verify_turnstile",
        new=AsyncMock(return_value=False),
    ):
        resp = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "anyone@example.com", "turnstile_token": "bad-token"},
        )
    assert resp.status_code == 400
    assert "Captcha" in _captcha_detail(resp)


async def test_magic_link_turnstile_pass_reaches_handler(client: AsyncClient):
    """With Turnstile passing, the request proceeds past the guard (returns 200)."""
    with patch(
        "app.api.v1.auth.login.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "nobody@example.com", "turnstile_token": "ok-token"},
        )
    # Email doesn't exist — handler still returns 200 (anti-enumeration)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /auth/resend-verification
# ---------------------------------------------------------------------------

async def test_resend_verification_turnstile_failure_returns_400(client: AsyncClient):
    """Turnstile failure on /auth/resend-verification returns 400 before any DB lookup."""
    with patch(
        "app.api.v1.auth.password.verify_turnstile",
        new=AsyncMock(return_value=False),
    ):
        resp = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "anyone@example.com", "turnstile_token": "bad-token"},
        )
    assert resp.status_code == 400
    assert "Captcha" in _captcha_detail(resp)


async def test_resend_verification_turnstile_pass_reaches_handler(client: AsyncClient):
    """With Turnstile passing, the request proceeds (returns 200 anti-enumeration)."""
    with patch(
        "app.api.v1.auth.password.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nobody@example.com", "turnstile_token": "ok-token"},
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /account/security/2fa/recovery
# ---------------------------------------------------------------------------

async def test_2fa_recovery_turnstile_failure_returns_400(client: AsyncClient):
    """Turnstile failure on /account/security/2fa/recovery returns 400.

    The guard runs BEFORE verify_2fa_pending_token: a bad turnstile token
    must return 400 (not 401 from an invalid pending_token), proving ordering.
    """
    with patch(
        "app.api.v1.account_security.verify_turnstile",
        new=AsyncMock(return_value=False),
    ):
        resp = await client.post(
            "/api/v1/account/security/2fa/recovery",
            json={
                "pending_token": "fake-pending-token",
                "recovery_code": "ABCD1234",
                "turnstile_token": "bad-token",
            },
        )
    # Guard fires first (400), not verify_2fa_pending_token failure (401)
    assert resp.status_code == 400
    assert "Captcha" in _captcha_detail(resp)


async def test_2fa_recovery_turnstile_pass_reaches_handler(client: AsyncClient):
    """With Turnstile passing, the request reaches verify_2fa_pending_token.

    An invalid pending_token returns 401 (not 400), proving the guard passed
    and execution continued to the pending-token check.
    """
    with patch(
        "app.api.v1.account_security.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(
            "/api/v1/account/security/2fa/recovery",
            json={
                "pending_token": "invalid-token",
                "recovery_code": "ABCD1234",
                "turnstile_token": "ok-token",
            },
        )
    # Turnstile passed; pending_token is invalid → 401 (not 400)
    assert resp.status_code == 401
