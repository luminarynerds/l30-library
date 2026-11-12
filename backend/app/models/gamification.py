# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from app.models.mixins import TimestampMixin
from sqlalchemy import (Boolean, Column, Date, DateTime, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class AchievementCategory(StrEnum):
    COURSE = "course"
    EXPLORATION = "exploration"
    STREAK = "streak"
    LAB = "lab"
    SECRET = "secret"


class LabType(StrEnum):
    RAG = "rag"
    HALLUCINATION = "hallucination"
    PROMPT = "prompt"
    AGENT = "agent"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))  # lucide icon name
    xp_value = Column(Integer, default=50)
    is_secret = Column(Boolean, default=False)
    category = Column(
        String(50), index=True
    )  # course, exploration, streak, lab, secret, server_default=func.now())

    # Relationships
    user_achievements = relationship(
        "UserAchievement", back_populates="achievement", cascade="all, delete-orphan"
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    achievement_id = Column(
        Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    earned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    achievement = relationship("Achievement", back_populates="user_achievements")


class UserStats(Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    total_xp = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date)
    lessons_completed = Column(Integer, default=0)
    courses_completed = Column(Integer, default=0)
    labs_completed = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LearningLab(Base):
    __tablename__ = "learning_labs"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    instructions = Column(JSONB)  # step-by-step guide
    lab_type = Column(String(50))  # rag, hallucination, prompt, agent
    estimated_minutes = Column(Integer)
    xp_reward = Column(Integer, default=50)
    is_published = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    # Relationships
    completions = relationship(
        "LabCompletion", back_populates="lab", cascade="all, delete-orphan"
    )


class LabCompletion(Base):
    __tablename__ = "lab_completions"
    __table_args__ = (UniqueConstraint("user_id", "lab_id", name="uq_lab_completion"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lab_id = Column(
        Integer, ForeignKey("learning_labs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    results = Column(JSONB)  # store user's experiment results

    # Relationships
    lab = relationship("LearningLab", back_populates="completions")
