# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..core.database import Base


class AntidoteType(StrEnum):
    DONE_IS_BETTER = "done_is_better"  # Done is better than perfect
    TIME_LIMIT = "time_limit"  # Time limits on tasks
    MOVE_ON_PROMPT = "move_on_prompt"  # Move on when stuck
    EIGHTY_TWENTY = "eighty_twenty"  # 80/20 prioritization
    IMPERFECT_ACTION = "imperfect_action"  # Imperfect action over inaction
    LEARN_ENOUGH = "learn_enough"  # Learning from good-enough
    CELEBRATE_PROGRESS = "celebrate_progress"  # Celebrate progress not perfection
    MANAGER_BALANCE = "manager_balance"  # Manager modeling balance
    HUMAN_GRACE = "human_grace"  # Grace for human limitations
    PERMISSION_HUMAN = "permission_human"  # Permission to be human


class SessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    NO_SHOW = "no_show"


class AdoptionStatus(StrEnum):
    DISCOVERING = "discovering"
    TRYING = "trying"
    ADOPTED = "adopted"


class PerfectionismAntidote(Base):
    __tablename__ = "perfectionism_antidotes"

    id = Column(Integer, primary_key=True)
    antidote_type = Column(SQLEnum(AntidoteType, values_callable=lambda x: [e.value for e in x]), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    reminder_text = Column(String(500), nullable=False)
    advice = Column(Text, nullable=True)
    example_scenario = Column(Text, nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)  # For time-limit antidote
    priority_score = Column(Float, default=0.5)  # 0-1 scale
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    icon_name = Column(String(50), nullable=True)
    color_code = Column(String(7), default="#3B82F6")  # Tailwind color hex

    # Relationships
    user_antidotes = relationship("UserAntidote", back_populates="antidote", cascade="all, delete-orphan")
    sessions = relationship("CoachingSession", back_populates="antidote", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserAntidote(Base):
    __tablename__ = "user_antidotes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    antidote_id = Column(Integer, ForeignKey("perfectionism_antidotes.id", ondelete="CASCADE"), nullable=False)

    # Progress tracking
    reminder_count = Column(Integer, default=0)  # Times user received reminder
    adoption_status = Column(SQLEnum(AdoptionStatus, values_callable=lambda x: [e.value for e in x]), default=AdoptionStatus.DISCOVERING)
    confidence_level = Column(Float, default=0.0)  # 0-1: how confident they are
    last_reminder_at = Column(DateTime, nullable=True)

    # Engagement
    times_acknowledged = Column(Integer, default=0)
    times_applied = Column(Integer, default=0)
    is_favorite = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    # Relationships
    antidote = relationship("PerfectionismAntidote", back_populates="user_antidotes")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CoachingSession(Base):
    __tablename__ = "coaching_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    antidote_id = Column(Integer, ForeignKey("perfectionism_antidotes.id", ondelete="SET NULL"), nullable=True)
    coach_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Session content
    topic = Column(String(300), nullable=False)
    challenge_description = Column(Text, nullable=False)
    coaching_notes = Column(Text, nullable=True)
    action_plan = Column(Text, nullable=True)

    # Progress
    session_status = Column(SQLEnum(SessionStatus, values_callable=lambda x: [e.value for e in x]), default=SessionStatus.SCHEDULED)
    progress_made = Column(String(500), nullable=True)
    confidence_increase = Column(Float, default=0.0)  # Change in confidence 0-1

    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Relationships
    antidote = relationship("PerfectionismAntidote", back_populates="sessions")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProgressMilestone(Base):
    __tablename__ = "perfectionism_milestones"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Milestone info
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    milestone_type = Column(String(50), nullable=False)  # launched_project, completed_task, shared_work, etc.

    # Evidence and reflection
    what_happened = Column(Text, nullable=False)
    what_learned = Column(Text, nullable=True)
    how_felt = Column(String(500), nullable=True)

    # Status
    is_celebrated = Column(Boolean, default=False)
    celebration_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DailyReminder(Base):
    __tablename__ = "daily_reminders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    antidote_id = Column(Integer, ForeignKey("perfectionism_antidotes.id", ondelete="CASCADE"), nullable=False)

    reminder_date = Column(DateTime, default=datetime.utcnow)
    reminder_text = Column(String(500), nullable=False)
    was_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    user_reflection = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class ManagerCoachingModel(Base):
    __tablename__ = "manager_coaching_models"

    id = Column(Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # What the manager models
    personal_commitment = Column(Text, nullable=True)  # Manager's commitment to balance
    visible_boundaries = Column(String(500), nullable=True)  # Work/life boundaries shown
    mistake_sharing = Column(Text, nullable=True)  # How manager shares learning from mistakes
    grace_examples = Column(Text, nullable=True)  # Examples of showing grace

    # Team impact
    team_feedback = Column(Text, nullable=True)
    observed_improvements = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
