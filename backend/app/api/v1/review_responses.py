# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API endpoints for review responses.

Provides CRUD endpoints for author/staff responses to reviews on:
- Event reviews
- Indie ebook reviews

Access control ensures only review authors or staff can create responses.
"""

from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.user import User, UserRole
from ...models.review_response import (
    EventReviewResponse,
    ResponseModerationStatus
)
from ...models.event_review import EventReview
from ...schemas.review_response import (
    EventReviewResponseCreate, EventReviewResponseResponse,
    EventReviewResponseUpdate, ReviewResponseApprovalRequest,
)
from .auth import get_current_user
from .dependencies import is_staff_or_admin, require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/review-responses", tags=["review-responses"])


# ============================================================================
# Event Review Responses
# ============================================================================

@router.post("/event/{review_id}", response_model=EventReviewResponseResponse)
async def create_event_review_response(
    review_id: int,
    response_data: EventReviewResponseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a response to an event review.

    Only the event author or library staff can create responses.
    """
    # Verify review exists
    await get_or_404(db, EventReview, review_id, "Review not found")

    # Check authorization - only staff or event organizer can respond
    is_staff = is_staff_or_admin(current_user)
    if not is_staff:
        raise HTTPException(
            status_code=403,
            detail="Only staff can respond to reviews"
        )

    # Create response
    response = EventReviewResponse(
        review_id=review_id,
        author_id=current_user.id,
        content=response_data.content,
        author_name=current_user.first_name,
        author_email=current_user.email,
        is_staff_response=is_staff,
        moderation_status=ResponseModerationStatus.PENDING if not is_staff else ResponseModerationStatus.APPROVED,
    )

    db.add(response)
    await db.commit()
    await db.refresh(response)

    logger.info(f"Event review response created: review={review_id}, author={current_user.id}")

    return response


@router.get("/event/{review_id}", response_model=list[EventReviewResponseResponse])
async def get_event_review_responses(
    review_id: int,
    approved_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get responses for an event review.

    By default, returns only approved responses. Staff can request all.
    """
    query = select(EventReviewResponse).where(
        EventReviewResponse.review_id == review_id
    )

    if approved_only:
        query = query.where(
            EventReviewResponse.moderation_status == ResponseModerationStatus.APPROVED
        )

    query = query.order_by(EventReviewResponse.moderated_at)
    result = await db.execute(query)
    responses = result.scalars().all()

    return responses


@router.put("/event-response/{response_id}", response_model=EventReviewResponseResponse)
async def update_event_review_response(
    response_id: int,
    response_data: EventReviewResponseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an event review response.

    Only the response author or staff can update.
    """
    response = await get_or_404(db, EventReviewResponse, response_id, "Response not found")

    # Check authorization
    is_staff = is_staff_or_admin(current_user)
    if response.author_id != current_user.id and not is_staff:
        raise HTTPException(status_code=403, detail="Not authorized to update this response")

    response.content = response_data.content
    response.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(response)

    logger.info(f"Event review response updated: response={response_id}")

    return response


@router.delete("/event-response/{response_id}")
async def delete_event_review_response(
    response_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an event review response.

    Only the response author or staff can delete.
    """
    response = await get_or_404(db, EventReviewResponse, response_id, "Response not found")

    # Check authorization
    is_staff = is_staff_or_admin(current_user)
    if response.author_id != current_user.id and not is_staff:
        raise HTTPException(status_code=403, detail="Not authorized to delete this response")

    await db.delete(response)
    await db.commit()

    logger.info(f"Event review response deleted: response={response_id}")

    return {"success": True}


@router.post("/event-response/{response_id}/approve", response_model=EventReviewResponseResponse)
async def approve_event_review_response(
    response_id: int,
    approval_data: ReviewResponseApprovalRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a pending event review response."""
    response = await get_or_404(db, EventReviewResponse, response_id, "Response not found")

    response.moderation_status = (
        ResponseModerationStatus.APPROVED if approval_data.approved
        else ResponseModerationStatus.REJECTED
    )
    response.moderated_by_id = staff_user.id
    response.moderated_at = datetime.now(timezone.utc)
    response.moderation_reason = approval_data.reason

    await db.commit()
    await db.refresh(response)

    logger.info(
        f"Event review response {approval_data.approved and 'approved' or 'rejected'}: "
        f"response={response_id}, staff={staff_user.id}"
    )

    return response

