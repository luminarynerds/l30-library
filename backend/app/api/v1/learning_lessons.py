# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Learning - Lesson Management API Endpoints

Provides endpoints for:
- Getting lesson content
- Marking lessons complete
- User preferences (accessibility)
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.learning import (
    Course, CourseView, Enrollment, Lesson, LessonBookmark,
    LessonProgress, Module, UserPreferences
)
from ...models.user import User, UserRole
from ...schemas.learning import (
    LessonProgressResponse, LessonProgressBrief, LessonWithQuiz,
    UserPreferencesResponse, UserPreferencesUpdate,
    MessageResponse, RecentCourseView, PositionSavedResponse,
    LessonPositionUpdate
)
from .auth import get_current_user, get_current_user_optional
from .dependencies import can_access_course, is_staff_or_admin

router = APIRouter(prefix="/learning", tags=["learning-lessons"])

# User accessibility/UI preferences (theme, font size, high contrast, sidebar
# collapse) are global per-user settings, NOT a learning-platform feature. They
# live on their own router so registry.py can mount them WITHOUT the
# require_learning_platform_enabled guard — otherwise turning the learning
# platform off 404s every preference save and the staff sidebar can never be
# collapsed (the save rolls back, causing a flicker).
preferences_router = APIRouter(prefix="/learning", tags=["user-preferences"])


@router.get("/lessons/{lesson_id}", response_model=LessonWithQuiz)
async def get_lesson(
    lesson_id: int,
    preview: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get lesson content with quiz questions if applicable.

    Access:
      - Anonymous / unenrolled patrons may read a lesson ONLY if it is a free
        preview (``lesson.is_preview``) on a patron-level course. No progress
        is recorded for them.
      - Authenticated users need course access + enrollment (or staff/admin),
        except preview lessons which are open to any authenticated user.
      - Staff/admin may pass ``preview=true`` to view any lesson as a patron
        would see it, bypassing the enrollment requirement. Non-staff callers
        with ``preview=true`` are rejected the same as without it.
    """
    # preview=true is a staff-only affordance; gate it immediately so the rest
    # of the function can assume normal patron rules for non-staff callers.
    if preview:
        if current_user is None:
            raise HTTPException(
                status_code=401,
                detail="Sign in with a staff account to use preview mode",
            )
        if not is_staff_or_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Staff or admin role required for preview mode",
            )

    result = await db.execute(
        select(Lesson)
        .options(
            selectinload(Lesson.variants),
            selectinload(Lesson.quiz_questions),
            selectinload(Lesson.module).selectinload(Module.course),
        )
        .where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    course = lesson.module.course
    is_preview = bool(lesson.is_preview)
    is_staff = is_staff_or_admin(current_user) if current_user else False

    if current_user is None:
        # Anonymous: free-preview lessons of patron courses only.
        if not (is_preview and course.access_level == "patron"):
            raise HTTPException(
                status_code=401,
                detail="Sign in and enroll to read this lesson",
            )
    else:
        if not can_access_course(current_user, course):
            raise HTTPException(
                status_code=403, detail="You don't have access to this lesson"
            )
        # preview=true (already staff-gated above) skips the enrollment check
        # so staff can see unenrolled lessons exactly as patrons would.
        if not is_staff and not is_preview and not preview:
            enrollment = await db.execute(
                select(Enrollment).where(
                    Enrollment.user_id == current_user.id,
                    Enrollment.course_id == lesson.module.course_id,
                )
            )
            if not enrollment.scalar_one_or_none():
                raise HTTPException(
                    status_code=403, detail="Please enroll in this course first"
                )

    # Progress is per-user; anonymous previewers don't get a progress record.
    lesson.progress = None
    if current_user is not None:
        progress_result = await db.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == current_user.id,
                LessonProgress.lesson_id == lesson_id,
            )
        )
        progress = progress_result.scalar_one_or_none()

        if not progress:
            progress = LessonProgress(
                user_id=current_user.id,
                lesson_id=lesson_id,
                status="in_progress",
                started_at=datetime.now(timezone.utc),
            )
            db.add(progress)
            await db.commit()
            await db.refresh(progress)
        elif progress.status == "not_started":
            progress.status = "in_progress"
            progress.started_at = datetime.now(timezone.utc)
            await db.commit()

        # Attach the user's progress so the viewer can restore scroll position
        # on resume without a second round-trip.
        lesson.progress = LessonProgressBrief(
            scroll_position=progress.scroll_position,
            status=progress.status,
        )

    # Strip facilitator notes for non-staff (and anonymous) users.
    if not is_staff:
        lesson.facilitator_notes = None

    return lesson


@router.post("/lessons/{lesson_id}/complete", response_model=LessonProgressResponse)
async def complete_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a lesson as completed."""
    # Load lesson with module and course for access checks
    result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.module).selectinload(Module.course))
        .where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Check course access permission
    if not can_access_course(current_user, lesson.module.course):
        raise HTTPException(
            status_code=403, detail="You don't have access to this lesson"
        )

    # Check enrollment (unless staff/admin)
    enrollment = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == lesson.module.course_id,
        )
    )
    if not enrollment.scalar_one_or_none() and not is_staff_or_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Please enroll in this course first"
        )

    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            status="completed",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(progress)
    else:
        progress.status = "completed"
        progress.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(progress)
    return progress




