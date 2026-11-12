# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from enum import StrEnum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# Enums
class AchievementCategory(StrEnum):
    course = "course"
    exploration = "exploration"
    streak = "streak"
    lab = "lab"
    secret = "secret"


class LabType(StrEnum):
    rag = "rag"
    hallucination = "hallucination"
    prompt = "prompt"
    agent = "agent"


class Difficulty(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


# Achievement schemas
class AchievementBase(BaseModel):
    slug: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    xp_value: int = 50
    is_secret: bool = False
    category: Optional[str] = None


class AchievementCreate(StrictInputSchema, AchievementBase):
    pass


class AchievementResponse(AchievementBase):
    id: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class AchievementPublic(BaseModel):

    id: int
    slug: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    xp_value: int
    category: Optional[str]

    class Config:
        from_attributes = True


# User Achievement schemas
class UserAchievementBase(BaseModel):
    achievement_id: int


class UserAchievementCreate(StrictInputSchema, UserAchievementBase):
    user_id: int


class UserAchievementResponse(BaseModel):
    id: int
    user_id: int
    achievement: AchievementPublic
    earned_at: datetime

    class Config:
        from_attributes = True


class EarnedAchievement(BaseModel):

    achievement: AchievementPublic
    earned_at: datetime
    xp_earned: int
    is_new: bool = True

    class Config:
        from_attributes = True


# User Stats schemas
class UserStatsBase(BaseModel):
    total_xp: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    lessons_completed: int = 0
    courses_completed: int = 0
    labs_completed: int = 0


class UserStatsResponse(UserStatsBase):
    id: int
    user_id: int
    last_activity_date: Optional[date]
    updated_at: datetime | None = None
    level: int = 1  # computed from XP

    class Config:
        from_attributes = True


class UserStatsWithAchievements(UserStatsResponse):

    recent_achievements: List[EarnedAchievement] = []
    achievement_count: int = 0


# Leaderboard schemas
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    total_xp: int
    level: int
    courses_completed: int
    current_streak: int
    is_current_user: bool = False


class LeaderboardResponse(BaseModel):
    period: str  # weekly, monthly, all_time
    entries: List[LeaderboardEntry]
    total_users: int
    current_user_rank: Optional[int] = None


# Learning Lab schemas
class LearningLabBase(BaseModel):
    slug: str = Field(..., max_length=50)
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    instructions: Optional[dict] = None
    lab_type: Optional[str] = None
    estimated_minutes: Optional[int] = None
    xp_reward: int = 50
    sort_order: int = 0


class LearningLabCreate(StrictInputSchema, LearningLabBase):
    is_published: bool = False


class LearningLabUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    instructions: Optional[dict] = None
    lab_type: Optional[str] = None
    estimated_minutes: Optional[int] = None
    xp_reward: Optional[int] = None
    is_published: Optional[bool] = None
    sort_order: Optional[int] = None


class LearningLabResponse(LearningLabBase):
    id: int
    is_published: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class LearningLabWithProgress(LearningLabResponse):

    is_completed: bool = False
    completed_at: Optional[datetime] = None


# Lab Completion schemas
class LabCompletionBase(BaseModel):
    results: Optional[dict] = None


class LabCompletionCreate(StrictInputSchema, LabCompletionBase):
    user_id: int
    lab_id: int


class LabCompletionResponse(LabCompletionBase):
    id: int
    user_id: int
    lab_id: int
    completed_at: datetime

    class Config:
        from_attributes = True


# XP calculation helpers
def calculate_level(total_xp: int) -> int:
    # Level 1: 0-99 XP
    # Level 2: 100-249 XP
    # Level 3: 250-449 XP
    # Level N: ~50 * N^2 XP needed
    level = 1
    xp_needed = 100
    remaining = total_xp
    while remaining >= xp_needed:
        remaining -= xp_needed
        level += 1
        xp_needed = int(100 * (1.5 ** (level - 1)))
    return level


def xp_for_next_level(total_xp: int) -> tuple[int, int]:
    level = 1
    xp_needed = 100
    remaining = total_xp
    while remaining >= xp_needed:
        remaining -= xp_needed
        level += 1
        xp_needed = int(100 * (1.5 ** (level - 1)))
    return remaining, xp_needed
