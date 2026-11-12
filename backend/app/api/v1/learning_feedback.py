# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Learning - Course Feedback API Endpoints

Provides endpoints for:
- Patrons: submit feedback on courses/lessons
- Staff/Admin: list, filter, and moderate feedback
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.learning import Course, CourseFeedback, Lesson, Module
from ...models.user import User, UserRole
from ...schemas.learning import (
    CourseFeedbackAdminResponse,
    CourseFeedbackAdminUpdate,
    CourseFeedbackCreate,
    CourseFeedbackListResponse,
    CourseFeedbackResponse,
)
from .auth import get_current_user, get_optional_user
from .dependencies import check_staff_access

router = APIRouter(prefix="/learning", tags=["learning-feedback"])


# ---------------------------------------------------------------------------
# Patron endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/feedback",
    response_model=CourseFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    payload: CourseFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback on a course or lesson."""
    # Verify course exists
    result = await db.execute(select(Course).where(Course.id == payload.course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    # Verify lesson exists and belongs to the specified course (via Module)
    if payload.lesson_id is not None:
        result = await db.execute(
            select(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Lesson.id == payload.lesson_id,
                Module.course_id == payload.course_id,
            )
        )
        lesson = result.scalar_one_or_none()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found or does not belong to the specified course",
            )

    feedback = CourseFeedback(
        user_id=current_user.id,
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        feedback_type=str(payload.feedback_type),
        comment=payload.comment,
        status="pending",
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback



@router.get("/courses/{course_id}/reviews")
async def get_course_reviews(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get published reviews for a course (public endpoint)."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Course not found")

    query = (
        select(CourseFeedback)
        .where(
            CourseFeedback.course_id == course_id,
            CourseFeedback.feedback_type == "review",
            CourseFeedback.rating.isnot(None),
            CourseFeedback.status.in_(["approved", "reviewed"]),
        )
        .order_by(CourseFeedback.created_at.desc())
    )
    result = await db.execute(query)
    feedbacks = result.scalars().all()

    user_ids = {f.user_id for f in feedbacks if f.user_id}
    users_map = {}
    if user_ids:
        res = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in res.scalars().all():
            users_map[u.id] = u

    reviews = []
    for fb in feedbacks:
        user = users_map.get(fb.user_id)
        reviews.append({
            "id": fb.id,
            "user_name": user.full_name if user and hasattr(user, "full_name") else "Anonymous",
            "rating": fb.rating,
            "comment": fb.comment,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
        })

    ratings = [fb.rating for fb in feedbacks if fb.rating]
    distribution = {i: 0 for i in range(1, 6)}
    for r in ratings:
        bucket = min(5, max(1, int(round(r))))
        distribution[bucket] += 1

    summary = {
        "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0,
        "total_reviews": len(ratings),
        "rating_distribution": distribution,
    }

    return {"summary": summary, "reviews": reviews}


@router.post("/courses/{course_id}/reviews", status_code=status.HTTP_201_CREATED)
async def submit_course_review(
    course_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a review (rating + comment) for a course."""
    rating = payload.get("rating")
    comment = payload.get("comment", "")

    if not rating or not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    result = await db.execute(select(Course).where(Course.id == course_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Course not found")

    existing = await db.execute(
        select(CourseFeedback).where(
            CourseFeedback.user_id == current_user.id,
            CourseFeedback.course_id == course_id,
            CourseFeedback.feedback_type == "review",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already reviewed this course")

    feedback = CourseFeedback(
        user_id=current_user.id,
        course_id=course_id,
        feedback_type="review",
        rating=float(rating),
        comment=comment[:2000] if comment else None,
        status="approved",
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    user_name = current_user.full_name if hasattr(current_user, "full_name") else current_user.email
    return {
        "id": feedback.id,
        "user_name": user_name,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
    }


# ---------------------------------------------------------------------------
# Admin / Staff endpoints
# ---------------------------------------------------------------------------




@router.get(
    "/admin/feedback",
    response_model=CourseFeedbackListResponse,
)
async def list_feedback(
    course_id: Optional[int] = None,
    lesson_id: Optional[int] = None,
    feedback_type: Optional[str] = None,
    feedback_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all course feedback (staff/admin only). Supports filtering."""
    check_staff_access(current_user)

    query = select(CourseFeedback)

    if course_id is not None:
        query = query.where(CourseFeedback.course_id == course_id)
    if lesson_id is not None:
        query = query.where(CourseFeedback.lesson_id == lesson_id)
    if feedback_type:
        query = query.where(CourseFeedback.feedback_type == feedback_type)
    if feedback_status:
        query = query.where(CourseFeedback.status == feedback_status)

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginated results
    offset = (page - 1) * page_size
    query = query.order_by(CourseFeedback.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    rows = result.scalars().all()

    # Batch-load related names
    user_ids = {r.user_id for r in rows if r.user_id}
    reviewer_ids = {r.reviewed_by_id for r in rows if r.reviewed_by_id}
    all_user_ids = user_ids | reviewer_ids
    course_ids = {r.course_id for r in rows}
    lesson_ids = {r.lesson_id for r in rows if r.lesson_id}

    users_map: dict[int, User] = {}
    if all_user_ids:
        res = await db.execute(select(User).where(User.id.in_(all_user_ids)))
        for u in res.scalars().all():
            users_map[u.id] = u

    courses_map: dict[int, str] = {}
    if course_ids:
        res = await db.execute(select(Course.id, Course.title).where(Course.id.in_(course_ids)))
        for cid, title in res.all():
            courses_map[cid] = title

    lessons_map: dict[int, str] = {}
    if lesson_ids:
        res = await db.execute(select(Lesson.id, Lesson.title).where(Lesson.id.in_(lesson_ids)))
        for lid, title in res.all():
            lessons_map[lid] = title

    items = []
    for fb in rows:
        submitter = users_map.get(fb.user_id) if fb.user_id else None
        reviewer = users_map.get(fb.reviewed_by_id) if fb.reviewed_by_id else None
        items.append(
            CourseFeedbackAdminResponse(
                id=fb.id,
                user_id=fb.user_id,
                course_id=fb.course_id,
                lesson_id=fb.lesson_id,
                feedback_type=fb.feedback_type,
                rating=fb.rating,
                comment=fb.comment,
                status=fb.status,
                admin_notes=fb.admin_notes,
                reviewed_by_id=fb.reviewed_by_id,
                reviewed_at=fb.reviewed_at,
                created_at=fb.created_at,
                updated_at=fb.updated_at,
                user_name=submitter.full_name if submitter and hasattr(submitter, "full_name") else (submitter.email if submitter else None),
                user_email=submitter.email if submitter else None,
                course_title=courses_map.get(fb.course_id),
                lesson_title=lessons_map.get(fb.lesson_id) if fb.lesson_id else None,
                reviewer_name=reviewer.full_name if reviewer and hasattr(reviewer, "full_name") else (reviewer.email if reviewer else None),
            )
        )

    # Aggregate counts across all feedback (not just current page)
    pending_result = await db.execute(
        select(func.count()).where(CourseFeedback.status == "pending")
    )
    pending_count = pending_result.scalar() or 0

    issue_types = ("content_error", "broken_link", "accessibility", "other")
    issue_result = await db.execute(
        select(func.count()).where(CourseFeedback.feedback_type.in_(issue_types))
    )
    issue_count = issue_result.scalar() or 0

    return CourseFeedbackListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pending_count=pending_count,
        issue_count=issue_count,
    )


@router.patch(
    "/admin/feedback/{feedback_id}",
    response_model=CourseFeedbackResponse,
)
async def update_feedback(
    feedback_id: int,
    payload: CourseFeedbackAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update feedback status / admin notes (staff/admin only)."""
    check_staff_access(current_user)

    result = await db.execute(
        select(CourseFeedback).where(CourseFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found"
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status":
            setattr(feedback, field, value.value if hasattr(value, "value") else value)
        else:
            setattr(feedback, field, value)

    feedback.reviewed_by_id = current_user.id
    feedback.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(feedback)
    return feedback


@router.delete(
    "/admin/feedback/{feedback_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a feedback entry (admin only)."""
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete feedback",
        )

    result = await db.execute(
        select(CourseFeedback).where(CourseFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found"
        )

    await db.delete(feedback)
    await db.commit()
