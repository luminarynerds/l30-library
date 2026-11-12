# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from typing import Optional, List, Dict
from decimal import Decimal
from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema


# ==================== LEARNER SCHEMAS ====================

class LearnerIntakeRequest(StrictInputSchema):
    user_id: int
    program_id: int
    age: Optional[int] = None
    date_of_birth: Optional[date] = None
    native_language: Optional[str] = None
    languages_spoken: Optional[str] = None
    education_background: Optional[str] = None
    employment_status: Optional[str] = None
    income_level: Optional[str] = None
    barriers_to_literacy: Optional[str] = None
    health_notes: Optional[str] = None
    accessibility_needs: Optional[str] = None
    transportation_needs: bool = False
    childcare_needed: bool = False
    referred_from: Optional[str] = None
    notes: Optional[str] = None


class LearnerResponse(BaseModel):
    id: int
    user_id: int
    program_id: int
    enrollment_date: datetime
    status: str
    age: Optional[int]
    native_language: Optional[str]
    languages_spoken: Optional[str]
    current_level: Optional[str]
    last_assessment_date: Optional[datetime]
    total_hours_attended: MoneyDecimal
    total_sessions_completed: int
    current_reading_level_wpm: Optional[int]

    class Config:
        from_attributes = True


class ProgressResponse(BaseModel):
    current_level: Optional[str]
    total_hours_attended: float
    total_sessions_completed: int
    total_assessments: int
    latest_score: Optional[float]
    improvement_percentage: float
    completed_goals: int
    active_goals: int
    last_assessment_date: Optional[str]
    reading_speed_wpm: Optional[int]


# ==================== ASSESSMENT SCHEMAS ====================

class AssessmentRequest(StrictInputSchema):
    assessor_id: int
    assessment_type: str
    score: float
    level: str
    percentage: Optional[float] = None
    reading_speed_wpm: Optional[int] = None
    comprehension_percentage: Optional[float] = None
    assessment_tool_used: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    total_points: Optional[float] = None


class AssessmentResponse(BaseModel):
    id: int
    learner_id: int
    assessment_type: str
    assessment_date: datetime
    score: float
    percentage: Optional[float]
    level: str
    reading_speed_wpm: Optional[int]


# ==================== GOAL SCHEMAS ====================

class GoalRequest(StrictInputSchema):
    goal_type: str
    goal_statement: str
    target_level: Optional[str] = None
    target_date: date
    notes: Optional[str] = None


class GoalResponse(BaseModel):
    id: int
    learner_id: int
    goal_type: str
    goal_statement: str
    target_date: date
    status: str
    completed_date: Optional[datetime]
    progress_percentage: int

    class Config:
        from_attributes = True


class MilestoneRequest(StrictInputSchema):
    goal_id: int
    description: str
    target_date: date
    notes: Optional[str] = None


class MilestoneResponse(BaseModel):
    id: int
    goal_id: int
    description: str
    target_date: date
    is_completed: bool
    completed_date: Optional[datetime]


# ==================== TUTOR SCHEMAS ====================

class TutorRegistrationRequest(StrictInputSchema):
    user_id: int
    primary_focus: Optional[str] = None
    languages_spoken: Optional[str] = None
    specializations: Optional[str] = None
    can_teach_ged: bool = False
    can_teach_esol: bool = False
    can_work_with_special_needs: bool = False
    years_experience: Optional[int] = None
    preferred_learner_level: Optional[str] = None
    can_teach_remote: bool = False
    can_teach_in_person: bool = True
    bio: Optional[str] = None


class TutorResponse(BaseModel):
    id: int
    user_id: int
    status: str
    is_active: bool
    primary_focus: Optional[str]
    languages_spoken: Optional[str]
    can_teach_ged: bool
    can_teach_esol: bool
    total_learners_taught: int
    total_hours_taught: MoneyDecimal
    average_learner_satisfaction: Optional[MoneyDecimal]
    class Config:
        from_attributes = True


class QualificationRequest(StrictInputSchema):
    tutor_id: int
    qualification_type: str
    issuer: Optional[str] = None
    issue_date: date
    expiry_date: Optional[date] = None
    credential_url: Optional[str] = None


# ==================== MATCHING SCHEMAS ====================

class MatchRequest(StrictInputSchema):
    learner_id: int
    tutor_id: int
    reason: str
    compatibility_score: float


