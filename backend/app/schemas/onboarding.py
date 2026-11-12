# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# ============================================================================
# Pre-Arrival Checklist Schemas
# ============================================================================

class PreArrivalChecklistItemCreateRequest(StrictInputSchema):

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=50)
    assigned_to_id: Optional[int] = None
    notes: Optional[str] = None


class PreArrivalChecklistItemUpdateRequest(StrictInputSchema):

    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    evidence_url: Optional[str] = None


class PreArrivalChecklistItemResponse(BaseModel):

    id: int
    title: str
    description: Optional[str]
    category: str
    status: str
    assigned_to_id: Optional[int]
    completed_at: Optional[datetime]
    completed_by_id: Optional[int]
    notes: Optional[str]
    evidence_url: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Orientation Schedule Schemas
# ============================================================================

class OrientationScheduleCreateRequest(StrictInputSchema):

    activity_title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    scheduled_time: datetime
    duration_minutes: int = Field(..., gt=0)
    location: Optional[str] = None
    facilitator_id: Optional[int] = None


class OrientationScheduleUpdateRequest(StrictInputSchema):

    activity_title: Optional[str] = None
    description: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    facilitator_id: Optional[int] = None
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class OrientationScheduleResponse(BaseModel):

    id: int
    activity_title: str
    description: Optional[str]
    scheduled_time: datetime
    duration_minutes: int
    location: Optional[str]
    facilitator_id: Optional[int]
    status: str
    completed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Training Module Schemas
# ============================================================================

class TrainingModuleCreateRequest(StrictInputSchema):

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=50)
    duration_minutes: int = Field(..., gt=0)
    is_mandatory: bool = True
    content_url: Optional[str] = None
    delivery_type: str = Field(..., min_length=1, max_length=50)
    passing_score: int = Field(default=80, ge=0, le=100)
    order: Optional[int] = None


class TrainingModuleResponse(BaseModel):

    id: int
    title: str
    description: Optional[str]
    category: str
    duration_minutes: int
    is_mandatory: bool
    content_url: Optional[str]
    delivery_type: str
    passing_score: int
    order: Optional[int]
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class TrainingModuleAssignmentCreateRequest(StrictInputSchema):

    training_module_id: int
    due_date: date


class TrainingModuleAssignmentUpdateRequest(StrictInputSchema):

    status: Optional[str] = None
    score: Optional[int] = None
    passed: Optional[bool] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    notes: Optional[str] = None


class TrainingModuleAssignmentResponse(BaseModel):

    id: int
    training_module_id: int
    training_module: Optional[TrainingModuleResponse] = None
    assigned_at: datetime
    due_date: date
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    score: Optional[int]
    passed: Optional[bool]
    verified_by_id: Optional[int]
    verified_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Policy Acknowledgment Schemas
# ============================================================================

class PolicyCreateRequest(StrictInputSchema):

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=50)
    content: str
    version: str = "1.0"
    is_mandatory: bool = True
    effective_date: date


class PolicyResponse(BaseModel):

    id: int
    title: str
    description: Optional[str]
    category: str
    content: str
    version: str
    is_mandatory: bool
    effective_date: date
    supersedes_policy_id: Optional[int]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class PolicyAcknowledgmentCreateRequest(StrictInputSchema):

    policy_id: int


class PolicyAcknowledgmentResponse(BaseModel):

    id: int
    policy_id: int
    policy: Optional[PolicyResponse] = None
    acknowledged_at: datetime
    acknowledged_by_id: int
    ip_address: Optional[str]
    notes: Optional[str]
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# System Access Schemas
# ============================================================================

class SystemAccessCreateRequest(StrictInputSchema):

    system_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    access_type: str = Field(..., min_length=1, max_length=50)
    provisioning_instructions: Optional[str] = None
    deprovisioning_instructions: Optional[str] = None


class SystemAccessResponse(BaseModel):

    id: int
    system_name: str
    description: Optional[str]
    access_type: str
    provisioning_instructions: Optional[str]
    deprovisioning_instructions: Optional[str]
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class SystemAccessProvisioningCreateRequest(StrictInputSchema):

    system_access_id: int


class SystemAccessProvisioningUpdateRequest(StrictInputSchema):

    status: Optional[str] = None
    provisioned_by_id: Optional[int] = None
    provisioned_at: Optional[datetime] = None
    credentials_provided: Optional[bool] = None
    credentials_provided_at: Optional[datetime] = None
    revoked_by_id: Optional[int] = None
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    notes: Optional[str] = None


class SystemAccessProvisioningResponse(BaseModel):

    id: int
    system_access_id: int
    system_access: Optional[SystemAccessResponse] = None
    requested_at: datetime
    requested_by_id: Optional[int]
    status: str
    provisioned_at: Optional[datetime]
    provisioned_by_id: Optional[int]
    credentials_provided: bool
    credentials_provided_at: Optional[datetime]
    revoked_at: Optional[datetime]
    revoked_by_id: Optional[int]
    revocation_reason: Optional[str]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Check-in Meeting Schemas
# ============================================================================

class CheckInMeetingCreateRequest(StrictInputSchema):

    period: str
    scheduled_date: date
    scheduled_time: Optional[datetime] = None
    scheduled_with_id: Optional[int] = None
    topics: List[str] = Field(default=[])
    preparation_notes: Optional[str] = None


