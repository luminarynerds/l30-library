# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for summer reading launch automation endpoint."""

from datetime import date, timedelta

import pytest

from app.models.reading import PrizeType, ReadingPrize, ReadingProgram, ReadingProgramType


@pytest.fixture
async def source_summer_program(test_db):
    """Create a source summer program with one prize template."""
    program = ReadingProgram(
        name="Summer Reading Challenge 2025",
        description="Last year's summer reading challenge.",
        program_type=ReadingProgramType.summer,
        age_group="All Ages",
        start_date=date.today() - timedelta(days=365),
        end_date=date.today() - timedelta(days=300),
        reading_goal_type="books",
        reading_goal_value=10,
        is_active=False,
    )
    test_db.add(program)
    await test_db.flush()

    prize = ReadingPrize(
        program_id=program.id,
        name="Free Book",
        description="Pick a free book from the prize cart.",
        prize_type=PrizeType.PHYSICAL,
        prize_value="$10",
        threshold_type="books",
        threshold_value=5,
        quantity_available=100,
        quantity_redeemed=20,
        is_active=False,
        available_from=program.start_date,
        available_until=program.end_date,
        sort_order=1,
    )
    test_db.add(prize)
    await test_db.commit()
    await test_db.refresh(program)
    return program


@pytest.mark.asyncio
async def test_launch_summer_reading_automation_clones_program_and_prizes(
    client,
    test_admin,
    test_admin_data,
    source_summer_program,
):
    """Staff can launch summer reading automation from a previous program."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_admin_data["email"], "password": test_admin_data["password"]},
    )
    token = login_response.json()["access_token"]

    new_start = date.today() + timedelta(days=35)
    new_end = date.today() + timedelta(days=95)

    response = await client.post(
        f"/api/v1/reading-programs/programs/{source_summer_program.id}/launch-summer",
        json={
            "name": "Summer Reading Challenge 2026",
            "description": "Read, imagine, and win all summer.",
            "start_date": new_start.isoformat(),
            "end_date": new_end.isoformat(),
            "theme": "Color Our World",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["source_program_id"] == source_summer_program.id
    assert data["new_program_id"] != source_summer_program.id
    assert data["cloned_prizes"] == 1
    assert len(data["tasks"]) == 11
    assert data["tasks"][0]["key"] == "clone_structure"
    assert data["tasks"][-1]["key"] == "celebration_planning"


@pytest.mark.asyncio
async def test_launch_summer_reading_automation_requires_staff(
    client,
    test_patron,
    test_user_data,
    source_summer_program,
):
    """Patrons cannot run launch automation."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    token = login_response.json()["access_token"]

    response = await client.post(
        f"/api/v1/reading-programs/programs/{source_summer_program.id}/launch-summer",
        json={
            "name": "Summer Reading Challenge 2026",
            "start_date": (date.today() + timedelta(days=30)).isoformat(),
            "end_date": (date.today() + timedelta(days=90)).isoformat(),
            "theme": "Adventure Begins",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
