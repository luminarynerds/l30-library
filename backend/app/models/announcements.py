# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class AnnouncementPriority(StrEnum):

    LOW = "low"
    NORMAL = "normal"
    IMPORTANT = "important"
    HIGH = "high"
    URGENT = "urgent"


class AnnouncementStatus(StrEnum):

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Announcement(Base):

    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(String(500), nullable=True)

    # Category and priority
    category = Column(String(50), default="general", nullable=False)
    priority = Column(
        SQLEnum(
            AnnouncementPriority,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=AnnouncementPriority.NORMAL,
        nullable=False,
    )

    # Status workflow
    status = Column(
        SQLEnum(
            AnnouncementStatus,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=AnnouncementStatus.DRAFT,
        nullable=False,
    )
    active = Column(Boolean, default=True, nullable=False)
    pinned = Column(Boolean, default=False, nullable=False)

    # Scheduling
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Display options
    show_on_homepage = Column(Boolean, default=True, nullable=False)
    show_banner = Column(
        Boolean, default=False, nullable=False
    )  # Top banner for urgent
    dismissible = Column(Boolean, default=True, nullable=False)

    # Targeting (optional)
    target_audience = Column(String(50), nullable=True)  # all, staff, patrons, students

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_name = Column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<Announcement(title='{self.title}', priority='{self.priority}', status='{self.status}')>"

    def is_currently_active(self) -> bool:
        if self.status != AnnouncementStatus.PUBLISHED:
            return False
        if not self.active:
            return False

        now = datetime.now(timezone.utc)

        # Check start date
        if self.starts_at:
            starts_at_aware = self.starts_at if self.starts_at.tzinfo else self.starts_at.replace(tzinfo=timezone.utc)
            if now < starts_at_aware:
                return False

        # Check end date
        if self.ends_at:
            ends_at_aware = self.ends_at if self.ends_at.tzinfo else self.ends_at.replace(tzinfo=timezone.utc)
            if now > ends_at_aware:
                return False

        # Check expiration
        if self.expires_at:
            expires_at_aware = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
            if now > expires_at_aware:
                return False

        return True


# Alias for backward compatibility
AnnouncementBanner = Announcement
