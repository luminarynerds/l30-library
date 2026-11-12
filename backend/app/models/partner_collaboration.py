# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# Enums
# ============================================================================

class SharedEventType(StrEnum):
    program = "program"
    workshop = "workshop"
    meeting = "meeting"
    training = "training"
    community_event = "community_event"
    fundraiser = "fundraiser"
    outreach = "outreach"
    virtual_event = "virtual_event"


class SharedEventStatus(StrEnum):
    planned = "planned"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    postponed = "postponed"


class ResourceRequestType(StrEnum):
    materials = "materials"
    equipment = "equipment"
    space = "space"
    expertise = "expertise"
    volunteer_time = "volunteer_time"
    funding = "funding"
    marketing = "marketing"


class ResourceRequestStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    in_progress = "in_progress"
    completed = "completed"
    rejected = "rejected"
    cancelled = "cancelled"


class CoSponsoredProgramStatus(StrEnum):
    in_development = "in_development"
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class MeetingType(StrEnum):
    planning = "planning"
    strategy = "strategy"
    review = "review"
    problem_solving = "problem_solving"
    celebration = "celebration"
    partnership_update = "partnership_update"
    annual = "annual"


class MOUStatus(StrEnum):
    draft = "draft"
    under_review = "under_review"
    signed = "signed"
    active = "active"
    expired = "expired"
    terminated = "terminated"


class GrantOpportunityStatus(StrEnum):
    identified = "identified"
    evaluating = "evaluating"
    applying = "applying"
    submitted = "submitted"
    awarded = "awarded"
    rejected = "rejected"
    funded = "funded"


class ImpactMetricType(StrEnum):
    participants_served = "participants_served"
    hours_contributed = "hours_contributed"
    resources_shared = "resources_shared"
    events_hosted = "events_hosted"
    community_reach = "community_reach"
    funding_generated = "funding_generated"
    learning_outcomes = "learning_outcomes"
    awareness_raised = "awareness_raised"


class RecognitionType(StrEnum):
    thank_you_letter = "thank_you_letter"
    award = "award"
    certificate = "certificate"
    spotlight_feature = "spotlight_feature"
    public_recognition = "public_recognition"
    appreciation_event = "appreciation_event"
    gift = "gift"
    naming_opportunity = "naming_opportunity"


# ============================================================================
# Shared Event Calendar
# ============================================================================

