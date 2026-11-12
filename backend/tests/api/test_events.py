# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API tests covering the 2026-05-15 events.py backend correctness fixes.

Bugs fixed (see PR description):
  1. cancel_registration: authorization no longer trusts a query string.
  2. Self-shadowed literal routes (/moderation/queue, /reviews/stats, etc.)
     are now reachable.
  3. Duplicate-registration race is closed by a partial unique index +
     IntegrityError handler returning 409.
  5. PLS attendance fallback no longer counts EventRegistration rows.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.event import Event
from app.models.event_registration import (
    EventRegistration,
    EventRegistrationStatus,
)
from app.models.user import User, UserRole


# ============================================================================
# Helpers
# ============================================================================


def _now_tz_aware_compat(db) -> datetime:
    """Return a UTC `now` whose tz-awareness matches what the underlying
    DB driver will surface on read. SQLite/aiosqlite (used as the test
    fallback) strips tzinfo round-trip; asyncpg/Postgres preserves it.
    Tests that do an Event() insert then re-read it must use the same
    flavor or `<=` comparisons throw TypeError."""
    n = datetime.now(timezone.utc)
    try:
        if db.bind.dialect.name == "sqlite":
            return n.replace(tzinfo=None)
    except Exception:
        pass
    return n


async def _create_published_event(db, **overrides) -> Event:
    """Create a published, registration-required event in the future."""
    start = _now_tz_aware_compat(db) + timedelta(days=7)
    defaults = dict(
        title="Test Event",
        description="Test event for events.py regression tests",
        start_time=start,
        end_time=start + timedelta(hours=1),
        location="Main Library",
        is_published=True,
        registration_required=True,
        max_attendees=10,
    )
    defaults.update(overrides)
    event = Event(**defaults)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def _create_registration(
    db, event_id: int, email: str, status: str | None = None
) -> EventRegistration:
    reg = EventRegistration(
        event_id=event_id,
        patron_name="Test Patron",
        patron_email=email.lower(),
        status=status or EventRegistrationStatus.CONFIRMED.value,
    )
    db.add(reg)
    await db.commit()
    await db.refresh(reg)
    return reg


@pytest.fixture
def authed_client_factory(client):
    """Return a helper that authenticates the test client as `user`."""

    def _auth(user: User):
        app.dependency_overrides[get_current_user] = lambda: user
        return client

    yield _auth
    app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# Bug 1: cancel_registration authorization
# ============================================================================


