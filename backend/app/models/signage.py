# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum, StrEnum
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    Float,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class SignageDisplayType(StrEnum):

    wall_mounted = "wall_mounted"
    kiosk = "kiosk"
    digital_poster = "digital_poster"
    directory = "directory"
    wayfinding = "wayfinding"
    information_booth = "information_booth"
    event_board = "event_board"


class SignageDisplayStatus(StrEnum):

    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"
    offline = "offline"


class SignageContentType(StrEnum):

    announcement = "announcement"
    promotion = "promotion"
    wayfinding = "wayfinding"
    schedule = "schedule"
    hours = "hours"
    availability = "availability"
    event = "event"
    emergency = "emergency"
    wait_times = "wait_times"
    template_based = "template_based"


class SignageApprovalStatus(StrEnum):

    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    scheduled = "scheduled"
    active = "active"
    archived = "archived"


class SignageScheduleType(StrEnum):

    one_time = "one_time"
    recurring_daily = "recurring_daily"
    recurring_weekly = "recurring_weekly"
    recurring_monthly = "recurring_monthly"
    continuous = "continuous"
    event_based = "event_based"


# Association table for many-to-many relationship between SignageContent and SignageDisplay
signage_content_display = Table(
    "signage_content_display",
    Base.metadata,
    Column("content_id", Integer, ForeignKey("signage_content.id", ondelete="CASCADE")),
    Column("display_id", Integer, ForeignKey("signage_display.id", ondelete="CASCADE")),
)

# Association table for many-to-many relationship between SignageDisplay and Branch
signage_display_branch = Table(
    "signage_display_branch",
    Base.metadata,
    Column("display_id", Integer, ForeignKey("signage_display.id", ondelete="CASCADE")),
    Column(
        "branch_id", Integer, nullable=True
    ),
)