class SharedEvent(Base):
    __tablename__ = "shared_events"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    title = Column(String(300), nullable=False)
    description = Column(Text)
    event_type = Column(
        SQLEnum(SharedEventType, name="sharedeventtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Event date/time
    event_date = Column(Date, nullable=False)
    start_time = Column(String(10), nullable=True)  # HH:MM format
    end_time = Column(String(10), nullable=True)

    # Status and visibility
    status = Column(
        SQLEnum(SharedEventStatus, name="sharedeventstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SharedEventStatus.planned,
        nullable=False, index=True
    )
    is_public = Column(Boolean, default=True)

    # Location
    location = Column(String(500))
    virtual_meeting_url = Column(String(500))  # Zoom, Teams, etc.

    # Participating partners
    organizing_partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )
    co_organizing_partner_ids = Column(ARRAY(Integer), default=[], nullable=False)

    # Event details
    expected_attendance = Column(Integer)
    target_audience = Column(String(200))
    materials_needed = Column(JSONB, default=list)
    budget = Column(Float)

    # Coordination
    lead_organizer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    coordinator_ids = Column(ARRAY(Integer), default=[], nullable=False)

    # Outcomes (after event)
    actual_attendance = Column(Integer)
    outcomes = Column(Text)
    lessons_learned = Column(Text)
    follow_up_actions = Column(JSONB, default=list)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    organizing_partner = relationship("OutreachPartner")
    lead_organizer = relationship("User", foreign_keys=[lead_organizer_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_shared_events_date", "event_date"),
        Index("ix_shared_events_status_date", "status", "event_date"),
        Index("ix_shared_events_partner", "organizing_partner_id"),
    )


# ============================================================================
# Resource Sharing Requests
# ============================================================================

class ResourceSharingRequest(Base):
    __tablename__ = "resource_sharing_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    resource_type = Column(
        SQLEnum(ResourceRequestType, name="resourcerequesttype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Requesting and providing parties
    requesting_partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )
    providing_partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="SET NULL")
    )

    # Status
    status = Column(
        SQLEnum(ResourceRequestStatus, name="resourcerequeststatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ResourceRequestStatus.pending,
        nullable=False, index=True
    )

    # Request details
    quantity = Column(Integer)
    unit = Column(String(50))  # items, hours, etc.
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)

    # Resource specifics
    specific_items = Column(JSONB, default=list)  # Detailed list of items needed
    cost_estimate = Column(Float)
    budget_approved = Column(Boolean, default=False)

    # Contact info
    requester_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    contact_name = Column(String(200))
    contact_email = Column(String(255))
    contact_phone = Column(String(30))

    # Approval workflow
    approval_notes = Column(Text)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(DateTime(timezone=True))

    # Delivery/Pickup
    delivery_date = Column(Date)
    return_date = Column(Date)
    delivery_location = Column(String(500))

    # Outcomes
    completion_notes = Column(Text)
    satisfaction_rating = Column(Integer)  # 1-5 rating

    # Audit, server_default=func.now())

    # Relationships
    requesting_partner = relationship(
        "OutreachPartner", foreign_keys=[requesting_partner_id]
    )
    providing_partner = relationship(
        "OutreachPartner", foreign_keys=[providing_partner_id]
    )
    requester_user = relationship("User", foreign_keys=[requester_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_resource_requests_requesting_partner", "requesting_partner_id"),
        Index("ix_resource_requests_status", "status"),
        Index("ix_resource_requests_dates", "start_date", "end_date"),
    )


# ============================================================================
# Co-Sponsored Programs
# ============================================================================

class CoSponsoredProgram(Base):
    __tablename__ = "co_sponsored_programs"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String(300), nullable=False)
    description = Column(Text)
    program_type = Column(String(100))  # reading program, workshop series, etc.

    # Status
    status = Column(
        SQLEnum(CoSponsoredProgramStatus, name="cosponsoredprogramstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CoSponsoredProgramStatus.in_development,
        nullable=False, index=True
    )

    # Sponsoring partners
    lead_partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )
    co_sponsor_partner_ids = Column(ARRAY(Integer), default=[], nullable=False)

    # Program timing
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)

    # Program details
    target_audience = Column(String(200))
    goals = Column(JSONB, default=list)
    expected_reach = Column(Integer)

    # Budget and resources
    total_budget = Column(Float)
    library_contribution = Column(Float)
    partner_contributions = Column(JSONB, default=dict)  # {partner_id: amount}

    # Coordination
    program_manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    partner_leads = Column(JSONB, default=dict)  # {partner_id: user_name}

    # Outcomes
    participants = Column(Integer)
    completion_rate = Column(Float)  # 0-100%
    outcomes_achieved = Column(JSONB, default=list)
    impact_summary = Column(Text)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    lead_partner = relationship("OutreachPartner", foreign_keys=[lead_partner_id])
    program_manager = relationship("User", foreign_keys=[program_manager_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    sessions = relationship(
        "ProgramSession", back_populates="program",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_co_sponsored_programs_lead_partner", "lead_partner_id"),
        Index("ix_co_sponsored_programs_status", "status"),
        Index("ix_co_sponsored_programs_dates", "start_date", "end_date"),
    )


class ProgramSession(Base):
    __tablename__ = "program_sessions"

    id = Column(Integer, primary_key=True, index=True)

    program_id = Column(
        Integer, ForeignKey("co_sponsored_programs.id", ondelete="CASCADE"),
        nullable=False
    )

    # Session details
    title = Column(String(300), nullable=False)
    session_number = Column(Integer)
    session_date = Column(Date, nullable=False)
    start_time = Column(String(10))
    end_time = Column(String(10))

    # Location and format
    location = Column(String(500))
    format = Column(String(50))  # in-person, virtual, hybrid
    virtual_url = Column(String(500))

    # Attendance
    expected_attendance = Column(Integer)
    actual_attendance = Column(Integer)

    # Facilitation
    lead_facilitator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    co_facilitators = Column(JSONB, default=list)  # List of user names

    # Notes
    session_notes = Column(Text)
    outcomes = Column(Text)

    # Relationships
    program = relationship("CoSponsoredProgram", back_populates="sessions")
    lead_facilitator = relationship("User", foreign_keys=[lead_facilitator_id])

    __table_args__ = (
        Index("ix_program_sessions_program_date", "program_id", "session_date"),
    )


# ============================================================================
# Enhanced Contact Directory
# ============================================================================

class PartnerContactDirectory(Base):
    __tablename__ = "partner_contact_directory"

    id = Column(Integer, primary_key=True, index=True)

    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )

    # Contact information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(150))
    department = Column(String(150))

    # Multiple contact methods
    email = Column(String(255))
    phone = Column(String(30))
    mobile = Column(String(30))
    fax = Column(String(30))

    # Specialty/expertise
    expertise_areas = Column(ARRAY(String), default=[], nullable=False)
    language_skills = Column(ARRAY(String), default=[], nullable=False)

    # Preferences
    preferred_contact_method = Column(String(50))  # email, phone, text
    best_time_to_contact = Column(String(100))
    receives_notifications = Column(Boolean, default=True)

    # Roles and responsibilities
    roles = Column(ARRAY(String), default=[], nullable=False)  # decision_maker, program_lead, etc.
    is_primary = Column(Boolean, default=False)
    is_backup = Column(Boolean, default=False)

    # Relationship notes
    notes = Column(Text)
    last_contact_date = Column(Date)

    # Address
    address = Column(String(500))

    # Audit, server_default=func.now())

    # Relationships
    partner = relationship("OutreachPartner")

    __table_args__ = (
        Index("ix_partner_directory_partner_name", "partner_id", "last_name", "first_name"),
        Index("ix_partner_directory_email", "email"),
    )


# ============================================================================
# Meeting Notes and History
# ============================================================================

class PartnershipMeeting(Base):
    __tablename__ = "partnership_meetings"

    id = Column(Integer, primary_key=True, index=True)

    # Meeting info
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )
    meeting_type = Column(
        SQLEnum(MeetingType, name="meetingtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    title = Column(String(300), nullable=False)

    # Meeting timing
    meeting_date = Column(Date, nullable=False)
    start_time = Column(String(10))
    end_time = Column(String(10))

    # Location/format
    location = Column(String(500))
    format = Column(String(50))  # in-person, virtual, hybrid, phone
    meeting_url = Column(String(500))  # For virtual meetings

    # Attendees
    attendees = Column(JSONB, default=list)  # [{name, title, organization}]
    library_attendees = Column(JSONB, default=list)

    # Meeting content
    agenda = Column(Text)
    topics_discussed = Column(JSONB, default=list)
    decisions_made = Column(JSONB, default=list)

    # Notes and outcomes
    meeting_notes = Column(Text, nullable=False)
    next_steps = Column(JSONB, default=list)  # [{action, owner, due_date}]
    action_items = Column(JSONB, default=list)

    # Follow-up
    follow_up_date = Column(Date)
    follow_up_notes = Column(Text)

    # Attachments
    attachments = Column(JSONB, default=list)  # [{filename, url, type}]

    # Audit
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    partner = relationship("OutreachPartner")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])

    __table_args__ = (
        Index("ix_partnership_meetings_partner_date", "partner_id", "meeting_date"),
        Index("ix_partnership_meetings_type", "meeting_type"),
    )


