# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test for /youth/upcoming-events TIME serialization.

The DB declares `programs.start_time` / `programs.end_time` as TIME columns,
which SQLAlchemy returns as `datetime.time`. The Pydantic schema declares
both as `str`, so under Pydantic v2 strict mode the route used to raise
``ValidationError`` and silently return ``[]`` due to its top-level
``except Exception``. This test pins the HH:MM serialization contract.
"""

from datetime import date, time, timedelta

import pytest

from app.models.program import Program, ProgramStatus


@pytest.fixture
async def teen_program(test_db):
    p = Program(
        title="Teen Storytime",
        description="Test program",
        program_type="storytime",
        audience="teen",
        program_date=date.today() + timedelta(days=7),
        start_time=time(16, 0),
        end_time=time(17, 0),
        location_name="Lobby",
        max_capacity=20,
        status=ProgramStatus.PLANNED,
    )
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


@pytest.fixture
async def teen_program_no_end_time(test_db):
    p = Program(
        title="Teen Drop-in",
        description="Test program with no end time",
        program_type="drop_in",
        audience="teen",
        program_date=date.today() + timedelta(days=8),
        start_time=time(9, 30),
        end_time=None,
        location_name="Lobby",
        status=ProgramStatus.SCHEDULED,
    )
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


@pytest.mark.asyncio
async def test_upcoming_events_serializes_times_as_hhmm(client, teen_program):
    resp = await client.get("/api/v1/youth/upcoming-events")
    assert resp.status_code == 200
    data = resp.json()
    event = next((e for e in data if e["title"] == "Teen Storytime"), None)
    assert event is not None, f"Teen Storytime not in response: {data}"
    assert event["start_time"] == "16:00"
    assert event["end_time"] == "17:00"


@pytest.mark.asyncio
async def test_upcoming_events_null_end_time_serializes_to_none(
    client, teen_program_no_end_time
):
    resp = await client.get("/api/v1/youth/upcoming-events")
    assert resp.status_code == 200
    data = resp.json()
    event = next((e for e in data if e["title"] == "Teen Drop-in"), None)
    assert event is not None
    assert event["start_time"] == "09:30"
    assert event["end_time"] is None
