# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API endpoints for learning paths."""

from app.core.logging import get_logger
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.learning import Course, Enrollment, Lesson, LessonProgress, Module
from ...models.learning_path import LearningPath, PathCourse, PathEnrollment
from ...models.user import User, UserRole
from ...schemas.learning_path import (BulkAddCoursesRequest,
                                      LearningPathCreate, LearningPathDetail,
                                      LearningPathResponse, LearningPathUpdate,
                                      PathCourseCreate, PathCourseResponse,
                                      PathCourseUpdate, PathCourseWithDetails,
                                      PathEnrollmentCreate,
                                      PathEnrollmentDetail,
                                      PathEnrollmentResponse,
                                      PathProgressUpdate)
from ...services.learning_path_service import LearningPathService
from .auth import get_current_user, get_current_user_optional

logger = get_logger(__name__)
router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])


def _ensure_admin(current_user: User) -> None:
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or staff access required",
        )


# ===== PUBLIC ENDPOINTS =====


@router.get("", response_model=List[LearningPathResponse])
async def list_learning_paths(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    List learning paths.

    - Public users see only published public paths
    - Authenticated users see published paths (public and private)
    - Admins see all paths
    """
    # Apply visibility filters
    allowed_public = {"published", "draft"}
    if not current_user:
        if status not in allowed_public:
            status = "published"
        is_public = True
    elif current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.STAFF]:
        if status not in allowed_public:
            status = "published"
        # Logged-in patrons see only public paths, same as anonymous visitors.
        # Non-public paths (e.g. staff-targeted tracks) stay visible to staff/admin only.
        is_public = True

    paths = await LearningPathService.list_paths(
        db=db, status=status, is_public=is_public, skip=skip, limit=limit
    )

    results = []
    for p in paths:
        r = LearningPathResponse.model_validate(p)
        r.total_courses = len(p.path_courses)
        results.append(r)
    return results


@router.get("/{path_id}", response_model=LearningPathDetail)
async def get_learning_path_detail(
    path_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get detailed learning path with courses and enrollment info.
    """
    # Use load_course_details=True to eagerly load Course for each PathCourse
    path = await LearningPathService.get_path(
        db, path_id, load_courses=True, load_course_details=True
    )

    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found"
        )

    # Check visibility (published + draft visible to all for Coming Soon; archived is staff-only)
    visible_statuses = {"published", "draft"}
    if not current_user and (path.status not in visible_statuses or not path.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found"
        )

    if current_user and current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.STAFF]:
        if path.status not in visible_statuses or not path.is_public:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found"
            )

    # Build detailed response
    response = LearningPathDetail.model_validate(path)

    # Get enrollment info if user is logged in
    enrollment = None
    if current_user:
        enrollment = await LearningPathService.get_enrollment(
            db, current_user.id, path_id
        )

    response.is_enrolled = enrollment is not None
    response.enrollment_progress = enrollment.progress_percentage if enrollment else 0

    # Pre-compute can_access for all courses (avoids N+1 on can_access_course calls)
    completed_course_ids = enrollment.completed_course_ids if enrollment else []
    prerequisite_map = {pc.course_id: pc.prerequisite_course_ids or [] for pc in path.path_courses}

    def can_access_course(course_id: int) -> bool:
        if not current_user:
            return True
        if not path.enforce_prerequisites:
            return True
        prereqs = prerequisite_map.get(course_id, [])
        if not prereqs:
            return True
        return all(prereq_id in completed_course_ids for prereq_id in prereqs)

    # Build course details using eagerly loaded course relationship
    courses_with_details = []
    for path_course in path.path_courses:
        course = path_course.course
        if not course:
            continue

        course_detail = PathCourseWithDetails(
            **PathCourseResponse.model_validate(path_course).dict(),
            course_title=course.title,
            course_thumbnail=course.thumbnail_url,
            course_estimated_minutes=course.estimated_minutes,
            course_difficulty=course.difficulty,
            is_completed=path_course.course_id in completed_course_ids,
            can_access=can_access_course(path_course.course_id)
        )
        courses_with_details.append(course_detail)

    response.courses = courses_with_details
    response.total_courses = len(path.path_courses)
    response.required_courses = len([pc for pc in path.path_courses if pc.is_required])
    response.optional_courses = len(
        [pc for pc in path.path_courses if not pc.is_required]
    )

    # Compute real duration from constituent published courses
    response.total_minutes = sum(
        c.course_estimated_minutes or 0 for c in courses_with_details
    )

    return response


# ===== USER ENROLLMENT ENDPOINTS =====


