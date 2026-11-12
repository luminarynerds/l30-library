# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas._base import StrictInputSchema

from ..models.parent_onboarding import (
    CareAssignmentStatus, CareCheckInType, CheckInFrequency,
    ChildcareRegistrationStatus, ChildcareSessionStatus,
    ConnectionGroupType, EnrollmentFacilitationStatus,
    GroupMemberStatus, HomeVisitPurpose, HomeVisitStatus,
    MeetingFrequency, ParentOnboardingStatus, RiskLevel,
    ResourceGuideFlagReason, ResourceGuideFlagResolution,
    ResourceGuideFlagStatus,
)


# ============================================================================
# Component 1: Welcome Onboarding Sessions
# ============================================================================

class ParentOnboardingSessionCreate(StrictInputSchema):
    patron_id: int
    staff_id: Optional[int] = None
    branch_id: int
    scheduled_at: datetime
    baby_age_months: Optional[int] = Field(None, ge=0, le=60)
    languages_spoken: list[str] = []


class ParentOnboardingSessionUpdate(StrictInputSchema):
    staff_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[ParentOnboardingStatus] = None
    baby_age_months: Optional[int] = Field(None, ge=0, le=60)
    languages_spoken: Optional[list[str]] = None
    family_situation_notes: Optional[str] = Field(None, max_length=5000)
    needs_identified: Optional[list[dict]] = None
    services_referred: Optional[list[dict]] = None
    welcome_packet_id: Optional[int] = None


class ParentOnboardingSessionComplete(StrictInputSchema):
    family_situation_notes: Optional[str] = Field(None, max_length=5000)
    needs_identified: list = []
    services_referred: list = []
    welcome_packet_id: Optional[int] = None


