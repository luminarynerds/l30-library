# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""PR #999: tests for the real event waitlist surface.

Covers join (full / has-spots-409), idempotency, position, cancel-by-token,
promotion-triggers-claim-email when a confirmed registration is cancelled,
and the magic-link claim flow including expiry.

These tests exercise the full HTTP path. Same SQLite tz caveat as
test_event_registration.py — skip on SQLite where applicable.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.event import Event
from app.models.event_registration import EventRegistration, EventRegistrationStatus
from app.models.event_waitlist import EventWaitlistEntry, WaitlistStatus


def _is_sqlite(db) -> bool:
    try:
        return db.bind.dialect.name == "sqlite"
    except Exception:
        return False


async def _create_full_event(test_db, *, max_attendees: int = 2) -> Event:
    n = datetime.now(timezone.utc)
    if _is_sqlite(test_db):
        n = n.replace(tzinfo=None)
    start = n + timedelta(days=7)
    event = Event(
        title="Sold Out Storytime",
        description="Capacity 2.",
        start_time=start,
        end_time=start + timedelta(hours=1),
        is_published=True,
        registration_required=True,
        max_attendees=max_attendees,
        photos_will_be_taken=False,
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)
    # Fill it
    for i in range(max_attendees):
        test_db.add(
            EventRegistration(
                event_id=event.id,
                patron_name=f"Filler {i}",
                patron_email=f"filler{i}@example.com",
                status=EventRegistrationStatus.CONFIRMED.value,
            )
        )
    await test_db.commit()
    return event


async def _create_open_event(test_db, *, max_attendees: int = 10) -> Event:
    n = datetime.now(timezone.utc)
    if _is_sqlite(test_db):
        n = n.replace(tzinfo=None)
    start = n + timedelta(days=7)
    event = Event(
        title="Open Event",
        description="Has spots.",
        start_time=start,
        end_time=start + timedelta(hours=1),
        is_published=True,
        registration_required=True,
        max_attendees=max_attendees,
        photos_will_be_taken=False,
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)
    return event


def _stub_turnstile(monkeypatch) -> None:
    from app.api.v1 import event_waitlist_routes

    async def _fake_verify(*_a, **_kw):
        return True

    monkeypatch.setattr(event_waitlist_routes, "verify_turnstile", _fake_verify)


@pytest.mark.asyncio
async def test_waitlist_join_when_full(test_db, client, monkeypatch):
    if _is_sqlite(test_db):
        pytest.skip("Endpoint compares tz-aware now() to start_time")
    _stub_turnstile(monkeypatch)
    event = await _create_full_event(test_db)

    resp = await client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"email": "wait1@example.com", "name": "Waiter One"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["position"] == 1
    assert body["status"] == "waiting"
    assert body["cancel_token"]


@pytest.mark.asyncio
async def test_waitlist_join_409_when_spots_available(test_db, client, monkeypatch):
    if _is_sqlite(test_db):
        pytest.skip("Endpoint compares tz-aware now() to start_time")
    _stub_turnstile(monkeypatch)
    event = await _create_open_event(test_db)

    resp = await client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"email": "early@example.com"},
    )
    assert resp.status_code == 409, resp.text
    detail = resp.json()["error"]["message"]
    assert detail["error"] == "event_has_spots"
    assert detail["register_url"].endswith(f"/events/{event.id}/register")


@pytest.mark.asyncio
async def test_waitlist_join_idempotent_on_duplicate_email(test_db, client, monkeypatch):
    if _is_sqlite(test_db):
        pytest.skip("Endpoint compares tz-aware now() to start_time")
    _stub_turnstile(monkeypatch)
    event = await _create_full_event(test_db)

    r1 = await client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"email": "dup@example.com"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"email": "dup@example.com"},
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == r1.json()["id"]
    assert r2.json()["position"] == 1


@pytest.mark.asyncio
async def test_waitlist_position_1_indexed_and_404(test_db, client, monkeypatch):
    if _is_sqlite(test_db):
        pytest.skip("Endpoint compares tz-aware now() to start_time")
    _stub_turnstile(monkeypatch)
    event = await _create_full_event(test_db)

    await client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"email": "first@example.com"},
    )
    await client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"email": "second@example.com"},
    )

    r1 = await client.get(
        f"/api/v1/events/{event.id}/waitlist/position",
        params={"email": "first@example.com"},
    )
    assert r1.status_code == 200
    assert r1.json()["position"] == 1

    r2 = await client.get(
        f"/api/v1/events/{event.id}/waitlist/position",
        params={"email": "second@example.com"},
    )
    assert r2.status_code == 200
    assert r2.json()["position"] == 2

    r404 = await client.get(
        f"/api/v1/events/{event.id}/waitlist/position",
        params={"email": "ghost@example.com"},
    )
    assert r404.status_code == 404


@pytest.mark.asyncio
async def test_waitlist_cancel_by_token_and_wrong_token_403(test_db, client, monkeypatch):
    if _is_sqlite(test_db):
        pytest.skip("Endpoint compares tz-aware now() to start_time")
    _stub_turnstile(monkeypatch)
    event = await _create_full_event(test_db)

    join = await client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"email": "leaver@example.com"},
    )
    token = join.json()["cancel_token"]

    bad = await client.delete(
        f"/api/v1/events/{event.id}/waitlist",
        params={"email": "leaver@example.com", "token": "wrong"},
    )
    assert bad.status_code == 403

    ok = await client.delete(
        f"/api/v1/events/{event.id}/waitlist",
        params={"email": "leaver@example.com", "token": token},
    )
    assert ok.status_code == 204


