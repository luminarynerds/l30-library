# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class SharePlatform(StrEnum):
    facebook = "facebook"
    twitter = "twitter"
    linkedin = "linkedin"
    reddit = "reddit"
    email = "email"
    copy_link = "copy_link"
    whatsapp = "whatsapp"
    telegram = "telegram"


class ShareableResourceType(StrEnum):
    book = "book"
    event = "event"
    reading_list = "reading_list"
    author_profile = "author_profile"
    staff_pick = "staff_pick"


class ShareEvent(Base):

    __tablename__ = "share_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Resource being shared
    resource_type = Column(
        SQLEnum(ShareableResourceType, name="shareable_resource_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    resource_id = Column(Integer, nullable=False, index=True)

    # Platform shared to
    platform = Column(
        SQLEnum(SharePlatform, name="shareplatform", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Optional tracking details
    is_public_resource = Column(Boolean, default=True)  # Was the shared resource public?
    share_url = Column(String(500), nullable=True)  # URL that was shared
    referrer = Column(String(500), nullable=True)  # Where the share originated
    shared_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", backref="share_events")


class ShareStatistics(Base):

    __tablename__ = "share_statistics"

    id = Column(Integer, primary_key=True, index=True)

    # Resource identification
    resource_type = Column(
        SQLEnum(ShareableResourceType, name="shareable_resource_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    resource_id = Column(Integer, nullable=False, index=True)

    # Share counts by platform
    total_shares = Column(Integer, default=0)
    facebook_shares = Column(Integer, default=0)
    twitter_shares = Column(Integer, default=0)
    linkedin_shares = Column(Integer, default=0)
    reddit_shares = Column(Integer, default=0)
    email_shares = Column(Integer, default=0)
    copy_link_shares = Column(Integer, default=0)
    whatsapp_shares = Column(Integer, default=0)
    telegram_shares = Column(Integer, default=0)

    # Timestamps
    last_shared_at = Column(DateTime(timezone=True), nullable=True)


class SocialSharingConfig(Base, TimestampMixin):

    __tablename__ = "social_sharing_config"

    id = Column(Integer, primary_key=True, index=True)

    # General settings
    sharing_enabled = Column(Boolean, default=True, nullable=False)
    share_buttons_enabled = Column(Boolean, default=True, nullable=False)
    share_counts_enabled = Column(Boolean, default=True, nullable=False)
    default_message_template = Column(Text, nullable=True)

    # Platform settings
    twitter_handle = Column(String(100), nullable=True)
    facebook_app_id = Column(String(100), nullable=True)
    linkedin_enabled = Column(Boolean, default=True, nullable=False)
    pinterest_enabled = Column(Boolean, default=False, nullable=False)
    email_enabled = Column(Boolean, default=True, nullable=False)
    copy_link_enabled = Column(Boolean, default=True, nullable=False)

    # Open Graph defaults
    og_default_image = Column(String(500), nullable=True)

    # UTM tracking
    utm_tracking_enabled = Column(Boolean, default=False, nullable=False)
    utm_source = Column(String(200), nullable=True)
    utm_medium = Column(String(200), nullable=True)

    # Admin who last updated
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = relationship("User", foreign_keys=[updated_by_id])
