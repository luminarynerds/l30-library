# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import ClassVar, List, Optional

from pydantic import BaseModel, Field, field_validator
from .._base import StrictInputSchema

# ============ Board Member Schemas ============


class BoardMemberBase(BaseModel):
    full_name: str = Field(..., max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field("member", max_length=50)
    term_start_date: datetime
    term_end_date: Optional[datetime] = None
    is_current: Optional[bool] = True
    bio: Optional[str] = None
    photo_url: Optional[str] = Field(None, max_length=500)
    public_email: Optional[str] = Field(None, max_length=255)
    office_hours: Optional[str] = None


class BoardMemberCreate(BoardMemberBase, StrictInputSchema):
    pass


class BoardMemberUpdate(StrictInputSchema):
    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, max_length=50)
    term_start_date: Optional[datetime] = None
    term_end_date: Optional[datetime] = None
    is_current: Optional[bool] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = Field(None, max_length=500)
    public_email: Optional[str] = Field(None, max_length=255)
    office_hours: Optional[str] = None


class BoardMemberResponse(BoardMemberBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Board Meeting Schemas ============


class NoticePostingLocation(BaseModel):
    location: str = Field(..., max_length=100)  # e.g., "website", "bulletin_board", "newspaper"
    url: Optional[str] = Field(None, max_length=1000)
    posted_at: Optional[datetime] = None
    notes: Optional[str] = None


class BoardMeetingBase(BaseModel):
    meeting_type: str = Field("regular", max_length=30)
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    scheduled_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=500)
    is_virtual: Optional[bool] = False
    virtual_meeting_url: Optional[str] = Field(None, max_length=1000)
    # Public participation
    public_comment_enabled: Optional[bool] = True
    public_comment_instructions: Optional[str] = None
    accessibility_info: Optional[str] = None
    # Executive session
    has_executive_session: Optional[bool] = False
    executive_session_reason: Optional[str] = None
    # Notice settings
    notice_lead_days_required: Optional[int] = 2


class BoardMeetingCreate(BoardMeetingBase, StrictInputSchema):
    pass


class BoardMeetingUpdate(StrictInputSchema):
    meeting_type: Optional[str] = Field(None, max_length=30)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=500)
    is_virtual: Optional[bool] = None
    virtual_meeting_url: Optional[str] = Field(None, max_length=1000)
    # Public participation
    public_comment_enabled: Optional[bool] = None
    public_comment_instructions: Optional[str] = None
    accessibility_info: Optional[str] = None
    # Executive session
    has_executive_session: Optional[bool] = None
    executive_session_reason: Optional[str] = None
    # Notice settings
    notice_lead_days_required: Optional[int] = None



class AgendaPreviewItem(BaseModel):
    title: str
    item_number: str

    class Config:
        from_attributes = True


class BoardMeetingResponse(BoardMeetingBase):
    id: int
    is_cancelled: Optional[bool] = False
    cancellation_reason: Optional[str] = None
    quorum_met: Optional[bool] = None
    minutes_approved: Optional[bool] = False
    agenda_published_at: Optional[datetime] = None
    agenda_published_by_id: Optional[int] = None
    # Notice compliance fields
    notice_status: Optional[str] = "not_posted"
    notice_posted_at: Optional[datetime] = None
    notice_posted_by_id: Optional[int] = None
    notice_posting_locations: Optional[List[NoticePostingLocation]] = []
    notice_document_id: Optional[int] = None
    created_at: datetime | None = None
    # Legacy production rows can have NULL creator IDs; keep responses resilient.
    created_by_id: Optional[int] = None
    updated_at: Optional[datetime] = None
    agenda_preview: List[AgendaPreviewItem] = []

    class Config:
        from_attributes = True


class BoardMeetingListItem(BoardMeetingResponse):
    # Relative deep link to the detail page's minutes section when approved minutes exist.
    minutes_url: Optional[str] = None
    # Whatever is on BoardMinutes.recording_url (typically an external Zoom/YouTube URL).
    recording_url: Optional[str] = None
    # No agenda-packet FK on BoardMeeting today — always None until a follow-up adds one
    # (or surfaces it via the polymorphic BoardDocument relationship).
    agenda_packet_url: Optional[str] = None


# ============ Meeting Search Schemas ============


