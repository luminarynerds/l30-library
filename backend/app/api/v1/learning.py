# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Learning - Course & Enrollment API Endpoints

Provides endpoints for:
- Course listing and details
- Course CRUD (staff/admin)
- User enrollment
"""

from app.core.logging import get_logger
from io import BytesIO
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.file_validation import validate_file_size, validate_file_type
from ...core.shortcuts import get_or_404
from ...services.storage_service import get_storage
from ...models.learning import (
    Course,
    CourseLifecycleStage,
    CourseSkill,
    CourseStageTransition,
    Enrollment,
    Lesson,
    LessonProgress,
    LessonType,
    Module,
    QuizQuestion,
    Skill,
    UserPreferences,
)
from ...models.gamification import UserStats
from ...models.user import User, UserRole
from ...schemas.learning import (
    CourseBrief,
    CourseCloneRequest,
    CourseCreate,
    CourseImportPayload,
    CourseImportResponse,
    CourseListItem,
    CourseListItemAdmin,
    CoursePublishToggleRequest,
    CourseResponse,
    CourseStageTransitionHistoryItem,
    CourseStageTransitionRequest,
    CourseUpdate,
    LastReviewedBy,
    ReviewQueueResponse,
    CourseWithModules,
    EnrolledCourse,
    EnrollmentResponse,
    ModuleCreate,
    ModuleUpdate,
    ModuleResponse,
    LessonCreate,
    LessonUpdate,
    LessonResponse,
    LessonMediaUploadResponse,
    CourseMediaUploadResponse,
    CoursePrerequisitesStatus,
    PrerequisiteCourseInfo,
    SkillBrief,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    CourseProgressResponse,
)
from .auth import get_current_user, get_current_user_optional
from .dependencies import (
    can_access_course,
    is_admin,
    is_staff_or_admin,
    require_admin,
    require_staff,
)
from .learning_team import (
    assign_course_to_report as assign_course_to_report,
    get_team_progress_endpoint as get_team_progress_endpoint,
    router as learning_team_router,
)
from ...services.course_lifecycle_service import (
    ALLOWED_TRANSITIONS,
    EmptyCourseError,
    is_transition_allowed,
    transition_course_stage,
)
from datetime import datetime, timedelta, timezone

logger = get_logger(__name__)

router = APIRouter(prefix="/learning", tags=["learning"])


MAX_PREREQUISITE_DEPTH = 10


async def check_circular_prerequisites(
    db: AsyncSession,
    course_id: int,
    new_prerequisite_ids: List[int],
    visited: Optional[set] = None,
    depth: int = 0,
) -> bool:
    if depth >= MAX_PREREQUISITE_DEPTH:
        return True  # Treat excessively deep chains as circular

    if visited is None:
        visited = set()

    # Direct self-reference check
    if course_id in new_prerequisite_ids:
        return True

    # Check each prerequisite recursively
    for prereq_id in new_prerequisite_ids:
        if prereq_id in visited:
            continue

        visited.add(prereq_id)

        # Get the prerequisite course and its prerequisites
        result = await db.execute(select(Course).where(Course.id == prereq_id))
        prereq_course = result.scalar_one_or_none()

        if prereq_course:
            prereq_prereqs = prereq_course.prerequisite_course_ids or []

            # If course_id is a prerequisite of any of our prerequisites, we have a cycle
            if course_id in prereq_prereqs:
                return True

            # Recursively check deeper levels
            if prereq_prereqs:
                if await check_circular_prerequisites(
                    db, course_id, prereq_prereqs, visited, depth + 1
                ):
                    return True

    return False


async def get_user_completed_course_ids(
    db: AsyncSession, user_id: int, course_ids: List[int]
) -> set:
    if not course_ids:
        return set()

    result = await db.execute(
        select(Enrollment.course_id).where(
            Enrollment.user_id == user_id,
            Enrollment.course_id.in_(course_ids),
            Enrollment.completed_at.isnot(None),
        )
    )
    return {row[0] for row in result.all()}


def _skills_for_course(course: Course) -> List[SkillBrief]:
    out: List[SkillBrief] = []
    for cs in getattr(course, "course_skills", []) or []:
        skill = getattr(cs, "skill", None)
        if skill is None:
            continue
        out.append(
            SkillBrief(
                id=skill.id,
                name=skill.name,
                level_taught=cs.level_taught,
            )
        )
    return out


async def get_prerequisite_courses_with_status(
    db: AsyncSession, prerequisite_ids: List[int], user_id: Optional[int] = None
) -> List[PrerequisiteCourseInfo]:
    if not prerequisite_ids:
        return []

    # Batch fetch all prerequisite courses
    result = await db.execute(select(Course).where(Course.id.in_(prerequisite_ids)))
    prereq_courses = {course.id: course for course in result.scalars().all()}

    # Get completion status if user is provided
    completed_ids = set()
    if user_id:
        completed_ids = await get_user_completed_course_ids(db, user_id, prerequisite_ids)

    # Build response in the order of prerequisite_ids
    prerequisites = []
    for prereq_id in prerequisite_ids:
        course = prereq_courses.get(prereq_id)
        if course:
            prerequisites.append(
                PrerequisiteCourseInfo(
                    id=course.id, title=course.title, completed=prereq_id in completed_ids
                )
            )

    return prerequisites


# ============ COURSES ============


@router.get("/courses", response_model=List[CourseListItem])
async def list_courses(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    difficulty: Optional[str] = Query(
        None,
        pattern=r"^(beginner|intermediate|advanced)$",
        description="Filter by course difficulty",
    ),
    duration_min: Optional[int] = Query(
        None, ge=0, description="Minimum estimated_minutes (inclusive)"
    ),
    duration_max: Optional[int] = Query(
        None, ge=0, description="Maximum estimated_minutes (inclusive)"
    ),
    content_type: Optional[str] = Query(
        None,
        pattern=r"^(article|video|quiz|mixed)$",
        description="Filter by lesson content type. article/video/quiz match courses with at least one lesson of that type; mixed matches courses with 2+ distinct lesson_type values.",
    ),
    search: Optional[str] = Query(
        None, max_length=100, description="Case-insensitive substring match on title or description"
    ),
    limit: int = Query(50, ge=1, le=200, description="Max rows to return (default 50, max 200)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """List published courses. Public endpoint - anonymous users see patron-level courses.

    Filters (all optional, composed with AND):
      - difficulty: beginner | intermediate | advanced
      - duration_min / duration_max: clamp on courses.estimated_minutes (NULL excluded when either bound is set)
      - content_type: article|video|quiz (course has >=1 lesson of that type) or mixed (>=2 distinct lesson_types)
      - search: ILIKE substring match on title OR description
      - limit (default 50, max 200) + offset

    Response body shape is unchanged (List[CourseListItem]). The unfiltered-by-limit
    total row count is returned in the X-Total-Count header.
    """
    # Subquery for module counts per course
    module_counts = (
        select(Module.course_id, func.count(Module.id).label("module_count"))
        .group_by(Module.course_id)
        .subquery()
    )

    # Subquery for lesson counts per course
    lesson_counts = (
        select(Module.course_id, func.count(Lesson.id).label("lesson_count"))
        .join(Lesson, Lesson.module_id == Module.id)
        .group_by(Module.course_id)
        .subquery()
    )

    # Base predicate list — shared by the row query and the total-count query so
    # X-Total-Count stays consistent with the filtered (but un-paginated) result set.
    base_where = [
        Course.lifecycle_stage == CourseLifecycleStage.PUBLISHED,
        Course.deleted_at.is_(None),
    ]

    # Access level filter (same role gating as before):
    # - Anonymous / Patron: patron-level only
    # - Staff: patron + staff
    # - Admin / Director / Super Admin: all access levels (no filter)
    if current_user is None or current_user.role == UserRole.PATRON:
        base_where.append(Course.access_level == "patron")
    elif current_user.role == UserRole.STAFF:
        base_where.append(Course.access_level.in_(["patron", "staff"]))
    elif not is_admin(current_user):
        # Safety net: unknown or future roles default to patron-level access
        base_where.append(Course.access_level == "patron")

    if difficulty is not None:
        base_where.append(Course.difficulty == difficulty)

    if duration_min is not None:
        base_where.append(Course.estimated_minutes >= duration_min)
    if duration_max is not None:
        base_where.append(Course.estimated_minutes <= duration_max)

    if search:
        like = f"%{search}%"
        base_where.append((Course.title.ilike(like)) | (Course.description.ilike(like)))

    if content_type is not None:
        # Course has no content_type column — derive from the lesson_type values
        # of lessons belonging to this course's modules. "article"/"video"/"quiz"
        # = any lesson with that lesson_type. "mixed" = at least 2 distinct
        # lesson_type values across the course's lessons.
        if content_type == "mixed":
            mixed_subq = (
                select(Module.course_id)
                .join(Lesson, Lesson.module_id == Module.id)
                .group_by(Module.course_id)
                .having(func.count(func.distinct(Lesson.lesson_type)) >= 2)
                .subquery()
            )
            base_where.append(Course.id.in_(select(mixed_subq.c.course_id)))
        else:
            ct_subq = (
                select(Module.course_id)
                .join(Lesson, Lesson.module_id == Module.id)
                .where(Lesson.lesson_type == content_type)
                .subquery()
            )
            base_where.append(Course.id.in_(select(ct_subq.c.course_id)))

    # Wave 5: eager-load course_skills + their Skill so the SkillBrief
    # mapping is a single round-trip instead of N+1 per row.
    query = (
        select(
            Course,
            func.coalesce(module_counts.c.module_count, 0).label("module_count"),
            func.coalesce(lesson_counts.c.lesson_count, 0).label("lesson_count"),
        )
        .options(selectinload(Course.course_skills).joinedload(CourseSkill.skill))
        .outerjoin(module_counts, Course.id == module_counts.c.course_id)
        .outerjoin(lesson_counts, Course.id == lesson_counts.c.course_id)
    )
    for predicate in base_where:
        query = query.where(predicate)

    # Total-count query: same filters, no limit/offset, no joins/eager loads.
    count_query = select(func.count()).select_from(Course)
    for predicate in base_where:
        count_query = count_query.where(predicate)
    total = (await db.execute(count_query)).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    result = await db.execute(query.order_by(Course.created_at.desc()).limit(limit).offset(offset))
    rows = result.all()

    course_list = []
    for row in rows:
        course = row[0]
        module_count = row[1]
        lesson_count = row[2]

        course_data = CourseListItem(
            **{c.name: getattr(course, c.name) for c in course.__table__.columns},
            module_count=module_count,
            lesson_count=lesson_count,
            skills=_skills_for_course(course),
        )
        course_list.append(course_data)

    return course_list


@router.get("/courses/{course_id}", response_model=CourseWithModules)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get course details with modules and lessons."""
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons).selectinload(Lesson.variants),
            # Wave 5: eager-load skills for the chip strip on detail page too.
            selectinload(Course.course_skills).joinedload(CourseSkill.skill),
        )
        .where(Course.id == course_id)
        .where(Course.deleted_at.is_(None))
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Non-published courses are only visible to staff/admin
    if course.lifecycle_stage != CourseLifecycleStage.PUBLISHED and not (
        current_user and is_staff_or_admin(current_user)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Check access level: anonymous users can only see patron courses,
    # authenticated users are checked via can_access_course
    if not current_user:
        if course.access_level != "patron":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this course"
            )
    elif not can_access_course(current_user, course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this course"
        )

    return course


