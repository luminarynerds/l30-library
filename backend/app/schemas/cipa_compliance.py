# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# =============================================================================
# Policy Acceptance Schemas
# =============================================================================


class PolicyAcceptanceRequest(StrictInputSchema):
    policy_type: str = Field(..., description="Type of policy: internet_use, computer_lab, wifi_access, minor_internet")
    policy_version: str = Field(..., description="Version of the policy being accepted")
    workstation_id: Optional[str] = Field(None, description="Workstation identifier for computer lab")
    device_mac_hash: Optional[str] = Field(None, description="Hashed MAC address for WiFi devices")
    acknowledged_filtering: bool = Field(True, description="Patron acknowledges content filtering is active")
    acknowledged_monitoring: bool = Field(True, description="Patron acknowledges session may be monitored")


class PolicyAcceptanceResponse(BaseModel):
    id: int
    session_id: str
    policy_type: str
    policy_version: str
    is_minor: bool
    accepted_at: datetime
    valid_until: datetime
    message: str

    class Config:
        from_attributes = True


class PolicyAcceptanceCheck(BaseModel):
    has_valid_acceptance: bool
    policy_type: Optional[str] = None
    accepted_at: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    requires_minor_policy: bool = False


# =============================================================================
# Filter Bypass Schemas
# =============================================================================


class FilterBypassRequest(StrictInputSchema):
    patron_id: int = Field(..., description="ID of the adult patron requesting bypass")
    reason: str = Field(..., description="Reason: bona_fide_research, medical_information, legal_research, educational_purpose, other_lawful")
    reason_details: Optional[str] = Field(None, max_length=500, description="Additional context for the bypass")
    workstation_id: str = Field(..., description="Workstation where bypass will be active")
    duration_minutes: int = Field(60, ge=15, le=480, description="Duration of bypass in minutes (15-480)")
    patron_acknowledged_aup: bool = Field(True, description="Patron has acknowledged AUP")
    patron_acknowledged_monitoring: bool = Field(True, description="Patron acknowledges continued monitoring")


class FilterBypassResponse(BaseModel):
    id: int
    patron_id: int
    patron_name: str
    approved_by_name: str
    reason: str
    reason_details: Optional[str]
    workstation_id: str
    status: str
    bypass_start: datetime
    bypass_end: datetime
    duration_minutes: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class FilterBypassListResponse(BaseModel):
    bypasses: List[FilterBypassResponse]
    total: int
    active_count: int


class FilterBypassRevoke(StrictInputSchema):
    reason: str = Field(..., max_length=255, description="Reason for revocation")


# =============================================================================
# Computer Session Schemas
# =============================================================================


class ComputerSessionStart(StrictInputSchema):
    workstation_id: str = Field(..., description="Workstation identifier")
    patron_id: Optional[int] = Field(None, description="Patron ID if logged in, null for guest")
    policy_acceptance_id: Optional[int] = Field(None, description="ID of policy acceptance record")


class ComputerSessionResponse(BaseModel):
    id: int
    session_token: str
    patron_id: Optional[int]
    patron_name: Optional[str]
    workstation_id: str
    branch_id: Optional[int] = None
    branch_location: Optional[str]  # deprecated; use branch_id
    status: str
    is_minor: bool
    content_filtering_enabled: bool
    minor_filtering_enabled: bool
    started_at: datetime
    scheduled_end: Optional[datetime]
    ended_at: Optional[datetime]
    duration_minutes: int
    max_duration_minutes: int
    extension_count: int
    is_overtime: bool

    class Config:
        from_attributes = True


class ComputerSessionEnd(StrictInputSchema):
    reason: Optional[str] = Field(None, max_length=255, description="Optional reason for ending session")


class ComputerSessionExtend(StrictInputSchema):
    additional_minutes: int = Field(30, ge=15, le=60, description="Additional time in minutes")


class ActiveSessionsResponse(BaseModel):
    sessions: List[ComputerSessionResponse]
    total_active: int
    total_overtime: int
    workstations_in_use: int
    workstations_available: int


# =============================================================================
# CIPA Report Schemas
# =============================================================================


class CIPAReportRequest(StrictInputSchema):
    start_date: datetime = Field(..., description="Report period start")
    end_date: datetime = Field(..., description="Report period end")
    branch_id: Optional[int] = Field(None, description="Specific branch id, or null for all")
    branch_location: Optional[str] = Field(None, description="Specific branch label (deprecated; prefer branch_id)", deprecated=True)
    include_session_details: bool = Field(False, description="Include individual session records")


class CIPAReportSummary(BaseModel):
    report_period_start: datetime
    report_period_end: datetime
    branch_id: Optional[int] = None
    branch_location: Optional[str]  # deprecated; use branch_id

    # Session statistics
    total_sessions: int
    minor_sessions: int
    adult_sessions: int
    guest_sessions: int
    total_session_hours: float

    # Policy acceptance statistics
    policy_acceptances: int
    minor_policy_acceptances: int
    unique_patrons_accepted: int

    # Filter bypass statistics
    bypass_requests_total: int
    bypass_requests_by_reason: dict
    bypass_average_duration_minutes: float
    bypass_revocations: int

    # Compliance indicators
    minor_filtering_compliance_rate: float  # % of minor sessions with filtering
    policy_acceptance_rate: float  # % of sessions with valid policy acceptance

    generated_at: datetime


class CIPAReportResponse(BaseModel):
    summary: CIPAReportSummary
    report_file_url: Optional[str] = None
    message: str


# =============================================================================
# Internet Safety Policy Schemas
# =============================================================================


class InternetSafetyPolicyResponse(BaseModel):
    version: str
    effective_date: datetime
    title: str
    content_html: str
    minor_addendum_html: Optional[str]
    last_board_approval: Optional[datetime]
    next_review_date: Optional[datetime]


class PolicyVersionInfo(BaseModel):
    version: str
    effective_date: datetime
    is_current: bool
    policy_type: str


# =============================================================================
# CIPA Statistics Schemas
# =============================================================================


class CIPADashboardStats(BaseModel):
    # Current state
    active_sessions: int
    active_minor_sessions: int
    active_bypasses: int
    workstations_in_use: int
    workstations_total: int

    # Today's totals
    sessions_today: int
    minor_sessions_today: int
    policy_acceptances_today: int
    bypass_requests_today: int

    # Compliance metrics
    filtering_enabled_rate: float
    policy_acceptance_compliance: float

    # Alerts
    overtime_sessions: int
    expiring_bypasses: int


class WorkstationStatus(BaseModel):
    workstation_id: str
    branch_id: Optional[int] = None
    branch_location: Optional[str]  # deprecated; use branch_id
    is_in_use: bool
    current_session_id: Optional[int]
    patron_type: Optional[str]
    is_minor: bool
    filtering_enabled: bool
    bypass_active: bool
    session_started_at: Optional[datetime]
    session_time_remaining_minutes: Optional[int]
    is_overtime: bool


class WorkstationStatusList(BaseModel):
    workstations: List[WorkstationStatus]
    total: int
    in_use: int
    available: int