@pytest.mark.asyncio
async def test_cancel_registration_rejects_other_users_email(
    test_db, authed_client_factory, test_patron, test_admin_data
):
    """A patron MUST NOT be able to cancel another patron's registration even
    if they know the registered email. The pre-fix endpoint authorized by
    comparing a query string to the registration row; this test pins the new
    behavior that authorization comes from current_user only."""
    from app.core.security import hash_password

    # Owner of the registration
    owner = User(
        email="owner@example.com",
        password_hash=hash_password("ownerpass123!"),
        first_name="Owner",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(owner)
    await test_db.commit()
    await test_db.refresh(owner)

    event = await _create_published_event(test_db)
    reg = await _create_registration(test_db, event.id, owner.email)

    # The attacker is `test_patron`, NOT the registration owner.
    c = authed_client_factory(test_patron)
    resp = await c.delete(
        f"/api/v1/events/{event.id}/register/{reg.id}",
    )
    assert resp.status_code == 403, resp.text

    # Re-fetch: registration must still be CONFIRMED.
    await test_db.refresh(reg)
    assert reg.status == EventRegistrationStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_cancel_registration_owner_succeeds(
    test_db, authed_client_factory, test_patron
):
    """The patron who registered (matched on lowercased email) can cancel."""
    event = await _create_published_event(test_db)
    # Use mixed-case email to also pin the case-insensitive match.
    reg = await _create_registration(
        test_db, event.id, test_patron.email.upper()
    )

    c = authed_client_factory(test_patron)
    resp = await c.delete(f"/api/v1/events/{event.id}/register/{reg.id}")
    assert resp.status_code in (200, 204), resp.text

    await test_db.refresh(reg)
    assert reg.status == EventRegistrationStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_cancel_registration_staff_bypass(
    test_db, authed_client_factory, test_staff
):
    """Staff role can cancel any registration."""
    event = await _create_published_event(test_db)
    reg = await _create_registration(test_db, event.id, "someone@example.com")

    c = authed_client_factory(test_staff)
    resp = await c.delete(f"/api/v1/events/{event.id}/register/{reg.id}")
    assert resp.status_code in (200, 204), resp.text

    await test_db.refresh(reg)
    assert reg.status == EventRegistrationStatus.CANCELLED.value


# ============================================================================
# Bug 2: literal moderation/review routes no longer shadowed by /{event_id}
# ============================================================================


@pytest.mark.asyncio
async def test_moderation_queue_route_is_reachable(
    authed_client_factory, test_staff
):
    """GET /api/v1/events/moderation/queue used to be intercepted by
    GET /api/v1/events/{event_id} (which 422'd because "moderation" is
    not an int). It must now hit the moderation handler and return 200."""
    c = authed_client_factory(test_staff)
    resp = await c.get("/api/v1/events/moderation/queue")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    # Standard PaginatedResponse[ReviewModerationQueue]
    assert "data" in payload
    assert isinstance(payload["data"], list)


@pytest.mark.asyncio
async def test_reviews_stats_route_is_reachable(
    authed_client_factory, test_staff
):
    """GET /api/v1/events/reviews/stats must hit the stats handler, not
    /{event_id}."""
    c = authed_client_factory(test_staff)
    resp = await c.get("/api/v1/events/reviews/stats")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "by_status" in payload
    assert "removed_count" in payload


# ============================================================================
# Bug 3: concurrent same-patron registration blocked by unique index
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_registration_one_patron_blocked_by_unique_index(
    test_db, client, monkeypatch
):
    """Concurrent same-patron registrations must not both insert. With the
    partial unique index in place, the second insert raises IntegrityError;
    the register endpoint catches it and returns 409.

    We can't true-concurrency in a single asyncio test, so we drive the API
    twice: the first call wins, the second hits the duplicate path. The
    duplicate must come back as a clean 409 (not 500, not 201).

    Postgres is required for partial unique indexes — SQLite supports them
    but our conftest test DB doesn't reliably apply the alembic head to the
    SQLite fallback. We skip when not on Postgres so this is a pure-behavior
    pin that will exercise the index whenever Postgres is reachable.
    """
    from app.api.v1 import events as events_module
    from app.core.database import engine as app_engine  # type: ignore

    try:
        dialect = app_engine.sync_engine.dialect.name
    except Exception:
        dialect = ""
    if dialect != "postgresql":
        pytest.skip(
            "Partial unique index requires the test run to be on PostgreSQL; "
            "the alembic-applied index isn't present on the SQLite fallback. "
            "Re-run with TEST_DATABASE_URL pointing at l30_test on Postgres."
        )

    async def _fake_verify(*_args, **_kwargs):
        return True

    monkeypatch.setattr(events_module, "verify_turnstile", _fake_verify)

    event = await _create_published_event(test_db, max_attendees=100)
    email = "patron@example.com"

    payload = {
        "patron_name": "Patron",
        "patron_email": email,
        "turnstile_token": "ignored-in-test",
        "reminder_requested": False,
        "accommodation_requested": False,
    }
    resp1 = await client.post(f"/api/v1/events/{event.id}/register", json=payload)
    assert resp1.status_code == 201, resp1.text

    payload["patron_email"] = email.upper()  # case mismatch must still 409
    resp2 = await client.post(f"/api/v1/events/{event.id}/register", json=payload)
    assert resp2.status_code == 409, resp2.text


@pytest.mark.asyncio
async def test_duplicate_registration_status_code_is_409(test_db, client):
    """Pin the status-code contract: a duplicate registration returns 409
    (was 400). We can't drive the register endpoint without hitting a
    pre-existing SQLite tz-naive vs tz-aware bug at events.py:start_time
    comparison, so this asserts the exception class signature in the
    handler directly to lock the value in.
    """
    import re
    from pathlib import Path

    events_src = Path(
        __file__
    ).parent.parent.parent.joinpath("app/api/v1/events.py").read_text()
    # The duplicate-check branch must raise 409 (HTTP_409_CONFLICT)
    # and the IntegrityError catch must raise 409.
    duplicate_block = re.search(
        r"if existing\.scalar_one_or_none\(\):\s*raise HTTPException\(\s*status_code=([^,]+)",
        events_src,
    )
    assert duplicate_block is not None, "duplicate-check branch not found"
    assert "409" in duplicate_block.group(1) or "CONFLICT" in duplicate_block.group(1), (
        f"duplicate-registration pre-check must return 409, got {duplicate_block.group(1)}"
    )

    integrity_block = re.search(
        r"except IntegrityError:.*?raise HTTPException\(\s*status_code=([^,]+)",
        events_src,
        re.DOTALL,
    )
    assert integrity_block is not None, "IntegrityError handler not found"
    assert "409" in integrity_block.group(1) or "CONFLICT" in integrity_block.group(1), (
        f"IntegrityError handler must return 409, got {integrity_block.group(1)}"
    )


# ============================================================================
# Bug 5: PLS attendance uses attended_count / AttendanceSession, not regs
# ============================================================================


@pytest.mark.asyncio
async def test_pls_attendance_uses_attended_count_not_registrations(
    test_db,
):
    """PLS / IMLS report ATTENDANCE, not registration signups. The legacy
    fallback in usage_statistics_service used to count EventRegistration
    rows, which inflates by counting cancelled, waitlisted, no-show, and
    future-but-registered patrons. New behavior:
        1. Prefer Event.attended_count when set.
        2. Else sum AttendanceSession.total_checked_in.
        3. Else 0 — NEVER fall back to registration counts.
    """
    from datetime import date

    from app.services.usage_statistics_service import UsageStatisticsService

    # Past event window
    start = _now_tz_aware_compat(test_db) - timedelta(days=2)
    event = Event(
        title="Past event",
        start_time=start,
        end_time=start + timedelta(hours=1),
        is_published=True,
        registration_required=True,
        max_attendees=100,
        attended_count=4,  # staff recorded 4 actual attendees
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)

    # Add 9 registrations including cancelled, waitlisted, confirmed.
    for i, status_ in enumerate(
        [EventRegistrationStatus.CONFIRMED.value] * 4
        + [EventRegistrationStatus.WAITLISTED.value] * 3
        + [EventRegistrationStatus.CANCELLED.value] * 2
    ):
        test_db.add(
            EventRegistration(
                event_id=event.id,
                patron_name=f"P{i}",
                patron_email=f"p{i}@example.com",
                status=status_,
            )
        )
    await test_db.commit()

    svc = UsageStatisticsService(test_db)
    stats = await svc.generate_program_statistics(
        period_start=date.today() - timedelta(days=7),
        period_end=date.today() + timedelta(days=1),
        period_type="weekly",
    )

    # 4 attended (from attended_count), not 9 (registration count).
    assert stats.total_program_attendance == 4, (
        f"expected 4 attendees from Event.attended_count, "
        f"got {stats.total_program_attendance}"
    )


@pytest.mark.asyncio
async def test_pls_attendance_falls_back_to_attendance_sessions(test_db):
    """If attended_count is NULL but an AttendanceSession exists, sum
    total_checked_in from that session."""
    from datetime import date

    from app.models.attendance import (
        AttendanceSession,
        AttendanceSessionStatus,
    )
    from app.services.usage_statistics_service import UsageStatisticsService

    start = _now_tz_aware_compat(test_db) - timedelta(days=1)
    event = Event(
        title="Past event with attendance session",
        start_time=start,
        end_time=start + timedelta(hours=1),
        is_published=True,
        registration_required=False,
        # attended_count intentionally NULL
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)

    session = AttendanceSession(
        event_id=event.id,
        session_name="Door count",
        session_date=date.today() - timedelta(days=1),
        status=AttendanceSessionStatus.CLOSED.value
        if hasattr(AttendanceSessionStatus.CLOSED, "value")
        else AttendanceSessionStatus.CLOSED,
        qr_code_token="test-token-pls-1",
        total_checked_in=7,
    )
    test_db.add(session)
    await test_db.commit()

    # Plus 20 stale registrations that should NOT be counted as attendance.
    for i in range(20):
        test_db.add(
            EventRegistration(
                event_id=event.id,
                patron_name=f"P{i}",
                patron_email=f"sess{i}@example.com",
                status=EventRegistrationStatus.CONFIRMED.value,
            )
        )
    await test_db.commit()

    svc = UsageStatisticsService(test_db)
    stats = await svc.generate_program_statistics(
        period_start=date.today() - timedelta(days=7),
        period_end=date.today() + timedelta(days=1),
        period_type="weekly",
    )

    assert stats.total_program_attendance == 7, (
        f"expected 7 from AttendanceSession.total_checked_in, "
        f"got {stats.total_program_attendance}"
    )


# ============================================================================
# Phase 2: age range, partner organization, recurrence_rule, photo release
# ============================================================================


@pytest.mark.asyncio
async def test_event_create_with_age_range_validates_min_le_max(
    test_db, authed_client_factory, test_admin
):
    """Valid age range (min <= max) is accepted and persisted."""
    c = authed_client_factory(test_admin)
    start = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=14, hours=1)).isoformat()
    resp = await c.post(
        "/api/v1/events",
        json={
            "title": "Tween Book Club",
            "start_time": start,
            "end_time": end,
            "min_age": 8,
            "max_age": 12,
            "caregiver_required": False,
        },
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert body["min_age"] == 8
    assert body["max_age"] == 12


@pytest.mark.asyncio
async def test_event_create_rejects_invalid_age_range_with_422(
    test_db, authed_client_factory, test_admin
):
    """min_age > max_age must produce a 422, not a DB-level 500."""
    c = authed_client_factory(test_admin)
    start = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=14, hours=1)).isoformat()
    resp = await c.post(
        "/api/v1/events",
        json={
            "title": "Bad Age Range",
            "start_time": start,
            "end_time": end,
            "min_age": 12,
            "max_age": 8,
        },
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_event_create_with_program_partner_id(
    test_db, authed_client_factory, test_admin
):
    """Event accepts program_partner_id FK and round-trips it."""
    from app.models.event_program_partner import EventProgramPartner

    partner = EventProgramPartner(
        name="Test Partner", slug="test_partner", is_active=True
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)

    c = authed_client_factory(test_admin)
    start = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=14, hours=1)).isoformat()
    resp = await c.post(
        "/api/v1/events",
        json={
            "title": "Co-Hosted Event",
            "start_time": start,
            "end_time": end,
            "program_partner_id": partner.id,
        },
    )
    assert resp.status_code in (200, 201), resp.text
    assert resp.json()["program_partner_id"] == partner.id


