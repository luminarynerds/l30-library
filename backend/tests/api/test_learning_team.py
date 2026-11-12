# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the manager Team progress endpoint:

    GET /api/v1/learning/team/progress

Authorization rules under test:
  - A staff user with at least one direct report (via
    StaffOnboarding.manager_id) gets back the aggregated progress for
    those reports — and only those reports.
  - A staff user with no direct reports gets back an empty list (200, []).
  - A patron is rejected with 403 by `require_staff`.

We deliberately do NOT accept a `manager_id` query param; the endpoint
always derives it from the authenticated caller. That contract is
exercised implicitly here — there's no parameter to pass.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import Course, CourseLifecycleStage, Enrollment
from app.models.onboarding import OnboardingStatus, StaffOnboarding


# --------------------------------------------------------------------------
# Helpers / fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def staff_client(client, test_staff):
    """Client where get_current_user resolves to the staff user."""
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    """Client where get_current_user resolves to a patron user."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _make_report(test_db, manager_user, *, email: str, first: str, last: str):
    """Create a user and link them as a direct report of `manager_user`."""
    from app.models.user import User, UserRole
    from app.core.security import hash_password

    report = User(
        email=email,
        password_hash=hash_password("test-password-123!"),
        first_name=first,
        last_name=last,
        role=UserRole.STAFF,
    )
    test_db.add(report)
    await test_db.flush()

    onboarding = StaffOnboarding(
        user_id=report.id,
        status=OnboardingStatus.in_progress,
        start_date=date.today(),
        expected_completion_date=date.today() + timedelta(days=90),
        department="library",
        position="staff",
        manager_id=manager_user.id,
    )
    test_db.add(onboarding)
    await test_db.flush()
    return report


async def _make_course(test_db, *, title: str, duration_days: int | None = 30):
    course = Course(
        title=title,
        description=f"{title} description",
        access_level="staff",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        duration_days=duration_days,
    )
    test_db.add(course)
    await test_db.flush()
    return course


async def _enroll(
    test_db,
    *,
    user_id: int,
    course_id: int,
    completed: bool = False,
    overdue: bool = False,
    due_in_days: int | None = None,
):
    now = datetime.now(timezone.utc)
    if overdue:
        due_at = now - timedelta(days=2)
    elif due_in_days is not None:
        due_at = now + timedelta(days=due_in_days)
    else:
        due_at = None

    enrollment = Enrollment(
        user_id=user_id,
        course_id=course_id,
        enrolled_at=now - timedelta(days=10),
        due_at=due_at,
        completed_at=now if completed else None,
    )
    test_db.add(enrollment)
    await test_db.flush()
    return enrollment


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manager_gets_their_reports_progress(
    staff_client, test_db, test_staff
):
    """Staff with reports sees one row per report, with correct aggregates."""
    report_a = await _make_report(
        test_db, test_staff, email="report-a@example.com", first="Alice", last="A"
    )
    course1 = await _make_course(test_db, title="Course 1")
    course2 = await _make_course(test_db, title="Course 2")

    await _enroll(test_db, user_id=report_a.id, course_id=course1.id, completed=True)
    await _enroll(test_db, user_id=report_a.id, course_id=course2.id, overdue=True)
    await test_db.commit()

    response = await staff_client.get("/api/v1/learning/team/progress")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1

    row = payload[0]
    assert row["user_id"] == report_a.id
    assert row["email"] == "report-a@example.com"
    assert row["courses_total"] == 2
    assert row["courses_completed"] == 1
    assert row["overdue_count"] == 1
    assert row["due_soon_count"] == 0
    assert row["completion_rate"] == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_staff_with_no_reports_gets_empty_list(staff_client):
    """Staff who manage nobody get [] — the frontend hides the Team tab."""
    response = await staff_client.get("/api/v1/learning/team/progress")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_patron_is_forbidden(patron_client):
    """Patrons cannot reach the team-progress endpoint at all."""
    response = await patron_client.get("/api/v1/learning/team/progress")
    assert response.status_code == 403
