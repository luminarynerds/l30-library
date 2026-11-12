# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema

_LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "My Library")


# ============ Metric / Update Schemas ============


class MetricSchema(BaseModel):
    name: str
    current: float
    target: float
    unit: Optional[str] = None


class UpdateSchema(StrictInputSchema):
    date: str
    progress: int
    note: Optional[str] = None


# ============ Goal Schemas ============


class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    target_date: Optional[datetime] = None
    progress: int = Field(default=0, ge=0, le=100)
    status: str = "not_started"
    metrics: Optional[List[dict]] = []
    owner: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)


class GoalCreate(StrictInputSchema, GoalBase):
    pass


class GoalUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_date: Optional[datetime] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = None
    metrics: Optional[List[dict]] = None
    owner: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)


class GoalResponse(GoalBase):
    id: int
    plan_id: int
    completed_date: Optional[datetime] = None
    updates: Optional[List[dict]] = []
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ProgressUpdateRequest(StrictInputSchema):
    progress: int = Field(..., ge=0, le=100)
    note: Optional[str] = None
    status: Optional[str] = None


class ReorderGoalsRequest(StrictInputSchema):
    goal_ids: List[int]


# ============ Plan Schemas ============


class PlanBase(BaseModel):
    title: str
    description: Optional[str] = None
    period_start: datetime
    period_end: datetime
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: Optional[List[str]] = []
    status: str = "draft"


class PlanCreate(StrictInputSchema, PlanBase):
    pass


class PlanUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: Optional[List[str]] = None
    status: Optional[str] = None
    next_review: Optional[datetime] = None


class PlanResponse(PlanBase):
    id: int
    last_reviewed: Optional[datetime] = None
    next_review: Optional[datetime] = None
    created_at: datetime | None = None
    goals: List[GoalResponse] = []

    class Config:
        from_attributes = True


class PlanSummary(BaseModel):
    id: int
    title: str
    status: str
    period_start: datetime
    period_end: datetime
    goal_count: int
    overall_progress: int

    class Config:
        from_attributes = True


# ============ Pagination Schemas ============


