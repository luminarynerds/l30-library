# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, field_validator

from ._base import StrictInputSchema


# =============================================================================
# Campaign Schemas
# =============================================================================


class EventMarketingCampaignCreate(StrictInputSchema):
    event_id: int
    campaign_name: str = Field(..., min_length=1, max_length=300)
    short_description: str | None = Field(None, max_length=500)
    marketing_copy: str | None = None
    hashtags: list[str] | None = None
    target_audience_tags: list[str] | None = None
    channels: list[str] = Field(..., min_length=1)
    distribute_at: datetime | None = None
    auto_distribute: bool | None = False
    registration_base_url: str | None = Field(None, max_length=500)

    @field_validator("channels", mode="before")
    @classmethod
    def validate_channels(cls, v: list) -> list[str]:
        from enum import Enum
        valid = {"website", "facebook", "instagram", "nextdoor",
                 "community_calendar", "email", "print_flyer"}
        result = []
        for ch in v:
            s = ch.value if isinstance(ch, Enum) else str(ch)
            if s not in valid:
                raise ValueError(f"Invalid channel: {s}. Must be one of: {valid}")
            result.append(s)
        return result


class EventMarketingCampaignUpdate(StrictInputSchema):
    campaign_name: str | None = Field(None, min_length=1, max_length=300)
    short_description: str | None = Field(None, max_length=500)
    marketing_copy: str | None = None
    hashtags: list[str] | None = None
    target_audience_tags: list[str] | None = None
    channels: list[str] | None = None
    distribute_at: datetime | None = None
    auto_distribute: bool | None = None
    registration_base_url: str | None = Field(None, max_length=500)


class EventMarketingCampaignResponse(BaseModel):
    id: int
    event_id: int
    campaign_name: str
    short_description: str | None
    marketing_copy: str | None
    hashtags: list[str] | None
    target_audience_tags: list[str] | None
    channels: dict[str, bool]
    distribute_at: datetime | None
    auto_distribute: bool | None = False
    registration_base_url: str | None
    archive_status: str
    archived_at: datetime | None
    feedback_requested_at: datetime | None
    feedback_deadline: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# =============================================================================
# Distribution Schemas
# =============================================================================


class DistributionResponse(BaseModel):
    id: int
    campaign_id: int
    channel: str
    status: str
    platform_post_id: str | None
    platform_url: str | None
    scheduled_at: datetime | None
    posted_at: datetime | None
    failed_at: datetime | None
    failure_reason: str | None
    retry_count: int
    impressions: int
    clicks: int
    likes: int
    shares: int
    comments: int
    calendar_provider: str | None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class DistributeRequest(StrictInputSchema):
    channels: list[str] | None = None  # None = all configured channels
    schedule_at: datetime | None = None  # None = post immediately


class CalendarSubmissionRequest(StrictInputSchema):
    provider: str = Field(..., max_length=50)
    additional_details: str | None = Field(None, max_length=2000)


# =============================================================================
# Flyer Schemas
# =============================================================================


class FlyerGenerateRequest(StrictInputSchema):
    size: str = Field(default="letter")
    title: str | None = Field(None, max_length=300)
    subtitle: str | None = Field(None, max_length=500)
    body_text: str | None = None
    template_name: str | None = Field(None, max_length=100)
    color_scheme: dict | None = None
    include_logo: bool = True
    include_map: bool = False

    @field_validator("size", mode="before")
    @classmethod
    def validate_size(cls, v: object) -> str:
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v)
        valid = {"letter", "half_letter", "quarter_letter", "poster", "bookmark"}
        if s not in valid:
            raise ValueError(f"Invalid size: {s}. Must be one of: {valid}")
        return s


class FlyerResponse(BaseModel):
    id: int
    campaign_id: int
    size: str
    title: str
    subtitle: str | None
    body_text: str | None
    qr_code_url: str | None
    qr_code_data: str | None
    pdf_url: str | None
    image_url: str | None
    template_name: str | None
    include_logo: bool
    include_map: bool
    print_count: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# =============================================================================
# Graphics Schemas
# =============================================================================


