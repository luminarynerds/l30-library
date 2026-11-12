# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the manager course-assign endpoint:

    POST /api/v1/learning/enrollments/assign

Critical security boundary — these tests pin the authorization rules:
  - Patrons cannot assign (require_staff → 403).
  - Staff can only assign to their direct reports
    (StaffOnboarding.manager_id == caller.id). Cross-manager assignment
    yields 403.
  - Re-assigning the same course updates the existing enrollment rather
    than creating a duplicate (idempotent UPSERT semantics).
  - Due-date fallback: explicit > course.duration_days > NULL.
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import Course, CourseLifecycleStage, Enrollment
from app.models.onboarding import OnboardingStatus, StaffOnboarding


# --------------------------------------------------------------------------
# Helpers / fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def staff_client(client, test_staff):
    """Client where get_current_user resolves to the staff manager."""
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    """Client where get_current_user resolves to a patron."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _make_user(test_db, *, email: str, first: str, last: str, role=None):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=email,
        password_hash=hash_password("test-password-123!"),
        first_name=first,
        last_name=last,
        role=role or UserRole.STAFF,
    )
    test_db.add(user)
    await test_db.flush()
    return user


async def _link_report(test_db, *, manager, report):
    onboarding = StaffOnboarding(
        user_id=report.id,
        status=OnboardingStatus.in_progress,
        start_date=date.today(),
        expected_completion_date=date.today() + timedelta(days=90),
        department="library",
        position="staff",
        manager_id=manager.id,
    )
    test_db.add(onboarding)
    await test_db.flush()
    return onboarding


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


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manager_assigns_to_their_report(staff_client, test_db, test_staff):
    """Manager can assign to a direct report → 201 + is_required=True."""
    report = await _make_user(
        test_db, email="report@example.com", first="Rae", last="Port"
    )
    await _link_report(test_db, manager=test_staff, report=report)
    course = await _make_course(test_db, title="First Aid Basics")
    await test_db.commit()

    response = await staff_client.post(
        "/api/v1/learning/enrollments/assign",
        json={"user_id": report.id, "course_id": course.id, "is_required": True},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_id"] == report.id
    assert body["course_id"] == course.id
    assert body["is_required"] is True
    assert body["assigned_by_id"] == test_staff.id

    # Confirm the row really landed in the DB.
    result = await test_db.execute(
        select(Enrollment).where(
            Enrollment.user_id == report.id, Enrollment.course_id == course.id
        )
    )
    enrollment = result.scalar_one()
    assert enrollment.is_required is True
    assert enrollment.assigned_by_id == test_staff.id


@pytest.mark.asyncio
async def test_manager_cannot_assign_to_non_report(staff_client, test_db, test_staff):
    """A staff caller cannot assign to a user who isn't their direct report."""
    stranger = await _make_user(
        test_db, email="stranger@example.com", first="Out", last="Sider"
    )
    # Deliberately NO StaffOnboarding link to test_staff.
    course = await _make_course(test_db, title="Cross-Boundary 101")
    await test_db.commit()

    response = await staff_client.post(
        "/api/v1/learning/enrollments/assign",
        json={"user_id": stranger.id, "course_id": course.id},
    )
    assert response.status_code == 403, response.text

    # Nothing should have been written.
    result = await test_db.execute(
        select(Enrollment).where(Enrollment.user_id == stranger.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_patron_cannot_assign(patron_client, test_db, test_patron):
    """Patrons hit `require_staff` and get a 403 before authorization runs."""
    # The body doesn't matter — the gate fires first.
    response = await patron_client.post(
        "/api/v1/learning/enrollments/assign",
        json={"user_id": test_patron.id, "course_id": 1},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_reassign_updates_existing_enrollment(
    staff_client, test_db, test_staff
):
    """Assigning the same course twice updates the row rather than duplicating."""
    report = await _make_user(
        test_db, email="report-2@example.com", first="Re", last="Two"
    )
    await _link_report(test_db, manager=test_staff, report=report)
    course = await _make_course(test_db, title="Reassign Me", duration_days=14)
    await test_db.commit()

    first = await staff_client.post(
        "/api/v1/learning/enrollments/assign",
        json={"user_id": report.id, "course_id": course.id, "is_required": False},
    )
    assert first.status_code == 201
    first_id = first.json()["id"]
    assert first.json()["is_required"] is False

    # Second call: now mark it Required. Should *update*, not duplicate.
    second = await staff_client.post(
        "/api/v1/learning/enrollments/assign",
        json={"user_id": report.id, "course_id": course.id, "is_required": True},
    )
    assert second.status_code == 201
    assert second.json()["id"] == first_id
    assert second.json()["is_required"] is True

    # Exactly one enrollment row exists.
    result = await test_db.execute(
        select(Enrollment).where(
            Enrollment.user_id == report.id, Enrollment.course_id == course.id
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_due_at_fallback_uses_course_duration(
    staff_client, test_db, test_staff
):
    """Without explicit due_at, due falls back to now + course.duration_days."""
    report = await _make_user(
        test_db, email="report-3@example.com", first="Re", last="Three"
    )
    await _link_report(test_db, manager=test_staff, report=report)
    course = await _make_course(test_db, title="Has Duration", duration_days=21)
    await test_db.commit()

    response = await staff_client.post(
        "/api/v1/learning/enrollments/assign",
        json={"user_id": report.id, "course_id": course.id},
    )
    assert response.status_code == 201
    due_at = response.json()["due_at"]
    assert due_at is not None
    parsed = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
    expected_min = datetime.now(timezone.utc) + timedelta(days=20)
    expected_max = datetime.now(timezone.utc) + timedelta(days=22)
    assert expected_min < parsed < expected_max


@pytest.mark.asyncio
async def test_due_at_explicit_value_wins(staff_client, test_db, test_staff):
    """Caller-supplied due_at is preserved verbatim."""
    report = await _make_user(
        test_db, email="report-4@example.com", first="Re", last="Four"
    )
    await _link_report(test_db, manager=test_staff, report=report)
    course = await _make_course(test_db, title="Explicit Due", duration_days=30)
    await test_db.commit()

    explicit = datetime(2027, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    response = await staff_client.post(
        "/api/v1/learning/enrollments/assign",
        json={
            "user_id": report.id,
            "course_id": course.id,
            "due_at": explicit.isoformat(),
        },
    )
    assert response.status_code == 201
    parsed = datetime.fromisoformat(response.json()["due_at"].replace("Z", "+00:00"))
    assert parsed == explicit


@pytest.mark.asyncio
async def test_due_at_null_when_no_duration_and_no_explicit(
    staff_client, test_db, test_staff
):
    """No explicit due + course.duration_days IS NULL → enrollment.due_at NULL."""
    report = await _make_user(
        test_db, email="report-5@example.com", first="Re", last="Five"
    )
    await _link_report(test_db, manager=test_staff, report=report)
    course = await _make_course(test_db, title="No Duration", duration_days=None)
    await test_db.commit()

    response = await staff_client.post(
        "/api/v1/learning/enrollments/assign",
        json={"user_id": report.id, "course_id": course.id},
    )
    assert response.status_code == 201
    assert response.json()["due_at"] is None
