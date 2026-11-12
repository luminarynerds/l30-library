# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Series Management API Endpoints

Provides REST API for:
- Series reading order and sequences
- Patron reading history tracking
- Series completion tracking
- Series waitlists
- Series recommendations
- Series notifications and alerts
- Series popularity metrics
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.series_management import (
    SeriesReadingOrder, PatronReadingHistory, SeriesCompletion,
    SeriesWaitlist, SeriesRecommendation, SeriesNotificationRule,
    SeriesPopularity, NotificationTrigger, WaitlistStatus
)
from ...models.user import User, UserRole
from ...schemas.series_management import (
    SeriesReadingOrderCreate, SeriesReadingOrderResponse,
    PatronReadingHistoryCreate, PatronReadingHistoryResponse,
    SeriesCompletionResponse, SeriesCompletionUpdate,
    SeriesWaitlistCreate, SeriesWaitlistResponse,
    SeriesRecommendationResponse,
    SeriesNotificationRuleCreate, SeriesNotificationRuleResponse,
    SeriesNotificationRuleUpdate,
    NextBookSuggestion, SeriesSuggestionsResponse,
    AvailableBooksResponse, SeriesInfoResponse,
    SeriesPopularityResponse, PatronSeriesAnalytics
)
from ...services.series_management_service import SeriesManagementService
from .auth import get_current_user


router = APIRouter(prefix="/series", tags=["series"])


# ============================================================================
# Dependency Functions
# ============================================================================


async def get_series_service(db: AsyncSession = Depends(get_db)) -> SeriesManagementService:
    return SeriesManagementService(db)


# ============================================================================
# Series Reading Order Endpoints
# ============================================================================