class MeetingSearchParams(BaseModel):
    q: Optional[str] = Field(None, description="Full-text search across title, description, location, agenda items")
    meeting_type: Optional[str] = Field(None, description="Filter by meeting type (regular, special, emergency, etc.)")
    status: Optional[str] = Field(None, description="Filter by status: scheduled, completed, cancelled")
    date_from: Optional[str] = Field(None, description="Meetings on or after this date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="Meetings on or before this date (YYYY-MM-DD)")
    has_recording: Optional[bool] = Field(None, description="Only meetings with a recording URL")
    committee_id: Optional[int] = Field(None, description="Filter by committee ID")
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)


class MeetingSearchResponse(BaseModel):
    results: List["BoardMeetingResponse"]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True


# ============ Public Meeting Notice Schemas ============


class NoticeGenerateRequest(StrictInputSchema):
    include_agenda: bool = True
    include_accessibility_info: bool = True
    custom_header: Optional[str] = None
    custom_footer: Optional[str] = None


class NoticePostRequest(StrictInputSchema):
    location: str = Field(..., max_length=100)  # e.g., "website", "bulletin_board", "newspaper"
    url: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = None


class NoticeComplianceStatus(BaseModel):
    meeting_id: int
    meeting_title: str
    scheduled_date: datetime
    notice_status: str
    notice_posted_at: Optional[datetime] = None
    notice_lead_days_required: int
    actual_lead_days: Optional[float] = None
    is_compliant: bool
    compliance_issues: List[str] = []
    posting_locations: List[NoticePostingLocation] = []
    agenda_published: bool = False
    has_accessibility_info: bool = False


class NoticeResponse(BaseModel):
    meeting_id: int
    notice_content: str
    generated_at: datetime
    includes_agenda: bool
    includes_accessibility_info: bool


# ============ Agenda Item Schemas ============


class AgendaItemBase(BaseModel):
    item_number: str = Field(..., max_length=20)
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    presenter: Optional[str] = Field(None, max_length=200)
    estimated_duration_minutes: Optional[int] = None
    sort_order: int = 0
    requires_action: Optional[bool] = False
    action_type: Optional[str] = Field(None, max_length=100)


class AgendaItemCreate(AgendaItemBase, StrictInputSchema):
    meeting_id: int


class AgendaItemUpdate(StrictInputSchema):
    item_number: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    presenter: Optional[str] = Field(None, max_length=200)
    estimated_duration_minutes: Optional[int] = None
    sort_order: Optional[int] = None
    requires_action: Optional[bool] = None
    action_type: Optional[str] = Field(None, max_length=100)
    action_taken: Optional[str] = None
    vote_result: Optional[str] = Field(None, max_length=200)


class AgendaItemResponse(AgendaItemBase):
    id: int
    meeting_id: int
    action_taken: Optional[str] = None
    vote_result: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Board Minutes Schemas ============


class BoardMinutesBase(BaseModel):
    status: str = Field("not_started", max_length=50)
    sections: Optional[List] = []
    meeting_called_to_order_at: Optional[datetime] = None
    meeting_adjourned_at: Optional[datetime] = None
    members_present: Optional[List] = []
    members_absent: Optional[List] = []
    members_excused: Optional[List] = []
    guests_present: Optional[List] = []
    quorum_met: Optional[bool] = None
    quorum_count: Optional[str] = None
    recording_url: Optional[str] = None
    notes: Optional[str] = None
    plain_language_summary: Optional[str] = None


class BoardMinutesCreate(BoardMinutesBase, StrictInputSchema):
    meeting_id: int


class BoardMinutesUpdate(BoardMinutesBase, StrictInputSchema):
    pass


class BoardMinutesResponse(BoardMinutesBase):
    id: int
    meeting_id: int
    approved: Optional[bool] = False
    approved_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    approval_vote_result: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Board Document Schemas ============


class BoardDocumentBase(BaseModel):
    document_type: str = Field(..., max_length=50)
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    filename: str = Field(..., max_length=500)
    file_path: str = Field(..., max_length=1000)
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = Field(None, max_length=100)
    is_public: Optional[bool] = True


class BoardDocumentCreate(BoardDocumentBase, StrictInputSchema):
    meeting_id: Optional[int] = None


class BoardDocumentUpdate(StrictInputSchema):
    document_type: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    is_public: Optional[bool] = None


