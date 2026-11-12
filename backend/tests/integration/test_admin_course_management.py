# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for admin course management.

Tests cover:
- Course CRUD operations (create, read, update, delete)
- Module management (create, update, delete within courses)
- Lesson management (create, update, delete within modules)
- Content reordering (modules and lessons via sort_order)
- Publishing workflows (publish/unpublish courses)
- Permission validation (staff/admin access)
- Prerequisite course management and validation
"""

from datetime import datetime, timedelta
import pytest


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...} -- fall back to "detail" for any endpoint that
    still raises before that handler applies."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


@pytest.fixture
async def test_admin_user(test_db):
    """Create an admin user for course management tests."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="courseadmin@example.com",
        password_hash=hash_password("AdminPassword123!"),
        first_name="Course",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_regular_user(test_db):
    """Create a regular patron user for permission tests."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="regularuser@example.com",
        password_hash=hash_password("UserPassword123!"),
        first_name="Regular",
        last_name="User",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_staff_user(test_db):
    """Create a staff user for permission tests."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="staffuser@example.com",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Staff",
        last_name="User",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_course(test_db):
    """Create a test course."""
    from app.models.learning import Course, CourseLifecycleStage

    course = Course(
        title="Test Course",
        description="A test course for unit testing",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.DRAFT,
        difficulty="beginner",
        estimated_minutes=60,
        quiz_passing_threshold=70,
        xp_reward=100,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)
    return course


@pytest.fixture
async def test_published_course(test_db):
    """Create a published test course."""
    from app.models.learning import Course, CourseLifecycleStage

    course = Course(
        title="Published Course",
        description="A published course for testing",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        difficulty="intermediate",
        estimated_minutes=120,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)
    return course


@pytest.fixture
async def test_module(test_db, test_course):
    """Create a test module."""
    from app.models.learning import Module

    module = Module(
        course_id=test_course.id,
        title="Test Module",
        description="A test module",
        sort_order=0,
    )
    test_db.add(module)
    await test_db.commit()
    await test_db.refresh(module)
    return module


