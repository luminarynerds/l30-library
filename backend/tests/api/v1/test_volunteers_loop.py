# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests for the patron volunteer loop: shift signup, hour logging,
hour verification, skill add.

The endpoints took raw dicts splatted into services with different kwarg
names (500s), read body fields from query params (silently dropped), and
signup looked up Volunteer by primary key == user id (wrong volunteer).
"""

from datetime import date

import pytest


async def _request(user, db, method, url, json_body=None):
    from httpx import AsyncClient, ASGITransport
    from app.api.v1.auth import get_current_user
    from app.api.v1.dependencies import require_authenticated, require_staff
    from app.core.database import get_db
    from app.main import app

    async def override_user():
        return user

    async def override_db():
        yield db

    app.dependency_overrides[require_authenticated] = override_user
    app.dependency_overrides[require_staff] = override_user
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            return await ac.request(method, url, json=json_body)
    finally:
        for dep in (require_authenticated, require_staff, get_current_user, get_db):
            app.dependency_overrides.pop(dep, None)


async def _make_volunteer(db, user):
    from app.models.volunteer import VolunteerStatus
    from app.services.volunteer_service import VolunteerProfileService

    return await VolunteerProfileService.create_volunteer_profile(
        db,
        user_id=user.id,
        primary_role_category="shelving",
        phone="",
        status=VolunteerStatus.active,
    )


async def _make_shift(db):
    from app.models.volunteer import VolunteerShift

    shift = VolunteerShift(
        title="Shelving shift",
        role_category="shelving",
        shift_date=date(2026, 8, 1),
        start_time="10:00",
        end_time="12:00",
        duration_hours=2.0,
        volunteers_needed=2,
    )
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift


@pytest.mark.asyncio
async def test_signup_uses_current_users_volunteer_profile(test_db, test_patron, test_admin):
    """Signup must resolve the volunteer via user_id, not Volunteer.id == user.id."""
    # Another user's profile takes the first Volunteer id, so the patron's
    # Volunteer.id diverges from their user id (regression: signup used the
    # pk as the user id).
    await _make_volunteer(test_db, test_admin)
    volunteer = await _make_volunteer(test_db, test_patron)
    assert volunteer.id != test_patron.id, "test setup must diverge the ids"
    shift = await _make_shift(test_db)

    response = await _request(
        test_patron, test_db, "POST", f"/api/v1/volunteers/shifts/{shift.id}/signup"
    )
    assert response.status_code == 200, response.text
    assert response.json()["shift_id"] == shift.id

    from sqlalchemy import select
    from app.models.volunteer import ShiftSignup

    signup = (
        await test_db.execute(select(ShiftSignup).where(ShiftSignup.shift_id == shift.id))
    ).scalar_one()
    assert signup.volunteer_id == volunteer.id


@pytest.mark.asyncio
async def test_log_hours_json_body_lands_submitted(test_db, test_patron):
    """The dialog's payload must create a log in submitted status (the one
    every pending-hours summary counts)."""
    volunteer = await _make_volunteer(test_db, test_patron)

    response = await _request(
        test_patron,
        test_db,
        "POST",
        f"/api/v1/volunteers/{volunteer.id}/hours/log",
        {"log_date": "2026-07-05", "hours": 2.5, "activity_type": "shift_work",
         "description": "sweep test"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "submitted"

    summary = await _request(test_patron, test_db, "GET", "/api/v1/volunteers/me/hours")
    assert summary.json()["pending_hours"] == 2.5


@pytest.mark.asyncio
async def test_verify_hours_reads_notes_from_body(test_db, test_patron, test_admin):
    """Verification notes sent as a JSON body must persist (they were read
    from a query param and silently dropped)."""
    volunteer = await _make_volunteer(test_db, test_patron)
    log_response = await _request(
        test_patron,
        test_db,
        "POST",
        f"/api/v1/volunteers/{volunteer.id}/hours/log",
        {"log_date": "2026-07-05", "hours": 1.0, "activity_type": "training"},
    )
    log_id = log_response.json()["id"]

    response = await _request(
        test_admin,
        test_db,
        "POST",
        f"/api/v1/volunteers/hour-logs/{log_id}/verify",
        {"verification_notes": "confirmed at desk"},
    )
    assert response.status_code == 200, response.text

    from sqlalchemy import select
    from app.models.volunteer import GeneralVolunteerHourLog, Volunteer

    log = (
        await test_db.execute(
            select(GeneralVolunteerHourLog).where(GeneralVolunteerHourLog.id == log_id)
        )
    ).scalar_one()
    assert log.status == "verified"
    assert log.verification_notes == "confirmed at desk"

    refreshed = (
        await test_db.execute(select(Volunteer).where(Volunteer.id == volunteer.id))
    ).scalar_one()
    assert refreshed.total_hours == 1.0


@pytest.mark.asyncio
async def test_staff_create_shift_visible_to_patrons(test_db, test_patron, test_admin):
    """Staff create a shift via JSON body (was a raw-dict splat that 500'd on
    any client key); patrons see it in the available-shifts envelope."""
    response = await _request(
        test_admin,
        test_db,
        "POST",
        "/api/v1/volunteers/shifts",
        {"title": "Storytime setup", "role_category": "programming",
         "shift_date": "2026-08-02", "start_time": "09:00", "end_time": "11:00",
         "duration_hours": 2.0, "volunteers_needed": 3, "location": "Children's room"},
    )
    assert response.status_code == 200, response.text
    shift_id = response.json()["id"]

    listing = await _request(test_patron, test_db, "GET", "/api/v1/volunteers/shifts")
    shifts = listing.json()["shifts"]
    assert any(s["id"] == shift_id for s in shifts)


@pytest.mark.asyncio
async def test_add_skill_json_body(test_db, test_patron):
    """The dialog's payload keys must reach the service (years_of_experience/
    description, not years_experience/notes)."""
    volunteer = await _make_volunteer(test_db, test_patron)

    response = await _request(
        test_patron,
        test_db,
        "POST",
        f"/api/v1/volunteers/{volunteer.id}/skills",
        {"skill_name": "Spanish", "proficiency_level": "advanced",
         "description": "conversational"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["skill_name"] == "Spanish"

    listing = await _request(test_patron, test_db, "GET", "/api/v1/volunteers/me/skills")
    names = [s["skill_name"] for s in listing.json()]
    assert "Spanish" in names
