# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Content Flagging Admin API Endpoints

Provides endpoints for:
- Viewing flagged content in moderation queue
- Staff feedback on flags
- Resolving flags
- Statistics and analytics
"""

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.exceptions import InternalServerError
from ...core.error_codes import ErrorCode
from ...core.shortcuts import get_or_404
from ...models.user import User
from ...models.content_flag import ContentFlag, FlagStatus, FlagAnalysisResult
from ...schemas.event_review import (
    ContentFlagResponse,
    ContentFlagListResponse,
    ContentFlagFeedbackRequest,
    ContentFlagStatisticsResponse,
    ContentFlagReviewContent,
)
from ...models.event_review import EventReview
from ...models.event import Event
from ...services.content_flagging_service import ContentFlaggingService
from .auth import get_current_user
from .dependencies import require_staff
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/content-flags", tags=["content-flags"])


# =============================================================================
# Helper Functions
# =============================================================================


async def build_review_content(flag: ContentFlag, db: AsyncSession) -> Optional[ContentFlagReviewContent]:
    if flag.review_type != "event_review":
        return None

    result = await db.execute(
        select(EventReview, Event.title)
        .join(Event, EventReview.event_id == Event.id, isouter=True)
        .where(EventReview.id == flag.review_id)
    )
    row = result.first()
    if not row:
        return None

    review, event_title = row
    return ContentFlagReviewContent(
        review_id=review.id,
        review_type=flag.review_type,
        comment=review.comment,
        rating=review.rating,
        patron_email=review.patron_email,
        moderation_status=review.moderation_status,
        is_removed=review.is_removed,
        event_id=review.event_id,
        event_title=event_title,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


# =============================================================================
# Content Flags Endpoints
# =============================================================================

@router.get("/", response_model=dict)
async def get_flagged_content(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    review_type: Optional[str] = Query(None, description="Filter by review type (event_review, indie_review, etc.)"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, RESOLVED, FALSE_POSITIVE, FALSE_NEGATIVE)"),
    min_score: int = Query(70, ge=0, le=100, description="Minimum confidence score (flag severity)"),
    max_score: Optional[int] = Query(None, ge=0, le=100, description="Maximum confidence score"),
    flag_type: Optional[str] = Query(None, description="Filter by flag type (SPAM, HATE_SPEECH, EXCESSIVE_CAPS, etc.)"),
    date_from: Optional[datetime] = Query(None, description="Filter flags created on or after this date"),
    date_to: Optional[datetime] = Query(None, description="Filter flags created on or before this date"),
    resolved_by: Optional[str] = Query(None, description="Filter by assigned moderator (staff email)"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all flagged content for staff review.

    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - review_type: Filter by review type (event_review, indie_review, etc.)
    - status: Filter by status (PENDING, RESOLVED, FALSE_POSITIVE, FALSE_NEGATIVE)
    - min_score: Minimum confidence score to include (default: 70)
    - max_score: Maximum confidence score to include
    - flag_type: Filter by flag type (SPAM, HATE_SPEECH, EXCESSIVE_CAPS, SUSPICIOUS_PATTERN, OFF_TOPIC, DUPLICATE)
    - date_from: Filter flags created on or after this date (ISO format)
    - date_to: Filter flags created on or before this date (ISO format)
    - resolved_by: Filter by assigned moderator (staff email who resolved/is assigned)

    Returns:
    - items: List of flagged content with AI scores and details
    - total: Total number of matching flags
    - page: Current page
    - per_page: Items per page
    """
    try:
        query = select(ContentFlag)

        # Apply filters
        filters = []
        if status:
            try:
                filters.append(ContentFlag.status == FlagStatus(status))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}") from None

        if review_type:
            filters.append(ContentFlag.review_type == review_type)

        if flag_type:
            try:
                from ...models.content_flag import FlagType as ModelFlagType
                filters.append(ContentFlag.flag_type == ModelFlagType(flag_type))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid flag_type: {flag_type}") from None

        filters.append(ContentFlag.confidence_score >= min_score)

        if max_score is not None:
            filters.append(ContentFlag.confidence_score <= max_score)

        # Date range filters
        if date_from:
            filters.append(ContentFlag.created_at >= date_from)
        if date_to:
            filters.append(ContentFlag.created_at <= date_to)

        # Assigned moderator filter
        if resolved_by:
            filters.append(ContentFlag.resolved_by == resolved_by)

        if filters:
            from sqlalchemy import and_
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count(ContentFlag.id))
        if filters:
            from sqlalchemy import and_
            count_query = count_query.where(and_(*filters))

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = (
            query
            .order_by(ContentFlag.status == FlagStatus.PENDING, ContentFlag.confidence_score.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await db.execute(query)
        flags = result.scalars().all()

        items = [
            ContentFlagListResponse(
                id=flag.id,
                review_id=flag.review_id,
                review_type=flag.review_type,
                flag_type=str(flag.flag_type),
                confidence_score=flag.confidence_score,
                status=str(flag.status),
                created_at=flag.created_at,
                updated_at=flag.updated_at
            )
            for flag in flags
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching flagged content")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/{flag_id}", response_model=ContentFlagResponse)
async def get_flag_details(
    flag_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific flag."""
    try:
        result = await db.execute(
            select(ContentFlag)
            .options(selectinload(ContentFlag.analysis_results))
            .where(ContentFlag.id == flag_id)
        )
        flag = result.scalar_one_or_none()

        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")

        review_content = await build_review_content(flag, db)

        return ContentFlagResponse(
            id=flag.id,
            review_id=flag.review_id,
            review_type=flag.review_type,
            flag_type=str(flag.flag_type),
            confidence_score=flag.confidence_score,
            analysis_details=flag.analysis_details,
            status=str(flag.status),
            resolved_by=flag.resolved_by,
            resolved_at=flag.resolved_at,
            resolution_notes=flag.resolution_notes,
            is_correct_flag=flag.is_correct_flag,
            staff_feedback=flag.staff_feedback,
            created_at=flag.created_at,
            updated_at=flag.updated_at,
            review_content=review_content,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching flag details")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.patch("/{flag_id}/resolve", response_model=ContentFlagResponse)
async def resolve_flag(
    flag_id: int,
    feedback: ContentFlagFeedbackRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve a flagged item with staff feedback.

    Status options:
    - resolved: Flag resolved, no action needed
    - false_positive: Flag was incorrect
    - false_negative: Flag should have been flagged but wasn't

    Staff can provide:
    - is_correct_flag: Whether the flag was correct
    - resolution_notes: Notes about how it was resolved
    - staff_feedback: Feedback for model improvement
    """
    try:
        # Validate status
        valid_statuses = ["resolved", "false_positive", "false_negative"]
        if feedback.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        # Convert to enum value
        status_map = {
            "resolved": FlagStatus.RESOLVED.value,
            "false_positive": FlagStatus.FALSE_POSITIVE.value,
            "false_negative": FlagStatus.FALSE_NEGATIVE.value
        }

        flag = await ContentFlaggingService.resolve_flag(
            db=db,
            flag_id=flag_id,
            status=status_map[feedback.status],
            resolved_by=staff_user.email,
            is_correct_flag=feedback.is_correct_flag,
            resolution_notes=feedback.resolution_notes,
            staff_feedback=feedback.staff_feedback
        )

        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")

        logger.info(
            f"Flag resolved by {staff_user.email}: flag_id={flag_id}, "
            f"status={feedback.status}, is_correct={feedback.is_correct_flag}"
        )

        return ContentFlagResponse(
            id=flag.id,
            review_id=flag.review_id,
            review_type=flag.review_type,
            flag_type=str(flag.flag_type),
            confidence_score=flag.confidence_score,
            analysis_details=flag.analysis_details,
            status=str(flag.status),
            resolved_by=flag.resolved_by,
            resolved_at=flag.resolved_at,
            resolution_notes=flag.resolution_notes,
            is_correct_flag=flag.is_correct_flag,
            staff_feedback=flag.staff_feedback,
            created_at=flag.created_at,
            updated_at=flag.updated_at
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error resolving flag")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.post("/{flag_id}/feedback", response_model=ContentFlagResponse)
async def submit_flag_feedback(
    flag_id: int,
    feedback: ContentFlagFeedbackRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Submit feedback on a flag for model training."""
    try:
        flag = await get_or_404(db, ContentFlag, flag_id, "Flag not found")

        # Update feedback fields
        flag.is_correct_flag = feedback.is_correct_flag
        flag.staff_feedback = feedback.staff_feedback

        if flag.status == FlagStatus.PENDING:
            flag.status = FlagStatus(
                FlagStatus.RESOLVED.value
                if feedback.is_correct_flag
                else FlagStatus.FALSE_POSITIVE.value
            )

        flag.resolved_by = staff_user.email
        flag.resolved_at = datetime.now(timezone.utc)
        flag.resolution_notes = feedback.resolution_notes

        await db.commit()
        await db.refresh(flag)

        return ContentFlagResponse(
            id=flag.id,
            review_id=flag.review_id,
            review_type=flag.review_type,
            flag_type=str(flag.flag_type),
            confidence_score=flag.confidence_score,
            analysis_details=flag.analysis_details,
            status=str(flag.status),
            resolved_by=flag.resolved_by,
            resolved_at=flag.resolved_at,
            resolution_notes=flag.resolution_notes,
            is_correct_flag=flag.is_correct_flag,
            staff_feedback=flag.staff_feedback,
            created_at=flag.created_at,
            updated_at=flag.updated_at
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error submitting feedback")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/statistics/summary", response_model=ContentFlagStatisticsResponse)
async def get_flag_statistics(
    days: int = Query(30, ge=1, le=365),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """
    Get content flagging statistics for the last N days.

    Returns:
    - total_flags: Total flags created
    - avg_confidence: Average confidence score
    - high_confidence_flags: Flags with score > 70
    - false_positives: Number of false positive flags
    - false_negatives: Number of false negative flags
    - false_positive_rate: Percentage of flags that were false positives
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import and_

        cutoff_date = utc_now() - timedelta(days=days)

        # Total flags
        total_result = await db.execute(
            select(func.count(ContentFlag.id)).where(
                ContentFlag.created_at >= cutoff_date
            )
        )
        total_flags = total_result.scalar() or 0

        # Average confidence
        avg_result = await db.execute(
            select(func.avg(ContentFlag.confidence_score)).where(
                ContentFlag.created_at >= cutoff_date
            )
        )
        avg_confidence = float(avg_result.scalar() or 0)

        # High confidence flags
        high_conf_result = await db.execute(
            select(func.count(ContentFlag.id)).where(
                and_(
                    ContentFlag.created_at >= cutoff_date,
                    ContentFlag.confidence_score > 70
                )
            )
        )
        high_confidence_flags = high_conf_result.scalar() or 0

        # False positives
        fp_result = await db.execute(
            select(func.count(ContentFlag.id)).where(
                and_(
                    ContentFlag.created_at >= cutoff_date,
                    ContentFlag.status == FlagStatus.FALSE_POSITIVE
                )
            )
        )
        false_positives = fp_result.scalar() or 0

        # False negatives
        fn_result = await db.execute(
            select(func.count(ContentFlag.id)).where(
                and_(
                    ContentFlag.created_at >= cutoff_date,
                    ContentFlag.status == FlagStatus.FALSE_NEGATIVE
                )
            )
        )
        false_negatives = fn_result.scalar() or 0

        # False positive rate
        resolved_result = await db.execute(
            select(func.count(ContentFlag.id)).where(
                and_(
                    ContentFlag.created_at >= cutoff_date,
                    ContentFlag.status != FlagStatus.PENDING
                )
            )
        )
        total_resolved = resolved_result.scalar() or 0
        false_positive_rate = (
            (false_positives / total_resolved * 100)
            if total_resolved > 0
            else 0.0
        )

        return ContentFlagStatisticsResponse(
            total_flags=total_flags,
            avg_confidence=round(avg_confidence, 2),
            high_confidence_flags=high_confidence_flags,
            false_positives=false_positives,
            false_negatives=false_negatives,
            false_positive_rate=round(false_positive_rate, 2)
        )

    except Exception:
        logger.exception("Error getting statistics")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/statistics/by-type", response_model=dict)
async def get_statistics_by_type(
    days: int = Query(30, ge=1, le=365),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Get flagging statistics broken down by flag type."""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import and_

        cutoff_date = utc_now() - timedelta(days=days)

        query = select(
            ContentFlag.flag_type,
            func.count(ContentFlag.id).label("count"),
            func.avg(ContentFlag.confidence_score).label("avg_score")
        ).where(
            ContentFlag.created_at >= cutoff_date
        ).group_by(ContentFlag.flag_type)

        result = await db.execute(query)
        rows = result.all()

        stats = {
            row[0].value: {
                "count": row[1],
                "avg_score": round(float(row[2] or 0), 2)
            }
            for row in rows
        }

        return {
            "stats_by_type": stats,
            "period_days": days
        }

    except Exception:
        logger.exception("Error getting type statistics")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/statistics/by-review-type", response_model=dict)
async def get_statistics_by_review_type(
    days: int = Query(30, ge=1, le=365),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Get flagging statistics broken down by review type."""
    try:
        from datetime import datetime, timedelta

        cutoff_date = utc_now() - timedelta(days=days)

        query = select(
            ContentFlag.review_type,
            func.count(ContentFlag.id).label("count"),
            func.avg(ContentFlag.confidence_score).label("avg_score")
        ).where(
            ContentFlag.created_at >= cutoff_date
        ).group_by(ContentFlag.review_type)

        result = await db.execute(query)
        rows = result.all()

        stats = {
            row[0]: {
                "count": row[1],
                "avg_score": round(float(row[2] or 0), 2)
            }
            for row in rows
        }

        return {
            "stats_by_review_type": stats,
            "period_days": days
        }

    except Exception:
        logger.exception("Error getting review type statistics")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None
