# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base
from .mixins import TimestampMixin


class RequestType(StrEnum):
    SUBPOENA = "subpoena"
    WARRANT = "warrant"
    NATIONAL_SECURITY_LETTER = "national_security_letter"
    COURT_ORDER = "court_order"
    INFORMAL_REQUEST = "informal_request"  # Should always be declined


class LegalReviewStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_MODIFICATION = "requires_modification"
    APPEALING = "appealing"


class WorkflowStatus(StrEnum):
    RECEIVED = "received"
    VALIDATING = "validating"
    LEGAL_REVIEW = "legal_review"
    PATRON_NOTIFICATION = "patron_notification"
    PREPARING_RESPONSE = "preparing_response"
    RESPONSE_SENT = "response_sent"
    COMPLETED = "completed"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ChecklistItemType(StrEnum):
    RECEIVE_REQUEST = "receive_request"
    VERIFY_VALIDITY = "verify_validity"
    VERIFY_JURISDICTION = "verify_jurisdiction"
    VERIFY_SCOPE = "verify_scope"
    LEGAL_REVIEW = "legal_review"
    DIRECTOR_APPROVAL = "director_approval"
    NOTIFY_PATRON = "notify_patron"
    PREPARE_RESPONSE = "prepare_response"
    MINIMIZE_DATA = "minimize_data"
    DOCUMENT_COMPLIANCE = "document_compliance"
    SEND_RESPONSE = "send_response"
    FINAL_REVIEW = "final_review"


class AuditActionType(StrEnum):
    REQUEST_CREATED = "request_created"
    REQUEST_UPDATED = "request_updated"
    STATUS_CHANGED = "status_changed"
    LEGAL_REVIEW_UPDATED = "legal_review_updated"
    CHECKLIST_UPDATED = "checklist_updated"
    DOCUMENT_ATTACHED = "document_attached"
    DOCUMENT_REMOVED = "document_removed"
    PATRON_NOTIFIED = "patron_notified"
    RESPONSE_PREPARED = "response_prepared"
    RESPONSE_SENT = "response_sent"
    DATA_EXPORTED = "data_exported"
    NOTE_ADDED = "note_added"
    VIEWED = "viewed"


