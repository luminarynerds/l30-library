# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum, StrEnum
from datetime import datetime, date, time

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, String, Text, Index, Numeric, Time
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class MatchStatus(StrEnum):
    PROPOSED = "proposed"  # Pending acceptance
    ACTIVE = "active"  # Currently matched
    PAUSED = "paused"  # Temporarily paused
    ENDED = "ended"  # Match completed
    TRANSFERRED = "transferred"  # Learner moved to different tutor


class MatchReason(StrEnum):
    AVAILABILITY = "availability"
    SPECIALIZATION = "specialization"
    LOCATION = "location"
    LEARNER_PREFERENCE = "learner_preference"
    LANGUAGE = "language"
    EXPERIENCE_LEVEL = "experience_level"
    PERSONALITY_FIT = "personality_fit"


class LiteracySessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    NO_SHOW = "no_show"


class AttendanceStatus(StrEnum):
    ATTENDED = "attended"
    PARTIALLY_ATTENDED = "partially_attended"
    NOT_ATTENDED = "not_attended"
    CANCELLED_BY_TUTOR = "cancelled_by_tutor"
    CANCELLED_BY_LEARNER = "cancelled_by_learner"


class LiteracyTutorMatch(Base, TimestampMixin):
    __tablename__ = "literacy_tutor_matches"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)
    tutor_id = Column(Integer, ForeignKey("literacy_tutors.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== MATCH INFORMATION ====================
    match_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(
        String(50),
        default=MatchStatus.PROPOSED,
        nullable=False,
        index=True
    )
    reason = Column(
        String(50),
        nullable=True
    )

    # ==================== COMPATIBILITY SCORING ====================
    compatibility_score = Column(Numeric(3, 2), nullable=True)  # 0-1 scale (0-100%)
    score_breakdown = Column(Text, nullable=True)  # JSON with factor scores

    # ==================== MATCH TIMELINE ====================
    start_date = Column(Date, nullable=True)  # When match became active
    end_date = Column(Date, nullable=True)  # When match ended
    end_reason = Column(String(255), nullable=True)  # Reason for end

    # ==================== TRACKING ====================
    sessions_completed = Column(Integer, default=0, nullable=False)
    total_hours = Column(Numeric(8, 2), default=0, nullable=False)

    # ==================== NOTES ====================
    match_notes = Column(Text, nullable=True)
    learner_feedback = Column(Text, nullable=True)
    tutor_feedback = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    learner = relationship("LiteracyLearner", back_populates="matches", foreign_keys=[learner_id])
    tutor = relationship("TutorProfile", back_populates="matches", foreign_keys=[tutor_id])
    sessions = relationship(
        "LiteracySessionSchedule",
        back_populates="match",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_literacy_match_learner_status", learner_id, status),
        Index("idx_literacy_match_tutor_status", tutor_id, status),
        Index("idx_literacy_match_dates", start_date, end_date),
    )


class LiteracySessionSchedule(Base, TimestampMixin):
    __tablename__ = "literacy_session_schedules"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("literacy_tutor_matches.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== SESSION SCHEDULE ====================
    scheduled_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False)  # e.g., 60 for 1 hour
    status = Column(
        String(50),
        default=LiteracySessionStatus.SCHEDULED,
        nullable=False,
        index=True
    )

    # ==================== LOCATION ====================
    location = Column(String(255), nullable=True)  # In-person or remote
    is_remote = Column(Boolean, default=False)
    meeting_url = Column(String(500), nullable=True)  # For remote sessions

    # ==================== SESSION DETAILS ====================
    learner_confirmed = Column(Boolean, default=False)
    tutor_confirmed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    # ==================== COMPLETION ====================
    session_log_id = Column(Integer, ForeignKey("literacy_session_logs.id", ondelete="SET NULL"), nullable=True)

    # ==================== RESCHEDULING ====================
    rescheduled_from_id = Column(Integer, ForeignKey("literacy_session_schedules.id", ondelete="SET NULL"), nullable=True)
    reschedule_reason = Column(String(255), nullable=True)

    # ==================== RELATIONSHIPS ====================
    match = relationship("LiteracyTutorMatch", back_populates="sessions")
    session_log = relationship("LiteracySessionLog", backref="scheduled_session")

    __table_args__ = (
        Index("idx_literacy_session_match_date", match_id, scheduled_date),
        Index("idx_literacy_session_scheduled_date", scheduled_date, status),
    )


class LiteracySessionLog(Base, TimestampMixin):
    __tablename__ = "literacy_session_logs"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("literacy_tutor_matches.id", ondelete="CASCADE"), nullable=False, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)
    tutor_id = Column(Integer, ForeignKey("literacy_tutors.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== SESSION TIMING ====================
    session_date = Column(Date, nullable=False, index=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)  # Calculated from actual_start/end

    # ==================== ATTENDANCE ====================
    attendance_status = Column(
        String(50),
        nullable=False,
        index=True
    )
    learner_present = Column(Boolean, default=True, nullable=False)
    tutor_present = Column(Boolean, default=True, nullable=False)

    # ==================== SESSION QUALITY ====================
    learner_engagement = Column(Integer, nullable=True)  # 1-5 scale
    learner_focus = Column(Integer, nullable=True)  # 1-5 scale
    progress_observed = Column(Integer, nullable=True)  # 1-5 scale

    # ==================== LOCATION ====================
    location = Column(String(255), nullable=True)
    is_remote = Column(Boolean, default=False)

    # ==================== RELATIONSHIPS ====================
    match = relationship("LiteracyTutorMatch", backref="session_logs")
    learner = relationship("LiteracyLearner", back_populates="sessions", foreign_keys=[learner_id])
    tutor = relationship("TutorProfile", back_populates="session_logs", foreign_keys=[tutor_id])
    notes = relationship(
        "LiteracySessionNotes",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_literacy_session_log_learner_date", learner_id, session_date),
        Index("idx_literacy_session_log_tutor_date", tutor_id, session_date),
        Index("idx_literacy_session_log_match_date", match_id, session_date),
    )


class LiteracySessionNotes(Base, TimestampMixin):
    __tablename__ = "literacy_session_notes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("literacy_session_logs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # ==================== SESSION CONTENT ====================
    topics_covered = Column(Text, nullable=True)  # Comma-separated or JSON list
    activities_conducted = Column(Text, nullable=True)  # Description of activities

    # ==================== LEARNING OUTCOMES ====================
    skills_practiced = Column(Text, nullable=True)  # Skills worked on
    progress_notes = Column(Text, nullable=True)  # Observable progress

    # ==================== HOMEWORK AND NEXT STEPS ====================
    homework_assigned = Column(Text, nullable=True)
    homework_from_previous = Column(Text, nullable=True)  # Reference to previous homework
    next_lesson_focus = Column(Text, nullable=True)

    # ==================== BEHAVIORAL AND ENGAGEMENT ====================
    learner_mood = Column(String(50), nullable=True)  # engaged, distracted, tired, motivated, etc.
    learner_feedback = Column(Text, nullable=True)  # Learner's comments about session
    behavioral_notes = Column(Text, nullable=True)

    # ==================== RESOURCES USED ====================
    resources_used = Column(Text, nullable=True)  # JSON or comma-separated list of resources

    # ==================== TUTOR REFLECTION ====================
    tutor_notes = Column(Text, nullable=True)
    recommended_adjustments = Column(Text, nullable=True)  # Changes to approach
    concerns = Column(Text, nullable=True)  # Any concerns or issues

    # ==================== RELATIONSHIPS ====================
    session = relationship("LiteracySessionLog", back_populates="notes")
