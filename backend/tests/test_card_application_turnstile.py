# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Turnstile gate on POST /card-applications.

Mirrors the AsyncClient + AsyncMock pattern from test_2fa_recovery_turnstile.py
and test_auth_turnstile_gaps.py.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def _reset_test_engine_pool():
    """Dispose the shared async-PG pool between tests in this file.

    See feedback_l30_async_pytest_one_at_a_time: L30 async tests share a
    process-wide engine pool while each pytest-asyncio test gets a fresh
    event loop; without disposal the second test fails with
    'Event loop is closed'.
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


CARD_APP_URL = "/api/v1/card-applications"

VALID_PAYLOAD = {
    "first_name": "Ada",
    "last_name": "Lovelace",
    "email": "ada.lovelace@example.com",
    "address_line1": "1 Analytical Engine Way",
    "city": "London",
    "state": "ON",
    "zip_code": "12345",
}


async def test_card_application_turnstile_failure_returns_400(client: AsyncClient):
    """Endpoint rejects when Turnstile verification fails."""
    with patch(
        "app.api.v1.card_applications.verify_turnstile",
        new=AsyncMock(return_value=False),
    ) as mock_verify:
        resp = await client.post(
            CARD_APP_URL,
            json={**VALID_PAYLOAD, "turnstile_token": "bad"},
        )

    assert resp.status_code == 400
    body = resp.json()
    # Error envelope wraps detail in {"error": {"message": ...}} on this app;
    # fall back to top-level detail for compatibility with either shape.
    msg = (
        body.get("error", {}).get("message")
        or body.get("detail")
        or ""
    ).lower()
    assert "captcha" in msg
    # Confirm verify_turnstile was called with the submitted token.
    mock_verify.assert_awaited_once()
    args, _ = mock_verify.await_args
    assert args[0] == "bad"


async def test_card_application_turnstile_success_proceeds_to_create(
    client: AsyncClient,
):
    """When Turnstile passes, the gate clears and the endpoint creates the app.

    A successful Turnstile mock followed by a 201 response proves the guard
    executed BEFORE the persistence path -- if the guard had short-circuited
    with 400 we would not see the created application.
    """
    with patch(
        "app.api.v1.card_applications.verify_turnstile",
        new=AsyncMock(return_value=True),
    ) as mock_verify:
        resp = await client.post(
            CARD_APP_URL,
            json={**VALID_PAYLOAD, "turnstile_token": "ok"},
        )

    assert resp.status_code == 201, resp.text
    mock_verify.assert_awaited_once()
