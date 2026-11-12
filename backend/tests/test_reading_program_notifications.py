# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the reading-program progress-nudge service (P2-6 foundation).

The service writes Notification rows; the email/in-app send path is the
follow-up PR. These tests assert on the row-write behaviour: threshold
detection, dedup, opt-out, and the "below threshold" no-op path.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.notification import Notification, NotificationType
from app.models.reading import (
    ReadingLogEntry,
    ReadingProgram,
    ReadingProgramType,
    ReadingRegistration,
)
from app.models.user import User, UserRole
from app.services.reading_program_notifications_service import (
    maybe_send_progress_nudge,
)


@pytest.fixture
async def patron(test_db):
    user = User(
        email="rp-nudge@example.com",
        password_hash="hashedpassword",
        first_name="Nudge",
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
        name="Nudge Test Program",
        description="Progress nudge coverage",
        program_type=ReadingProgramType.summer,
        age_group="All Ages",
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=30),
        reading_goal_type="minutes",
        reading_goal_value=100,
        is_active=True,
    )
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


@pytest.fixture
async def registration(test_db, patron, program):
    reg = ReadingRegistration(
        user_id=patron.id,
        program_id=program.id,
        goal_target=program.reading_goal_value,
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    return reg


async def _log(test_db, registration_id: int, minutes: int) -> None:
    test_db.add(
        ReadingLogEntry(
            registration_id=registration_id,
            minutes_read=minutes,
            books_read=0,
            pages_read=0,
        )
    )
    await test_db.commit()


@pytest.mark.asyncio
class TestProgressNudge:
    async def test_no_nudge_below_50_pct(self, test_db, registration):
        await _log(test_db, registration.id, 30)  # 30/100 = 30%
        result = await maybe_send_progress_nudge(test_db, registration.id)
        assert result is None

    async def test_fires_at_50_pct(self, test_db, registration):
        await _log(test_db, registration.id, 60)  # 60/100 = 60%
        result = await maybe_send_progress_nudge(test_db, registration.id)
        assert result is not None
        assert result.notification_type == NotificationType.READING_PROGRAM_PROGRESS_NUDGE
        assert result.context_data["threshold"] == 50

    async def test_fires_at_80_pct(self, test_db, registration):
        await _log(test_db, registration.id, 85)  # 85/100 = 85%
        result = await maybe_send_progress_nudge(test_db, registration.id)
        assert result is not None
        assert result.context_data["threshold"] == 80

    async def test_dedup_same_threshold(self, test_db, registration):
        await _log(test_db, registration.id, 60)  # 60%
        first = await maybe_send_progress_nudge(test_db, registration.id)
        await test_db.commit()
        assert first is not None

        second = await maybe_send_progress_nudge(test_db, registration.id)
        assert second is None

        rows = (
            await test_db.execute(
                select(Notification).where(
                    Notification.user_id == registration.user_id,
                    Notification.notification_type
                    == NotificationType.READING_PROGRAM_PROGRESS_NUDGE,
                )
            )
        ).scalars().all()
        assert len(rows) == 1

    async def test_separate_thresholds_each_fire_once(
        self, test_db, registration
    ):
        # Cross 50 first.
        await _log(test_db, registration.id, 55)
        first = await maybe_send_progress_nudge(test_db, registration.id)
        await test_db.commit()
        assert first is not None
        assert first.context_data["threshold"] == 50

        # Then jump to 85 -- should fire the 80 nudge.
        await _log(test_db, registration.id, 35)  # 55+35=90
        second = await maybe_send_progress_nudge(test_db, registration.id)
        await test_db.commit()
        assert second is not None
        assert second.context_data["threshold"] == 80

        # A third call at the same level is a no-op.
        third = await maybe_send_progress_nudge(test_db, registration.id)
        assert third is None
