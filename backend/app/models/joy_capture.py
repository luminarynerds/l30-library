# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from app.models.mixins import TimestampMixin
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship
from ..core.database import Base

class JoyVisibility(StrEnum):
    TEAM = "team"
    ORGANIZATION = "organization"
    PUBLIC = "public"

class MoodType(StrEnum):
    DELIGHTFUL = "delightful"
    GRATEFUL = "grateful"
    INSPIRING = "inspiring"
    FUNNY = "funny"
    HEARTWARMING = "heartwarming"


class JoyMomentType(StrEnum):
    BRIGHT_SPOT = "bright_spot"
    FUNNY_MOMENT = "funny_moment"
    KID_DRAWING = "kid_drawing"
    COMMUNITY_LOVE_LETTER = "community_love_letter"
    STAFF_MEMORY = "staff_memory"

class BrightSpot(Base):
    __tablename__ = "bright_spots"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    moment_type = Column(SQLEnum(JoyMomentType, values_callable=lambda x: [e.value for e in x]), default=JoyMomentType.BRIGHT_SPOT, index=True)
    mood = Column(SQLEnum(MoodType, values_callable=lambda x: [e.value for e in x]), default=MoodType.DELIGHTFUL)
    visibility = Column(SQLEnum(JoyVisibility, values_callable=lambda x: [e.value for e in x]), default=JoyVisibility.TEAM)
    is_featured = Column(Boolean, default=False, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # Note: organization_id FK exists but no Organization model defined yet
    user = relationship("User")

class PatronThankYou(Base):
    __tablename__ = "patron_thank_yous"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patron_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    can_share = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # Note: organization_id FK exists but no Organization model defined yet
    staff = relationship("User")

class JoyJarEntry(Base):
    __tablename__ = "joy_jar_entries"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    entry_text = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False)
    mood = Column(SQLEnum(MoodType, values_callable=lambda x: [e.value for e in x]), default=MoodType.GRATEFUL)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # Note: organization_id FK exists but no Organization model defined yet
    user = relationship("User")
