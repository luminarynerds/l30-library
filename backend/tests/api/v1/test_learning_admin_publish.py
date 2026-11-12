# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the admin course publish-toggle endpoint:

    PATCH /api/v1/learning/admin/courses/{course_id}/publish

Authorization rules under test:
  - Admin (require_admin) can toggle.
  - Staff/patron get 403.
  - 404 on missing or soft-deleted course.

Business rule under test:
  - Cannot transition is_published=false -> true on an empty course
    (no modules / no lessons). The Lesson model has no is_published
    column, so "has lessons" is the published-content proxy.
"""
import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import Course, CourseLifecycleStage, Lesson, Module


# --------------------------------------------------------------------------
# Helpers / fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def admin_client(client, test_admin):
    """httpx client where get_current_user resolves to the admin user."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def staff_client(client, test_staff):
    """httpx client where get_current_user resolves to a staff user.

    Staff is below admin for this endpoint -> should get 403.
    """
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    """httpx client where get_current_user resolves to a patron user."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _make_course(test_db, *, title: str, is_published: bool = False) -> Course:
    course = Course(
        title=title,
        description=f"{title} description",
        access_level="staff",
        lifecycle_stage=(
            CourseLifecycleStage.PUBLISHED
            if is_published
            else CourseLifecycleStage.DRAFT
        ),
    )
    test_db.add(course)
    await test_db.flush()
    await test_db.commit()
    return course


async def _add_module_with_lesson(test_db, course: Course) -> None:
    module = Module(
        course_id=course.id,
        title=f"{course.title} Module",
        sort_order=0,
    )
    test_db.add(module)
    await test_db.flush()

    lesson = Lesson(
        module_id=module.id,
        title=f"{course.title} Lesson",
        lesson_type="text",
        content={"body": "lesson body"},
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.flush()
    await test_db.commit()


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_publish_course_with_content(admin_client, test_db):
    """A draft course with >=1 module and >=1 lesson -> legacy publish
    endpoint succeeds and routes through the lifecycle service.

    The legacy endpoint goes through ALLOWED_TRANSITIONS; draft -> published
    is now a direct edge, so is_published=True publishes a draft directly."""
    course = await _make_course(test_db, title="Publishable", is_published=False)
    await _add_module_with_lesson(test_db, course)

    response = await admin_client.patch(
        f"/api/v1/learning/admin/courses/{course.id}/publish",
        json={"is_published": True},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    # Returned shape is CourseListItem -> includes module_count + lesson_count.
    assert payload["id"] == course.id
    assert payload["is_published"] is True
    assert payload["module_count"] == 1
    assert payload["lesson_count"] == 1


@pytest.mark.asyncio
async def test_admin_cannot_publish_empty_course(admin_client, test_db):
    """Empty draft course -> EmptyCourseError -> 400, state unchanged.

    draft -> published is allowed, so the service-level empty-course guard
    fires (not the transition-not-allowed guard). The error stays a str."""
    course = await _make_course(test_db, title="Empty Shell", is_published=False)

    response = await admin_client.patch(
        f"/api/v1/learning/admin/courses/{course.id}/publish",
        json={"is_published": True},
    )
    assert response.status_code == 400, response.text
    msg = response.json()["error"]["message"]
    # EmptyCourseError flows through as a plain str detail.
    assert isinstance(msg, str)
    assert "empty course" in msg.lower()

    # Re-read directly: state must not have flipped.
    await test_db.refresh(course)
    assert course.lifecycle_stage == CourseLifecycleStage.DRAFT


@pytest.mark.asyncio
async def test_admin_can_unpublish_without_content_check(admin_client, test_db):
    """Unpublish skips the empty-course gate (it only fires for the
    target=published path).

    PR-C2: reseeded at ARCHIVED so the legal target is DRAFT under
    ALLOWED_TRANSITIONS (ARCHIVED -> DRAFT is the one-way-out edge).
    The legacy endpoint maps ``is_published=False -> DRAFT``."""
    from app.models.learning import CourseLifecycleStage
    course = await _make_course(test_db, title="Already Live", is_published=True)
    course.lifecycle_stage = CourseLifecycleStage.ARCHIVED
    # Deliberately no modules/lessons -- the gate should NOT block unpublish.
    await test_db.commit()

    response = await admin_client.patch(
        f"/api/v1/learning/admin/courses/{course.id}/publish",
        json={"is_published": False},
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_published"] is False
    await test_db.refresh(course)
    assert course.lifecycle_stage == CourseLifecycleStage.DRAFT


@pytest.mark.asyncio
async def test_staff_is_forbidden(staff_client, test_db):
    """Staff (not admin) -> 403."""
    course = await _make_course(test_db, title="Staff View", is_published=False)
    await _add_module_with_lesson(test_db, course)

    response = await staff_client.patch(
        f"/api/v1/learning/admin/courses/{course.id}/publish",
        json={"is_published": True},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patron_is_forbidden(patron_client, test_db):
    """Patron -> 403."""
    course = await _make_course(test_db, title="Patron View", is_published=False)
    await _add_module_with_lesson(test_db, course)

    response = await patron_client.patch(
        f"/api/v1/learning/admin/courses/{course.id}/publish",
        json={"is_published": True},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unknown_course_returns_404(admin_client):
    """Non-existent course id -> 404."""
    response = await admin_client.patch(
        "/api/v1/learning/admin/courses/999999/publish",
        json={"is_published": True},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bad_body_returns_422(admin_client, test_db):
    """Missing is_published key -> 422 (FastAPI validation)."""
    course = await _make_course(test_db, title="Body Check", is_published=False)
    await _add_module_with_lesson(test_db, course)

    response = await admin_client.patch(
        f"/api/v1/learning/admin/courses/{course.id}/publish",
        json={},
    )
    assert response.status_code == 422
