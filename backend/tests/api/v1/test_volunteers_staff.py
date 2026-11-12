# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for staff volunteer endpoints that close the "staff verify via psql"
gap from #1804: cross-volunteer hour-log queue, hour-log rejection, shift
edit, and shift cancel/staff listing.
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


async def _request_as_non_staff(user, db, method, url, json_body=None):
    """Like _request but leaves require_staff wired to its real check, so an
    authenticated non-staff user hits the real role gate."""
    from httpx import AsyncClient, ASGITransport
    from app.api.v1.auth import get_current_user
    from app.api.v1.dependencies import require_authenticated
    from app.core.database import get_db
    from app.main import app

    async def override_user():
        return user

    async def override_db():
        yield db

    app.dependency_overrides[require_authenticated] = override_user
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            return await ac.request(method, url, json=json_body)
    finally:
        for dep in (require_authenticated, get_current_user, get_db):
            app.dependency_overrides.pop(dep, None)


async def _make_volunteer(db, user, role_category="shelving"):
    from app.models.volunteer import VolunteerStatus
    from app.services.volunteer_service import VolunteerProfileService

    return await VolunteerProfileService.create_volunteer_profile(
        db,
        user_id=user.id,
        primary_role_category=role_category,
        phone="",
        status=VolunteerStatus.active,
    )


async def _make_second_patron(db, email="second@example.org"):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=email,
        password_hash=hash_password("SecondPassword123!"),
        first_name="Second",
        last_name="Volunteer",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _make_shift(db, **overrides):
    from app.models.volunteer import VolunteerShift

    fields = {
        "title": "Shelving shift",
        "role_category": "shelving",
        "shift_date": date(2026, 8, 1),
        "start_time": "10:00",
        "end_time": "12:00",
        "duration_hours": 2.0,
        "volunteers_needed": 2,
    }
    fields.update(overrides)
    shift = VolunteerShift(**fields)
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift


async def _log_hours(user, db, volunteer_id, **overrides):
    payload = {"log_date": "2026-07-05", "hours": 2.0, "activity_type": "shift_work"}
    payload.update(overrides)
    response = await _request(
        user, db, "POST", f"/api/v1/volunteers/{volunteer_id}/hours/log", payload
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


# ============================================================================
# GET /volunteers/hour-logs — cross-volunteer queue
# ============================================================================

@pytest.mark.asyncio
async def test_hour_log_queue_lists_cross_volunteer_submitted_with_names(
    test_db, test_patron, test_admin
):
    volunteer_a = await _make_volunteer(test_db, test_patron)
    second_user = await _make_second_patron(test_db)
    volunteer_b = await _make_volunteer(test_db, second_user)

    log_a = await _log_hours(test_patron, test_db, volunteer_a.id)
    log_b = await _log_hours(second_user, test_db, volunteer_b.id)

    response = await _request(test_admin, test_db, "GET", "/api/v1/volunteers/hour-logs")
    assert response.status_code == 200, response.text
    entries = {entry["id"]: entry for entry in response.json()["hour_logs"]}
    assert log_a in entries and log_b in entries
    assert entries[log_a]["volunteer_name"] == "Test User"
    assert entries[log_b]["volunteer_name"] == "Second Volunteer"
    assert all(entry["status"] == "submitted" for entry in entries.values())


@pytest.mark.asyncio
async def test_hour_log_queue_filters_by_status(test_db, test_patron, test_admin):
    volunteer = await _make_volunteer(test_db, test_patron)
    log_id = await _log_hours(test_patron, test_db, volunteer.id)

    verify = await _request(
        test_admin, test_db, "POST", f"/api/v1/volunteers/hour-logs/{log_id}/verify"
    )
    assert verify.status_code == 200, verify.text

    default_queue = await _request(test_admin, test_db, "GET", "/api/v1/volunteers/hour-logs")
    assert log_id not in {e["id"] for e in default_queue.json()["hour_logs"]}

    verified_queue = await _request(
        test_admin, test_db, "GET", "/api/v1/volunteers/hour-logs?status=verified"
    )
    assert log_id in {e["id"] for e in verified_queue.json()["hour_logs"]}


@pytest.mark.asyncio
async def test_hour_log_queue_filters_by_rejected_status(test_db, test_patron, test_admin):
    volunteer = await _make_volunteer(test_db, test_patron)
    log_id = await _log_hours(test_patron, test_db, volunteer.id)

    reject = await _request(
        test_admin,
        test_db,
        "POST",
        f"/api/v1/volunteers/hour-logs/{log_id}/reject",
        {"reason": "duplicate entry"},
    )
    assert reject.status_code == 200, reject.text

    default_queue = await _request(test_admin, test_db, "GET", "/api/v1/volunteers/hour-logs")
    assert log_id not in {e["id"] for e in default_queue.json()["hour_logs"]}

    rejected_queue = await _request(
        test_admin, test_db, "GET", "/api/v1/volunteers/hour-logs?status=rejected"
    )
    assert log_id in {e["id"] for e in rejected_queue.json()["hour_logs"]}


@pytest.mark.asyncio
async def test_hour_log_queue_rejects_bogus_status(test_db, test_admin):
    response = await _request(
        test_admin, test_db, "GET", "/api/v1/volunteers/hour-logs?status=bogus"
    )
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_hour_log_queue_paginates(test_db, test_patron, test_admin):
    volunteer = await _make_volunteer(test_db, test_patron)
    second_user = await _make_second_patron(test_db)
    volunteer_b = await _make_volunteer(test_db, second_user)

    log_a = await _log_hours(test_patron, test_db, volunteer.id, log_date="2026-07-01")
    log_b = await _log_hours(second_user, test_db, volunteer_b.id, log_date="2026-07-02")

    page_1 = await _request(
        test_admin, test_db, "GET", "/api/v1/volunteers/hour-logs?limit=1&page=1"
    )
    assert page_1.status_code == 200, page_1.text
    body_1 = page_1.json()
    assert body_1["total"] == 2
    assert body_1["page"] == 1
    assert body_1["limit"] == 1
    assert len(body_1["hour_logs"]) == 1
    assert body_1["hour_logs"][0]["id"] == log_b  # log_date desc

    page_2 = await _request(
        test_admin, test_db, "GET", "/api/v1/volunteers/hour-logs?limit=1&page=2"
    )
    assert page_2.status_code == 200, page_2.text
    body_2 = page_2.json()
    assert body_2["total"] == 2
    assert len(body_2["hour_logs"]) == 1
    assert body_2["hour_logs"][0]["id"] == log_a

    ids_seen = {body_1["hour_logs"][0]["id"], body_2["hour_logs"][0]["id"]}
    assert ids_seen == {log_a, log_b}


# ============================================================================
# POST /volunteers/hour-logs/{id}/reject
# ============================================================================

@pytest.mark.asyncio
async def test_reject_hour_log_requires_reason(test_db, test_patron, test_admin):
    volunteer = await _make_volunteer(test_db, test_patron)
    log_id = await _log_hours(test_patron, test_db, volunteer.id)

    response = await _request(
        test_admin, test_db, "POST", f"/api/v1/volunteers/hour-logs/{log_id}/reject", {}
    )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_reject_hour_log_sets_rejected_and_does_not_bump_hours(
    test_db, test_patron, test_admin
):
    volunteer = await _make_volunteer(test_db, test_patron)
    log_id = await _log_hours(test_patron, test_db, volunteer.id, hours=3.0)

    response = await _request(
        test_admin,
        test_db,
        "POST",
        f"/api/v1/volunteers/hour-logs/{log_id}/reject",
        {"reason": "Hours don't match the shift log"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rejected"

    from sqlalchemy import select
    from app.models.volunteer import GeneralVolunteerHourLog, Volunteer

    log = (
        await test_db.execute(
            select(GeneralVolunteerHourLog).where(GeneralVolunteerHourLog.id == log_id)
        )
    ).scalar_one()
    assert log.status == "rejected"
    assert log.rejected_reason == "Hours don't match the shift log"

    refreshed = (
        await test_db.execute(select(Volunteer).where(Volunteer.id == volunteer.id))
    ).scalar_one()
    assert refreshed.total_hours == 0


@pytest.mark.asyncio
async def test_reject_already_verified_log_conflicts(test_db, test_patron, test_admin):
    volunteer = await _make_volunteer(test_db, test_patron)
    log_id = await _log_hours(test_patron, test_db, volunteer.id)

    verify = await _request(
        test_admin, test_db, "POST", f"/api/v1/volunteers/hour-logs/{log_id}/verify"
    )
    assert verify.status_code == 200, verify.text

    response = await _request(
        test_admin,
        test_db,
        "POST",
        f"/api/v1/volunteers/hour-logs/{log_id}/reject",
        {"reason": "too late"},
    )
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test_reject_nonexistent_log_is_404(test_db, test_admin):
    response = await _request(
        test_admin,
        test_db,
        "POST",
        "/api/v1/volunteers/hour-logs/999999/reject",
        {"reason": "not found"},
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_reject_hour_log_stamps_rejected_by_and_rejected_at(
    test_db, test_patron, test_admin
):
    volunteer = await _make_volunteer(test_db, test_patron)
    log_id = await _log_hours(test_patron, test_db, volunteer.id)

    response = await _request(
        test_admin,
        test_db,
        "POST",
        f"/api/v1/volunteers/hour-logs/{log_id}/reject",
        {"reason": "Not a valid activity"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["rejected_at"] is not None

    from sqlalchemy import select
    from app.models.volunteer import GeneralVolunteerHourLog

    log = (
        await test_db.execute(
            select(GeneralVolunteerHourLog).where(GeneralVolunteerHourLog.id == log_id)
        )
    ).scalar_one()
    assert log.rejected_by_id == test_admin.id
    assert log.rejected_at is not None


# ============================================================================
# PATCH /volunteers/shifts/{id}
# ============================================================================

@pytest.mark.asyncio
async def test_update_shift_persists_fields(test_db, test_admin):
    shift = await _make_shift(test_db)

    response = await _request(
        test_admin,
        test_db,
        "PATCH",
        f"/api/v1/volunteers/shifts/{shift.id}",
        {"title": "Updated shift", "volunteers_needed": 5, "location": "Main desk"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Updated shift"
    assert body["volunteers_needed"] == 5
    assert body["location"] == "Main desk"

    from sqlalchemy import select
    from app.models.volunteer import VolunteerShift

    refreshed = (
        await test_db.execute(select(VolunteerShift).where(VolunteerShift.id == shift.id))
    ).scalar_one()
    assert refreshed.title == "Updated shift"
    assert refreshed.duration_hours == 2.0  # untouched field unchanged


@pytest.mark.asyncio
async def test_update_shift_validates_role_category(test_db, test_admin):
    shift = await _make_shift(test_db)

    response = await _request(
        test_admin,
        test_db,
        "PATCH",
        f"/api/v1/volunteers/shifts/{shift.id}",
        {"role_category": "not-a-real-category"},
    )
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_update_nonexistent_shift_is_404(test_db, test_admin):
    response = await _request(
        test_admin, test_db, "PATCH", "/api/v1/volunteers/shifts/999999", {"title": "x"}
    )
    assert response.status_code == 404, response.text


# ============================================================================
# POST /volunteers/shifts/{id}/cancel + staff shift listing
# ============================================================================

@pytest.mark.asyncio
async def test_cancel_shift_hides_from_patron_list_but_staff_can_see_it(test_db, test_admin):
    shift = await _make_shift(test_db)

    response = await _request(
        test_admin, test_db, "POST", f"/api/v1/volunteers/shifts/{shift.id}/cancel"
    )
    assert response.status_code == 200, response.text
    assert response.json()["cancelled"] is True

    patron_view = await _request(test_admin, test_db, "GET", "/api/v1/volunteers/shifts")
    assert shift.id not in {s["id"] for s in patron_view.json()["shifts"]}

    staff_default = await _request(
        test_admin, test_db, "GET", "/api/v1/volunteers/shifts/staff"
    )
    assert shift.id not in {s["id"] for s in staff_default.json()["shifts"]}

    staff_all = await _request(
        test_admin, test_db, "GET", "/api/v1/volunteers/shifts/staff?include_cancelled=true"
    )
    assert shift.id in {s["id"] for s in staff_all.json()["shifts"]}


@pytest.mark.asyncio
async def test_cancel_nonexistent_shift_is_404(test_db, test_admin):
    response = await _request(
        test_admin, test_db, "POST", "/api/v1/volunteers/shifts/999999/cancel"
    )
    assert response.status_code == 404, response.text


# ============================================================================
# role_category validation on shift listing endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_list_available_shifts_rejects_bogus_role_category(test_db, test_admin):
    response = await _request(
        test_admin, test_db, "GET", "/api/v1/volunteers/shifts?role_category=not-a-role"
    )
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_list_available_shifts_valid_role_category_filters(test_db, test_admin):
    await _make_shift(test_db, role_category="shelving")
    programming_shift = await _make_shift(
        test_db, title="Storytime", role_category="programming"
    )

    response = await _request(
        test_admin, test_db, "GET", "/api/v1/volunteers/shifts?role_category=programming"
    )
    assert response.status_code == 200, response.text
    ids = {s["id"] for s in response.json()["shifts"]}
    assert ids == {programming_shift.id}


@pytest.mark.asyncio
async def test_list_shifts_staff_rejects_bogus_role_category(test_db, test_admin):
    response = await _request(
        test_admin,
        test_db,
        "GET",
        "/api/v1/volunteers/shifts/staff?role_category=not-a-role",
    )
    assert response.status_code == 400, response.text


# ============================================================================
# Staff-only gating
# ============================================================================

@pytest.mark.asyncio
async def test_new_staff_endpoints_reject_non_staff(test_db, test_patron):
    volunteer = await _make_volunteer(test_db, test_patron)
    log_id = await _log_hours(test_patron, test_db, volunteer.id)
    shift = await _make_shift(test_db)

    checks = [
        ("GET", "/api/v1/volunteers/hour-logs", None),
        ("POST", f"/api/v1/volunteers/hour-logs/{log_id}/reject", {"reason": "no"}),
        ("PATCH", f"/api/v1/volunteers/shifts/{shift.id}", {"title": "nope"}),
        ("POST", f"/api/v1/volunteers/shifts/{shift.id}/cancel", None),
        ("GET", "/api/v1/volunteers/shifts/staff", None),
    ]
    for method, url, body in checks:
        response = await _request_as_non_staff(test_patron, test_db, method, url, body)
        assert response.status_code in (401, 403), f"{method} {url}: {response.status_code}"
