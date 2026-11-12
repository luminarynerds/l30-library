# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import secrets
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


# =============================================================================
# Enums
# =============================================================================


class DistributionChannel(StrEnum):
    WEBSITE = "website"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    NEXTDOOR = "nextdoor"
    COMMUNITY_CALENDAR = "community_calendar"
    EMAIL = "email"
    PRINT_FLYER = "print_flyer"


class DistributionStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CalendarProvider(StrEnum):
    GOOGLE_CALENDAR = "google_calendar"
    LIBRARY_WEBSITE = "library_website"
    CITY_CALENDAR = "city_calendar"
    COUNTY_CALENDAR = "county_calendar"
    NEWSPAPER_CALENDAR = "newspaper_calendar"
    COMMUNITY_BOARD = "community_board"
    PATCH = "patch"
    EVENTBRITE = "eventbrite"


class FlyerSize(StrEnum):
    LETTER = "letter"          # 8.5 x 11
    HALF_LETTER = "half_letter"  # 5.5 x 8.5
    QUARTER_LETTER = "quarter_letter"  # 4.25 x 5.5
    POSTER = "poster"          # 11 x 17
    BOOKMARK = "bookmark"      # 2 x 6


class GraphicFormat(StrEnum):
    FACEBOOK_POST = "facebook_post"        # 1200x630
    INSTAGRAM_SQUARE = "instagram_square"  # 1080x1080
    INSTAGRAM_STORY = "instagram_story"    # 1080x1920
    NEXTDOOR_POST = "nextdoor_post"        # 1200x900
    EMAIL_HEADER = "email_header"          # 600x200
    WEBSITE_BANNER = "website_banner"      # 1920x600


class ArchiveStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    FEEDBACK_PENDING = "feedback_pending"
    FEEDBACK_COMPLETE = "feedback_complete"


# =============================================================================
# Event Marketing Campaign
# =============================================================================


