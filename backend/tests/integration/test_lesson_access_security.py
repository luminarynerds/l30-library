# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Security tests for lesson and quiz access control.

Tests verify that:
1. Users cannot access lessons without enrollment
2. Users cannot complete lessons without enrollment
3. Users cannot submit quizzes without enrollment
4. Prerequisites are properly enforced at enrollment time
"""

import pytest
from datetime import datetime, timezone


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...}."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


@pytest.fixture
async def test_admin_user(test_db):
    """Create an admin user."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="security_admin@example.com",
        password_hash=hash_password("AdminPassword123!"),
        first_name="Security",
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
async def test_patron_user(test_db):
    """Create a patron user who is NOT enrolled in any course."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="unenrolled_patron@example.com",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Unenrolled",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_enrolled_patron(test_db):
    """Create a patron user who IS enrolled in a course."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="enrolled_patron@example.com",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Enrolled",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_course_with_lesson(test_db):
    """Create a published course with a module and lesson."""
    from app.models.learning import Course, CourseLifecycleStage, Lesson, Module

    course = Course(
        title="Security Test Course",
        description="Course for testing access control",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        difficulty="beginner",
        estimated_minutes=60,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    module = Module(
        course_id=course.id,
        title="Test Module",
        description="Module for testing",
        sort_order=0,
    )
    test_db.add(module)
    await test_db.commit()
    await test_db.refresh(module)

    lesson = Lesson(
        module_id=module.id,
        title="Test Lesson",
        lesson_type="article",
        content={"text": "This is lesson content"},
        estimated_minutes=10,
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.commit()
    await test_db.refresh(lesson)

    return {"course": course, "module": module, "lesson": lesson}


@pytest.fixture
async def test_course_with_quiz(test_db):
    """Create a published course with a quiz lesson."""
    from app.models.learning import Course, CourseLifecycleStage, Lesson, Module, QuizQuestion

    course = Course(
        title="Quiz Security Test Course",
        description="Course with quiz for testing access control",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        difficulty="beginner",
        estimated_minutes=30,
        quiz_passing_threshold=70,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    module = Module(
        course_id=course.id,
        title="Quiz Module",
        description="Module with quiz",
        sort_order=0,
    )
    test_db.add(module)
    await test_db.commit()
    await test_db.refresh(module)

    quiz_lesson = Lesson(
        module_id=module.id,
        title="Quiz Lesson",
        lesson_type="quiz",
        content={"instructions": "Answer the questions"},
        estimated_minutes=15,
        sort_order=0,
    )
    test_db.add(quiz_lesson)
    await test_db.commit()
    await test_db.refresh(quiz_lesson)

    # Add quiz questions
    question = QuizQuestion(
        lesson_id=quiz_lesson.id,
        question_text="What is 2 + 2?",
        question_type="multiple_choice",
        options=[
            {"text": "3", "is_correct": False},
            {"text": "4", "is_correct": True},
            {"text": "5", "is_correct": False},
        ],
        sort_order=0,
    )
    test_db.add(question)
    await test_db.commit()
    await test_db.refresh(question)

    return {"course": course, "module": module, "lesson": quiz_lesson, "question": question}


@pytest.fixture
async def prerequisite_course(test_db):
    """Create a prerequisite course."""
    from app.models.learning import Course, CourseLifecycleStage, Lesson, Module

    course = Course(
        title="Prerequisite Course",
        description="This course must be completed first",
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
        title="Prereq Module",
        sort_order=0,
    )
    test_db.add(module)
    await test_db.commit()
    await test_db.refresh(module)

    lesson = Lesson(
        module_id=module.id,
        title="Prereq Lesson",
        lesson_type="article",
        content={"text": "Prerequisite content"},
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.commit()
    await test_db.refresh(lesson)

    return {"course": course, "module": module, "lesson": lesson}


@pytest.fixture
async def course_with_prerequisites(test_db, prerequisite_course):
    """Create a course that requires the prerequisite course."""
    from app.models.learning import Course, CourseLifecycleStage, Lesson, Module

    course = Course(
        title="Advanced Course",
        description="Requires completing prerequisite first",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        difficulty="intermediate",
        estimated_minutes=60,
        prerequisite_course_ids=[prerequisite_course["course"].id],
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    module = Module(
        course_id=course.id,
        title="Advanced Module",
        sort_order=0,
    )
    test_db.add(module)
    await test_db.commit()
    await test_db.refresh(module)

    lesson = Lesson(
        module_id=module.id,
        title="Advanced Lesson",
        lesson_type="article",
        content={"text": "Advanced content"},
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.commit()
    await test_db.refresh(lesson)

    return {"course": course, "module": module, "lesson": lesson}


async def get_token(client, email, password):
    """Helper to get authentication token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": email, "password": password},
    )
    return response.json()["access_token"]


# ============ LESSON ACCESS TESTS ============


@pytest.mark.integration
class TestLessonAccessControl:
    """Tests for lesson access control."""

    async def test_unenrolled_user_cannot_access_lesson(
        self, client, test_patron_user, test_course_with_lesson
    ):
        """Test that unenrolled users cannot access lessons."""
        token = await get_token(client, "unenrolled_patron@example.com", "PatronPassword123!")
        lesson_id = test_course_with_lesson["lesson"].id

        response = await client.get(
            f"/api/v1/learning/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "enroll" in _error_detail(response).lower()

    async def test_enrolled_user_can_access_lesson(
        self, client, test_db, test_enrolled_patron, test_course_with_lesson
    ):
        """Test that enrolled users can access lessons."""
        from app.models.learning import Enrollment

        # Enroll the user
        enrollment = Enrollment(
            user_id=test_enrolled_patron.id,
            course_id=test_course_with_lesson["course"].id,
        )
        test_db.add(enrollment)
        await test_db.commit()

        token = await get_token(client, "enrolled_patron@example.com", "PatronPassword123!")
        lesson_id = test_course_with_lesson["lesson"].id

        response = await client.get(
            f"/api/v1/learning/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Test Lesson"


@pytest.mark.integration
class TestLessonCompletionSecurity:
    """Tests for lesson completion access control."""

    async def test_unenrolled_user_cannot_complete_lesson(
        self, client, test_patron_user, test_course_with_lesson
    ):
        """
        SECURITY TEST: Unenrolled users should NOT be able to mark lessons as complete.

        This tests for a potential bypass where users could complete lessons
        without being enrolled in the course.
        """
        token = await get_token(client, "unenrolled_patron@example.com", "PatronPassword123!")
        lesson_id = test_course_with_lesson["lesson"].id

        response = await client.post(
            f"/api/v1/learning/lessons/{lesson_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should fail - user is not enrolled
        assert response.status_code == 403, (
            f"SECURITY VULNERABILITY: Unenrolled user was able to complete lesson! "
            f"Expected 403, got {response.status_code}"
        )
        assert "enroll" in _error_detail(response).lower()

    async def test_enrolled_user_can_complete_lesson(
        self, client, test_db, test_enrolled_patron, test_course_with_lesson
    ):
        """Test that enrolled users CAN complete lessons."""
        from app.models.learning import Enrollment

        # Enroll the user
        enrollment = Enrollment(
            user_id=test_enrolled_patron.id,
            course_id=test_course_with_lesson["course"].id,
        )
        test_db.add(enrollment)
        await test_db.commit()

        token = await get_token(client, "enrolled_patron@example.com", "PatronPassword123!")
        lesson_id = test_course_with_lesson["lesson"].id

        response = await client.post(
            f"/api/v1/learning/lessons/{lesson_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "completed"


@pytest.mark.integration
class TestQuizSubmissionSecurity:
    """Tests for quiz submission access control."""

    async def test_unenrolled_user_cannot_submit_quiz(
        self, client, test_patron_user, test_course_with_quiz
    ):
        """
        SECURITY TEST: Unenrolled users should NOT be able to submit quiz answers.

        This tests for a potential bypass where users could submit quiz answers
        and potentially earn XP/progress without being enrolled.
        """
        token = await get_token(client, "unenrolled_patron@example.com", "PatronPassword123!")
        lesson_id = test_course_with_quiz["lesson"].id
        question_id = test_course_with_quiz["question"].id

        response = await client.post(
            f"/api/v1/learning/lessons/{lesson_id}/quiz/submit",
            json={
                "answers": [
                    {"question_id": question_id, "selected_option_index": 1}
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should fail - user is not enrolled
        assert response.status_code == 403, (
            f"SECURITY VULNERABILITY: Unenrolled user was able to submit quiz! "
            f"Expected 403, got {response.status_code}"
        )
        assert "enroll" in _error_detail(response).lower()

    async def test_unenrolled_user_cannot_start_quiz(
        self, client, test_patron_user, test_course_with_quiz
    ):
        """Test that unenrolled users cannot start a quiz attempt."""
        token = await get_token(client, "unenrolled_patron@example.com", "PatronPassword123!")
        lesson_id = test_course_with_quiz["lesson"].id

        response = await client.post(
            f"/api/v1/learning/lessons/{lesson_id}/quiz/start",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should fail - user is not enrolled
        assert response.status_code == 403
        assert "enroll" in _error_detail(response).lower()

    async def test_enrolled_user_can_submit_quiz(
        self, client, test_db, test_enrolled_patron, test_course_with_quiz
    ):
        """Test that enrolled users CAN submit quiz answers."""
        from app.models.learning import Enrollment

        # Enroll the user
        enrollment = Enrollment(
            user_id=test_enrolled_patron.id,
            course_id=test_course_with_quiz["course"].id,
        )
        test_db.add(enrollment)
        await test_db.commit()

        token = await get_token(client, "enrolled_patron@example.com", "PatronPassword123!")
        lesson_id = test_course_with_quiz["lesson"].id
        question_id = test_course_with_quiz["question"].id

        response = await client.post(
            f"/api/v1/learning/lessons/{lesson_id}/quiz/submit",
            json={
                "answers": [
                    {"question_id": question_id, "selected_option_index": 1}
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert "score" in response.json()


@pytest.mark.integration
class TestQuizHistoryIntegrity:
    """Tests for best-score-wins LessonProgress + quiz_attempts persistence."""

    async def test_retake_with_lower_score_does_not_regress_completed_lesson(
        self, client, test_db, test_enrolled_patron, test_course_with_quiz
    ):
        """A passing attempt followed by a lower retake must NOT regress quiz_score or status."""
        from app.models.learning import Enrollment, LessonProgress
        from sqlalchemy import select

        enrollment = Enrollment(
            user_id=test_enrolled_patron.id,
            course_id=test_course_with_quiz["course"].id,
        )
        test_db.add(enrollment)
        await test_db.commit()

        token = await get_token(client, "enrolled_patron@example.com", "PatronPassword123!")
        lesson_id = test_course_with_quiz["lesson"].id
        question_id = test_course_with_quiz["question"].id

        # First attempt: correct answer (option index 1 = "4" is_correct=True) -> 100%, passes.
        first = await client.post(
            f"/api/v1/learning/lessons/{lesson_id}/quiz/submit",
            json={"answers": [{"question_id": question_id, "selected_option_index": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first.status_code == 200
        assert first.json()["passed"] is True
        assert first.json()["percentage"] == 100.0

        # Second attempt: wrong answer (option index 0 = "3" is_correct=False) -> 0%.
        second = await client.post(
            f"/api/v1/learning/lessons/{lesson_id}/quiz/submit",
            json={"answers": [{"question_id": question_id, "selected_option_index": 0}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second.status_code == 200
        assert second.json()["passed"] is False

        progress_row = (
            await test_db.execute(
                select(LessonProgress).where(
                    LessonProgress.user_id == test_enrolled_patron.id,
                    LessonProgress.lesson_id == lesson_id,
                )
            )
        ).scalar_one()
        # Best-score-wins: prior 100% preserved, status stays completed.
        assert progress_row.quiz_score == 100
        assert progress_row.status == "completed"
        assert progress_row.completed_at is not None

    async def test_quiz_attempts_row_persists_per_submission(
        self, client, test_db, test_enrolled_patron, test_course_with_quiz
    ):
        """quiz_attempts count must go 0 -> 1 -> 2 across two submissions."""
        from app.models.learning import Enrollment, QuizAttempt
        from sqlalchemy import func, select

        enrollment = Enrollment(
            user_id=test_enrolled_patron.id,
            course_id=test_course_with_quiz["course"].id,
        )
        test_db.add(enrollment)
        await test_db.commit()

        token = await get_token(client, "enrolled_patron@example.com", "PatronPassword123!")
        lesson_id = test_course_with_quiz["lesson"].id
        question_id = test_course_with_quiz["question"].id

        async def attempt_count() -> int:
            result = await test_db.execute(
                select(func.count())
                .select_from(QuizAttempt)
                .where(
                    QuizAttempt.user_id == test_enrolled_patron.id,
                    QuizAttempt.lesson_id == lesson_id,
                )
            )
            return result.scalar_one()

        assert await attempt_count() == 0

        first = await client.post(
            f"/api/v1/learning/lessons/{lesson_id}/quiz/submit",
            json={"answers": [{"question_id": question_id, "selected_option_index": 0}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first.status_code == 200
        assert await attempt_count() == 1

        second = await client.post(
            f"/api/v1/learning/lessons/{lesson_id}/quiz/submit",
            json={"answers": [{"question_id": question_id, "selected_option_index": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second.status_code == 200
        assert await attempt_count() == 2

        # Verify the persisted answers shape includes is_correct.
        rows = (
            await test_db.execute(
                select(QuizAttempt)
                .where(
                    QuizAttempt.user_id == test_enrolled_patron.id,
                    QuizAttempt.lesson_id == lesson_id,
                )
                .order_by(QuizAttempt.id)
            )
        ).scalars().all()
        assert rows[0].passed is False
        assert rows[1].passed is True
        assert rows[0].answers[0]["is_correct"] is False
        assert rows[1].answers[0]["is_correct"] is True


# ============ PREREQUISITE ENFORCEMENT TESTS ============


@pytest.mark.integration
class TestPrerequisiteEnforcement:
    """Tests for course prerequisite enforcement."""

    async def test_cannot_enroll_without_completing_prerequisites(
        self, client, test_patron_user, course_with_prerequisites
    ):
        """Test that users cannot enroll in a course without completing prerequisites."""
        token = await get_token(client, "unenrolled_patron@example.com", "PatronPassword123!")
        course_id = course_with_prerequisites["course"].id

        response = await client.post(
            f"/api/v1/learning/courses/{course_id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "prerequisite" in _error_detail(response).lower()

    async def test_can_enroll_after_completing_prerequisites(
        self, client, test_db, test_enrolled_patron, prerequisite_course, course_with_prerequisites
    ):
        """Test that users CAN enroll after completing all prerequisites."""
        from app.models.learning import Enrollment, LessonProgress

        # Enroll in and complete the prerequisite course
        prereq_enrollment = Enrollment(
            user_id=test_enrolled_patron.id,
            course_id=prerequisite_course["course"].id,
            completed_at=datetime.now(timezone.utc),
        )
        test_db.add(prereq_enrollment)

        # Mark prerequisite lesson as completed
        prereq_progress = LessonProgress(
            user_id=test_enrolled_patron.id,
            lesson_id=prerequisite_course["lesson"].id,
            status="completed",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        test_db.add(prereq_progress)
        await test_db.commit()

        token = await get_token(client, "enrolled_patron@example.com", "PatronPassword123!")
        course_id = course_with_prerequisites["course"].id

        response = await client.post(
            f"/api/v1/learning/courses/{course_id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        assert response.json()["course_id"] == course_id

    async def test_prerequisite_status_shows_incomplete(
        self, client, test_patron_user, course_with_prerequisites
    ):
        """Test that prerequisite status endpoint correctly shows incomplete prerequisites."""
        token = await get_token(client, "unenrolled_patron@example.com", "PatronPassword123!")
        course_id = course_with_prerequisites["course"].id

        response = await client.get(
            f"/api/v1/learning/courses/{course_id}/prerequisites",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["all_met"] is False
        assert data["missing_count"] == 1
        assert len(data["prerequisites"]) == 1
        assert data["prerequisites"][0]["completed"] is False


# ============ STAFF/ADMIN BYPASS TESTS ============


@pytest.mark.integration
class TestStaffAdminBypass:
    """Tests to verify staff/admin can bypass enrollment requirements."""

    async def test_staff_can_access_lesson_without_enrollment(
        self, client, test_db, test_course_with_lesson
    ):
        """Test that staff can access lessons without being enrolled."""
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        staff_user = User(
            email="staff_access@example.com",
            password_hash=hash_password("StaffPassword123!"),
            first_name="Staff",
            last_name="Access",
            role=UserRole.STAFF,
            is_active=True,
            email_verified=True,
        )
        test_db.add(staff_user)
        await test_db.commit()

        token = await get_token(client, "staff_access@example.com", "StaffPassword123!")
        lesson_id = test_course_with_lesson["lesson"].id

        response = await client.get(
            f"/api/v1/learning/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Staff should be able to access without enrollment
        assert response.status_code == 200

    async def test_admin_can_access_lesson_without_enrollment(
        self, client, test_admin_user, test_course_with_lesson
    ):
        """Test that admins can access lessons without being enrolled."""
        token = await get_token(client, "security_admin@example.com", "AdminPassword123!")
        lesson_id = test_course_with_lesson["lesson"].id

        response = await client.get(
            f"/api/v1/learning/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Admin should be able to access without enrollment
        assert response.status_code == 200
