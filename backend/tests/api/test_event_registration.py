# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 2 registration tests focused on photo_release_granted semantics.

These tests drive the full POST /events/{id}/register path. The endpoint
compares event.start_time to datetime.now(timezone.utc); on the SQLite
fallback start_time round-trips as naive and that comparison TypeErrors —
so we run the actual HTTP path tests only on Postgres, and run a unit-level
test of the photo_release pass-through on either backend.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.event import Event
from app.models.event_registration import EventRegistration


def _is_sqlite(db) -> bool:
    try:
        return db.bind.dialect.name == "sqlite"
    except Exception:
        return False


async def _create_event(test_db, *, photos_will_be_taken: bool) -> Event:
    """Create an event whose start_time matches the dialect's tz behavior."""
    n = datetime.now(timezone.utc)
    if _is_sqlite(test_db):
        n = n.replace(tzinfo=None)
    start = n + timedelta(days=7)
    event = Event(
        title="Phase 2 Event",
        description="Photo release test",
        start_time=start,
        end_time=start + timedelta(hours=1),
        is_published=True,
        registration_required=True,
        photos_will_be_taken=photos_will_be_taken,
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)
    return event


@pytest.mark.asyncio
async def test_register_with_photo_release_granted(
    test_db, client, monkeypatch
):
    """When event.photos_will_be_taken is True and patron consents,
    photo_release_granted is persisted as True (and False stays False)."""
    if _is_sqlite(test_db):
        pytest.skip(
            "Register endpoint compares tz-aware now() to start_time which "
            "rounds-trips naive on SQLite. Run with Postgres test DB to "
            "exercise the full HTTP path."
        )
    from app.api.v1 import events as events_module

    async def _fake_verify(*_args, **_kwargs):
        return True

    monkeypatch.setattr(events_module, "verify_turnstile", _fake_verify)

    event = await _create_event(test_db, photos_will_be_taken=True)

    resp = await client.post(
        f"/api/v1/events/{event.id}/register",
        json={
            "patron_name": "Yes Patron",
            "patron_email": "yes@example.com",
            "photo_release_granted": True,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["photo_release_granted"] is True

    resp2 = await client.post(
        f"/api/v1/events/{event.id}/register",
        json={
            "patron_name": "No Patron",
            "patron_email": "no@example.com",
            "photo_release_granted": False,
        },
    )
    assert resp2.status_code == 201, resp2.text
    assert resp2.json()["photo_release_granted"] is False


@pytest.mark.asyncio
async def test_register_photo_release_defaults_null_when_not_provided(
    test_db, client, monkeypatch
):
    """When the event does NOT take photos, photo_release_granted is NULL
    regardless of what the client sends — three-valued semantics."""
    if _is_sqlite(test_db):
        pytest.skip(
            "Register endpoint requires tz-aware datetimes; "
            "run with Postgres test DB."
        )
    from app.api.v1 import events as events_module

    async def _fake_verify(*_args, **_kwargs):
        return True

    monkeypatch.setattr(events_module, "verify_turnstile", _fake_verify)

    event = await _create_event(test_db, photos_will_be_taken=False)

    resp = await client.post(
        f"/api/v1/events/{event.id}/register",
        json={
            "patron_name": "Default Patron",
            "patron_email": "default@example.com",
            "photo_release_granted": True,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["photo_release_granted"] is None


@pytest.mark.asyncio
async def test_registration_create_schema_accepts_photo_release_granted():
    """Direct schema test — does not depend on DB dialect.

    Pins the Pydantic shape and three-valued default.
    """
    from app.schemas.event_registration import RegistrationCreate

    # Default is None ("not asked").
    a = RegistrationCreate(patron_name="A", patron_email="a@example.com")
    assert a.photo_release_granted is None

    # Explicit True / False stick.
    b = RegistrationCreate(
        patron_name="B", patron_email="b@example.com", photo_release_granted=True
    )
    assert b.photo_release_granted is True

    c = RegistrationCreate(
        patron_name="C", patron_email="c@example.com", photo_release_granted=False
    )
    assert c.photo_release_granted is False


@pytest.mark.asyncio
async def test_event_registration_model_round_trips_photo_release(test_db):
    """ORM-level round trip — works on either backend, pins the column."""
    n = datetime.now(timezone.utc)
    if _is_sqlite(test_db):
        n = n.replace(tzinfo=None)
    event = Event(
        title="Round trip",
        start_time=n + timedelta(days=7),
        is_published=True,
        photos_will_be_taken=True,
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)

    reg = EventRegistration(
        event_id=event.id,
        patron_name="Roundtrip",
        patron_email="rt@example.com",
        photo_release_granted=True,
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    assert reg.photo_release_granted is True

    reg2 = EventRegistration(
        event_id=event.id,
        patron_name="Null",
        patron_email="null@example.com",
        photo_release_granted=None,
    )
    test_db.add(reg2)
    await test_db.commit()
    await test_db.refresh(reg2)
    assert reg2.photo_release_granted is None


# ============================================================================
# Email-or-phone contact requirement (registration escape hatch). Patrons
# without email can register phone-only; neither contact method is a 422.
# ============================================================================


@pytest.mark.asyncio
async def test_registration_create_schema_requires_email_or_phone():
    """Direct schema test — does not depend on DB dialect."""
    from pydantic import ValidationError

    from app.schemas.event_registration import RegistrationCreate

    # Phone-only is valid.
    phone_only = RegistrationCreate(patron_name="P", patron_phone="555-867-5309")
    assert phone_only.patron_email is None

    # Email-only stays valid (the historical shape).
    email_only = RegistrationCreate(patron_name="E", patron_email="e@example.com")
    assert email_only.patron_phone is None

    # Neither is rejected.
    with pytest.raises(ValidationError):
        RegistrationCreate(patron_name="N")


@pytest.mark.asyncio
async def test_register_neither_contact_method_is_422(test_db, client):
    """HTTP path: missing both email and phone fails request validation
    (422) before the handler runs — works on either DB backend."""
    event = await _create_event(test_db, photos_will_be_taken=False)

    resp = await client.post(
        f"/api/v1/events/{event.id}/register",
        json={"patron_name": "No Contact"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_register_phone_only_succeeds(test_db, client, monkeypatch):
    """Phone-only registration persists with NULL email and skips the
    confirmation email path without erroring."""
    if _is_sqlite(test_db):
        pytest.skip(
            "Register endpoint requires tz-aware datetimes; "
            "run with Postgres test DB."
        )
    from app.api.v1 import events as events_module

    async def _fake_verify(*_args, **_kwargs):
        return True

    monkeypatch.setattr(events_module, "verify_turnstile", _fake_verify)

    event = await _create_event(test_db, photos_will_be_taken=False)

    resp = await client.post(
        f"/api/v1/events/{event.id}/register",
        json={"patron_name": "Phone Patron", "patron_phone": "555-867-5309"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["patron_email"] is None
    assert body["patron_phone"] == "555-867-5309"
    assert body["status"] == "confirmed"

    # Same phone again is a duplicate (phone-keyed dedup for phone-only).
    resp2 = await client.post(
        f"/api/v1/events/{event.id}/register",
        json={"patron_name": "Phone Patron", "patron_phone": "555-867-5309"},
    )
    assert resp2.status_code == 409, resp2.text


@pytest.mark.asyncio
async def test_event_registration_model_allows_null_email(test_db):
    """ORM-level: patron_email column is nullable (phone-only rows)."""
    n = datetime.now(timezone.utc)
    if _is_sqlite(test_db):
        n = n.replace(tzinfo=None)
    event = Event(
        title="Phone only",
        start_time=n + timedelta(days=7),
        is_published=True,
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)

    reg = EventRegistration(
        event_id=event.id,
        patron_name="Phone Patron",
        patron_email=None,
        patron_phone="555-867-5309",
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    assert reg.patron_email is None
    assert reg.patron_phone == "555-867-5309"