class EventMarketingCampaign(Base, TimestampMixin):
    __tablename__ = "event_marketing_campaigns"

    id = Column(Integer, primary_key=True, index=True)

    # Link to the event
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Campaign metadata
    campaign_name = Column(String(300), nullable=False)
    short_description = Column(String(500), nullable=True)
    marketing_copy = Column(Text, nullable=True)
    hashtags = Column(ARRAY(String(100)), nullable=True, default=list)
    target_audience_tags = Column(ARRAY(String(100)), nullable=True, default=list)

    # Channels to distribute to (selected by staff)
    channels = Column(JSONB, nullable=False, default=list)

    # Scheduling
    distribute_at = Column(DateTime(timezone=True), nullable=True)
    auto_distribute = Column(Boolean, default=False)

    # Registration tracking
    registration_base_url = Column(String(500), nullable=True)

    # Post-event
    archive_status = Column(
        String(30),
        default=ArchiveStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    archived_at = Column(DateTime(timezone=True), nullable=True)
    feedback_requested_at = Column(DateTime(timezone=True), nullable=True)
    feedback_deadline = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    event = relationship("Event", backref="marketing_campaign")
    created_by = relationship("User", foreign_keys=[created_by_id])
    distributions = relationship(
        "EventDistribution",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    registration_sources = relationship(
        "EventRegistrationSource",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    flyers = relationship(
        "EventFlyer",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    graphics = relationship(
        "EventGraphic",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    feedback_responses = relationship(
        "EventFeedback",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_event_marketing_archive", "archive_status"),
    )


# =============================================================================
# Channel Distribution Tracking
# =============================================================================


class EventDistribution(Base, TimestampMixin):
    __tablename__ = "event_distributions"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("event_marketing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Channel info
    channel = Column(String(50), nullable=False)
    status = Column(
        String(30),
        default=DistributionStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Platform-specific data
    platform_post_id = Column(String(255), nullable=True)
    platform_url = Column(String(500), nullable=True)
    platform_response = Column(JSONB, nullable=True)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)

    # Retry management
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Engagement metrics (updated via webhooks or polling)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)

    # For community calendars
    calendar_provider = Column(String(50), nullable=True)
    submission_reference = Column(String(255), nullable=True)

    # Relationships
    campaign = relationship("EventMarketingCampaign", back_populates="distributions")

    __table_args__ = (
        UniqueConstraint("campaign_id", "channel", "calendar_provider",
                         name="uq_distribution_channel"),
        Index("ix_distribution_status_channel", "status", "channel"),
    )


# =============================================================================
# Social Media Platform Configuration
# =============================================================================


class SocialMediaConfig(Base, TimestampMixin):
    __tablename__ = "social_media_configs"

    id = Column(Integer, primary_key=True, index=True)

    platform = Column(String(50), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=True)

    # API credentials (encrypted at rest in production)
    api_key = Column(String(500), nullable=True)
    api_secret = Column(String(500), nullable=True)
    access_token = Column(String(1000), nullable=True)
    refresh_token = Column(String(1000), nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Platform-specific identifiers
    page_id = Column(String(255), nullable=True)
    account_id = Column(String(255), nullable=True)

    # Configuration
    is_active = Column(Boolean, default=False, nullable=False)
    auto_post_enabled = Column(Boolean, default=False, nullable=False)
    default_hashtags = Column(ARRAY(String(100)), nullable=True, default=list)

    # Last sync
    last_post_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Audit
    configured_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    configured_by = relationship("User", foreign_keys=[configured_by_id])


# =============================================================================
# Print Flyer Generation
# =============================================================================


class EventFlyer(Base, TimestampMixin):
    __tablename__ = "event_flyers"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("event_marketing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Flyer configuration
    size = Column(String(30), default=FlyerSize.LETTER.value, nullable=False)
    title = Column(String(300), nullable=False)
    subtitle = Column(String(500), nullable=True)
    body_text = Column(Text, nullable=True)

    # QR code
    qr_code_url = Column(String(500), nullable=True)
    qr_code_data = Column(Text, nullable=True)

    # Generated files
    pdf_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)

    # Template/styling
    template_name = Column(String(100), nullable=True)
    color_scheme = Column(JSONB, nullable=True)
    include_logo = Column(Boolean, default=True)
    include_map = Column(Boolean, default=False)

    # Print tracking
    print_count = Column(Integer, default=0)
    last_printed_at = Column(DateTime(timezone=True), nullable=True)

    # Audit
    generated_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    # Relationships
    campaign = relationship("EventMarketingCampaign", back_populates="flyers")


# =============================================================================
# Shareable Graphics
# =============================================================================


class EventGraphic(Base, TimestampMixin):
    __tablename__ = "event_graphics"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("event_marketing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Graphic configuration
    format = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)

    # Dimensions
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    # Generated files
    image_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)

    # Template/styling
    template_name = Column(String(100), nullable=True)
    color_scheme = Column(JSONB, nullable=True)
    background_image_url = Column(String(500), nullable=True)

    # Usage tracking
    download_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)

    # Relationships
    campaign = relationship("EventMarketingCampaign", back_populates="graphics")


# =============================================================================
# Registration Source Tracking
# =============================================================================


class EventRegistrationSource(Base, TimestampMixin):
    __tablename__ = "event_registration_sources"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("event_marketing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    registration_id = Column(
        Integer,
        ForeignKey("event_registrations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # UTM-style tracking
    source = Column(String(100), nullable=False)       # facebook, instagram, flyer, email
    medium = Column(String(100), nullable=True)        # social, print, email, qr_code
    campaign_tag = Column(String(200), nullable=True)  # specific campaign identifier
    content = Column(String(200), nullable=True)       # ad variant, A/B test

    # Tracking token (appended to registration URLs)
    tracking_token = Column(
        String(64), nullable=False, unique=True, index=True
    )

    # Click/conversion tracking
    click_count = Column(Integer, default=0)
    first_clicked_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)

    # Visitor info (anonymized)
    referrer_url = Column(String(500), nullable=True)

    # Relationships
    campaign = relationship(
        "EventMarketingCampaign", back_populates="registration_sources"
    )
    registration = relationship("EventRegistration")

    __table_args__ = (
        Index("ix_reg_source_campaign_source", "campaign_id", "source"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.tracking_token:
            self.tracking_token = secrets.token_urlsafe(24)


# =============================================================================
# Post-Event Feedback
# =============================================================================


class EventFeedback(Base, TimestampMixin):
    __tablename__ = "event_feedback"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("event_marketing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Respondent (optional - can be anonymous)
    patron_email = Column(String(255), nullable=True, index=True)
    patron_name = Column(String(255), nullable=True)
    is_anonymous = Column(Boolean, default=False)

    # Feedback content
    overall_rating = Column(Integer, nullable=False)  # 1-5
    would_attend_again = Column(Boolean, nullable=True)
    would_recommend = Column(Boolean, nullable=True)

    # Structured feedback
    what_liked = Column(Text, nullable=True)
    what_improve = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)

    # How they heard about the event
    heard_from_source = Column(String(100), nullable=True)

    # Token for anonymous submission
    feedback_token = Column(
        String(64), nullable=True, unique=True, index=True
    )

    # Relationships
    campaign = relationship(
        "EventMarketingCampaign", back_populates="feedback_responses"
    )

    __table_args__ = (
        Index("ix_event_feedback_event", "event_id"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.feedback_token:
            self.feedback_token = secrets.token_urlsafe(24)
