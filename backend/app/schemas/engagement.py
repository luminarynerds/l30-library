# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from enum import StrEnum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._base import StrictInputSchema


class SurveyPlacement(StrEnum):
    entry_pulse = "entry_pulse"
    embedded_lesson = "embedded_lesson"
    pre_certificate = "pre_certificate"
    longitudinal = "longitudinal"


class SurveyQuestionType(StrEnum):
    likert = "likert"
    single_choice = "single_choice"
    multi_choice = "multi_choice"
    free_text = "free_text"
    scenario = "scenario"


class SurveyResponseStatus(StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"
    expired = "expired"


# ---- Question ----

class SurveyQuestionBase(BaseModel):
    question_text: str
    question_type: SurveyQuestionType
    options: Optional[Any] = None
    is_optional: bool = False
    is_demographic: bool = False
    sort_order: int = 0
    branching_rules: Optional[List[Any]] = None


class SurveyQuestionCreate(StrictInputSchema, SurveyQuestionBase):
    pass


class SurveyQuestionResponse(SurveyQuestionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    survey_id: int


# ---- Survey ----

class SurveyBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    placement: SurveyPlacement
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    blocks_progression: bool = False
    triggers_remediation: bool = True
    is_anonymous: bool = False
    estimated_minutes: Optional[int] = None
    trigger_offset_days: Optional[int] = None
    consent_copy: Optional[str] = None


class SurveyCreate(StrictInputSchema, SurveyBase):
    questions: List[SurveyQuestionCreate] = []


class SurveyUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    blocks_progression: Optional[bool] = None
    triggers_remediation: Optional[bool] = None
    is_anonymous: Optional[bool] = None
    estimated_minutes: Optional[int] = None
    trigger_offset_days: Optional[int] = None
    consent_copy: Optional[str] = None


class SurveyResponse_(SurveyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_published: bool
    questions: List[SurveyQuestionResponse] = []


class SurveyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    placement: SurveyPlacement
    course_id: Optional[int]
    is_published: bool
    estimated_minutes: Optional[int]


# ---- Response submission ----

class SurveyAnswer(BaseModel):
    question_id: int
    value: Any  # int for Likert, str/list for choice, str for free-text


class SurveyResponseSubmit(StrictInputSchema):
    answers: List[SurveyAnswer]


class SurveyOutcomePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    outcome_type: str
    target: Optional[str] = None
    status: str


class SurveyResponseResult(BaseModel):
    response_id: int
    status: SurveyResponseStatus
    score: Optional[int] = None
    derived_track: Optional[str] = None
    blocked: bool = False
    outcomes: List[SurveyOutcomePublic] = []
    next_url: Optional[str] = None


# ---- Pending surveys (user dashboard widget) ----

class PendingSurvey(BaseModel):
    survey_id: int
    title: str
    placement: SurveyPlacement
    course_id: Optional[int] = None
    estimated_minutes: Optional[int] = None
    consent_copy: Optional[str] = None
    delivery_token: Optional[str] = None  # only for longitudinal magic-link surveys


# ---- Demographics ----

class UserDemographicsUpdate(StrictInputSchema):
    primary_language: Optional[str] = Field(None, max_length=10)
    is_native_english: Optional[bool] = None
    age_range: Optional[str] = Field(None, max_length=10)
    underserved_self_id: Optional[bool] = None
    zip_code: Optional[str] = Field(None, max_length=10)


class UserDemographicsResponse(UserDemographicsUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int


# ---- Badges (read-only views over learning_badges / learning_user_badges) ----

class BadgeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    icon_url: Optional[str] = None


class UserBadgeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    badge: BadgeView
    earned_at: datetime
    earned_for: Optional[str] = None
