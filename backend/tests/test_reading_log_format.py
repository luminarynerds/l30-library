# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the reading_log_entries.format column added in rp_log_format_001."""

from datetime import date, timedelta

import pytest

from app.models.reading import (
    ReadingLogEntry,
    ReadingLogFormat,
    ReadingProgram,
    ReadingProgramType,
    ReadingRegistration,
)
from app.models.user import User, UserRole


@pytest.fixture
async def patron(test_db):
    user = User(
        email="format-test@example.com",
        password_hash="hashedpassword",
        first_name="Format",
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
        name="Format Test Program",
        description="Format coverage",
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


@pytest.mark.asyncio
class TestReadingLogFormat:
    async def test_enum_values_stable(self):
        # Spec-level lock so a careless rename of an enum value is caught here.
        assert {f.value for f in ReadingLogFormat} == {
            "print",
            "large_print",
            "ebook",
            "audiobook",
            "braille",
        }

    async def test_default_when_omitted_is_print(self, test_db, registration):
        entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=1,
            minutes_read=30,
            pages_read=20,
        )
        test_db.add(entry)
        await test_db.commit()
        await test_db.refresh(entry)
        # server_default of the column kicks in for omitted writes
        assert entry.format == "print"

    async def test_audiobook_round_trips(self, test_db, registration):
        entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=0,
            minutes_read=45,
            pages_read=0,
            format=ReadingLogFormat.audiobook.value,
        )
        test_db.add(entry)
        await test_db.commit()
        await test_db.refresh(entry)
        assert entry.format == "audiobook"

    async def test_braille_round_trips(self, test_db, registration):
        entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=0,
            minutes_read=20,
            pages_read=15,
            format=ReadingLogFormat.braille.value,
        )
        test_db.add(entry)
        await test_db.commit()
        await test_db.refresh(entry)
        assert entry.format == "braille"