class BoardDocumentResponse(BoardDocumentBase):
    id: int
    meeting_id: Optional[int] = None
    status: str
    published_date: Optional[datetime] = None
    published_by_id: Optional[int] = None
    view_count: int | None = 0
    download_count: int | None = 0
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Document Version Schemas ============


class DocumentVersionBase(BaseModel):
    file_url: str = Field(..., max_length=1000)
    file_size: Optional[int] = None
    file_type: Optional[str] = Field(None, max_length=100)
    change_notes: Optional[str] = None


class DocumentVersionCreate(DocumentVersionBase, StrictInputSchema):
    pass


class DocumentVersionResponse(DocumentVersionBase):
    id: int
    document_id: int
    version_number: int
    created_by_id: Optional[int] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ Board Vote Schemas ============


class BoardVoteBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: str
    vote_type: str = Field("simple_majority", max_length=50)
    opens_at: datetime
    closes_at: datetime
    quorum_required: int = 4


class BoardVoteCreate(BoardVoteBase, StrictInputSchema):
    meeting_id: Optional[int] = None


class BoardVoteUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    vote_type: Optional[str] = Field(None, max_length=50)
    opens_at: Optional[datetime] = None
    closes_at: Optional[datetime] = None
    quorum_required: Optional[int] = None


class BoardVoteResponse(BoardVoteBase):
    id: int
    meeting_id: Optional[int] = None
    status: str
    passed: Optional[bool] = None
    final_tally_yes: int = 0
    final_tally_no: int = 0
    final_tally_abstain: int = 0
    final_tally_recusal: int = 0
    closed_at_actual: Optional[datetime] = None
    closed_by_id: Optional[int] = None
    created_at: datetime | None = None
    created_by_id: Optional[int] = None
    updated_at: Optional[datetime] = None

    # The tally columns are nullable in the DB (default 0, no NOT NULL); seeded/
    # legacy rows hold NULL, and from_attributes hands pydantic the explicit None,
    # which the declared default does NOT cover -> ResponseValidationError 500.
    # Coerce None back to 0 at the boundary. created_by_id is a nullable audit FK
    # (AuditMixin) and is handled by the Optional type above, not coercion.
    _NULL_DEFAULTS: ClassVar[dict] = {
        "final_tally_yes": 0,
        "final_tally_no": 0,
        "final_tally_abstain": 0,
        "final_tally_recusal": 0,
    }

    @field_validator(
        "final_tally_yes", "final_tally_no", "final_tally_abstain",
        "final_tally_recusal",
        mode="before",
    )
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


# ============ Vote Cast Schemas ============


class VoteCastCreate(StrictInputSchema):
    choice: str = Field(..., pattern="^(yes|no|abstain|recusal)$")
    comment: Optional[str] = Field(None, max_length=1000)


class VoteCastResponse(BaseModel):
    id: int
    vote_id: int
    board_member_id: int
    choice: str
    comment: Optional[str] = None
    cast_at: datetime
    # Advisory-only: set post-validation in cast_vote() when the voting
    # member has a current COI disclosure whose keywords overlap this vote's
    # title/description. Not persisted -- response-only nudge toward recusal.
    coi_warning: Optional[str] = None

    class Config:
        from_attributes = True


# ============ Meeting Attendance Schemas ============


class AttendanceBase(BaseModel):
    rsvp_status: str = Field("no_response", max_length=30)
    rsvp_notes: Optional[str] = None
    is_voting_member: bool = True
    is_guest: bool = False
    guest_affiliation: Optional[str] = Field(None, max_length=200)


class AttendanceCreate(AttendanceBase, StrictInputSchema):
    user_id: int


class AttendanceUpdate(StrictInputSchema):
    rsvp_status: Optional[str] = Field(None, max_length=30)
    rsvp_notes: Optional[str] = None
    attendance_status: Optional[str] = Field(None, max_length=30)
    attended_remotely: Optional[bool] = None
    remote_connection_method: Optional[str] = Field(None, max_length=100)
    absence_reason: Optional[str] = None


class AttendanceCheckIn(BaseModel):
    attendance_status: str = Field("present", pattern="^(present|tardy|left_early)$")
    attended_remotely: bool = False
    remote_connection_method: Optional[str] = Field(None, max_length=100)


class AttendanceResponse(AttendanceBase):
    id: int
    meeting_id: int
    user_id: int
    attendance_status: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    attended_remotely: bool = False
    remote_connection_method: Optional[str] = None
    absence_reason: Optional[str] = None
    rsvp_at: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Action Item Schemas ============


class ActionItemBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    assigned_to_name: Optional[str] = Field(None, max_length=200)
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")
    due_date: Optional[datetime] = None
    requires_board_update: bool = False


class ActionItemCreate(ActionItemBase, StrictInputSchema):
    agenda_item_id: Optional[int] = None
    assigned_to_id: Optional[int] = None


class ActionItemUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = Field(None, max_length=200)
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    due_date: Optional[datetime] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    requires_board_update: Optional[bool] = None


class ActionItemStatusUpdate(StrictInputSchema):
    status: str = Field(..., pattern="^(not_started|in_progress|completed|cancelled|on_hold)$")
    notes: Optional[str] = None


class ActionItemResponse(ActionItemBase):
    id: int
    meeting_id: int
    agenda_item_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    assigned_by_id: Optional[int] = None
    status: str
    progress_percentage: int = 0
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    board_update_provided: bool = False
    board_update_meeting_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # board_update_provided is nullable in the DB (default False, no NOT NULL);
    # legacy rows hold NULL, which from_attributes passes through as None and
    # 500s the response. Coerce None back to False at the boundary.
    @field_validator("board_update_provided", mode="before")
    @classmethod
    def _coerce_null_board_update_provided(cls, v):
        if v is None:
            return False
        return v

    class Config:
        from_attributes = True


# ============ Meeting Brief Schemas ============


class BriefResponse(BaseModel):
    id: int
    meeting_id: int
    status: str
    brief_content: Optional[str] = None
    key_discussion_points: Optional[List] = None
    recommended_questions: Optional[List] = None
    background_context: Optional[str] = None
    model_used: Optional[str] = None
    generation_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True

    @classmethod
    def from_orm_brief(cls, brief):
        return cls(
            id=brief.id,
            meeting_id=brief.meeting_id,
            status=brief.status,
            brief_content=brief.executive_summary,
            key_discussion_points=brief.agenda_highlights,
            recommended_questions=brief.recommended_prep,
            background_context=brief.background_context,
            model_used=brief.ai_model_used,
            generation_time_ms=brief.generation_time_ms,
            error_message=brief.error_message,
            created_at=brief.created_at,
        )


# ============ Committee Schemas ============


class CommitteeBase(BaseModel):
    name: str = Field(..., max_length=200)
    committee_type: str = Field("standing", max_length=30)
    status: str = Field("active", max_length=30)
    description: Optional[str] = None
    purpose: Optional[str] = None
    responsibilities: Optional[str] = None
    meeting_schedule: Optional[str] = Field(None, max_length=500)
    default_meeting_location: Optional[str] = Field(None, max_length=500)
    min_members: int = 3
    max_members: Optional[int] = None
    quorum_requirement: int = 2
    chair_term_months: Optional[int] = 12
    member_term_months: Optional[int] = 24
    is_public: Optional[bool] = True
    public_description: Optional[str] = None


class CommitteeCreate(CommitteeBase, StrictInputSchema):
    parent_committee_id: Optional[int] = None
    established_date: Optional[datetime] = None


class CommitteeUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, max_length=200)
    committee_type: Optional[str] = Field(None, max_length=30)
    status: Optional[str] = Field(None, max_length=30)
    description: Optional[str] = None
    purpose: Optional[str] = None
    responsibilities: Optional[str] = None
    meeting_schedule: Optional[str] = Field(None, max_length=500)
    default_meeting_location: Optional[str] = Field(None, max_length=500)
    min_members: Optional[int] = None
    max_members: Optional[int] = None
    quorum_requirement: Optional[int] = None
    chair_term_months: Optional[int] = None
    member_term_months: Optional[int] = None
    is_public: Optional[bool] = None
    public_description: Optional[str] = None
    dissolution_date: Optional[datetime] = None
    dissolution_reason: Optional[str] = None


class CommitteeResponse(CommitteeBase):
    id: int
    parent_committee_id: Optional[int] = None
    established_date: Optional[datetime] = None
    dissolution_date: Optional[datetime] = None
    dissolution_reason: Optional[str] = None
    created_at: datetime | None = None
    created_by_id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CommitteeMemberBase(BaseModel):
    role: str = Field("member", max_length=30)
    appointed_date: datetime
    term_end_date: Optional[datetime] = None
    appointment_notes: Optional[str] = None


