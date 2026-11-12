# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema

from ..models.professional_judgment import (
    CommitteeMemberRole,
    CommitteeStatus,
    DevelopmentActivityType,
    DevelopmentCategory,
    ExceptionOutcome,
    ExpertiseLevel,
    MembershipStatus,
    OverrideCategory,
    OverrideStatus,
    PolicyFeedbackStatus,
    PolicyFeedbackType,
    ProjectStatus,
    ProfessionalRecognitionType,
)


# ============================================================================
# Policy Override Schemas
# ============================================================================

class PolicyOverrideCreate(StrictInputSchema):
    policy_area: str = Field(..., max_length=200, description="Policy area being overridden")
    standard_policy: str = Field(..., description="What the standard policy requires")
    action_taken: str = Field(..., description="What was done instead")
    reasoning: str = Field(..., description="Professional reasoning for the override")
    patron_circumstance: Optional[str] = Field(None, description="Context without PII")
    category: OverrideCategory
    financial_impact: Optional[float] = None


class PolicyOverrideUpdate(StrictInputSchema):
    outcome: Optional[ExceptionOutcome] = None
    outcome_notes: Optional[str] = None
    status: Optional[OverrideStatus] = None
    review_notes: Optional[str] = None


class PolicyOverrideResponse(BaseModel):
    id: int
    organization_id: int
    staff_id: int
    policy_area: str
    standard_policy: str
    action_taken: str
    reasoning: str
    patron_circumstance: Optional[str]
    category: OverrideCategory
    status: OverrideStatus
    outcome: Optional[ExceptionOutcome]
    outcome_notes: Optional[str]
    reviewed_by_id: Optional[int]
    review_date: Optional[datetime]
    review_notes: Optional[str]
    led_to_policy_review: bool
    policy_change_reference: Optional[str]
    financial_impact: Optional[float]
    created_at: datetime | None = None
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PolicyOverrideListResponse(BaseModel):
    id: int
    staff_id: int
    policy_area: str
    action_taken: str
    category: OverrideCategory
    status: OverrideStatus
    outcome: Optional[ExceptionOutcome]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Committee Schemas
# ============================================================================

class CommitteeCreate(StrictInputSchema):
    name: str = Field(..., max_length=200)
    purpose: str
    meeting_frequency: Optional[str] = Field(None, max_length=100)
    is_standing: bool = True
    focus_areas: list[str] = Field(default_factory=list)
    expected_outcomes: Optional[str] = None


class CommitteeUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, max_length=200)
    purpose: Optional[str] = None
    meeting_frequency: Optional[str] = Field(None, max_length=100)
    status: Optional[CommitteeStatus] = None
    focus_areas: Optional[list[str]] = None
    expected_outcomes: Optional[str] = None


class CommitteeResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    purpose: str
    meeting_frequency: Optional[str]
    status: CommitteeStatus
    is_standing: bool
    proposed_by_id: Optional[int]
    approved_date: Optional[datetime]
    focus_areas: list[str]
    expected_outcomes: Optional[str]
    created_at: datetime | None = None
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CommitteeMemberCreate(StrictInputSchema):
    committee_id: int
    role: CommitteeMemberRole = CommitteeMemberRole.member


class CommitteeMemberUpdate(StrictInputSchema):
    role: Optional[CommitteeMemberRole] = None
    status: Optional[MembershipStatus] = None
    contributions_summary: Optional[str] = None


class CommitteeMemberResponse(BaseModel):
    id: int
    committee_id: int
    staff_id: int
    role: CommitteeMemberRole
    status: MembershipStatus
    joined_date: datetime
    departed_date: Optional[datetime]
    contributions_summary: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Project Leadership Schemas
# ============================================================================

