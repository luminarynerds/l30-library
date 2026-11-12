# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class PublicRecordsRequestType(StrEnum):
    FOIA_FEDERAL = "foia_federal"  # Federal Freedom of Information Act
    STATE_OPEN_RECORDS = "state_open_records"  # State-level open records law
    MUNICIPAL_RECORDS = "municipal_records"  # Local/municipal records request
    MEDIA_INQUIRY = "media_inquiry"  # Media/press inquiry
    RESEARCH_REQUEST = "research_request"  # Academic/research request
    INTERNAL_AUDIT = "internal_audit"  # Internal records request


class PublicRecordsRequestStatus(StrEnum):
    RECEIVED = "received"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    PENDING_CLARIFICATION = "pending_clarification"
    PENDING_FEE_PAYMENT = "pending_fee_payment"
    RECORDS_LOCATED = "records_located"
    UNDER_REVIEW = "under_review"
    REDACTION_IN_PROGRESS = "redaction_in_progress"
    READY_FOR_RELEASE = "ready_for_release"
    COMPLETED = "completed"
    DENIED = "denied"
    PARTIALLY_DENIED = "partially_denied"
    WITHDRAWN = "withdrawn"
    APPEALED = "appealed"


class ExemptionType(StrEnum):
    PERSONAL_PRIVACY = "personal_privacy"  # Patron privacy, SSN, etc.
    LAW_ENFORCEMENT = "law_enforcement"  # Active investigation
    ATTORNEY_CLIENT = "attorney_client"  # Legal privilege
    TRADE_SECRET = "trade_secret"  # Vendor proprietary info
    SECURITY = "security"  # Building security, IT systems
    DELIBERATIVE = "deliberative"  # Internal deliberations
    PERSONNEL = "personnel"  # Employee personnel records
    MINOR_PROTECTION = "minor_protection"  # Child information
    COPPA = "coppa"  # Children's privacy
    FERPA = "ferpa"  # Student educational records
    HIPAA = "hipaa"  # Health information
    OTHER = "other"


class JurisdictionType(StrEnum):
    FEDERAL = "federal"  # FOIA - 20 business days
    CALIFORNIA = "california"  # CA PRA - 10 days
    TEXAS = "texas"  # TX PIA - 10 business days
    NEW_YORK = "new_york"  # NY FOIL - 5 business days
    FLORIDA = "florida"  # FL Sunshine Law - Prompt
    ILLINOIS = "illinois"  # IL FOIA - 5 business days
    PENNSYLVANIA = "pennsylvania"  # PA RTK - 5 business days
    OHIO = "ohio"  # OH PRA - Prompt
    GEORGIA = "georgia"  # GA ORA - 3 business days
    MICHIGAN = "michigan"  # MI FOIA - 5 business days
    OTHER = "other"  # Default 10 business days


# Response deadline mapping (business days)
JURISDICTION_DEADLINES = {
    JurisdictionType.FEDERAL: 20,
    JurisdictionType.CALIFORNIA: 10,
    JurisdictionType.TEXAS: 10,
    JurisdictionType.NEW_YORK: 5,
    JurisdictionType.FLORIDA: 3,  # "Prompt" interpreted as 3 days
    JurisdictionType.ILLINOIS: 5,
    JurisdictionType.PENNSYLVANIA: 5,
    JurisdictionType.OHIO: 5,  # "Prompt" interpreted as 5 days
    JurisdictionType.GEORGIA: 3,
    JurisdictionType.MICHIGAN: 5,
    JurisdictionType.OTHER: 10,
}