class SignageDisplay(Base, TimestampMixin):

    __tablename__ = "signage_display"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    display_type = Column(SQLEnum(SignageDisplayType, values_callable=lambda x: [e.value for e in x]), default=SignageDisplayType.wall_mounted)
    location_description = Column(String(500), nullable=False)
    location_lat = Column(Float, nullable=True)
    location_lon = Column(Float, nullable=True)
    status = Column(SQLEnum(SignageDisplayStatus, values_callable=lambda x: [e.value for e in x]), default=SignageDisplayStatus.active)

    # Display configuration
    width_pixels = Column(Integer, default=1920)
    height_pixels = Column(Integer, default=1080)
    rotation_degrees = Column(Integer, default=0)  # 0, 90, 180, 270
    brightness_level = Column(Integer, default=100)  # 0-100
    refresh_interval_seconds = Column(Integer, default=30)

    # Hardware tracking
    device_identifier = Column(String(255), unique=True, nullable=True)
    mac_address = Column(String(17), unique=True, nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    is_online = Column(Boolean, default=True)

    # Content control
    is_emergency_override_active = Column(Boolean, default=False)
    emergency_override_priority = Column(Integer, default=1000)
    default_content_id = Column(Integer, ForeignKey("signage_content.id", ondelete="SET NULL"), nullable=True)

    # Branch-specific content
    branch_id = Column(Integer, nullable=True)

    # Metadata
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    content_items = relationship(
        "SignageContent",
        secondary=signage_content_display,
        back_populates="displays",
    )
    schedules = relationship(
        "SignageSchedule", back_populates="display", cascade="all, delete-orphan"
    )
    analytics = relationship(
        "SignageAnalytics", back_populates="display", cascade="all, delete-orphan"
    )
    emergency_message = relationship(
        "SignageEmergencyMessage", back_populates="display", uselist=False
    )
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class SignageTemplate(Base, TimestampMixin):

    __tablename__ = "signage_template"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)

    # Template configuration
    html_template = Column(Text, nullable=False)
    css_styles = Column(Text, nullable=True)
    preview_image_url = Column(String(500), nullable=True)

    # Variables that can be substituted in the template
    template_variables = Column(JSON, default={})  # {"var_name": "display_name", ...}

    # Data sources for dynamic content
    data_source_config = Column(JSON, nullable=True)  # Config for live data integration

    is_public = Column(Boolean, default=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    content_items = relationship(
        "SignageContent", back_populates="template", cascade="all, delete-orphan"
    )


class SignageContent(Base, TimestampMixin):

    __tablename__ = "signage_content"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(SQLEnum(SignageContentType, values_callable=lambda x: [e.value for e in x]), default=SignageContentType.announcement)

    # Content data
    html_content = Column(Text, nullable=True)
    css_styles = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)

    # Template-based content
    template_id = Column(Integer, ForeignKey("signage_template.id", ondelete="SET NULL"), nullable=True)
    template_variables_values = Column(JSON, default={})  # Substituted variable values

    # Live data integration
    live_data_source = Column(String(100), nullable=True)  # "wait_times", "availability", etc.
    live_data_refresh_seconds = Column(Integer, default=60)

    # Display duration when shown
    display_duration_seconds = Column(Integer, default=30)
    transition_effect = Column(String(50), default="fade")  # fade, slide, zoom, etc.

    # Approval workflow
    approval_status = Column(
        SQLEnum(SignageApprovalStatus, values_callable=lambda x: [e.value for e in x]), default=SignageApprovalStatus.draft
    )
    rejection_reason = Column(Text, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Branch-specific content
    branch_id = Column(Integer, nullable=True)

    # Metadata
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    displays = relationship(
        "SignageDisplay",
        secondary=signage_content_display,
        back_populates="content_items",
    )
    schedules = relationship(
        "SignageSchedule", back_populates="content", cascade="all, delete-orphan"
    )
    template = relationship("SignageTemplate", back_populates="content_items")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    analytics = relationship(
        "SignageAnalytics", back_populates="content", cascade="all, delete-orphan"
    )


class SignageSchedule(Base):

    __tablename__ = "signage_schedule"

    id = Column(Integer, primary_key=True, index=True)
    display_id = Column(Integer, ForeignKey("signage_display.id", ondelete="CASCADE"), nullable=False)
    content_id = Column(Integer, ForeignKey("signage_content.id", ondelete="CASCADE"), nullable=False)

    # Schedule type
    schedule_type = Column(
        SQLEnum(SignageScheduleType, values_callable=lambda x: [e.value for e in x]), default=SignageScheduleType.one_time
    )

    # Timing
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True), nullable=True)
    start_time_of_day = Column(String(5), nullable=True)  # HH:MM format for recurring
    end_time_of_day = Column(String(5), nullable=True)  # HH:MM format for recurring

    # Recurrence for recurring schedules
    recurrence_days = Column(String(50), nullable=True)  # "1,3,5" for Mon,Wed,Fri
    recurrence_end_date = Column(DateTime(timezone=True), nullable=True)

    # Event-based scheduling
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    show_before_event_hours = Column(Integer, default=24)
    show_after_event_hours = Column(Integer, default=2)

    # Display order when multiple items scheduled
    display_priority = Column(Integer, default=100)  # Lower = higher priority

    # Control flags
    is_active = Column(Boolean, default=True)
    is_override = Column(Boolean, default=False)

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    display = relationship("SignageDisplay", back_populates="schedules")
    content = relationship("SignageContent", back_populates="schedules")
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class SignageEmergencyMessage(Base):

    __tablename__ = "signage_emergency_message"

    id = Column(Integer, primary_key=True, index=True)
    display_id = Column(Integer, ForeignKey("signage_display.id", ondelete="SET NULL"), nullable=True)

    message_title = Column(String(255), nullable=False)
    message_content = Column(Text, nullable=False)
    message_type = Column(String(50), default="warning")  # warning, alert, critical, info

    # Emergency configuration
    background_color = Column(String(7), default="#FF0000")  # Hex color
    text_color = Column(String(7), default="#FFFFFF")
    flash_enabled = Column(Boolean, default=False)
    flash_rate_ms = Column(Integer, default=500)
    sound_alert_enabled = Column(Boolean, default=False)

    # Activation
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime(timezone=True), default=func.now())
    deactivated_at = Column(DateTime(timezone=True), nullable=True)

    # Scope: if display_id is NULL, applies to all displays
    applies_to_all_displays = Column(Boolean, default=False)

    # Metadata
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    display = relationship("SignageDisplay", back_populates="emergency_message")
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class SignageAnalytics(Base):

    __tablename__ = "signage_analytics"

    id = Column(Integer, primary_key=True, index=True)
    display_id = Column(Integer, ForeignKey("signage_display.id", ondelete="SET NULL"), nullable=True)
    content_id = Column(Integer, ForeignKey("signage_content.id", ondelete="SET NULL"), nullable=True)

    # Metrics
    view_count = Column(Integer, default=0)
    total_display_time_seconds = Column(Integer, default=0)
    interaction_count = Column(Integer, default=0)  # Clicks, touches, etc.

    # Event tracking
    event_type = Column(String(50))  # "view_start", "view_end", "interaction"
    event_data = Column(JSON, nullable=True)

    # Time period
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date = Column(String(10), index=True)  # YYYY-MM-DD for aggregation, server_default=func.now())

    # Relationships
    display = relationship("SignageDisplay", back_populates="analytics")
    content = relationship("SignageContent", back_populates="analytics")


