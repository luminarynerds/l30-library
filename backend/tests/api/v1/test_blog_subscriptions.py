# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for blog email digest subscription endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.blog_subscription import BlogEmailSubscription


# Each test sets is_sent_mock to control send_email's return; default True.
@pytest.fixture
def mock_send_email():
    """Patch app.api.v1.blog_subscriptions.send_email -> AsyncMock returning True."""
    with patch(
        "app.api.v1.blog_subscriptions.send_email",
        new_callable=AsyncMock,
        return_value=True,
    ) as m:
        yield m


# ---------------------------------------------------------------------------
# POST /api/v1/blog/subscribe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribe_anon_creates_subscription(
    public_client, test_db, mock_send_email
):
    resp = await public_client.post(
        "/api/v1/blog/subscribe",
        json={"email": "Anon@Example.COM", "frequency": "weekly"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending_confirmation"
    assert body["already_subscribed"] is False
    assert body["frequency"] == "weekly"
    assert body["email"] == "anon@example.com"

    # Confirmation email was queued
    assert mock_send_email.await_count == 1
    sent_kwargs = mock_send_email.await_args.kwargs
    assert sent_kwargs["to_email"] == "anon@example.com"

    # Row exists with no user_id and tokens populated
    result = await test_db.execute(
        select(BlogEmailSubscription).where(
            BlogEmailSubscription.email == "anon@example.com"
        )
    )
    row = result.scalar_one()
    assert row.user_id is None
    assert row.confirmed_at is None
    assert len(row.confirmation_token) >= 32
    assert len(row.unsubscribe_token) >= 32


@pytest.mark.asyncio
async def test_subscribe_idempotent_same_email_freq(
    public_client, test_db, mock_send_email
):
    payload = {"email": "dup@example.com", "frequency": "weekly"}
    r1 = await public_client.post("/api/v1/blog/subscribe", json=payload)
    r2 = await public_client.post("/api/v1/blog/subscribe", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["already_subscribed"] is False
    assert r2.json()["already_subscribed"] is True
    assert r2.json()["status"] == "already_subscribed"

    # Confirmation email only sent once
    assert mock_send_email.await_count == 1

    # Still exactly one row
    result = await test_db.execute(
        select(BlogEmailSubscription).where(
            BlogEmailSubscription.email == "dup@example.com"
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_subscribe_invalid_email_returns_422(
    public_client, mock_send_email
):
    resp = await public_client.post(
        "/api/v1/blog/subscribe",
        json={"email": "not-an-email", "frequency": "weekly"},
    )
    assert resp.status_code == 422
    assert mock_send_email.await_count == 0


@pytest.mark.asyncio
async def test_subscribe_authed_user_links_user_id(
    staff_client, test_db, test_staff, mock_send_email
):
    # staff_client fixture overrides get_current_user only; this route declares
    # get_optional_user, so add a local override that returns the authed staff
    # user. Removed in finally so other tests stay anon-by-default.
    from app.api.v1.auth.helpers import get_optional_user
    from app.main import app

    async def _override_optional_authed():
        return test_staff

    app.dependency_overrides[get_optional_user] = _override_optional_authed
    try:
        resp = await staff_client.post(
            "/api/v1/blog/subscribe",
            json={"email": "staffsub@example.com", "frequency": "weekly"},
        )
        assert resp.status_code == 200, resp.text

        result = await test_db.execute(
            select(BlogEmailSubscription).where(
                BlogEmailSubscription.email == "staffsub@example.com"
            )
        )
        row = result.scalar_one()
        assert row.user_id == test_staff.id
    finally:
        app.dependency_overrides.pop(get_optional_user, None)


# ---------------------------------------------------------------------------
# GET /api/v1/blog/unsubscribe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsubscribe_removes_subscription(
    public_client, test_db, mock_send_email
):
    await public_client.post(
        "/api/v1/blog/subscribe",
        json={"email": "leaving@example.com", "frequency": "weekly"},
    )
    result = await test_db.execute(
        select(BlogEmailSubscription).where(
            BlogEmailSubscription.email == "leaving@example.com"
        )
    )
    row = result.scalar_one()
    token = row.unsubscribe_token

    resp = await public_client.get(f"/api/v1/blog/unsubscribe?token={token}")
    assert resp.status_code == 200
    assert "unsubscribed" in resp.text.lower()

    # Row gone (expire identity map so we see the route's commit)
    test_db.expire_all()
    result = await test_db.execute(
        select(BlogEmailSubscription).where(
            BlogEmailSubscription.email == "leaving@example.com"
        )
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_unsubscribe_bad_token_returns_400(public_client):
    resp = await public_client.get(
        "/api/v1/blog/unsubscribe?token=clearly-not-a-real-token"
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/v1/blog/confirm
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_activates_subscription(
    public_client, test_db, mock_send_email
):
    await public_client.post(
        "/api/v1/blog/subscribe",
        json={"email": "confirm-me@example.com", "frequency": "weekly"},
    )
    result = await test_db.execute(
        select(BlogEmailSubscription).where(
            BlogEmailSubscription.email == "confirm-me@example.com"
        )
    )
    row = result.scalar_one()
    assert row.confirmed_at is None

    resp = await public_client.get(
        f"/api/v1/blog/confirm?token={row.confirmation_token}"
    )
    assert resp.status_code == 200
    assert "confirmed" in resp.text.lower()

    await test_db.refresh(row)
    assert row.confirmed_at is not None


# ---------------------------------------------------------------------------
# GET /api/v1/blog/subscriptions/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_my_subscriptions(
    staff_client, test_db, test_staff, mock_send_email
):
    # POSTs hit /subscribe which uses get_optional_user — needs a local override
    # so user_id is linked; otherwise GET /me filters them out.
    from app.api.v1.auth.helpers import get_optional_user
    from app.main import app

    async def _override_optional_authed():
        return test_staff

    app.dependency_overrides[get_optional_user] = _override_optional_authed
    try:
        # Subscribe twice with different frequencies
        await staff_client.post(
            "/api/v1/blog/subscribe",
            json={"email": "me-list@example.com", "frequency": "weekly"},
        )
        await staff_client.post(
            "/api/v1/blog/subscribe",
            json={"email": "me-list@example.com", "frequency": "monthly"},
        )
    finally:
        app.dependency_overrides.pop(get_optional_user, None)

    resp = await staff_client.get("/api/v1/blog/subscriptions/me")
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    # The fixture user might have other historic rows from prior tests in the
    # same session if the DB is shared; check ours are present.
    emails_freqs = {(i["email"], i["frequency"]) for i in items}
    assert ("me-list@example.com", "weekly") in emails_freqs
    assert ("me-list@example.com", "monthly") in emails_freqs
