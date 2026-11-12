# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, timedelta

import pytest

from app.models.reading import ReadingProgram, ReadingProgramType
from app.services.patron_onboarding_service import check_summer_reading_active


@pytest.mark.asyncio
async def test_check_summer_reading_active_uses_db_programs(test_db):
    program = ReadingProgram(
        name="Summer Reading",
        description="Seasonal challenge",
        program_type=ReadingProgramType.summer,
        start_date=date.today() - timedelta(days=2),
        end_date=date.today() + timedelta(days=20),
        is_active=True,
    )
    test_db.add(program)
    await test_db.commit()

    assert await check_summer_reading_active(test_db) is True


@pytest.mark.asyncio
async def test_check_summer_reading_active_false_when_no_program(test_db):
    assert await check_summer_reading_active(test_db) is False