class CheckInMeetingUpdateRequest(StrictInputSchema):

    scheduled_date: Optional[date] = None
    scheduled_time: Optional[datetime] = None
    scheduled_with_id: Optional[int] = None
    topics: Optional[List[str]] = None
    preparation_notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    location: Optional[str] = None
    meeting_notes: Optional[str] = None
    feedback_from_new_hire: Optional[str] = None
    feedback_from_manager: Optional[str] = None
    action_items: Optional[List[str]] = None
    next_steps: Optional[str] = None


class CheckInMeetingResponse(BaseModel):

    id: int
    period: str
    scheduled_date: date
    scheduled_time: Optional[datetime]
    scheduled_with_id: Optional[int]
    topics: List[str]
    preparation_notes: Optional[str]
    completed_at: Optional[datetime]
    location: Optional[str]
    meeting_notes: Optional[str]
    feedback_from_new_hire: Optional[str]
    feedback_from_manager: Optional[str]
    action_items: List[str]
    next_steps: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Introduction Announcement Schemas
# ============================================================================

class IntroductionAnnouncementCreateRequest(StrictInputSchema):

    title: str = Field(..., min_length=1, max_length=200)
    content: str
    announcement_type: str = Field(..., min_length=1, max_length=50)
    scheduled_date: date
    distributed_to: List[str] = Field(default=[])


class IntroductionAnnouncementUpdateRequest(StrictInputSchema):

    title: Optional[str] = None
    content: Optional[str] = None
    announcement_type: Optional[str] = None
    scheduled_date: Optional[date] = None
    distributed_to: Optional[List[str]] = None
    published_at: Optional[datetime] = None
    published_by_id: Optional[int] = None


class IntroductionAnnouncementResponse(BaseModel):

    id: int
    title: str
    content: str
    announcement_type: str
    scheduled_date: date
    distributed_to: List[str]
    created_by_id: Optional[int]
    published_at: Optional[datetime]
    published_by_id: Optional[int]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Onboarding Feedback Schemas
# ============================================================================

class OnboardingFeedbackCreateRequest(StrictInputSchema):

    feedback_type: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    is_anonymous: bool = False


class OnboardingFeedbackResponse(BaseModel):

    id: int
    feedback_type: str
    rating: Optional[int]
    comments: Optional[str]
    provided_by_id: int
    is_anonymous: bool
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Main Staff Onboarding Schemas
# ============================================================================

class StaffOnboardingCreateRequest(StrictInputSchema):

    user_id: int
    department: str = Field(..., min_length=1, max_length=100)
    position: str = Field(..., min_length=1, max_length=100)
    start_date: date
    expected_completion_date: date
    manager_id: Optional[int] = None
    buddy_mentor_id: Optional[int] = None
    probation_end_date: Optional[date] = None


class StaffOnboardingUpdateRequest(StrictInputSchema):

    status: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    expected_completion_date: Optional[date] = None
    actual_completion_date: Optional[datetime] = None
    manager_id: Optional[int] = None
    buddy_mentor_id: Optional[int] = None
    buddy_mentor_assigned_at: Optional[datetime] = None
    probation_status: Optional[str] = None
    probation_end_date: Optional[date] = None
    all_policies_acknowledged: Optional[bool] = None
    all_systems_provisioned: Optional[bool] = None
    notes: Optional[str] = None


class StaffOnboardingProgressResponse(BaseModel):

    id: int
    user_id: int
    status: str
    start_date: date
    expected_completion_date: date
    actual_completion_date: Optional[datetime]
    department: str
    position: str
    manager_id: Optional[int]
    buddy_mentor_id: Optional[int]
    buddy_mentor_assigned_at: Optional[datetime]
    probation_status: str
    probation_start_date: Optional[date]
    probation_end_date: Optional[date]
    progress_percentage: int
    all_policies_acknowledged: bool
    all_systems_provisioned: bool
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Related data
    pre_arrival_checklist: List[PreArrivalChecklistItemResponse] = []
    orientation_schedule: List[OrientationScheduleResponse] = []
    training_assignments: List[TrainingModuleAssignmentResponse] = []
    policy_acknowledgments: List[PolicyAcknowledgmentResponse] = []
    system_access_provisioning: List[SystemAccessProvisioningResponse] = []
    check_in_meetings: List[CheckInMeetingResponse] = []
    introduction_announcements: List[IntroductionAnnouncementResponse] = []
    feedback: List[OnboardingFeedbackResponse] = []

    model_config = {"from_attributes": True}


class StaffOnboardingBasicResponse(BaseModel):

    id: int
    user_id: int
    status: str
    start_date: date
    expected_completion_date: date
    actual_completion_date: Optional[datetime]
    department: str
    position: str
    manager_id: Optional[int]
    buddy_mentor_id: Optional[int]
    probation_status: str
    progress_percentage: int
    all_policies_acknowledged: bool
    all_systems_provisioned: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Dashboard and List Views
# ============================================================================

class StaffOnboardingListResponse(BaseModel):

    id: int
    user_id: int
    user_name: Optional[str] = None
    status: str
    department: str
    position: str
    start_date: date
    expected_completion_date: date
    progress_percentage: int
    manager_id: Optional[int]
    buddy_mentor_id: Optional[int]
    probation_status: str
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class OnboardingProgressSummary(BaseModel):

    total_onboarding_count: int
    in_progress_count: int
    completed_count: int
    pending_count: int
    on_hold_count: int
    average_progress_percentage: float
    overdue_count: int
    probation_failures_count: int
