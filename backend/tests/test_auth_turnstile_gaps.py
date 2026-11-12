# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Turnstile gates on the magic-link and resend-verification endpoints.

Mirrors the AsyncClient + AsyncMock pattern from
tests/api/v1/test_public_records_public.py.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def _reset_test_engine_pool():
    """Dispose the shared async-PG pool between tests in this file.

    L30 async tests share a process-wide engine pool while each pytest-asyncio
    test gets a fresh event loop; without disposal, the second test in the
    same session fails with 'Event loop is closed' (see
    feedback_l30_async_pytest_one_at_a_time).
    """
    yield
    import tests.conftest as tc
    if tc._engine is not None:
        try:
            await tc._engine.dispose()
        except Exception:
            pass
        tc._engine = None
        tc._session_factory = None


MAGIC_LINK_URL = "/api/v1/auth/magic-link"
RESEND_VERIFICATION_URL = "/api/v1/auth/resend-verification"


async def test_magic_link_turnstile_failure_returns_400(client: AsyncClient):
    """Magic-link issuance rejects when Turnstile verification fails."""
    with patch(
        "app.api.v1.auth.login.verify_turnstile",
        new=AsyncMock(return_value=False),
    ):
        resp = await client.post(
            MAGIC_LINK_URL,
            json={"email": "patron@example.com", "turnstile_token": "bad"},
        )

    assert resp.status_code == 400
    assert "captcha" in resp.json()["error"]["message"].lower()


async def test_magic_link_turnstile_success_returns_200(client: AsyncClient):
    """Magic-link issuance proceeds (generic 200) when Turnstile passes,
    even for an unknown email — the handler never leaks existence."""
    with patch(
        "app.api.v1.auth.login.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(
            MAGIC_LINK_URL,
            json={"email": "nobody@example.com", "turnstile_token": "ok"},
        )

    assert resp.status_code == 200
    assert "sign-in link" in resp.json()["message"].lower()


async def test_resend_verification_turnstile_failure_returns_400(client: AsyncClient):
    """Resend-verification rejects when Turnstile verification fails."""
    with patch(
        "app.api.v1.auth.password.verify_turnstile",
        new=AsyncMock(return_value=False),
    ):
        resp = await client.post(
            RESEND_VERIFICATION_URL,
            json={"email": "patron@example.com", "turnstile_token": "bad"},
        )

    assert resp.status_code == 400
    assert "captcha" in resp.json()["error"]["message"].lower()


async def test_resend_verification_turnstile_success_returns_200(client: AsyncClient):
    """Resend-verification proceeds (generic 200) when Turnstile passes,
    even for an unknown email — the handler never leaks existence."""
    with patch(
        "app.api.v1.auth.password.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(
            RESEND_VERIFICATION_URL,
            json={"email": "nobody@example.com", "turnstile_token": "ok"},
        )

    assert resp.status_code == 200
    assert "verification email" in resp.json()["message"].lower()
