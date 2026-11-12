# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the Library Visit Scheduling API.

Covers:
- POST /library-visits/request                (teacher creates request)
- GET  /library-visits/requests/{school_id}   (teacher lists own pending/rejected)
- DELETE /library-visits/requests/{id}        (teacher cancels own; 403 on others')
- GET  /library-visits/{school_id}            (scheduled visits, no teacher filter)
- POST /library-visits/requests/{id}/approve  (staff transitions pending -> scheduled)
- POST /library-visits/requests/{id}/reject   (staff transitions pending -> rejected)
"""

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.outreach import OutreachPartner
from app.models.user import User, UserRole


# ==================== Setup Fixtures ====================


@pytest.fixture
async def school(test_db):
    """A school (OutreachPartner) the teacher can request visits at."""
    s = OutreachPartner(
        name="Test Elementary School",
        partner_type="school",
        status="active",
    )
    test_db.add(s)
    await test_db.commit()
    await test_db.refresh(s)
    return s


@pytest.fixture
async def teacher(test_db, school):
    """The primary teacher identity for these tests. The endpoint requires
    role TEACHER or STAFF ("Teacher or staff access required") AND, for
    TEACHER-role callers, that user.school_id match the school in the URL
    ("Teachers can only access their assigned school") -- the global
    test_patron fixture is role=PATRON and has no school_id, so it doesn't
    qualify."""
    from app.core.security import hash_password

    u = User(
        email="teacher@example.com",
        password_hash=hash_password("TeacherPassword123!"),
        first_name="Test",
        last_name="Teacher",
        role=UserRole.TEACHER,
        school_id=school.id,
        is_active=True,
        email_verified=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


@pytest.fixture
async def other_teacher(test_db, school):
    """A second teacher, at the same school, used to test cross-user
    isolation (same-school access is required to even reach the 403)."""
    from app.core.security import hash_password

    u = User(
        email="other.teacher@example.com",
        password_hash=hash_password("OtherPassword123!"),
        first_name="Other",
        last_name="Teacher",
        role=UserRole.TEACHER,
        school_id=school.id,
        is_active=True,
        email_verified=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


@pytest.fixture(autouse=True)
def _bypass_first_boot():
    """The FirstBootMiddleware returns 503 until first-boot setup completes.
    Flip the cached app.state flag so the middleware short-circuits past its
    DB check, which would otherwise fire on every request in the suite."""
    app.state.setup_complete = True
    yield


@pytest.fixture
def teacher_client(client, teacher):
    app.dependency_overrides[get_current_user] = lambda: teacher
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def staff_client(client, test_staff):
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


def _as(user):
    """Switch the get_current_user override to act as a different user mid-test.
    pytest can't compose two `client` fixtures with conflicting overrides on
    the same test, so we flip explicitly when crossing user boundaries.
    """
    app.dependency_overrides[get_current_user] = lambda: user


def _request_payload(school_id: int) -> dict:
    return {
        "schoolId": school_id,
        "requestedDate": "2026-06-01T10:00:00Z",
        "numberOfStudents": 25,
        "gradeLevel": "3rd Grade",
        "teacherName": "Ms. Smith",
        "purpose": "Library orientation and book selection",
    }


# ==================== POST /library-visits/request ====================


@pytest.mark.asyncio
async def test_create_visit_request_returns_201_and_pending_status(teacher_client, school):
    resp = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["schoolId"] == school.id
    assert body["teacherName"] == "Ms. Smith"
    assert body["numberOfStudents"] == 25
    assert body["gradeLevel"] == "3rd Grade"
    assert body["id"] > 0


@pytest.mark.asyncio
async def test_create_visit_request_unknown_school_returns_404(staff_client):
    # Use staff_client: a TEACHER-role caller is scoped to their own
    # school_id and would 403 before the school-existence check ever runs
    # (assert_teacher_access_to_school checks role/school binding first).
    # Staff has no per-school binding, so this exercises the actual
    # not-found path.
    resp = await staff_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(999_999),
    )
    assert resp.status_code == 404


# ==================== GET /library-visits/requests/{school_id} ====================


@pytest.mark.asyncio
async def test_list_requests_returns_only_my_pending_and_rejected(
    teacher_client, school, teacher, other_teacher
):
    # Teacher A submits two requests
    _as(teacher)
    r1 = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    assert r1.status_code == 201
    r2 = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    assert r2.status_code == 201

    # Teacher B submits one - should not appear in A's list
    _as(other_teacher)
    r3 = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    assert r3.status_code == 201

    # Teacher A lists - sees their own 2
    _as(teacher)
    listing = await teacher_client.get(
        f"/api/v1/school-partnerships/library-visits/requests/{school.id}"
    )
    assert listing.status_code == 200
    requests = listing.json()["requests"]
    assert len(requests) == 2
    ids = {r["id"] for r in requests}
    assert r1.json()["id"] in ids
    assert r2.json()["id"] in ids
    assert r3.json()["id"] not in ids


# ==================== DELETE /library-visits/requests/{id} ====================


@pytest.mark.asyncio
async def test_cancel_own_request_succeeds(teacher_client, school):
    create = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    req_id = create.json()["id"]

    cancel = await teacher_client.delete(
        f"/api/v1/school-partnerships/library-visits/requests/{req_id}"
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    # Cancelled request should no longer appear in the teacher's pending/rejected list
    listing = await teacher_client.get(
        f"/api/v1/school-partnerships/library-visits/requests/{school.id}"
    )
    ids = [r["id"] for r in listing.json()["requests"]]
    assert req_id not in ids


@pytest.mark.asyncio
async def test_cancel_other_users_request_returns_403(
    teacher_client, school, teacher, other_teacher
):
    # other_teacher creates a request
    _as(other_teacher)
    create = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    req_id = create.json()["id"]

    # teacher tries to cancel it - should be 403
    _as(teacher)
    cancel = await teacher_client.delete(
        f"/api/v1/school-partnerships/library-visits/requests/{req_id}"
    )
    assert cancel.status_code == 403


# ==================== POST /library-visits/requests/{id}/approve ====================


@pytest.mark.asyncio
async def test_staff_can_approve_pending_request(teacher_client, staff_client, school):
    create = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    req_id = create.json()["id"]

    approve = await staff_client.post(
        f"/api/v1/school-partnerships/library-visits/requests/{req_id}/approve",
        json={"scheduledDate": "2026-06-05T11:00:00Z"},
    )
    assert approve.status_code == 200, approve.text
    body = approve.json()
    assert body["status"] == "scheduled"
    assert body["scheduledDate"] is not None
    assert body["approvedByUserId"] is not None
    assert body["approvedAt"] is not None

    # And it now shows up in the scheduled-visits list (no teacher filter)
    visits = await staff_client.get(f"/api/v1/school-partnerships/library-visits/{school.id}")
    assert visits.status_code == 200
    visit_ids = [v["id"] for v in visits.json()["visits"]]
    assert req_id in visit_ids


@pytest.mark.asyncio
async def test_teacher_cannot_approve(teacher_client, school):
    create = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    req_id = create.json()["id"]

    approve = await teacher_client.post(
        f"/api/v1/school-partnerships/library-visits/requests/{req_id}/approve",
        json={"scheduledDate": "2026-06-05T11:00:00Z"},
    )
    assert approve.status_code == 403


# ==================== POST /library-visits/requests/{id}/reject ====================


@pytest.mark.asyncio
async def test_staff_can_reject_pending_request(teacher_client, staff_client, school):
    create = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    req_id = create.json()["id"]

    reject = await staff_client.post(
        f"/api/v1/school-partnerships/library-visits/requests/{req_id}/reject",
        json={"reason": "Library closed that day for inventory"},
    )
    assert reject.status_code == 200, reject.text
    body = reject.json()
    assert body["status"] == "rejected"
    assert body["rejectionReason"] == "Library closed that day for inventory"


@pytest.mark.asyncio
async def test_approve_already_scheduled_returns_400(teacher_client, staff_client, school):
    create = await teacher_client.post(
        "/api/v1/school-partnerships/library-visits/request",
        json=_request_payload(school.id),
    )
    req_id = create.json()["id"]

    first = await staff_client.post(
        f"/api/v1/school-partnerships/library-visits/requests/{req_id}/approve",
        json={"scheduledDate": "2026-06-05T11:00:00Z"},
    )
    assert first.status_code == 200

    second = await staff_client.post(
        f"/api/v1/school-partnerships/library-visits/requests/{req_id}/approve",
        json={"scheduledDate": "2026-06-06T11:00:00Z"},
    )
    assert second.status_code == 400