class GraphicGenerateRequest(StrictInputSchema):
    format: str
    title: str | None = Field(None, max_length=300)
    template_name: str | None = Field(None, max_length=100)
    color_scheme: dict | None = None
    background_image_url: str | None = Field(None, max_length=500)

    @field_validator("format", mode="before")
    @classmethod
    def validate_format(cls, v: object) -> str:
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v)
        valid = {"facebook_post", "instagram_square", "instagram_story",
                 "nextdoor_post", "email_header", "website_banner"}
        if s not in valid:
            raise ValueError(f"Invalid format: {s}. Must be one of: {valid}")
        return s


class GraphicResponse(BaseModel):
    id: int
    campaign_id: int
    format: str
    title: str
    width: int
    height: int
    image_url: str | None
    thumbnail_url: str | None
    template_name: str | None
    download_count: int
    share_count: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# =============================================================================
# Registration Source Tracking Schemas
# =============================================================================


class TrackingLinkCreateRequest(StrictInputSchema):
    source: str = Field(..., max_length=100)
    medium: str | None = Field(None, max_length=100)
    campaign_tag: str | None = Field(None, max_length=200)
    content: str | None = Field(None, max_length=200)


class TrackingLinkResponse(BaseModel):
    id: int
    campaign_id: int
    source: str
    medium: str | None
    campaign_tag: str | None
    content: str | None
    tracking_token: str
    registration_url: str
    click_count: int
    first_clicked_at: datetime | None
    converted_at: datetime | None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class RegistrationSourceStats(BaseModel):
    source: str
    medium: str | None
    total_clicks: int
    total_conversions: int
    conversion_rate: float


class CampaignAnalytics(BaseModel):
    campaign_id: int
    event_id: int
    campaign_name: str
    total_distributions: int
    successful_distributions: int
    failed_distributions: int
    total_impressions: int
    total_clicks: int
    total_registrations: int
    sources: list[RegistrationSourceStats]
    channel_metrics: list[DistributionResponse]


# =============================================================================
# Email Notification Schemas
# =============================================================================


class EventEmailRequest(StrictInputSchema):
    subject: str | None = Field(None, max_length=200)
    preview_text: str | None = Field(None, max_length=200)
    target_interests: list[int] | None = None  # Interest category IDs
    target_all_subscribers: bool = False
    send_at: datetime | None = None


class EventEmailResponse(BaseModel):
    campaign_id: int
    recipients_count: int
    scheduled_at: datetime | None
    status: str


# =============================================================================
# Post-Event / Archive / Feedback Schemas
# =============================================================================


class ArchiveRequest(StrictInputSchema):
    request_feedback: bool = True
    feedback_deadline_days: int = Field(default=14, ge=1, le=90)


class FeedbackSubmitRequest(StrictInputSchema):
    overall_rating: int = Field(..., ge=1, le=5)
    would_attend_again: bool | None = None
    would_recommend: bool | None = None
    what_liked: str | None = Field(None, max_length=2000)
    what_improve: str | None = Field(None, max_length=2000)
    suggestions: str | None = Field(None, max_length=2000)
    heard_from_source: str | None = Field(None, max_length=100)
    patron_email: EmailStr | None = None
    patron_name: str | None = Field(None, max_length=255)
    is_anonymous: bool = False


class FeedbackResponse(BaseModel):
    id: int
    campaign_id: int
    event_id: int
    overall_rating: int
    would_attend_again: bool | None
    would_recommend: bool | None
    what_liked: str | None
    what_improve: str | None
    suggestions: str | None
    heard_from_source: str | None
    is_anonymous: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class FeedbackSummary(BaseModel):
    campaign_id: int
    event_id: int
    total_responses: int
    average_rating: float | None
    would_attend_again_pct: float | None
    would_recommend_pct: float | None
    top_sources: list[dict]
    recent_comments: list[dict]


# =============================================================================
# Social Media Config Schemas
# =============================================================================


class SocialMediaConfigUpdate(StrictInputSchema):
    display_name: str | None = Field(None, max_length=200)
    api_key: str | None = None
    api_secret: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    page_id: str | None = Field(None, max_length=255)
    account_id: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    auto_post_enabled: bool | None = None
    default_hashtags: list[str] | None = None


class SocialMediaConfigResponse(BaseModel):
    id: int
    platform: str
    display_name: str | None
    page_id: str | None
    account_id: str | None
    is_active: bool
    auto_post_enabled: bool
    default_hashtags: list[str] | None
    has_api_key: bool = False
    has_access_token: bool = False
    last_post_at: datetime | None
    last_error: str | None

    class Config:
        from_attributes = True