@pytest.fixture
async def test_lesson(test_db, test_module):
    """Create a test lesson."""
    from app.models.learning import Lesson

    lesson = Lesson(
        module_id=test_module.id,
        title="Test Lesson",
        lesson_type="article",
        content={"text": "This is lesson content"},
        estimated_minutes=15,
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.commit()
    await test_db.refresh(lesson)
    return lesson


async def get_admin_token(client, admin_email="courseadmin@example.com"):
    """Helper to get admin authentication token."""
    login_data = {
        "username": admin_email,
        "password": "AdminPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


async def get_staff_token(client):
    """Helper to get staff authentication token."""
    login_data = {
        "username": "staffuser@example.com",
        "password": "StaffPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


async def get_user_token(client, email, password):
    """Helper to get user authentication token."""
    login_data = {
        "username": email,
        "password": password,
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


# ============ COURSE CRUD TESTS ============


@pytest.mark.integration
class TestCourseCreate:
    """Tests for course creation."""

    async def test_create_course_as_admin(self, client, test_admin_user):
        """Test admin can create a course."""
        token = await get_admin_token(client)
        course_data = {
            "title": "New Admin Course",
            "description": "A course created by admin",
            "access_level": "patron",
            "difficulty": "beginner",
            "estimated_minutes": 30,
        }
        response = await client.post(
            "/api/v1/learning/courses",
            json=course_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Admin Course"
        assert data["description"] == "A course created by admin"
        assert data["is_published"] is False
        assert data["difficulty"] == "beginner"

    async def test_create_course_as_patron_forbidden(self, client, test_regular_user):
        """Test that patrons cannot create courses."""
        token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        course_data = {
            "title": "Unauthorized Course",
            "description": "Should fail",
        }
        response = await client.post(
            "/api/v1/learning/courses",
            json=course_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert (
            "staff" in _error_detail(response).lower() or "admin" in _error_detail(response).lower()
        )

    async def test_create_course_as_staff(self, client, test_staff_user):
        """Test that staff can create courses."""
        token = await get_user_token(client, "staffuser@example.com", "StaffPassword123!")
        course_data = {
            "title": "Staff Course",
            "description": "Created by staff",
            "access_level": "patron",
            "difficulty": "beginner",
        }
        response = await client.post(
            "/api/v1/learning/courses",
            json=course_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Staff Course"
        assert data["description"] == "Created by staff"

    async def test_create_course_requires_auth(self, client):
        """Test that course creation requires authentication."""
        course_data = {
            "title": "No Auth Course",
            "description": "Should fail",
        }
        response = await client.post("/api/v1/learning/courses", json=course_data)
        assert response.status_code == 401

    async def test_create_course_with_all_fields(self, client, test_admin_user):
        """Test creating a course with all available fields."""
        token = await get_admin_token(client)
        course_data = {
            "title": "Complete Course",
            "description": "A fully specified course",
            "access_level": "staff",
            "difficulty": "advanced",
            "estimated_minutes": 180,
            "sensory_warning": "Contains flashing images",
            "quiz_passing_threshold": 80,
            "prerequisite_course_ids": [],
        }
        response = await client.post(
            "/api/v1/learning/courses",
            json=course_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Complete Course"
        assert data["access_level"] == "staff"
        assert data["difficulty"] == "advanced"
        assert data["sensory_warning"] == "Contains flashing images"

    async def test_create_course_title_required(self, client, test_admin_user):
        """Test that course title is required."""
        token = await get_admin_token(client)
        course_data = {
            "description": "Missing title",
        }
        response = await client.post(
            "/api/v1/learning/courses",
            json=course_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestCourseRead:
    """Tests for reading courses."""

    async def test_list_published_courses_public(self, client, test_published_course):
        """Test that published courses are publicly accessible."""
        response = await client.get("/api/v1/learning/courses")
        assert response.status_code == 200
        courses = response.json()
        assert len(courses) >= 1
        # Verify published course is in the list
        titles = [c["title"] for c in courses]
        assert "Published Course" in titles

    async def test_unpublished_courses_not_in_public_list(
        self, client, test_course, test_published_course
    ):
        """Test that unpublished courses are not in public list."""
        response = await client.get("/api/v1/learning/courses")
        assert response.status_code == 200
        courses = response.json()
        titles = [c["title"] for c in courses]
        assert "Test Course" not in titles  # Unpublished course

    async def test_admin_can_list_all_courses(
        self, client, test_admin_user, test_course, test_published_course
    ):
        """Test admin can see all courses including unpublished."""
        token = await get_admin_token(client)
        response = await client.get(
            "/api/v1/learning/admin/courses",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        courses = response.json()
        titles = [c["title"] for c in courses]
        assert "Test Course" in titles  # Unpublished
        assert "Published Course" in titles  # Published

    async def test_get_course_details(self, client, test_published_course):
        """Test getting course details."""
        response = await client.get(f"/api/v1/learning/courses/{test_published_course.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Published Course"
        assert "modules" in data

    async def test_get_unpublished_course_as_admin(self, client, test_admin_user, test_course):
        """Test admin can access unpublished course details."""
        token = await get_admin_token(client)
        response = await client.get(
            f"/api/v1/learning/courses/{test_course.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Test Course"

    async def test_get_unpublished_course_as_patron_fails(
        self, client, test_regular_user, test_course
    ):
        """Test patron cannot access unpublished course."""
        token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.get(
            f"/api/v1/learning/courses/{test_course.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404  # Hidden, returns not found

    async def test_get_nonexistent_course(self, client):
        """Test getting nonexistent course returns 404."""
        response = await client.get("/api/v1/learning/courses/99999")
        assert response.status_code == 404


@pytest.mark.integration
class TestCourseUpdate:
    """Tests for course updates."""

    async def test_update_course_as_admin(self, client, test_admin_user, test_course):
        """Test admin can update a course."""
        token = await get_admin_token(client)
        update_data = {
            "title": "Updated Course Title",
            "description": "Updated description",
        }
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Course Title"
        assert data["description"] == "Updated description"

    async def test_update_course_partial(self, client, test_admin_user, test_course):
        """Test partial course update (only some fields)."""
        token = await get_admin_token(client)
        original_description = test_course.description
        update_data = {
            "title": "Only Title Changed",
        }
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Only Title Changed"
        assert data["description"] == original_description

    async def test_update_course_as_patron_forbidden(self, client, test_regular_user, test_course):
        """Test patron cannot update courses."""
        token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"title": "Hacked Title"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_update_nonexistent_course(self, client, test_admin_user):
        """Test updating nonexistent course returns 404."""
        token = await get_admin_token(client)
        response = await client.put(
            "/api/v1/learning/courses/99999",
            json={"title": "Ghost Course"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestCourseDelete:
    """Tests for course deletion."""

    async def test_delete_course_as_admin(self, client, test_db, test_admin_user):
        """Test admin can delete a course.

        Deletion is a cascade-archive (see delete_course docstring), not a
        destructive delete: the course stays visible to staff/admin —
        that's what makes it recoverable — but flips to lifecycle_stage
        "archived" and disappears from patron-facing views.
        """
        from app.models.learning import Course, CourseLifecycleStage

        # Create a course to delete
        course = Course(
            title="Course To Delete",
            description="Will be deleted",
            lifecycle_stage=CourseLifecycleStage.DRAFT,
        )
        test_db.add(course)
        await test_db.commit()
        await test_db.refresh(course)
        course_id = course.id

        token = await get_admin_token(client)
        response = await client.delete(
            f"/api/v1/learning/courses/{course_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Nothing was destroyed: admin can still see the course, now archived.
        response = await client.get(
            f"/api/v1/learning/courses/{course_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["lifecycle_stage"] == "archived"

        # Deleting again is idempotent-404, same as the old soft-delete contract.
        response = await client.delete(
            f"/api/v1/learning/courses/{course_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

        # Patrons/anonymous users don't see archived courses.
        response = await client.get(f"/api/v1/learning/courses/{course_id}")
        assert response.status_code == 404

    async def test_delete_course_as_patron_forbidden(self, client, test_regular_user, test_course):
        """Test patron cannot delete courses."""
        token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.delete(
            f"/api/v1/learning/courses/{test_course.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_delete_nonexistent_course(self, client, test_admin_user):
        """Test deleting nonexistent course returns 404."""
        token = await get_admin_token(client)
        response = await client.delete(
            "/api/v1/learning/courses/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


# ============ MODULE MANAGEMENT TESTS ============


@pytest.mark.integration
class TestModuleCreate:
    """Tests for module creation within courses."""

    async def test_create_module_as_admin(self, client, test_admin_user, test_course):
        """Test admin can create a module in a course."""
        token = await get_admin_token(client)
        module_data = {
            "title": "New Module",
            "description": "A new module for the course",
            "sort_order": 1,
            "course_id": test_course.id,
        }
        response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/modules",
            json=module_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Module"
        assert data["course_id"] == test_course.id
        assert data["sort_order"] == 1

    async def test_create_module_as_patron_forbidden(self, client, test_regular_user, test_course):
        """Test patron cannot create modules."""
        token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/modules",
            json={"title": "Unauthorized Module"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_create_module_in_nonexistent_course(self, client, test_admin_user):
        """Test creating module in nonexistent course fails."""
        token = await get_admin_token(client)
        response = await client.post(
            "/api/v1/learning/courses/99999/modules",
            json={"title": "Orphan Module", "course_id": 99999},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestModuleUpdate:
    """Tests for module updates."""

    async def test_update_module_as_admin(self, client, test_admin_user, test_module):
        """Test admin can update a module."""
        token = await get_admin_token(client)
        update_data = {
            "title": "Updated Module Title",
            "description": "Updated module description",
        }
        response = await client.put(
            f"/api/v1/learning/modules/{test_module.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Module Title"

    async def test_update_module_sort_order(self, client, test_admin_user, test_module):
        """Test updating module sort order."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/modules/{test_module.id}",
            json={"sort_order": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["sort_order"] == 5

    async def test_update_nonexistent_module(self, client, test_admin_user):
        """Test updating nonexistent module returns 404."""
        token = await get_admin_token(client)
        response = await client.put(
            "/api/v1/learning/modules/99999",
            json={"title": "Ghost Module"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestModuleDelete:
    """Tests for module deletion."""

    async def test_delete_module_as_admin(self, client, test_db, test_admin_user, test_course):
        """Test admin can delete a module."""
        from app.models.learning import Module

        # Create a module to delete
        module = Module(
            course_id=test_course.id,
            title="Module To Delete",
            sort_order=0,
        )
        test_db.add(module)
        await test_db.commit()
        await test_db.refresh(module)
        module_id = module.id

        token = await get_admin_token(client)
        response = await client.delete(
            f"/api/v1/learning/modules/{module_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    async def test_delete_module_cascades_to_lessons(
        self, client, test_db, test_admin_user, test_module, test_lesson
    ):
        """Test deleting module also deletes its lessons."""
        from app.models.learning import Lesson
        from sqlalchemy import select

        lesson_id = test_lesson.id
        module_id = test_module.id

        token = await get_admin_token(client)
        response = await client.delete(
            f"/api/v1/learning/modules/{module_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Verify lesson is also deleted
        result = await test_db.execute(select(Lesson).where(Lesson.id == lesson_id))
        assert result.scalar_one_or_none() is None


# ============ LESSON MANAGEMENT TESTS ============


@pytest.mark.integration
class TestLessonCreate:
    """Tests for lesson creation within modules."""

    async def test_create_lesson_as_admin(self, client, test_admin_user, test_module):
        """Test admin can create a lesson in a module."""
        token = await get_admin_token(client)
        lesson_data = {
            "title": "New Lesson",
            "lesson_type": "article",
            "content": {"text": "Lesson content here"},
            "estimated_minutes": 10,
            "sort_order": 1,
            "module_id": test_module.id,
        }
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json=lesson_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Lesson"
        assert data["lesson_type"] == "article"
        assert data["module_id"] == test_module.id

    async def test_create_video_lesson(self, client, test_admin_user, test_module):
        """Test creating a video lesson."""
        token = await get_admin_token(client)
        lesson_data = {
            "title": "Video Lesson",
            "lesson_type": "video",
            "content": {
                "video_url": "https://example.com/video.mp4",
                "transcript": "Video transcript here",
            },
            "estimated_minutes": 15,
            "module_id": test_module.id,
        }
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json=lesson_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["lesson_type"] == "video"

    async def test_create_quiz_lesson(self, client, test_admin_user, test_module):
        """Test creating a quiz lesson."""
        token = await get_admin_token(client)
        lesson_data = {
            "title": "Quiz Lesson",
            "lesson_type": "quiz",
            "content": {"instructions": "Answer the following questions"},
            "estimated_minutes": 20,
            "module_id": test_module.id,
        }
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json=lesson_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["lesson_type"] == "quiz"

    async def test_create_lesson_as_patron_forbidden(self, client, test_regular_user, test_module):
        """Test patron cannot create lessons."""
        token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Unauthorized Lesson",
                "lesson_type": "article",
                "content": {},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_create_lesson_in_nonexistent_module(self, client, test_admin_user):
        """Test creating lesson in nonexistent module fails."""
        token = await get_admin_token(client)
        response = await client.post(
            "/api/v1/learning/modules/99999/lessons",
            json={
                "title": "Orphan Lesson",
                "lesson_type": "article",
                "content": {},
                "module_id": 99999,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestLessonUpdate:
    """Tests for lesson updates."""

    async def test_update_lesson_as_admin(self, client, test_admin_user, test_lesson):
        """Test admin can update a lesson."""
        token = await get_admin_token(client)
        update_data = {
            "title": "Updated Lesson Title",
            "content": {"text": "Updated content"},
        }
        response = await client.put(
            f"/api/v1/learning/lessons/{test_lesson.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Lesson Title"

    async def test_update_lesson_type(self, client, test_admin_user, test_lesson):
        """Test changing lesson type."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/lessons/{test_lesson.id}",
            json={
                "lesson_type": "video",
                "content": {"video_url": "https://example.com/video.mp4"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["lesson_type"] == "video"

    async def test_update_lesson_accessibility_fields(self, client, test_admin_user, test_lesson):
        """Test updating lesson accessibility fields."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/lessons/{test_lesson.id}",
            json={
                "sensory_notes": "Contains audio content",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["sensory_notes"] == "Contains audio content"


@pytest.mark.integration
class TestLessonDelete:
    """Tests for lesson deletion."""

    async def test_delete_lesson_as_admin(self, client, test_db, test_admin_user, test_module):
        """Test admin can delete a lesson."""
        from app.models.learning import Lesson

        # Create a lesson to delete
        lesson = Lesson(
            module_id=test_module.id,
            title="Lesson To Delete",
            lesson_type="article",
            content={"text": "Will be deleted"},
            sort_order=0,
        )
        test_db.add(lesson)
        await test_db.commit()
        await test_db.refresh(lesson)
        lesson_id = lesson.id

        token = await get_admin_token(client)
        response = await client.delete(
            f"/api/v1/learning/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    async def test_delete_nonexistent_lesson(self, client, test_admin_user):
        """Test deleting nonexistent lesson returns 404."""
        token = await get_admin_token(client)
        response = await client.delete(
            "/api/v1/learning/lessons/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


# ============ CONTENT REORDERING TESTS ============


@pytest.mark.integration
class TestModuleReordering:
    """Tests for reordering modules within courses."""

    async def test_reorder_modules_via_sort_order(
        self, client, test_db, test_admin_user, test_course
    ):
        """Test reordering modules by updating sort_order."""
        from app.models.learning import Module

        # Create multiple modules
        module1 = Module(
            course_id=test_course.id,
            title="Module 1",
            sort_order=0,
        )
        module2 = Module(
            course_id=test_course.id,
            title="Module 2",
            sort_order=1,
        )
        module3 = Module(
            course_id=test_course.id,
            title="Module 3",
            sort_order=2,
        )
        test_db.add_all([module1, module2, module3])
        await test_db.commit()
        await test_db.refresh(module1)
        await test_db.refresh(module2)
        await test_db.refresh(module3)

        token = await get_admin_token(client)

        # Move module 3 to the front
        response = await client.put(
            f"/api/v1/learning/modules/{module3.id}",
            json={"sort_order": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["sort_order"] == 0

        # Verify new order via course details
        course_response = await client.get(
            f"/api/v1/learning/courses/{test_course.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert course_response.status_code == 200


@pytest.mark.integration
class TestLessonReordering:
    """Tests for reordering lessons within modules."""

    async def test_reorder_lessons_via_sort_order(
        self, client, test_db, test_admin_user, test_module
    ):
        """Test reordering lessons by updating sort_order."""
        from app.models.learning import Lesson

        # Create multiple lessons
        lesson1 = Lesson(
            module_id=test_module.id,
            title="Lesson 1",
            lesson_type="article",
            content={"text": "Content 1"},
            sort_order=0,
        )
        lesson2 = Lesson(
            module_id=test_module.id,
            title="Lesson 2",
            lesson_type="article",
            content={"text": "Content 2"},
            sort_order=1,
        )
        lesson3 = Lesson(
            module_id=test_module.id,
            title="Lesson 3",
            lesson_type="article",
            content={"text": "Content 3"},
            sort_order=2,
        )
        test_db.add_all([lesson1, lesson2, lesson3])
        await test_db.commit()
        await test_db.refresh(lesson1)
        await test_db.refresh(lesson2)
        await test_db.refresh(lesson3)

        token = await get_admin_token(client)

        # Move lesson 3 to position 1
        response = await client.put(
            f"/api/v1/learning/lessons/{lesson3.id}",
            json={"sort_order": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["sort_order"] == 1


# ============ PUBLISHING WORKFLOW TESTS ============


@pytest.mark.integration
class TestPublishingWorkflow:
    """Tests for course publishing workflow."""

    async def test_published_course_visible_to_public(self, client, test_published_course):
        """A published course (lifecycle_stage=published) appears in the
        public listing."""
        response = await client.get("/api/v1/learning/courses")
        assert response.status_code == 200
        titles = [c["title"] for c in response.json()]
        assert test_published_course.title in titles

    async def test_unpublished_course_hidden_from_public(self, client, test_course):
        """A non-published course (lifecycle_stage=draft) is hidden from
        the public listing."""
        response = await client.get("/api/v1/learning/courses")
        assert response.status_code == 200
        course_ids = [c["id"] for c in response.json()]
        assert test_course.id not in course_ids

    async def test_patron_cannot_update_course(self, client, test_regular_user, test_course):
        """A patron cannot mutate a course (require_staff -> 403). Auth
        is enforced at the dependency layer, before body validation."""
        token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"title": "Patron Edit Attempt"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


# ============ PREREQUISITE MANAGEMENT TESTS ============


@pytest.mark.integration
class TestPrerequisiteManagement:
    """Tests for course prerequisite management."""

    async def test_create_course_with_prerequisites(
        self, client, test_db, test_admin_user, test_published_course
    ):
        """Test creating a course with prerequisites."""
        token = await get_admin_token(client)
        course_data = {
            "title": "Advanced Course",
            "description": "Requires completing another course first",
            "access_level": "patron",
            "prerequisite_course_ids": [test_published_course.id],
        }
        response = await client.post(
            "/api/v1/learning/courses",
            json=course_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert test_published_course.id in response.json()["prerequisite_course_ids"]

    async def test_update_course_prerequisites(
        self, client, test_admin_user, test_course, test_published_course
    ):
        """Test updating course prerequisites."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"prerequisite_course_ids": [test_published_course.id]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert test_published_course.id in response.json()["prerequisite_course_ids"]

    async def test_remove_course_prerequisites(
        self, client, test_admin_user, test_course, test_published_course
    ):
        """Test removing course prerequisites."""
        token = await get_admin_token(client)

        # First add prerequisites
        await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"prerequisite_course_ids": [test_published_course.id]},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Then remove them
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"prerequisite_course_ids": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["prerequisite_course_ids"] == []

    async def test_cannot_set_self_as_prerequisite(self, client, test_admin_user, test_course):
        """Test course cannot require itself as prerequisite."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"prerequisite_course_ids": [test_course.id]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "circular" in _error_detail(response).lower()

    async def test_cannot_create_circular_prerequisites(self, client, test_db, test_admin_user):
        """Test circular prerequisite dependencies are rejected."""
        from app.models.learning import Course, CourseLifecycleStage

        # Create course A
        course_a = Course(
            title="Course A",
            description="First course",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        test_db.add(course_a)
        await test_db.commit()
        await test_db.refresh(course_a)

        # Create course B that requires A
        course_b = Course(
            title="Course B",
            description="Second course",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
            prerequisite_course_ids=[course_a.id],
        )
        test_db.add(course_b)
        await test_db.commit()
        await test_db.refresh(course_b)

        token = await get_admin_token(client)

        # Try to make A require B (creates cycle A->B->A)
        response = await client.put(
            f"/api/v1/learning/courses/{course_a.id}",
            json={"prerequisite_course_ids": [course_b.id]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "circular" in _error_detail(response).lower()

    async def test_prerequisite_with_nonexistent_course(self, client, test_admin_user, test_course):
        """Test setting nonexistent course as prerequisite fails."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"prerequisite_course_ids": [99999]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "do not exist" in _error_detail(response).lower()


# ============ ACCESS LEVEL TESTS ============


@pytest.mark.integration
class TestAccessLevelManagement:
    """Tests for course access level management."""

    async def test_create_staff_only_course(self, client, test_admin_user):
        """Test creating a staff-only course."""
        token = await get_admin_token(client)
        course_data = {
            "title": "Staff Training Course",
            "description": "Only for staff",
            "access_level": "staff",
        }
        response = await client.post(
            "/api/v1/learning/courses",
            json=course_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["access_level"] == "staff"

    async def test_create_admin_only_course(self, client, test_admin_user):
        """Test creating an admin-only course."""
        token = await get_admin_token(client)
        course_data = {
            "title": "Admin Training Course",
            "description": "Only for admins",
            "access_level": "admin",
        }
        response = await client.post(
            "/api/v1/learning/courses",
            json=course_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["access_level"] == "admin"

    async def test_patron_cannot_access_staff_course(self, client, test_db, test_regular_user):
        """Test patron cannot access staff-only course."""
        from app.models.learning import Course, CourseLifecycleStage

        # Create staff-only published course
        staff_course = Course(
            title="Staff Only Course",
            description="Restricted",
            access_level="staff",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        )
        test_db.add(staff_course)
        await test_db.commit()
        await test_db.refresh(staff_course)

        token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.get(
            f"/api/v1/learning/courses/{staff_course.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_staff_can_access_staff_course(self, client, test_db, test_staff_user):
        """Test staff can access staff-only course."""
        from app.models.learning import Course, CourseLifecycleStage

        # Create staff-only published course
        staff_course = Course(
            title="Staff Access Course",
            description="For staff",
            access_level="staff",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        )
        test_db.add(staff_course)
        await test_db.commit()
        await test_db.refresh(staff_course)

        token = await get_user_token(client, "staffuser@example.com", "StaffPassword123!")
        response = await client.get(
            f"/api/v1/learning/courses/{staff_course.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


# ============ FULL WORKFLOW TESTS ============


@pytest.mark.integration
class TestFullCourseWorkflow:
    """End-to-end tests for complete course management workflows."""

    async def test_complete_course_creation_workflow(self, client, test_admin_user):
        """Test creating a complete course with modules and lessons."""
        token = await get_admin_token(client)

        # 1. Create course
        course_response = await client.post(
            "/api/v1/learning/courses",
            json={
                "title": "Complete Workflow Course",
                "description": "Testing the full workflow",
                "difficulty": "beginner",
                "estimated_minutes": 60,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert course_response.status_code == 201
        course_id = course_response.json()["id"]

        # 2. Add first module
        module1_response = await client.post(
            f"/api/v1/learning/courses/{course_id}/modules",
            json={
                "title": "Introduction Module",
                "description": "Getting started",
                "sort_order": 0,
                "course_id": course_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert module1_response.status_code == 201
        module1_id = module1_response.json()["id"]

        # 3. Add lesson to first module
        lesson1_response = await client.post(
            f"/api/v1/learning/modules/{module1_id}/lessons",
            json={
                "title": "Welcome Lesson",
                "lesson_type": "article",
                "content": {"text": "Welcome to the course!"},
                "estimated_minutes": 5,
                "sort_order": 0,
                "module_id": module1_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert lesson1_response.status_code == 201

        # 4. Add second module
        module2_response = await client.post(
            f"/api/v1/learning/courses/{course_id}/modules",
            json={
                "title": "Core Content Module",
                "description": "Main learning material",
                "sort_order": 1,
                "course_id": course_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert module2_response.status_code == 201
        module2_id = module2_response.json()["id"]

        # 5. Add quiz to second module
        quiz_response = await client.post(
            f"/api/v1/learning/modules/{module2_id}/lessons",
            json={
                "title": "Knowledge Check",
                "lesson_type": "quiz",
                "content": {"instructions": "Test your knowledge"},
                "estimated_minutes": 15,
                "sort_order": 0,
                "module_id": module2_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert quiz_response.status_code == 201

        # 6. Publish the course via the lifecycle transition endpoint
        #    (draft -> published directly; is_published is no longer a
        #    writable field — lifecycle_stage is the source of truth).
        publish_response = await client.post(
            f"/api/v1/learning/admin/courses/{course_id}/transition",
            json={"to_stage": "published"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert publish_response.status_code == 200, publish_response.text
        assert publish_response.json()["is_published"] is True
        assert publish_response.json()["lifecycle_stage"] == "published"

        # 7. Verify course is in public listing
        list_response = await client.get("/api/v1/learning/courses")
        assert list_response.status_code == 200
        titles = [c["title"] for c in list_response.json()]
        assert "Complete Workflow Course" in titles

        # 8. Get full course details with structure
        detail_response = await client.get(f"/api/v1/learning/courses/{course_id}")
        assert detail_response.status_code == 200
        course_data = detail_response.json()
        assert len(course_data["modules"]) == 2
        assert course_data["modules"][0]["title"] == "Introduction Module"
        assert len(course_data["modules"][0]["lessons"]) == 1


# ============ ADDITIONAL LESSON TYPE TESTS ============


@pytest.mark.integration
class TestLessonTypes:
    """Tests for different lesson types including sandbox and lab."""

    async def test_create_sandbox_lesson(self, client, test_admin_user, test_module):
        """Test creating a sandbox lesson for interactive practice."""
        token = await get_admin_token(client)
        lesson_data = {
            "title": "Practice Environment",
            "lesson_type": "sandbox",
            "content": {
                "environment": "python",
                "initial_code": "# Write your code here\n",
                "instructions": "Practice Python basics in this sandbox",
                "validation_tests": ["assert True"],
            },
            "estimated_minutes": 30,
            "sort_order": 0,
            "module_id": test_module.id,
        }
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json=lesson_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["lesson_type"] == "sandbox"
        assert data["title"] == "Practice Environment"
        assert data["content"]["environment"] == "python"

    async def test_create_lab_lesson(self, client, test_admin_user, test_module):
        """Test creating a lab lesson for guided exercises."""
        token = await get_admin_token(client)
        lesson_data = {
            "title": "Hands-on Lab",
            "lesson_type": "lab",
            "content": {
                "objectives": ["Learn database queries", "Practice CRUD operations"],
                "setup_instructions": "Download the starter files",
                "steps": [
                    {"title": "Step 1", "description": "Create a database connection"},
                    {"title": "Step 2", "description": "Execute your first query"},
                ],
                "submission_requirements": "Submit your completed code",
            },
            "estimated_minutes": 45,
            "sort_order": 1,
            "module_id": test_module.id,
        }
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json=lesson_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["lesson_type"] == "lab"
        assert data["content"]["objectives"] == [
            "Learn database queries",
            "Practice CRUD operations",
        ]

    async def test_update_lesson_type_article_to_quiz(self, client, test_admin_user, test_lesson):
        """Test converting an article lesson to a quiz."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/lessons/{test_lesson.id}",
            json={
                "lesson_type": "quiz",
                "content": {
                    "instructions": "Answer the following questions",
                    "passing_score": 80,
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["lesson_type"] == "quiz"
        assert data["content"]["passing_score"] == 80


# ============ BATCH REORDERING TESTS ============


@pytest.mark.integration
class TestBatchReordering:
    """Tests for batch reordering of modules and lessons."""

    async def test_reorder_multiple_modules(self, client, test_db, test_admin_user, test_course):
        """Test reordering multiple modules at once."""
        from app.models.learning import Module

        # Create multiple modules with initial order
        modules = []
        for i in range(4):
            module = Module(
                course_id=test_course.id,
                title=f"Module {i + 1}",
                description=f"Description {i + 1}",
                sort_order=i,
            )
            test_db.add(module)
            modules.append(module)

        await test_db.commit()
        for m in modules:
            await test_db.refresh(m)

        token = await get_admin_token(client)

        # Reorder: Move module 4 to position 0, module 2 to position 1
        # New order should be: Module 4, Module 2, Module 1, Module 3
        await client.put(
            f"/api/v1/learning/modules/{modules[3].id}",
            json={"sort_order": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        await client.put(
            f"/api/v1/learning/modules/{modules[1].id}",
            json={"sort_order": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        await client.put(
            f"/api/v1/learning/modules/{modules[0].id}",
            json={"sort_order": 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        await client.put(
            f"/api/v1/learning/modules/{modules[2].id}",
            json={"sort_order": 3},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify order via course details
        course_response = await client.get(
            f"/api/v1/learning/courses/{test_course.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert course_response.status_code == 200
        course_data = course_response.json()
        sorted_modules = sorted(course_data["modules"], key=lambda x: x["sort_order"])
        assert sorted_modules[0]["title"] == "Module 4"
        assert sorted_modules[1]["title"] == "Module 2"
        assert sorted_modules[2]["title"] == "Module 1"
        assert sorted_modules[3]["title"] == "Module 3"

    async def test_reorder_multiple_lessons(self, client, test_db, test_admin_user, test_module):
        """Test reordering multiple lessons within a module."""
        from app.models.learning import Lesson

        # Create multiple lessons
        lessons = []
        for i in range(5):
            lesson = Lesson(
                module_id=test_module.id,
                title=f"Lesson {i + 1}",
                lesson_type="article",
                content={"text": f"Content {i + 1}"},
                sort_order=i,
            )
            test_db.add(lesson)
            lessons.append(lesson)

        await test_db.commit()
        for lsn in lessons:
            await test_db.refresh(lsn)

        token = await get_admin_token(client)

        # Move last lesson to first position
        response = await client.put(
            f"/api/v1/learning/lessons/{lessons[4].id}",
            json={"sort_order": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["sort_order"] == 0

    async def test_reorder_preserves_other_data(self, client, test_admin_user, test_module):
        """Test that reordering preserves lesson content and metadata."""
        token = await get_admin_token(client)

        # Create a lesson with detailed content
        original_content = {
            "text": "Important lesson content",
            "key_points": ["Point 1", "Point 2"],
        }
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Detailed Lesson",
                "lesson_type": "article",
                "content": original_content,
                "estimated_minutes": 20,
                "sensory_notes": "Contains images",
                "sort_order": 5,
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        # Reorder the lesson
        reorder_response = await client.put(
            f"/api/v1/learning/lessons/{lesson_id}",
            json={"sort_order": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert reorder_response.status_code == 200
        data = reorder_response.json()

        # Verify all original data is preserved
        assert data["title"] == "Detailed Lesson"
        assert data["lesson_type"] == "article"
        assert data["content"] == original_content
        assert data["estimated_minutes"] == 20
        assert data["sensory_notes"] == "Contains images"
        assert data["sort_order"] == 0


# ============ DELETION CASCADE TESTS ============


@pytest.mark.integration
class TestDeletionCascades:
    """Tests for cascade deletion of course content."""

    async def test_delete_course_cascades_to_modules_and_lessons(
        self, client, test_db, test_admin_user
    ):
        """Test that deleting a course archives it and cascades that
        archive to its modules/lessons — nothing destroyed, nothing
        orphaned (maintainer decision 2026-07-09).

        Modules/lessons have no lifecycle_stage of their own; every route
        that serves them gates purely on the parent course's stage, so the
        cascade is verified two ways: (1) the rows themselves are untouched
        in the DB, and (2) the patron-facing routes that would surface them
        now 404 instead of leaking archived content.
        """
        from app.models.learning import Course, CourseLifecycleStage, Lesson, Module
        from sqlalchemy import select

        # Create course with modules and lessons
        course = Course(
            title="Cascade Test Course",
            description="Will be archived with all content",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        )
        test_db.add(course)
        await test_db.commit()
        await test_db.refresh(course)

        module = Module(
            course_id=course.id,
            title="Test Module",
            sort_order=0,
        )
        test_db.add(module)
        await test_db.commit()
        await test_db.refresh(module)

        lessons = []
        for i in range(3):
            lesson = Lesson(
                module_id=module.id,
                title=f"Test Lesson {i + 1}",
                lesson_type="article",
                content={"text": f"Content {i + 1}"},
                sort_order=i,
            )
            test_db.add(lesson)
            lessons.append(lesson)

        await test_db.commit()
        for lsn in lessons:
            await test_db.refresh(lsn)

        # Store IDs for verification
        course_id = course.id
        module_id = module.id
        lesson_ids = [lsn.id for lsn in lessons]

        token = await get_admin_token(client)

        # Delete the course
        response = await client.delete(
            f"/api/v1/learning/courses/{course_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Course row is untouched except for the lifecycle flip.
        course_result = await test_db.execute(select(Course).where(Course.id == course_id))
        archived_course = course_result.scalar_one_or_none()
        assert archived_course is not None
        assert archived_course.deleted_at is None
        assert CourseLifecycleStage(archived_course.lifecycle_stage) == (
            CourseLifecycleStage.ARCHIVED
        )

        # Module row is untouched — still attached to the archived course.
        module_result = await test_db.execute(select(Module).where(Module.id == module_id))
        surviving_module = module_result.scalar_one_or_none()
        assert surviving_module is not None
        assert surviving_module.course_id == course_id

        # All lesson rows are untouched.
        for lesson_id in lesson_ids:
            lesson_result = await test_db.execute(select(Lesson).where(Lesson.id == lesson_id))
            surviving_lesson = lesson_result.scalar_one_or_none()
            assert surviving_lesson is not None
            assert surviving_lesson.module_id == module_id

        # Patron-facing views no longer surface the archived course or its
        # children — the cascade that matters to a reader.
        anon_course_resp = await client.get(f"/api/v1/learning/courses/{course_id}")
        assert anon_course_resp.status_code == 404

        anon_modules_resp = await client.get(f"/api/v1/learning/courses/{course_id}/modules")
        assert anon_modules_resp.status_code in (401, 404)

        listing_resp = await client.get("/api/v1/learning/courses")
        listing_ids = {c["id"] for c in listing_resp.json()}
        assert course_id not in listing_ids

        # Staff/admin still see it (archived, not gone) — recoverable via
        # the existing archived -> draft "Restore" transition.
        admin_course_resp = await client.get(
            f"/api/v1/learning/courses/{course_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert admin_course_resp.status_code == 200
        assert admin_course_resp.json()["lifecycle_stage"] == "archived"

    async def test_delete_module_preserves_course(
        self, client, test_db, test_admin_user, test_course
    ):
        """Test that deleting a module preserves the parent course."""
        from app.models.learning import Course, CourseLifecycleStage, Module
        from sqlalchemy import select

        # Create module
        module = Module(
            course_id=test_course.id,
            title="Module to Delete",
            sort_order=0,
        )
        test_db.add(module)
        await test_db.commit()
        await test_db.refresh(module)
        module_id = module.id

        token = await get_admin_token(client)

        # Delete the module
        response = await client.delete(
            f"/api/v1/learning/modules/{module_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Verify course still exists
        course_result = await test_db.execute(select(Course).where(Course.id == test_course.id))
        assert course_result.scalar_one_or_none() is not None


# ============ XP REWARD CONFIGURATION TESTS ============


@pytest.mark.integration
class TestXPRewardConfiguration:
    """Tests for XP reward configuration on courses and lessons."""

    async def test_create_course_with_xp_reward(self, client, test_admin_user):
        """Test creating a course with custom XP reward."""
        token = await get_admin_token(client)
        response = await client.post(
            "/api/v1/learning/courses",
            json={
                "title": "High XP Course",
                "description": "Earn lots of XP",
                "xp_reward": 500,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["xp_reward"] == 500

    async def test_course_default_xp_reward(self, client, test_admin_user):
        """Test that course has default XP reward when not specified."""
        token = await get_admin_token(client)
        response = await client.post(
            "/api/v1/learning/courses",
            json={
                "title": "Default XP Course",
                "description": "Uses default XP",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        # Default XP reward is 100 according to model
        assert response.json()["xp_reward"] == 100

    async def test_update_course_xp_reward(self, client, test_admin_user, test_course):
        """Test updating course XP reward."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"xp_reward": 250},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["xp_reward"] == 250

    async def test_create_lesson_with_xp_reward(self, client, test_admin_user, test_module):
        """Test creating a lesson with custom XP reward."""
        token = await get_admin_token(client)
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Bonus XP Lesson",
                "lesson_type": "article",
                "content": {"text": "Learn this for extra XP"},
                "xp_reward": 50,
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["xp_reward"] == 50

    async def test_lesson_default_xp_reward(self, client, test_admin_user, test_module):
        """Test that lesson has default XP reward when not specified."""
        token = await get_admin_token(client)
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Default XP Lesson",
                "lesson_type": "article",
                "content": {"text": "Standard content"},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        # Default XP reward is 10 according to model
        assert response.json()["xp_reward"] == 10


# ============ PUBLISHING WORKFLOW EDGE CASES ============


@pytest.mark.integration
class TestPublishingEdgeCases:
    """Edge case tests for publishing workflow."""

    async def test_published_course_access_levels(
        self, client, test_db, test_admin_user, test_regular_user, test_staff_user
    ):
        """Test access to published courses based on access level."""
        from app.models.learning import Course, CourseLifecycleStage

        # Create staff-only course
        staff_course = Course(
            title="Staff Only Published",
            description="Only staff can see this",
            access_level="staff",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        )
        test_db.add(staff_course)
        await test_db.commit()
        await test_db.refresh(staff_course)

        # Patron cannot access staff course
        patron_token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        patron_response = await client.get(
            f"/api/v1/learning/courses/{staff_course.id}",
            headers={"Authorization": f"Bearer {patron_token}"},
        )
        assert patron_response.status_code == 403

        # Staff can access
        staff_token = await get_user_token(client, "staffuser@example.com", "StaffPassword123!")
        staff_response = await client.get(
            f"/api/v1/learning/courses/{staff_course.id}",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert staff_response.status_code == 200

    async def test_unpublished_course_not_in_public_list_with_filters(
        self, client, test_db, test_admin_user
    ):
        """Test unpublished courses don't appear even with search/filter."""
        from app.models.learning import Course, CourseLifecycleStage

        # Create unpublished course with specific title
        unpub_course = Course(
            title="Secret Unpublished Course XYZ",
            description="Should not appear",
            lifecycle_stage=CourseLifecycleStage.DRAFT,
            difficulty="beginner",
        )
        test_db.add(unpub_course)
        await test_db.commit()

        # Public list should not show unpublished course
        response = await client.get("/api/v1/learning/courses")
        assert response.status_code == 200
        titles = [c["title"] for c in response.json()]
        assert "Secret Unpublished Course XYZ" not in titles


# ============ QUIZ PASSING THRESHOLD TESTS ============


@pytest.mark.integration
class TestQuizPassingThreshold:
    """Tests for quiz passing threshold configuration."""

    async def test_create_course_with_custom_passing_threshold(self, client, test_admin_user):
        """Test creating course with custom quiz passing threshold."""
        token = await get_admin_token(client)
        response = await client.post(
            "/api/v1/learning/courses",
            json={
                "title": "High Standards Course",
                "description": "Requires 90% to pass",
                "quiz_passing_threshold": 90,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["quiz_passing_threshold"] == 90

    async def test_update_course_passing_threshold(self, client, test_admin_user, test_course):
        """Test updating quiz passing threshold."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"quiz_passing_threshold": 80},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["quiz_passing_threshold"] == 80

    async def test_default_passing_threshold(self, client, test_admin_user):
        """Test default quiz passing threshold is 70."""
        token = await get_admin_token(client)
        response = await client.post(
            "/api/v1/learning/courses",
            json={
                "title": "Standard Threshold Course",
                "description": "Uses default threshold",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["quiz_passing_threshold"] == 70


# ============ COURSE ESTIMATED TIME TESTS ============


@pytest.mark.integration
class TestCourseEstimatedTime:
    """Tests for course and lesson estimated time configuration."""

    async def test_create_course_with_estimated_minutes(self, client, test_admin_user):
        """Test creating course with estimated completion time."""
        token = await get_admin_token(client)
        response = await client.post(
            "/api/v1/learning/courses",
            json={
                "title": "Timed Course",
                "description": "Takes about 2 hours",
                "estimated_minutes": 120,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["estimated_minutes"] == 120

    async def test_update_lesson_estimated_minutes(self, client, test_admin_user, test_lesson):
        """Test updating lesson estimated time."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/lessons/{test_lesson.id}",
            json={"estimated_minutes": 25},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["estimated_minutes"] == 25


# ============ SENSORY WARNING TESTS ============


@pytest.mark.integration
class TestSensoryWarnings:
    """Tests for sensory warnings and accessibility notes."""

    async def test_create_course_with_sensory_warning(self, client, test_admin_user):
        """Test creating course with sensory warning for accessibility."""
        token = await get_admin_token(client)
        response = await client.post(
            "/api/v1/learning/courses",
            json={
                "title": "Visual Course",
                "description": "Contains visual content",
                "sensory_warning": "Contains flashing images and rapid color changes. Photosensitive individuals should use caution.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "flashing images" in data["sensory_warning"]

    async def test_lesson_sensory_notes(self, client, test_admin_user, test_module):
        """Test creating lesson with sensory notes."""
        token = await get_admin_token(client)
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Audio Lesson",
                "lesson_type": "video",
                "content": {"video_url": "https://example.com/video.mp4"},
                "sensory_notes": "Contains background music and sound effects",
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["sensory_notes"] == "Contains background music and sound effects"

    async def test_update_sensory_warning(self, client, test_admin_user, test_course):
        """Test updating course sensory warning."""
        token = await get_admin_token(client)
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={
                "sensory_warning": "Updated: Now includes audio narration",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["sensory_warning"] == "Updated: Now includes audio narration"


# ============ QUIZ QUESTION TESTS ============


@pytest.mark.integration
class TestQuizQuestions:
    """Tests for quiz question management within lessons."""

    async def test_create_quiz_lesson_with_questions(
        self, client, test_db, test_admin_user, test_module
    ):
        """Test creating a quiz lesson and adding questions directly to database."""
        from app.models.learning import Lesson, QuizQuestion

        # Create quiz lesson
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Knowledge Check Quiz",
                "lesson_type": "quiz",
                "content": {"instructions": "Answer all questions"},
                "sort_order": 0,
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert lesson_response.status_code == 201
        lesson_id = lesson_response.json()["id"]

        # Add quiz questions directly to database
        questions = [
            QuizQuestion(
                lesson_id=lesson_id,
                question_text="What is 2 + 2?",
                question_type="multiple_choice",
                options=[
                    {"text": "3", "is_correct": False},
                    {"text": "4", "is_correct": True},
                    {"text": "5", "is_correct": False},
                ],
                explanation="Basic addition",
                sort_order=0,
            ),
            QuizQuestion(
                lesson_id=lesson_id,
                question_text="What color is the sky?",
                question_type="multiple_choice",
                options=[
                    {"text": "Red", "is_correct": False},
                    {"text": "Blue", "is_correct": True},
                    {"text": "Green", "is_correct": False},
                ],
                explanation="Common observation",
                sort_order=1,
            ),
        ]
        for q in questions:
            test_db.add(q)
        await test_db.commit()

        # Verify questions were added
        from sqlalchemy import select

        result = await test_db.execute(
            select(QuizQuestion).where(QuizQuestion.lesson_id == lesson_id)
        )
        saved_questions = result.scalars().all()
        assert len(saved_questions) == 2
        assert saved_questions[0].question_text == "What is 2 + 2?"

    async def test_quiz_question_options_structure(
        self, client, test_db, test_admin_user, test_module
    ):
        """Test that quiz question options are stored correctly."""
        from app.models.learning import Lesson, QuizQuestion

        # Create quiz lesson
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Options Test Quiz",
                "lesson_type": "quiz",
                "content": {},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        # Create question with multiple options
        options = [
            {"text": "Option A", "is_correct": False},
            {"text": "Option B", "is_correct": True},
            {"text": "Option C", "is_correct": False},
            {"text": "Option D", "is_correct": False},
        ]
        question = QuizQuestion(
            lesson_id=lesson_id,
            question_text="Test question",
            options=options,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Verify options structure
        assert len(question.options) == 4
        assert question.options[1]["is_correct"] is True

    async def test_quiz_question_sort_order(self, client, test_db, test_admin_user, test_module):
        """Test quiz questions are ordered by sort_order."""
        from app.models.learning import QuizQuestion
        from sqlalchemy import select

        # Create quiz lesson
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Ordered Quiz",
                "lesson_type": "quiz",
                "content": {},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        # Create questions with specific order
        for i, text in enumerate(["Third", "First", "Second"]):
            sort = [2, 0, 1][i]  # Third=2, First=0, Second=1
            q = QuizQuestion(
                lesson_id=lesson_id,
                question_text=text,
                options=[{"text": "A", "is_correct": True}],
                sort_order=sort,
            )
            test_db.add(q)
        await test_db.commit()

        # Verify ordering
        result = await test_db.execute(
            select(QuizQuestion)
            .where(QuizQuestion.lesson_id == lesson_id)
            .order_by(QuizQuestion.sort_order)
        )
        questions = result.scalars().all()
        assert questions[0].question_text == "First"
        assert questions[1].question_text == "Second"
        assert questions[2].question_text == "Third"

    async def test_delete_quiz_lesson_cascades_to_questions(
        self, client, test_db, test_admin_user, test_module
    ):
        """Test that deleting a quiz lesson deletes its questions."""
        from app.models.learning import QuizQuestion
        from sqlalchemy import select

        # Create quiz lesson with questions
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Deletable Quiz",
                "lesson_type": "quiz",
                "content": {},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        question = QuizQuestion(
            lesson_id=lesson_id,
            question_text="Will be deleted",
            options=[{"text": "Yes", "is_correct": True}],
        )
        test_db.add(question)
        await test_db.commit()
        question_id = question.id

        # Delete the lesson
        delete_response = await client.delete(
            f"/api/v1/learning/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_response.status_code == 204

        # Verify question is deleted
        result = await test_db.execute(select(QuizQuestion).where(QuizQuestion.id == question_id))
        assert result.scalar_one_or_none() is None


# ============ LESSON RESOURCES TESTS ============


@pytest.mark.integration
class TestLessonResources:
    """Tests for lesson resource management."""

    async def test_create_lesson_resource(self, client, test_db, test_admin_user, test_module):
        """Test creating lesson resources attached to a lesson."""
        from app.models.learning import LessonResource

        # Create lesson
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Lesson with Resources",
                "lesson_type": "article",
                "content": {"text": "Read the attached materials"},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        # Add resources
        resources = [
            LessonResource(
                lesson_id=lesson_id,
                title="Study Guide PDF",
                description="Comprehensive study guide",
                resource_type="pdf",
                url="https://example.com/study-guide.pdf",
                sort_order=0,
            ),
            LessonResource(
                lesson_id=lesson_id,
                title="Practice Checklist",
                description="Step-by-step checklist",
                resource_type="checklist",
                url="https://example.com/checklist.pdf",
                sort_order=1,
            ),
        ]
        for r in resources:
            test_db.add(r)
        await test_db.commit()

        # Verify resources
        from sqlalchemy import select

        result = await test_db.execute(
            select(LessonResource).where(LessonResource.lesson_id == lesson_id)
        )
        saved_resources = result.scalars().all()
        assert len(saved_resources) == 2
        assert saved_resources[0].resource_type == "pdf"

    async def test_lesson_resource_types(self, client, test_db, test_admin_user, test_module):
        """Test different resource types can be created."""
        from app.models.learning import LessonResource

        # Create lesson
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Multi-Resource Lesson",
                "lesson_type": "article",
                "content": {"text": "Multiple resource types"},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        # Test all resource types
        resource_types = ["pdf", "checklist", "script", "video", "audio", "link"]
        for i, res_type in enumerate(resource_types):
            resource = LessonResource(
                lesson_id=lesson_id,
                title=f"{res_type.capitalize()} Resource",
                resource_type=res_type,
                url=f"https://example.com/{res_type}",
                sort_order=i,
            )
            test_db.add(resource)
        await test_db.commit()

        # Verify all types were created
        from sqlalchemy import select

        result = await test_db.execute(
            select(LessonResource).where(LessonResource.lesson_id == lesson_id)
        )
        saved_resources = result.scalars().all()
        assert len(saved_resources) == 6
        saved_types = {r.resource_type for r in saved_resources}
        assert saved_types == set(resource_types)

    async def test_delete_lesson_cascades_to_resources(
        self, client, test_db, test_admin_user, test_module
    ):
        """Test that deleting a lesson deletes its resources."""
        from app.models.learning import LessonResource
        from sqlalchemy import select

        # Create lesson with resource
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Lesson to Delete",
                "lesson_type": "article",
                "content": {},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        resource = LessonResource(
            lesson_id=lesson_id,
            title="Attached Resource",
            resource_type="pdf",
            url="https://example.com/file.pdf",
        )
        test_db.add(resource)
        await test_db.commit()
        resource_id = resource.id

        # Delete the lesson
        await client.delete(
            f"/api/v1/learning/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify resource is deleted
        result = await test_db.execute(
            select(LessonResource).where(LessonResource.id == resource_id)
        )
        assert result.scalar_one_or_none() is None


# ============ LESSON VARIANTS TESTS ============


@pytest.mark.integration
class TestLessonVariants:
    """Tests for lesson variant management (accessibility alternatives)."""

    async def test_create_lesson_variants(self, client, test_db, test_admin_user, test_module):
        """Test creating accessibility variants for a lesson."""
        from app.models.learning import LessonVariant

        # Create lesson
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Lesson with Variants",
                "lesson_type": "article",
                "content": {"text": "Main content"},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        # Add accessibility variants
        variants = [
            LessonVariant(
                lesson_id=lesson_id,
                variant_type="audio",
                content={
                    "audio_url": "https://example.com/audio.mp3",
                    "duration_seconds": 300,
                },
            ),
            LessonVariant(
                lesson_id=lesson_id,
                variant_type="text_only",
                content={"text": "Simplified text version without images"},
            ),
            LessonVariant(
                lesson_id=lesson_id,
                variant_type="summary",
                content={"text": "Brief summary of key points"},
            ),
        ]
        for v in variants:
            test_db.add(v)
        await test_db.commit()

        # Verify variants
        from sqlalchemy import select

        result = await test_db.execute(
            select(LessonVariant).where(LessonVariant.lesson_id == lesson_id)
        )
        saved_variants = result.scalars().all()
        assert len(saved_variants) == 3

    async def test_lesson_variant_types(self, client, test_db, test_admin_user, test_module):
        """Test different variant types for accessibility."""
        from app.models.learning import LessonVariant

        # Create lesson
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Full Variants Lesson",
                "lesson_type": "video",
                "content": {"video_url": "https://example.com/video.mp4"},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        # Test all variant types
        variant_configs = [
            ("audio", {"audio_url": "https://example.com/audio.mp3"}),
            ("visual", {"image_url": "https://example.com/image.png", "alt_text": "Description"}),
            ("text_only", {"text": "Plain text version"}),
            ("summary", {"text": "Quick summary"}),
            ("interactive", {"quiz_url": "https://example.com/quiz"}),
        ]
        for variant_type, content in variant_configs:
            variant = LessonVariant(
                lesson_id=lesson_id,
                variant_type=variant_type,
                content=content,
            )
            test_db.add(variant)
        await test_db.commit()

        # Verify all variants created
        from sqlalchemy import select

        result = await test_db.execute(
            select(LessonVariant).where(LessonVariant.lesson_id == lesson_id)
        )
        saved_variants = result.scalars().all()
        assert len(saved_variants) == 5
        types = {v.variant_type for v in saved_variants}
        assert "audio" in types
        assert "visual" in types
        assert "text_only" in types

    async def test_delete_lesson_cascades_to_variants(
        self, client, test_db, test_admin_user, test_module
    ):
        """Test that deleting a lesson deletes its variants."""
        from app.models.learning import LessonVariant
        from sqlalchemy import select

        # Create lesson with variant
        token = await get_admin_token(client)
        lesson_response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Variant Cascade Test",
                "lesson_type": "article",
                "content": {},
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        lesson_id = lesson_response.json()["id"]

        variant = LessonVariant(
            lesson_id=lesson_id,
            variant_type="audio",
            content={"audio_url": "https://example.com/audio.mp3"},
        )
        test_db.add(variant)
        await test_db.commit()
        variant_id = variant.id

        # Delete the lesson
        await client.delete(
            f"/api/v1/learning/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify variant is deleted
        result = await test_db.execute(select(LessonVariant).where(LessonVariant.id == variant_id))
        assert result.scalar_one_or_none() is None


# ============ ENROLLMENT PREREQUISITE ENFORCEMENT TESTS ============


@pytest.mark.integration
class TestEnrollmentPrerequisiteEnforcement:
    """Tests for prerequisite course enforcement during enrollment."""

    async def test_enroll_without_prerequisites_succeeds(
        self, client, test_db, test_admin_user, test_regular_user
    ):
        """Test enrolling in a course with no prerequisites."""
        from app.models.learning import Course, CourseLifecycleStage

        # Create published course with no prerequisites
        course = Course(
            title="No Prerequisites Course",
            description="Anyone can enroll",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        test_db.add(course)
        await test_db.commit()
        await test_db.refresh(course)

        # Enroll as regular user
        user_token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.post(
            f"/api/v1/learning/courses/{course.id}/enroll",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 201

    async def test_enroll_with_incomplete_prerequisites_fails(
        self, client, test_db, test_admin_user, test_regular_user
    ):
        """Test that enrollment fails when prerequisites are incomplete."""
        from app.models.learning import Course, CourseLifecycleStage

        # Create prerequisite course
        prereq_course = Course(
            title="Prerequisite Course",
            description="Must complete first",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        test_db.add(prereq_course)
        await test_db.commit()
        await test_db.refresh(prereq_course)

        # Create course requiring the prerequisite
        main_course = Course(
            title="Advanced Course",
            description="Requires prerequisite",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
            prerequisite_course_ids=[prereq_course.id],
        )
        test_db.add(main_course)
        await test_db.commit()
        await test_db.refresh(main_course)

        # Try to enroll without completing prerequisite
        user_token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.post(
            f"/api/v1/learning/courses/{main_course.id}/enroll",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 400
        assert "prerequisite" in _error_detail(response).lower()

    async def test_enroll_with_completed_prerequisites_succeeds(
        self, client, test_db, test_admin_user, test_regular_user
    ):
        """Test enrollment succeeds when prerequisites are completed."""
        from app.models.learning import Course, CourseLifecycleStage, Enrollment
        from datetime import datetime, timezone

        # Create prerequisite course
        prereq_course = Course(
            title="Completed Prerequisite",
            description="User completed this",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        test_db.add(prereq_course)
        await test_db.commit()
        await test_db.refresh(prereq_course)

        # Mark prerequisite as completed for user
        enrollment = Enrollment(
            user_id=test_regular_user.id,
            course_id=prereq_course.id,
            completed_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)
        await test_db.commit()

        # Create course requiring the prerequisite
        main_course = Course(
            title="Next Course",
            description="Can enroll after prereq",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
            prerequisite_course_ids=[prereq_course.id],
        )
        test_db.add(main_course)
        await test_db.commit()
        await test_db.refresh(main_course)

        # Enroll should succeed
        user_token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.post(
            f"/api/v1/learning/courses/{main_course.id}/enroll",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 201

    async def test_enroll_with_multiple_prerequisites_requires_all(
        self, client, test_db, test_admin_user, test_regular_user
    ):
        """Test that all prerequisites must be completed."""
        from app.models.learning import Course, CourseLifecycleStage, Enrollment
        from datetime import datetime, timezone

        # Create two prerequisite courses
        prereq1 = Course(
            title="Prereq 1",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        prereq2 = Course(
            title="Prereq 2",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        test_db.add(prereq1)
        test_db.add(prereq2)
        await test_db.commit()
        await test_db.refresh(prereq1)
        await test_db.refresh(prereq2)

        # Complete only one prerequisite
        enrollment = Enrollment(
            user_id=test_regular_user.id,
            course_id=prereq1.id,
            completed_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)
        await test_db.commit()

        # Create course requiring both
        main_course = Course(
            title="Requires Both",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
            prerequisite_course_ids=[prereq1.id, prereq2.id],
        )
        test_db.add(main_course)
        await test_db.commit()
        await test_db.refresh(main_course)

        # Enrollment should fail - only one prereq completed
        user_token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.post(
            f"/api/v1/learning/courses/{main_course.id}/enroll",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 400

    async def test_get_prerequisites_status_api(
        self, client, test_db, test_admin_user, test_regular_user
    ):
        """Test the prerequisites status API endpoint."""
        from app.models.learning import Course, CourseLifecycleStage, Enrollment
        from datetime import datetime, timezone

        # Create prerequisite courses
        prereq1 = Course(
            title="Completed Prereq",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        prereq2 = Course(
            title="Incomplete Prereq",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        test_db.add(prereq1)
        test_db.add(prereq2)
        await test_db.commit()
        await test_db.refresh(prereq1)
        await test_db.refresh(prereq2)

        # Complete first prereq
        enrollment = Enrollment(
            user_id=test_regular_user.id,
            course_id=prereq1.id,
            completed_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)
        await test_db.commit()

        # Create main course
        main_course = Course(
            title="Status Check Course",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
            prerequisite_course_ids=[prereq1.id, prereq2.id],
        )
        test_db.add(main_course)
        await test_db.commit()
        await test_db.refresh(main_course)

        # Check prerequisites status
        user_token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.get(
            f"/api/v1/learning/courses/{main_course.id}/prerequisites",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["all_met"] is False
        assert data["missing_count"] == 1
        assert len(data["prerequisites"]) == 2

    async def test_enrolled_but_not_completed_prerequisite_fails(
        self, client, test_db, test_admin_user, test_regular_user
    ):
        """Test that being enrolled in prerequisite is not enough - must be completed."""
        from app.models.learning import Course, CourseLifecycleStage, Enrollment

        # Create prerequisite course
        prereq = Course(
            title="In Progress Prereq",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        test_db.add(prereq)
        await test_db.commit()
        await test_db.refresh(prereq)

        # Enroll but don't complete
        enrollment = Enrollment(
            user_id=test_regular_user.id,
            course_id=prereq.id,
            # completed_at is None - not completed
        )
        test_db.add(enrollment)
        await test_db.commit()

        # Create main course
        main_course = Course(
            title="Needs Completion",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
            prerequisite_course_ids=[prereq.id],
        )
        test_db.add(main_course)
        await test_db.commit()
        await test_db.refresh(main_course)

        # Enrollment should fail
        user_token = await get_user_token(client, "regularuser@example.com", "UserPassword123!")
        response = await client.post(
            f"/api/v1/learning/courses/{main_course.id}/enroll",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 400


# ============ STAFF COURSE MANAGEMENT TESTS ============


@pytest.mark.integration
class TestStaffCourseManagement:
    """Tests verifying staff users can perform full CRUD on courses, modules, and lessons."""

    async def test_staff_can_list_all_courses(
        self, client, test_staff_user, test_course, test_published_course
    ):
        """Test staff can see all courses including unpublished via admin endpoint."""
        token = await get_staff_token(client)
        response = await client.get(
            "/api/v1/learning/admin/courses",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        courses = response.json()
        titles = [c["title"] for c in courses]
        assert "Test Course" in titles
        assert "Published Course" in titles

    async def test_staff_can_create_course(self, client, test_staff_user):
        """Test staff can create a course."""
        token = await get_staff_token(client)
        course_data = {
            "title": "Staff Created Course",
            "description": "Created by a staff member",
            "access_level": "patron",
            "difficulty": "intermediate",
            "estimated_minutes": 45,
        }
        response = await client.post(
            "/api/v1/learning/courses",
            json=course_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Staff Created Course"
        assert data["description"] == "Created by a staff member"
        assert data["is_published"] is False

    async def test_staff_can_update_course(self, client, test_staff_user, test_course):
        """Test staff can update a course."""
        token = await get_staff_token(client)
        response = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={
                "title": "Staff Updated Title",
                "description": "Updated by staff",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Staff Updated Title"
        assert data["description"] == "Updated by staff"

    async def test_staff_can_delete_course(self, client, test_db, test_staff_user):
        """Test staff can delete a course."""
        from app.models.learning import Course, CourseLifecycleStage

        course = Course(
            title="Staff Delete Target",
            description="Will be deleted by staff",
            lifecycle_stage=CourseLifecycleStage.DRAFT,
        )
        test_db.add(course)
        await test_db.commit()
        await test_db.refresh(course)

        token = await get_staff_token(client)
        response = await client.delete(
            f"/api/v1/learning/courses/{course.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    async def test_staff_can_create_module(self, client, test_staff_user, test_course):
        """Test staff can create a module in a course."""
        token = await get_staff_token(client)
        response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/modules",
            json={
                "title": "Staff Module",
                "description": "Created by staff",
                "sort_order": 0,
                "course_id": test_course.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["title"] == "Staff Module"

    async def test_staff_can_update_module(self, client, test_staff_user, test_module):
        """Test staff can update a module."""
        token = await get_staff_token(client)
        response = await client.put(
            f"/api/v1/learning/modules/{test_module.id}",
            json={"title": "Staff Updated Module"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Staff Updated Module"

    async def test_staff_can_delete_module(self, client, test_db, test_staff_user, test_course):
        """Test staff can delete a module."""
        from app.models.learning import Module

        module = Module(
            course_id=test_course.id,
            title="Staff Delete Module",
            sort_order=0,
        )
        test_db.add(module)
        await test_db.commit()
        await test_db.refresh(module)

        token = await get_staff_token(client)
        response = await client.delete(
            f"/api/v1/learning/modules/{module.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    async def test_staff_can_create_lesson(self, client, test_staff_user, test_module):
        """Test staff can create a lesson in a module."""
        token = await get_staff_token(client)
        response = await client.post(
            f"/api/v1/learning/modules/{test_module.id}/lessons",
            json={
                "title": "Staff Lesson",
                "lesson_type": "article",
                "content": {"text": "Created by staff"},
                "sort_order": 0,
                "module_id": test_module.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["title"] == "Staff Lesson"

    async def test_staff_can_update_lesson(self, client, test_staff_user, test_lesson):
        """Test staff can update a lesson."""
        token = await get_staff_token(client)
        response = await client.put(
            f"/api/v1/learning/lessons/{test_lesson.id}",
            json={
                "title": "Staff Updated Lesson",
                "content": {"text": "Updated by staff"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Staff Updated Lesson"

    async def test_staff_can_delete_lesson(self, client, test_db, test_staff_user, test_module):
        """Test staff can delete a lesson."""
        from app.models.learning import Lesson

        lesson = Lesson(
            module_id=test_module.id,
            title="Staff Delete Lesson",
            lesson_type="article",
            content={"text": "Will be deleted"},
            sort_order=0,
        )
        test_db.add(lesson)
        await test_db.commit()
        await test_db.refresh(lesson)

        token = await get_staff_token(client)
        response = await client.delete(
            f"/api/v1/learning/lessons/{lesson.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    async def test_staff_can_view_unpublished_course(self, client, test_staff_user, test_course):
        """Test staff can access unpublished course details."""
        token = await get_staff_token(client)
        response = await client.get(
            f"/api/v1/learning/courses/{test_course.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Test Course"
