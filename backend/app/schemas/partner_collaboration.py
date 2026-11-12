# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from ._base import StrictInputSchema

from ..models.partner_collaboration import (
    SharedEventType, SharedEventStatus,
    ResourceRequestType, ResourceRequestStatus,
    CoSponsoredProgramStatus,
    MeetingType,
    MOUStatus,
    GrantOpportunityStatus,
    ImpactMetricType,
    RecognitionType
)


# ============================================================================
# Shared Event Schemas
# ============================================================================

class SharedEventCreate(StrictInputSchema):
    title: str = Field(..., max_length=300, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    event_type: str = Field(..., description="Type of event")
    event_date: str = Field(..., description="Event date (ISO format)")
    start_time: Optional[str] = Field(None, description="Start time HH:MM")
    end_time: Optional[str] = Field(None, description="End time HH:MM")
    location: Optional[str] = Field(None, max_length=500, description="Physical location")
    virtual_meeting_url: Optional[str] = Field(None, max_length=500, description="Virtual meeting link")
    is_public: bool = Field(True, description="Visible to public")
    organizing_partner_id: int = Field(..., description="Partner organizing the event")
    co_organizing_partner_ids: Optional[List[int]] = Field(default=[], description="Co-organizing partners")
    expected_attendance: Optional[int] = Field(None, description="Expected attendees")
    target_audience: Optional[str] = Field(None, max_length=200, description="Target audience")
    materials_needed: Optional[List[str]] = Field(default=[], description="Materials needed")
    budget: Optional[float] = Field(None, description="Event budget")


class SharedEventUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    actual_attendance: Optional[int] = None
    outcomes: Optional[str] = None
    lessons_learned: Optional[str] = None


class SharedEventResponse(BaseModel):
    id: int
    title: str
    event_type: SharedEventType
    event_date: date
    start_time: Optional[str]
    end_time: Optional[str]
    status: SharedEventStatus
    is_public: bool
    location: Optional[str]
    virtual_meeting_url: Optional[str]
    organizing_partner_id: int
    co_organizing_partner_ids: List[int]
    expected_attendance: Optional[int]
    actual_attendance: Optional[int]
    outcomes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Resource Sharing Request Schemas
# ============================================================================

class ResourceSharingRequestCreate(StrictInputSchema):
    title: str = Field(..., max_length=300)
    description: str = Field(...)
    resource_type: str = Field(..., description="Type of resource")
    requesting_partner_id: int
    start_date: str = Field(..., description="ISO format date")
    end_date: Optional[str] = None
    quantity: Optional[int] = None
    unit: Optional[str] = None
    specific_items: Optional[List[str]] = Field(default=[], description="Detailed items list")
    cost_estimate: Optional[float] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class ResourceSharingRequestUpdate(StrictInputSchema):
    status: Optional[str] = None
    providing_partner_id: Optional[int] = None
    delivery_date: Optional[str] = None
    return_date: Optional[str] = None
    approval_notes: Optional[str] = None
    completion_notes: Optional[str] = None
    satisfaction_rating: Optional[int] = None


class ResourceSharingRequestResponse(BaseModel):
    id: int
    title: str
    description: str
    resource_type: ResourceRequestType
    requesting_partner_id: int
    providing_partner_id: Optional[int]
    status: ResourceRequestStatus
    start_date: date
    end_date: Optional[date]
    quantity: Optional[int]
    cost_estimate: Optional[float]
    approved_at: Optional[datetime]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Co-Sponsored Program Schemas
# ============================================================================

class ProgramSessionCreate(StrictInputSchema):
    title: str = Field(..., max_length=300)
    session_number: Optional[int] = None
    session_date: str = Field(...)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    format: Optional[str] = None  # in-person, virtual, hybrid
    virtual_url: Optional[str] = None
    expected_attendance: Optional[int] = None


class CoSponsoredProgramCreate(StrictInputSchema):
    name: str = Field(..., max_length=300)
    description: Optional[str] = None
    program_type: Optional[str] = None
    lead_partner_id: int
    co_sponsor_partner_ids: Optional[List[int]] = Field(default=[])
    start_date: str
    end_date: Optional[str] = None
    target_audience: Optional[str] = None
    goals: Optional[List[str]] = Field(default=[])
    expected_reach: Optional[int] = None
    total_budget: Optional[float] = None
    library_contribution: Optional[float] = None


class CoSponsoredProgramResponse(BaseModel):
    id: int
    name: str
    program_type: Optional[str]
    status: CoSponsoredProgramStatus
    lead_partner_id: int
    co_sponsor_partner_ids: List[int]
    start_date: date
    end_date: Optional[date]
    target_audience: Optional[str]
    total_budget: Optional[float]
    participants: Optional[int]
    completion_rate: Optional[float]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Contact Directory Schemas
# ============================================================================

class PartnerContactCreate(StrictInputSchema):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    title: Optional[str] = Field(None, max_length=150)
    department: Optional[str] = Field(None, max_length=150)
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    fax: Optional[str] = None
    expertise_areas: Optional[List[str]] = Field(default=[])
    language_skills: Optional[List[str]] = Field(default=[])
    preferred_contact_method: Optional[str] = None
    best_time_to_contact: Optional[str] = None
    roles: Optional[List[str]] = Field(default=[])
    is_primary: bool = False
    is_backup: bool = False


class PartnerContactResponse(BaseModel):
    id: int
    partner_id: int
    first_name: str
    last_name: str
    title: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    mobile: Optional[str]
    expertise_areas: List[str]
    language_skills: List[str]
    is_primary: bool
    is_backup: bool
    last_contact_date: Optional[date]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Partnership Meeting Schemas
# ============================================================================

class PartnershipMeetingCreate(StrictInputSchema):
    meeting_type: str = Field(..., description="Type of meeting")
    title: str = Field(..., max_length=300)
    meeting_date: str = Field(...)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    format: Optional[str] = None  # in-person, virtual, hybrid, phone
    meeting_url: Optional[str] = None
    attendees: Optional[List[Dict[str, str]]] = Field(default=[], description="[{name, title, organization}]")
    library_attendees: Optional[List[Dict[str, str]]] = Field(default=[])
    agenda: Optional[str] = None
    topics_discussed: Optional[List[str]] = Field(default=[])
    decisions_made: Optional[List[str]] = Field(default=[])
    meeting_notes: str = Field(...)
    next_steps: Optional[List[Dict[str, str]]] = Field(default=[], description="[{action, owner, due_date}]")


class PartnershipMeetingResponse(BaseModel):
    id: int
    partner_id: int
    meeting_type: MeetingType
    title: str
    meeting_date: date
    start_time: Optional[str]
    end_time: Optional[str]
    format: Optional[str]
    attendees: List[Dict[str, str]]
    topics_discussed: List[str]
    meeting_notes: str
    next_steps: List[Dict[str, str]]
    follow_up_date: Optional[date]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Partnership Agreement Schemas
# ============================================================================

class PartnershipAgreementCreate(StrictInputSchema):
    agreement_type: str = Field(..., max_length=100)
    title: str = Field(..., max_length=300)
    start_date: str
    end_date: Optional[str] = None
    scope_of_work: Optional[str] = None
    objectives: Optional[List[str]] = Field(default=[])
    financial_terms: Optional[str] = None
    library_signatory: Optional[str] = None
    partner_signatory: Optional[str] = None
    document_url: Optional[str] = None
    document_filename: Optional[str] = None
    notes: Optional[str] = None


class PartnershipAgreementResponse(BaseModel):
    id: int
    partner_id: int
    agreement_type: str
    title: str
    status: MOUStatus
    start_date: date
    end_date: Optional[date]
    renewal_date: Optional[date]
    signed_at: Optional[datetime]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Joint Grant Opportunity Schemas
# ============================================================================

class JointGrantOpportunityCreate(StrictInputSchema):
    title: str = Field(..., max_length=300)
    description: Optional[str] = None
    funding_source: str = Field(..., max_length=300)
    partner_ids: Optional[List[int]] = Field(default=[])
    total_funding_available: Optional[float] = None
    amount_requested: Optional[float] = None
    grant_deadline: Optional[str] = None
    project_start_date: Optional[str] = None
    project_end_date: Optional[str] = None
    project_description: Optional[str] = None
    goals_and_outcomes: Optional[List[str]] = Field(default=[])


class JointGrantOpportunityResponse(BaseModel):
    id: int
    title: str
    funding_source: str
    status: GrantOpportunityStatus
    partner_ids: List[int]
    total_funding_available: Optional[float]
    amount_requested: Optional[float]
    grant_deadline: Optional[date]
    notification_date: Optional[date]
    awarded_amount: Optional[float]
    award_date: Optional[date]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Impact Report Schemas
# ============================================================================

class ImpactMetricCreate(StrictInputSchema):
    metric_type: str = Field(...)
    metric_name: str = Field(..., max_length=200)
    target_value: Optional[float] = None
    actual_value: float = Field(...)
    unit: Optional[str] = None
    notes: Optional[str] = None
    data_source: Optional[str] = None


class PartnerImpactReportCreate(StrictInputSchema):
    reporting_period_start: str
    reporting_period_end: str
    programs_delivered: int = 0
    program_sessions: int = 0
    total_participants: int = 0
    resources_shared_value: float = 0.0
    volunteer_hours: float = 0.0
    staff_hours_contributed: float = 0.0
    unique_people_served: int = 0
    impact_summary: Optional[str] = None
    outcomes_achieved: Optional[List[str]] = Field(default=[])
    success_stories: Optional[List[str]] = Field(default=[])
    estimated_value_provided: Optional[float] = None


class PartnerImpactReportResponse(BaseModel):
    id: int
    partner_id: int
    reporting_period_start: date
    reporting_period_end: date
    programs_delivered: int
    total_participants: int
    volunteer_hours: float
    staff_hours_contributed: float
    unique_people_served: int
    impact_summary: Optional[str]
    estimated_value_provided: Optional[float]
    metrics: List[ImpactMetricCreate] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Partner Recognition Schemas
# ============================================================================

class PartnerRecognitionCreate(StrictInputSchema):
    recognition_type: str = Field(...)
    title: str = Field(..., max_length=300)
    reason: str = Field(...)
    recognition_date: str
    accomplishments: Optional[List[str]] = Field(default=[])
    presented_by: Optional[str] = None
    certificate_issued: bool = False
    featured_in: Optional[List[str]] = Field(default=[])


class PartnerRecognitionResponse(BaseModel):
    id: int
    partner_id: int
    recognition_type: RecognitionType
    title: str
    reason: str
    recognition_date: date
    certificate_issued: bool
    award_name: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ThankYouMessageCreate(StrictInputSchema):
    contact_id: Optional[int] = None
    subject: str = Field(..., max_length=300)
    message_body: str = Field(...)
    message_type: Optional[str] = None  # email, letter, card, verbal
    sent_date: str
    sent_to_email: Optional[str] = None
    sent_to_name: Optional[str] = None
    reason: Optional[str] = None
    acknowledgement_of: Optional[str] = None


class ThankYouMessageResponse(BaseModel):
    id: int
    partner_id: int
    contact_id: Optional[int]
    subject: str
    message_type: Optional[str]
    sent_date: date
    sent_to_name: Optional[str]
    received_confirmation: bool
    response_received: Optional[datetime]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True
