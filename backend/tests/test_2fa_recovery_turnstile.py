# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Turnstile gate on the /2fa/recovery endpoint.

Mirrors the AsyncClient + AsyncMock pattern from test_auth_turnstile_gaps.py.
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


RECOVERY_URL = "/api/v1/account/security/2fa/recovery"


async def test_2fa_recovery_turnstile_failure_returns_400(client: AsyncClient):
    """Recovery endpoint rejects when Turnstile verification fails."""
    with patch(
        "app.api.v1.account_security.verify_turnstile",
        new=AsyncMock(return_value=False),
    ):
        resp = await client.post(
            RECOVERY_URL,
            json={
                "pending_token": "bogus-pending-token",
                "recovery_code": "BOGUS-CODE",
                "turnstile_token": "bad",
            },
        )

    assert resp.status_code == 400
    assert "captcha" in resp.json()["error"]["message"].lower()


async def test_2fa_recovery_turnstile_success_reaches_pending_token_verify(client: AsyncClient):
    """When Turnstile passes, guard exits cleanly and pending-token verify runs.

    A bogus pending_token yields 401 — proving the Turnstile guard executed
    BEFORE verify_2fa_pending_token (which would not produce 401 if the guard
    had short-circuited with 400 first).
    """
    with patch(
        "app.api.v1.account_security.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(
            RECOVERY_URL,
            json={
                "pending_token": "bogus-pending-token",
                "recovery_code": "BOGUS-CODE",
                "turnstile_token": "ok",
            },
        )

    assert resp.status_code == 401