class SignageEventPromotion(Base):

    __tablename__ = "signage_event_promotion"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)

    # Display configuration
    auto_create_content = Column(Boolean, default=True)
    content_id = Column(Integer, ForeignKey("signage_content.id", ondelete="SET NULL"), nullable=True)

    # Scheduling
    start_showing_hours_before = Column(Integer, default=24)
    stop_showing_hours_after = Column(Integer, default=2)

    # Content template
    display_title_format = Column(String(255), nullable=True)  # Can use {event_name}, etc.
    display_template_id = Column(Integer, ForeignKey("signage_template.id", ondelete="SET NULL"), nullable=True)

    # Target displays
    target_display_types = Column(String(500), nullable=True)  # "wall_mounted,kiosk"
    target_branches = Column(String(500), nullable=True)  # Comma-separated branch IDs

    is_enabled = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    template = relationship("SignageTemplate", foreign_keys=[display_template_id])


class SignageBranchContent(Base):

    __tablename__ = "signage_branch_content"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, nullable=False)

    content_id = Column(Integer, ForeignKey("signage_content.id", ondelete="CASCADE"), nullable=False)

    # Branch-specific display rules
    is_branch_primary = Column(Boolean, default=False)  # Featured for this branch
    display_priority = Column(Integer, default=100)
    visibility_scope = Column(String(50), default="branch_only")  # "branch_only", "system"

    # Hours for display
    operating_hours_start = Column(String(5), nullable=True)  # HH:MM
    operating_hours_end = Column(String(5), nullable=True)  # HH:MM
    show_on_weekends = Column(Boolean, default=True)

    is_active = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class SignageWayfinderNode(Base):

    __tablename__ = "signage_wayfinder_node"

    id = Column(Integer, primary_key=True, index=True)
    display_id = Column(Integer, ForeignKey("signage_display.id", ondelete="SET NULL"), nullable=True)

    # Location information
    location_name = Column(String(255), nullable=False)
    location_type = Column(String(100), nullable=True)  # "floor", "section", "room", etc.
    floor_number = Column(Integer, nullable=True)
    coordinates_x = Column(Float, nullable=True)
    coordinates_y = Column(Float, nullable=True)

    # Wayfinding data
    connected_nodes = Column(String(500), nullable=True)  # Comma-separated node IDs
    directions_text = Column(Text, nullable=True)
    icon_url = Column(String(500), nullable=True)

    # Directory information
    services_available = Column(String(500), nullable=True)  # Comma-separated service names
    staff_info = Column(JSON, nullable=True)  # Staff directory for this location
    room_info = Column(JSON, nullable=True)  # Room availability, hours, etc.

    is_active = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