@router.post("/{path_id}/enroll", response_model=PathEnrollmentResponse)
async def enroll_in_path(
    path_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enroll in a learning path.

    Validates that the user can access the first course in the path
    when prerequisites enforcement is enabled.
    """
    path = await LearningPathService.get_path(db, path_id, load_courses=True)

    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found"
        )

    if path.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enroll in unpublished path",
        )

    # Validate prerequisites if enforcement is enabled
    if path.enforce_prerequisites and path.path_courses:
        sorted_courses = sorted(path.path_courses, key=lambda x: x.sort_order)
        first_course = sorted_courses[0] if sorted_courses else None

        if first_course and first_course.prerequisite_course_ids:
            # Check if the first course has external prerequisites
            # User must have completed these courses before enrolling
            for prereq_id in first_course.prerequisite_course_ids:
                # Check if prerequisite course exists and user has completed it
                prereq_result = await db.execute(
                    select(Course).where(Course.id == prereq_id)
                )
                prereq_course = prereq_result.scalar_one_or_none()

                if prereq_course:
                    # Check if user has completed this prerequisite course
                    # Get enrollment for prerequisite course
                    enrollment_result = await db.execute(
                        select(Enrollment).where(
                            Enrollment.user_id == current_user.id,
                            Enrollment.course_id == prereq_id
                        )
                    )
                    prereq_enrollment = enrollment_result.scalar_one_or_none()

                    if not prereq_enrollment:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"You must complete the prerequisite course '{prereq_course.title}' before enrolling in this learning path"
                        )

                    # Check if user has completed all lessons in the prerequisite course
                    total_lessons_result = await db.execute(
                        select(func.count(Lesson.id))
                        .join(Module, Lesson.module_id == Module.id)
                        .where(Module.course_id == prereq_id)
                    )
                    total_lessons = total_lessons_result.scalar() or 0

                    completed_lessons_result = await db.execute(
                        select(func.count(LessonProgress.id))
                        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
                        .join(Module, Lesson.module_id == Module.id)
                        .where(
                            Module.course_id == prereq_id,
                            LessonProgress.user_id == current_user.id,
                            LessonProgress.status == "completed"
                        )
                    )
                    completed_lessons = completed_lessons_result.scalar() or 0

                    if total_lessons > 0 and completed_lessons < total_lessons:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"You must complete all lessons in '{prereq_course.title}' before enrolling in this learning path"
                        )

    enrollment = await LearningPathService.enroll_user(db, current_user.id, path_id)
    return PathEnrollmentResponse.model_validate(enrollment)


@router.get("/enrollments/my", response_model=List[PathEnrollmentDetail])
async def get_my_enrollments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None),
):
    """Get current user enrollments."""
    # Get enrollments with learning_path eagerly loaded
    query = (
        select(PathEnrollment)
        .options(
            selectinload(PathEnrollment.learning_path)
            .selectinload(LearningPath.path_courses)
        )
        .where(PathEnrollment.user_id == current_user.id)
    )
    if status:
        query = query.where(PathEnrollment.status == status)
    query = query.order_by(PathEnrollment.enrolled_at.desc())

    result = await db.execute(query)
    enrollments = result.scalars().all()

    if not enrollments:
        return []

    # Build detailed responses using pre-loaded data
    detailed_enrollments = []
    for enrollment in enrollments:
        path = enrollment.learning_path
        if not path:
            continue

        # Calculate next course inline to avoid N+1 service calls
        completed_ids = enrollment.completed_course_ids or []
        next_course_id = None

        if path.path_courses:
            sorted_courses = sorted(path.path_courses, key=lambda x: x.sort_order)

            # Build prerequisite map for can_access check
            prerequisite_map = {pc.course_id: pc.prerequisite_course_ids or [] for pc in sorted_courses}

            def can_access(course_id: int) -> bool:
                if not path.enforce_prerequisites:
                    return True
                prereqs = prerequisite_map.get(course_id, [])
                return not prereqs or all(p in completed_ids for p in prereqs)

            # Find first incomplete required course user can access
            for pc in sorted_courses:
                if pc.is_required and pc.course_id not in completed_ids and can_access(pc.course_id):
                    next_course_id = pc.course_id
                    break

            # If all required done, find first incomplete optional
            if next_course_id is None:
                for pc in sorted_courses:
                    if not pc.is_required and pc.course_id not in completed_ids and can_access(pc.course_id):
                        next_course_id = pc.course_id
                        break

        detail = PathEnrollmentDetail(
            **PathEnrollmentResponse.model_validate(enrollment).dict(),
            path_title=path.title,
            path_thumbnail=path.thumbnail_url,
            path_description=path.description,
            total_courses=len(path.path_courses),
            completed_courses=len(completed_ids),
            next_course_id=next_course_id
        )
        detailed_enrollments.append(detail)

    return detailed_enrollments


@router.post("/{path_id}/progress", response_model=PathEnrollmentResponse)
async def update_course_progress(
    path_id: int,
    progress: PathProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update progress for a course in the path."""
    enrollment = await LearningPathService.update_progress(
        db=db,
        user_id=current_user.id,
        path_id=path_id,
        course_id=progress.course_id,
        completed=progress.completed,
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found. Please enroll first.",
        )

    return PathEnrollmentResponse.model_validate(enrollment)


# ===== ADMIN ENDPOINTS =====


@router.post(
    "", response_model=LearningPathResponse, status_code=status.HTTP_201_CREATED
)
async def create_learning_path(
    payload: LearningPathCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new learning path (admin only)."""
    _ensure_admin(current_user)

    path = await LearningPathService.create_path(
        db=db, data=payload.dict(), created_by=current_user
    )

    return LearningPathResponse.model_validate(path)


@router.put("/{path_id}", response_model=LearningPathResponse)
async def update_learning_path(
    path_id: int,
    payload: LearningPathUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a learning path (admin only)."""
    _ensure_admin(current_user)

    path = await LearningPathService.update_path(
        db=db, path_id=path_id, data=payload.dict(exclude_unset=True)
    )

    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found"
        )

    return LearningPathResponse.model_validate(path)


@router.delete("/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learning_path(
    path_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a learning path (admin only)."""
    _ensure_admin(current_user)

    success = await LearningPathService.delete_path(db, path_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found"
        )


@router.post(
    "/{path_id}/courses",
    response_model=PathCourseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_course_to_path(
    path_id: int,
    payload: PathCourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a course to a learning path (admin only)."""
    _ensure_admin(current_user)

    path_course = await LearningPathService.add_course_to_path(
        db=db, path_id=path_id, course_data=payload.dict()
    )

    return PathCourseResponse.model_validate(path_course)


@router.put("/courses/{path_course_id}", response_model=PathCourseResponse)
async def update_path_course(
    path_course_id: int,
    payload: PathCourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a course in a path (admin only)."""
    _ensure_admin(current_user)

    path_course = await LearningPathService.update_path_course(
        db=db, path_course_id=path_course_id, data=payload.dict(exclude_unset=True)
    )

    if not path_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Path course not found"
        )

    return PathCourseResponse.model_validate(path_course)


@router.delete("/courses/{path_course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_course_from_path(
    path_course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a course from a path (admin only)."""
    _ensure_admin(current_user)

    success = await LearningPathService.remove_course_from_path(db, path_course_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Path course not found"
        )


@router.get("/courses/{path_course_id}", response_model=PathCourseResponse)
async def get_courses__path_course_id_(
    path_course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get PathCourse information."""
    path_course = await LearningPathService.get_path_course(db, path_course_id)

    if not path_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Path course not found"
        )

    return PathCourseResponse.model_validate(path_course)



# --- Waitlist (Coming Soon) ---

from ...models.learning_path_waitlist import LearningPathWaitlist
from pydantic import BaseModel


class WaitlistResponse(BaseModel):
    joined: bool
    waitlist_count: int

    class Config:
        from_attributes = True


@router.post("/{path_id}/waitlist", response_model=WaitlistResponse)
async def join_waitlist(
    path_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join waitlist for a draft/upcoming learning path."""
    path = await LearningPathService.get_path(db, path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    if path.status == "published":
        raise HTTPException(status_code=400, detail="Path is already published -- enroll instead")

    existing = await db.execute(
        select(LearningPathWaitlist).where(
            LearningPathWaitlist.user_id == current_user.id,
            LearningPathWaitlist.learning_path_id == path_id,
        )
    )
    if existing.scalar_one_or_none():
        count_result = await db.execute(
            select(func.count(LearningPathWaitlist.id)).where(
                LearningPathWaitlist.learning_path_id == path_id
            )
        )
        return WaitlistResponse(joined=True, waitlist_count=count_result.scalar() or 0)

    entry = LearningPathWaitlist(user_id=current_user.id, learning_path_id=path_id)
    db.add(entry)
    await db.commit()

    count_result = await db.execute(
        select(func.count(LearningPathWaitlist.id)).where(
            LearningPathWaitlist.learning_path_id == path_id
        )
    )
    return WaitlistResponse(joined=True, waitlist_count=count_result.scalar() or 0)


@router.get("/{path_id}/waitlist", response_model=WaitlistResponse)
async def get_waitlist_status(
    path_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Check waitlist status for a learning path."""
    if current_user:
        existing = await db.execute(
            select(LearningPathWaitlist).where(
                LearningPathWaitlist.user_id == current_user.id,
                LearningPathWaitlist.learning_path_id == path_id,
            )
        )
        joined = existing.scalar_one_or_none() is not None
    else:
        joined = False

    count_result = await db.execute(
        select(func.count(LearningPathWaitlist.id)).where(
            LearningPathWaitlist.learning_path_id == path_id
        )
    )
    return WaitlistResponse(joined=joined, waitlist_count=count_result.scalar() or 0)
