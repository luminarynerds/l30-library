# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the per-course enrollment + completion aggregates that
GET /api/v1/learning/admin/courses now returns.

Asserts:
  - the four new admin-only fields are present on each row
  - counts and last_activity_at match a seeded scenario
    (2 enrolled, 1 completed at course-level, 1 in-progress)
  - patron-facing /learning/courses keeps the old CourseListItem shape
    (no enrollment counts leaked to learners)

Uses the dependency-override pattern from feedback_l30_test_auth_token_revocation:
override `get_current_user` directly so the route's `require_staff` dep
sees an authenticated staff user without going through the token cache.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.user import User, UserRole
from app.models.learning import (
    Course,
    CourseLifecycleStage,
    Module,
    Lesson,
    Enrollment,
    LessonProgress,
)


async def _make_user(db, role: UserRole, email: str) -> User:
    user = User(
        email=email,
        password_hash="not-used-in-this-test",
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def seeded_course(test_db):
    """Course with 2 modules x 2 lessons each (4 lessons total)."""
    course = Course(
        title="Aggregates Test Course",
        description="seed for admin aggregate test",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        difficulty="beginner",
        estimated_minutes=60,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    lessons = []
    for m_idx in range(2):
        module = Module(
            course_id=course.id,
            title=f"Module {m_idx}",
            sort_order=m_idx,
        )
        test_db.add(module)
        await test_db.commit()
        await test_db.refresh(module)

        for l_idx in range(2):
            lesson = Lesson(
                module_id=module.id,
                title=f"M{m_idx} Lesson {l_idx}",
                lesson_type="article",
                content={"text": "x"},
                estimated_minutes=10,
                sort_order=l_idx,
            )
            test_db.add(lesson)
            lessons.append(lesson)
        await test_db.commit()

    for lesson in lessons:
        await test_db.refresh(lesson)

    return course, lessons


@pytest.mark.integration
async def test_admin_courses_includes_enrollment_aggregates(
    client, test_db, seeded_course
):
    """Two enrolled, one completed (course-level), one with partial lesson_progress."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    course, lessons = seeded_course

    staff = await _make_user(test_db, UserRole.STAFF, "agg-staff@example.com")
    completed_user = await _make_user(test_db, UserRole.PATRON, "agg-done@example.com")
    in_progress_user = await _make_user(test_db, UserRole.PATRON, "agg-wip@example.com")

    now = datetime.now(timezone.utc)
    completion_ts = now - timedelta(hours=2)
    progress_ts = now - timedelta(minutes=15)

    # Enrollment 1: course-completed (Enrollment.completed_at set)
    test_db.add(
        Enrollment(
            user_id=completed_user.id,
            course_id=course.id,
            enrolled_at=now - timedelta(days=5),
            completed_at=completion_ts,
        )
    )
    # Enrollment 2: in-progress, has a lesson_progress row on lesson 0 only
    test_db.add(
        Enrollment(
            user_id=in_progress_user.id,
            course_id=course.id,
            enrolled_at=now - timedelta(days=1),
        )
    )
    await test_db.commit()

    # completed user finished every lesson (older timestamps so progress_ts is the max)
    for lesson in lessons:
        test_db.add(
            LessonProgress(
                user_id=completed_user.id,
                lesson_id=lesson.id,
                status="completed",
                started_at=completion_ts - timedelta(hours=1),
                completed_at=completion_ts,
            )
        )
    # in-progress user has touched just one lesson — and this is the most
    # recent activity timestamp, so last_activity_at should equal progress_ts.
    # The query uses MAX(COALESCE(completed_at, started_at)); with no
    # completed_at, started_at IS the activity timestamp, so seed it == progress_ts.
    test_db.add(
        LessonProgress(
            user_id=in_progress_user.id,
            lesson_id=lessons[0].id,
            status="in_progress",
            started_at=progress_ts,
            completed_at=None,
        )
    )
    await test_db.commit()

    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        resp = await client.get("/api/v1/learning/admin/courses")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, resp.text
    rows = resp.json()
    row = next((r for r in rows if r["id"] == course.id), None)
    assert row is not None, f"seeded course {course.id} missing from admin list"

    # Shape: four new fields present
    for key in ("enrollment_count", "completion_count", "in_progress_count", "last_activity_at"):
        assert key in row, f"missing '{key}' on admin CourseListItem"

    # Counts match the seed
    assert row["enrollment_count"] == 2, row
    assert row["completion_count"] == 1, row
    assert row["in_progress_count"] == 1, row

    # last_activity_at == progress_ts (most recent across all lesson_progress rows
    # for this course). SQLite strips timezones on round-trip, so coerce both
    # sides to UTC-aware before subtracting.
    assert row["last_activity_at"] is not None
    parsed = datetime.fromisoformat(row["last_activity_at"].replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    assert abs((parsed - progress_ts).total_seconds()) < 2, (
        f"last_activity_at {parsed} should be ~progress_ts {progress_ts}"
    )

    # Pre-existing fields still present on the admin shape
    assert row["module_count"] == 2
    assert row["lesson_count"] == 4


@pytest.mark.integration
async def test_admin_courses_zero_aggregates_for_empty_course(
    client, test_db
):
    """A course with no enrollments and no progress reports zeros + null timestamp."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, UserRole.STAFF, "agg-empty-staff@example.com")
    course = Course(
        title="No Activity Course",
        description="empty",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.DRAFT,
        difficulty="beginner",
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        resp = await client.get("/api/v1/learning/admin/courses")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, resp.text
    row = next((r for r in resp.json() if r["id"] == course.id), None)
    assert row is not None
    assert row["enrollment_count"] == 0
    assert row["completion_count"] == 0
    assert row["in_progress_count"] == 0
    assert row["last_activity_at"] is None


@pytest.mark.integration
async def test_patron_courses_response_does_not_leak_aggregate_fields(
    client, test_db
):
    """Patron-facing /learning/courses must NOT carry per-course enrollment data."""
    from app.api.v1.auth import get_current_user_optional
    from app.main import app

    course = Course(
        title="Patron-Visible",
        description="public",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        difficulty="beginner",
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    patron = await _make_user(test_db, UserRole.PATRON, "agg-patron@example.com")
    app.dependency_overrides[get_current_user_optional] = lambda: patron
    try:
        resp = await client.get("/api/v1/learning/courses")
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)

    assert resp.status_code == 200, resp.text
    row = next((r for r in resp.json() if r["id"] == course.id), None)
    assert row is not None
    # The four admin-only fields must be absent on the patron response.
    for key in ("enrollment_count", "completion_count", "in_progress_count", "last_activity_at"):
        assert key not in row, (
            f"patron-facing /learning/courses leaked admin field '{key}': "
            "narrow the schema, don't extend CourseListItem in place."
        )


# ──────────────────────────────────────────────────────────────────────────────
# PR-C4: patron visibility is gated SOLELY by lifecycle_stage == 'published'.
# This is the regression that would silently break prod if the patron-list
# filter or the computed is_published field drifted — keep it airtight.
# ──────────────────────────────────────────────────────────────────────────────


async def _make_patron_course(test_db, *, title: str, stage: CourseLifecycleStage):
    course = Course(
        title=title,
        description=f"{title} desc",
        access_level="patron",
        lifecycle_stage=stage,
        difficulty="beginner",
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)
    return course


@pytest.mark.integration
async def test_patron_list_includes_only_published_excludes_all_other_stages(
    client, test_db
):
    """Patron GET /learning/courses returns ONLY published courses.

    draft / archived MUST all be invisible.
    Anonymous request (no auth) — the most exposed path.
    """
    published = await _make_patron_course(
        test_db, title="PUB", stage=CourseLifecycleStage.PUBLISHED
    )
    hidden = {
        s.name: await _make_patron_course(test_db, title=s.name, stage=s)
        for s in (
            CourseLifecycleStage.DRAFT,
            CourseLifecycleStage.ARCHIVED,
        )
    }

    resp = await client.get("/api/v1/learning/courses")
    assert resp.status_code == 200, resp.text
    ids = {r["id"] for r in resp.json()}

    assert published.id in ids, "published course must be patron-visible"
    for stage_name, course in hidden.items():
        assert course.id not in ids, (
            f"{stage_name} course leaked into patron listing — only "
            f"lifecycle_stage='published' may be visible"
        )

    pub_row = next(r for r in resp.json() if r["id"] == published.id)
    assert pub_row["lifecycle_stage"] == "published"
    assert pub_row["is_published"] is True


@pytest.mark.integration
async def test_patron_list_drops_course_when_unpublished(
    client, test_db, test_admin
):
    """A published course transitioned back to draft (unpublished) disappears
    from the patron listing (matches the new-enrollment/listing gate)."""
    from app.services.course_lifecycle_service import transition_course_stage

    course = await _make_patron_course(
        test_db, title="WillRegress", stage=CourseLifecycleStage.PUBLISHED
    )
    resp = await client.get("/api/v1/learning/courses")
    assert course.id in {r["id"] for r in resp.json()}

    await transition_course_stage(
        test_db, course, CourseLifecycleStage.DRAFT, actor=test_admin
    )
    await test_db.commit()

    resp = await client.get("/api/v1/learning/courses")
    assert course.id not in {r["id"] for r in resp.json()}, (
        "unpublished course must NOT remain in the patron listing"
    )


@pytest.mark.integration
async def test_patron_list_adds_course_when_transitioned_to_published(
    client, test_db, test_admin
):
    """A draft course becomes patron-visible once published."""
    from app.services.course_lifecycle_service import transition_course_stage

    course = await _make_patron_course(
        test_db, title="WillPublish", stage=CourseLifecycleStage.DRAFT
    )
    module = Module(course_id=course.id, title="M", sort_order=0)
    test_db.add(module)
    await test_db.flush()
    test_db.add(Lesson(module_id=module.id, title="L", lesson_type="article",
                        content={}, sort_order=0))
    await test_db.commit()

    resp = await client.get("/api/v1/learning/courses")
    assert course.id not in {r["id"] for r in resp.json()}

    await transition_course_stage(
        test_db, course, CourseLifecycleStage.PUBLISHED, actor=test_admin
    )
    await test_db.commit()

    resp = await client.get("/api/v1/learning/courses")
    rows = resp.json()
    assert course.id in {r["id"] for r in rows}
    row = next(r for r in rows if r["id"] == course.id)
    assert row["is_published"] is True
    assert row["lifecycle_stage"] == "published"


def test_transition_service_no_longer_references_is_published():
    """Behavioral guard: the compat shim is gone. The service source
    must not assign the dropped ``is_published`` column."""
    import inspect

    from app.services import course_lifecycle_service

    src = inspect.getsource(course_lifecycle_service.transition_course_stage)
    assert "course.is_published" not in src, (
        "compat shim reintroduced — is_published was dropped in PR-C4"
    )
