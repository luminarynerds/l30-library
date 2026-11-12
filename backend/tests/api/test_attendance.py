# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API tests for the pre_registered check-in path.

Covers the gap left by the staff Roster (PR #569) -> mark-no-show (PR #574)
sequence: "Mark attended" used to fall back to a walk_in row because no
registration->check-in endpoint existed. The new endpoint (events.py) and
service method (attendance_service.check_in_pre_registered) wire the link
back via AttendanceCheckIn.registration_id with check_in_method='pre_registered'.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.attendance import (
    AttendanceCheckIn,
    AttendanceSession,
    AttendanceSessionStatus,
    CheckInMethod,
)
from app.models.event import Event
from app.models.event_registration import (
    EventRegistration,
    EventRegistrationStatus,
)
from app.models.user import User
from app.services.attendance_service import AttendanceService


# ============================================================================
# Helpers (mirrors test_events.py style — keep behaviour identical so the
# tz handling matches across DB drivers).
# ============================================================================


def _now_tz_aware_compat(db) -> datetime:
    n = datetime.now(timezone.utc)
    try:
        if db.bind.dialect.name == "sqlite":
            return n.replace(tzinfo=None)
    except Exception:
        pass
    return n


async def _create_event(db, **overrides) -> Event:
    start = _now_tz_aware_compat(db) + timedelta(days=1)
    defaults = dict(
        title="Pre-Reg Event",
        description="Test event for pre_registered check-in",
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


async def _create_registration(db, event_id: int, email: str = "patron@l.org") -> EventRegistration:
    reg = EventRegistration(
        event_id=event_id,
        patron_name="Pre-Reg Patron",
        patron_email=email.lower(),
        status=EventRegistrationStatus.CONFIRMED.value,
    )
    db.add(reg)
    await db.commit()
    await db.refresh(reg)
    return reg


async def _open_session(db, staff_id: int, event: Event) -> AttendanceSession:
    return await AttendanceService.create_session(
        db=db,
        session_name=event.title,
        session_date=event.start_time.date(),
        staff_id=staff_id,
        event_id=event.id,
    )


@pytest.fixture
def authed_client_factory(client):
    def _auth(user: User):
        app.dependency_overrides[get_current_user] = lambda: user
        return client

    yield _auth
    app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# Service-layer tests (direct, no HTTP)
# ============================================================================


@pytest.mark.asyncio
async def test_pre_registered_check_in_sets_method_and_registration_id(
    test_db, test_staff
):
    """check_in_pre_registered creates an AttendanceCheckIn with
    check_in_method=PRE_REGISTERED and registration_id set."""
    event = await _create_event(test_db)
    reg = await _create_registration(test_db, event.id)
    session = await _open_session(test_db, test_staff.id, event)
    await test_db.commit()

    check_in = await AttendanceService.check_in_pre_registered(
        db=test_db,
        session_id=session.id,
        registration_id=reg.id,
        staff_id=test_staff.id,
        guest_name=reg.patron_name,
        guest_email=reg.patron_email,
    )
    await test_db.commit()
    await test_db.refresh(check_in)

    method_value = (
        check_in.check_in_method.value
        if hasattr(check_in.check_in_method, "value")
        else check_in.check_in_method
    )
    assert method_value == "pre_registered"
    assert check_in.registration_id == reg.id
    assert check_in.session_id == session.id
    assert check_in.checked_in_by_id == test_staff.id

    # Rollup counter went to total_pre_registered, NOT total_walk_ins.
    await test_db.refresh(session)
    assert session.total_pre_registered == 1
    assert session.total_walk_ins == 0
    assert session.total_checked_in == 1


@pytest.mark.asyncio
async def test_walk_in_check_in_still_works_with_null_registration_id(
    test_db, test_staff
):
    """Regression guard: the existing walk_in path is untouched and
    registration_id stays NULL for walk-ins."""
    event = await _create_event(test_db)
    session = await _open_session(test_db, test_staff.id, event)
    await test_db.commit()

    check_in = await AttendanceService.check_in_walk_in(
        db=test_db,
        session_id=session.id,
        staff_id=test_staff.id,
        guest_name="Drop-In Patron",
        guest_email="dropin@l.org",
    )
    await test_db.commit()
    await test_db.refresh(check_in)

    method_value = (
        check_in.check_in_method.value
        if hasattr(check_in.check_in_method, "value")
        else check_in.check_in_method
    )
    assert method_value == "walk_in"
    assert check_in.registration_id is None
    assert check_in.guest_name == "Drop-In Patron"

    await test_db.refresh(session)
    assert session.total_walk_ins == 1
    assert session.total_pre_registered == 0


@pytest.mark.asyncio
async def test_pre_registered_check_in_is_idempotent(
    test_db, test_staff
):
    """Re-calling for the same (session, registration) returns the existing
    row without double-counting session totals."""
    event = await _create_event(test_db)
    reg = await _create_registration(test_db, event.id)
    session = await _open_session(test_db, test_staff.id, event)
    await test_db.commit()

    first = await AttendanceService.check_in_pre_registered(
        db=test_db,
        session_id=session.id,
        registration_id=reg.id,
        staff_id=test_staff.id,
    )
    await test_db.commit()

    second = await AttendanceService.check_in_pre_registered(
        db=test_db,
        session_id=session.id,
        registration_id=reg.id,
        staff_id=test_staff.id,
    )
    await test_db.commit()

    assert second.id == first.id

    await test_db.refresh(session)
    assert session.total_pre_registered == 1
    assert session.total_checked_in == 1