@router.get("/reading-order/{series_title}", response_model=List[SeriesReadingOrderResponse])
async def get_series_reading_order(
    series_title: str,
    limit: Optional[int] = Query(None, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get complete reading order for a series."""
    service = SeriesManagementService(db)
    books = await service.get_series_reading_order(series_title, limit)

    if not books:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Series '{series_title}' not found"
        )

    return [SeriesReadingOrderResponse.model_validate(b) for b in books]


@router.get("/{series_title}/info", response_model=SeriesInfoResponse)
async def get_series_info(
    series_title: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get complete information about a series."""
    service = SeriesManagementService(db)
    books = await service.get_series_reading_order(series_title)

    if not books:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Series '{series_title}' not found"
        )

    starting_points = await service.get_series_starting_points(series_title)

    patron_progress = None
    patron_on_waitlist = False

    if current_user:
        result = await db.execute(
            select(SeriesCompletion).where(
                SeriesCompletion.user_id == current_user.id,
                SeriesCompletion.series_title == series_title
            )
        )
        completion = result.scalars().first()
        if completion:
            patron_progress = SeriesCompletionResponse.model_validate(completion)
            patron_progress.completion_percentage = await service.get_series_completion_percentage(
                current_user.id, series_title
            )

        result = await db.execute(
            select(SeriesWaitlist).where(
                SeriesWaitlist.user_id == current_user.id,
                SeriesWaitlist.series_title == series_title,
                SeriesWaitlist.status.in_(["waiting", "notified"])
            )
        )
        waitlist = result.scalars().first()
        patron_on_waitlist = bool(waitlist)

    return SeriesInfoResponse(
        series_title=series_title,
        total_books=len(books),
        books=[SeriesReadingOrderResponse.model_validate(b) for b in books],
        starting_points=[SeriesReadingOrderResponse.model_validate(b) for b in starting_points],
        patron_progress=patron_progress,
        patron_on_waitlist=patron_on_waitlist
    )


@router.post("/reading-order", response_model=SeriesReadingOrderResponse, status_code=status.HTTP_201_CREATED)
async def add_book_to_series(
    data: SeriesReadingOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a book to series reading order (staff only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.STAFF, UserRole.DIRECTOR, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can add books to series"
        )

    service = SeriesManagementService(db)
    entry = await service.add_book_to_series(
        series_title=data.series_title,
        bibframe_work_id=data.bibframe_work_id,
        sequence_number=data.sequence_number,
        book_title=data.book_title,
        series_type=data.series_type,
        created_by_id=current_user.id,
        is_recommended_start=data.is_recommended_starting_point
    )

    return SeriesReadingOrderResponse.model_validate(entry)


# ============================================================================
# Reading History Endpoints
# ============================================================================


@router.post("/reading-history", response_model=PatronReadingHistoryResponse, status_code=status.HTTP_201_CREATED)
async def log_book_read(
    data: PatronReadingHistoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Log that current user has read a book."""
    service = SeriesManagementService(db)
    history = await service.log_book_read(
        user_id=current_user.id,
        bibframe_work_id=data.bibframe_work_id,
        is_completed=data.is_completed,
        rating=data.rating,
        review=data.review,
        format_read=data.format_read
    )

    return PatronReadingHistoryResponse.model_validate(history)


@router.get("/reading-history", response_model=List[PatronReadingHistoryResponse])
async def get_reading_history(
    limit: Optional[int] = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's reading history."""
    service = SeriesManagementService(db)
    history = await service.get_patron_reading_history(current_user.id)

    return [
        PatronReadingHistoryResponse.model_validate(h)
        for h in history[:limit]
    ]


@router.get("/reading-history/{series_title}", response_model=List[PatronReadingHistoryResponse])
async def get_reading_history_for_series(
    series_title: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's reading history for a specific series."""
    service = SeriesManagementService(db)
    history = await service.get_patron_books_in_series(current_user.id, series_title)

    return [PatronReadingHistoryResponse.model_validate(h) for h in history]


@router.post("/reading-history/{work_id}/favorite", response_model=PatronReadingHistoryResponse)
async def mark_as_favorite(
    work_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a book as favorite."""
    service = SeriesManagementService(db)
    history = await service.mark_book_as_favorite(current_user.id, work_id)

    return PatronReadingHistoryResponse.model_validate(history)


# ============================================================================
# Series Completion Endpoints
# ============================================================================


@router.get("/completion/{series_title}", response_model=SeriesCompletionResponse)
async def get_series_completion(
    series_title: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's progress in a series."""
    service = SeriesManagementService(db)
    completion = await service.track_series_progress(current_user.id, series_title)

    response = SeriesCompletionResponse.model_validate(completion)
    response.completion_percentage = await service.get_series_completion_percentage(
        current_user.id, series_title
    )

    return response


@router.get("/completion", response_model=List[SeriesCompletionResponse])
async def get_all_series_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's progress in all series they're following."""
    service = SeriesManagementService(db)
    completions = await service.get_patron_series_progress(current_user.id)

    results = []
    for completion in completions:
        response = SeriesCompletionResponse.model_validate(completion)
        response.completion_percentage = await service.get_series_completion_percentage(
            current_user.id, completion.series_title
        )
        results.append(response)

    return results


@router.patch("/completion/{series_title}", response_model=SeriesCompletionResponse)
async def update_series_completion(
    series_title: str,
    data: SeriesCompletionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update series completion settings (follow, prefer, etc)."""
    result = await db.execute(
        select(SeriesCompletion).where(
            SeriesCompletion.user_id == current_user.id,
            SeriesCompletion.series_title == series_title
        )
    )
    completion = result.scalars().first()

    if not completion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Series completion not found"
        )

    if data.is_following is not None:
        completion.is_following = data.is_following
    if data.preferred is not None:
        completion.preferred = data.preferred

    await db.flush()
    await db.refresh(completion)

    response = SeriesCompletionResponse.model_validate(completion)
    service = SeriesManagementService(db)
    response.completion_percentage = await service.get_series_completion_percentage(
        current_user.id, series_title
    )

    return response


# ============================================================================
# Series Waitlist Endpoints
# ============================================================================


@router.post("/waitlist", response_model=SeriesWaitlistResponse, status_code=status.HTTP_201_CREATED)
async def add_to_waitlist(
    data: SeriesWaitlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add current user to series waitlist."""
    service = SeriesManagementService(db)
    entry = await service.add_to_series_waitlist(
        user_id=current_user.id,
        series_title=data.series_title,
        next_book_sequence=data.next_book_sequence,
        next_book_title=data.next_book_title,
        notification_method=data.notification_method
    )

    return SeriesWaitlistResponse.model_validate(entry)


@router.get("/waitlist", response_model=List[SeriesWaitlistResponse])
async def get_my_waitlist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's series waitlist."""
    service = SeriesManagementService(db)
    entries = await service.get_active_waitlist_entries(current_user.id)

    return [SeriesWaitlistResponse.model_validate(e) for e in entries]


@router.delete("/waitlist/{waitlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_waitlist(
    waitlist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove current user from series waitlist."""
    entry = await db.get(SeriesWaitlist, waitlist_id)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found"
        )

    if entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove other user's waitlist entry"
        )

    entry.status = WaitlistStatus.cancelled
    await db.flush()


# ============================================================================
# Series Recommendations Endpoints
# ============================================================================


@router.get("/recommendations", response_model=List[SeriesRecommendationResponse])
async def get_my_recommendations(
    limit: Optional[int] = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get series recommendations for current user."""
    service = SeriesManagementService(db)

    # Get existing recommendations
    recommendations = await service.get_patron_recommendations(current_user.id, limit)

    # If not enough, generate new ones
    if len(recommendations) < limit:
        await service.generate_recommendations_for_patron(current_user.id)
        recommendations = await service.get_patron_recommendations(current_user.id, limit)

    return [SeriesRecommendationResponse.model_validate(r) for r in recommendations]


@router.post("/recommendations/{rec_id}/view", response_model=SeriesRecommendationResponse)
async def track_recommendation_view(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Track that user viewed a recommendation."""
    service = SeriesManagementService(db)
    rec = await service.track_recommendation_engagement(rec_id, viewed=True)

    if not rec or rec.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    return SeriesRecommendationResponse.model_validate(rec)


@router.post("/recommendations/{rec_id}/click", response_model=SeriesRecommendationResponse)
async def track_recommendation_click(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Track that user clicked on a recommendation."""
    service = SeriesManagementService(db)
    rec = await service.track_recommendation_engagement(rec_id, clicked=True)

    if not rec or rec.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    return SeriesRecommendationResponse.model_validate(rec)


# ============================================================================
# Series Notifications Endpoints
# ============================================================================


@router.post("/notifications/rules", response_model=SeriesNotificationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_rule(
    data: SeriesNotificationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a notification rule for series updates."""
    service = SeriesManagementService(db)
    rule = await service.create_notification_rule(
        user_id=current_user.id,
        series_title=data.series_title,
        trigger_type=data.trigger_type,
        notification_method=data.notification_method,
        frequency=data.frequency
    )

    return SeriesNotificationRuleResponse.model_validate(rule)


@router.get("/notifications/rules", response_model=List[SeriesNotificationRuleResponse])
async def get_my_notification_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's notification rules."""
    service = SeriesManagementService(db)
    rules = await service.get_active_notification_rules(current_user.id)

    return [SeriesNotificationRuleResponse.model_validate(r) for r in rules]


@router.patch("/notifications/rules/{rule_id}", response_model=SeriesNotificationRuleResponse)
async def update_notification_rule(
    rule_id: int,
    data: SeriesNotificationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a notification rule."""
    rule = await db.get(SeriesNotificationRule, rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )

    if rule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify other user's rule"
        )

    if data.is_active is not None:
        rule.is_active = data.is_active
    if data.notification_method is not None:
        rule.notification_method = data.notification_method
    if data.frequency is not None:
        rule.frequency = data.frequency

    await db.flush()
    await db.refresh(rule)

    return SeriesNotificationRuleResponse.model_validate(rule)


@router.delete("/notifications/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a notification rule."""
    rule = await db.get(SeriesNotificationRule, rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )

    if rule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete other user's rule"
        )

    await db.delete(rule)
    await db.flush()


# ============================================================================
# Series Suggestions & Dashboard Endpoints
# ============================================================================


@router.get("/suggestions/next-books", response_model=SeriesSuggestionsResponse)
async def get_next_book_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get suggestions for next books in series patron is reading."""
    service = SeriesManagementService(db)
    suggestions = await service.get_series_suggestions(current_user.id)

    return SeriesSuggestionsResponse(
        suggestions=[
            NextBookSuggestion(**s) for s in suggestions
        ],
        count=len(suggestions)
    )


@router.get("/available-next-books", response_model=AvailableBooksResponse)
async def get_available_next_books(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get next books available for patron in series they're reading."""
    service = SeriesManagementService(db)
    available = await service.get_available_next_books(current_user.id)

    return AvailableBooksResponse(
        available_books=available,
        count=len(available)
    )


# ============================================================================
# Series Popularity Endpoints
# ============================================================================


@router.get("/popularity/{series_title}", response_model=SeriesPopularityResponse)
async def get_series_popularity(
    series_title: str,
    db: AsyncSession = Depends(get_db)
):
    """Get popularity metrics for a series."""
    service = SeriesManagementService(db)
    popularity = await service.update_series_popularity(series_title)

    return SeriesPopularityResponse.model_validate(popularity)


@router.get("/trending", response_model=List[SeriesPopularityResponse])
async def get_trending_series(
    limit: Optional[int] = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get trending series."""
    service = SeriesManagementService(db)
    trending = await service.get_trending_series(limit)

    return [SeriesPopularityResponse.model_validate(t) for t in trending]


@router.get("/popular", response_model=List[SeriesPopularityResponse])
async def get_popular_series(
    limit: Optional[int] = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get most popular series."""
    service = SeriesManagementService(db)
    popular = await service.get_popular_series(limit)

    return [SeriesPopularityResponse.model_validate(p) for p in popular]


# ============================================================================
# Analytics Endpoints
# ============================================================================


@router.get("/analytics", response_model=PatronSeriesAnalytics)
async def get_series_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get series reading analytics for current user."""
    service = SeriesManagementService(db)

    # Get series statistics
    result = await db.execute(
        select(SeriesCompletion).where(
            SeriesCompletion.user_id == current_user.id
        )
    )
    all_series = result.scalars().all()

    completed = [s for s in all_series if s.is_completed]

    avg_completion = 0.0
    if all_series:
        total_completion = 0.0
        for s in all_series:
            total_completion += await service.get_series_completion_percentage(current_user.id, s.series_title)
        avg_completion = total_completion / len(all_series)

    favorite = None
    if all_series:
        preferred = [s for s in all_series if s.preferred]
        if preferred:
            favorite = preferred[0].series_title

    # Get recommendations and trending
    result = await db.execute(
        select(SeriesRecommendation).where(
            SeriesRecommendation.user_id == current_user.id
        ).limit(10)
    )
    recommendations = result.scalars().all()

    trending = await service.get_trending_series(10)

    return PatronSeriesAnalytics(
        total_series_started=len(all_series),
        series_completed=len(completed),
        average_completion_percentage=avg_completion,
        favorite_series=favorite,
        current_reading=await service.get_patron_series_progress(current_user.id),
        trending_series=[SeriesPopularityResponse.model_validate(t) for t in trending],
        recommended_series=[SeriesRecommendationResponse.model_validate(r) for r in recommendations]
    )
