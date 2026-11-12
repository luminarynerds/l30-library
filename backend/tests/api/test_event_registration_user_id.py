# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for user_id-based event registration ownership.

Covers:
  (a) A registration created while logged in is returned by my-registrations
      even after the user's email address changes.
  (b) Phone-only (email=NULL) registrations linked by user_id are returned.

These use ORM fixtures (no HTTP register path) so they work on either backend.
The my-registrations endpoint DOES require tz-aware datetimes (Event.start_time
>= now(utc)) so we skip on SQLite rather than fake the comparison.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.event import Event
from app.models.event_registration import EventRegistration, EventRegistrationStatus
from app.models.user import User, UserRole


def _is_sqlite(db) -> bool:
    try:
        return db.bind.dialect.name == "sqlite"
    except Exception:
        return False


async def _make_future_event(db) -> Event:
    n = datetime.now(timezone.utc)
    if _is_sqlite(db):
        n = n.replace(tzinfo=None)
    event = Event(
        title="Test Event",
        description="For user_id tests",
        start_time=n + timedelta(days=7),
        end_time=n + timedelta(days=7, hours=1),
        is_published=True,
        registration_required=True,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def _make_user(db, email: str) -> User:
    from app.core.security import hash_password

    user = User(
        email=email,
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="User",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# (a) Email-change stability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_my_registrations_survives_email_change(test_db, client):
    """A registration linked by user_id is returned after the patron's email
    address is changed — the email-only query would have lost this row."""
    if _is_sqlite(test_db):
        pytest.skip("my-registrations uses tz-aware now(); needs Postgres test DB")

    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    original_email = "original@example.com"
    user = await _make_user(test_db, original_email)
    event = await _make_future_event(test_db)

    # Register with user_id set (simulates a logged-in registration).
    reg = EventRegistration(
        event_id=event.id,
        patron_name=user.first_name,
        patron_email=original_email,
        user_id=user.id,
        status=EventRegistrationStatus.CONFIRMED.value,
    )
    test_db.add(reg)
    await test_db.commit()

    # Simulate email change — patron_email no longer matches current_user.email.
    user.email = "changed@example.com"
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    # Override get_current_user so the endpoint sees the updated user object.
    async def _override_get_current_user():
        return user

    async def _override_get_db():
        yield test_db

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_db] = _override_get_db
    app.state.setup_complete = True

    try:
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/events/my-registrations")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1, f"Expected 1 registration, got {len(body)}: {body}"
    assert body[0]["id"] == reg.id


# ---------------------------------------------------------------------------
# (b) Phone-only registrations linked by user_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_my_registrations_includes_phone_only_row_with_user_id(test_db, client):
    """A phone-only registration (patron_email IS NULL) linked via user_id
    is returned by my-registrations. The old email-only query never found these."""
    if _is_sqlite(test_db):
        pytest.skip("my-registrations uses tz-aware now(); needs Postgres test DB")

    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    user = await _make_user(test_db, "phone_user@example.com")
    event = await _make_future_event(test_db)

    reg = EventRegistration(
        event_id=event.id,
        patron_name="Phone Patron",
        patron_email=None,
        patron_phone="555-867-5309",
        user_id=user.id,
        status=EventRegistrationStatus.CONFIRMED.value,
    )
    test_db.add(reg)
    await test_db.commit()

    async def _override_get_current_user():
        return user

    async def _override_get_db():
        yield test_db

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_db] = _override_get_db
    app.state.setup_complete = True

    try:
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/events/my-registrations")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1, f"Expected 1 phone-only registration, got {len(body)}: {body}"
    assert body[0]["id"] == reg.id


# ---------------------------------------------------------------------------
# ORM-level: model accepts user_id (works on either backend)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_registration_model_persists_user_id(test_db):
    """EventRegistration.user_id column round-trips correctly."""
    n = datetime.now(timezone.utc)
    if _is_sqlite(test_db):
        n = n.replace(tzinfo=None)

    event = Event(
        title="user_id model test",
        start_time=n + timedelta(days=7),
        is_published=True,
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)

    user = await _make_user(test_db, "model_round_trip@example.com")

    reg = EventRegistration(
        event_id=event.id,
        patron_name="Round Trip",
        patron_email="model_round_trip@example.com",
        user_id=user.id,
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)

    assert reg.user_id == user.id

    # NULL user_id is also valid (anonymous registration).
    reg_anon = EventRegistration(
        event_id=event.id,
        patron_name="Anon",
        patron_phone="555-000-0000",
        patron_email=None,
        user_id=None,
    )
    test_db.add(reg_anon)
    await test_db.commit()
    await test_db.refresh(reg_anon)

    assert reg_anon.user_id is None