@pytest.mark.asyncio
async def test_event_create_with_recurrence_rule_persists(
    test_db, authed_client_factory, test_admin
):
    """recurrence_rule round-trips on create; not expanded at this layer."""
    c = authed_client_factory(test_admin)
    start = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=14, hours=1)).isoformat()
    rrule = "FREQ=WEEKLY;BYDAY=TU;UNTIL=20260815T120000Z"
    resp = await c.post(
        "/api/v1/events",
        json={
            "title": "Weekly Storytime",
            "start_time": start,
            "end_time": end,
            "recurrence_rule": rrule,
        },
    )
    assert resp.status_code in (200, 201), resp.text
    assert resp.json()["recurrence_rule"] == rrule


# ============================================================================
# Accommodation acknowledgment: persistence + RegistrationResponse exposure
# (2026-05-15: schema fields missing meant the staff Roster UI re-showed the
# Acknowledge button after a hard refresh.)
# ============================================================================


# ============================================================================
# Mark no-show endpoint
# ============================================================================


@pytest.mark.asyncio
async def test_acknowledge_accommodation_persists_at_and_by(
    test_db, authed_client_factory, test_staff
):
    """POST acknowledge-accommodation writes BOTH accommodation_acknowledged_at
    and accommodation_acknowledged_by (= current_user.id) to the row."""
    event = await _create_published_event(test_db)
    reg = EventRegistration(
        event_id=event.id,
        patron_name="Accom Patron",
        patron_email="accom@example.com",
        status=EventRegistrationStatus.CONFIRMED.value,
        accommodation_requested=True,
        accommodation_details="Wheelchair access",
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    assert reg.accommodation_acknowledged_at is None
    assert reg.accommodation_acknowledged_by is None

    c = authed_client_factory(test_staff)
    resp = await c.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/acknowledge-accommodation"
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(reg)
    assert reg.accommodation_acknowledged_at is not None
    assert reg.accommodation_acknowledged_by == test_staff.id


@pytest.mark.asyncio
async def test_registration_response_exposes_accommodation_ack_fields(
    test_db, authed_client_factory, test_staff
):
    """GET /events/{id}/registrations returns accommodation_acknowledged_at +
    accommodation_acknowledged_by so the staff Roster UI can render the
    'Acknowledged' state across page refreshes (not just session-local)."""
    event = await _create_published_event(test_db)
    ack_time = _now_tz_aware_compat(test_db)
    reg = EventRegistration(
        event_id=event.id,
        patron_name="Already Acked",
        patron_email="acked@example.com",
        status=EventRegistrationStatus.CONFIRMED.value,
        accommodation_requested=True,
        accommodation_details="Sign language interpreter",
        accommodation_acknowledged_at=ack_time,
        accommodation_acknowledged_by=test_staff.id,
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)

    c = authed_client_factory(test_staff)
    resp = await c.get(f"/api/v1/events/{event.id}/registrations")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    rows = body["registrations"]
    row = next(r for r in rows if r["id"] == reg.id)
    assert "accommodation_acknowledged_at" in row
    assert "accommodation_acknowledged_by" in row
    assert row["accommodation_acknowledged_at"] is not None
    assert row["accommodation_acknowledged_by"] == test_staff.id


# ============================================================================
# Mark no-show endpoint
# ============================================================================


async def test_mark_no_show_sets_status(
    test_db, authed_client_factory, test_staff
):
    """POST mark-no-show flips status from confirmed → no_show and 200s."""
    event = await _create_published_event(test_db)
    reg = await _create_registration(test_db, event.id, "patron@l.org")

    c = authed_client_factory(test_staff)
    resp = await c.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/mark-no-show",
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == reg.id
    assert body["status"] == EventRegistrationStatus.NO_SHOW.value

    await test_db.refresh(reg)
    assert reg.status == EventRegistrationStatus.NO_SHOW.value


@pytest.mark.asyncio
async def test_mark_no_show_is_idempotent(
    test_db, authed_client_factory, test_staff
):
    """Re-calling on an already-no_show registration returns 200, not an error."""
    event = await _create_published_event(test_db)
    reg = await _create_registration(
        test_db,
        event.id,
        "patron@l.org",
        status=EventRegistrationStatus.NO_SHOW.value,
    )

    c = authed_client_factory(test_staff)
    resp = await c.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/mark-no-show",
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == EventRegistrationStatus.NO_SHOW.value


@pytest.mark.asyncio
async def test_mark_no_show_requires_staff(
    test_db, authed_client_factory, test_patron, client
):
    """Anonymous → 401 (no current_user); patron-role → 403."""
    event = await _create_published_event(test_db)
    reg = await _create_registration(test_db, event.id, "patron@l.org")

    # Anonymous: no auth override applied → get_current_user raises 401.
    resp = await client.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/mark-no-show",
    )
    assert resp.status_code == 401, resp.text

    # Patron role: passes get_current_user, fails require_staff → 403.
    c = authed_client_factory(test_patron)
    resp = await c.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/mark-no-show",
    )
    assert resp.status_code == 403, resp.text

    await test_db.refresh(reg)
    assert reg.status == EventRegistrationStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_mark_no_show_validates_event_id_match(
    test_db, authed_client_factory, test_staff
):
    """Registration exists but belongs to a different event → 422."""
    event_a = await _create_published_event(test_db, title="Event A")
    event_b = await _create_published_event(test_db, title="Event B")
    reg = await _create_registration(test_db, event_a.id, "patron@l.org")

    c = authed_client_factory(test_staff)
    resp = await c.post(
        f"/api/v1/events/{event_b.id}/registrations/{reg.id}/mark-no-show",
    )
    assert resp.status_code == 422, resp.text

    await test_db.refresh(reg)
    assert reg.status == EventRegistrationStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_mark_no_show_returns_404_for_missing_registration(
    test_db, authed_client_factory, test_staff
):
    """Bonus: missing registration → 404 (not 422)."""
    event = await _create_published_event(test_db)

    c = authed_client_factory(test_staff)
    resp = await c.post(
        f"/api/v1/events/{event.id}/registrations/999999/mark-no-show",
    )
    assert resp.status_code == 404, resp.text