class CommitteeMemberCreate(CommitteeMemberBase, StrictInputSchema):
    committee_id: int
    board_member_id: int


class CommitteeMemberUpdate(StrictInputSchema):
    role: Optional[str] = Field(None, max_length=30)
    term_end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    appointment_notes: Optional[str] = None


class CommitteeMemberRemove(BaseModel):
    removal_reason: Optional[str] = None


class CommitteeMemberResponse(CommitteeMemberBase):
    id: int
    committee_id: int
    board_member_id: int
    is_active: bool = True
    removed_date: Optional[datetime] = None
    removal_reason: Optional[str] = None
    removed_by_id: Optional[int] = None
    created_at: datetime | None = None
    created_by_id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True




class CommitteeMemberNested(BaseModel):
    id: int
    board_member_id: int
    board_member_name: str
    board_member_position: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class CommitteeWithMembersResponse(CommitteeResponse):
    members: List["CommitteeMemberNested"] = []

    class Config:
        from_attributes = True

# ============ Motion Schemas ============


class MotionBase(BaseModel):
    motion_type: str = Field("main", max_length=30)
    motion_number: Optional[str] = Field(None, max_length=50)
    title: str = Field(..., max_length=500)
    motion_text: str
    rationale: Optional[str] = None
    plain_language_summary: Optional[str] = None


class MotionCreate(MotionBase, StrictInputSchema):
    meeting_id: int
    moved_by_id: Optional[int] = None
    parent_motion_id: Optional[int] = None
    amended_text: Optional[str] = None


class MotionUpdate(StrictInputSchema):
    motion_number: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=500)
    motion_text: Optional[str] = None
    rationale: Optional[str] = None
    plain_language_summary: Optional[str] = None
    discussion_notes: Optional[str] = None
    outcome_notes: Optional[str] = None


class MotionSecond(BaseModel):
    seconded_by_id: int


class MotionRefer(BaseModel):
    referred_to_committee_id: int
    referred_notes: Optional[str] = None


class MotionTable(BaseModel):
    tabled_until: Optional[datetime] = None
    tabled_reason: Optional[str] = None


class MotionWithdraw(BaseModel):
    withdrawn_reason: Optional[str] = None


class MotionResponse(MotionBase):
    id: int
    meeting_id: int
    status: str
    parent_motion_id: Optional[int] = None
    amended_text: Optional[str] = None
    moved_by_id: Optional[int] = None
    moved_at: datetime
    seconded_by_id: Optional[int] = None
    seconded_at: Optional[datetime] = None
    discussion_opened_at: Optional[datetime] = None
    discussion_closed_at: Optional[datetime] = None
    discussion_notes: Optional[str] = None
    vote_id: Optional[int] = None
    vote_called_at: Optional[datetime] = None
    outcome_recorded_at: Optional[datetime] = None
    outcome_notes: Optional[str] = None
    referred_to_committee_id: Optional[int] = None
    referred_at: Optional[datetime] = None
    referred_notes: Optional[str] = None
    tabled_at: Optional[datetime] = None
    tabled_until: Optional[datetime] = None
    tabled_reason: Optional[str] = None
    withdrawn_at: Optional[datetime] = None
    withdrawn_reason: Optional[str] = None
    created_at: datetime | None = None
    created_by_id: Optional[int] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Resolution Schemas ============


class ResolutionBase(BaseModel):
    resolution_number: str = Field(..., max_length=50)
    title: str = Field(..., max_length=500)
    preamble: Optional[str] = None
    resolution_text: str
    summary: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = []
    is_public: Optional[bool] = True


class ResolutionCreate(ResolutionBase, StrictInputSchema):
    originating_motion_id: Optional[int] = None
    meeting_id: Optional[int] = None
    committee_id: Optional[int] = None
    proposed_by_id: Optional[int] = None
    proposed_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class ResolutionUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=500)
    preamble: Optional[str] = None
    resolution_text: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class ResolutionAdopt(BaseModel):
    adopted_vote_id: int
    effective_date: Optional[datetime] = None


class ResolutionSupersede(BaseModel):
    supersedes_resolution_id: int


class ResolutionRescind(BaseModel):
    rescinded_by_motion_id: int
    rescinded_reason: Optional[str] = None


