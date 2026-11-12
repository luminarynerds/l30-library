# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the lesson preview=true staff bypass.

Verifies the security model:
  - preview=true + staff/admin => 200 (enrollment skipped)
  - preview=true + patron (non-staff) => 403
  - preview=true + anonymous => 401
  - preview=false/absent + patron unenrolled => 403 (unchanged)

Uses dependency-override clients (no real login/Redis) following the staff_client pattern.
"""
import contextlib
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def preview_course_with_lesson(test_db):
    from app.models.learning import Course, CourseLifecycleStage, Lesson, Module

    course = Course(
        title="Preview Test Course",
        description="Course for testing preview bypass",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        difficulty="beginner",
        estimated_minutes=30,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    module = Module(
        course_id=course.id,
        title="Preview Module",
        description="Module for preview testing",
        sort_order=0,
    )
    test_db.add(module)
    await test_db.commit()
    await test_db.refresh(module)

    lesson = Lesson(
        module_id=module.id,
        title="Preview Test Lesson",
        lesson_type="article",
        content={"body": "Preview lesson content"},
        estimated_minutes=10,
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.commit()
    await test_db.refresh(lesson)

    return {"course": course, "module": module, "lesson": lesson}


@pytest.fixture
async def patron_user(test_db):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="preview_patron@example.com",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Preview",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@contextlib.asynccontextmanager
async def _make_client(test_db, current_user_override=None, optional_user_override=None):
    """Build a test client with dependency overrides for a given user."""
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user, get_optional_user
    from app.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.state.setup_complete = True

    if current_user_override is not None:
        async def _current_user():
            return current_user_override
        app.dependency_overrides[get_current_user] = _current_user

    if optional_user_override is not None:
        async def _optional_user():
            return optional_user_override
        app.dependency_overrides[get_optional_user] = _optional_user
    elif optional_user_override is None and current_user_override is not None:
        # optional should return the same user so the optional dependency works
        _u = current_user_override
        async def _optional_user_from_current():
            return _u
        app.dependency_overrides[get_optional_user] = _optional_user_from_current

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_user, None)


@pytest.mark.integration
class TestLessonPreviewBypass:
    async def test_staff_preview_bypasses_enrollment(
        self, test_db, staff_user, preview_course_with_lesson
    ):
        """Staff with preview=true gets 200 without enrollment."""
        lesson_id = preview_course_with_lesson["lesson"].id

        async with _make_client(test_db, current_user_override=staff_user) as ac:
            resp = await ac.get(f"/api/v1/learning/lessons/{lesson_id}?preview=true")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json()["title"] == "Preview Test Lesson"

    async def test_patron_preview_still_blocked(
        self, test_db, patron_user, preview_course_with_lesson
    ):
        """Non-staff with preview=true gets 403, not 200."""
        lesson_id = preview_course_with_lesson["lesson"].id

        async with _make_client(test_db, current_user_override=patron_user) as ac:
            resp = await ac.get(f"/api/v1/learning/lessons/{lesson_id}?preview=true")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        data = resp.json()
        detail = (data.get("detail") or data.get("error", {}).get("message", "")).lower()
        assert "staff" in detail or "role" in detail, f"Expected staff/role in detail: {detail}"

    async def test_anonymous_preview_blocked(
        self, test_db, preview_course_with_lesson
    ):
        """Anonymous caller with preview=true gets 401, not lesson content."""
        lesson_id = preview_course_with_lesson["lesson"].id

        async with _make_client(test_db, optional_user_override=None) as ac:
            resp = await ac.get(f"/api/v1/learning/lessons/{lesson_id}?preview=true")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    async def test_patron_without_preview_still_blocked(
        self, test_db, patron_user, preview_course_with_lesson
    ):
        """Normal unenrolled patron without preview param stays 403 (no regression)."""
        lesson_id = preview_course_with_lesson["lesson"].id

        async with _make_client(test_db, current_user_override=patron_user) as ac:
            resp = await ac.get(f"/api/v1/learning/lessons/{lesson_id}")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        data = resp.json()
        detail = (data.get("detail") or data.get("error", {}).get("message", "")).lower()
        assert "enroll" in detail, f"Expected 'enroll' in detail: {detail}"

    async def test_admin_preview_bypasses_enrollment(
        self, test_db, admin_user, preview_course_with_lesson
    ):
        """Admin with preview=true also gets 200 without enrollment."""
        lesson_id = preview_course_with_lesson["lesson"].id

        async with _make_client(test_db, current_user_override=admin_user) as ac:
            resp = await ac.get(f"/api/v1/learning/lessons/{lesson_id}?preview=true")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
