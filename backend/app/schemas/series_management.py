# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

from ..models.series_management import (
    SeriesType, NotificationTrigger, WaitlistStatus, RecommendationReason
)


# ============================================================================
# Series Reading Order Schemas
# ============================================================================


class SeriesReadingOrderCreate(StrictInputSchema):
    series_title: str = Field(..., min_length=1, max_length=500)
    series_type: SeriesType = SeriesType.main_series
    bibframe_work_id: int
    sequence_number: float
    book_title: str = Field(..., min_length=1, max_length=1000)
    publication_year: Optional[int] = None
    is_recommended_starting_point: bool = False
    skip_note: Optional[str] = None
    parent_series_id: Optional[int] = None


class SeriesReadingOrderResponse(BaseModel):
    id: int
    series_title: str
    series_type: SeriesType
    sequence_number: float
    book_title: str
    publication_year: Optional[int]
    is_recommended_starting_point: bool
    skip_note: Optional[str]
    verified: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Patron Reading History Schemas
# ============================================================================


class PatronReadingHistoryCreate(StrictInputSchema):
    bibframe_work_id: int
    is_completed: bool = True
    rating: Optional[float] = Field(None, ge=0, le=5)
    review: Optional[str] = None
    format_read: Optional[str] = None  # print, ebook, audiobook


class PatronReadingHistoryResponse(BaseModel):
    id: int
    user_id: int
    bibframe_work_id: int
    started_date: Optional[datetime]
    completed_date: Optional[datetime]
    is_completed: bool
    rating: Optional[float]
    favorite: bool
    did_not_finish: bool
    format_read: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Series Completion Schemas
# ============================================================================


class SeriesCompletionResponse(BaseModel):
    id: int
    user_id: int
    series_title: str
    total_books_in_series: Optional[int]
    books_read: int
    books_available: int
    last_book_read_number: Optional[float]
    last_book_read_title: Optional[str]
    next_book_number: Optional[float]
    next_book_title: Optional[str]
    is_completed: bool
    is_following: bool
    preferred: bool
    completion_percentage: float = Field(..., ge=0, le=100)
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class SeriesCompletionUpdate(StrictInputSchema):
    is_following: Optional[bool] = None
    preferred: Optional[bool] = None


# ============================================================================
# Series Waitlist Schemas
# ============================================================================


class SeriesWaitlistCreate(StrictInputSchema):
    series_title: str = Field(..., min_length=1, max_length=500)
    next_book_sequence: Optional[float] = None
    next_book_title: Optional[str] = None
    notification_method: str = "email"  # email, sms, both


class SeriesWaitlistResponse(BaseModel):
    id: int
    user_id: int
    series_title: str
    next_book_sequence: Optional[float]
    next_book_title: Optional[str]
    status: WaitlistStatus
    position: int
    notification_method: Optional[str]
    notified_at: Optional[datetime]
    fulfilled_date: Optional[datetime]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Series Recommendations Schemas
# ============================================================================


class SeriesRecommendationResponse(BaseModel):
    id: int
    user_id: int
    series_title: str
    reason: RecommendationReason
    confidence_score: float
    series_description: Optional[str]
    viewed: bool
    clicked: bool
    added_to_wishlist: bool
    started_series: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Series Notification Rules Schemas
# ============================================================================


class SeriesNotificationRuleCreate(StrictInputSchema):
    series_title: str = Field(..., min_length=1, max_length=500)
    trigger_type: NotificationTrigger
    notification_method: str = "email"  # email, sms, both
    frequency: str = "immediate"  # immediate, daily, weekly, monthly


class SeriesNotificationRuleResponse(BaseModel):
    id: int
    user_id: int
    series_title: str
    trigger_type: NotificationTrigger
    notification_method: str
    frequency: str
    is_active: bool
    last_notification_sent: Optional[datetime]
    notification_count: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class SeriesNotificationRuleUpdate(StrictInputSchema):
    is_active: Optional[bool] = None
    notification_method: Optional[str] = None
    frequency: Optional[str] = None


# ============================================================================
# Series Suggestions/Dashboard Schemas
# ============================================================================


class NextBookSuggestion(BaseModel):
    type: str = "next_in_series"
    series_title: str
    message: str
    book_number: float
    book_title: str
    books_read: int
    total_books: Optional[int]


class SeriesSuggestionsResponse(BaseModel):
    suggestions: List[NextBookSuggestion]
    count: int


class AvailableNextBook(BaseModel):
    series_title: str
    book_number: float
    book_title: str
    work_id: int
    progress: str  # e.g. "3 of 7"


class AvailableBooksResponse(BaseModel):
    available_books: List[AvailableNextBook]
    count: int


# ============================================================================
# Series Info Schemas
# ============================================================================


class SeriesInfoResponse(BaseModel):
    series_title: str
    total_books: int
    books: List[SeriesReadingOrderResponse]
    starting_points: List[SeriesReadingOrderResponse]
    patron_progress: Optional[SeriesCompletionResponse] = None
    patron_on_waitlist: bool = False


class SeriesPopularityResponse(BaseModel):
    series_title: str
    patron_followers: int
    patron_completion_count: int
    average_rating: Optional[float]
    is_trending: bool
    trend_score: Optional[float]
    last_updated: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Batch Operations Schemas
# ============================================================================


class BulkReadingHistoryCreate(StrictInputSchema):
    books: List[PatronReadingHistoryCreate] = Field(..., min_items=1, max_items=100)


class BulkReadingHistoryResponse(BaseModel):
    success_count: int
    error_count: int
    results: List[PatronReadingHistoryResponse]


# ============================================================================
# Analytics Schemas
# ============================================================================


class PatronSeriesAnalytics(BaseModel):
    total_series_started: int
    series_completed: int
    average_completion_percentage: float
    favorite_series: Optional[str]
    current_reading: List[SeriesCompletionResponse]
    trending_series: List[SeriesPopularityResponse]
    recommended_series: List[SeriesRecommendationResponse]
