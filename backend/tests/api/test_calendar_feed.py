# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the per-patron iCal feed.

Endpoints:
- GET /api/v1/me/calendar.ics?token=...  (token-authed)
- POST /api/v1/me/calendar/token         (auth required)
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.calendar_feed import mint_calendar_token
from app.core.security import hash_password
from app.main import app
from app.models.catalog import CatalogItem
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_patron(db, email):
    user = User(
        email=email,
        password_hash=hash_password("TestPass123!"),
        first_name="Cal",
        last_name="Endar",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _make_item(db, title):
    item = CatalogItem(title=title, author="A. Tester")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _make_checkout(db, user_id, item_id, due_in_days=7):
    co = Checkout(
        user_id=user_id,
        item_id=item_id,
        status=CheckoutStatus.active,
        due_date=datetime.now(timezone.utc) + timedelta(days=due_in_days),
    )
    db.add(co)
    await db.commit()
    await db.refresh(co)
    return co


async def _make_ready_hold(db, user_id, item_id):
    h = Hold(
        user_id=user_id,
        item_id=item_id,
        status=HoldStatus.ready,
        position=1,
        notified_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=5),
    )
    db.add(h)
    await db.commit()
    await db.refresh(h)
    return h


# ---------------------------------------------------------------------------
# Tests: GET /me/calendar.ics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_token_returns_calendar_with_checkout_event(client, db):
    patron = await _make_patron(db, "cal.valid@example.com")
    item = await _make_item(db, "Trail Mix Cookery")
    await _make_checkout(db, patron.id, item.id)

    token = mint_calendar_token(patron.id)
    resp = await client.get(f"/api/v1/me/calendar.ics?token={token}")

    assert resp.status_code == 200, resp.text
    ct = resp.headers["content-type"]
    assert ct.startswith("text/calendar"), ct
    assert "charset=utf-8" in ct.lower()
    assert "inline" in resp.headers.get("content-disposition", "")
    assert "l30-calendar.ics" in resp.headers.get("content-disposition", "")
    assert resp.headers.get("cache-control", "").lower().startswith("private")

    body = resp.text
    assert body.startswith("BEGIN:VCALENDAR\r\n")
    assert body.endswith("END:VCALENDAR\r\n")
    assert "BEGIN:VEVENT\r\n" in body
    assert "END:VEVENT\r\n" in body
    assert "UID:l30-checkout-" in body
    assert "DTSTART;VALUE=DATE:" in body
    assert "SUMMARY:Library item due: Trail Mix Cookery" in body


@pytest.mark.asyncio
async def test_calendar_includes_ready_hold_event(client, db):
    patron = await _make_patron(db, "cal.hold@example.com")
    item = await _make_item(db, "Pickup, Please\\")
    await _make_ready_hold(db, patron.id, item.id)

    token = mint_calendar_token(patron.id)
    resp = await client.get(f"/api/v1/me/calendar.ics?token={token}")
    assert resp.status_code == 200
    body = resp.text

    assert "UID:l30-hold-" in body
    assert "DTSTART;VALUE=DATE:" in body
    assert "DTEND;VALUE=DATE:" in body
    # Comma + backslash escaped per RFC 5545; backslash first so we don't
    # double-escape downstream characters.
    assert "SUMMARY:Hold ready for pickup: Pickup\\, Please\\\\" in body


@pytest.mark.asyncio
async def test_tampered_token_returns_401(client, db):
    patron = await _make_patron(db, "cal.tamper@example.com")
    item = await _make_item(db, "Defacto Standards")
    await _make_checkout(db, patron.id, item.id)

    good = mint_calendar_token(patron.id)
    # Flip one hex char in the signature.
    user_part, sig = good.split(".", 1)
    flipped_char = "0" if sig[0] != "0" else "1"
    tampered = f"{user_part}.{flipped_char}{sig[1:]}"

    resp = await client.get(f"/api/v1/me/calendar.ics?token={tampered}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wrong_user_token_only_returns_that_users_data(client, db):
    """Token signed for user A must not surface user B's checkouts.

    A token signed with user B's user_id but trying to claim user A's data
    is impossible by construction -- the signature is over the user_id --
    so we instead assert that swapping the user_id portion invalidates
    the signature (returns 401)."""
    patron_a = await _make_patron(db, "cal.a@example.com")
    patron_b = await _make_patron(db, "cal.b@example.com")
    item_a = await _make_item(db, "Patron A's Book")
    item_b = await _make_item(db, "Patron B's Book")
    await _make_checkout(db, patron_a.id, item_a.id)
    await _make_checkout(db, patron_b.id, item_b.id)

    # Take patron_a's valid signature, paste it onto patron_b's user_id.
    token_a = mint_calendar_token(patron_a.id)
    _user_a, sig_a = token_a.split(".", 1)
    forged = f"{patron_b.id}.{sig_a}"
    resp = await client.get(f"/api/v1/me/calendar.ics?token={forged}")
    assert resp.status_code == 401

    # And the well-formed token for patron_b returns only patron_b's data.
    token_b = mint_calendar_token(patron_b.id)
    resp_b = await client.get(f"/api/v1/me/calendar.ics?token={token_b}")
    assert resp_b.status_code == 200
    assert "Patron B's Book" in resp_b.text
    assert "Patron A's Book" not in resp_b.text


@pytest.mark.asyncio
async def test_malformed_token_returns_401(client):
    for bad in ("", "no-dot-here", "abc.def", ".sig", "1.", "1.deadbeef"):
        resp = await client.get(f"/api/v1/me/calendar.ics?token={bad}")
        assert resp.status_code == 401, f"expected 401 for {bad!r}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Tests: POST /me/calendar/token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_mint_endpoint_returns_webcal_url(test_db):
    """The mint endpoint requires auth; we override the dep to inject a patron."""
    from app.api.v1.auth import get_current_user
    from app.core.database import get_db

    patron = await _make_patron(test_db, "cal.mint@example.com")

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return patron

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/me/calendar/token")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "url" in body
    url = body["url"]
    assert url.startswith("webcal://"), url
    assert "/api/v1/me/calendar.ics?token=" in url
    # The token in the URL should validate back to the same patron.
    token = url.split("token=", 1)[1]
    from app.api.v1.calendar_feed import verify_calendar_token
    assert verify_calendar_token(token) == patron.id


@pytest.mark.asyncio
async def test_token_mint_requires_auth(client):
    resp = await client.post("/api/v1/me/calendar/token")
    assert resp.status_code in (401, 403)
