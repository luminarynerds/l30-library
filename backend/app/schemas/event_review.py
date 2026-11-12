# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# ──────────────────────────────────────────────────────────────────────────────
# Validation-Sync Report
# Frontend files that consume this schema's constraints:
#   - frontend/src/components/EventReviewForm.tsx       (currently disabled; review form)
#   - frontend/src/pages/StaffReviewResponsesPage.tsx   (event review display/moderation)
# ──────────────────────────────────────────────────────────────────────────────

from datetime import datetime

from pydantic import BaseModel, Field, EmailStr, field_validator

from ._base import StrictInputSchema


class EventReviewCreate(StrictInputSchema):

    patron_email: EmailStr = Field(..., description="Email used when registering for the event")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    comment: str | None = Field(None, min_length=10, max_length=2000, description="Review comment (10-2000 chars if provided)")

    @field_validator("comment", mode="before")
    @classmethod
    def validate_comment(cls, v: str | None) -> str | None:
        if v and not v.strip():
            raise ValueError("Comment cannot be empty or whitespace only")
        return v


class EventReviewResponse(BaseModel):

    id: int
    event_id: int
    patron_email: str | None = None
    rating: int
    comment: str | None
    moderation_status: str
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class EventReviewDetailResponse(BaseModel):

    id: int
    event_id: int
    patron_email: str
    rating: int
    comment: str | None
    moderation_status: str
    moderated_by: str | None
    moderated_at: datetime | None
    moderation_reason: str | None
    is_removed: int
    removal_reason: str | None
    removed_by: str | None
    removed_at: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ReviewModerationAction(StrictInputSchema):

    action: str = Field(..., description="Action to take: 'approve', 'reject', or 'remove'")
    reason: str | None = Field(None, max_length=1000, description="Reason for the action")


class ReviewModerationQueue(BaseModel):

    id: int
    event_id: int
    event_title: str
    patron_email: str
    rating: int
    comment: str | None
    created_at: datetime | None = None
    moderation_status: str

    class Config:
        from_attributes = True


class EventReviewSummary(BaseModel):

    event_id: int
    average_rating: float | None
    total_reviews: int
    rating_distribution: dict[int, int]  # {1: count, 2: count, ...}


# ============================================================================
# Content Flagging Schemas
# ============================================================================

class ContentFlagAnalysisDetail(BaseModel):

    id: int
    flag_category: str
    category_score: int
    evidence: dict | None

    class Config:
        from_attributes = True


class ContentFlagListResponse(BaseModel):

    id: int
    review_id: int
    review_type: str
    flag_type: str
    confidence_score: int
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ContentFlagReviewContent(BaseModel):

    review_id: int
    review_type: str
    comment: str | None
    rating: int | None
    patron_email: str | None
    moderation_status: str | None
    is_removed: int | None
    event_id: int | None = None
    event_title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ContentFlagResponse(BaseModel):

    id: int
    review_id: int
    review_type: str
    flag_type: str
    confidence_score: int
    analysis_details: dict | None
    status: str
    resolved_by: str | None
    resolved_at: datetime | None
    resolution_notes: str | None
    is_correct_flag: bool | None
    staff_feedback: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    review_content: ContentFlagReviewContent | None = None

    class Config:
        from_attributes = True


class ContentFlagFeedbackRequest(StrictInputSchema):

    status: str = Field(
        ...,
        description="Status: 'resolved', 'false_positive', or 'false_negative'"
    )
    is_correct_flag: bool | None = Field(
        None,
        description="Whether the flag was correct"
    )
    resolution_notes: str | None = Field(
        None,
        max_length=1000,
        description="Notes on how the flag was resolved"
    )
    staff_feedback: str | None = Field(
        None,
        max_length=2000,
        description="Feedback for AI model improvement"
    )


class ContentFlagStatisticsResponse(BaseModel):

    total_flags: int
    avg_confidence: float
    high_confidence_flags: int
    false_positives: int
    false_negatives: int
    false_positive_rate: float

    class Config:
        from_attributes = True


class EventReviewEditRequest(StrictInputSchema):

    comment: str = Field(..., max_length=2000, description="Updated review comment")
    reason: str | None = Field(None, max_length=1000, description="Reason for edit")
