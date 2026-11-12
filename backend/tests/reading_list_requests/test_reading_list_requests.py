# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the Reading List Requests API.

Covers:
- POST /schools/{school_id}/reading-lists/{list_id}/request  (teacher creates)
- GET  /schools/{school_id}/reading-list-requests            (teacher lists own)
- POST /reading-list-requests/{id}/approve                   (staff)
- POST /reading-list-requests/{id}/fulfill                   (staff)
- POST /reading-list-requests/{id}/reject                    (staff)
- DELETE /reading-list-requests/{id}                         (teacher cancels)
- Cross-user isolation
"""

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.outreach import OutreachPartner
from app.models.reading import SharedReadingList
from app.models.user import User, UserRole


# ==================== Setup Fixtures ====================


@pytest.fixture
async def school(test_db):
    """A school (OutreachPartner) the teacher can request reading lists at."""
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
async def reading_list(test_db, school):
    """A SharedReadingList tied to the test school."""
    rl = SharedReadingList(
        name="3rd Grade Spring Picks",
        description="Curated picks for Q2",
        partner_id=school.id,
        curriculum_alignment="Language Arts",
        grade_levels=["3rd"],
        reading_levels=["AR 3.0-4.0"],
        topics=["nature", "friendship"],
        is_active=True,
    )
    test_db.add(rl)
    await test_db.commit()
    await test_db.refresh(rl)
    return rl


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
        email="teacher.rlr@example.com",
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
    """A second teacher, at the same school, for cross-user isolation."""
    from app.core.security import hash_password

    u = User(
        email="other.teacher.rlr@example.com",
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
    """FirstBootMiddleware returns 503 until first-boot setup completes;
    flip the cached flag so it short-circuits."""
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
    """Flip the get_current_user override mid-test to switch acting user."""
    app.dependency_overrides[get_current_user] = lambda: user


def _create_url(school_id: int, list_id: int) -> str:
    return f"/api/v1/school-partnerships/schools/{school_id}/reading-lists/{list_id}/request"


def _list_url(school_id: int) -> str:
    return f"/api/v1/school-partnerships/schools/{school_id}/reading-list-requests"


# ==================== POST /schools/.../reading-lists/.../request ====================


@pytest.mark.asyncio
async def test_create_request_returns_201_and_pending_status(teacher_client, school, reading_list):
    resp = await teacher_client.post(
        _create_url(school.id, reading_list.id),
        json={"copies": 25, "notes": "For Spring unit"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["schoolId"] == school.id
    assert body["listId"] == reading_list.id
    assert body["listTitle"] == "3rd Grade Spring Picks"
    assert body["copies"] == 25
    assert body["notes"] == "For Spring unit"
    assert body["id"] > 0
    assert body["requestDate"] is not None


@pytest.mark.asyncio
async def test_create_request_unknown_school_returns_404(staff_client, reading_list):
    # Use staff_client: a TEACHER-role caller is scoped to their own
    # school_id and would 403 before the school-existence check ever runs
    # (assert_teacher_access_to_school checks role/school binding first).
    # Staff has no per-school binding, so this exercises the actual
    # not-found path.
    resp = await staff_client.post(
        _create_url(999_999, reading_list.id),
        json={"copies": 1},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_request_unknown_list_returns_404(teacher_client, school):
    resp = await teacher_client.post(
        _create_url(school.id, 999_999),
        json={"copies": 1},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_request_list_from_other_school_returns_404(
    staff_client, test_db, school, reading_list
):
    # A second school with no reading list; using `reading_list.id` (which
    # belongs to `school`) should 404 when requested via the other school.
    # Use staff_client for the same reason as the unknown-school test above:
    # a TEACHER-role caller is scoped to their own school_id and would 403
    # before this list/school mismatch is ever checked.
    other = OutreachPartner(name="Other School", partner_type="school", status="active")
    test_db.add(other)
    await test_db.commit()
    await test_db.refresh(other)

    resp = await staff_client.post(
        _create_url(other.id, reading_list.id),
        json={"copies": 1},
    )
    assert resp.status_code == 404


# ==================== GET /schools/.../reading-list-requests ====================


@pytest.mark.asyncio
async def test_list_requests_returns_only_my_requests(
    teacher_client, school, reading_list, teacher, other_teacher
):
    # Teacher A submits two
    _as(teacher)
    r1 = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 10})
    r2 = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 5})
    assert r1.status_code == 201
    assert r2.status_code == 201

    # Teacher B submits one - should NOT appear in A's list
    _as(other_teacher)
    r3 = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 3})
    assert r3.status_code == 201

    # Teacher A lists
    _as(teacher)
    listing = await teacher_client.get(_list_url(school.id))
    assert listing.status_code == 200
    requests = listing.json()["requests"]
    assert len(requests) == 2
    ids = {r["id"] for r in requests}
    assert r1.json()["id"] in ids
    assert r2.json()["id"] in ids
    assert r3.json()["id"] not in ids

    # Each row carries the page's required fields
    sample = requests[0]
    for key in ("listId", "listTitle", "requestDate", "status", "copies"):
        assert key in sample, f"missing key {key}: {sample}"


# ==================== POST /reading-list-requests/{id}/approve ====================


@pytest.mark.asyncio
async def test_staff_can_approve_pending_request(
    teacher_client, staff_client, school, reading_list
):
    create = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 12})
    req_id = create.json()["id"]

    approve = await staff_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/approve"
    )
    assert approve.status_code == 200, approve.text
    body = approve.json()
    assert body["status"] == "approved"
    assert body["id"] == req_id


@pytest.mark.asyncio
async def test_teacher_cannot_approve(teacher_client, school, reading_list):
    create = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 1})
    req_id = create.json()["id"]

    approve = await teacher_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/approve"
    )
    assert approve.status_code == 403


@pytest.mark.asyncio
async def test_approve_already_approved_returns_400(
    teacher_client, staff_client, school, reading_list
):
    create = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 1})
    req_id = create.json()["id"]

    first = await staff_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/approve"
    )
    assert first.status_code == 200

    second = await staff_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/approve"
    )
    assert second.status_code == 400


# ==================== POST /reading-list-requests/{id}/fulfill ====================


@pytest.mark.asyncio
async def test_staff_can_fulfill_pending_request(
    teacher_client, staff_client, school, reading_list
):
    create = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 1})
    req_id = create.json()["id"]

    fulfill = await staff_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/fulfill"
    )
    assert fulfill.status_code == 200, fulfill.text
    body = fulfill.json()
    assert body["status"] == "fulfilled"
    assert body["fulfilledAt"] is not None
    assert body["fulfilledByUserId"] is not None


@pytest.mark.asyncio
async def test_staff_can_fulfill_approved_request(
    teacher_client, staff_client, school, reading_list
):
    create = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 1})
    req_id = create.json()["id"]
    approve = await staff_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/approve"
    )
    assert approve.status_code == 200

    fulfill = await staff_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/fulfill"
    )
    assert fulfill.status_code == 200
    assert fulfill.json()["status"] == "fulfilled"


# ==================== POST /reading-list-requests/{id}/reject ====================


@pytest.mark.asyncio
async def test_staff_can_reject_pending_request(teacher_client, staff_client, school, reading_list):
    create = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 1})
    req_id = create.json()["id"]

    reject = await staff_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/reject",
        json={"reason": "Out of stock"},
    )
    assert reject.status_code == 200, reject.text
    body = reject.json()
    assert body["status"] == "rejected"
    assert body["rejectionReason"] == "Out of stock"


@pytest.mark.asyncio
async def test_reject_after_fulfill_returns_400(teacher_client, staff_client, school, reading_list):
    create = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 1})
    req_id = create.json()["id"]
    fulfilled = await staff_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/fulfill"
    )
    assert fulfilled.status_code == 200

    reject = await staff_client.post(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}/reject",
        json={"reason": "Changed mind"},
    )
    assert reject.status_code == 400


# ==================== DELETE /reading-list-requests/{id} ====================


@pytest.mark.asyncio
async def test_cancel_own_request_succeeds(teacher_client, school, reading_list):
    create = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 1})
    req_id = create.json()["id"]

    cancel = await teacher_client.delete(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}"
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    # Cancelled does not appear in the teacher's list
    listing = await teacher_client.get(_list_url(school.id))
    ids = [r["id"] for r in listing.json()["requests"]]
    assert req_id not in ids


@pytest.mark.asyncio
async def test_cancel_other_users_request_returns_403(
    teacher_client, school, reading_list, teacher, other_teacher
):
    _as(other_teacher)
    create = await teacher_client.post(_create_url(school.id, reading_list.id), json={"copies": 1})
    req_id = create.json()["id"]

    _as(teacher)
    cancel = await teacher_client.delete(
        f"/api/v1/school-partnerships/reading-list-requests/{req_id}"
    )
    assert cancel.status_code == 403


# ==================== Librarian-notification email fan-out ====================


@pytest.mark.asyncio
async def test_email_fanout_dispatches_in_background_without_blocking():
    """The librarian email fan-out must run on a background task, not inline.

    Regression: with the fan-out awaited inline, one sequential ``send_email``
    round trip per staff recipient (~18 in prod) made 'Request' hang for
    seconds. ``_schedule_email_fanout`` must return immediately (nothing sent
    yet) and then deliver every job once the loop runs.
    """
    import asyncio

    from app.api.v1.school_reading import _notifications
    from app.api.v1.school_reading._notifications import _schedule_email_fanout

    release = asyncio.Event()
    sent: list[str] = []
    seen_kwargs: list[dict] = []

    async def _blocking_send_email(to_email, subject, html, **kwargs):
        sent.append(to_email)
        seen_kwargs.append(kwargs)
        await release.wait()
        return True

    jobs = [
        ("librarian0.fanout@example.com", "teacher_action_reading_list_request_u1"),
        ("librarian1.fanout@example.com", "teacher_action_reading_list_request_u2"),
        ("librarian2.fanout@example.com", "teacher_action_reading_list_request_u3"),
    ]

    _schedule_email_fanout(
        _blocking_send_email,
        jobs,
        subject="A teacher requested a reading list",
        html="<div>hi</div>",
        action_type="reading_list_request",
    )

    # Scheduling must NOT block: it returns before any email is sent, even
    # though every send is held by the unreleased event.
    assert sent == [], "emails were sent inline instead of on a background task"

    # Release the sends and let the background task drain.
    release.set()
    pending = list(_notifications._background_email_tasks)
    assert pending, "no background email task was scheduled"
    await asyncio.gather(*pending)

    assert sorted(sent) == [
        "librarian0.fanout@example.com",
        "librarian1.fanout@example.com",
        "librarian2.fanout@example.com",
    ]
    # Per-recipient Resend tag + notification_type are preserved.
    assert seen_kwargs[0]["categories"] == ["teacher_action_reading_list_request_u1"]
    assert seen_kwargs[0]["notification_type"] == "teacher_action_reading_list_request"


@pytest.mark.asyncio
async def test_resolve_recipients_restricts_to_childrens_teen_and_admin(test_db):
    """Broadcast recipients = admin-level floor + STAFF whose staff_role is a
    children's/teen role. Line staff (circ, pages, reference, uncategorized)
    and patrons are excluded.
    """
    from app.api.v1.school_reading._notifications import _resolve_recipients
    from app.core.security import hash_password

    def _mk(email, role, staff_role=None):
        return User(
            email=email,
            password_hash=hash_password("FloorPass123!"),
            first_name="A",
            last_name="B",
            role=role,
            staff_role=staff_role,
            is_active=True,
            email_verified=True,
        )

    included = {
        "childrens.resolve@example.com": (UserRole.STAFF, "childrens_librarian"),
        "teen.resolve@example.com": (UserRole.STAFF, "teen_librarian"),
        "admin.resolve@example.com": (UserRole.ADMIN, "head_circulation"),
        "super.resolve@example.com": (UserRole.SUPER_ADMIN, "director"),
        "director.resolve@example.com": (UserRole.DIRECTOR, None),
        "libadmin.resolve@example.com": (UserRole.LIBRARY_ADMIN, None),
    }
    excluded = {
        "circ.resolve@example.com": (UserRole.STAFF, "circulation"),
        "page.resolve@example.com": (UserRole.STAFF, "page"),
        "ref.resolve@example.com": (UserRole.STAFF, "reference_librarian"),
        "nostaffrole.resolve@example.com": (UserRole.STAFF, None),
        "patron.resolve@example.com": (UserRole.PATRON, None),
    }
    for email, (role, staff_role) in {**included, **excluded}.items():
        test_db.add(_mk(email, role, staff_role))
    await test_db.commit()

    recipients = await _resolve_recipients(test_db, target_user_id=None)
    got = {u.email for u in recipients}

    assert set(included) <= got, f"missing expected recipients: {set(included) - got}"
    assert got.isdisjoint(set(excluded)), f"leaked excluded recipients: {got & set(excluded)}"
