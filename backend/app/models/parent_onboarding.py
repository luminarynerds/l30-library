# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, Float, Index,
    Integer, Numeric, String, Text, ForeignKey, UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


# ============================================================================
# Enums
# ============================================================================

class ParentOnboardingStatus(StrEnum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class CareAssignmentStatus(StrEnum):
    active = "active"
    paused = "paused"
    completed = "completed"
    transferred = "transferred"


class CheckInFrequency(StrEnum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class CareCheckInType(StrEnum):
    phone = "phone"
    in_person = "in_person"
    video = "video"
    text = "text"


class ChildcareSessionStatus(StrEnum):
    available = "available"
    full = "full"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ChildcareRegistrationStatus(StrEnum):
    registered = "registered"
    checked_in = "checked_in"
    checked_out = "checked_out"
    no_show = "no_show"
    cancelled = "cancelled"


class ConnectionGroupType(StrEnum):
    first_time_parents = "first_time_parents"
    teen_parents = "teen_parents"
    single_parents = "single_parents"
    postpartum_support = "postpartum_support"
    general = "general"
    support = "support"
    education = "education"
    activity = "activity"


class GroupMemberStatus(StrEnum):
    active = "active"
    inactive = "inactive"
    waitlisted = "waitlisted"
    pending_approval = "pending_approval"
    denied = "denied"


class MeetingFrequency(StrEnum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"


class EnrollmentFacilitationStatus(StrEnum):
    identified = "identified"
    contacted = "contacted"
    application_started = "application_started"
    application_submitted = "application_submitted"
    enrolled = "enrolled"
    denied = "denied"
    withdrawn = "withdrawn"


class HomeVisitPurpose(StrEnum):
    intake = "intake"
    resource_delivery = "resource_delivery"
    check_in = "check_in"
    service_enrollment = "service_enrollment"
    follow_up = "follow_up"


class HomeVisitStatus(StrEnum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    rescheduled = "rescheduled"


# ============================================================================
# Component 1: Welcome Onboarding Sessions
# ============================================================================

class ParentOnboardingSession(Base, TimestampMixin):
    __tablename__ = "parent_onboarding_sessions"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_id = Column(Integer, nullable=False, index=True)

    status = Column(
        String(50),
        default=ParentOnboardingStatus.scheduled,
        nullable=False,
        index=True,
    )

    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    baby_age_months = Column(Integer, nullable=True)
    languages_spoken = Column(ARRAY(String), default=list)
    family_situation_notes = Column(Text, nullable=True)  # Staff-only, sensitive
    needs_identified = Column(JSONB, default=list)
    services_referred = Column(JSONB, default=list)

    welcome_packet_id = Column(Integer, ForeignKey("welcome_packets.id", ondelete="SET NULL"), nullable=True)

    patron = relationship("User", foreign_keys=[patron_id])
    staff = relationship("User", foreign_keys=[staff_id])

    __table_args__ = (
        Index("idx_parent_session_patron_status", "patron_id", "status"),
        Index("idx_parent_session_branch_scheduled", "branch_id", "scheduled_at"),
    )


# ============================================================================
# Component 2: Care Coordinator
# ============================================================================

class CareCoordinatorAssignment(Base, TimestampMixin):
    __tablename__ = "care_coordinator_assignments"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    coordinator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_session_id = Column(Integer, ForeignKey("parent_onboarding_sessions.id", ondelete="SET NULL"), nullable=True)

    status = Column(
        String(50),
        default=CareAssignmentStatus.active,
        nullable=False,
        index=True,
    )

    check_in_frequency = Column(
        String(50),
        default=CheckInFrequency.biweekly,
        nullable=False,
    )

    risk_level = Column(
        String(50),
        default=RiskLevel.low,
        nullable=False,
    )

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)  # Staff-only

    patron = relationship("User", foreign_keys=[patron_id])
    coordinator = relationship("User", foreign_keys=[coordinator_id])
    parent_session = relationship("ParentOnboardingSession")
    check_ins = relationship("CareCoordinatorCheckIn", back_populates="assignment")

    __table_args__ = (
        Index("idx_care_assignment_coordinator_status", "coordinator_id", "status"),
    )


class CareCoordinatorCheckIn(Base, TimestampMixin):
    __tablename__ = "care_coordinator_check_ins"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("care_coordinator_assignments.id", ondelete="CASCADE"), nullable=False, index=True)

    check_in_type = Column(
        String(50),
        nullable=False,
    )

    scheduled_date = Column(Date, nullable=False)
    completed_date = Column(Date, nullable=True)
    mood_assessment = Column(Integer, nullable=True)  # 1-5 scale
    concerns_raised = Column(Text, nullable=True)  # Staff-only, sensitive
    actions_taken = Column(Text, nullable=True)
    follow_up_needed = Column(Boolean, default=False, nullable=False)
    next_check_in_date = Column(Date, nullable=True)

    assignment = relationship("CareCoordinatorAssignment", back_populates="check_ins")

    __table_args__ = (
        Index("idx_check_in_scheduled", "assignment_id", "scheduled_date"),
    )


# ============================================================================
# Component 3: Resource Guide (Hybrid CMS/i18n)
# ============================================================================

class ParentResourceGuideSection(Base, TimestampMixin):
    __tablename__ = "parent_resource_guide_sections"

    id = Column(Integer, primary_key=True, index=True)
    title_key = Column(String(100), nullable=False)  # i18n key reference
    icon = Column(String(50), nullable=True)  # Icon name for display
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    branch_id = Column(Integer, nullable=True, index=True)  # NULL = global, set = branch-specific

    items = relationship("ParentResourceGuideItem", back_populates="section", order_by="ParentResourceGuideItem.display_order")

    __table_args__ = (
        Index("idx_guide_section_branch_active", "branch_id", "is_active"),
    )


class ParentResourceGuideItem(Base, TimestampMixin):
    __tablename__ = "parent_resource_guide_items"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("parent_resource_guide_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    contact_info = Column(String(300), nullable=True)
    url = Column(String(500), nullable=True)
    languages = Column(ARRAY(String), default=list)
    # Multilingual variants.
    # Per-language overrides of title/description. Shape:
    #   {"es": {"title": "...", "description": "..."}, "so": {...}}
    # Empty {} on existing rows is intentional -- API falls back to the
    # source-language columns when no translation exists for the requested
    # lang code. `languages` (above) advertises *availability* of the
    # real-world resource; `translations` carries library-curated copy.
    translations = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    display_order = Column(Integer, default=0, nullable=False)

    # Verification trail.
    # NULL on existing rows is intentional: rendered as "Not yet re-verified"
    # and treated as stale. updated_at (from TimestampMixin) mutates on any
    # edit, including typo fixes, so it cannot stand in for "verified".
    last_verified_at = Column(DateTime(timezone=True), nullable=True, index=True)
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    section = relationship("ParentResourceGuideSection", back_populates="items")
    verified_by = relationship("User", foreign_keys=[verified_by_id], lazy="joined")
    flags = relationship(
        "ParentResourceGuideFlag",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="ParentResourceGuideFlag.created_at.desc()",
    )


class ResourceGuideFlagStatus(StrEnum):
    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


class ResourceGuideFlagReason(StrEnum):
    disconnected_phone = "disconnected_phone"
    wrong_address = "wrong_address"
    eligibility_changed = "eligibility_changed"
    closed_permanently = "closed_permanently"
    other = "other"


class ResourceGuideFlagResolution(StrEnum):
    verified_current = "verified_current"
    retired = "retired"
    edited = "edited"
    duplicate = "duplicate"
    invalid = "invalid"


class ParentResourceGuideFlag(Base, TimestampMixin):
    __tablename__ = "parent_resource_guide_flags"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(
        Integer,
        ForeignKey("parent_resource_guide_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flagged_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason_code = Column(String(50), nullable=False)  # ResourceGuideFlagReason value
    comment = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open")  # ResourceGuideFlagStatus value
    resolution = Column(String(50), nullable=True)  # ResourceGuideFlagResolution value
    resolution_notes = Column(Text, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    item = relationship("ParentResourceGuideItem", back_populates="flags")
    flagged_by = relationship("User", foreign_keys=[flagged_by_id], lazy="joined")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id], lazy="joined")

    __table_args__ = (
        Index("idx_flags_item", "item_id"),
        Index("idx_flags_status_created", "status", "created_at"),
    )


# ============================================================================
# Component 4: Emergency Childcare
# ============================================================================

class ChildcareSession(Base, TimestampMixin):
    __tablename__ = "childcare_sessions"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    date = Column(Date, nullable=False, index=True)
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)

    max_children = Column(Integer, nullable=False, default=6)
    age_range_min_months = Column(Integer, default=0)
    age_range_max_months = Column(Integer, default=60)  # Up to 5 years

    status = Column(
        String(50),
        default=ChildcareSessionStatus.available,
        nullable=False,
        index=True,
    )

    staff = relationship("User", foreign_keys=[staff_id])
    registrations = relationship("ChildcareRegistration", back_populates="session")

    __table_args__ = (
        Index("idx_childcare_session_branch_date", "branch_id", "date"),
    )


class ChildcareRegistration(Base, TimestampMixin):
    __tablename__ = "childcare_registrations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("childcare_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    child_name = Column(String(200), nullable=False)
    child_age_months = Column(Integer, nullable=False)
    special_needs_notes = Column(Text, nullable=True)
    emergency_contact_name = Column(String(200), nullable=False)
    emergency_contact_phone = Column(String(50), nullable=False)

    status = Column(
        String(50),
        default=ChildcareRegistrationStatus.registered,
        nullable=False,
    )

    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)

    # List of adults authorized to pick this child up. Each entry:
    #   {"name": str, "phone": str, "relationship": str, "id_required": bool}
    # SQLite (tests) stores as JSON text; Postgres uses native JSONB.
    authorized_pickup = Column(JSONB, nullable=False, default=list, server_default="[]")

    # Audit columns populated by the checkout endpoint after the
    # validate_pickup_authorization() guard succeeds.
    checked_out_by_name = Column(String(200), nullable=True)
    checked_out_by_phone = Column(String(50), nullable=True)
    pickup_override_reason = Column(Text, nullable=True)

    # Staff-side audit columns for the roster check-in / check-out / no-show
    # flow (PR follow-up to pickup_auth_001). ``checked_out_by_staff_id`` is
    # distinct from ``checked_out_by_name`` above: name is the *adult picking
    # up the child*; staff_id is the staff member who operated the checkout
    # UI. All FKs use ondelete=SET NULL so a deleted staff account doesn't
    # cascade-wipe historical childcare audit rows.
    checked_in_by_staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    checked_out_by_staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    no_show_flagged_by_staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    no_show_flagged_at = Column(DateTime(timezone=True), nullable=True)
    no_show_reason = Column(Text, nullable=True)

    patron = relationship("User", foreign_keys=[patron_id])
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_staff_id])
    checked_out_by = relationship("User", foreign_keys=[checked_out_by_staff_id])
    no_show_flagged_by = relationship(
        "User", foreign_keys=[no_show_flagged_by_staff_id]
    )
    session = relationship("ChildcareSession", back_populates="registrations")

    __table_args__ = (
        Index("idx_childcare_reg_patron", "patron_id", "session_id"),
    )