# ============================================================================
# GET /events?expand_recurrence: virtual-instance expansion via RRULE
# ============================================================================


async def _create_recurring_published_event(db, **overrides) -> Event:
    """Like `_create_published_event` but force tz-aware times.

    The list endpoint compares stored `start_time` to `datetime.now(utc)`
    in Python (for the past-events review average), which TypeErrors on
    SQLite when start_time is naive. The handler's tz-awareness here is
    a pre-existing limitation; we sidestep it in tests by inserting
    tz-aware start_times directly.
    """
    start = overrides.pop("start_time", None) or (
        datetime.now(timezone.utc) + timedelta(days=2)
    )
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    end = overrides.pop("end_time", None) or (start + timedelta(hours=1))
    if end is not None and end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    defaults = dict(
        title="Test Event",
        description="Test event for events.py recurrence-expansion tests",
        location="Main Library",
        is_published=True,
        registration_required=False,
    )
    defaults.update(overrides)
    event = Event(start_time=start, end_time=end, **defaults)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@pytest.mark.asyncio
async def test_get_events_expand_recurrence_returns_virtual_instances(
    test_db, client
):
    """FREQ=WEEKLY;COUNT=4 should return 4 virtual instances when expanded."""
    await _create_recurring_published_event(
        test_db,
        title="Weekly Storytime",
        recurrence_rule="FREQ=WEEKLY;COUNT=4",
    )

    resp = await client.get("/api/v1/events?expand_recurrence=true")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    rows = body["data"]
    assert len(rows) == 4, [r["start_time"] for r in rows]
    # All four rows should be virtual instances with id=None.
    assert all(r["id"] is None for r in rows)
    assert all(r["is_virtual_instance"] is True for r in rows)
    # All four share the same parent_event_id (the recurring source row).
    parent_ids = {r["parent_event_id"] for r in rows}
    assert len(parent_ids) == 1
    assert next(iter(parent_ids)) is not None


@pytest.mark.asyncio
async def test_get_events_default_no_expansion(test_db, client):
    """Without expand_recurrence the recurring parent appears as a single row."""
    await _create_recurring_published_event(
        test_db,
        title="Weekly Storytime",
        recurrence_rule="FREQ=WEEKLY;COUNT=4",
    )

    resp = await client.get("/api/v1/events")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # One persisted parent row, NOT four expanded rows.
    rows = body["data"]
    assert len(rows) == 1
    assert rows[0]["id"] is not None
    assert rows[0].get("is_virtual_instance") is False
    assert rows[0]["recurrence_rule"] == "FREQ=WEEKLY;COUNT=4"


@pytest.mark.asyncio
async def test_get_events_mixed_recurring_and_one_time_sorted_by_start_time(
    test_db, client
):
    """A mix of one-time and recurring events comes back sorted by start_time."""
    rec_start = datetime.now(timezone.utc) + timedelta(days=2)
    await _create_recurring_published_event(
        test_db,
        title="Weekly Storytime",
        start_time=rec_start,
        recurrence_rule="FREQ=WEEKLY;COUNT=3",
    )

    # One-time event sandwiched between the 2nd and 3rd recurrence.
    one_off_start = datetime.now(timezone.utc) + timedelta(days=12)
    await _create_recurring_published_event(
        test_db,
        title="Author Talk",
        start_time=one_off_start,
    )

    resp = await client.get(
        "/api/v1/events?expand_recurrence=true&per_page=50"
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]
    # 3 virtual instances + 1 one-time = 4 rows total.
    assert len(rows) == 4
    starts = [r["start_time"] for r in rows]
    assert starts == sorted(starts), starts
    # And the one-time event lands between the 2nd and 3rd recurrence.
    titles_in_order = [r["title"] for r in rows]
    assert titles_in_order.index("Author Talk") == 2


@pytest.mark.asyncio
async def test_get_events_expand_horizon_caps_at_183_days(test_db, client):
    """UNTIL beyond the 183-day horizon must be clipped to the window."""
    # UNTIL is far in 2030 → 183-day window will cap the expansion.
    await _create_recurring_published_event(
        test_db,
        title="Weekly Storytime",
        recurrence_rule="FREQ=WEEKLY;UNTIL=20300101T120000Z",
    )

    resp = await client.get(
        "/api/v1/events?expand_recurrence=true&per_page=100"
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]
    # Weekly within ~183 days = ~26 occurrences (starting 2 days out). Hard
    # upper bound is ceil(183/7)+1 = 27. Lower bound is floor(181/7) = 25.
    assert 25 <= len(rows) <= 27, len(rows)
    # All within horizon: parse the last instance and assert <= horizon.
    last_start = datetime.fromisoformat(rows[-1]["start_time"].replace("Z", "+00:00"))
    if last_start.tzinfo is None:
        last_start = last_start.replace(tzinfo=timezone.utc)
    horizon = datetime.now(timezone.utc) + timedelta(days=183)
    assert last_start <= horizon

# Roster "Mark attended" -> pre_registered check-in
# ============================================================================