class PaginatedPlanSummary(BaseModel):
    items: List[PlanSummary]
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedGoalResponse(BaseModel):
    items: List[GoalResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedMilestoneResponse(BaseModel):
    items: List["MilestoneResponse"]
    total: int
    page: int
    per_page: int
    total_pages: int


# ============ Milestone Schemas ============


class MilestoneBase(BaseModel):
    title: str
    description: Optional[str] = None
    achieved_date: Optional[datetime] = None
    celebration_text: Optional[str] = None
    impact_story: Optional[str] = None
    photo_url: Optional[str] = None
    is_public: bool = True
    is_featured: bool = False
    display_order: Optional[int] = 0
    milestone_type: str = "achievement"
    goal_id: Optional[int] = None


class MilestoneCreate(StrictInputSchema, MilestoneBase):
    pass


class MilestoneUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    achieved_date: Optional[datetime] = None
    celebration_text: Optional[str] = None
    impact_story: Optional[str] = None
    photo_url: Optional[str] = None
    is_public: Optional[bool] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = None
    milestone_type: Optional[str] = None
    goal_id: Optional[int] = None


class MilestoneResponse(MilestoneBase):
    id: int
    plan_id: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ Comment Schemas ============


class CommentBase(BaseModel):
    content: str
    parent_id: Optional[int] = None


class CommentCreate(StrictInputSchema, CommentBase):
    pass


class CommentUpdate(StrictInputSchema):
    content: str


class CommentUserInfo(BaseModel):
    id: int
    email: str
    name: Optional[str] = None

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: int
    goal_id: int
    user_id: int
    content: str
    parent_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None
    user: Optional[CommentUserInfo] = None
    replies: List["CommentResponse"] = []

    class Config:
        from_attributes = True


# ============ Notification Schemas ============


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_type: str
    title: str
    message: Optional[str] = None
    link: Optional[str] = None
    related_goal_id: Optional[int] = None
    related_milestone_id: Optional[int] = None
    is_read: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    unread_count: int


# ============ Attachment Schemas ============


class AttachmentResponse(BaseModel):
    id: int
    goal_id: Optional[int] = None
    milestone_id: Optional[int] = None
    filename: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by_id: Optional[int] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ Analytics Schemas ============


class GoalStatusBreakdown(BaseModel):
    not_started: int = 0
    on_track: int = 0
    at_risk: int = 0
    delayed: int = 0
    completed: int = 0


class DepartmentBreakdown(BaseModel):
    department: str
    count: int
    progress: int


class CategoryBreakdown(BaseModel):
    category: str
    count: int
    progress: int


class RecentProgressUpdate(StrictInputSchema):
    goal_id: int
    goal_title: str
    progress: int
    note: Optional[str] = None
    updated_at: str
    updated_by: Optional[str] = None


class UpcomingDeadline(BaseModel):
    goal_id: int
    title: str
    target_date: datetime
    progress: int
    status: str
    days_remaining: int


class AtRiskGoal(BaseModel):
    id: int
    title: str
    status: str
    progress: int
    target_date: Optional[datetime] = None
    reason: str


class AnalyticsResponse(BaseModel):
    overall_progress: int
    goals_by_status: GoalStatusBreakdown
    goals_by_department: List[DepartmentBreakdown]
    goals_by_category: List[CategoryBreakdown]
    recent_progress_updates: List[RecentProgressUpdate]
    upcoming_deadlines: List[UpcomingDeadline]
    at_risk_goals: List[AtRiskGoal]
    total_goals: int
    plan_period: Optional[str] = None


# ============ Board Report Schema ============


class BoardReportGoal(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    progress: int
    status: str
    target_date: Optional[datetime] = None
    owner: Optional[str] = None
    recent_updates: List[dict] = []


class BoardReportResponse(BaseModel):
    generated_at: datetime
    plan_id: int
    plan_title: str
    plan_period: str
    mission: Optional[str] = None
    vision: Optional[str] = None
    overall_progress: int
    status_summary: GoalStatusBreakdown
    goals_by_category: dict
    goals: List[BoardReportGoal]
    milestones: List[dict]
    key_achievements: List[str]
    areas_of_concern: List[str]


# ============ Public Our Story Schema ============


class TimelineEvent(BaseModel):
    year: int
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class PublicGoalProgress(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    progress: int
    status: str


class PublicMilestone(BaseModel):
    id: int
    title: str
    celebration_text: Optional[str] = None
    impact_story: Optional[str] = None
    photo_url: Optional[str] = None
    achieved_date: Optional[datetime] = None
    milestone_type: str


class OurStoryResponse(BaseModel):
    has_plan: bool
    library_name: str = _LIBRARY_NAME
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: Optional[List[str]] = []
    story_intro: Optional[str] = None
    hero_image_url: Optional[str] = None
    history_timeline: List[TimelineEvent] = []
    goals: List[PublicGoalProgress] = []
    milestones: List[PublicMilestone] = []
    plan_period: Optional[str] = None


# ============ Import/Export Schema ============


class ImportPlanData(BaseModel):
    title: str
    description: Optional[str] = None
    period_start: str
    period_end: str
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: Optional[List[str]] = []
    story_intro: Optional[str] = None
    hero_image_url: Optional[str] = None
    history_timeline: Optional[List[dict]] = []
    goals: Optional[List[dict]] = []
    milestones: Optional[List[dict]] = []


# ============ Template Schemas ============


class TemplateMetricSchema(BaseModel):
    name: str
    unit: Optional[str] = None
    target_placeholder: Optional[str] = None


class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    suggested_timeline_months: Optional[int] = None
    default_metrics: List[dict] = []
    is_system_template: bool = False


class TemplateCreate(StrictInputSchema, TemplateBase):
    pass


class TemplateUpdate(StrictInputSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    suggested_timeline_months: Optional[int] = None
    default_metrics: Optional[List[dict]] = None
    is_system_template: Optional[bool] = None


class TemplateResponse(TemplateBase):
    id: int

    class Config:
        from_attributes = True


# ============ Phase 1: Initiative Schemas ============

_INITIATIVE_STATUSES = {"planning", "approved", "in_progress", "on_hold", "completed", "cancelled"}
_DECISION_TYPES = {"approval", "funding", "amendment", "closure"}


class InitiativeCreate(StrictInputSchema):
    title: str
    description: Optional[str] = None
    business_case: Optional[str] = None
    expected_outcomes: List[str] = []
    status: str = "planning"
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    estimated_budget: Optional[MoneyDecimal] = None
    assigned_leader_id: Optional[int] = None
    team_members: List[int] = []
    priority: int = Field(default=3, ge=1, le=5)
    strategic_alignment_score: Optional[int] = Field(default=None, ge=1, le=10)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _INITIATIVE_STATUSES:
            raise ValueError(f"status must be one of {_INITIATIVE_STATUSES}")
        return v


class InitiativeUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    business_case: Optional[str] = None
    expected_outcomes: Optional[List[str]] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    estimated_budget: Optional[MoneyDecimal] = None
    actual_cost: Optional[MoneyDecimal] = None
    assigned_leader_id: Optional[int] = None
    team_members: Optional[List[int]] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    strategic_alignment_score: Optional[int] = Field(default=None, ge=1, le=10)
    completion_percentage: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _INITIATIVE_STATUSES:
            raise ValueError(f"status must be one of {_INITIATIVE_STATUSES}")
        return v


class InitiativeMilestoneCreate(StrictInputSchema):
    title: str
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    dependencies: List[int] = []
    deliverables: List[str] = []


class MilestoneCompleteRequest(StrictInputSchema):
    completion_notes: Optional[str] = None


class BoardDecisionLinkCreate(StrictInputSchema):
    meeting_date: datetime
    decision_type: str
    meeting_reference: Optional[str] = None
    decision_summary: Optional[str] = None
    vote_result: Optional[str] = None
    minutes_url: Optional[str] = None
    resolution_number: Optional[str] = None

    @field_validator("decision_type")
    @classmethod
    def validate_decision_type(cls, v: str) -> str:
        if v not in _DECISION_TYPES:
            raise ValueError(f"decision_type must be one of {_DECISION_TYPES}")
        return v


class InitiativeMilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    initiative_id: int
    title: str
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    dependencies: Optional[List[int]] = []
    completed: Optional[bool] = False
    completion_notes: Optional[str] = None
    deliverables: Optional[List[str]] = []


class BoardDecisionLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    initiative_id: int
    meeting_date: datetime
    meeting_reference: Optional[str] = None
    decision_type: Optional[str] = None
    decision_summary: Optional[str] = None
    vote_result: Optional[str] = None
    minutes_url: Optional[str] = None
    resolution_number: Optional[str] = None


class InitiativeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    title: str
    description: Optional[str] = None
    business_case: Optional[str] = None
    expected_outcomes: Optional[List[str]] = []
    status: str
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    estimated_budget: Optional[MoneyDecimal] = None
    actual_cost: Optional[MoneyDecimal] = None
    assigned_leader_id: Optional[int] = None
    team_members: Optional[List[Union[int, Dict[str, Any]]]] = []  # seed rows store {id,name,role} objects
    priority: Optional[int] = None
    strategic_alignment_score: Optional[int] = None
    board_approved: Optional[bool] = None
    board_approval_date: Optional[datetime] = None
    board_meeting_reference: Optional[str] = None
    completion_percentage: Optional[int] = None
    milestones: List[InitiativeMilestoneResponse] = []
    board_decisions: List[BoardDecisionLinkResponse] = []


# ============ Phase 2: KPI Schemas ============


class KPICreate(StrictInputSchema):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: Optional[str] = None
    target_value: Optional[MoneyDecimal] = None
    baseline_value: Optional[MoneyDecimal] = None
    threshold_red: Optional[MoneyDecimal] = None
    threshold_yellow: Optional[MoneyDecimal] = None
    threshold_green: Optional[MoneyDecimal] = None
    frequency: str = "monthly"
    data_source: Optional[str] = None
    outcome_indicator_id: Optional[int] = None


class KPIUpdate(StrictInputSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: Optional[str] = None
    target_value: Optional[MoneyDecimal] = None
    baseline_value: Optional[MoneyDecimal] = None
    threshold_red: Optional[MoneyDecimal] = None
    threshold_yellow: Optional[MoneyDecimal] = None
    threshold_green: Optional[MoneyDecimal] = None
    frequency: Optional[str] = None
    data_source: Optional[str] = None
    outcome_indicator_id: Optional[int] = None
    is_active: Optional[bool] = None


class KPIValueCreate(StrictInputSchema):
    value: MoneyDecimal
    notes: Optional[str] = None
    is_estimated: bool = False


class KPIAlertResolve(StrictInputSchema):
    resolution_notes: Optional[str] = None


class KPIValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kpi_id: int
    value: MoneyDecimal
    recorded_date: Optional[datetime] = None
    notes: Optional[str] = None
    recorded_by_id: Optional[int] = None
    is_estimated: bool = False
    data_quality_score: Optional[int] = None


class KPIAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kpi_id: int
    severity: str
    message: str
    triggered_at: datetime
    threshold_violated: Optional[str] = None
    actual_value: Optional[MoneyDecimal] = None
    expected_value: Optional[MoneyDecimal] = None
    acknowledged: bool = False
    acknowledged_by_id: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolution_notes: Optional[str] = None


class KPIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: Optional[str] = None
    target_value: Optional[MoneyDecimal] = None
    baseline_value: Optional[MoneyDecimal] = None
    current_value: Optional[MoneyDecimal] = None
    threshold_red: Optional[MoneyDecimal] = None
    threshold_yellow: Optional[MoneyDecimal] = None
    threshold_green: Optional[MoneyDecimal] = None
    frequency: Optional[str] = None
    data_source: Optional[str] = None
    responsible_person_id: Optional[int] = None
    outcome_indicator_id: Optional[int] = None
    is_active: bool = True
    last_updated: Optional[datetime] = None
    trend_direction: Optional[str] = None
    variance_percentage: Optional[MoneyDecimal] = None
    values: List[KPIValueResponse] = []
    alerts: List[KPIAlertResponse] = []