# ============================================================================
# MOU/Agreement Tracking
# ============================================================================

class PartnershipAgreement(Base):
    __tablename__ = "partnership_agreements"

    id = Column(Integer, primary_key=True, index=True)

    # Agreement info
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )
    agreement_type = Column(String(100), nullable=False)  # MOU, Service Agreement, etc.
    title = Column(String(300), nullable=False)

    # Status
    status = Column(
        SQLEnum(MOUStatus, name="moustatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MOUStatus.draft,
        nullable=False, index=True
    )

    # Effective dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    renewal_date = Column(Date)

    # Key terms
    scope_of_work = Column(Text)
    objectives = Column(JSONB, default=list)
    responsibilities = Column(JSONB, default=dict)  # {party: responsibilities}
    financial_terms = Column(Text)

    # Signatories
    library_signatory = Column(String(200))
    partner_signatory = Column(String(200))

    # Documents
    document_url = Column(String(500))  # Link to stored document
    document_filename = Column(String(300))

    # Approval workflow
    draft_status = Column(String(50), default="draft")
    submitted_at = Column(DateTime(timezone=True))
    signed_at = Column(DateTime(timezone=True))

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Notes
    notes = Column(Text)

    # Audit, server_default=func.now())

    # Relationships
    partner = relationship("OutreachPartner")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    amendments = relationship(
        "AgreementAmendment", back_populates="agreement",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_partnership_agreements_partner", "partner_id"),
        Index("ix_partnership_agreements_status", "status"),
        Index("ix_partnership_agreements_dates", "start_date", "end_date"),
    )


class AgreementAmendment(Base):
    __tablename__ = "agreement_amendments"

    id = Column(Integer, primary_key=True, index=True)

    agreement_id = Column(
        Integer, ForeignKey("partnership_agreements.id", ondelete="CASCADE"),
        nullable=False
    )

    # Amendment info
    title = Column(String(300), nullable=False)
    amendment_number = Column(Integer)

    # Changes
    changes_summary = Column(Text, nullable=False)
    effective_date = Column(Date, nullable=False)

    # Documents
    document_url = Column(String(500))

    # Approval
    approved_at = Column(DateTime(timezone=True))
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    agreement = relationship("PartnershipAgreement", back_populates="amendments")
    approved_by = relationship("User", foreign_keys=[approved_by_id])


# ============================================================================
# Joint Grant Opportunities
# ============================================================================

class JointGrantOpportunity(Base):
    __tablename__ = "joint_grant_opportunities"

    id = Column(Integer, primary_key=True, index=True)

    # Grant info
    title = Column(String(300), nullable=False)
    description = Column(Text)
    funding_source = Column(String(300), nullable=False)

    # Status
    status = Column(
        SQLEnum(GrantOpportunityStatus, name="grantopportunitystatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=GrantOpportunityStatus.identified,
        nullable=False, index=True
    )

    # Participating partners
    partner_ids = Column(ARRAY(Integer), default=[], nullable=False)

    # Funding details
    total_funding_available = Column(Float)
    amount_requested = Column(Float)
    library_requesting = Column(Boolean, default=True)

    # Timeline
    grant_deadline = Column(Date)
    notification_date = Column(Date)
    project_start_date = Column(Date)
    project_end_date = Column(Date)

    # Project details
    project_description = Column(Text)
    goals_and_outcomes = Column(JSONB, default=list)
    budget_details = Column(JSONB, default=dict)

    # Management
    grant_lead_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    partner_leads = Column(JSONB, default=dict)  # {partner_id: lead_name}

    # Outcomes
    awarded_amount = Column(Float)
    award_date = Column(Date)
    award_letter_url = Column(String(500))

    # Notes
    notes = Column(Text)
    lessons_learned = Column(Text)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    grant_lead = relationship("User", foreign_keys=[grant_lead_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_joint_grant_opportunities_status", "status"),
        Index("ix_joint_grant_opportunities_deadline", "grant_deadline"),
    )


# ============================================================================
# Impact Reporting for Partners
# ============================================================================

class PartnerImpactReport(Base):
    __tablename__ = "partner_impact_reports"

    id = Column(Integer, primary_key=True, index=True)

    # Report period
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )
    reporting_period_start = Column(Date, nullable=False)
    reporting_period_end = Column(Date, nullable=False)

    # Program metrics
    programs_delivered = Column(Integer, default=0)
    program_sessions = Column(Integer, default=0)
    total_participants = Column(Integer, default=0)

    # Resource metrics
    resources_shared_value = Column(Float, default=0.0)
    volunteer_hours = Column(Float, default=0.0)
    staff_hours_contributed = Column(Float, default=0.0)

    # Reach metrics
    unique_people_served = Column(Integer, default=0)
    underserved_population_served = Column(Integer, default=0)

    # Outcomes
    outcomes_achieved = Column(JSONB, default=list)
    success_stories = Column(JSONB, default=list)

    # Impact narrative
    impact_summary = Column(Text)
    highlights = Column(JSONB, default=list)
    challenges_and_solutions = Column(JSONB, default=list)

    # Financial impact
    estimated_value_provided = Column(Float)
    cost_savings_generated = Column(Float)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    partner = relationship("OutreachPartner")
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    metrics = relationship(
        "ImpactMetric", back_populates="report",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_partner_impact_reports_partner", "partner_id"),
        Index("ix_partner_impact_reports_period", "reporting_period_start", "reporting_period_end"),
        UniqueConstraint(
            "partner_id", "reporting_period_start", "reporting_period_end",
            name="uq_impact_report_period"
        ),
    )


class ImpactMetric(Base):
    __tablename__ = "impact_metrics"

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(
        Integer, ForeignKey("partner_impact_reports.id", ondelete="CASCADE"),
        nullable=False
    )

    # Metric details
    metric_type = Column(
        SQLEnum(ImpactMetricType, name="impactmetrictype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    metric_name = Column(String(200), nullable=False)

    # Values
    target_value = Column(Float)
    actual_value = Column(Float, nullable=False)
    unit = Column(String(50))  # persons, hours, dollars, etc.

    # Details
    notes = Column(Text)
    data_source = Column(String(200))

    # Relationships
    report = relationship("PartnerImpactReport", back_populates="metrics")


# ============================================================================
# Partner Recognition and Appreciation
# ============================================================================

class PartnerRecognition(Base):
    __tablename__ = "partner_recognition"

    id = Column(Integer, primary_key=True, index=True)

    # Recognition details
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )
    recognition_type = Column(
        SQLEnum(RecognitionType, name="recognitiontype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    title = Column(String(300), nullable=False)
    description = Column(Text)

    # Recognition timing
    recognition_date = Column(Date, nullable=False)
    announcement_date = Column(Date)

    # Reason for recognition
    reason = Column(Text, nullable=False)
    accomplishments = Column(JSONB, default=list)

    # Recognition presentation
    presented_by = Column(String(200))
    presented_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Physical/digital items
    certificate_issued = Column(Boolean, default=False)
    certificate_url = Column(String(500))
    award_name = Column(String(300))

    # Media and publicity
    featured_in = Column(JSONB, default=list)  # newsletter, website, social media, etc.
    media_urls = Column(JSONB, default=list)

    # Attendees/Invitees
    attendees = Column(JSONB, default=list)  # Names of people invited

    # Impact
    outcome_notes = Column(Text)
    photos_url = Column(String(500))

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    partner = relationship("OutreachPartner")
    presented_by_user = relationship("User", foreign_keys=[presented_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_partner_recognition_partner", "partner_id"),
        Index("ix_partner_recognition_date", "recognition_date"),
        Index("ix_partner_recognition_type", "recognition_type"),
    )


class ThankYouMessage(Base):
    __tablename__ = "thank_you_messages"

    id = Column(Integer, primary_key=True, index=True)

    # Message details
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )

    contact_id = Column(
        Integer, ForeignKey("partner_contact_directory.id", ondelete="SET NULL")
    )

    # Message content
    subject = Column(String(300), nullable=False)
    message_body = Column(Text, nullable=False)
    message_type = Column(String(50))  # email, letter, card, verbal

    # Sending details
    sent_date = Column(Date, nullable=False)
    sent_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    sent_to_email = Column(String(255))
    sent_to_name = Column(String(200))

    # Reason for thank you
    reason = Column(Text)
    acknowledgement_of = Column(String(500))  # What they did

    # Acknowledgement
    received_confirmation = Column(Boolean, default=False)
    response_received = Column(DateTime(timezone=True))
    response_text = Column(Text)

    # Follow-up
    requires_follow_up = Column(Boolean, default=False)
    follow_up_date = Column(Date)

    # Relationships
    partner = relationship("OutreachPartner")
    contact = relationship("PartnerContactDirectory")
    sent_by = relationship("User", foreign_keys=[sent_by_id])

    __table_args__ = (
        Index("ix_thank_you_messages_partner", "partner_id"),
        Index("ix_thank_you_messages_sent_date", "sent_date"),
    )