# ============================================================================
# Component 5: Community Connection Groups
# ============================================================================

class ParentConnectionGroup(Base, TimestampMixin):
    __tablename__ = "parent_connection_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    facilitator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    branch_id = Column(Integer, nullable=False, index=True)

    group_type = Column(
        String(50),
        default=ConnectionGroupType.general,
        nullable=False,
        index=True,
    )

    max_members = Column(Integer, default=12)
    meeting_frequency = Column(
        String(50),
        default=MeetingFrequency.weekly,
        nullable=False,
    )
    meeting_day_of_week = Column(String(20), nullable=True)  # monday, tuesday, etc.
    meeting_time = Column(String(5), nullable=True)  # HH:MM
    location = Column(String(300), nullable=True)
    languages = Column(ARRAY(String), default=list)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Confidentiality + approval-gated waitlist (cg_confidential_001).
    # When True: list/detail endpoints omit facilitator + member-count keys
    # for non-staff callers, and /enroll routes general-staff requests through
    # the approval queue instead of direct enrollment.
    confidential = Column(
        Boolean, nullable=False, server_default="false", default=False, index=True,
    )
    confidential_card_description = Column(String(300), nullable=True)
    confidential_approval_message = Column(Text, nullable=True)
    estimated_response_window_hours = Column(
        Integer, nullable=False, server_default="48", default=48,
    )

    # Cohort lifecycle (cg_lifecycle_001).
    # cohort_start_date / cohort_end_date are *informational* — the v1 archive
    # is admin-driven, not date-driven. A future daily-job can auto-archive when
    # cohort_end_date passes, but that's not in scope here (spec Open Q1).
    cohort_start_date = Column(Date, nullable=True)
    cohort_end_date = Column(Date, nullable=True)

    # Archive audit columns.
    # is_active is the *operative* flag the UI/queries filter on; archived_at
    # is the timestamped audit row. The two are kept in sync via the archive
    # service path (admins should never flip is_active directly).
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archived_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    archive_reason = Column(String(40), nullable=True)
    archive_notes = Column(Text, nullable=True)

    facilitator = relationship("User", foreign_keys=[facilitator_id])
    archived_by = relationship("User", foreign_keys=[archived_by_id])
    members = relationship("ParentConnectionGroupMember", back_populates="group")
    meetings = relationship(
        "ParentConnectionGroupMeeting",
        back_populates="group",
        order_by="ParentConnectionGroupMeeting.meeting_date",
    )

    __table_args__ = (
        Index("idx_connection_group_branch_active", "branch_id", "is_active"),
    )