@pytest.mark.asyncio
async def test_cancellation_triggers_claim_token_for_first_waitlister(test_db, client, monkeypatch):
    """When a CONFIRMED registration is cancelled, the first WAITING patron
    on the new table is moved to NOTIFIED with a claim_token + 15min TTL.

    This is the load-bearing test for the new waitlist surface — if it ever
    starts skipping or returning a 0-row update, the feature is silently dead.
    Build all rows via ORM so we don't depend on POST /waitlist (which has the
    tz-aware now() check that fails on SQLite).
    """
    # Create the event + a single confirmed registration owned by a real User.
    event = await _create_open_event(test_db, max_attendees=1)
    from app.models.user import User, UserRole

    owner = User(
        email="owner@example.com",
        password_hash="x",
        role=UserRole.PATRON,
        is_active=True,
        first_name="Owner",
        last_name="Tester",
    )
    test_db.add(owner)
    await test_db.commit()
    await test_db.refresh(owner)

    confirmed = EventRegistration(
        event_id=event.id,
        patron_name="Owner",
        patron_email="owner@example.com",
        status=EventRegistrationStatus.CONFIRMED.value,
    )
    test_db.add(confirmed)
    # Build the waitlist entry directly — bypasses POST /waitlist's tz check.
    waiter = EventWaitlistEntry(
        event_id=event.id,
        email="waiter@example.com",
        name="Waiter",
        status=WaitlistStatus.WAITING.value,
        cancel_token="cancel-tok-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )
    test_db.add(waiter)
    await test_db.commit()
    await test_db.refresh(confirmed)
    await test_db.refresh(waiter)
    # Capture ids while objects are still attached — after expire_all() any
    # attribute access on `waiter`/`confirmed` triggers a sync lazy-load that
    # MissingGreenlet's under async.
    waiter_id = waiter.id
    confirmed_id = confirmed.id

    # Override get_current_user to return our owner so cancel_registration
    # passes its email-match authorization.
    from app.api.v1.auth import get_current_user
    from app.main import app as fastapi_app

    async def _override_user():
        return owner

    fastapi_app.dependency_overrides[get_current_user] = _override_user
    try:
        cancel = await client.delete(f"/api/v1/events/{event.id}/register/{confirmed_id}")
        assert cancel.status_code == 204, cancel.text

        # Re-read the waitlist row: must be NOTIFIED with a claim token.
        test_db.expire_all()
        res = await test_db.execute(
            EventWaitlistEntry.__table__.select().where(EventWaitlistEntry.id == waiter_id)
        )
        row = res.fetchone()
        assert row is not None
        m = dict(row._mapping)
        assert m["status"] == WaitlistStatus.NOTIFIED.value, m
        assert m["claim_token"], "claim_token must be set after cancellation"
        assert m["claim_token_expires_at"] is not None
        assert m["notified_at"] is not None
    finally:
        fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_claim_valid_token_promotes_and_expired_410(test_db, client, monkeypatch):
    # /claim itself does not compare event.start_time to now(); it only
    # checks claim_token_expires_at. Works on SQLite.
    event = await _create_open_event(test_db, max_attendees=1)

    # Build a NOTIFIED entry directly so we don't need the cancel path
    import secrets

    entry = EventWaitlistEntry(
        event_id=event.id,
        email="claimer@example.com",
        name="Claimer",
        status=WaitlistStatus.NOTIFIED.value,
        claim_token=secrets.token_urlsafe(32),
        claim_token_expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    test_db.add(entry)
    await test_db.commit()
    await test_db.refresh(entry)
    valid_token = entry.claim_token

    ok = await client.post(
        f"/api/v1/events/{event.id}/waitlist/claim",
        params={"token": valid_token},
    )
    assert ok.status_code == 201, ok.text

    # Expired flow
    expired = EventWaitlistEntry(
        event_id=event.id,
        email="lateclaimer@example.com",
        name="Late",
        status=WaitlistStatus.NOTIFIED.value,
        claim_token=secrets.token_urlsafe(32),
        claim_token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    test_db.add(expired)
    await test_db.commit()
    await test_db.refresh(expired)

    gone = await client.post(
        f"/api/v1/events/{event.id}/waitlist/claim",
        params={"token": expired.claim_token},
    )
    assert gone.status_code == 410


@pytest.mark.asyncio
async def test_per_event_ics_returns_calendar_mime_and_parses(test_db, client):
    # Per-event ICS path does not compare start_time to now() — it just
    # formats. Works on either backend.
    event = await _create_open_event(test_db)
    resp = await client.get(f"/api/v1/events/{event.id}/calendar.ics")
    assert resp.status_code == 200
    assert "text/calendar" in resp.headers["content-type"]
    body = resp.text
    assert body.startswith("BEGIN:VCALENDAR")
    assert "BEGIN:VEVENT" in body
    assert f"UID:event-{event.id}@" in body
    assert "END:VCALENDAR" in body
    assert "STATUS:CONFIRMED" in body


@pytest.mark.asyncio
async def test_feed_level_ics_includes_event(test_db, client):
    if _is_sqlite(test_db):
        # Feed-level endpoint filters Event.start_time >= now() which TypeErrors
        # on SQLite naive round-trip.
        pytest.skip("Feed-level uses tz-aware comparison; needs Postgres test DB")
    event = await _create_open_event(test_db)
    resp = await client.get("/api/v1/events/calendar.ics")
    assert resp.status_code == 200
    assert "text/calendar" in resp.headers["content-type"]
    assert f"UID:event-{event.id}@" in resp.text
