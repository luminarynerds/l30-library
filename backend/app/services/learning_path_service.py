# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.learning import Course, Enrollment
from ..models.learning_path import LearningPath, PathCourse, PathEnrollment
from ..models.user import User

logger = get_logger(__name__)


class LearningPathService:

    # ===== Learning Path CRUD =====

    @staticmethod
    async def create_path(
        db: AsyncSession, data: Dict[str, Any], created_by: User
    ) -> LearningPath:
        courses_data = data.pop("courses", [])

        path = LearningPath(**data, created_by_id=created_by.id)
        db.add(path)
        await db.flush()

        # Add courses
        for course_data in courses_data:
            path_course = PathCourse(learning_path_id=path.id, **course_data)
            db.add(path_course)

        await db.commit()
        await db.refresh(path)

        logger.info(f"Learning path created: {path.title} by user_id={created_by.id}")
        return path

    @staticmethod
    async def get_path(
        db: AsyncSession, path_id: int, load_courses: bool = False, load_course_details: bool = False
    ) -> Optional[LearningPath]:
        query = select(LearningPath).where(LearningPath.id == path_id)

        if load_courses:
            if load_course_details:
                query = query.options(
                    selectinload(LearningPath.path_courses).selectinload(PathCourse.course)
                )
            else:
                query = query.options(selectinload(LearningPath.path_courses))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_paths(
        db: AsyncSession,
        status: Optional[str] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LearningPath]:
        query = select(LearningPath).options(selectinload(LearningPath.path_courses))

        if status:
            query = query.where(LearningPath.status == status)
        if is_public is not None:
            query = query.where(LearningPath.is_public == is_public)

        query = query.order_by(LearningPath.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_path(
        db: AsyncSession, path_id: int, data: Dict[str, Any]
    ) -> Optional[LearningPath]:
        path = await LearningPathService.get_path(db, path_id)
        if not path:
            return None

        for key, value in data.items():
            if hasattr(path, key) and value is not None:
                setattr(path, key, value)

        path.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(path)

        return path

    @staticmethod
    async def delete_path(db: AsyncSession, path_id: int) -> bool:
        path = await LearningPathService.get_path(db, path_id)
        if not path:
            return False

        await db.delete(path)
        await db.commit()
        return True

    # ===== Path Course Management =====

    @staticmethod
    async def add_course_to_path(
        db: AsyncSession, path_id: int, course_data: Dict[str, Any]
    ) -> PathCourse:
        path_course = PathCourse(learning_path_id=path_id, **course_data)
        db.add(path_course)
        await db.commit()
        await db.refresh(path_course)

        return path_course

    @staticmethod
    async def remove_course_from_path(db: AsyncSession, path_course_id: int) -> bool:
        result = await db.execute(
            select(PathCourse).where(PathCourse.id == path_course_id)
        )
        path_course = result.scalar_one_or_none()

        if not path_course:
            return False

        await db.delete(path_course)
        await db.commit()
        return True

    @staticmethod
    async def update_path_course(
        db: AsyncSession, path_course_id: int, data: Dict[str, Any]
    ) -> Optional[PathCourse]:
        result = await db.execute(
            select(PathCourse).where(PathCourse.id == path_course_id)
        )
        path_course = result.scalar_one_or_none()

        if not path_course:
            return None

        for key, value in data.items():
            if hasattr(path_course, key) and value is not None:
                setattr(path_course, key, value)

        await db.commit()
        await db.refresh(path_course)
        return path_course

    @staticmethod
    async def get_path_course(
        db: AsyncSession, path_course_id: int
    ) -> Optional[PathCourse]:
        result = await db.execute(
            select(PathCourse).where(PathCourse.id == path_course_id)
        )
        return result.scalar_one_or_none()

    # ===== Enrollment Management =====

    @staticmethod
    async def enroll_user(
        db: AsyncSession, user_id: int, path_id: int
    ) -> PathEnrollment:
        # Check if already enrolled
        result = await db.execute(
            select(PathEnrollment).where(
                and_(
                    PathEnrollment.user_id == user_id,
                    PathEnrollment.learning_path_id == path_id,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        enrollment = PathEnrollment(user_id=user_id, learning_path_id=path_id)
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        logger.info(f"User {user_id} enrolled in path {path_id}")
        return enrollment

    @staticmethod
    async def get_enrollment(
        db: AsyncSession, user_id: int, path_id: int
    ) -> Optional[PathEnrollment]:
        result = await db.execute(
            select(PathEnrollment).where(
                and_(
                    PathEnrollment.user_id == user_id,
                    PathEnrollment.learning_path_id == path_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_enrollments(
        db: AsyncSession, user_id: int, status: Optional[str] = None
    ) -> List[PathEnrollment]:
        query = select(PathEnrollment).where(PathEnrollment.user_id == user_id)

        if status:
            query = query.where(PathEnrollment.status == status)

        query = query.order_by(PathEnrollment.enrolled_at.desc())

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_progress(
        db: AsyncSession,
        user_id: int,
        path_id: int,
        course_id: int,
        completed: bool = True,
    ) -> Optional[PathEnrollment]:
        enrollment = await LearningPathService.get_enrollment(db, user_id, path_id)
        if not enrollment:
            return None

        # Update completed courses
        completed_ids = enrollment.completed_course_ids or []

        if completed and course_id not in completed_ids:
            completed_ids.append(course_id)
        elif not completed and course_id in completed_ids:
            completed_ids.remove(course_id)

        enrollment.completed_course_ids = completed_ids
        enrollment.last_accessed_at = datetime.now(timezone.utc)

        # Update status
        if not enrollment.started_at:
            enrollment.started_at = datetime.now(timezone.utc)
            enrollment.status = "in_progress"

        # Calculate progress
        await LearningPathService._calculate_progress(db, enrollment)

        await db.commit()
        await db.refresh(enrollment)

        return enrollment

    @staticmethod
    async def _calculate_progress(db: AsyncSession, enrollment: PathEnrollment):
        # Get all courses in the path
        result = await db.execute(
            select(PathCourse).where(
                PathCourse.learning_path_id == enrollment.learning_path_id
            )
        )
        path_courses = result.scalars().all()

        if not path_courses:
            enrollment.progress_percentage = 0
            return

        # Count required courses completed
        required_courses = [pc for pc in path_courses if pc.is_required]
        completed_ids = enrollment.completed_course_ids or []

        if not required_courses:
            # No required courses, use all courses
            total = len(path_courses)
            completed = len(
                [pc for pc in path_courses if pc.course_id in completed_ids]
            )
        else:
            # Only count required courses
            total = len(required_courses)
            completed = len(
                [pc for pc in required_courses if pc.course_id in completed_ids]
            )

        enrollment.progress_percentage = (
            int((completed / total) * 100) if total > 0 else 0
        )

        # Update completion status
        if enrollment.progress_percentage >= 100:
            enrollment.status = "completed"
            if not enrollment.completed_at:
                enrollment.completed_at = datetime.now(timezone.utc)
        elif enrollment.progress_percentage > 0:
            enrollment.status = "in_progress"

    @staticmethod
    async def can_access_course(
        db: AsyncSession, user_id: int, path_id: int, course_id: int
    ) -> bool:
        # Get the path
        path = await LearningPathService.get_path(db, path_id, load_courses=True)
        if not path:
            return False

        # If prerequisites not enforced, allow access
        if not path.enforce_prerequisites:
            return True

        # Find the course in the path
        path_course = None
        for pc in path.path_courses:
            if pc.course_id == course_id:
                path_course = pc
                break

        if not path_course:
            return False

        # If no prerequisites, allow access
        if not path_course.prerequisite_course_ids:
            return True

        # Check if user completed prerequisites
        enrollment = await LearningPathService.get_enrollment(db, user_id, path_id)
        if not enrollment:
            return False

        completed_ids = enrollment.completed_course_ids or []

        for prereq_id in path_course.prerequisite_course_ids:
            if prereq_id not in completed_ids:
                return False

        return True

    @staticmethod
    async def get_next_course(
        db: AsyncSession, user_id: int, path_id: int
    ) -> Optional[int]:
        path = await LearningPathService.get_path(db, path_id, load_courses=True)
        if not path:
            return None

        enrollment = await LearningPathService.get_enrollment(db, user_id, path_id)
        completed_ids = enrollment.completed_course_ids if enrollment else []

        # Find first incomplete required course that user can access
        for path_course in sorted(path.path_courses, key=lambda x: x.sort_order):
            if path_course.is_required and path_course.course_id not in completed_ids:
                can_access = await LearningPathService.can_access_course(
                    db, user_id, path_id, path_course.course_id
                )
                if can_access:
                    return path_course.course_id

        # If all required done, find first incomplete optional
        for path_course in sorted(path.path_courses, key=lambda x: x.sort_order):
            if (
                not path_course.is_required
                and path_course.course_id not in completed_ids
            ):
                can_access = await LearningPathService.can_access_course(
                    db, user_id, path_id, path_course.course_id
                )
                if can_access:
                    return path_course.course_id

        return None