@router.put("/lessons/{lesson_id}/progress", response_model=LessonProgressResponse)
async def update_lesson_progress(
    lesson_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update lesson progress (status, percentage, etc.)."""
    result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.module).selectinload(Module.course))
        .where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    if not can_access_course(current_user, lesson.module.course):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        db.add(progress)

    # Apply updates from body
    if "status" in body:
        progress.status = body["status"]
        if body["status"] == "completed" and not progress.completed_at:
            progress.completed_at = datetime.now(timezone.utc)
    if "progress_percentage" in body:
        progress.progress_percentage = body["progress_percentage"]

    await db.commit()
    await db.refresh(progress)
    return progress

# ============ PREFERENCES (ND Accessibility) ============


@preferences_router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get current user's accessibility preferences."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)

    return prefs


@preferences_router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    prefs_update: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user's accessibility preferences."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)

    update_data = prefs_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    await db.commit()
    await db.refresh(prefs)
    return prefs


@router.get("/lessons/{lesson_id}/complete", response_model=LessonProgressResponse)
async def get_lesson_completion_status(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the current user's completion status for a lesson.

    Returns the LessonProgress record containing:
    - status: not_started, in_progress, or completed
    - quiz_score: user's quiz score if taken (null if not taken)
    - started_at: when user started the lesson
    - completed_at: when user completed the lesson (if completed)
    """
    # Load lesson with module and course for access checks
    result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.module).selectinload(Module.course))
        .where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Check course access permission
    if not can_access_course(current_user, lesson.module.course):
        raise HTTPException(
            status_code=403, detail="You don't have access to this lesson"
        )

    # Check enrollment (unless staff/admin)
    enrollment = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == lesson.module.course_id,
        )
    )
    if not enrollment.scalar_one_or_none() and not is_staff_or_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Please enroll in this course first"
        )

    # Get the lesson progress record
    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    progress = result.scalar_one_or_none()

    # If no progress record exists, return not_started status with null timestamps
    if not progress:
        progress = LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            status="not_started",
        )

    return progress


# ============ RECENTLY VIEWED COURSES ============


@router.get("/my-recent-courses", response_model=List[RecentCourseView])
async def get_recent_courses(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's recently viewed courses."""
    result = await db.execute(
        select(CourseView)
        .options(selectinload(CourseView.course))
        .where(CourseView.user_id == current_user.id)
        .order_by(CourseView.viewed_at.desc())
        .limit(limit)
    )
    views = result.scalars().all()

    return [
        {
            "id": v.course.id,
            "title": v.course.title,
            "viewedAt": v.viewed_at.isoformat() if v.viewed_at else None,
        }
        for v in views
        if v.course
    ]


@router.post("/courses/{course_id}/view", response_model=MessageResponse)
async def track_course_view(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record that the user viewed a course."""
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    result = await db.execute(
        select(CourseView).where(
            CourseView.user_id == current_user.id,
            CourseView.course_id == course_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.viewed_at = datetime.now(timezone.utc)
    else:
        db.add(CourseView(
            user_id=current_user.id,
            course_id=course_id,
            viewed_at=datetime.now(timezone.utc),
        ))

    await db.commit()
    return {"message": "Course view recorded"}


# ============ LESSON POSITION (RESUME) ============


@router.put("/lessons/{lesson_id}/position", response_model=PositionSavedResponse)
async def save_lesson_position(
    lesson_id: int,
    body: LessonPositionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save user's scroll/resume position in a lesson."""
    position = body.position

    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            status="in_progress",
            scroll_position=position,
            started_at=datetime.now(timezone.utc),
        )
        db.add(progress)
    else:
        progress.scroll_position = position

    await db.commit()
    return {"message": "Position saved", "position": position}


# ============ BOOKMARKS ============


@router.get("/my-bookmarks", response_model=List[int])
async def get_bookmarks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's bookmarked lesson IDs."""
    result = await db.execute(
        select(LessonBookmark.lesson_id)
        .where(LessonBookmark.user_id == current_user.id)
        .order_by(LessonBookmark.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/lessons/{lesson_id}/bookmark", response_model=MessageResponse)
async def add_bookmark(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bookmark a lesson."""
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    result = await db.execute(
        select(LessonBookmark).where(
            LessonBookmark.user_id == current_user.id,
            LessonBookmark.lesson_id == lesson_id,
        )
    )
    if result.scalar_one_or_none():
        return {"message": "Already bookmarked"}

    db.add(LessonBookmark(
        user_id=current_user.id,
        lesson_id=lesson_id,
    ))
    await db.commit()
    return {"message": "Bookmark added"}


@router.delete("/lessons/{lesson_id}/bookmark", response_model=MessageResponse)
async def remove_bookmark(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a lesson bookmark."""
    result = await db.execute(
        select(LessonBookmark).where(
            LessonBookmark.user_id == current_user.id,
            LessonBookmark.lesson_id == lesson_id,
        )
    )
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.delete(bookmark)
    await db.commit()
    return {"message": "Bookmark removed"}