@pytest.mark.asyncio
async def test_mark_attended_via_roster_creates_pre_registered_check_in(
    test_db, authed_client_factory, test_staff
):
    """POST /events/{id}/registrations/{rid}/check-in creates an
    AttendanceCheckIn with check_in_method='pre_registered' linked back to
    the registration (and rolls up total_pre_registered, NOT walk_ins)."""
    from sqlalchemy import select
    from app.models.attendance import AttendanceCheckIn, AttendanceSession

    event = await _create_published_event(test_db)
    reg = await _create_registration(test_db, event.id, "patron@l.org")

    c = authed_client_factory(test_staff)
    resp = await c.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/check-in",
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["registration_id"] == reg.id
    assert body["check_in_method"] == "pre_registered"

    # Persisted row has FK + method set.
    result = await test_db.execute(
        select(AttendanceCheckIn).where(AttendanceCheckIn.id == body["id"])
    )
    check_in = result.scalar_one()
    method_value = (
        check_in.check_in_method.value
        if hasattr(check_in.check_in_method, "value")
        else check_in.check_in_method
    )
    assert method_value == "pre_registered"
    assert check_in.registration_id == reg.id

    # Rollup correctness: counted as pre_registered, not walk_in.
    sresult = await test_db.execute(
        select(AttendanceSession).where(AttendanceSession.id == body["session_id"])
    )
    session = sresult.scalar_one()
    assert session.total_pre_registered == 1
    assert session.total_walk_ins == 0


@pytest.mark.asyncio
async def test_mark_attended_is_idempotent(
    test_db, authed_client_factory, test_staff
):
    """Re-posting for the same registration returns the existing check-in
    and does not double-count the session totals."""
    from sqlalchemy import select
    from app.models.attendance import AttendanceSession

    event = await _create_published_event(test_db)
    reg = await _create_registration(test_db, event.id, "patron@l.org")

    c = authed_client_factory(test_staff)
    r1 = await c.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/check-in",
    )
    r2 = await c.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/check-in",
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]

    sresult = await test_db.execute(
        select(AttendanceSession).where(AttendanceSession.id == r1.json()["session_id"])
    )
    session = sresult.scalar_one()
    assert session.total_pre_registered == 1


