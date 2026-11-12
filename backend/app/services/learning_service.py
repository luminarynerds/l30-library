# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.learning import (
    Course, Enrollment, Lesson, LessonProgress, Module,
    ProgressStatus
)
from app.models.user import User


class LearningService:

    @staticmethod
    async def enroll_user_in_course(
        db: AsyncSession,
        user_id: int,
        course_id: int
    ) -> tuple[Enrollment, bool]:
        # Check if already enrolled
        result = await db.execute(
            select(Enrollment)
            .where(
                and_(
                    Enrollment.user_id == user_id,
                    Enrollment.course_id == course_id
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing, False

        # Look up course to compute due_at from its configured duration.
        course_result = await db.execute(
            select(Course).where(Course.id == course_id)
        )
        course = course_result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        due_at = (
            now + timedelta(days=course.duration_days)
            if course is not None and course.duration_days
            else None
        )

        # Create new enrollment
        enrollment = Enrollment(
            user_id=user_id,
            course_id=course_id,
            enrolled_at=now,
            due_at=due_at,
        )

        db.add(enrollment)
        return enrollment, True

    @staticmethod
    async def check_user_enrollment(
        db: AsyncSession,
        user_id: int,
        course_id: int
    ) -> bool:
        result = await db.execute(
            select(Enrollment)
            .where(
                and_(
                    Enrollment.user_id == user_id,
                    Enrollment.course_id == course_id
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def check_prerequisites_met(
        db: AsyncSession,
        user_id: int,
        course_id: int
    ) -> bool:
        # Get the course with its prerequisites
        result = await db.execute(
            select(Course).where(Course.id == course_id)
        )
        course = result.scalar_one_or_none()

        if not course or not course.prerequisite_course_ids:
            return True

        # Check if user has completed all prerequisites
        prerequisite_ids = course.prerequisite_course_ids or []

        completed = await db.execute(
            select(func.count(Enrollment.id))
            .where(
                and_(
                    Enrollment.user_id == user_id,
                    Enrollment.course_id.in_(prerequisite_ids),
                    Enrollment.completed_at.isnot(None)
                )
            )
        )
        completed_count = completed.scalar()

        return completed_count == len(prerequisite_ids)

    @staticmethod
    async def complete_course(
        db: AsyncSession,
        user_id: int,
        course_id: int
    ) -> Optional[Enrollment]:
        result = await db.execute(
            select(Enrollment)
            .where(
                and_(
                    Enrollment.user_id == user_id,
                    Enrollment.course_id == course_id
                )
            )
        )
        enrollment = result.scalar_one_or_none()

        if enrollment:
            enrollment.completed_at = datetime.now(timezone.utc)

        return enrollment

    @staticmethod
    async def get_user_enrollments(
        db: AsyncSession,
        user_id: int
    ) -> List[Enrollment]:
        result = await db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.course))
            .where(Enrollment.user_id == user_id)
            .order_by(Enrollment.enrolled_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def calculate_course_progress(
        db: AsyncSession,
        user_id: int,
        course_id: int
    ) -> Dict[str, Any]:
        # Subquery for lesson IDs in this course
        course_lessons = (
            select(Lesson.id)
            .join(Module, Module.id == Lesson.module_id)
            .where(Module.course_id == course_id)
        ).subquery()

        # Count total lessons
        total_result = await db.execute(
            select(func.count()).select_from(course_lessons)
        )
        total_lessons = total_result.scalar()

        if total_lessons == 0:
            return {
                "progress_percentage": 0.0,
                "completed_lessons": 0,
                "total_lessons": 0,
                "in_progress_lessons": 0
            }

        # Count completed and in-progress in a single query
        status_counts = await db.execute(
            select(
                LessonProgress.status,
                func.count(LessonProgress.id)
            )
            .where(
                and_(
                    LessonProgress.user_id == user_id,
                    LessonProgress.lesson_id.in_(select(course_lessons.c.id)),
                    LessonProgress.status.in_([
                        ProgressStatus.COMPLETED,
                        ProgressStatus.IN_PROGRESS
                    ])
                )
            )
            .group_by(LessonProgress.status)
        )
        counts_by_status = {row[0]: row[1] for row in status_counts.all()}

        completed_lessons = counts_by_status.get(ProgressStatus.COMPLETED, 0)
        in_progress_lessons = counts_by_status.get(ProgressStatus.IN_PROGRESS, 0)

        progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0

        return {
            "progress_percentage": round(progress_percentage, 2),
            "completed_lessons": completed_lessons,
            "total_lessons": total_lessons,
            "in_progress_lessons": in_progress_lessons
        }

    @staticmethod
    async def get_course_lessons(
        db: AsyncSession,
        course_id: int
    ) -> List[Lesson]:
        result = await db.execute(
            select(Lesson)
            .join(Module, Module.id == Lesson.module_id)
            .where(Module.course_id == course_id)
            .order_by(Module.sort_order, Lesson.sort_order)
        )
        return result.scalars().all()

    @staticmethod
    async def get_next_lesson(
        db: AsyncSession,
        user_id: int,
        course_id: int
    ) -> Optional[Lesson]:
        lessons = await LearningService.get_course_lessons(db, course_id)

        # Get user's lesson progress
        lesson_ids = [l.id for l in lessons]
        progress_result = await db.execute(
            select(LessonProgress)
            .where(
                and_(
                    LessonProgress.user_id == user_id,
                    LessonProgress.lesson_id.in_(lesson_ids)
                )
            )
        )
        progress_by_lesson = {
            p.lesson_id: p for p in progress_result.scalars().all()
        }

        # Find first uncompleted lesson
        for lesson in lessons:
            progress = progress_by_lesson.get(lesson.id)
            if not progress or progress.status != ProgressStatus.COMPLETED:
                return lesson

        return None

    @staticmethod
    async def get_lesson_progress(
        db: AsyncSession,
        user_id: int,
        lesson_id: int
    ) -> Optional[LessonProgress]:
        result = await db.execute(
            select(LessonProgress)
            .where(
                and_(
                    LessonProgress.user_id == user_id,
                    LessonProgress.lesson_id == lesson_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_course_with_details(
        db: AsyncSession,
        course_id: int
    ) -> Optional[Course]:
        result = await db.execute(
            select(Course)
            .options(
                selectinload(Course.modules)
                .selectinload(Module.lessons)
            )
            .where(Course.id == course_id)
        )
        return result.scalar_one_or_none()
