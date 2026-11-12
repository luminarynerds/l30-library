# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Index, Integer, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy import text as sa_text
from sqlalchemy.orm import relationship

from ..core.database import Base


class SupportTicketStatus(StrEnum):

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicketContactMethod(StrEnum):

    EMAIL = "email"
    PHONE = "phone"
    VISIT = "visit"


class SupportTicketCategory(StrEnum):

    REFERENCE = "reference"
    CIRCULATION = "circulation"
    PROGRAMS_EVENTS = "programs_events"
    YOUTH = "youth"
    TEEN = "teen"
    ACQUISITIONS = "acquisitions"
    ILL = "ill"
    ACCESSIBILITY = "accessibility"
    DISCRIMINATION = "discrimination"
    BOOK_CONCERN = "book_concern"
    RECORDS_REQUEST = "records_request"
    BOARD = "board"
    DONATION = "donation"
    WEBSITE_BUG = "website_bug"
    GENERAL = "general"


class SupportTicketEventType(StrEnum):

    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    CATEGORY_CHANGED = "category_changed"
    NOTE_ADDED = "note_added"
    RESPONSE_SENT = "response_sent"
    HONEYPOT_REJECTED = "honeypot_rejected"


class SupportTicket(Base):

    __tablename__ = "support_tickets"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Ticket identification
    ticket_number = Column(String(50), unique=True, index=True, nullable=False)

    # Patron information
    # name/email relaxed to nullable for anonymous + COPPA-safe under-13 +
    # "no reply needed" submissions from the patron contact page. The
    # escalation modal still supplies both; see contact_form_fields_001
    # migration.
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)

    # Guide/context information
    guide_title = Column(String(255), nullable=True)
    step_number = Column(Integer, nullable=True)
    total_steps = Column(Integer, nullable=True)

    # Issue details
    issue_description = Column(Text, nullable=False)

    # Routing category. Stored as a plain string (not a postgres enum) so
    # adding new categories does not require a migration to ALTER the enum
    # type. Validate via SupportTicketCategory at the schema layer.
    category = Column(String(64), nullable=True, index=True)

    # Patron-supplied short subject (optional). Free-text for the staff list view.
    subject_line = Column(String(255), nullable=True)

    # When true, server strips identifying fields (name/email/phone) on insert
    # and triage UI suppresses them in the timeline. See create_support_ticket.
    is_anonymous = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))

    # Routing destination string derived from category at submit time, e.g.
    # "ada_coordinator", "records_officer", "circulation". Stored so triage
    # can filter without re-deriving from category.
    response_route = Column(String(64), nullable=True)

    # Contact preference
    contact_method = Column(SQLEnum(SupportTicketContactMethod, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Status tracking
    status = Column(SQLEnum(SupportTicketStatus, values_callable=lambda x: [e.value for e in x]), default=SupportTicketStatus.OPEN, index=True)

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Optional staff assignment and notes
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    internal_notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SupportTicket(id={self.id}, ticket_number={self.ticket_number}, status={self.status})>"


class SupportTicketEvent(Base):

    __tablename__ = "support_ticket_events"
    __table_args__ = (
        Index("ix_support_ticket_events_ticket", "ticket_id", "created_at"),
        Index("ix_support_ticket_events_type", "event_type", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(
        Integer,
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(40), nullable=False)

    actor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Denormalized identifier so the event row survives a user deletion.
    actor_identifier = Column(String(255), nullable=True)

    # For status/assignment/category transitions; free-form note for responses.
    from_value = Column(String(255), nullable=True)
    to_value = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<SupportTicketEvent(id={self.id}, ticket_id={self.ticket_id}, "
            f"event_type={self.event_type})>"
        )
