# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the forgot-password timing-oracle fix.

Spec: 2026-05-19-l30-rate-limiting-tiered-policy.md §11.

The handler used to ``await send_password_reset_email`` inline only on the
verified-account branch, which leaked account existence via response latency.
The fix defers the SMTP send to a FastAPI ``BackgroundTasks`` so the response
returns from BOTH branches before any email work happens.

These tests call the handler directly with stubs to avoid the integration-DB
harness; they verify the dispatch contract, which is the actual behavior the
fix introduces.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks

from app.api.v1.auth import password as password_mod
from app.schemas.user import ForgotPasswordRequest


def _make_request():
    """Build a minimal Request stand-in for the handler.

    app/core/rate_limit.py's client_ip() (used by the handler to log/rate
    -limit) now checks request.headers for CF-Connecting-IP / X-Real-IP
    before falling back to request.client.host -- this stub predates that
    and had no .headers at all, so client_ip() raised AttributeError before
    the handler ever got to the behavior these tests actually cover.
    """
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})


def _make_db_with(user):
    """Build an AsyncSession stand-in whose .execute(...).scalar_one_or_none() == user."""
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(scalar_one_or_none=lambda: user)
    )
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_forgot_password_defers_email_send_for_verified_user():
    """Verified-user branch must queue the send, not await it inline."""
    user = SimpleNamespace(
        id=42,
        email="verified@example.com",
        email_verified=True,
        first_name="Pat",
        reset_token=None,
        reset_token_expires=None,
    )
    bg = BackgroundTasks()
    req_body = ForgotPasswordRequest(
        email="verified@example.com", turnstile_token="x"
    )

    with patch.object(password_mod, "verify_turnstile", new=AsyncMock(return_value=True)), \
         patch.object(password_mod, "send_password_reset_email", new=AsyncMock()) as inline_send:
        resp = await password_mod.forgot_password(
            request=_make_request(),
            forgot_request=req_body,
            background_tasks=bg,
            db=_make_db_with(user),
        )

    # Response shipped before any SMTP work occurred.
    assert resp.message
    inline_send.assert_not_awaited()

    # The slow send was queued as a background task, not awaited in-line.
    assert len(bg.tasks) == 1
    task = bg.tasks[0]
    assert task.func is password_mod._send_password_reset_email_safe
    # email, token, first_name, user_id (token is random, just present)
    assert task.args[0] == "verified@example.com"
    assert isinstance(task.args[1], str) and len(task.args[1]) > 0
    assert task.args[2] == "Pat"
    assert task.args[3] == 42

    # DB-side bookkeeping (fast) still happens in-line so the token is valid by
    # the time the email arrives.
    assert user.reset_token is not None
    assert user.reset_token_expires is not None


@pytest.mark.asyncio
async def test_forgot_password_does_not_send_for_unverified_user():
    """Unverified-user branch must NOT queue any send (parity with not-exists)."""
    user = SimpleNamespace(
        id=7,
        email="unverified@example.com",
        email_verified=False,
        first_name="Sam",
        reset_token=None,
        reset_token_expires=None,
    )
    bg = BackgroundTasks()
    req_body = ForgotPasswordRequest(
        email="unverified@example.com", turnstile_token="x"
    )

    with patch.object(password_mod, "verify_turnstile", new=AsyncMock(return_value=True)), \
         patch.object(password_mod, "send_password_reset_email", new=AsyncMock()) as inline_send:
        resp = await password_mod.forgot_password(
            request=_make_request(),
            forgot_request=req_body,
            background_tasks=bg,
            db=_make_db_with(user),
        )

    assert resp.message
    inline_send.assert_not_awaited()
    assert bg.tasks == []
    assert user.reset_token is None


@pytest.mark.asyncio
async def test_forgot_password_does_not_send_for_unknown_email():
    """Nonexistent-email branch must NOT queue any send."""
    bg = BackgroundTasks()
    req_body = ForgotPasswordRequest(
        email="ghost@example.com", turnstile_token="x"
    )

    with patch.object(password_mod, "verify_turnstile", new=AsyncMock(return_value=True)), \
         patch.object(password_mod, "send_password_reset_email", new=AsyncMock()) as inline_send:
        resp = await password_mod.forgot_password(
            request=_make_request(),
            forgot_request=req_body,
            background_tasks=bg,
            db=_make_db_with(None),
        )

    assert resp.message
    inline_send.assert_not_awaited()
    assert bg.tasks == []


@pytest.mark.asyncio
async def test_background_wrapper_swallows_send_errors():
    """The background wrapper must log-and-swallow so failures never reach the client."""
    with patch.object(
        password_mod,
        "send_password_reset_email",
        new=AsyncMock(side_effect=RuntimeError("smtp down")),
    ):
        # Must not raise — the response has already been returned by this point.
        await password_mod._send_password_reset_email_safe(
            "x@example.com", "tok", "First", 99
        )