@router.get("/courses/{course_id}/prerequisites", response_model=CoursePrerequisitesStatus)
async def get_course_prerequisites(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get the prerequisite courses for a course and their completion status.

    Returns a list of prerequisites with:
    - id: Course ID
    - title: Course title
    - completed: Whether the current user has completed the course (false if not logged in)

    Also returns:
    - all_met: True if all prerequisites are completed
    - missing_count: Number of incomplete prerequisites
    """
    course = await get_or_404(db, Course, course_id, "Course not found")

    # Check if course is published or user is staff/admin
    if course.lifecycle_stage != CourseLifecycleStage.PUBLISHED and not (
        current_user and is_staff_or_admin(current_user)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Check access permissions
    if current_user and not can_access_course(current_user, course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this course"
        )
    if not current_user and course.access_level != "patron":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this course"
        )

    prerequisite_ids = course.prerequisite_course_ids or []

    if not prerequisite_ids:
        return CoursePrerequisitesStatus(prerequisites=[], all_met=True, missing_count=0)

    # Get prerequisites with completion status
    user_id = current_user.id if current_user else None
    prerequisites = await get_prerequisite_courses_with_status(db, prerequisite_ids, user_id)

    incomplete_count = sum(1 for p in prerequisites if not p.completed)

    return CoursePrerequisitesStatus(
        prerequisites=prerequisites, all_met=incomplete_count == 0, missing_count=incomplete_count
    )


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_in: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new course (staff/admin only)."""
    # Validate prerequisite course IDs exist if provided
    prereq_ids = course_in.prerequisite_course_ids or []
    if prereq_ids:
        prereq_result = await db.execute(select(Course.id).where(Course.id.in_(prereq_ids)))
        existing_prereq_ids = {row[0] for row in prereq_result.all()}
        missing_ids = set(prereq_ids) - existing_prereq_ids

        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The following prerequisite course IDs do not exist: {sorted(missing_ids)}",
            )

    # Wave 1 (course-authoring friction strip): stamp the creator so sweep
    # emails (W1-B) know whom to notify and the import endpoint (W1-D) can
    # carry creator attribution forward. Historical rows pre-dating this
    # column stay NULL — no backfill is possible.
    course = Course(
        **course_in.model_dump(),
        created_by_id=current_user.id,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.put("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_update: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a course (staff/admin only)."""
    course = await get_or_404(db, Course, course_id, "Course not found")

    update_data = course_update.model_dump(exclude_unset=True)

    # Validate prerequisite_course_ids if provided
    if "prerequisite_course_ids" in update_data:
        new_prereqs = update_data["prerequisite_course_ids"] or []

        if new_prereqs:
            # Check that all prerequisite courses exist
            prereq_result = await db.execute(select(Course.id).where(Course.id.in_(new_prereqs)))
            existing_prereq_ids = {row[0] for row in prereq_result.all()}
            missing_ids = set(new_prereqs) - existing_prereq_ids

            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The following prerequisite course IDs do not exist: {sorted(missing_ids)}",
                )

            # Check for circular dependencies
            if await check_circular_prerequisites(db, course_id, new_prereqs):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot set these prerequisites: this would create a circular dependency. "
                    "A course cannot require itself or require a course that eventually requires it.",
                )

    for field, value in update_data.items():
        setattr(course, field, value)

    await db.commit()
    await db.refresh(course)
    return course


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete a course (staff/admin only).

    Implemented as a cascade-archive through the existing 3-state lifecycle
    (draft/published/archived) rather than a destructive delete: nothing is
    dropped from the database, and the course is recoverable via the same
    archived -> draft "Restore" transition the Course Admin UI already
    exposes (POST /admin/courses/{id}/transition).

    Modules and lessons have no lifecycle/visibility state of their own —
    every endpoint that serves them (the nested CourseWithModules payload,
    GET .../modules, enrollment) already gates purely on the parent
    course's ``lifecycle_stage``. Archiving the course therefore cascades
    their invisibility to patrons for free, with no schema change and no
    risk of orphaning them: they stay attached to the (now archived)
    course and come back automatically if the course is restored.

    404 if the course doesn't exist, is legacy soft-deleted
    (``deleted_at`` set), or is already archived (idempotent — matches the
    old soft-delete contract where deleting twice 404s the second time).
    """
    course = await get_or_404(db, Course, course_id, "Course not found")

    if course.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    _coerce_lifecycle_stage(course)

    if course.lifecycle_stage == CourseLifecycleStage.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    try:
        await transition_course_stage(
            db,
            course,
            CourseLifecycleStage.ARCHIVED,
            actor=current_user,
            note="Archived via course deletion",
        )
    except ValueError as exc:
        # Defensive: the ARCHIVED check above should already have caught
        # this (every stage but ARCHIVED itself allows -> ARCHIVED).
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await db.commit()
    return {"message": "Course archived"}


@router.post("/courses/{course_id}/restore", response_model=dict)
async def restore_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Restore a soft-deleted course (staff/admin only)."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course or course.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No deleted course found with that ID"
        )

    course.deleted_at = None
    course.deleted_by_id = None
    await db.commit()
    return {"id": course.id, "title": course.title, "message": "Course restored"}


def _coerce_lifecycle_stage(course: Course) -> None:
    stage = course.lifecycle_stage
    if isinstance(stage, str):
        course.lifecycle_stage = CourseLifecycleStage(stage)


def _admin_courses_query():
    # Subquery for module counts per course
    module_counts = (
        select(Module.course_id, func.count(Module.id).label("module_count"))
        .group_by(Module.course_id)
        .subquery()
    )

    # Subquery for lesson counts per course
    lesson_counts = (
        select(Module.course_id, func.count(Lesson.id).label("lesson_count"))
        .join(Lesson, Lesson.module_id == Module.id)
        .group_by(Module.course_id)
        .subquery()
    )

    # Enrollment aggregate: total + completed counts in one pass.
    # completion_count uses Enrollment.completed_at IS NOT NULL — same
    # signal `get_user_completed_courses` (learning_paths.py:135) uses.
    enrollment_counts = (
        select(
            Enrollment.course_id.label("course_id"),
            func.count(Enrollment.id).label("enrollment_count"),
            func.count(Enrollment.completed_at).label("completion_count"),
        )
        .group_by(Enrollment.course_id)
        .subquery()
    )

    # Per-course lesson_progress aggregate: which (enrollee, course) pairs
    # have ANY progress row, and what's the latest activity timestamp.
    progress_per_course = (
        select(
            Module.course_id.label("course_id"),
            LessonProgress.user_id.label("user_id"),
            func.max(func.coalesce(LessonProgress.completed_at, LessonProgress.started_at)).label(
                "last_activity_at"
            ),
        )
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .group_by(Module.course_id, LessonProgress.user_id)
        .subquery()
    )

    # in_progress_count = enrolled AND not completed AND has at least one
    # lesson_progress row for some lesson in the course.
    in_progress_counts = (
        select(
            Enrollment.course_id.label("course_id"),
            func.count(func.distinct(Enrollment.user_id)).label("in_progress_count"),
        )
        .join(
            progress_per_course,
            (progress_per_course.c.course_id == Enrollment.course_id)
            & (progress_per_course.c.user_id == Enrollment.user_id),
        )
        .where(Enrollment.completed_at.is_(None))
        .group_by(Enrollment.course_id)
        .subquery()
    )

    # last_activity_at for the course is the MAX across ALL progress rows.
    activity_counts = (
        select(
            progress_per_course.c.course_id.label("course_id"),
            func.max(progress_per_course.c.last_activity_at).label("last_activity_at"),
        )
        .group_by(progress_per_course.c.course_id)
        .subquery()
    )

    return (
        select(
            Course,
            func.coalesce(module_counts.c.module_count, 0).label("module_count"),
            func.coalesce(lesson_counts.c.lesson_count, 0).label("lesson_count"),
            func.coalesce(enrollment_counts.c.enrollment_count, 0).label("enrollment_count"),
            func.coalesce(enrollment_counts.c.completion_count, 0).label("completion_count"),
            func.coalesce(in_progress_counts.c.in_progress_count, 0).label("in_progress_count"),
            activity_counts.c.last_activity_at.label("last_activity_at"),
        )
        .options(selectinload(Course.last_reviewed_by))
        .outerjoin(module_counts, Course.id == module_counts.c.course_id)
        .outerjoin(lesson_counts, Course.id == lesson_counts.c.course_id)
        .outerjoin(enrollment_counts, Course.id == enrollment_counts.c.course_id)
        .outerjoin(in_progress_counts, Course.id == in_progress_counts.c.course_id)
        .outerjoin(activity_counts, Course.id == activity_counts.c.course_id)
        .where(Course.deleted_at.is_(None))
    )


def _row_to_admin_item(row, *, now: datetime) -> CourseListItemAdmin:
    course = row[0]
    _coerce_lifecycle_stage(course)
    reviewer = None
    # last_reviewed_by was selectinload'd on the query — accessing it is
    # safe inside the async session (no MissingGreenlet).
    if course.last_reviewed_by is not None:
        reviewer = LastReviewedBy(
            id=course.last_reviewed_by.id,
            display_name=course.last_reviewed_by.full_name,
        )

    # SQLite returns naive datetimes from DateTime(timezone=True) columns;
    # normalise to UTC before comparing against the tz-aware ``now`` to
    # avoid a TypeError on the test DB. PostgreSQL returns tz-aware so
    # this is a no-op on prod.
    review_due_at = course.review_due_at
    if review_due_at is not None and review_due_at.tzinfo is None:
        review_due_at = review_due_at.replace(tzinfo=timezone.utc)
    is_due = (
        course.lifecycle_stage == CourseLifecycleStage.PUBLISHED
        and review_due_at is not None
        and review_due_at < now
    )

    return CourseListItemAdmin(
        **{c.name: getattr(course, c.name) for c in course.__table__.columns},
        module_count=row[1],
        lesson_count=row[2],
        enrollment_count=row[3],
        completion_count=row[4],
        in_progress_count=row[5],
        last_activity_at=row[6],
        last_reviewed_by=reviewer,
        is_review_due=is_due,
    )


@router.get("/admin/courses", response_model=List[CourseListItemAdmin])
async def list_all_courses_admin(
    stage: Optional[str] = Query(
        None,
        description=(
            "Comma-separated lifecycle stages to include (e.g. "
            "'draft,published'). Empty or missing returns all stages."
        ),
    ),
    review_due: bool = Query(
        False,
        description=(
            "If true, returns only published courses whose review_due_at "
            "is in the past — same set as /admin/courses/review-queue.courses."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all courses including unpublished (staff/admin only).

    Joins per-course aggregates (module + lesson counts, enrollment count,
    completion count, in-progress count, last-activity timestamp,
    last_reviewed_by) in a single SQL round-trip.

    Aggregates are intentionally admin-only — patron-facing /courses
    returns plain CourseListItem so enrollment counts don't leak.

    Query params (added in PR-C2 of admin-courses lifecycle-stages):
      ``stage``       Comma-separated allow-list of lifecycle stages.
                      Unknown values are silently dropped so the FE can
                      ship new stage strings ahead of the BE.
      ``review_due``  Convenience flag equivalent to
                      ``stage=published`` + ``review_due_at < now()``.
                      When both are set, ``stage`` is intersected with
                      "published" so you can't ask for due-draft courses.
    """
    now = datetime.now(timezone.utc)
    query = _admin_courses_query()

    if stage:
        valid = []
        for raw in stage.split(","):
            v = raw.strip()
            if not v:
                continue
            try:
                valid.append(CourseLifecycleStage(v))
            except ValueError:
                # Drop unknown stage tokens. Fail-open keeps the admin
                # list usable when the FE adds a stage before the BE
                # picks it up (extremely unlikely with our enum but the
                # filter shouldn't crash on garbage either).
                continue
        if valid:
            query = query.where(Course.lifecycle_stage.in_(valid))

    if review_due:
        query = query.where(
            Course.lifecycle_stage == CourseLifecycleStage.PUBLISHED,
            Course.review_due_at.is_not(None),
            Course.review_due_at < now,
        )

    result = await db.execute(query.order_by(Course.created_at.desc()))
    rows = result.all()

    return [_row_to_admin_item(row, now=now) for row in rows]