class StaffProjectCreate(StrictInputSchema):
    title: str = Field(..., max_length=300)
    description: str
    expected_impact: Optional[str] = None
    resources_needed: Optional[str] = None
    team_member_ids: list[int] = Field(default_factory=list)
    budget_requested: Optional[float] = None
    proposed_start_date: Optional[datetime] = None
    proposed_end_date: Optional[datetime] = None
    is_innovation_project: bool = False
    tags: list[str] = Field(default_factory=list)


class StaffProjectUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    team_member_ids: Optional[list[int]] = None
    budget_spent: Optional[float] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    outcomes_summary: Optional[str] = None
    lessons_learned: Optional[str] = None
    tags: Optional[list[str]] = None


class StaffProjectApproval(BaseModel):
    status: ProjectStatus
    approval_notes: Optional[str] = None
    budget_approved: Optional[float] = None


class StaffProjectResponse(BaseModel):
    id: int
    organization_id: int
    title: str
    description: str
    expected_impact: Optional[str]
    resources_needed: Optional[str]
    lead_id: int
    team_member_ids: list[int]
    status: ProjectStatus
    approved_by_id: Optional[int]
    approved_date: Optional[datetime]
    approval_notes: Optional[str]
    budget_requested: Optional[float]
    budget_approved: Optional[float]
    budget_spent: float
    proposed_start_date: Optional[datetime]
    proposed_end_date: Optional[datetime]
    actual_start_date: Optional[datetime]
    actual_end_date: Optional[datetime]
    outcomes_summary: Optional[str]
    lessons_learned: Optional[str]
    is_innovation_project: bool
    tags: list[str]
    created_at: datetime | None = None
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class StaffProjectListResponse(BaseModel):
    id: int
    title: str
    lead_id: int
    status: ProjectStatus
    is_innovation_project: bool
    tags: list[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Policy Feedback Schemas
# ============================================================================

class PolicyFeedbackCreate(StrictInputSchema):
    policy_name: str = Field(..., max_length=300)
    policy_document: Optional[str] = Field(None, max_length=500)
    feedback_type: PolicyFeedbackType
    title: str = Field(..., max_length=300)
    content: str
    proposed_change: Optional[str] = None
    rationale: Optional[str] = None
    is_anonymous: bool = False


class PolicyFeedbackReview(BaseModel):
    status: PolicyFeedbackStatus
    review_response: Optional[str] = None
    led_to_change: bool = False
    change_description: Optional[str] = None


class PolicyFeedbackResponse(BaseModel):
    id: int
    organization_id: int
    submitted_by_id: Optional[int]
    is_anonymous: bool
    policy_name: str
    policy_document: Optional[str]
    feedback_type: PolicyFeedbackType
    title: str
    content: str
    proposed_change: Optional[str]
    rationale: Optional[str]
    status: PolicyFeedbackStatus
    reviewed_by_id: Optional[int]
    review_date: Optional[datetime]
    review_response: Optional[str]
    led_to_change: bool
    change_description: Optional[str]
    created_at: datetime | None = None
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PolicyFeedbackListResponse(BaseModel):
    id: int
    policy_name: str
    feedback_type: PolicyFeedbackType
    title: str
    status: PolicyFeedbackStatus
    is_anonymous: bool
    led_to_change: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Expertise Recognition Schemas
# ============================================================================

class StaffExpertiseCreate(StrictInputSchema):
    domain: str = Field(..., max_length=200)
    description: Optional[str] = None
    level: ExpertiseLevel = ExpertiseLevel.proficient
    relevant_credentials: list[str] = Field(default_factory=list)
    years_experience: Optional[int] = None
    willing_to_mentor: bool = False
    willing_to_train: bool = False
    willing_to_consult: bool = True
    is_public: bool = True


class StaffExpertiseUpdate(StrictInputSchema):
    description: Optional[str] = None
    level: Optional[ExpertiseLevel] = None
    relevant_credentials: Optional[list[str]] = None
    years_experience: Optional[int] = None
    willing_to_mentor: Optional[bool] = None
    willing_to_train: Optional[bool] = None
    willing_to_consult: Optional[bool] = None
    is_public: Optional[bool] = None


class StaffExpertiseResponse(BaseModel):
    id: int
    staff_id: int
    organization_id: int
    domain: str
    description: Optional[str]
    level: ExpertiseLevel
    relevant_credentials: list[str]
    years_experience: Optional[int]
    willing_to_mentor: bool
    willing_to_train: bool
    willing_to_consult: bool
    is_public: bool
    created_at: datetime | None = None
    updated_at: Optional[datetime]

    # relevant_credentials is nullable in the DB but declared non-null here; rows
    # hold NULL, which from_attributes hands pydantic as an explicit None and the
    # response 500s. Coerce None back to the default.
    _NULL_DEFAULTS: ClassVar[dict] = {"relevant_credentials": []}

    @field_validator("relevant_credentials", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


class ExpertiseRecognitionCreate(StrictInputSchema):
    staff_id: int
    recognition_type: ProfessionalRecognitionType
    title: str = Field(..., max_length=300)
    description: Optional[str] = None
    expertise_domain: Optional[str] = Field(None, max_length=200)
    event_name: Optional[str] = Field(None, max_length=300)
    event_date: Optional[datetime] = None
    external_url: Optional[str] = Field(None, max_length=500)


class ExpertiseRecognitionResponse(BaseModel):
    id: int
    organization_id: int
    staff_id: int
    recognition_type: ProfessionalRecognitionType
    title: str
    description: Optional[str]
    recognized_by_id: Optional[int]
    expertise_domain: Optional[str]
    event_name: Optional[str]
    event_date: Optional[datetime]
    external_url: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Professional Development Schemas
# ============================================================================

class ProfessionalDevelopmentPlanCreate(StrictInputSchema):
    title: str = Field(..., max_length=300)
    career_goals: Optional[str] = None
    focus_areas: list[str] = Field(default_factory=list)
    planned_activities: list[str] = Field(default_factory=list)
    annual_budget: Optional[float] = None
    plan_year: int


class ProfessionalDevelopmentPlanUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=300)
    career_goals: Optional[str] = None
    focus_areas: Optional[list[str]] = None
    planned_activities: Optional[list[str]] = None
    annual_budget: Optional[float] = None
    review_notes: Optional[str] = None


class ProfessionalDevelopmentPlanResponse(BaseModel):
    id: int
    staff_id: int
    organization_id: int
    title: str
    career_goals: Optional[str]
    focus_areas: list[str]
    planned_activities: list[str]
    annual_budget: Optional[float]
    budget_used: float
    plan_year: int
    is_active: bool
    last_review_date: Optional[datetime]
    review_notes: Optional[str]
    created_at: datetime | None = None
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DevelopmentActivityCreate(StrictInputSchema):
    plan_id: int
    title: str = Field(..., max_length=300)
    description: Optional[str] = None
    activity_type: DevelopmentActivityType
    category: DevelopmentCategory
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    hours_spent: Optional[float] = None
    cost: Optional[float] = None
    provider: Optional[str] = Field(None, max_length=300)
    external_url: Optional[str] = Field(None, max_length=500)


class DevelopmentActivityUpdate(StrictInputSchema):
    completed: Optional[bool] = None
    completion_date: Optional[datetime] = None
    reflection: Optional[str] = None
    hours_spent: Optional[float] = None
    cost: Optional[float] = None
    certificate_earned: Optional[bool] = None


class DevelopmentActivityResponse(BaseModel):
    id: int
    plan_id: int
    staff_id: int
    title: str
    description: Optional[str]
    activity_type: DevelopmentActivityType
    category: DevelopmentCategory
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    hours_spent: Optional[float]
    cost: Optional[float]
    approved: bool
    completed: bool
    completion_date: Optional[datetime]
    reflection: Optional[str]
    provider: Optional[str]
    external_url: Optional[str]
    certificate_earned: bool
    created_at: datetime | None = None
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