class MatchResponse(BaseModel):
    id: int
    learner_id: int
    tutor_id: int
    match_date: datetime
    status: str
    reason: Optional[str]
    compatibility_score: Optional[MoneyDecimal]
    sessions_completed: int
    class Config:
        from_attributes = True


# ==================== SESSION SCHEMAS ====================

class SessionScheduleRequest(StrictInputSchema):
    match_id: int
    scheduled_date: date
    start_time: str  # HH:MM format
    duration_minutes: int
    location: Optional[str] = None
    is_remote: bool = False
    meeting_url: Optional[str] = None


class SessionScheduleResponse(BaseModel):
    id: int
    match_id: int
    scheduled_date: date
    start_time: str
    duration_minutes: int
    status: str
    location: Optional[str]


class SessionLogRequest(StrictInputSchema):
    match_id: int
    learner_id: int
    tutor_id: int
    session_date: date
    attendance_status: str
    actual_duration_minutes: Optional[int] = None
    learner_engagement: Optional[int] = None
    learner_focus: Optional[int] = None
    progress_observed: Optional[int] = None


class SessionNotesRequest(StrictInputSchema):
    topics_covered: Optional[str] = None
    activities_conducted: Optional[str] = None
    homework_assigned: Optional[str] = None
    learner_feedback: Optional[str] = None
    tutor_notes: Optional[str] = None


# ==================== RESOURCE SCHEMAS ====================

class ResourceRequest(StrictInputSchema):
    title: str
    description: Optional[str] = None
    isbn: Optional[str] = None
    resource_type: str
    format: str
    min_level: Optional[str] = None
    max_level: Optional[str] = None
    theme: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    resource_url: Optional[str] = None
    is_digital: bool = False


class ResourceResponse(BaseModel):
    id: int
    title: str
    resource_type: str
    format: str
    author: Optional[str]
    min_level: Optional[str]
    max_level: Optional[str]
    theme: Optional[str]
    average_rating: Optional[MoneyDecimal]
    is_featured: bool


class RecommendationResponse(BaseModel):
    resource_id: int
    title: str
    type: str
    level: Optional[str]
    theme: Optional[str]
    score: float
    reason: str
    url: Optional[str]
    is_digital: bool


class CollectionRequest(StrictInputSchema):
    name: str
    description: Optional[str] = None
    min_level: Optional[str] = None
    max_level: Optional[str] = None
    theme: Optional[str] = None
    resource_ids: Optional[List[int]] = None


class CollectionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    item_count: int
    is_featured: bool


# ==================== PARTNERSHIP SCHEMAS ====================

class PartnerOrganizationRequest(StrictInputSchema):
    organization_name: str
    organization_type: str
    description: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class ReferralRequest(StrictInputSchema):
    learner_id: int
    partner_id: int
    referral_reason: str
    referred_by_user_id: int


class ReferralResponse(BaseModel):
    id: int
    learner_id: int
    partner_id: int
    referral_date: datetime
    status: str
    ged_passed: Optional[bool]


# ==================== OUTCOME SCHEMAS ====================

class OutcomeRequest(StrictInputSchema):
    learner_id: int
    outcome_type: str
    outcome_date: date
    ged_score: Optional[int] = None
    ged_passed: Optional[bool] = None
    employment_job_title: Optional[str] = None
    employment_employer: Optional[str] = None
    education_institution: Optional[str] = None
    details: Optional[str] = None


class OutcomeResponse(BaseModel):
    id: int
    learner_id: int
    outcome_type: str
    outcome_date: date
    is_verified: bool
    details: Optional[str]


class ImpactMetricsResponse(BaseModel):
    learners_served: int
    new_learners_enrolled: int
    learners_completed_program: int
    total_sessions_completed: int
    total_tutor_hours: MoneyDecimal
    ged_completions: int
    level_advancements: int
    employment_outcomes: int
    retention_rate: Optional[MoneyDecimal]
    goal_achievement_rate: Optional[MoneyDecimal]


# ==================== CONFIDENTIALITY SCHEMAS ====================

class ConsentRequest(StrictInputSchema):
    learner_id: int
    consent_type: str
    status: str
    consent_text: Optional[str] = None
    consent_method: Optional[str] = None


class ConsentResponse(BaseModel):
    id: int
    learner_id: int
    consent_type: str
    status: str
    requested_date: datetime
    response_date: Optional[datetime]


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    learner_id: Optional[int]
    action: str
    action_date: datetime
    resource_type: Optional[str]
    field_accessed: Optional[str]
    access_granted: bool