class ParentOnboardingSessionResponse(BaseModel):
    id: int
    patron_id: int
    staff_id: Optional[int] = None
    branch_id: int
    status: ParentOnboardingStatus
    scheduled_at: datetime
    completed_at: Optional[datetime] = None
    baby_age_months: Optional[int] = None
    languages_spoken: list[str] = []
    family_situation_notes: Optional[str] = None
    needs_identified: list = []
    services_referred: list = []
    welcome_packet_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True

    # These columns are nullable jsonb in the DB but carry a non-null list
    # default here. from_attributes hands pydantic an explicit None, which the
    # declared default does NOT cover, so the response 500s with a
    # ResponseValidationError on rows that hold NULL. Coerce None back to [].
    _NULL_DEFAULTS: ClassVar[dict] = {
        "languages_spoken": [],
        "needs_identified": [],
        "services_referred": [],
    }

    @field_validator("languages_spoken", "needs_identified", "services_referred", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v


class ParentOnboardingSessionListResponse(BaseModel):
    sessions: list[ParentOnboardingSessionResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Component 2: Care Coordinator
# ============================================================================

class CareCoordinatorAssignmentCreate(StrictInputSchema):
    patron_id: int
    coordinator_id: int
    parent_session_id: Optional[int] = None
    check_in_frequency: CheckInFrequency = CheckInFrequency.biweekly
    risk_level: RiskLevel = RiskLevel.low
    start_date: date
    notes: Optional[str] = Field(None, max_length=5000)


class CareCoordinatorAssignmentUpdate(StrictInputSchema):
    coordinator_id: Optional[int] = None
    status: Optional[CareAssignmentStatus] = None
    check_in_frequency: Optional[CheckInFrequency] = None
    risk_level: Optional[RiskLevel] = None
    end_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=5000)


class CareCoordinatorAssignmentResponse(BaseModel):
    id: int
    patron_id: int
    coordinator_id: Optional[int] = None
    parent_session_id: Optional[int] = None
    status: CareAssignmentStatus
    check_in_frequency: CheckInFrequency
    risk_level: RiskLevel
    start_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class CareCoordinatorAssignmentListResponse(BaseModel):
    assignments: list[CareCoordinatorAssignmentResponse]
    total: int
    limit: int
    offset: int


class CareCheckInCreate(StrictInputSchema):
    check_in_type: CareCheckInType
    scheduled_date: date
    completed_date: Optional[date] = None
    mood_assessment: Optional[int] = Field(None, ge=1, le=5)
    concerns_raised: Optional[str] = Field(None, max_length=5000)
    actions_taken: Optional[str] = Field(None, max_length=5000)
    follow_up_needed: bool = False
    next_check_in_date: Optional[date] = None


class CareCheckInResponse(BaseModel):
    id: int
    assignment_id: int
    check_in_type: CareCheckInType
    scheduled_date: date
    completed_date: Optional[date] = None
    mood_assessment: Optional[int] = None
    concerns_raised: Optional[str] = None
    actions_taken: Optional[str] = None
    follow_up_needed: bool
    next_check_in_date: Optional[date] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class CareCheckInListResponse(BaseModel):
    check_ins: list[CareCheckInResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Component 3: Resource Guide
# ============================================================================

class ResourceGuideSectionCreate(StrictInputSchema):
    title_key: str = Field(..., max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    display_order: int = 0
    branch_id: Optional[int] = None


class ResourceGuideSectionUpdate(StrictInputSchema):
    title_key: Optional[str] = Field(None, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    branch_id: Optional[int] = None


class ResourceGuideItemTranslation(BaseModel):
    title: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = Field(None, max_length=2000)

    class Config:
        # Permissive on read (existing rows may carry future fields from a
        # later schema), strict-by-default on write via StrictInputSchema
        # callers below.
        extra = "ignore"


class ResourceGuideItemCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = Field(None, max_length=2000)
    contact_info: Optional[str] = Field(None, max_length=300)
    url: Optional[str] = Field(None, max_length=500)
    languages: list[str] = []
    # Per-language overrides keyed by ISO 639-1 code. Empty {} on create
    # is the common case; staff add translations via PATCH later.
    translations: dict[str, ResourceGuideItemTranslation] = {}
    display_order: int = 0


class ResourceGuideItemUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = Field(None, max_length=2000)
    contact_info: Optional[str] = Field(None, max_length=300)
    url: Optional[str] = Field(None, max_length=500)
    languages: Optional[list[str]] = None
    # Optional[None | dict[str, ResourceGuideItemTranslation | None]] in
    # spirit; pydantic doesn't let us express "value can be explicitly
    # null to delete" through the schema, so the route handler accepts
    # raw dict and validates each entry by hand.
    translations: Optional[dict[str, Optional[ResourceGuideItemTranslation]]] = None
    display_order: Optional[int] = None


class ResourceGuideItemResponse(BaseModel):
    id: int
    section_id: int
    title: str
    description: Optional[str] = None
    contact_info: Optional[str] = None
    url: Optional[str] = None
    languages: list[str] = []
    translations: dict[str, ResourceGuideItemTranslation] = {}
    display_order: int
    last_verified_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    verified_by_name: Optional[str] = None
    stale: bool = False
    open_flag_count: int = 0

    class Config:
        from_attributes = True


class ResourceGuideSectionResponse(BaseModel):
    id: int
    title_key: str
    icon: Optional[str] = None
    display_order: int
    is_active: bool
    branch_id: Optional[int] = None
    items: list[ResourceGuideItemResponse] = []
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ----------------------------------------------------------------------------
# Resource guide flags (verification trail)
# ----------------------------------------------------------------------------

class ResourceGuideFlagCreate(StrictInputSchema):
    reason_code: ResourceGuideFlagReason
    comment: Optional[str] = Field(None, max_length=500)


class ResourceGuideFlagUpdate(StrictInputSchema):
    status: ResourceGuideFlagStatus
    resolution: Optional[ResourceGuideFlagResolution] = None
    resolution_notes: Optional[str] = Field(None, max_length=2000)


class ResourceGuideFlagItemSnapshot(BaseModel):
    id: int
    section_id: int
    title: str
    contact_info: Optional[str] = None
    url: Optional[str] = None

    class Config:
        from_attributes = True


class ResourceGuideFlagResponse(BaseModel):
    id: int
    item_id: int
    flagged_by_id: Optional[int] = None
    flagged_by_name: Optional[str] = None
    reason_code: str
    comment: Optional[str] = None
    status: str
    resolution: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_by_id: Optional[int] = None
    resolved_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    item: Optional[ResourceGuideFlagItemSnapshot] = None

    class Config:
        from_attributes = True


# ============================================================================
# Component 4: Emergency Childcare
# ============================================================================

class ChildcareSessionCreate(StrictInputSchema):
    branch_id: int
    room_id: Optional[int] = None
    staff_id: Optional[int] = None
    date: date
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    max_children: int = Field(6, ge=1, le=20)
    age_range_min_months: int = Field(0, ge=0)
    age_range_max_months: int = Field(60, ge=0)


class ChildcareSessionUpdate(StrictInputSchema):
    room_id: Optional[int] = None
    staff_id: Optional[int] = None
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    max_children: Optional[int] = Field(None, ge=1, le=20)
    status: Optional[ChildcareSessionStatus] = None


class ChildcareSessionResponse(BaseModel):
    id: int
    branch_id: int
    room_id: Optional[int] = None
    staff_id: Optional[int] = None
    date: date
    start_time: str
    end_time: str
    max_children: int
    age_range_min_months: int
    age_range_max_months: int
    status: ChildcareSessionStatus
    registered_count: int = 0
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ChildcareSessionListResponse(BaseModel):
    sessions: list[ChildcareSessionResponse]
    total: int
    limit: int
    offset: int


class AuthorizedPickupEntry(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=7, max_length=50)
    relationship: str = Field(..., min_length=1, max_length=100)
    id_required: bool = False


class ChildcareRegistrationCreate(StrictInputSchema):
    child_name: str = Field(..., min_length=1, max_length=200)
    child_age_months: int = Field(..., ge=0, le=60)
    special_needs_notes: Optional[str] = Field(None, max_length=2000)
    emergency_contact_name: str = Field(..., min_length=1, max_length=200)
    emergency_contact_phone: str = Field(..., min_length=10, max_length=50)
    authorized_pickup: list[AuthorizedPickupEntry] = Field(default_factory=list, max_length=10)


class ChildcareRegistrationUpdate(StrictInputSchema):
    status: Optional[ChildcareRegistrationStatus] = None
    special_needs_notes: Optional[str] = Field(None, max_length=2000)
    authorized_pickup: Optional[list[AuthorizedPickupEntry]] = Field(None, max_length=10)
    no_show_reason: Optional[str] = Field(None, max_length=500)


class ChildcareCheckoutRequest(StrictInputSchema):
    picked_up_by_name: str = Field(..., min_length=1, max_length=200)
    picked_up_by_phone: str = Field(..., min_length=7, max_length=50)
    staff_override_reason: Optional[str] = Field(None, min_length=3, max_length=500)


class ChildcareRegistrationResponse(BaseModel):
    id: int
    session_id: int
    patron_id: int
    child_name: str
    child_age_months: int
    special_needs_notes: Optional[str] = None
    emergency_contact_name: str
    emergency_contact_phone: str
    status: ChildcareRegistrationStatus
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    authorized_pickup: list[AuthorizedPickupEntry] = Field(default_factory=list)
    checked_out_by_name: Optional[str] = None
    checked_out_by_phone: Optional[str] = None
    pickup_override_reason: Optional[str] = None
    # Staff-side audit columns. ``checked_out_by_staff_id`` is who operated
    # the checkout UI, distinct from ``checked_out_by_name`` (the adult).
    checked_in_by_staff_id: Optional[int] = None
    checked_out_by_staff_id: Optional[int] = None
    no_show_flagged_by_staff_id: Optional[int] = None
    no_show_flagged_at: Optional[datetime] = None
    no_show_reason: Optional[str] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ChildcareRosterEntry(BaseModel):
    registration: ChildcareRegistrationResponse
    parent_name: str
    parent_email: Optional[str] = None
    # Optional staff-name decoration: when populated lets the UI show
    # "checked in by Babbage" without a second lookup. None if the FK is
    # NULL or the User row was deleted.
    checked_in_by_name: Optional[str] = None
    checked_out_by_staff_name: Optional[str] = None
    no_show_flagged_by_name: Optional[str] = None
    class Config:
        from_attributes = True


class ChildcareRosterCounts(BaseModel):
    registered: int = 0
    checked_in: int = 0
    checked_out: int = 0
    no_show: int = 0
    cancelled: int = 0


class ChildcareRosterResponse(BaseModel):
    session_id: int
    entries: list[ChildcareRosterEntry]
    # ``counts`` is optional in this schema (older clients pre-checkin-roster
    # don't read it) but the endpoint always populates it.
    counts: ChildcareRosterCounts = Field(default_factory=ChildcareRosterCounts)


# ============================================================================
# Component 5: Connection Groups
# ============================================================================

_CONFIDENTIAL_DEFAULT_TYPES = {
    ConnectionGroupType.teen_parents,
    ConnectionGroupType.postpartum_support,
}


class ParentConnectionGroupCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    facilitator_id: Optional[int] = None
    branch_id: int
    group_type: ConnectionGroupType = ConnectionGroupType.general
    max_members: int = Field(12, ge=2, le=30)
    meeting_frequency: MeetingFrequency = MeetingFrequency.weekly
    meeting_day_of_week: Optional[str] = Field(None, max_length=20)
    meeting_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    location: Optional[str] = Field(None, max_length=300)
    languages: list[str] = []
    confidential: Optional[bool] = None
    confidential_card_description: Optional[str] = Field(None, max_length=300)
    confidential_approval_message: Optional[str] = Field(None, max_length=500)
    estimated_response_window_hours: int = Field(48, ge=1, le=336)
    # Optional cohort window. Both nullable — "leave blank for ongoing" per spec.
    cohort_start_date: Optional[date] = None
    cohort_end_date: Optional[date] = None

    @model_validator(mode="after")
    def _default_confidential_for_sensitive_types(self):
        # Privacy-by-default for stigma-risk group types unless caller explicit.
        if self.confidential is None:
            self.confidential = self.group_type in _CONFIDENTIAL_DEFAULT_TYPES
        return self


class ParentConnectionGroupUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    facilitator_id: Optional[int] = None
    group_type: Optional[ConnectionGroupType] = None
    max_members: Optional[int] = Field(None, ge=2, le=30)
    meeting_frequency: Optional[MeetingFrequency] = None
    meeting_day_of_week: Optional[str] = Field(None, max_length=20)
    meeting_time: Optional[str] = None
    location: Optional[str] = Field(None, max_length=300)
    languages: Optional[list[str]] = None
    is_active: Optional[bool] = None
    confidential: Optional[bool] = None
    confidential_card_description: Optional[str] = Field(None, max_length=300)
    confidential_approval_message: Optional[str] = Field(None, max_length=500)
    estimated_response_window_hours: Optional[int] = Field(None, ge=1, le=336)
    cohort_start_date: Optional[date] = None
    cohort_end_date: Optional[date] = None


class ParentConnectionGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    facilitator_id: Optional[int] = None
    branch_id: int
    group_type: ConnectionGroupType
    max_members: int
    meeting_frequency: MeetingFrequency
    meeting_day_of_week: Optional[str] = None
    meeting_time: Optional[str] = None
    location: Optional[str] = None
    languages: list[str] = []
    is_active: bool
    member_count: int = 0
    confidential: bool = False
    confidential_card_description: Optional[str] = None
    confidential_approval_message: Optional[str] = None
    estimated_response_window_hours: int = 48
    cohort_start_date: Optional[date] = None
    cohort_end_date: Optional[date] = None
    archived_at: Optional[datetime] = None
    archived_by_id: Optional[int] = None
    archive_reason: Optional[str] = None
    archive_notes: Optional[str] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Lifecycle: archive / unarchive / meeting instances (cg_lifecycle_001).
# ============================================================================
#
# Archive reasons + cancel reasons are *closed* enums on the wire. Backend
# accepts the string value; frontend renders via i18n keys whose names match
# the enum value 1:1 so the mapping stays mechanical (see spec i18n section).


_ARCHIVE_REASONS = ("cohort_complete", "low_attendance", "facilitator_departed", "other")
_CANCEL_REASONS = ("facilitator_sick", "venue_unavailable", "weather", "low_rsvp", "other")


class ArchiveGroupRequest(StrictInputSchema):
    archive_reason: str = Field(..., max_length=40)
    archive_notes: Optional[str] = Field(None, max_length=2000)
    notify_members: bool = False
    patron_message: Optional[str] = Field(None, max_length=2000)

    @field_validator("archive_reason")
    @classmethod
    def _validate_archive_reason(cls, v: str) -> str:
        if v not in _ARCHIVE_REASONS:
            raise ValueError(
                f"archive_reason must be one of: {', '.join(_ARCHIVE_REASONS)}"
            )
        return v


class ArchiveGroupResponse(BaseModel):
    id: int
    is_active: bool
    archived_at: Optional[datetime] = None
    archived_by_id: Optional[int] = None
    archive_reason: Optional[str] = None
    archive_notes: Optional[str] = None
    notified_member_count: int = 0
    email_dispatched: bool = False
    # email_partial is set to True if the daily-cap safeguard truncated the
    # send mid-batch. Caller surfaces this in a toast or admin log entry.
    email_partial: bool = False


class CapacityConflictDetail(BaseModel):
    error: str = "capacity_below_active_members"
    requested_max_members: int
    current_active_count: int
    excess: int
    affected_member_ids: list[int]


class GroupMeetingResponse(BaseModel):
    id: int
    group_id: int
    meeting_date: date
    scheduled_time: Optional[str] = None
    location: Optional[str] = None
    status: str
    cancelled_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by_id: Optional[int] = None
    rescheduled_to_meeting_id: Optional[int] = None
    staff_notes: Optional[str] = None
    patron_message: Optional[str] = None
    email_dispatched_at: Optional[datetime] = None
    email_dispatched_count: int = 0
    class Config:
        from_attributes = True


class GroupMeetingsListResponse(BaseModel):
    meetings: list[GroupMeetingResponse]
    total: int


class CancelMeetingRequest(StrictInputSchema):
    reason: str = Field(..., max_length=40)
    notes: Optional[str] = Field(None, max_length=2000)
    patron_message: Optional[str] = Field(None, max_length=500)

    @field_validator("reason")
    @classmethod
    def _validate_reason(cls, v: str) -> str:
        if v not in _CANCEL_REASONS:
            raise ValueError(
                f"reason must be one of: {', '.join(_CANCEL_REASONS)}"
            )
        return v


class RescheduleMeetingRequest(StrictInputSchema):
    new_date: date
    new_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    new_location: Optional[str] = Field(None, max_length=300)
    notes: Optional[str] = Field(None, max_length=2000)
    patron_message: Optional[str] = Field(None, max_length=500)


class MeetingDispatchResponse(BaseModel):
    meeting: GroupMeetingResponse
    # On reschedule the new row is created; the old row is the historical one.
    new_meeting: Optional[GroupMeetingResponse] = None
    notified_member_count: int = 0
    email_dispatched: bool = False
    email_partial: bool = False


class ConfidentialJoinRequest(StrictInputSchema):
    patron_id: int = Field(..., gt=0)
    request_message: Optional[str] = Field(None, max_length=500)
    consent_to_share_contact: bool = False


class ConfidentialJoinRequestResponse(BaseModel):
    id: int
    group_id: int
    patron_id: int
    status: GroupMemberStatus
    requested_at: datetime
    requested_by_id: int
    estimated_response_window_hours: int
    email_partial: bool = False


class ApprovalQueueEntry(BaseModel):
    id: int
    group_id: int
    group_name: str
    patron_id: int
    patron_name: Optional[str] = None
    patron_contact_visible: bool = False
    patron_email: Optional[str] = None
    patron_phone: Optional[str] = None
    request_message: Optional[str] = None
    requested_at: datetime
    days_pending: int


class ApprovalDecisionLogEntry(BaseModel):
    id: int
    patron_name: Optional[str] = None
    decision: GroupMemberStatus
    decided_at: datetime
    decided_by_id: Optional[int] = None
    decided_by_name: Optional[str] = None


class ApprovalQueueResponse(BaseModel):
    pending: list[ApprovalQueueEntry]
    approval_decision_log: list[ApprovalDecisionLogEntry]


class DecideRequestPayload(StrictInputSchema):
    decision: str = Field(..., description="approve|deny")
    decision_note: Optional[str] = Field(None, max_length=1000)
    patron_message: Optional[str] = Field(None, max_length=1000)

    @field_validator("decision")
    @classmethod
    def _validate_decision(cls, v: str) -> str:
        if v not in ("approve", "deny"):
            raise ValueError("decision must be 'approve' or 'deny'")
        return v


class DecideRequestResponse(BaseModel):
    id: int
    group_id: int
    patron_id: int
    status: GroupMemberStatus
    decided_at: datetime
    decided_by_id: int
    email_partial: bool = False


class ParentConnectionGroupListResponse(BaseModel):
    groups: list[ParentConnectionGroupResponse]
    total: int
    limit: int
    offset: int


class GroupMemberResponse(BaseModel):
    id: int
    group_id: int
    patron_id: int
    status: GroupMemberStatus
    joined_date: date
    left_date: Optional[date] = None
    attendance_count: int

    class Config:
        from_attributes = True


class StaffEnrollRequest(StrictInputSchema):
    patron_id: int = Field(..., gt=0)
    consent_note: Optional[str] = Field(default=None, max_length=500)
    override_capacity: bool = False
    override_justification: Optional[str] = Field(default=None, min_length=10, max_length=500)

    @model_validator(mode="after")
    def _require_justification_when_override(self):
        # Cross-field check: a field_validator wouldn'''t fire when justification
        # is omitted entirely; use model_validator so we catch the missing-field
        # case. Route handler also re-checks (defense in depth).
        if self.override_capacity and not self.override_justification:
            raise ValueError("override_justification is required when override_capacity is true")
        return self


class EnrollMemberResponse(BaseModel):
    id: int
    group_id: int
    patron_id: int
    patron_name: Optional[str] = None
    status: GroupMemberStatus
    joined_date: date
    enrolled_by_id: Optional[int] = None
    enrolled_by_name: Optional[str] = None
    consent_note_recorded: bool = False
    capacity_overridden: bool = False

    class Config:
        from_attributes = True


class GroupMemberDetailResponse(BaseModel):
    id: int
    group_id: int
    patron_id: int
    patron_name: Optional[str] = None
    status: GroupMemberStatus
    joined_date: date
    left_date: Optional[date] = None
    attendance_count: int
    enrolled_by_id: Optional[int] = None
    enrolled_by_name: Optional[str] = None
    capacity_override: bool = False

    class Config:
        from_attributes = True


class GroupMembersListResponse(BaseModel):
    members: list[GroupMemberDetailResponse]
    active_count: int
    waitlisted_count: int


# ============================================================================
# Component 6: Service Enrollment Facilitation
# ============================================================================

class ServiceEnrollmentCreate(StrictInputSchema):
    patron_id: int
    partner_id: Optional[int] = None
    staff_id: Optional[int] = None
    service_name: str = Field(..., min_length=1, max_length=300)
    documents_needed: list[str] = []
    notes: Optional[str] = Field(None, max_length=5000)


class ServiceEnrollmentUpdate(StrictInputSchema):
    status: Optional[EnrollmentFacilitationStatus] = None
    partner_id: Optional[int] = None
    application_date: Optional[date] = None
    enrollment_date: Optional[date] = None
    documents_needed: Optional[list[str]] = None
    documents_provided: Optional[list[str]] = None
    notes: Optional[str] = Field(None, max_length=5000)
    outcome_notes: Optional[str] = Field(None, max_length=5000)


class ServiceEnrollmentResponse(BaseModel):
    id: int
    patron_id: int
    partner_id: Optional[int] = None
    staff_id: Optional[int] = None
    service_name: str
    status: EnrollmentFacilitationStatus
    application_date: Optional[date] = None
    enrollment_date: Optional[date] = None
    documents_needed: list[str] = []
    documents_provided: list[str] = []
    notes: Optional[str] = None
    outcome_notes: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ServiceEnrollmentListResponse(BaseModel):
    enrollments: list[ServiceEnrollmentResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Component 7: Home Visits
# ============================================================================

class ParentHomeVisitCreate(StrictInputSchema):
    patron_id: int
    visitor_id: Optional[int] = None
    parent_session_id: Optional[int] = None
    purpose: HomeVisitPurpose
    scheduled_date: date
    scheduled_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    address: Optional[str] = Field(None, max_length=1000)
    safety_buddy_user_id: Optional[int] = None


class ParentHomeVisitUpdate(StrictInputSchema):
    visitor_id: Optional[int] = None
    status: Optional[HomeVisitStatus] = None
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[str] = None
    address: Optional[str] = Field(None, max_length=1000)
    visit_notes: Optional[str] = Field(None, max_length=5000)
    items_brought: Optional[list[dict]] = None
    services_discussed: Optional[list[dict]] = None
    follow_up_needed: Optional[bool] = None
    next_visit_date: Optional[date] = None
    safety_buddy_user_id: Optional[int] = None


class ParentHomeVisitComplete(BaseModel):
    visit_notes: Optional[str] = Field(None, max_length=5000)
    items_brought: list = []
    services_discussed: list = []
    follow_up_needed: bool = False
    next_visit_date: Optional[date] = None


# ----------------------------------------------------------------------------
# Status-mutation request bodies (home_visit_mutations_001, 2026-05-25)
# ----------------------------------------------------------------------------

class HomeVisitConfirmRequest(StrictInputSchema):
    reason: Optional[str] = Field(None, max_length=500)


class HomeVisitCompleteRequest(StrictInputSchema):
    outcomes: str = Field(..., min_length=1, max_length=2000)
    resources_delivered: list[str] = Field(default_factory=list)
    follow_up_needed: bool = False
    follow_up_date: Optional[date] = None
    follow_up_notes: Optional[str] = Field(None, max_length=2000)
    referrals: list[str] = Field(default_factory=list)


class HomeVisitCancelRequest(StrictInputSchema):
    cancelled_reason: str = Field(..., min_length=1, max_length=1000)
    notify_acknowledged: bool = False


class HomeVisitRescheduleRequest(StrictInputSchema):
    new_scheduled_date: date
    new_scheduled_time: Optional[str] = Field(
        None, pattern=r"^\d{2}:\d{2}$"
    )
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    reason: str = Field(..., min_length=1, max_length=1000)


class HomeVisitConflictItem(BaseModel):
    id: int
    scheduled_date: date
    scheduled_time: Optional[str] = None
    patron_id: int
    patron_name: Optional[str] = None
    status: HomeVisitStatus

    class Config:
        from_attributes = True


class HomeVisitConflictResponse(BaseModel):
    has_conflict: bool
    conflicting_visits: list[HomeVisitConflictItem] = []


class HomeVisitStatusHistoryItem(BaseModel):
    id: int
    visit_id: int
    from_status: Optional[HomeVisitStatus] = None
    to_status: HomeVisitStatus
    changed_by_id: Optional[int] = None
    changed_by_name: Optional[str] = None
    changed_at: datetime
    reason: Optional[str] = None
    metadata_json: Optional[dict] = None

    class Config:
        from_attributes = True


class HomeVisitStatusHistoryResponse(BaseModel):
    history: list[HomeVisitStatusHistoryItem]
    total: int


class HomeVisitRescheduleResponse(BaseModel):
    visit: "ParentHomeVisitResponse"
    replacement_visit: "ParentHomeVisitResponse"


class ParentHomeVisitResponse(BaseModel):
    id: int
    patron_id: int
    visitor_id: Optional[int] = None
    parent_session_id: Optional[int] = None
    purpose: HomeVisitPurpose
    status: HomeVisitStatus
    scheduled_date: date
    scheduled_time: Optional[str] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    address: Optional[str] = None
    visit_notes: Optional[str] = None
    items_brought: list = []
    services_discussed: list = []
    follow_up_needed: bool
    next_visit_date: Optional[date] = None
    # Lifecycle fields backed by home_visit_mutations_001 columns.
    outcomes: Optional[str] = None
    resources_delivered: Optional[list[str]] = None
    follow_up_date: Optional[date] = None
    cancelled_reason: Optional[str] = None
    rescheduled_to_id: Optional[int] = None
    safety_checkin_at: Optional[datetime] = None
    safety_checkout_at: Optional[datetime] = None
    safety_checkout_due_at: Optional[datetime] = None
    safety_buddy_user_id: Optional[int] = None
    safety_overdue_flagged_at: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True

    # Nullable jsonb columns with a non-null list default here. from_attributes
    # hands pydantic an explicit None, which the declared default does NOT
    # cover, so the response 500s with a ResponseValidationError on NULL rows.
    # Coerce None back to [].
    _NULL_DEFAULTS: ClassVar[dict] = {
        "items_brought": [],
        "services_discussed": [],
    }

    @field_validator("items_brought", "services_discussed", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v


class ParentHomeVisitListResponse(BaseModel):
    visits: list[ParentHomeVisitResponse]
    total: int
    limit: int
    offset: int


class HomeVisitSafetyCheckinRequest(StrictInputSchema):
    visit_duration_minutes: int = Field(..., ge=5, le=480)


class HomeVisitSafetyResponse(BaseModel):
    visit_id: int
    safety_checkin_at: Optional[datetime] = None
    safety_checkout_at: Optional[datetime] = None
    safety_checkout_due_at: Optional[datetime] = None
    safety_buddy_user_id: Optional[int] = None
    buddy_warning: Optional[str] = None


class OverdueHomeVisitSummary(BaseModel):
    visit_id: int
    visitor_id: Optional[int] = None
    visitor_name: Optional[str] = None
    safety_buddy_user_id: Optional[int] = None
    safety_buddy_name: Optional[str] = None
    safety_checkin_at: datetime
    safety_checkout_due_at: datetime
    safety_overdue_flagged_at: Optional[datetime] = None
    address: Optional[str] = None
    scheduled_date: date
    minutes_overdue: int


class OverdueHomeVisitListResponse(BaseModel):
    visits: list[OverdueHomeVisitSummary]
    total: int


# ============================================================================
# Dashboard
# ============================================================================

class ParentOnboardingSessionSummary(BaseModel):
    id: int
    patron_id: int
    patron_name: Optional[str] = None
    # Owning staff member -- the Up Next rail scopes by this.
    staff_id: Optional[int] = None
    scheduled_date: datetime
    status: ParentOnboardingStatus


class CareAssignmentSummary(BaseModel):
    id: int
    patron_id: int
    patron_name: Optional[str] = None
    # Owning coordinator -- the Up Next rail scopes by this.
    coordinator_id: Optional[int] = None
    next_check_in_due: Optional[date] = None
    risk_level: RiskLevel


class ParentHomeVisitSummary(BaseModel):
    id: int
    patron_id: int
    patron_name: Optional[str] = None
    # Visiting staff member -- the Up Next rail scopes by this.
    visitor_id: Optional[int] = None
    visitor_name: Optional[str] = None
    scheduled_date: date
    scheduled_time: Optional[str] = None
    purpose: HomeVisitPurpose
    status: HomeVisitStatus


class ParentOnboardingDashboard(BaseModel):
    active_families: int
    upcoming_sessions: int
    overdue_check_ins: int
    active_childcare_sessions: int
    active_connection_groups: int
    pending_enrollments: int
    upcoming_home_visits: int
    recent_sessions: list[ParentOnboardingSessionSummary] = []
    overdue_assignments: list[CareAssignmentSummary] = []
    upcoming_visits: list[ParentHomeVisitSummary] = []


# Forward-ref resolution for HomeVisitRescheduleResponse (declared
# before ParentHomeVisitResponse so its self-references resolve).
HomeVisitRescheduleResponse.model_rebuild()


# ============================================================================
# Component 8: Session follow-ups + referrals
# ============================================================================
#
# All input schemas extend StrictInputSchema (extra=forbid) per the L30
# strict-input convention -- this keeps the OpenAPI contract honest and
# catches typos at request validation time rather than as a silent drop.


class PartnerAgencyBase(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=64)
    agency_type: Optional[str] = Field(None, max_length=64)
    contact_phone: Optional[str] = Field(None, max_length=32)
    contact_email: Optional[str] = Field(None, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    service_area: Optional[str] = Field(None, max_length=255)
    languages_served: list[str] = []
    notes: Optional[str] = None
    is_active: bool = True


class PartnerAgencyResponse(BaseModel):
    id: int
    name: str
    slug: str
    agency_type: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    website_url: Optional[str] = None
    service_area: Optional[str] = None
    languages_served: list[str] = []
    notes: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PartnerAgencyListResponse(BaseModel):
    agencies: list[PartnerAgencyResponse]
    total: int


# ----- Follow-ups -----------------------------------------------------------

class FollowupCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    due_date: date
    priority: str = Field("normal", pattern=r"^(low|normal|high)$")


class FollowupUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None
    status: Optional[str] = Field(
        None, pattern=r"^(open|in_progress|completed|cancelled)$",
    )
    priority: Optional[str] = Field(None, pattern=r"^(low|normal|high)$")


class FollowupComplete(StrictInputSchema):
    completion_note: Optional[str] = None


class FollowupResponse(BaseModel):
    id: int
    session_id: int
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    due_date: date
    status: str
    priority: str
    completed_at: Optional[datetime] = None
    completed_by_id: Optional[int] = None
    completion_note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class FollowupListResponse(BaseModel):
    followups: list[FollowupResponse]
    total: int


# ----- Referrals ------------------------------------------------------------

class ReferralCreate(StrictInputSchema):
    partner_agency_id: Optional[int] = None
    agency_name_freetext: Optional[str] = Field(None, max_length=255)
    purpose: str = Field(..., min_length=1, max_length=255)
    status: str = Field(
        "made",
        pattern=r"^(made|scheduled|completed|declined_by_patron|declined_by_agency)$",
    )
    warm_handoff: bool = False
    patron_consent_to_share: bool = False
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _check_agency_present(self):
        if self.partner_agency_id is None and not self.agency_name_freetext:
            raise ValueError(
                "Either partner_agency_id or agency_name_freetext is required.",
            )
        return self


class ReferralUpdate(StrictInputSchema):
    partner_agency_id: Optional[int] = None
    agency_name_freetext: Optional[str] = Field(None, max_length=255)
    purpose: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(
        None,
        pattern=r"^(made|scheduled|completed|declined_by_patron|declined_by_agency)$",
    )
    warm_handoff: Optional[bool] = None
    patron_consent_to_share: Optional[bool] = None
    notes: Optional[str] = None


class ReferralResponse(BaseModel):
    id: int
    session_id: int
    partner_agency_id: Optional[int] = None
    partner_agency_name: Optional[str] = None
    agency_name_freetext: Optional[str] = None
    purpose: str
    status: str
    warm_handoff: bool
    patron_consent_to_share: bool
    notes: Optional[str] = None
    made_at: datetime
    made_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReferralListResponse(BaseModel):
    referrals: list[ReferralResponse]
    total: int


# ============================================================================
# Component 7b: Home Visit Day Plan (map-aware "Today's route" view)
# ----------------------------------------------------------------------------
# Feature flag: ``home_visit_day_plan_enabled`` (org-wide, default off).
# Endpoints under /api/v1/parent-onboarding/home-visits/day-plan and
# /api/v1/parent-onboarding/home-visit-access-notes.
# ============================================================================


class HomeVisitAccessNotesRead(BaseModel):
    has_steps: bool = False
    has_elevator: bool = False
    multi_floor: bool = False
    dog_on_premises: bool = False
    dog_safety_note: Optional[str] = None
    primary_language: Optional[str] = None
    needs_interpreter: bool = False
    buzzer_or_intercom: Optional[str] = None
    parking_notes: Optional[str] = None
    other_notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class HomeVisitAccessNotesUpsert(StrictInputSchema):
    has_steps: Optional[bool] = None
    has_elevator: Optional[bool] = None
    multi_floor: Optional[bool] = None
    dog_on_premises: Optional[bool] = None
    dog_safety_note: Optional[str] = Field(None, max_length=500)
    primary_language: Optional[str] = Field(None, max_length=20)
    needs_interpreter: Optional[bool] = None
    buzzer_or_intercom: Optional[str] = Field(None, max_length=500)
    parking_notes: Optional[str] = Field(None, max_length=500)
    other_notes: Optional[str] = Field(None, max_length=2000)


class DayPlanLeg(BaseModel):
    drive_minutes: int
    walk_minutes: int
    distance_km: float
    provider: str  # 'osrm' | 'haversine'


class DayPlanStop(BaseModel):
    visit_id: int
    sort_index: int
    scheduled_time: Optional[str] = None
    patron_id: int
    patron_name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    purpose: HomeVisitPurpose
    status: HomeVisitStatus
    access_notes: Optional[HomeVisitAccessNotesRead] = None
    leg_from_previous: Optional[DayPlanLeg] = None
    manual_order: bool = False


class DayPlanResponse(BaseModel):
    date: date
    visitor_id: int
    stops: list[DayPlanStop]
    total_drive_minutes: int = 0
    total_distance_km: float = 0.0
    warnings: list[str] = []


class DayPlanSortPatch(StrictInputSchema):
    sort_index: Optional[int] = Field(None, ge=1, le=100)


class GeocodeManualOverride(StrictInputSchema):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


# ----------------------------------------------------------------------------
# Component 9: Resource handouts (catalog + per-session assignments)
# ----------------------------------------------------------------------------


class ResourceHandoutResponse(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    language: str
    description: Optional[str] = None
    file_url: str
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    preview_thumbnail_url: Optional[str] = None
    tags: list[str] = []
    is_active: bool

    class Config:
        from_attributes = True


class ResourceHandoutListResponse(BaseModel):
    handouts: list[ResourceHandoutResponse]
    total: int


class SessionHandoutCreate(StrictInputSchema):
    resource_handout_id: Optional[int] = None
    community_resource_link_id: Optional[int] = None
    given_at: Optional[datetime] = None
    given_in_language: str = Field(..., min_length=2, max_length=8)
    delivery_method: str = Field(
        "printed",
        pattern=r"^(printed|emailed|linked|given_orally)$",
    )
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _check_exactly_one_target(self):
        has_handout = self.resource_handout_id is not None
        has_link = self.community_resource_link_id is not None
        if not has_handout and not has_link:
            raise ValueError(
                "Either resource_handout_id or community_resource_link_id "
                "is required.",
            )
        if has_handout and has_link:
            raise ValueError(
                "Set exactly one of resource_handout_id or "
                "community_resource_link_id, not both.",
            )
        return self


class SessionHandoutResponse(BaseModel):
    id: int
    session_id: int
    resource_handout_id: Optional[int] = None
    community_resource_link_id: Optional[int] = None
    # Composed: surfaces the handout title or the link name so the FE can
    # render a row without a second round-trip.
    display_title: Optional[str] = None
    given_at: datetime
    given_by_id: Optional[int] = None
    given_by_name: Optional[str] = None
    given_in_language: str
    delivery_method: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionHandoutListResponse(BaseModel):
    handouts: list[SessionHandoutResponse]
    total: int