class ParentConnectionGroupMember(Base, TimestampMixin):
    __tablename__ = "parent_connection_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("parent_connection_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(
        String(50),
        default=GroupMemberStatus.active,
        nullable=False,
    )

    joined_date = Column(Date, nullable=False)
    left_date = Column(Date, nullable=True)
    attendance_count = Column(Integer, default=0, nullable=False)

    # Staff-mediated enrollment audit trail.
    # enrolled_by_id is nullable so legacy self-joined rows (pre-enrollment-spec)
    # remain valid; NULL means "patron self-enrolled via deprecated /join".
    enrolled_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    enrollment_consent_note = Column(Text, nullable=True)
    capacity_override = Column(Boolean, nullable=False, server_default="false", default=False)
    override_justification = Column(Text, nullable=True)
    removed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    removal_reason = Column(String(40), nullable=True)

    # Confidentiality + approval-gated waitlist (cg_confidential_001).
    # Decision audit. decided_by_id is NULL until a facilitator/admin acts.
    request_message = Column(Text, nullable=True)
    consent_to_share_contact = Column(
        Boolean, nullable=False, server_default="false", default=False,
    )
    decided_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_note = Column(Text, nullable=True)
    decision_patron_message = Column(Text, nullable=True)

    patron = relationship("User", foreign_keys=[patron_id])
    group = relationship("ParentConnectionGroup", back_populates="members")
    enrolled_by = relationship("User", foreign_keys=[enrolled_by_id])
    removed_by = relationship("User", foreign_keys=[removed_by_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])

    __table_args__ = (
        Index("idx_group_member_unique", "group_id", "patron_id", unique=True),
    )


