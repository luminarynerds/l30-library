# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for event-attendance reading-program credit (rp_event_credit_001)."""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.attendance import (
    AgeRange,
    AttendanceCheckIn,
    AttendanceSession,
    AttendanceSessionStatus,
    CheckInMethod,
)
from app.models.event import Event
from app.models.reading import (
    EventReadingProgramCredit,
    ReadingLogEntry,
    ReadingProgram,
    ReadingProgramType,
    ReadingRegistration,
)
from app.models.user import User, UserRole
from app.services.event_attendance_credit_service import (
    grant_event_attendance_credits,
)


@pytest.fixture
async def patron(test_db):
    user = User(
        email="rp-credit@example.com",
        password_hash="hashedpassword",
        first_name="Credit",
        last_name="Tester",
        role=UserRole.PATRON,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def program(test_db):
    p = ReadingProgram(
        name="Credit Test Program",
        description="Event-credit coverage",
        program_type=ReadingProgramType.summer,
        age_group="All Ages",
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=30),
        reading_goal_type="minutes",
        reading_goal_value=1000,
        is_active=True,
    )
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


@pytest.fixture
async def event(test_db):
    e = Event(
        title="Storytime Test",
        start_time=datetime.now(timezone.utc),
        is_published=True,
    )
    test_db.add(e)
    await test_db.commit()
    await test_db.refresh(e)
    return e


@pytest.fixture
async def session_for_event(test_db, event):
    s = AttendanceSession(
        event_id=event.id,
        session_name=event.title,
        session_date=date.today(),
        status=AttendanceSessionStatus.OPEN,
        qr_code_token=str(uuid.uuid4()).replace("-", "")[:24],
    )
    test_db.add(s)
    await test_db.commit()
    await test_db.refresh(s)
    return s


async def _make_check_in(test_db, session, patron_id):
    ci = AttendanceCheckIn(
        session_id=session.id,
        patron_id=patron_id,
        check_in_method=CheckInMethod.QR_CODE,
        age_range=AgeRange.UNKNOWN,
        is_repeat_attendee=False,
        previous_visit_count=0,
    )
    test_db.add(ci)
    await test_db.commit()
    await test_db.refresh(ci)
    return ci


@pytest.mark.asyncio
class TestGrantEventAttendanceCredits:
    async def test_grants_when_credit_and_registration_exist(
        self, test_db, patron, program, event, session_for_event
    ):
        test_db.add(
            ReadingRegistration(
                user_id=patron.id, program_id=program.id, goal_target=1000
            )
        )
        test_db.add(
            EventReadingProgramCredit(
                event_id=event.id, program_id=program.id, minutes_credit=30
            )
        )
        await test_db.commit()
        ci = await _make_check_in(test_db, session_for_event, patron.id)

        granted = await grant_event_attendance_credits(test_db, ci)
        await test_db.commit()

        assert len(granted) == 1
        assert granted[0].minutes_read == 30
        assert granted[0].source == "event_attendance"
        assert granted[0].source_event_id == event.id

    async def test_skips_when_no_registration(
        self, test_db, patron, program, event, session_for_event
    ):
        # Configure a credit but the patron is not registered in the program.
        test_db.add(
            EventReadingProgramCredit(
                event_id=event.id, program_id=program.id, minutes_credit=30
            )
        )
        await test_db.commit()
        ci = await _make_check_in(test_db, session_for_event, patron.id)

        granted = await grant_event_attendance_credits(test_db, ci)

        assert granted == []
        rows = (
            await test_db.execute(select(ReadingLogEntry))
        ).scalars().all()
        assert all(r.source_event_id != event.id for r in rows)

    async def test_idempotent_on_repeat_check_in(
        self, test_db, patron, program, event, session_for_event
    ):
        test_db.add(
            ReadingRegistration(
                user_id=patron.id, program_id=program.id, goal_target=1000
            )
        )
        test_db.add(
            EventReadingProgramCredit(
                event_id=event.id, program_id=program.id, minutes_credit=30
            )
        )
        await test_db.commit()
        ci_1 = await _make_check_in(test_db, session_for_event, patron.id)
        granted_1 = await grant_event_attendance_credits(test_db, ci_1)
        await test_db.commit()
        assert len(granted_1) == 1

        # Second check-in for the same patron + event must not double-credit.
        ci_2 = await _make_check_in(test_db, session_for_event, patron.id)
        granted_2 = await grant_event_attendance_credits(test_db, ci_2)
        await test_db.commit()

        assert granted_2 == []
        count = (
            await test_db.execute(
                select(ReadingLogEntry).where(
                    ReadingLogEntry.source_event_id == event.id
                )
            )
        ).scalars().all()
        assert len(count) == 1

    async def test_anonymous_check_in_is_noop(
        self, test_db, program, event, session_for_event
    ):
        test_db.add(
            EventReadingProgramCredit(
                event_id=event.id, program_id=program.id, minutes_credit=30
            )
        )
        await test_db.commit()
        ci = AttendanceCheckIn(
            session_id=session_for_event.id,
            patron_id=None,
            guest_name="Anonymous",
            check_in_method=CheckInMethod.WALK_IN,
            age_range=AgeRange.UNKNOWN,
            is_repeat_attendee=False,
            previous_visit_count=0,
        )
        test_db.add(ci)
        await test_db.commit()
        await test_db.refresh(ci)

        granted = await grant_event_attendance_credits(test_db, ci)
        assert granted == []