@router.get(
    "/admin/courses/review-queue",
    response_model=ReviewQueueResponse,
)
async def admin_courses_review_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Published courses whose annual review is overdue.

    Same filter as ``GET /admin/courses?review_due=true`` plus two header
    aggregates the FE wants without re-aggregating client-side:
      * ``due_count``       - len(courses)
      * ``soonest_due_at``  - MIN(review_due_at) across the set

    Ordered by review_due_at ASC so the most-stale course is first.
    """
    now = datetime.now(timezone.utc)
    query = (
        _admin_courses_query()
        .where(
            Course.lifecycle_stage == CourseLifecycleStage.PUBLISHED,
            Course.review_due_at.is_not(None),
            Course.review_due_at < now,
        )
        .order_by(Course.review_due_at.asc())
    )

    result = await db.execute(query)
    rows = result.all()

    courses = [_row_to_admin_item(row, now=now) for row in rows]
    soonest = min((c.review_due_at for c in courses if c.review_due_at), default=None)
    return ReviewQueueResponse(
        due_count=len(courses),
        soonest_due_at=soonest,
        courses=courses,
    )


@router.post(
    "/admin/courses/{course_id}/transition",
    response_model=CourseListItemAdmin,
)
async def transition_course_lifecycle_stage(
    course_id: int,
    body: CourseStageTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Transition a course to a new lifecycle stage.

    Admin-only. Writes a CourseStageTransition audit row via
    ``course_lifecycle_service.transition_course_stage`` and returns the
    full ``CourseListItemAdmin`` row so the FE can patch its grid in place.

    Errors:
      * 404 if course missing or soft-deleted.
      * 400 if the requested transition is not in ALLOWED_TRANSITIONS for
        the course's current stage; ``allowed_targets`` is included in
        the error detail so the FE can render "You may move to: X, Y".
      * 400 if transitioning TO ``published`` and the course has no
        lessons (EmptyCourseError from the service).
      * 400 if transitioning TO ``archived`` with enrolled learners
        and ``confirm`` is false; ``enrollment_count`` is included so
        the FE can show "42 learners are enrolled — confirm archive?".
      * 403 non-admin.

    ``lifecycle_stage`` is the single source of truth (PR-C4 dropped
    the legacy ``is_published`` column and its compat shim).
    """
    course = await get_or_404(db, Course, course_id, "Course not found")
    if course.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    _coerce_lifecycle_stage(course)

    target = body.to_stage

    # Explicit transition-allowed check up here so the response can
    # include ``allowed_targets``. The service's ValueError doesn't
    # carry that list, and the FE needs it to render the dropdown.
    if not is_transition_allowed(course.lifecycle_stage, target):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    f"Cannot transition course from "
                    f"{course.lifecycle_stage.value} to {target.value}."
                ),
                "allowed_targets": sorted(
                    s.value for s in ALLOWED_TRANSITIONS.get(course.lifecycle_stage, set())
                ),
                "current_stage": course.lifecycle_stage.value,
            },
        )

    # Archive-with-enrollments confirm gate. Counts active + completed
    # enrollment rows (any history with the course); admins should
    # explicitly acknowledge they're archiving a course people touched.
    if target == CourseLifecycleStage.ARCHIVED and not body.confirm:
        enroll_row = await db.execute(
            select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
        )
        enrollment_count = enroll_row.scalar_one() or 0
        if enrollment_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": (
                        f"Archiving this course will hide it from "
                        f"{enrollment_count} enrolled learner(s). "
                        f"Re-submit with confirm=true to proceed."
                    ),
                    "enrollment_count": enrollment_count,
                    "requires_confirm": True,
                },
            )

    try:
        await transition_course_stage(db, course, target, actor=current_user, note=body.note)
    except EmptyCourseError as exc:
        # Service rolls nothing back (no commit yet); abort cleanly.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        # Defensive: pre-check above should have caught this, but keep
        # the safety net so a future ALLOWED_TRANSITIONS drift can't
        # 500 the endpoint.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Single commit covers both the audit row and the course mutation.
    await db.commit()

    # Re-fetch through the shared aggregate helper so the response is
    # exactly the same shape the list endpoint returns. Cheaper than
    # 5 ad-hoc count queries and stays in lockstep with the list logic.
    #
    # ``populate_existing=True`` forces SQLAlchemy to overwrite the
    # in-identity-map Course attributes (notably the ``last_reviewed_by``
    # selectinload). Without it, the just-committed row reuses the old
    # in-session instance whose relationship was never eager-loaded.
    now = datetime.now(timezone.utc)
    result = await db.execute(
        _admin_courses_query()
        .where(Course.id == course_id)
        .execution_options(populate_existing=True)
    )
    row = result.first()
    if row is None:
        # Shouldn't happen — course existed two awaits ago. Belt-and-
        # suspenders: surface a clean 404 instead of an attribute error.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return _row_to_admin_item(row, now=now)


