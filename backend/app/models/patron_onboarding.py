# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Text,
    ForeignKey,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.sql import func

from ..core.database import Base


class ReadingGoal(StrEnum):
    casual = "casual"        # 1-2 books/month
    regular = "regular"      # 3-4 books/month
    avid = "avid"            # 5+ books/month


class PatronOnboardingProgress(Base):
    __tablename__ = "patron_onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Step completion tracking
    step_welcome_completed = Column(Boolean, default=False, nullable=False)
    step_preferences_completed = Column(Boolean, default=False, nullable=False)
    step_branch_completed = Column(Boolean, default=False, nullable=False)
    step_tour_completed = Column(Boolean, default=False, nullable=False)
    step_complete_completed = Column(Boolean, default=False, nullable=False)

    # Current step (1-5) for resuming
    current_step = Column(Integer, default=1, nullable=False)

    # Reading preferences (Step 2)
    preferred_genres = Column(Text, nullable=True)  # JSON array: ["fiction","mystery",...]
    preferred_formats = Column(Text, nullable=True)  # JSON array: ["book","ebook",...]
    reading_goal = Column(
        String(50),
    )

    # Skipping
    skipped = Column(Boolean, default=False, nullable=False)
    skipped_at = Column(DateTime(timezone=True), nullable=True)

    # Completion
    completed_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class OnboardingAnalyticsEvent(Base):
    __tablename__ = "onboarding_analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    event_type = Column(String(50), nullable=False)  # step_started, step_completed, step_skipped, flow_completed, flow_abandoned
    step_number = Column(Integer, nullable=True)      # 1-5
    step_name = Column(String(50), nullable=True)     # welcome, preferences, branch, tour, complete
    event_metadata = Column(Text, nullable=True)            # JSON for extra data (time_spent, selections made, etc.)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
