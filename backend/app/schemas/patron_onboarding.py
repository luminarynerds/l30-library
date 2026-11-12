# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from ._base import StrictInputSchema


class PatronPreferencesUpdate(StrictInputSchema):
    preferred_genres: List[str] = Field(..., min_length=3, description="At least 3 genres")
    preferred_formats: List[str] = Field(..., min_length=1, description="At least 1 format")
    reading_goal: str = Field(..., pattern="^(casual|regular|avid)$")


class PatronHomeBranchUpdate(StrictInputSchema):
    branch_id: int


class OnboardingStepUpdate(StrictInputSchema):
    step: int = Field(..., ge=1, le=5)


class OnboardingSkipRequest(StrictInputSchema):
    current_step: Optional[int] = None


class OnboardingAnalyticsEventCreate(StrictInputSchema):
    event_type: str = Field(..., max_length=50)
    step_number: Optional[int] = Field(None, ge=1, le=5)
    step_name: Optional[str] = Field(None, max_length=50)
    metadata: Optional[dict] = None


class PatronOnboardingStatusResponse(BaseModel):
    patron_id: int
    current_step: int
    step_welcome_completed: bool
    step_preferences_completed: bool
    step_branch_completed: bool
    step_tour_completed: bool
    step_complete_completed: bool
    preferred_genres: Optional[List[str]] = None
    preferred_formats: Optional[List[str]] = None
    reading_goal: Optional[str] = None
    skipped: bool
    completed_at: Optional[datetime] = None
    started_at: datetime
    home_branch_id: Optional[int] = None
    home_branch_name: Optional[str] = None

    model_config = {"from_attributes": True}


class OnboardingAnalyticsSummary(BaseModel):
    total_started: int
    total_completed: int
    total_skipped: int
    completion_rate: float
    step_completion_rates: dict  # step_name -> completion percentage
    average_time_to_complete_seconds: Optional[float] = None
    drop_off_by_step: dict  # step_name -> count of users who dropped off