@router.get(
    "/admin/courses/{course_id}/transitions",
    response_model=List[CourseStageTransitionHistoryItem],
)
async def list_course_stage_transitions(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Stage-transition audit log for one course, newest first.

    Powers the "Stage history" panel on the course-edit page (PR-C3).
    Single query, no pagination — the transition log per course is
    small (one row per stage change). ``actor`` is selectinload'd to
    dodge the async-property landmine when serializing the nested
    LastReviewedBy on the relationship.
    """
    course = await get_or_404(db, Course, course_id, "Course not found")
    if course.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    result = await db.execute(
        select(CourseStageTransition)
        .where(CourseStageTransition.course_id == course_id)
        .options(selectinload(CourseStageTransition.actor))
        .order_by(CourseStageTransition.created_at.desc(), CourseStageTransition.id.desc())
    )
    rows = result.scalars().all()

    return [
        CourseStageTransitionHistoryItem(
            id=row.id,
            from_stage=row.from_stage,
            to_stage=row.to_stage,
            actor=(
                LastReviewedBy(id=row.actor.id, display_name=row.actor.full_name)
                if row.actor is not None
                else None
            ),
            note=row.note,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.patch(
    "/admin/courses/{course_id}/publish",
    response_model=CourseListItem,
    deprecated=True,
)
async def toggle_course_publish(
    course_id: int,
    body: CoursePublishToggleRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[DEPRECATED] Toggle a course's ``is_published`` flag.

    Kept for one release for FE-cache compatibility. Internally routes
    through ``transition_course_stage`` so the audit log captures the
    transition and the new ``lifecycle_stage`` field stays in sync.

    The mapping is intentionally lossy:
      * ``is_published: true``  -> transition to ``published``.
        Requires the course to currently be a draft; returns 400 with
        ``allowed_targets`` if not. FE should use /transition.
      * ``is_published: false`` -> transition to ``draft``.
        Allowed only from PUBLISHED or ARCHIVED;
        the FE should switch to the /transition endpoint for that path.

    Emits a ``Deprecation: true`` header and a ``Link`` pointing to the
    replacement endpoint.
    """
    course = await get_or_404(db, Course, course_id, "Course not found")
    if course.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    _coerce_lifecycle_stage(course)

    to_stage = CourseLifecycleStage.PUBLISHED if body.is_published else CourseLifecycleStage.DRAFT

    # Same allowed-transition pre-check as /transition, so the legacy
    # endpoint can keep returning a clean 400 + allowed_targets instead
    # of bubbling a bare ValueError.
    if not is_transition_allowed(course.lifecycle_stage, to_stage):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    f"Cannot transition course from "
                    f"{course.lifecycle_stage.value} to {to_stage.value} "
                    f"via the deprecated publish-toggle endpoint. Use "
                    f"POST /admin/courses/{course_id}/transition."
                ),
                "allowed_targets": sorted(
                    s.value for s in ALLOWED_TRANSITIONS.get(course.lifecycle_stage, set())
                ),
                "current_stage": course.lifecycle_stage.value,
            },
        )

    try:
        await transition_course_stage(
            db,
            course,
            to_stage,
            actor=current_user,
            note="(via deprecated publish-toggle endpoint)",
        )
    except EmptyCourseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await db.commit()
    await db.refresh(course)

    # Deprecation headers (RFC 8594 / draft-ietf-httpapi-deprecation-header).
    # ``Deprecation`` is the signal; ``Link`` points at the replacement so
    # API consumers can surface a one-click "use this instead" hint.
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = (
        f'</api/v1/learning/admin/courses/{course_id}/transition>; rel="successor-version"'
    )

    # Module/lesson counts re-computed to preserve the legacy response
    # shape. Aggregates beyond CourseListItem (enrollment_count etc.)
    # remain absent here — clients that need them should call the new
    # admin list endpoint after the transition.
    module_count_row = await db.execute(
        select(func.count(Module.id)).where(Module.course_id == course_id)
    )
    lesson_count_row = await db.execute(
        select(func.count(Lesson.id))
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course_id)
    )
    module_count = module_count_row.scalar_one() or 0
    lesson_count = lesson_count_row.scalar_one() or 0

    return CourseListItem(
        **{c.name: getattr(course, c.name) for c in course.__table__.columns},
        module_count=module_count,
        lesson_count=lesson_count,
    )