class ParentConnectionGroupMeeting(Base, TimestampMixin):
    __tablename__ = "parent_connection_group_meetings"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer,
        ForeignKey("parent_connection_groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    meeting_date = Column(Date, nullable=False, index=True)
    # scheduled_time mirrors group.meeting_time at materialization. We persist
    # a per-instance copy so a reschedule that changes the time on this one
    # meeting only doesn't lie about other dates' times.
    scheduled_time = Column(String(5), nullable=True)  # HH:MM
    location = Column(String(300), nullable=True)

    # status state machine: scheduled -> {cancelled, rescheduled, completed}.
    # "rescheduled" means a new row was created (linked via
    # rescheduled_to_meeting_id) and this row is the historical record.
    status = Column(String(20), nullable=False, server_default="scheduled", default="scheduled")

    # Cancel audit.
    cancelled_reason = Column(String(40), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # Reschedule audit. Self-FK with SET NULL: if the new meeting is later
    # deleted (shouldn't happen in v1; included for safety), the historical
    # row stays intact but the pointer goes null.
    rescheduled_to_meeting_id = Column(
        Integer,
        ForeignKey("parent_connection_group_meetings.id", ondelete="SET NULL"),
        nullable=True,
    )

    staff_notes = Column(Text, nullable=True)  # never sent to patrons
    patron_message = Column(Text, nullable=True)  # included in patron emails

    # Email dispatch audit. Distinct from staff_notes / patron_message
    # because the email-cap safeguard may partial-send; the count + the
    # most recent dispatch timestamp let us debug "did 12 of 18 actually
    # get notified?" without trawling Resend's dashboard.
    email_dispatched_at = Column(DateTime(timezone=True), nullable=True)
    email_dispatched_count = Column(Integer, nullable=False, server_default="0", default=0)

    group = relationship("ParentConnectionGroup", back_populates="meetings")
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    # NOTE: self-relationships left implicit (just the FK column). We don't
    # need a back-populated "rescheduled_from" relationship for v1.

    __table_args__ = (
        # Composite unique: a group can't have two meetings on the same date.
        # Reschedules create a new row on the NEW date; the old row stays at
        # the original date with status='rescheduled'. So this never collides.
        Index(
            "uq_connection_group_meeting_date",
            "group_id", "meeting_date",
            unique=True,
        ),
        Index("idx_connection_group_meeting_status", "group_id", "status"),
    )


# ============================================================================
# Component 6: Social Service Enrollment Facilitation
# ============================================================================

class ServiceEnrollmentFacilitation(Base, TimestampMixin):
    __tablename__ = "service_enrollment_facilitations"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    partner_id = Column(Integer, ForeignKey("outreach_partners.id", ondelete="SET NULL"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    service_name = Column(String(300), nullable=False)
    status = Column(
        String(50),
        default=EnrollmentFacilitationStatus.identified,
        nullable=False,
        index=True,
    )

    application_date = Column(Date, nullable=True)
    enrollment_date = Column(Date, nullable=True)
    documents_needed = Column(JSONB, default=list)
    documents_provided = Column(JSONB, default=list)
    notes = Column(Text, nullable=True)  # Staff-only
    outcome_notes = Column(Text, nullable=True)

    patron = relationship("User", foreign_keys=[patron_id])
    staff = relationship("User", foreign_keys=[staff_id])

    __table_args__ = (
        Index("idx_enrollment_patron_status", "patron_id", "status"),
    )


# ============================================================================
# Component 7: Home Visits
# ============================================================================

class ParentHomeVisit(Base, TimestampMixin):
    __tablename__ = "parent_home_visits"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    visitor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_session_id = Column(Integer, ForeignKey("parent_onboarding_sessions.id", ondelete="SET NULL"), nullable=True)

    purpose = Column(
        String(50),
        nullable=False,
    )

    status = Column(
        String(50),
        default=HomeVisitStatus.scheduled,
        nullable=False,
        index=True,
    )

    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(String(5), nullable=True)  # HH:MM
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)

    address = Column(Text, nullable=True)
    visit_notes = Column(Text, nullable=True)  # Staff-only, sensitive
    items_brought = Column(JSONB, default=list)  # Books, packets, etc.
    services_discussed = Column(JSONB, default=list)
    follow_up_needed = Column(Boolean, default=False, nullable=False)
    next_visit_date = Column(Date, nullable=True)

    # Lifecycle columns added by home_visit_mutations_001 (2026-05-25).
    # ``outcomes`` / ``resources_delivered`` / ``follow_up_date`` are the
    # canonical names the frontend and API contract use; the legacy
    # ``visit_notes`` / ``items_brought`` / ``next_visit_date`` columns
    # remain populated for older rows but new code writes here. Keeping
    # both prevents the silent-drop bug that was masking these fields
    # prior to this revision.
    outcomes = Column(Text, nullable=True)
    resources_delivered = Column(JSONB, nullable=True, default=list)
    follow_up_date = Column(Date, nullable=True)
    cancelled_reason = Column(Text, nullable=True)
    # When a visit is rescheduled, the original row keeps status=rescheduled
    # and points at the new visit row via this back-link. The new row has
    # status=scheduled and ``rescheduled_to_id`` left NULL.
    rescheduled_to_id = Column(
        Integer,
        ForeignKey("parent_home_visits.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Lone-worker safety check-in (feature flag: home_visit_safety_enabled).
    # checkout_due_at = safety_checkin_at + visit_duration_minutes + grace.
    # overdue_flagged_at is set by the periodic scan when checkout_due_at
    # passes without safety_checkout_at being set; its presence guarantees
    # the buddy + supervisors were notified at most once per visit.
    safety_checkin_at = Column(DateTime(timezone=True), nullable=True)
    safety_checkout_at = Column(DateTime(timezone=True), nullable=True)
    safety_checkout_due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    safety_buddy_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    safety_overdue_flagged_at = Column(DateTime(timezone=True), nullable=True)

    # Day-plan / map view (feature flag: home_visit_day_plan_enabled).
    # geocoded_lat/lng are populated from the geocode cache (or staff manual
    # entry) on visit-create and on the first day-plan view. NULL = not yet
    # geocoded; the day-plan response surfaces a warning so the UI can show
    # a "couldn't locate" badge and a manual-pin button.
    # day_plan_sort_index = NULL means "auto-order by scheduled_time".
    # Any non-NULL value puts the stop at that 1-based position in the day
    # plan, regardless of scheduled_time. Reset-to-auto = set back to NULL.
    geocoded_lat = Column(Numeric(precision=9, scale=6), nullable=True)
    geocoded_lng = Column(Numeric(precision=9, scale=6), nullable=True)
    day_plan_sort_index = Column(Integer, nullable=True)

    patron = relationship("User", foreign_keys=[patron_id])
    visitor = relationship("User", foreign_keys=[visitor_id])
    safety_buddy = relationship("User", foreign_keys=[safety_buddy_user_id])
    parent_session = relationship("ParentOnboardingSession")
    # Reschedule back-link, lazy-loaded. Use selectinload when serializing
    # to avoid the MissingGreenlet trap on response.
    rescheduled_to = relationship(
        "ParentHomeVisit",
        remote_side=[id],
        foreign_keys=[rescheduled_to_id],
    )
    status_history = relationship(
        "HomeVisitStatusHistory",
        back_populates="visit",
        cascade="all, delete-orphan",
        order_by="HomeVisitStatusHistory.changed_at.desc()",
    )

    __table_args__ = (
        Index("idx_home_visit_patron_status", "patron_id", "status"),
        Index("idx_home_visit_visitor_date", "visitor_id", "scheduled_date"),
    )


class HomeVisitStatusHistory(Base):

    __tablename__ = "home_visit_status_history"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(
        Integer,
        ForeignKey("parent_home_visits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Null for the synthetic "initial state" row written when a visit is
    # created via the mutation routes. Real transitions always have a from.
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    changed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)

    visit = relationship("ParentHomeVisit", back_populates="status_history")
    changed_by = relationship("User", foreign_keys=[changed_by_id])

    __table_args__ = (
        Index(
            "ix_home_visit_status_history_visit_changed",
            "visit_id",
            "changed_at",
        ),
    )


# ============================================================================
# Component 8: Session follow-ups + referrals (first-class objects)
# ============================================================================
#
# These promote the legacy stringly-typed `referrals_made` / `follow_up_date`
# fields (which never actually shipped to the prod DB -- spec was based on a
# stale FE-TS-types snapshot) to real linked records with lifecycle.
#
# - ParentOnboardingFollowup: assignee + due + status + completion note
# - ParentOnboardingReferral: link to partner_agency or freetext name
# - PartnerAgency: canonical lookup table (WIC, SNAP, shelter, etc.)


class FollowupStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class FollowupPriority(StrEnum):
    low = "low"
    normal = "normal"
    high = "high"


class ReferralStatus(StrEnum):
    made = "made"
    scheduled = "scheduled"
    completed = "completed"
    declined_by_patron = "declined_by_patron"
    declined_by_agency = "declined_by_agency"


class PartnerAgency(Base, TimestampMixin):
    __tablename__ = "partner_agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    agency_type = Column(String(64), nullable=True)  # "wic", "snap", "shelter", ...
    contact_phone = Column(String(32), nullable=True)
    contact_email = Column(String(255), nullable=True)
    website_url = Column(String(500), nullable=True)
    service_area = Column(String(255), nullable=True)
    languages_served = Column(ARRAY(String), default=list)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)


class ParentOnboardingFollowup(Base, TimestampMixin):
    __tablename__ = "parent_onboarding_followups"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("parent_onboarding_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    due_date = Column(Date, nullable=False, index=True)
    status = Column(
        String(32), default=FollowupStatus.open, nullable=False, index=True,
    )
    priority = Column(String(16), default=FollowupPriority.normal, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    completion_note = Column(Text, nullable=True)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    session = relationship("ParentOnboardingSession", foreign_keys=[session_id])
    assignee = relationship("User", foreign_keys=[assignee_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index(
            "idx_followup_assignee_status_due",
            "assignee_id", "status", "due_date",
        ),
    )


class ParentOnboardingReferral(Base, TimestampMixin):
    __tablename__ = "parent_onboarding_referrals"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("parent_onboarding_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_agency_id = Column(
        Integer,
        ForeignKey("partner_agencies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agency_name_freetext = Column(String(255), nullable=True)
    purpose = Column(String(255), nullable=False)
    status = Column(
        String(32), default=ReferralStatus.made, nullable=False, index=True,
    )
    warm_handoff = Column(Boolean, default=False, nullable=False)
    patron_consent_to_share = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    made_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    made_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    session = relationship("ParentOnboardingSession", foreign_keys=[session_id])
    partner_agency = relationship("PartnerAgency", foreign_keys=[partner_agency_id])
    made_by = relationship("User", foreign_keys=[made_by_id])


# ============================================================================
# Component 7b: Day-plan map cache + per-patron access notes
# ============================================================================


class HomeVisitGeocodeCache(Base):

    __tablename__ = "home_visit_geocode_cache"

    address_hash = Column(String(64), primary_key=True)
    address_raw = Column(Text, nullable=False)
    lat = Column(Numeric(precision=9, scale=6), nullable=False)
    lng = Column(Numeric(precision=9, scale=6), nullable=False)
    geocoded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    provider = Column(String(20), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "provider IN ('nominatim', 'manual')",
            name="ck_home_visit_geocode_cache_provider",
        ),
    )


class HomeVisitAccessNotes(Base):

    __tablename__ = "home_visit_access_notes"

    # SQLite tooling (test fixtures) doesn't autoincrement BigInteger PKs;
    # use Integer for compatibility -- range is still plenty for residence
    # notes, where one row per patron caps at the patron count.
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    has_steps = Column(Boolean, nullable=False, default=False)
    has_elevator = Column(Boolean, nullable=False, default=False)
    multi_floor = Column(Boolean, nullable=False, default=False)
    dog_on_premises = Column(Boolean, nullable=False, default=False)
    dog_safety_note = Column(Text, nullable=True)
    primary_language = Column(String(20), nullable=True)
    needs_interpreter = Column(Boolean, nullable=False, default=False)
    buzzer_or_intercom = Column(Text, nullable=True)
    parking_notes = Column(Text, nullable=True)
    other_notes = Column(Text, nullable=True)

    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patron = relationship("User", foreign_keys=[patron_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])

    __table_args__ = (
        UniqueConstraint("patron_id", name="uq_home_visit_access_notes_patron_id"),
    )


# ============================================================================
# Component 9: Session resource handouts (catalog + per-session assignments)
# ============================================================================
#
# Replaces the freeform `resources_provided` string input on the Complete
# Session form (which existed only in the FE-TS-types snapshot -- the prod
# `parent_onboarding_sessions` table never had that column) with a
# structured catalog picker.
#
# - ResourceHandout: catalog row for one localized PDF (slug + language).
# - ParentOnboardingSessionHandout: join row recording what was handed to
#   whom, when, by which staff, in what delivery method.
#
# The community_resource_links table stays as the URL-only sibling; a join
# row can target either a ResourceHandout (PDF) OR a community resource link
# (URL). The CHECK constraint enforces exactly one is set per join row.


class SessionHandoutDeliveryMethod(StrEnum):
    printed = "printed"
    emailed = "emailed"
    linked = "linked"
    given_orally = "given_orally"


class ResourceHandout(Base, TimestampMixin):
    __tablename__ = "resource_handouts"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(128), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    # BCP-47 code: "en", "es", "vi", "ar", ...
    language = Column(String(8), nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    preview_thumbnail_path = Column(String(500), nullable=True)
    tags = Column(ARRAY(String), default=list)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint(
            "slug", "language", name="uq_resource_handouts_slug_language",
        ),
        Index(
            "idx_resource_handouts_category_language_active",
            "category", "language", "is_active",
        ),
    )


class ParentOnboardingSessionHandout(Base, TimestampMixin):
    __tablename__ = "parent_onboarding_session_handouts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("parent_onboarding_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_handout_id = Column(
        Integer,
        ForeignKey("resource_handouts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    community_resource_link_id = Column(
        Integer,
        ForeignKey("community_resource_links.id", ondelete="SET NULL"),
        nullable=True,
    )
    given_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    given_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    given_in_language = Column(String(8), nullable=False)
    delivery_method = Column(
        String(32),
        default=SessionHandoutDeliveryMethod.printed.value,
        nullable=False,
    )
    notes = Column(Text, nullable=True)

    session = relationship(
        "ParentOnboardingSession", foreign_keys=[session_id],
    )
    resource_handout = relationship(
        "ResourceHandout", foreign_keys=[resource_handout_id],
    )
    community_resource_link = relationship(
        "CommunityResourceLink", foreign_keys=[community_resource_link_id],
    )
    given_by = relationship("User", foreign_keys=[given_by_id])

    __table_args__ = (
        # Equity-reporting queries scan (given_in_language, given_at).
        Index(
            "idx_session_handouts_language_given_at",
            "given_in_language", "given_at",
        ),
        # Staff-activity reports scan (given_by_id, given_at).
        Index(
            "idx_session_handouts_given_by_given_at",
            "given_by_id", "given_at",
        ),
    )
