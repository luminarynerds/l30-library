# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Beta Feedback API - Submit and manage beta tester feedback."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.beta_feedback import BetaFeedback, BetaFeedbackType, FeedbackStatus, FeedbackPriority
from ...models.user import User
from .auth import get_current_user, get_optional_user

router = APIRouter(prefix="/beta-feedback", tags=["beta"])


# Schemas
class FeedbackCreate(BaseModel):
    type: BetaFeedbackType
    subject: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    page_url: Optional[str] = Field(default=None, max_length=500)
    browser_info: Optional[str] = Field(default=None, max_length=300)
    email: Optional[str] = Field(default=None, max_length=254)

class FeedbackResponse(BaseModel):
    id: int
    type: BetaFeedbackType
    status: FeedbackStatus
    priority: FeedbackPriority
    subject: str
    description: str
    page_url: Optional[str] = None
    email: Optional[str] = None
    admin_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class FeedbackUpdate(BaseModel):
    status: Optional[FeedbackStatus] = None
    priority: Optional[FeedbackPriority] = None
    admin_notes: Optional[str] = None


# Public - submit feedback (auth optional)
@router.post("/", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(  # noqa: role-check -- public beta feedback submission, optional auth
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    feedback = BetaFeedback(
        type=data.type,
        subject=data.subject,
        description=data.description,
        page_url=data.page_url,
        browser_info=data.browser_info,
        email=data.email if not current_user else current_user.email,
        submitted_by_id=current_user.id if current_user else None,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


# Admin - list all feedback
@router.get("/", response_model=List[FeedbackResponse])
async def list_feedback(
    type_filter: Optional[BetaFeedbackType] = Query(default=None, alias="type"),
    status_filter: Optional[FeedbackStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if str(current_user.role) not in ("SUPER_ADMIN", "ADMIN", "STAFF"):
        raise HTTPException(status_code=403, detail="Staff access required")

    query = select(BetaFeedback).options(selectinload(BetaFeedback.submitted_by)).order_by(BetaFeedback.created_at.desc())
    if type_filter:
        query = query.where(BetaFeedback.type == type_filter)
    if status_filter:
        query = query.where(BetaFeedback.status == status_filter)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


# Admin - get stats
@router.get("/stats")
async def feedback_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if str(current_user.role) not in ("SUPER_ADMIN", "ADMIN", "STAFF"):
        raise HTTPException(status_code=403, detail="Staff access required")

    total = await db.execute(select(func.count(BetaFeedback.id)))
    by_type = await db.execute(
        select(BetaFeedback.type, func.count(BetaFeedback.id))
        .group_by(BetaFeedback.type)
    )
    by_status = await db.execute(
        select(BetaFeedback.status, func.count(BetaFeedback.id))
        .group_by(BetaFeedback.status)
    )

    return {
        "total": total.scalar() or 0,
        "by_type": {row[0].value: row[1] for row in by_type.all()},
        "by_status": {row[0].value: row[1] for row in by_status.all()},
    }


# Admin - update feedback
@router.patch("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: int,
    data: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if str(current_user.role) not in ("SUPER_ADMIN", "ADMIN", "STAFF"):
        raise HTTPException(status_code=403, detail="Staff access required")

    result = await db.execute(select(BetaFeedback).where(BetaFeedback.id == feedback_id))
    feedback = result.scalar_one_or_none()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if data.status is not None:
        feedback.status = data.status
        if data.status == FeedbackStatus.RESOLVED:
            feedback.resolved_by_id = current_user.id
            feedback.resolved_at = datetime.now(timezone.utc)
    if data.priority is not None:
        feedback.priority = data.priority
    if data.admin_notes is not None:
        feedback.admin_notes = data.admin_notes

    await db.commit()
    await db.refresh(feedback)
    return feedback