@router.post(
    "/admin/courses/{course_id}/clone",
    response_model=CourseListItem,
    status_code=status.HTTP_201_CREATED,
)
async def clone_course(
    course_id: int,
    payload: CourseCloneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Deep-clone a course into a new draft (admin only).

    Behavior:
      * Copies all course-level metadata except identity/audit fields and
        `lifecycle_stage` (the clone always starts as a draft via the
        column server-default).
      * Deep-copies every module and its lessons, preserving sort_order.
      * Skips enrollments, lesson_progress, and certificates - the clone is
        a fresh seasonal re-run, not a learner-state migration.
      * Wraps the whole operation in a single transaction; if any step
        fails, nothing is persisted.

    Note on `include_unpublished_lessons`: lessons currently have no
    publish flag in the data model, so this parameter is accepted but
    has no effect today. It's reserved for when per-lesson publish state
    lands. All lessons are copied regardless of the value.
    """
    # Eager-load modules + lessons to avoid MissingGreenlet during the copy.
    source_q = (
        select(Course)
        .where(Course.id == course_id, Course.deleted_at.is_(None))
        .options(selectinload(Course.modules).selectinload(Module.lessons))
    )
    source = (await db.execute(source_q)).scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    new_title = payload.new_title.strip()
    if not (3 <= len(new_title) <= 200):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title must be 3-200 characters",
        )

    # Duplicate-title check against live courses (ignore soft-deleted).
    dup_q = select(Course.id).where(
        func.lower(Course.title) == new_title.lower(),
        Course.deleted_at.is_(None),
    )
    if (await db.execute(dup_q)).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A course with that title already exists",
        )

    # Build the clone inside a single transaction. SQLAlchemy's AsyncSession
    # already runs inside an implicit transaction; on exception we roll
    # back explicitly so callers get a clean DB state, no orphan rows.
    new_course = Course(
        title=new_title,
        description=source.description,
        thumbnail_url=source.thumbnail_url,
        access_level=source.access_level,
        difficulty=source.difficulty,
        estimated_minutes=source.estimated_minutes,
        sensory_warning=source.sensory_warning,
        quiz_passing_threshold=source.quiz_passing_threshold,
        xp_reward=source.xp_reward,
        prerequisite_course_ids=list(source.prerequisite_course_ids or []),
        duration_days=source.duration_days,
        # Wave 1 (course-authoring friction strip): the clone is owned by the
        # admin who triggered the clone, NOT the source course's creator.
        # The new draft is the caller's now — they will iterate on it.
        created_by_id=current_user.id,
    )
    db.add(new_course)

    try:
        # Flush so new_course.id is populated for FK assignments.
        await db.flush()

        for src_module in source.modules:
            new_module = Module(
                course_id=new_course.id,
                title=src_module.title,
                description=src_module.description,
                sort_order=src_module.sort_order,
            )
            db.add(new_module)
            await db.flush()

            # `payload.include_unpublished_lessons` is accepted but ignored
            # - see endpoint docstring.
            for src_lesson in src_module.lessons:
                new_lesson = Lesson(
                    module_id=new_module.id,
                    title=src_lesson.title,
                    lesson_type=src_lesson.lesson_type,
                    content=src_lesson.content,
                    estimated_minutes=src_lesson.estimated_minutes,
                    sensory_notes=src_lesson.sensory_notes,
                    xp_reward=src_lesson.xp_reward,
                    sort_order=src_lesson.sort_order,
                    summary=src_lesson.summary,
                    visual_aid_url=src_lesson.visual_aid_url,
                    audio_narration_url=src_lesson.audio_narration_url,
                    preferred_break_interval=src_lesson.preferred_break_interval,
                    facilitator_notes=src_lesson.facilitator_notes,
                )
                db.add(new_lesson)

        await db.commit()
    except HTTPException:
        # Re-raise FastAPI errors as-is after rolling back.
        await db.rollback()
        raise
    except Exception:
        # Anything else (DB constraint, programming error, etc.) becomes a
        # 500 — but the rollback guarantees no partial clone is persisted.
        # Capture source_id up front so logging doesn't trigger a fresh
        # ORM load on a session that's mid-recovery.
        failed_source_id = course_id
        try:
            await db.rollback()
        except Exception:
            # Defensive: rollback can itself fail on an already-broken
            # connection (e.g. greenlet boundary). The original error is
            # still the meaningful one — surface that.
            logger.exception(
                "Rollback after clone failure also raised for source %s",
                failed_source_id,
            )
        logger.exception("Course clone failed for source course_id=%s", failed_source_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Course clone failed; no changes persisted",
        ) from None

    # Compute counts for the response - cheap, the clone is fresh.
    module_count = len(source.modules)
    lesson_count = sum(len(m.lessons) for m in source.modules)

    await db.refresh(new_course)
    return CourseListItem(
        **{c.name: getattr(new_course, c.name) for c in new_course.__table__.columns},
        module_count=module_count,
        lesson_count=lesson_count,
    )


# ============ BULK IMPORT (Wave 1 / W1-D) ============


@router.post(
    "/admin/courses/import",
    response_model=CourseImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_course(
    body: CourseImportPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """All-or-nothing nested course import (Wave 1 / W1-D).

    Replaces the client-side bulk-import orchestration in
    AdminCourseBulkImportPage (which fired 5+ sequential POSTs and left
    orphans on mid-stream failure). Single transaction: any error rolls
    back the whole tree.

    Behavior:
      * Always lands in `draft` (Pydantic Literal["draft"] on target_stage
        rejects 'published' with 422 — publishing must go through
        /admin/courses/{id}/transition to keep the audit trail intact).
      * Duplicate title (case-insensitive, ignoring soft-deleted) → 422
        BEFORE any insert, mirroring clone_course's pre-check convention.
      * IntegrityError → 409 as defensive belt-and-suspenders (the
        pre-check should catch the title case; this catches anything
        else, e.g. an FK that fails at flush time).
      * created_by_id populated from current_user.id (Task 1 column).
      * sort_order is client-supplied at every level — import order is
        meaningful.
      * Response uses selectinload across Course→Module→Lesson→QuizQuestion
        so async Pydantic serialization doesn't trip MissingGreenlet
        (per feedback_l30_async_property_landmine).
    """
    # 1) Duplicate-title pre-check (mirrors clone_course, learning.py:1213-1221).
    #    Live courses only — soft-deleted titles don't collide.
    incoming_title = body.course.title.strip()
    dup_q = select(Course.id).where(
        func.lower(Course.title) == incoming_title.lower(),
        Course.deleted_at.is_(None),
    )
    if (await db.execute(dup_q)).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A course with that title already exists",
        )

    # 2) Validate prerequisite IDs exist (mirrors create_course, learning.py:486-499).
    prereq_ids = body.course.prerequisite_course_ids or []
    if prereq_ids:
        prereq_result = await db.execute(select(Course.id).where(Course.id.in_(prereq_ids)))
        existing_prereq_ids = {row[0] for row in prereq_result.all()}
        missing_ids = set(prereq_ids) - existing_prereq_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"The following prerequisite course IDs do not exist: {sorted(missing_ids)}"
                ),
            )

    # 3) Build the tree inside a single transaction.
    course_id: Optional[int] = None
    try:
        course = Course(
            title=body.course.title,
            description=body.course.description,
            thumbnail_url=body.course.thumbnail_url,
            access_level=body.course.access_level,
            difficulty=body.course.difficulty,
            estimated_minutes=body.course.estimated_minutes,
            sensory_warning=body.course.sensory_warning,
            quiz_passing_threshold=body.course.quiz_passing_threshold,
            prerequisite_course_ids=body.course.prerequisite_course_ids,
            duration_days=body.course.duration_days,
            lifecycle_stage=CourseLifecycleStage.DRAFT,
            created_by_id=current_user.id,
        )
        db.add(course)
        await db.flush()
        course_id = course.id

        for mod in body.modules:
            module = Module(
                course_id=course.id,
                title=mod.title,
                description=mod.description,
                sort_order=mod.sort_order,
            )
            db.add(module)
            await db.flush()

            for lsn in mod.lessons:
                # Wave 1 W1-D: lesson import surface is intentionally narrow (title/lesson_type/
                # sort_order/content). xp_reward, summary, preferred_break_interval flow via
                # the rich editor (W2-A) only. Widen LessonBase + this constructor together
                # when the import wizard grows beyond the minimal-shape contract.
                # lesson_type is a LessonType enum from Pydantic — store its
                # string value (the Lesson.lesson_type column is String, not
                # SQLEnum, per the model).
                lesson = Lesson(
                    module_id=module.id,
                    title=lsn.title,
                    lesson_type=(
                        lsn.lesson_type.value
                        if hasattr(lsn.lesson_type, "value")
                        else lsn.lesson_type
                    ),
                    content=lsn.content,
                    estimated_minutes=lsn.estimated_minutes,
                    sensory_notes=lsn.sensory_notes,
                    sort_order=lsn.sort_order,
                    facilitator_notes=lsn.facilitator_notes,
                    visual_aid_url=lsn.visual_aid_url,
                    audio_narration_url=lsn.audio_narration_url,
                )
                db.add(lesson)
                await db.flush()

                for q in lsn.quiz_questions:
                    question = QuizQuestion(
                        lesson_id=lesson.id,
                        question_text=q.question_text,
                        question_type=q.question_type,
                        options=[opt.model_dump() for opt in q.options],
                        explanation=q.explanation,
                        sort_order=q.sort_order,
                    )
                    db.add(question)

        await db.commit()

    except IntegrityError as exc:
        await db.rollback()
        # Title-as-uniqueness is pre-checked above; remaining IntegrityErrors
        # are likely FK or any future unique constraints. 409 is the right
        # signal for the FE to surface "collision" without retrying.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        logger.exception("Bulk course import failed; rolled back")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Course import failed; no changes persisted",
        ) from None

    # 4) Re-fetch with selectinload across the whole tree so async
    #    serialization doesn't trip MissingGreenlet on relationship access.
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.modules)
            .selectinload(Module.lessons)
            .selectinload(Lesson.quiz_questions),
        )
    )
    return result.scalar_one()


# ============ SKILL → COURSES (Wave 5) ============


# ============ SKILL → COURSES (Wave 5) ============


@router.get("/skills/{skill_id}/courses", response_model=List[CourseBrief])
async def list_courses_for_skill(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List the courses that build a given skill (Wave 5).

    Powers the "Show N courses that build this skill" disclosure on the
    Skills tab. Staff-only (`require_staff`) — this view is part of the
    staff training admin surface; patrons consume the public course list
    instead.

    Returns a list of `CourseBrief` ordered by course title for predictable
    rendering. 404 if the skill doesn't exist (so the frontend can show a
    clean error rather than an empty disclosure that's actually wrong).
    """
    # Confirm the skill exists — distinguishes "no courses tagged yet"
    # (200 + []) from "no such skill" (404).
    skill = await db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    # Single round-trip: pull the association rows + their joined Course in
    # one query. Filter out soft-deleted and unpublished courses so the
    # public-facing chip → reverse view stays consistent with what users
    # can actually open.
    result = await db.execute(
        select(CourseSkill)
        .options(selectinload(CourseSkill.course))
        .where(CourseSkill.skill_id == skill_id)
    )
    rows = result.scalars().all()

    briefs: List[CourseBrief] = []
    for cs in rows:
        course = cs.course
        if course is None or course.deleted_at is not None:
            continue
        if course.lifecycle_stage != CourseLifecycleStage.PUBLISHED:
            continue
        briefs.append(CourseBrief(id=course.id, title=course.title, level_taught=cs.level_taught))

    # Stable, plain-language ordering for the disclosure list.
    briefs.sort(key=lambda b: b.title.lower())
    return briefs


# ============ MODULES ============


@router.post(
    "/courses/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_module(
    course_id: int,
    module_in: ModuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new module in a course (staff/admin only)."""
    course_result = await db.execute(select(Course).where(Course.id == course_id))
    if not course_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if module_in.course_id is not None and module_in.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"course_id in body ({module_in.course_id}) conflicts with URL path ({course_id})",
        )

    module_data = module_in.model_dump()
    module_data["course_id"] = course_id
    module = Module(**module_data)
    db.add(module)
    await db.commit()
    # Re-fetch with selectinload across the whole tree so async serialization
    # doesn't trip MissingGreenlet on relationship access -- ModuleResponse
    # nests LessonResponse, which itself needs `variants`, so a shallow
    # db.refresh(attribute_names=["lessons"]) isn't enough (same idiom as
    # the course-import re-fetch above).
    result = await db.execute(
        select(Module)
        .options(selectinload(Module.lessons).selectinload(Lesson.variants))
        .where(Module.id == module.id)
    )
    return result.scalar_one()


@router.put("/modules/{module_id}", response_model=ModuleResponse)
async def update_module(
    module_id: int,
    module_update: ModuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a module (staff/admin only)."""
    result = await db.execute(
        select(Module).options(selectinload(Module.lessons)).where(Module.id == module_id)
    )
    module = result.scalar_one_or_none()

    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    update_data = module_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(module, field, value)

    await db.commit()
    # Re-fetch with selectinload across the whole tree so async serialization
    # doesn't trip MissingGreenlet on relationship access -- ModuleResponse
    # nests LessonResponse, which itself needs `variants`, so a shallow
    # db.refresh(attribute_names=["lessons"]) isn't enough: it reloads the
    # `lessons` collection but not each lesson's own `variants` (same idiom
    # as the course-import re-fetch elsewhere in this file).
    result = await db.execute(
        select(Module)
        .options(selectinload(Module.lessons).selectinload(Lesson.variants))
        .where(Module.id == module_id)
    )
    return result.scalar_one()


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(
    module_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete a module and all its lessons (staff/admin only)."""
    module = await get_or_404(db, Module, module_id, "Module not found")

    await db.delete(module)
    await db.commit()
    return {"message": "Module deleted"}


# ============ LESSONS ============


@router.post(
    "/modules/{module_id}/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson(
    module_id: int,
    lesson_in: LessonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new lesson in a module (staff/admin only)."""
    module_result = await db.execute(select(Module).where(Module.id == module_id))
    if not module_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    if lesson_in.module_id is not None and lesson_in.module_id != module_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"module_id in body ({lesson_in.module_id}) conflicts with URL path ({module_id})",
        )

    lesson_data = lesson_in.model_dump()
    lesson_data["module_id"] = module_id
    lesson = Lesson(**lesson_data)
    db.add(lesson)
    await db.commit()
    # Refresh + eager-load the `variants` relationship so LessonResponse
    # serialization doesn't trip MissingGreenlet on lazy access (same
    # pattern as create_stub_lesson / duplicate_lesson below).
    await db.refresh(lesson, attribute_names=["variants"])
    return lesson


@router.post(
    "/admin/modules/{module_id}/lessons/stub",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_stub_lesson(
    module_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a minimal empty lesson (admin authoring stub) -- Wave 1 / W1-B.

    The FE routes the admin into the rich lesson editor after creating a
    stub, so they don't have to fill out the LessonCreate form just to get
    a row to edit. Stubs that the admin never fills in (title=='' AND
    content body empty) get swept nightly after 24h by
    ``app.services.lesson_sweep_service`` -- the sweep emails the course's
    ``created_by_id`` admin first (when not NULL) and defers entirely if
    the daily email cap can't cover the notification batch (per
    ``feedback_l30_email_safeguard_cap_masks_failure``).
    """
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    # Append-at-end: max(sort_order) + 1, defaulting to 0 for the first lesson.
    next_sort = await db.scalar(
        select(func.coalesce(func.max(Lesson.sort_order), -1) + 1).where(
            Lesson.module_id == module_id
        )
    )
    lesson = Lesson(
        module_id=module_id,
        title="",
        lesson_type=LessonType.ARTICLE.value,
        content={"body": ""},
        sort_order=int(next_sort or 0),
    )
    db.add(lesson)
    await db.commit()
    # Refresh + eager-load the `variants` relationship so LessonResponse
    # serialization doesn't trip MissingGreenlet on lazy access. New stubs
    # always have zero variants, but pydantic still reads the attr.
    await db.refresh(lesson, attribute_names=["variants"])
    return lesson


@router.post(
    "/admin/lessons/{lesson_id}/duplicate",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.variants), selectinload(Lesson.quiz_questions))
        .where(Lesson.id == lesson_id)
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    next_sort = await db.scalar(
        select(func.coalesce(func.max(Lesson.sort_order), -1) + 1).where(
            Lesson.module_id == original.module_id
        )
    )
    copy = Lesson(
        module_id=original.module_id,
        title=f"{original.title} (copy)",
        lesson_type=original.lesson_type,
        content=dict(original.content),
        estimated_minutes=original.estimated_minutes,
        sensory_notes=original.sensory_notes,
        xp_reward=original.xp_reward,
        sort_order=int(next_sort or 0),
        summary=original.summary,
        visual_aid_url=original.visual_aid_url,
        audio_narration_url=original.audio_narration_url,
        facilitator_notes=original.facilitator_notes,
    )
    db.add(copy)
    await db.flush()

    for q in original.quiz_questions:
        db.add(
            QuizQuestion(
                lesson_id=copy.id,
                question_text=q.question_text,
                question_type=q.question_type,
                options=list(q.options) if q.options else None,
                explanation=q.explanation,
                sort_order=q.sort_order,
            )
        )

    await db.commit()
    await db.refresh(copy, attribute_names=["variants"])
    return copy


@router.put("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    lesson_update: LessonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a lesson (staff/admin only)."""
    result = await db.execute(
        select(Lesson).options(selectinload(Lesson.variants)).where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    update_data = lesson_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)

    await db.commit()
    # Refresh + eager-load `variants` so LessonResponse serialization
    # doesn't trip MissingGreenlet on lazy access (commit expires the
    # selectinload above; same pattern as create_stub_lesson / duplicate_lesson).
    await db.refresh(lesson, attribute_names=["variants"])
    return lesson


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete a lesson (staff/admin only)."""
    lesson = await get_or_404(db, Lesson, lesson_id, "Lesson not found")

    await db.delete(lesson)
    await db.commit()
    return {"message": "Lesson deleted"}


@router.post(
    "/lessons/{lesson_id}/media",
    response_model=LessonMediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_lesson_media(
    lesson_id: int,
    media_type: Literal["visual_aid", "audio"] = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Upload a visual aid (image) or audio narration for a lesson.

    Returns the public URL. The caller is responsible for persisting it on
    the lesson via PUT /lessons/{lesson_id} (visual_aid_url / audio_narration_url).
    """
    lesson = await get_or_404(db, Lesson, lesson_id, "Lesson not found")

    # Read in chunks with early size bailout to prevent memory exhaustion
    from app.core.file_validation import MAX_FILE_SIZES

    size_limit = MAX_FILE_SIZES.get(
        "audio" if media_type == "audio" else "image", MAX_FILE_SIZES["default"]
    )
    chunks = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)  # 64KB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > size_limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large",
            )
        chunks.append(chunk)
    content = b"".join(chunks)
    detected_mime = validate_file_type(content[:16], file.filename or "upload")

    if media_type == "visual_aid":
        if detected_mime is None or not detected_mime.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Visual aid must be an image (PNG, JPEG, GIF, WebP)",
            )
        size_category = "image"
    else:  # audio
        if detected_mime is None or not detected_mime.startswith("audio/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio must be MP3, WAV, or Ogg",
            )
        size_category = "audio"

    if not validate_file_size(len(content), size_category):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    storage = get_storage()
    storage_key = storage.generate_unique_key(
        prefix=f"lesson-media/{lesson_id}/{media_type}",
        filename=file.filename or "upload",
    )
    storage_path, _hash, _size = await storage.upload_file(
        file_data=BytesIO(content),
        key=storage_key,
        content_type=detected_mime,
    )

    logger.info(
        "Lesson media upload: user_id=%s lesson_id=%s media_type=%s mime=%s size=%s",
        current_user.id,
        lesson_id,
        media_type,
        detected_mime,
        len(content),
    )

    return LessonMediaUploadResponse(media_type=media_type, url=storage_path)