class ResolutionResponse(ResolutionBase):
    id: int
    status: str
    originating_motion_id: Optional[int] = None
    meeting_id: Optional[int] = None
    committee_id: Optional[int] = None
    proposed_date: Optional[datetime] = None
    proposed_by_id: Optional[int] = None
    adopted_date: Optional[datetime] = None
    adopted_vote_id: Optional[int] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    supersedes_resolution_id: Optional[int] = None
    superseded_by_resolution_id: Optional[int] = None
    superseded_date: Optional[datetime] = None
    rescinded_date: Optional[datetime] = None
    rescinded_by_motion_id: Optional[int] = None
    rescinded_reason: Optional[str] = None
    published_date: Optional[datetime] = None
    published_by_id: Optional[int] = None
    attachment_document_ids: Optional[List[int]] = []
    created_at: datetime | None = None
    created_by_id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Public Comment Schemas ============


class PublicCommentBase(BaseModel):
    comment_type: str = Field("written", max_length=30)
    commenter_name: str = Field(..., max_length=200)
    commenter_email: Optional[str] = Field(None, max_length=255)
    commenter_phone: Optional[str] = Field(None, max_length=50)
    commenter_address: Optional[str] = None
    organization: Optional[str] = Field(None, max_length=200)
    is_resident: Optional[bool] = None
    subject: Optional[str] = Field(None, max_length=500)
    comment_text: str


class PublicCommentCreate(PublicCommentBase, StrictInputSchema):
    meeting_id: int
    agenda_item_id: Optional[int] = None


class PublicCommentUpdate(StrictInputSchema):
    subject: Optional[str] = Field(None, max_length=500)
    comment_text: Optional[str] = None
    include_in_minutes: Optional[bool] = None
    redact_contact_info: Optional[bool] = None