@pytest.mark.asyncio
async def test_mark_attended_validates_event_id_match(
    test_db, authed_client_factory, test_staff
):
    """Registration belongs to a different event → 422."""
    event_a = await _create_published_event(test_db, title="Event A")
    event_b = await _create_published_event(test_db, title="Event B")
    reg = await _create_registration(test_db, event_a.id, "patron@l.org")

    c = authed_client_factory(test_staff)
    resp = await c.post(
        f"/api/v1/events/{event_b.id}/registrations/{reg.id}/check-in",
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_mark_attended_returns_404_for_missing_registration(
    test_db, authed_client_factory, test_staff
):
    """Missing registration → 404 (not 422)."""
    event = await _create_published_event(test_db)

    c = authed_client_factory(test_staff)
    resp = await c.post(
        f"/api/v1/events/{event.id}/registrations/999999/check-in",
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_mark_attended_requires_staff(
    test_db, authed_client_factory, test_patron, client
):
    """Anonymous → 401; patron-role → 403."""
    event = await _create_published_event(test_db)
    reg = await _create_registration(test_db, event.id, "patron@l.org")

    resp = await client.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/check-in",
    )
    assert resp.status_code == 401, resp.text

    c = authed_client_factory(test_patron)
    resp = await c.post(
        f"/api/v1/events/{event.id}/registrations/{reg.id}/check-in",
    )
    assert resp.status_code == 403, resp.text

# ============================================================================
# Bulk-create recurring series: POST /events/bulk-from-recurrence
# (2026-05-15 — parent + N real children with parent_event_id; see PR for caps)
# ============================================================================

from sqlalchemy import select as _bulk_select  # local alias to avoid clashing
from app.models.event import Event as _BulkEvent


def _bulk_payload(
    *,
    start: datetime,
    end: datetime,
    rrule: str = "FREQ=WEEKLY;BYDAY=TU;COUNT=4",
    dry_run: bool = False,
    **overrides,
) -> dict:
    body = {
        "title": "Weekly Storytime",
        "description": "Bulk-create test",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "location": "Main Library",
        "audience": "All ages",
        "category": "Story Time",
        "registration_required": True,
        "max_attendees": 20,
        "recurrence_rule": rrule,
        "dry_run": dry_run,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_bulk_from_recurrence_creates_parent_and_children(
    test_db, authed_client_factory, test_admin
):
    """Real-create path: parent gets the RRULE, children get parent_event_id
    and recurrence_rule=NULL. Inherited fields are copied to every child."""
    c = authed_client_factory(test_admin)
    start = datetime.now(timezone.utc) + timedelta(days=7)
    end = start + timedelta(hours=1)
    resp = await c.post(
        "/api/v1/events/bulk-from-recurrence",
        json=_bulk_payload(start=start, end=end, rrule="FREQ=WEEKLY;BYDAY=TU;COUNT=4"),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["count"] == 4
    assert isinstance(body["parent_id"], int)
    assert len(body["child_ids"]) == 4

    # Verify shape in DB: parent has rule, children have parent_event_id.
    parent = (
        await test_db.execute(_bulk_select(_BulkEvent).where(_BulkEvent.id == body["parent_id"]))
    ).scalar_one()
    assert parent.recurrence_rule == "FREQ=WEEKLY;BYDAY=TU;COUNT=4"
    assert parent.parent_event_id is None

    children = (
        await test_db.execute(
            _bulk_select(_BulkEvent).where(_BulkEvent.parent_event_id == parent.id)
        )
    ).scalars().all()
    assert len(children) == 4
    for ch in children:
        assert ch.recurrence_rule is None
        assert ch.parent_event_id == parent.id
        assert ch.title == "Weekly Storytime"
        assert ch.location == "Main Library"
        assert ch.max_attendees == 20
        assert ch.registration_required is True


@pytest.mark.asyncio
async def test_bulk_from_recurrence_dry_run_returns_count_no_writes(
    test_db, authed_client_factory, test_admin
):
    """dry_run=True returns expansion preview without inserting any rows."""
    # Snapshot row count before the call.
    before = (
        await test_db.execute(_bulk_select(_BulkEvent))
    ).scalars().all()
    n_before = len(before)

    c = authed_client_factory(test_admin)
    start = datetime.now(timezone.utc) + timedelta(days=10)
    end = start + timedelta(hours=1)
    resp = await c.post(
        "/api/v1/events/bulk-from-recurrence",
        json=_bulk_payload(
            start=start,
            end=end,
            rrule="FREQ=WEEKLY;BYDAY=TU;COUNT=6",
            dry_run=True,
        ),
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert body["count"] == 6
    assert len(body["instances"]) == 6
    assert body["first_start"] is not None
    assert body["last_start"] is not None
    assert body["first_start"] <= body["last_start"]

    # No new events written.
    after = (
        await test_db.execute(_bulk_select(_BulkEvent))
    ).scalars().all()
    assert len(after) == n_before


@pytest.mark.asyncio
async def test_bulk_from_recurrence_invalid_rule_returns_422(
    test_db, authed_client_factory, test_admin
):
    """Garbage RRULE → clean 422, not a 500."""
    c = authed_client_factory(test_admin)
    start = datetime.now(timezone.utc) + timedelta(days=7)
    end = start + timedelta(hours=1)
    resp = await c.post(
        "/api/v1/events/bulk-from-recurrence",
        json=_bulk_payload(start=start, end=end, rrule="THIS-IS-NOT-AN-RRULE"),
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_bulk_from_recurrence_over_52_returns_422(
    test_db, authed_client_factory, test_admin
):
    """Expansion above 52 occurrences → 422 referencing the cap."""
    c = authed_client_factory(test_admin)
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(hours=1)
    # 60 weekly occurrences > 52.
    resp = await c.post(
        "/api/v1/events/bulk-from-recurrence",
        json=_bulk_payload(start=start, end=end, rrule="FREQ=WEEKLY;COUNT=60"),
    )
    assert resp.status_code == 422, resp.text
    assert "52" in resp.text


@pytest.mark.asyncio
async def test_bulk_from_recurrence_caps_at_366d_horizon(
    test_db, authed_client_factory, test_admin
):
    """Unbounded daily rule must not blow past the 366d horizon AND its
    expansion (>366 occurrences) must trip the 52-row cap. Either way, no
    rows are created and the response is 422."""
    before = (await test_db.execute(_bulk_select(_BulkEvent))).scalars().all()
    n_before = len(before)

    c = authed_client_factory(test_admin)
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(hours=1)
    # No COUNT, no UNTIL: relies on the in-endpoint horizon cap + 52-row cap.
    resp = await c.post(
        "/api/v1/events/bulk-from-recurrence",
        json=_bulk_payload(start=start, end=end, rrule="FREQ=DAILY"),
    )
    assert resp.status_code == 422, resp.text

    after = (await test_db.execute(_bulk_select(_BulkEvent))).scalars().all()
    assert len(after) == n_before, "horizon-capped path must NOT create rows"


@pytest.mark.asyncio
async def test_bulk_from_recurrence_atomic_on_failure(
    test_db, authed_client_factory, test_admin, monkeypatch
):
    """If the Nth insert fails, NO parent and NO children must persist."""
    before = (await test_db.execute(_bulk_select(_BulkEvent))).scalars().all()
    n_before = len(before)

    # Patch AsyncSession.flush to fail on the second invocation (children flush).
    from sqlalchemy.ext.asyncio import AsyncSession as _AS

    orig_flush = _AS.flush
    call_count = {"n": 0}

    async def flaky_flush(self, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("simulated failure mid-bulk-create")
        return await orig_flush(self, *args, **kwargs)

    monkeypatch.setattr(_AS, "flush", flaky_flush)

    c = authed_client_factory(test_admin)
    start = datetime.now(timezone.utc) + timedelta(days=14)
    end = start + timedelta(hours=1)
    resp = await c.post(
        "/api/v1/events/bulk-from-recurrence",
        json=_bulk_payload(start=start, end=end, rrule="FREQ=WEEKLY;COUNT=4"),
    )
    # Endpoint surfaces InternalServerError as 5xx.
    assert resp.status_code >= 500, resp.text

    # No rows should remain — atomicity proof.
    after = (await test_db.execute(_bulk_select(_BulkEvent))).scalars().all()
    assert len(after) == n_before


@pytest.mark.asyncio
async def test_bulk_from_recurrence_requires_staff(
    test_db, client, authed_client_factory, test_patron
):
    """Anonymous → 401. Patron → 403. Staff-or-admin only."""
    start = datetime.now(timezone.utc) + timedelta(days=14)
    end = start + timedelta(hours=1)
    body = _bulk_payload(start=start, end=end)

    # Anonymous
    resp = await client.post("/api/v1/events/bulk-from-recurrence", json=body)
    assert resp.status_code == 401, resp.text

    # Patron role
    c = authed_client_factory(test_patron)
    resp = await c.post("/api/v1/events/bulk-from-recurrence", json=body)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_bulk_from_recurrence_children_inherit_accessibility_fields(
    test_db, authed_client_factory, test_admin
):
    """Accessibility flags + notes on the request body propagate to every
    child row, not just the parent."""
    c = authed_client_factory(test_admin)
    start = datetime.now(timezone.utc) + timedelta(days=21)
    end = start + timedelta(hours=1)
    resp = await c.post(
        "/api/v1/events/bulk-from-recurrence",
        json=_bulk_payload(
            start=start,
            end=end,
            rrule="FREQ=WEEKLY;COUNT=3",
            wheelchair_accessible=True,
            asl_provided=True,
            captioning_provided=False,
            assistive_listening=True,
            sensory_friendly=True,
            large_print_available=True,
            accessibility_notes="Quiet room available on request",
            photos_will_be_taken=True,
            min_age=3,
            max_age=8,
            caregiver_required=True,
        ),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    parent_id = body["parent_id"]
    children = (
        await test_db.execute(
            _bulk_select(_BulkEvent).where(_BulkEvent.parent_event_id == parent_id)
        )
    ).scalars().all()
    assert len(children) == 3
    for ch in children:
        assert ch.wheelchair_accessible is True
        assert ch.asl_provided is True
        assert ch.captioning_provided is False
        assert ch.assistive_listening is True
        assert ch.sensory_friendly is True
        assert ch.large_print_available is True
        assert ch.accessibility_notes == "Quiet room available on request"
        assert ch.photos_will_be_taken is True
        assert ch.min_age == 3
        assert ch.max_age == 8
        assert ch.caregiver_required is True


# ============================================================================
# GET /events filtering: time window, drop-in, accessibility provisions
# (PR2 — patron events filtering. The matching quick chips / filter panel
#  were re-wired here after PR #1101 removed the dead, unwired controls.)
# ============================================================================


async def _create_event_at(db, *, title: str, start_offset_days: int, **overrides) -> Event:
    """Create a published, tz-aware future event `start_offset_days` out.

    tz-aware on purpose: the list endpoint compares start_time to
    datetime.now(utc), which TypeErrors on the SQLite fallback when the
    stored value is naive (see _create_recurring_published_event)."""
    start = datetime.now(timezone.utc) + timedelta(days=start_offset_days)
    defaults = dict(
        title=title,
        start_time=start,
        end_time=start + timedelta(hours=1),
        is_published=True,
        registration_required=True,
    )
    defaults.update(overrides)
    event = Event(**defaults)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@pytest.mark.asyncio
async def test_list_events_starts_before_caps_window(test_db, client):
    """`starts_before` excludes events that start after the given instant."""
    await _create_event_at(test_db, title="Soon", start_offset_days=1)
    await _create_event_at(test_db, title="Later", start_offset_days=10)

    cutoff = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    # pass via params= so httpx encodes the `+00:00` offset (a raw `+` in the
    # query string would be decoded back to a space and fail validation).
    resp = await client.get("/api/v1/events", params={"starts_before": cutoff})
    assert resp.status_code == 200, resp.text
    titles = [r["title"] for r in resp.json()["data"]]
    assert titles == ["Soon"], titles


@pytest.mark.asyncio
async def test_list_events_starts_after_floors_window(test_db, client):
    """`starts_after` excludes events that start before the given instant."""
    await _create_event_at(test_db, title="Soon", start_offset_days=1)
    await _create_event_at(test_db, title="Later", start_offset_days=10)

    floor = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    resp = await client.get("/api/v1/events", params={"starts_after": floor})
    assert resp.status_code == 200, resp.text
    titles = [r["title"] for r in resp.json()["data"]]
    assert titles == ["Later"], titles


@pytest.mark.asyncio
async def test_list_events_drop_in_excludes_registration_events(test_db, client):
    """`drop_in=true` returns only events with registration_required=False."""
    await _create_event_at(
        test_db, title="Sign Up", start_offset_days=2, registration_required=True
    )
    await _create_event_at(
        test_db, title="Walk In", start_offset_days=3, registration_required=False
    )

    resp = await client.get("/api/v1/events?drop_in=true")
    assert resp.status_code == 200, resp.text
    titles = [r["title"] for r in resp.json()["data"]]
    assert titles == ["Walk In"], titles


@pytest.mark.asyncio
async def test_list_events_accessibility_single_provision(test_db, client):
    """A single `accessibility` token returns events with that flag set."""
    await _create_event_at(
        test_db, title="Ramp", start_offset_days=2, wheelchair_accessible=True
    )
    await _create_event_at(
        test_db, title="ASL", start_offset_days=3, asl_provided=True
    )
    await _create_event_at(test_db, title="Plain", start_offset_days=4)

    resp = await client.get("/api/v1/events?accessibility=wheelchair_accessible")
    assert resp.status_code == 200, resp.text
    titles = {r["title"] for r in resp.json()["data"]}
    assert titles == {"Ramp"}, titles


@pytest.mark.asyncio
async def test_list_events_accessibility_multiple_is_and_semantics(test_db, client):
    """Multiple `accessibility` tokens require ALL provisions (AND)."""
    await _create_event_at(
        test_db,
        title="Both",
        start_offset_days=2,
        wheelchair_accessible=True,
        asl_provided=True,
    )
    await _create_event_at(
        test_db,
        title="WheelchairOnly",
        start_offset_days=3,
        wheelchair_accessible=True,
        asl_provided=False,
    )

    resp = await client.get(
        "/api/v1/events?accessibility=wheelchair_accessible&accessibility=asl_provided"
    )
    assert resp.status_code == 200, resp.text
    titles = [r["title"] for r in resp.json()["data"]]
    assert titles == ["Both"], titles


@pytest.mark.asyncio
async def test_list_events_accessibility_unknown_token_ignored(test_db, client):
    """An unknown `accessibility` token is dropped, not 500'd — a stale or
    hand-edited client must never break the list endpoint."""
    await _create_event_at(test_db, title="Plain", start_offset_days=2)

    resp = await client.get("/api/v1/events?accessibility=not_a_real_column")
    assert resp.status_code == 200, resp.text
    titles = [r["title"] for r in resp.json()["data"]]
    assert titles == ["Plain"], titles


# ============================================================================
# GET /events filtering: program language (event_language, OR semantics)
# ============================================================================


@pytest.mark.asyncio
async def test_list_events_language_single(test_db, client):
    """`languages=es` returns only events conducted in Spanish."""
    await _create_event_at(
        test_db, title="Cuentos", start_offset_days=2, event_language="es"
    )
    await _create_event_at(
        test_db, title="Story Time", start_offset_days=3, event_language="en"
    )
    await _create_event_at(test_db, title="Unspecified", start_offset_days=4)

    resp = await client.get("/api/v1/events?languages=es")
    assert resp.status_code == 200, resp.text
    titles = {r["title"] for r in resp.json()["data"]}
    assert titles == {"Cuentos"}, titles


@pytest.mark.asyncio
async def test_list_events_language_multiple_is_or_semantics(test_db, client):
    """Multiple `languages` values match ANY (OR), mirroring `audiences`."""
    await _create_event_at(
        test_db, title="Cuentos", start_offset_days=2, event_language="es"
    )
    await _create_event_at(
        test_db, title="Gushi", start_offset_days=3, event_language="zh"
    )
    await _create_event_at(
        test_db, title="Story Time", start_offset_days=4, event_language="en"
    )

    resp = await client.get("/api/v1/events?languages=es&languages=zh")
    assert resp.status_code == 200, resp.text
    titles = {r["title"] for r in resp.json()["data"]}
    assert titles == {"Cuentos", "Gushi"}, titles


@pytest.mark.asyncio
async def test_list_events_language_in_public_response(test_db, client):
    """event_language is exposed on the public list payload (not sensitive)."""
    await _create_event_at(
        test_db, title="Cuentos", start_offset_days=2, event_language="es"
    )

    resp = await client.get("/api/v1/events")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["data"] if r["title"] == "Cuentos")
    assert row["event_language"] == "es"


# ============================================================================
# GET /events filtering: hosting branch (branch_ids, OR semantics)
# ============================================================================


async def _create_branch(db, *, name: str):
    from app.models.multi_branch import Branch, LibrarySystem

    system = (
        await db.execute(_bulk_select(LibrarySystem).limit(1))
    ).scalar_one_or_none()
    if system is None:
        system = LibrarySystem(code="TST", name="Test System")
        db.add(system)
        await db.flush()
    branch = Branch(
        library_system_id=system.id,
        code=name[:10].upper().replace(" ", ""),
        name=name,
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch


@pytest.mark.asyncio
async def test_list_events_branch_filter_single(test_db, client):
    """`branch_ids=N` returns only events hosted at that branch; events with
    no branch assigned are excluded while the filter is active."""
    main = await _create_branch(test_db, name="Main Library")
    north = await _create_branch(test_db, name="North Branch")
    await _create_event_at(
        test_db, title="At Main", start_offset_days=2, branch_id=main.id
    )
    await _create_event_at(
        test_db, title="At North", start_offset_days=3, branch_id=north.id
    )
    await _create_event_at(test_db, title="No Branch", start_offset_days=4)

    resp = await client.get(f"/api/v1/events?branch_ids={main.id}")
    assert resp.status_code == 200, resp.text
    titles = {r["title"] for r in resp.json()["data"]}
    assert titles == {"At Main"}, titles


@pytest.mark.asyncio
async def test_list_events_branch_filter_multiple_is_or_semantics(test_db, client):
    """Multiple `branch_ids` values match ANY (OR), mirroring `audiences`."""
    main = await _create_branch(test_db, name="Main Library")
    north = await _create_branch(test_db, name="North Branch")
    south = await _create_branch(test_db, name="South Branch")
    await _create_event_at(
        test_db, title="At Main", start_offset_days=2, branch_id=main.id
    )
    await _create_event_at(
        test_db, title="At North", start_offset_days=3, branch_id=north.id
    )
    await _create_event_at(
        test_db, title="At South", start_offset_days=4, branch_id=south.id
    )

    resp = await client.get(
        f"/api/v1/events?branch_ids={main.id}&branch_ids={north.id}"
    )
    assert resp.status_code == 200, resp.text
    titles = {r["title"] for r in resp.json()["data"]}
    assert titles == {"At Main", "At North"}, titles


@pytest.mark.asyncio
async def test_list_events_branch_id_and_name_in_public_response(test_db, client):
    """branch_id and the resolved branch_name are exposed on the public list
    payload; branchless events carry nulls."""
    main = await _create_branch(test_db, name="Main Library")
    await _create_event_at(
        test_db, title="At Main", start_offset_days=2, branch_id=main.id
    )
    await _create_event_at(test_db, title="No Branch", start_offset_days=3)

    resp = await client.get("/api/v1/events")
    assert resp.status_code == 200, resp.text
    rows = {r["title"]: r for r in resp.json()["data"]}
    assert rows["At Main"]["branch_id"] == main.id
    assert rows["At Main"]["branch_name"] == "Main Library"
    assert rows["No Branch"]["branch_id"] is None
    assert rows["No Branch"]["branch_name"] is None


@pytest.mark.asyncio
async def test_get_event_detail_exposes_branch_name(test_db, client):
    """The single-event endpoint resolves branch_name too."""
    main = await _create_branch(test_db, name="Main Library")
    event = await _create_event_at(
        test_db, title="At Main", start_offset_days=2, branch_id=main.id
    )

    resp = await client.get(f"/api/v1/events/{event.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["branch_id"] == main.id
    assert body["branch_name"] == "Main Library"


# ============================================================================
# Structured sensory fields (events review enhancement #2): lighting,
# noise_level, crowd_size, quiet_space_available — staff-set descriptors that
# let sensory-sensitive patrons pre-assess an event.
# ============================================================================


@pytest.mark.asyncio
async def test_event_create_with_sensory_fields_persists(
    test_db, authed_client_factory, test_admin
):
    """Valid sensory descriptors round-trip on create."""
    c = authed_client_factory(test_admin)
    start = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=14, hours=1)).isoformat()
    resp = await c.post(
        "/api/v1/events",
        json={
            "title": "Sensory-Friendly Storytime",
            "start_time": start,
            "end_time": end,
            "lighting": "dim",
            "noise_level": "quiet",
            "crowd_size": "small",
            "quiet_space_available": True,
        },
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert body["lighting"] == "dim"
    assert body["noise_level"] == "quiet"
    assert body["crowd_size"] == "small"
    assert body["quiet_space_available"] is True


@pytest.mark.asyncio
async def test_event_create_lowercases_sensory_value(
    test_db, authed_client_factory, test_admin
):
    """Mixed-case sensory input is normalised to the lowercase vocabulary."""
    c = authed_client_factory(test_admin)
    start = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=14, hours=1)).isoformat()
    resp = await c.post(
        "/api/v1/events",
        json={
            "title": "Loud Concert",
            "start_time": start,
            "end_time": end,
            "noise_level": "LIVELY",
            "crowd_size": "Large",
        },
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert body["noise_level"] == "lively"
    assert body["crowd_size"] == "large"


@pytest.mark.asyncio
async def test_event_create_rejects_invalid_sensory_value_with_422(
    test_db, authed_client_factory, test_admin
):
    """A value outside the fixed vocabulary is a 422, not a DB-level 500."""
    c = authed_client_factory(test_admin)
    start = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=14, hours=1)).isoformat()
    resp = await c.post(
        "/api/v1/events",
        json={
            "title": "Bad Lighting",
            "start_time": start,
            "end_time": end,
            "lighting": "neon",
        },
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_event_update_rejects_invalid_sensory_value_with_422(
    test_db, authed_client_factory, test_admin
):
    """The same vocabulary guard applies on the staff update (PUT) path."""
    event = await _create_published_event(test_db)
    c = authed_client_factory(test_admin)
    resp = await c.put(
        f"/api/v1/events/{event.id}",
        json={"crowd_size": "enormous"},
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# _ical_fold UTF-8 boundary safety (L30-BACKEND-5)
# ---------------------------------------------------------------------------


def test_ical_fold_handles_multibyte_lead_at_boundary():
    """RFC 5545 fold must not split UTF-8 multibyte sequences.

    L30-BACKEND-5 fired when an event description put an em-dash (U+2014,
    UTF-8 \xe2\x80\x94) such that its lead byte landed at byte 75 -- the
    fold boundary. The walk-back only stripped trailing continuation bytes
    and left the lone lead byte; the resulting \xe2\r\n \x80\x94 byte
    sequence then failed UTF-8 decode.
    """
    from app.api.v1.events import _ical_fold

    prefix = "DESCRIPTION:"
    padding = "x" * (75 - len(prefix) - 1)  # \xe2 lands at byte 75
    line = prefix + padding + "\u2014 copies available for purchase."

    encoded = line.encode("utf-8")
    assert encoded[74] == 0xE2, "test setup: em-dash lead must be at byte 75"

    # Pre-fix this raised UnicodeDecodeError; post-fix it returns the folded line.
    folded = _ical_fold(line)
    assert "\u2014" in folded  # em-dash preserved
    # And the fold boundary moved the whole codepoint to the continuation line.
    head, tail = folded.split("\r\n ", 1)
    assert "\u2014" not in head
    assert tail.startswith("\u2014")