@router.post(
    "/courses/{course_id}/media",
    response_model=CourseMediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_course_media(
    course_id: int,
    media_type: Literal["thumbnail"] = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Upload a course thumbnail (image). Returns the public URL.

    The caller persists it on the course via PUT /courses/{course_id}
    (thumbnail_url). Mirrors upload_lesson_media.
    """
    await get_or_404(db, Course, course_id, "Course not found")

    from app.core.file_validation import MAX_FILE_SIZES

    size_limit = MAX_FILE_SIZES.get("image", MAX_FILE_SIZES["default"])
    chunks = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > size_limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large",
            )
        chunks.append(chunk)
    content = b"".join(chunks)
    detected_mime = validate_file_type(content[:16], file.filename or "upload")

    if detected_mime is None or not detected_mime.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thumbnail must be an image (PNG, JPEG, GIF, WebP)",
        )

    if not validate_file_size(len(content), "image"):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    storage = get_storage()
    storage_key = storage.generate_unique_key(
        prefix=f"course-media/{course_id}/thumbnail",
        filename=file.filename or "upload",
    )
    storage_path, _hash, _size = await storage.upload_file(
        file_data=BytesIO(content),
        key=storage_key,
        content_type=detected_mime,
    )

    logger.info(
        "Course media upload: user_id=%s course_id=%s mime=%s size=%s",
        current_user.id,
        course_id,
        detected_mime,
        len(content),
    )

    return CourseMediaUploadResponse(media_type=media_type, url=storage_path)


# ============ ENROLLMENTS ============


@router.post(
    "/courses/{course_id}/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_in_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enroll current user in a course."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()

    if not course or course.lifecycle_stage != CourseLifecycleStage.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if not can_access_course(current_user, course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this course"
        )

    # Check prerequisite courses are completed
    prerequisite_ids = course.prerequisite_course_ids or []
    if prerequisite_ids:
        prerequisites = await get_prerequisite_courses_with_status(
            db, prerequisite_ids, current_user.id
        )
        incomplete_prereqs = [p for p in prerequisites if not p.completed]

        if incomplete_prereqs:
            missing_titles = [p.title for p in incomplete_prereqs]
            missing_count = len(incomplete_prereqs)

            # Build a helpful, accessible error message
            if missing_count == 1:
                detail = (
                    f"You must complete the prerequisite course before enrolling: "
                    f'"{missing_titles[0]}". '
                    f"Please complete this course first and then try again."
                )
            else:
                titles_list = ", ".join(f'"{t}"' for t in missing_titles[:-1])
                titles_list += f', and "{missing_titles[-1]}"'
                detail = (
                    f"You must complete {missing_count} prerequisite courses before enrolling: "
                    f"{titles_list}. "
                    f"Please complete these courses first and then try again."
                )

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    existing = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id, Enrollment.course_id == course_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Already enrolled in this course"
        )

    # Compute due_at from the course's configured duration. NULL = no deadline.
    now = datetime.now(timezone.utc)
    due_at = now + timedelta(days=course.duration_days) if course.duration_days else None
    enrollment = Enrollment(
        user_id=current_user.id,
        course_id=course_id,
        enrolled_at=now,
        due_at=due_at,
    )
    db.add(enrollment)

    # Auto-create UserStats on first enrollment so the gamification surface
    # (XP, streaks, level) has a row to read instead of 404'ing for users
    # who enrolled before ever loading the stats page. Mirrors the lazy
    # create in learning_gamification.get_my_stats.
    stats_result = await db.execute(select(UserStats).where(UserStats.user_id == current_user.id))
    if stats_result.scalar_one_or_none() is None:
        db.add(
            UserStats(
                user_id=current_user.id,
                total_xp=0,
                current_streak=0,
                longest_streak=0,
                lessons_completed=0,
                courses_completed=0,
                labs_completed=0,
            )
        )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(enrollment)
    return enrollment


@router.get("/my-courses", response_model=List[EnrolledCourse])
async def list_my_courses(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List courses the current user is enrolled in with progress."""
    # Get enrollments with courses.
    # Wave 5: eager-load course_skills + their Skill so the inline chip strip
    # on the trainings table doesn't trigger N+1 round-trips per row. The
    # `Course.skills` @property reads `course_skills` from `__dict__`, so
    # the relationship MUST be loaded here.
    result = await db.execute(
        select(Enrollment)
        .options(
            selectinload(Enrollment.course)
            .selectinload(Course.course_skills)
            .joinedload(CourseSkill.skill)
        )
        .where(Enrollment.user_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
    )
    enrollments = result.scalars().all()

    if not enrollments:
        return []

    # Get course IDs for batch queries
    course_ids = [e.course_id for e in enrollments]

    # Batch query: total lessons per course
    lesson_counts_result = await db.execute(
        select(Module.course_id, func.count(Lesson.id).label("total"))
        .join(Lesson, Lesson.module_id == Module.id)
        .where(Module.course_id.in_(course_ids))
        .group_by(Module.course_id)
    )
    lesson_counts = {row[0]: row[1] for row in lesson_counts_result.all()}

    # Batch query: completed lessons per course for this user
    completed_counts_result = await db.execute(
        select(Module.course_id, func.count(LessonProgress.id).label("completed"))
        .join(Lesson, Lesson.module_id == Module.id)
        .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
        .where(
            Module.course_id.in_(course_ids),
            LessonProgress.user_id == current_user.id,
            LessonProgress.status == "completed",
        )
        .group_by(Module.course_id)
    )
    completed_counts = {row[0]: row[1] for row in completed_counts_result.all()}

    # Build response
    enrolled_courses = []
    for enrollment in enrollments:
        total_lessons = lesson_counts.get(enrollment.course_id, 0)
        completed_lessons = completed_counts.get(enrollment.course_id, 0)
        progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

        enrolled_courses.append(
            EnrolledCourse(
                course=enrollment.course,
                enrollment=enrollment,
                progress_percentage=round(progress, 1),
                completed_lessons=completed_lessons,
                total_lessons=total_lessons,
            )
        )

    return enrolled_courses


@router.get("/progress/{course_id}", response_model=CourseProgressResponse)
async def get_course_progress(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's progress in a course."""
    from ...services.learning_service import LearningService

    # Check enrollment
    enrollment = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id, Enrollment.course_id == course_id
        )
    )
    if not enrollment.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You are not enrolled in this course"
        )

    # Get course with details
    course = await LearningService.get_course_with_details(db, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Calculate progress
    progress = await LearningService.calculate_course_progress(db, current_user.id, course_id)

    # Get next lesson
    next_lesson = await LearningService.get_next_lesson(db, current_user.id, course_id)

    return {
        "course_id": course_id,
        "course_title": course.title,
        **progress,
        "next_lesson_id": next_lesson.id if next_lesson else None,
        "next_lesson_title": next_lesson.title if next_lesson else None,
    }


@router.get("/courses/{course_id}/enroll", response_model=EnrollmentResponse)
async def get_courses__course_id__enroll(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's enrollment info for a course."""
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id, Enrollment.course_id == course_id
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")

    return enrollment


@router.get("/courses/{course_id}/modules", response_model=List[ModuleResponse])
async def get_courses__course_id__modules(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all modules for a course."""
    course_result = await db.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.lifecycle_stage != CourseLifecycleStage.PUBLISHED and not is_staff_or_admin(
        current_user
    ):
        raise HTTPException(status_code=404, detail="Course not found")

    modules_result = await db.execute(
        select(Module)
        .options(selectinload(Module.lessons))
        .where(Module.course_id == course_id)
        .order_by(Module.sort_order)
    )
    modules = modules_result.scalars().all()

    return modules


router.include_router(learning_team_router)