class PublicCommentModerate(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    moderation_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class PublicCommentReadIntoRecord(BaseModel):
    reading_notes: Optional[str] = None
    time_allocated_seconds: Optional[int] = None


class PublicCommentStaffResponse(BaseModel):
    staff_response: str


class PublicCommentResponse(PublicCommentBase):
    id: int
    meeting_id: int
    agenda_item_id: Optional[int] = None
    status: str
    submitted_at: datetime
    moderated_by_id: Optional[int] = None
    moderated_at: Optional[datetime] = None
    moderation_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    read_at: Optional[datetime] = None
    read_by_id: Optional[int] = None
    reading_notes: Optional[str] = None
    time_allocated_seconds: Optional[int] = None
    speaker_order: Optional[int] = None
    include_in_minutes: bool = True
    redact_contact_info: bool = True
    staff_response: Optional[str] = None
    staff_response_by_id: Optional[int] = None
    staff_response_at: Optional[datetime] = None
    board_response: Optional[str] = None
    board_response_at: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Public-facing comment submission (limited fields exposed)
class PublicCommentSubmit(StrictInputSchema):
    meeting_id: int
    agenda_item_id: Optional[int] = None
    commenter_name: str = Field(..., max_length=200)
    commenter_email: Optional[str] = Field(None, max_length=255)
    commenter_phone: Optional[str] = Field(None, max_length=50)
    organization: Optional[str] = Field(None, max_length=200)
    is_resident: Optional[bool] = None
    subject: Optional[str] = Field(None, max_length=500)
    comment_text: str = Field(..., max_length=5000)


# ============ Public Comment Period Schemas ============


class CommentPeriodBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = None
    opens_at: datetime
    closes_at: datetime
    scheduled_start_time: Optional[datetime] = None
    max_comments: Optional[int] = None
    max_speakers: Optional[int] = None
    time_per_speaker_seconds: int = 180
    allow_written: bool = True
    allow_in_person: bool = True
    allow_virtual: bool = True
    require_advance_signup: bool = False


class CommentPeriodCreate(CommentPeriodBase, StrictInputSchema):
    meeting_id: int
    agenda_item_id: Optional[int] = None


class CommentPeriodUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = None
    opens_at: Optional[datetime] = None
    closes_at: Optional[datetime] = None
    scheduled_start_time: Optional[datetime] = None
    max_comments: Optional[int] = None
    max_speakers: Optional[int] = None
    time_per_speaker_seconds: Optional[int] = None
    allow_written: Optional[bool] = None
    allow_in_person: Optional[bool] = None
    allow_virtual: Optional[bool] = None
    require_advance_signup: Optional[bool] = None
    is_active: Optional[bool] = None


class CommentPeriodResponse(CommentPeriodBase):
    id: int
    meeting_id: int
    agenda_item_id: Optional[int] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime | None = None
    created_by_id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Board Report Schemas ============


class BoardReportBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    report_period_start: datetime
    report_period_end: datetime
    comparison_period_start: Optional[datetime] = None
    comparison_period_end: Optional[datetime] = None


class BoardReportCreate(BoardReportBase, StrictInputSchema):
    template_id: Optional[int] = None
    recipient_emails: Optional[List[str]] = None


class BoardReportGenerateRequest(StrictInputSchema):
    start_date: datetime
    end_date: datetime
    template_id: Optional[int] = None
    include_comparison: bool = True
    export_format: str = Field("both", pattern="^(powerpoint|pdf|both)$")
    send_to_emails: Optional[List[str]] = None


class BoardReportResponse(BoardReportBase):
    id: int
    status: str
    frequency: str
    executive_summary: Optional[str] = None
    key_metrics: Optional[dict] = None
    narrative_prompts: Optional[dict] = None
    stats_snapshot: Optional[dict] = None
    file_powerpoint: Optional[bool] = None
    file_pdf: Optional[bool] = None
    format_generated: str
    email_sent: Optional[bool] = False
    email_sent_at: Optional[datetime] = None
    created_at: datetime | None = None
    generated_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("file_powerpoint", "file_pdf", mode="before")
    @classmethod
    def _bytes_to_presence_bool(cls, v):
        # Model columns are BYTEA; the response should expose only a "file present?" flag.
        if isinstance(v, (bytes, bytearray, memoryview)):
            return len(v) > 0
        return v

    class Config:
        from_attributes = True


class BoardReportTemplateBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    include_sections: dict  # {circulation: bool, financial: bool, ...}
    colors: Optional[dict] = None
    logo_url: Optional[str] = Field(None, max_length=1000)
    branding: Optional[dict] = None
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    chart_config: Optional[dict] = None


class BoardReportTemplateCreate(BoardReportTemplateBase, StrictInputSchema):
    pass


class BoardReportTemplateUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    include_sections: Optional[dict] = None
    colors: Optional[dict] = None
    logo_url: Optional[str] = Field(None, max_length=1000)
    branding: Optional[dict] = None
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    chart_config: Optional[dict] = None


class BoardReportTemplateResponse(BoardReportTemplateBase):
    id: int
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BoardReportScheduleBase(BaseModel):
    name: str = Field(..., max_length=255)
    is_active: bool = True
    frequency: str = Field(..., pattern="^(monthly|quarterly|annually)$")
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    time_of_day: Optional[str] = Field(None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    template_id: Optional[int] = None
    recipient_user_ids: Optional[List[int]] = None
    recipient_emails: Optional[List[str]] = None
    report_format: str = Field("both", pattern="^(powerpoint|pdf|both)$")
    include_comparison: bool = True


class BoardReportScheduleCreate(BoardReportScheduleBase, StrictInputSchema):
    pass


class BoardReportScheduleUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    frequency: Optional[str] = Field(None, pattern="^(monthly|quarterly|annually)$")
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    time_of_day: Optional[str] = Field(None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    template_id: Optional[int] = None
    recipient_user_ids: Optional[List[int]] = None
    recipient_emails: Optional[List[str]] = None
    report_format: Optional[str] = Field(None, pattern="^(powerpoint|pdf|both)$")
    include_comparison: Optional[bool] = None


class BoardReportScheduleResponse(BoardReportScheduleBase):
    id: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Board Audit Log Schemas ============


class BoardAuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: int
    meeting_id: Optional[int] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Board Recusal Schemas ============


class RecusalDeclareRequest(StrictInputSchema):
    vote_id: Optional[int] = None
    motion_id: Optional[int] = None
    topic_description: Optional[str] = None
    reason: str = Field(..., min_length=10, max_length=2000)


class RecusalWithdrawRequest(StrictInputSchema):
    reason: str = Field(..., min_length=10, max_length=2000)


class RecusalResponse(BaseModel):
    id: int
    board_member_id: int
    vote_id: Optional[int] = None
    motion_id: Optional[int] = None
    topic_description: Optional[str] = None
    reason: str
    declared_at: datetime
    is_active: bool
    withdrawn_at: Optional[datetime] = None
    withdrawn_reason: Optional[str] = None

    class Config:
        from_attributes = True


# ============ Board Minutes Amendment Schemas ============


class MinutesAmendmentCreate(StrictInputSchema):
    amendment_text: str = Field(..., min_length=10)
    section_title: Optional[str] = Field(None, max_length=200)
    original_text: Optional[str] = None
    amendment_reason: str = Field(..., min_length=10)
    amendment_vote_result: str = Field(..., max_length=200)


class MinutesAmendmentResponse(BaseModel):
    id: int
    minutes_id: int
    amendment_text: str
    section_title: Optional[str] = None
    original_text: Optional[str] = None
    amendment_reason: str
    amendment_vote_result: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# ============ Board Records Retention Schemas ============


class RetentionScheduleResponse(BaseModel):
    id: int
    record_type: str
    retention_years: Optional[int] = None
    is_permanent: bool
    description: Optional[str] = None
    legal_authority: Optional[str] = None

    class Config:
        from_attributes = True


class RetentionScheduleUpdate(StrictInputSchema):
    retention_years: Optional[int] = None
    is_permanent: bool = True
    description: Optional[str] = None
    legal_authority: Optional[str] = None


class LegalHoldCreate(StrictInputSchema):
    title: str = Field(..., max_length=500)
    reason: str = Field(..., min_length=10)
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None


class LegalHoldReleaseRequest(StrictInputSchema):
    reason: str = Field(..., min_length=10)


class LegalHoldResponse(BaseModel):
    id: int
    title: str
    reason: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    placed_by_id: int
    placed_at: datetime
    is_active: bool
    released_at: Optional[datetime] = None
    release_reason: Optional[str] = None

    class Config:
        from_attributes = True


# ============ State Compliance Profile Schemas ============


class ComplianceProfileResponse(BaseModel):
    id: int
    state_code: str
    state_name: str
    is_active: bool
    notice_lead_hours: int
    emergency_notice_rule: Optional[str] = None
    open_meeting_law_citation: Optional[str] = None
    permitted_exec_session_reasons: Optional[List] = []
    public_records_law_name: Optional[str] = None
    public_records_response_days: Optional[int] = None
    public_records_law_citation: Optional[str] = None
    minutes_retention: Optional[str] = "permanent"
    resolution_retention: Optional[str] = "permanent"

    class Config:
        from_attributes = True


class ComplianceProfileCreate(StrictInputSchema):
    state_code: str = Field(..., min_length=2, max_length=2)
    state_name: str = Field(..., max_length=100)
    notice_lead_hours: int = Field(..., ge=1)
    emergency_notice_rule: Optional[str] = None
    open_meeting_law_citation: Optional[str] = None
    permitted_exec_session_reasons: Optional[List] = []
    public_records_law_name: Optional[str] = None
    public_records_response_days: Optional[int] = None
    public_records_law_citation: Optional[str] = None
    minutes_retention: str = "permanent"
    resolution_retention: str = "permanent"


class ComplianceProfileUpdate(StrictInputSchema):
    notice_lead_hours: Optional[int] = Field(None, ge=1)
    emergency_notice_rule: Optional[str] = None
    open_meeting_law_citation: Optional[str] = None
    permitted_exec_session_reasons: Optional[List] = None
    public_records_law_name: Optional[str] = None
    public_records_response_days: Optional[int] = None
    public_records_law_citation: Optional[str] = None
    minutes_retention: Optional[str] = None
    resolution_retention: Optional[str] = None


# ============ Board COI Disclosure Schemas ============


class COIDisclosureCreate(StrictInputSchema):
    fiscal_year: str = Field(..., max_length=10)
    disclosure_text: str = Field(..., min_length=20)
    categories: List[str] = []
    keywords: List[str] = []
    attestation_statement: str = Field(..., min_length=20, max_length=1000)


class COIDisclosureResponse(BaseModel):
    id: int
    board_member_id: int
    fiscal_year: str
    disclosure_text: str
    categories: List[str] = []
    keywords: List[str] = []
    attested_at: datetime
    attestation_statement: str
    is_current: bool
    superseded_at: Optional[datetime] = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class COIComplianceStatus(BaseModel):
    fiscal_year: str
    total_members: int
    members_with_disclosure: int
    members_missing_disclosure: List[dict] = []
