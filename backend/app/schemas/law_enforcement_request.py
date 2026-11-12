# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema

from ..models.law_enforcement_request import (
    AuditActionType,
    ChecklistItemType,
    LegalReviewStatus,
    RequestType,
    WorkflowStatus,
)


# =============================================================================
# Base Schemas
# =============================================================================


class LawEnforcementRequestBase(StrictInputSchema):
    requesting_agency: str = Field(..., min_length=1, max_length=255)
    agency_contact_name: Optional[str] = Field(None, max_length=200)
    agency_contact_phone: Optional[str] = Field(None, max_length=50)
    agency_contact_email: Optional[str] = Field(None, max_length=255)
    agency_case_number: Optional[str] = Field(None, max_length=100)

    request_type: RequestType
    date_received: datetime
    date_due: Optional[datetime] = None

    patron_id: Optional[int] = None
    patron_name_on_request: Optional[str] = Field(None, max_length=200)
    patron_identifiers: Optional[str] = None

    data_requested: str = Field(..., min_length=1)
    data_date_range_start: Optional[datetime] = None
    data_date_range_end: Optional[datetime] = None

    patron_notification_permitted: bool = True
    gag_order_until: Optional[datetime] = None

    internal_notes: Optional[str] = None


class LawEnforcementRequestCreate(LawEnforcementRequestBase):

    @field_validator('request_type')
    @classmethod
    def validate_request_type(cls, v: RequestType) -> RequestType:
        if v == RequestType.INFORMAL_REQUEST:
            # Informal requests should generally be declined
            # but we still want to track them
            pass
        return v


class LawEnforcementRequestUpdate(StrictInputSchema):
    requesting_agency: Optional[str] = Field(None, min_length=1, max_length=255)
    agency_contact_name: Optional[str] = Field(None, max_length=200)
    agency_contact_phone: Optional[str] = Field(None, max_length=50)
    agency_contact_email: Optional[str] = Field(None, max_length=255)
    agency_case_number: Optional[str] = Field(None, max_length=100)

    date_due: Optional[datetime] = None

    patron_id: Optional[int] = None
    patron_name_on_request: Optional[str] = Field(None, max_length=200)
    patron_identifiers: Optional[str] = None

    data_requested: Optional[str] = None
    data_date_range_start: Optional[datetime] = None
    data_date_range_end: Optional[datetime] = None

    patron_notification_permitted: Optional[bool] = None
    gag_order_until: Optional[datetime] = None

    internal_notes: Optional[str] = None


# =============================================================================
# Legal Review Schemas
# =============================================================================


class LegalReviewUpdate(StrictInputSchema):
    legal_review_status: LegalReviewStatus
    legal_review_notes: Optional[str] = None


class LegalReviewResponse(BaseModel):
    legal_review_status: LegalReviewStatus
    legal_reviewer_id: Optional[int] = None
    legal_reviewer_name: Optional[str] = None
    legal_review_date: Optional[datetime] = None
    legal_review_notes: Optional[str] = None

    model_config = {"from_attributes": True}


# =============================================================================
# Workflow Schemas
# =============================================================================


class WorkflowStatusUpdate(StrictInputSchema):
    workflow_status: WorkflowStatus
    notes: Optional[str] = None


class WorkflowStatusResponse(BaseModel):
    workflow_status: WorkflowStatus
    checklist_progress: dict  # {completed: int, total: int, percent: float}

    model_config = {"from_attributes": True}


# =============================================================================
# Checklist Schemas
# =============================================================================


class ChecklistItemUpdate(StrictInputSchema):
    is_completed: Optional[bool] = None
    is_applicable: Optional[bool] = None
    completion_notes: Optional[str] = None


class ChecklistItemResponse(BaseModel):
    id: int
    item_type: ChecklistItemType
    item_description: str
    is_completed: bool
    is_required: bool
    is_applicable: bool
    completed_by_id: Optional[int] = None
    completed_by_name: Optional[str] = None
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    sort_order: int

    model_config = {"from_attributes": True}


# =============================================================================
# Response/Compliance Schemas
# =============================================================================


class ResponseUpdate(StrictInputSchema):
    response_method: str = Field(..., max_length=100)
    response_summary: str
    data_provided_summary: Optional[str] = None


class PatronNotificationRecord(BaseModel):
    notification_method: str = Field(..., max_length=100)
    notification_notes: Optional[str] = None


# =============================================================================
# Audit Log Schemas
# =============================================================================


class AuditLogResponse(BaseModel):
    id: int
    action: AuditActionType
    performed_by_id: Optional[int] = None
    performed_by_name: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class AddNoteRequest(StrictInputSchema):
    note: str = Field(..., min_length=1)


# =============================================================================
# Template Schemas
# =============================================================================


class ResponseTemplateCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    template_type: str = Field(..., max_length=50)
    applicable_request_types: Optional[list[str]] = None
    subject_template: Optional[str] = Field(None, max_length=500)
    body_template: str = Field(..., min_length=1)


class ResponseTemplateUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    template_type: Optional[str] = Field(None, max_length=50)
    applicable_request_types: Optional[list[str]] = None
    subject_template: Optional[str] = Field(None, max_length=500)
    body_template: Optional[str] = None
    is_active: Optional[bool] = None


class ResponseTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    template_type: str
    applicable_request_types: Optional[list[str]] = None
    subject_template: Optional[str] = None
    body_template: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RenderedTemplate(BaseModel):
    subject: Optional[str] = None
    body: str


# =============================================================================
# Full Response Schemas
# =============================================================================


class PatronSummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    library_card: Optional[str] = None

    model_config = {"from_attributes": True}


class LawEnforcementRequestResponse(BaseModel):
    id: int
    tracking_number: str

    # Agency info
    requesting_agency: str
    agency_contact_name: Optional[str] = None
    agency_contact_phone: Optional[str] = None
    agency_contact_email: Optional[str] = None
    agency_case_number: Optional[str] = None

    # Request details
    request_type: RequestType
    date_received: datetime
    date_due: Optional[datetime] = None

    # Patron info
    patron_id: Optional[int] = None
    patron: Optional[PatronSummary] = None
    patron_name_on_request: Optional[str] = None
    patron_identifiers: Optional[str] = None

    # Data requested
    data_requested: str
    data_date_range_start: Optional[datetime] = None
    data_date_range_end: Optional[datetime] = None

    # Legal review
    legal_review_status: LegalReviewStatus
    legal_reviewer_id: Optional[int] = None
    legal_review_date: Optional[datetime] = None
    legal_review_notes: Optional[str] = None

    # Workflow
    workflow_status: WorkflowStatus

    # Response
    response_date: Optional[datetime] = None
    responding_staff_id: Optional[int] = None
    response_method: Optional[str] = None
    response_summary: Optional[str] = None
    data_provided_summary: Optional[str] = None

    # Patron notification
    patron_notification_permitted: bool
    patron_notification_date: Optional[datetime] = None
    patron_notification_method: Optional[str] = None
    gag_order_until: Optional[datetime] = None

    # Internal
    internal_notes: Optional[str] = None

    # Metadata
    created_by_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # Progress
    checklist_progress: Optional[dict] = None

    model_config = {"from_attributes": True}


class LawEnforcementRequestListItem(StrictInputSchema):
    id: int
    tracking_number: str
    requesting_agency: str
    request_type: RequestType
    date_received: datetime
    date_due: Optional[datetime] = None
    patron_name_on_request: Optional[str] = None
    legal_review_status: LegalReviewStatus
    workflow_status: WorkflowStatus
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# =============================================================================
# Reporting Schemas
# =============================================================================


class TransparencyReportRequest(StrictInputSchema):
    year: int = Field(..., ge=2000, le=2100)
    include_details: bool = False  # Whether to include request-level details


class TransparencyReportSummary(BaseModel):
    year: int
    total_requests: int
    requests_by_type: dict[str, int]
    requests_by_status: dict[str, int]
    requests_by_legal_outcome: dict[str, int]

    # Compliance metrics
    average_response_time_days: Optional[float] = None
    requests_with_patron_notification: int
    requests_with_gag_order: int

    # Data disclosure metrics
    requests_fully_complied: int
    requests_partially_complied: int
    requests_rejected: int
    requests_withdrawn: int

    # Patron impact
    unique_patrons_affected: int


class TransparencyReportDetail(BaseModel):
    tracking_number: str
    request_type: RequestType
    requesting_agency: str
    date_received: datetime
    response_date: Optional[datetime] = None
    legal_outcome: LegalReviewStatus
    workflow_status: WorkflowStatus
    patron_notified: bool
    data_types_provided: Optional[str] = None  # General description, not specific data


class TransparencyReport(BaseModel):
    report_generated_at: datetime
    summary: TransparencyReportSummary
    details: Optional[list[TransparencyReportDetail]] = None


# =============================================================================
# Data Export Schemas
# =============================================================================


class PatronDataExportRequest(StrictInputSchema):
    request_id: int  # The law enforcement request this is for
    include_profile: bool = True
    include_checkouts: bool = True
    include_holds: bool = True
    include_fines: bool = True
    include_reading_history: bool = False  # Only if tracking enabled and requested
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class PatronDataExportResponse(BaseModel):
    request_id: int
    patron_id: int
    exported_at: datetime
    data_categories_included: list[str]
    profile: Optional[dict] = None
    checkouts: Optional[list[dict]] = None
    holds: Optional[list[dict]] = None
    fines: Optional[list[dict]] = None
    reading_history: Optional[list[dict]] = None


# =============================================================================
# List and Statistics Schemas
# =============================================================================


class LawEnforcementRequestListResponse(BaseModel):
    items: list[LawEnforcementRequestListItem]
    total: int
    skip: int
    limit: int


class LawEnforcementStatsResponse(BaseModel):
    total_requests: int
    pending_review: int
    in_progress: int
    completed: int
    this_year: int