class PublicRecordsAuditAction(StrEnum):
    REQUEST_RECEIVED = "request_received"
    REQUEST_ACKNOWLEDGED = "request_acknowledged"
    STATUS_CHANGED = "status_changed"
    CLARIFICATION_REQUESTED = "clarification_requested"
    CLARIFICATION_RECEIVED = "clarification_received"
    RECORDS_SEARCH_STARTED = "records_search_started"
    RECORDS_LOCATED = "records_located"
    NO_RECORDS_FOUND = "no_records_found"
    REDACTION_STARTED = "redaction_started"
    REDACTION_COMPLETED = "redaction_completed"
    EXEMPTION_APPLIED = "exemption_applied"
    FEE_ESTIMATED = "fee_estimated"
    FEE_WAIVED = "fee_waived"
    FEE_PAID = "fee_paid"
    RECORDS_RELEASED = "records_released"
    REQUEST_DENIED = "request_denied"
    APPEAL_FILED = "appeal_filed"
    APPEAL_DECIDED = "appeal_decided"
    EXTENSION_REQUESTED = "extension_requested"
    EXTENSION_GRANTED = "extension_granted"
    NOTE_ADDED = "note_added"
    DOCUMENT_ATTACHED = "document_attached"
    VIEWED = "viewed"


class PublicRecordsRequest(Base):
    __tablename__ = "public_records_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Unique tracking number
    tracking_number = Column(String(50), unique=True, nullable=False, index=True)

    # Request classification
    request_type = Column(
        SQLEnum(PublicRecordsRequestType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    jurisdiction = Column(
        SQLEnum(JurisdictionType, values_callable=lambda x: [e.value for e in x]),
        default=JurisdictionType.OTHER,
        nullable=False
    )

    # Requester information
    requester_name = Column(String(200), nullable=False)
    requester_organization = Column(String(255), nullable=True)
    requester_email = Column(String(255), nullable=True)
    requester_phone = Column(String(50), nullable=True)
    requester_address = Column(Text, nullable=True)
    is_media = Column(Boolean, default=False, nullable=False)
    is_commercial = Column(Boolean, default=False, nullable=False)  # Commercial purpose requests

    # Linkage to board meetings / committees (optional, set when the request
    # came in scoped to a specific meeting or committee)
    meeting_id = Column(
        Integer,
        ForeignKey("board_meetings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    committee_id = Column(
        Integer,
        ForeignKey("board_committees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Channel that submitted this request (NULL for legacy staff-logged
    # requests prior to public form rollout)
    submitted_via = Column(String(30), nullable=True)

    # Request details
    date_received = Column(DateTime(timezone=True), nullable=False)
    date_acknowledged = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=False)  # What records are being requested
    records_date_range_start = Column(Date, nullable=True)
    records_date_range_end = Column(Date, nullable=True)
    preferred_format = Column(String(100), nullable=True)  # electronic, paper, inspection

    # Deadline tracking
    response_deadline = Column(Date, nullable=False, index=True)
    extension_granted = Column(Boolean, default=False, nullable=False)
    extension_reason = Column(Text, nullable=True)
    extended_deadline = Column(Date, nullable=True)

    # Status tracking
    status = Column(
        SQLEnum(PublicRecordsRequestStatus, values_callable=lambda x: [e.value for e in x]),
        default=PublicRecordsRequestStatus.RECEIVED,
        nullable=False,
        index=True
    )

    # Assignment
    assigned_to_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Fee tracking
    fee_estimate = Column(Numeric(10, 2), nullable=True)
    fee_estimate_date = Column(DateTime(timezone=True), nullable=True)
    fee_waived = Column(Boolean, default=False, nullable=False)
    fee_waiver_reason = Column(Text, nullable=True)
    fee_paid = Column(Numeric(10, 2), nullable=True)
    fee_paid_date = Column(DateTime(timezone=True), nullable=True)

    # Response details
    response_date = Column(DateTime(timezone=True), nullable=True)
    response_method = Column(String(100), nullable=True)  # email, mail, pickup, portal
    records_provided_count = Column(Integer, nullable=True)  # Number of records/pages provided
    records_withheld_count = Column(Integer, nullable=True)  # Number withheld (partial denial)
    response_summary = Column(Text, nullable=True)

    # Denial information
    denial_reason = Column(Text, nullable=True)
    exemptions_cited = Column(JSON, nullable=True)  # List of ExemptionType values

    # Appeal tracking
    appeal_filed = Column(Boolean, default=False, nullable=False)
    appeal_date = Column(DateTime(timezone=True), nullable=True)
    appeal_deadline = Column(Date, nullable=True)
    appeal_decision = Column(String(50), nullable=True)  # upheld, overturned, partial
    appeal_decision_date = Column(DateTime(timezone=True), nullable=True)

    # Internal notes (not disclosed)
    internal_notes = Column(Text, nullable=True)

    # Document references
    request_document_id = Column(String(255), nullable=True)  # Original request document
    response_document_id = Column(String(255), nullable=True)  # Response letter
    released_documents_path = Column(String(500), nullable=True)  # Path to released records

    # Metadata
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    meeting = relationship("BoardMeeting", foreign_keys=[meeting_id])
    committee = relationship("Committee", foreign_keys=[committee_id])

    audit_logs = relationship(
        "PublicRecordsAuditLog",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="PublicRecordsAuditLog.created_at"
    )
    redactions = relationship(
        "PublicRecordsRedaction",
        back_populates="request",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_prr_status_deadline', 'status', 'response_deadline'),
        Index('ix_prr_type_status', 'request_type', 'status'),
        Index('ix_prr_assigned', 'assigned_to_id', 'status'),
    )

    @property
    def is_overdue(self) -> bool:
        if self.status in [
            PublicRecordsRequestStatus.COMPLETED,
            PublicRecordsRequestStatus.DENIED,
            PublicRecordsRequestStatus.WITHDRAWN,
        ]:
            return False
        effective_deadline = self.extended_deadline or self.response_deadline
        return date.today() > effective_deadline

    @property
    def days_until_deadline(self) -> int:
        effective_deadline = self.extended_deadline or self.response_deadline
        return (effective_deadline - date.today()).days

    @property
    def effective_deadline(self) -> date:
        return self.extended_deadline or self.response_deadline

    def __repr__(self) -> str:
        return f"<PublicRecordsRequest(id={self.id}, tracking={self.tracking_number}, status={self.status})>"


class PublicRecordsAuditLog(Base):
    __tablename__ = "public_records_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(
        Integer,
        ForeignKey("public_records_requests.id", ondelete="CASCADE"),
        nullable=False
    )

    action = Column(SQLEnum(PublicRecordsAuditAction, values_callable=lambda x: [e.value for e in x]), nullable=False)

    performed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    details = Column(JSON, nullable=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    request = relationship("PublicRecordsRequest", back_populates="audit_logs")
    performed_by = relationship("User", foreign_keys=[performed_by_id])

    __table_args__ = (
        Index('ix_pra_request_action', 'request_id', 'action'),
        Index('ix_pra_date_range', 'created_at', 'request_id'),
    )

    def __repr__(self) -> str:
        return f"<PublicRecordsAuditLog(id={self.id}, request_id={self.request_id}, action={self.action})>"


class PublicRecordsRedaction(Base):
    __tablename__ = "public_records_redactions"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(
        Integer,
        ForeignKey("public_records_requests.id", ondelete="CASCADE"),
        nullable=False
    )

    # Document identification
    document_name = Column(String(255), nullable=False)
    page_number = Column(Integer, nullable=True)
    section_reference = Column(String(255), nullable=True)  # e.g., "Paragraph 3", "Row 5"

    # Redaction details
    exemption_type = Column(SQLEnum(ExemptionType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    exemption_description = Column(Text, nullable=True)  # Specific reason
    redaction_description = Column(Text, nullable=True)  # What was redacted (in general terms)

    # Who performed the redaction
    redacted_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    redacted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Review tracking
    reviewed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    request = relationship("PublicRecordsRequest", back_populates="redactions")
    redacted_by = relationship("User", foreign_keys=[redacted_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        Index('ix_prred_request_exemption', 'request_id', 'exemption_type'),
    )

    def __repr__(self) -> str:
        return f"<PublicRecordsRedaction(id={self.id}, document={self.document_name}, exemption={self.exemption_type})>"


def calculate_response_deadline(
    date_received: datetime,
    jurisdiction: JurisdictionType,
) -> date:
    business_days = JURISDICTION_DEADLINES.get(jurisdiction, 10)

    current_date = date_received.date()
    days_added = 0

    while days_added < business_days:
        current_date += timedelta(days=1)
        # Skip weekends (5 = Saturday, 6 = Sunday)
        if current_date.weekday() < 5:
            days_added += 1

    return current_date