class LawEnforcementRequest(Base):
    __tablename__ = "law_enforcement_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Unique tracking number for the request
    tracking_number = Column(String(50), unique=True, nullable=False, index=True)

    # Agency information
    requesting_agency = Column(String(255), nullable=False)
    agency_contact_name = Column(String(200), nullable=True)
    agency_contact_phone = Column(String(50), nullable=True)
    agency_contact_email = Column(String(255), nullable=True)
    agency_case_number = Column(String(100), nullable=True)

    # Request details
    request_type = Column(
        SQLEnum(RequestType, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    date_received = Column(DateTime(timezone=True), nullable=False)
    date_due = Column(DateTime(timezone=True), nullable=True)  # Deadline for response

    # Affected patron
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Nullable in case patron is deleted
    )
    patron_name_on_request = Column(String(200), nullable=True)  # Name as appears on request
    patron_identifiers = Column(Text, nullable=True)  # Other identifiers (address, card #, etc.)

    # What data is being requested
    data_requested = Column(Text, nullable=False)
    data_date_range_start = Column(DateTime(timezone=True), nullable=True)
    data_date_range_end = Column(DateTime(timezone=True), nullable=True)

    # Legal review
    legal_review_status = Column(
        SQLEnum(LegalReviewStatus, values_callable=lambda x: [e.value for e in x]),
        default=LegalReviewStatus.PENDING_REVIEW,
        nullable=False,
        index=True,
    )
    legal_reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    legal_review_date = Column(DateTime(timezone=True), nullable=True)
    legal_review_notes = Column(Text, nullable=True)

    # Workflow status
    workflow_status = Column(
        SQLEnum(WorkflowStatus, values_callable=lambda x: [e.value for e in x]),
        default=WorkflowStatus.RECEIVED,
        nullable=False,
    )

    # Response tracking
    response_date = Column(DateTime(timezone=True), nullable=True)
    responding_staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    response_method = Column(String(100), nullable=True)  # email, mail, in-person, etc.
    response_summary = Column(Text, nullable=True)
    data_provided_summary = Column(Text, nullable=True)  # What was actually provided

    # Patron notification
    patron_notification_permitted = Column(Boolean, default=True, nullable=False)
    patron_notification_date = Column(DateTime(timezone=True), nullable=True)
    patron_notification_method = Column(String(100), nullable=True)
    gag_order_until = Column(DateTime(timezone=True), nullable=True)  # NSL gag order expiration

    # Document references (stored in separate secure location)
    original_request_document_id = Column(String(255), nullable=True)
    response_document_id = Column(String(255), nullable=True)

    # Internal notes (not shared externally)
    internal_notes = Column(Text, nullable=True)

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="law_enforcement_requests")
    legal_reviewer = relationship("User", foreign_keys=[legal_reviewer_id])
    responding_staff = relationship("User", foreign_keys=[responding_staff_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    audit_logs = relationship(
        "LawEnforcementAuditLog",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="LawEnforcementAuditLog.created_at",
    )
    checklist_items = relationship(
        "LawEnforcementChecklist", back_populates="request", cascade="all, delete-orphan"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_le_request_date_status", "date_received", "workflow_status"),
        Index("ix_le_request_type_status", "request_type", "workflow_status"),
        # Note: Functional index on EXTRACT requires IMMUTABLE function workaround
        # Index('ix_le_request_year', func.extract('year', date_received)),
    )

    def __repr__(self) -> str:
        return f"<LawEnforcementRequest(id={self.id}, tracking={self.tracking_number}, type={self.request_type})>"


class LawEnforcementAuditLog(Base):
    __tablename__ = "law_enforcement_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Link to the request
    request_id = Column(
        Integer, ForeignKey("law_enforcement_requests.id", ondelete="CASCADE"), nullable=False
    )

    # What action was taken
    action = Column(
        SQLEnum(AuditActionType, values_callable=lambda x: [e.value for e in x]), nullable=False
    )

    # Who performed the action
    performed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Details of the action (JSON for flexibility)
    # Contains: old_value, new_value, field_changed, etc.
    details = Column(JSON, nullable=True)

    # Security metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Timestamp (immutable - set once at creation)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    request = relationship("LawEnforcementRequest", back_populates="audit_logs")
    performed_by = relationship("User", foreign_keys=[performed_by_id])

    __table_args__ = (
        Index("ix_le_audit_request_action", "request_id", "action"),
        Index("ix_le_audit_date_range", "created_at", "request_id"),
    )

    def __repr__(self) -> str:
        return f"<LawEnforcementAuditLog(id={self.id}, request_id={self.request_id}, action={self.action})>"


class LawEnforcementChecklist(Base):
    __tablename__ = "law_enforcement_checklists"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(
        Integer, ForeignKey("law_enforcement_requests.id", ondelete="CASCADE"), nullable=False
    )

    item_type = Column(
        SQLEnum(ChecklistItemType, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    item_description = Column(String(500), nullable=False)

    # Completion tracking
    is_completed = Column(Boolean, default=False, nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)
    is_applicable = Column(Boolean, default=True, nullable=False)  # Some items may not apply

    completed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Order for display
    sort_order = Column(Integer, default=0, nullable=False)

    # Timestamps, server_default=func.now())

    # Relationships
    request = relationship("LawEnforcementRequest", back_populates="checklist_items")
    completed_by = relationship("User", foreign_keys=[completed_by_id])

    __table_args__ = (
        UniqueConstraint("request_id", "item_type", name="uq_le_checklist_request_item"),
        Index("ix_le_checklist_status", "request_id", "is_completed"),
    )

    def __repr__(self) -> str:
        return f"<LawEnforcementChecklist(request_id={self.request_id}, item={self.item_type}, completed={self.is_completed})>"


class LawEnforcementResponseTemplate(Base, TimestampMixin):
    __tablename__ = "law_enforcement_response_templates"

    id = Column(Integer, primary_key=True)

    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Template category
    template_type = Column(String(50), nullable=False, index=True)
    # Types: acknowledgment, clarification, compliance, objection, partial_compliance, patron_notification

    # Which request types this template applies to
    applicable_request_types = Column(JSON, nullable=True)  # List of RequestType values

    # Template content with placeholders
    # Placeholders: {{agency_name}}, {{tracking_number}}, {{patron_name}}, {{date}}, etc.
    subject_template = Column(String(500), nullable=True)
    body_template = Column(Text, nullable=False)

    # Whether this template is currently active
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return f"<LawEnforcementResponseTemplate(id={self.id}, name={self.name})>"


# Default checklist items for new requests
DEFAULT_CHECKLIST_ITEMS = [
    {
        "item_type": ChecklistItemType.RECEIVE_REQUEST,
        "item_description": "Document receipt of request with date, time, and delivery method",
        "is_required": True,
        "sort_order": 1,
    },
    {
        "item_type": ChecklistItemType.VERIFY_VALIDITY,
        "item_description": "Verify request is in proper legal form (signed, dated, on official letterhead)",
        "is_required": True,
        "sort_order": 2,
    },
    {
        "item_type": ChecklistItemType.VERIFY_JURISDICTION,
        "item_description": "Verify requesting agency has jurisdiction over this matter",
        "is_required": True,
        "sort_order": 3,
    },
    {
        "item_type": ChecklistItemType.VERIFY_SCOPE,
        "item_description": "Review scope of request - ensure it is specific and not overly broad",
        "is_required": True,
        "sort_order": 4,
    },
    {
        "item_type": ChecklistItemType.LEGAL_REVIEW,
        "item_description": "Legal counsel reviews request and provides recommendation",
        "is_required": True,
        "sort_order": 5,
    },
    {
        "item_type": ChecklistItemType.DIRECTOR_APPROVAL,
        "item_description": "Library Director reviews and approves response plan",
        "is_required": True,
        "sort_order": 6,
    },
    {
        "item_type": ChecklistItemType.NOTIFY_PATRON,
        "item_description": "Notify affected patron of the request (if legally permitted)",
        "is_required": False,  # May be prohibited by gag order
        "sort_order": 7,
    },
    {
        "item_type": ChecklistItemType.PREPARE_RESPONSE,
        "item_description": "Prepare response documents and data export",
        "is_required": True,
        "sort_order": 8,
    },
    {
        "item_type": ChecklistItemType.MINIMIZE_DATA,
        "item_description": "Minimize data to only what is specifically requested and legally required",
        "is_required": True,
        "sort_order": 9,
    },
    {
        "item_type": ChecklistItemType.DOCUMENT_COMPLIANCE,
        "item_description": "Document all actions taken for compliance records",
        "is_required": True,
        "sort_order": 10,
    },
    {
        "item_type": ChecklistItemType.SEND_RESPONSE,
        "item_description": "Send response via secure method and document delivery",
        "is_required": True,
        "sort_order": 11,
    },
    {
        "item_type": ChecklistItemType.FINAL_REVIEW,
        "item_description": "Final review of complete file for transparency reporting",
        "is_required": True,
        "sort_order": 12,
    },
]
