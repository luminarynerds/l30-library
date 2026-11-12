# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression net for /api/v1/staff/schedule/today (see issue #803).

The endpoint filters Program rows by program_date == date.today(). Three demo
rows had been seeded with mismatched (date, day-of-week-in-notes) values; that
is fixed in alembic revision fix_recurring_program_dow_001.

These tests don't exercise the migration itself -- they pin the endpoint
contract that the data fix relies on: a program whose program_date matches
today appears in the response; one with a different date does not.
"""

from datetime import date, time, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.models.program import Program, ProgramStatus


@pytest.mark.asyncio
class TestStaffScheduleToday:
    """Regression net for the today-on-desk filter contract."""

    async def test_only_returns_programs_with_program_date_today(
        self, staff_client: AsyncClient, test_db
    ):
        """A program on today's date should appear; one on another date should not."""
        # Make sure no other programs pollute the result (other tests / seeded data).
        await test_db.execute(delete(Program))
        await test_db.commit()

        today = date.today()
        tomorrow = today + timedelta(days=1)

        on_today = Program(
            title="Recurring Demo (today)",
            program_type="book_club",
            audience="adult",
            program_date=today,
            start_time=time(13, 0),
            end_time=time(14, 0),
            location_name="Meeting Room A",
            status=ProgramStatus.SCHEDULED,
            notes="Wednesdays. Should appear on today's desk schedule.",
        )
        not_today = Program(
            title="Recurring Demo (tomorrow)",
            program_type="book_club",
            audience="adult",
            program_date=tomorrow,
            start_time=time(13, 0),
            end_time=time(14, 0),
            location_name="Meeting Room A",
            status=ProgramStatus.SCHEDULED,
            notes="Wednesdays. Should NOT appear today.",
        )
        test_db.add_all([on_today, not_today])
        await test_db.commit()

        response = await staff_client.get("/api/v1/staff/schedule/today")
        assert response.status_code == 200, response.text
        titles = [item["title"] for item in response.json()["items"]]
        assert "Recurring Demo (today)" in titles
        assert "Recurring Demo (tomorrow)" not in titles

    async def test_excludes_completed_and_cancelled_programs(
        self, staff_client: AsyncClient, test_db
    ):
        """Only planned/scheduled/in_progress programs surface on the desk."""
        await test_db.execute(delete(Program))
        await test_db.commit()

        today = date.today()
        scheduled = Program(
            title="Visible scheduled",
            program_type="book_club",
            audience="adult",
            program_date=today,
            start_time=time(10, 0),
            status=ProgramStatus.SCHEDULED,
        )
        completed = Program(
            title="Hidden completed",
            program_type="book_club",
            audience="adult",
            program_date=today,
            start_time=time(11, 0),
            status=ProgramStatus.COMPLETED,
        )
        cancelled = Program(
            title="Hidden cancelled",
            program_type="book_club",
            audience="adult",
            program_date=today,
            start_time=time(12, 0),
            status=ProgramStatus.CANCELLED,
        )
        test_db.add_all([scheduled, completed, cancelled])
        await test_db.commit()

        response = await staff_client.get("/api/v1/staff/schedule/today")
        assert response.status_code == 200, response.text
        titles = [item["title"] for item in response.json()["items"]]
        assert "Visible scheduled" in titles
        assert "Hidden completed" not in titles
        assert "Hidden cancelled" not in titles
