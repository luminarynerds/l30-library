# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin, SoftDeleteMixin

from ..core.database import Base


class NoteCategory(StrEnum):

    GENERAL = "general"
    ACCOMMODATION_NEEDS = "accommodation_needs"
    INCIDENT = "incident"
    FOLLOW_UP = "follow_up"
    PATRON_PREFERENCE = "patron_preference"  # Large print, fragile items, etc.
    OTHER = "other"


class NotePriority(StrEnum):

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageType(StrEnum):

    OVERDUE_NOTICE = "overdue_notice"
    HOLD_READY = "hold_ready"
    FINE_REMINDER = "fine_reminder"
    ACCOUNT_BLOCKED = "account_blocked"
    WELCOME_NEW_PATRON = "welcome_new_patron"
    CUSTOM = "custom"


class MessageChannel(StrEnum):

    EMAIL = "email"
    SMS = "sms"
    PRINT = "print"


class MessageStatus(StrEnum):

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    PRINTED = "printed"


class PatronNote(Base, TimestampMixin, SoftDeleteMixin):

    __tablename__ = "patron_notes"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    category = Column(
        SQLEnum(NoteCategory, name="notecategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=NoteCategory.GENERAL,
        nullable=False,
        index=True,
    )

    content = Column(Text, nullable=False)

    # Priority level for the note (helps staff identify urgent issues)
    priority = Column(
        SQLEnum(NotePriority, name="notepriority", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=NotePriority.NORMAL,
        nullable=False,
        index=True,
    )

    # Visibility control
    is_branch_shared = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="If true, visible to all branches; if false, only visible to patron's home branch"
    )
    visible_to_branch_ids = Column(
        String(500),
        nullable=True,
        comment="Comma-separated list of branch IDs that can see this note"
    )

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="patron_notes")
    author = relationship("User", foreign_keys=[author_id])
    note_audits = relationship(
        "NoteAudit",
        back_populates="note",
        cascade="all, delete-orphan",
        foreign_keys="NoteAudit.note_id"
    )


class PatronMessage(Base):

    __tablename__ = "patron_messages"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    message_type = Column(
        SQLEnum(MessageType, name="messagetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MessageType.CUSTOM,
        nullable=False,
        index=True,
    )

    channel = Column(
        SQLEnum(MessageChannel, name="messagechannel", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MessageChannel.EMAIL,
        nullable=False,
    )

    # Message content
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)

    # Recipient info (stored at send time for historical accuracy)
    recipient_email = Column(String(255), nullable=True)
    recipient_phone = Column(String(20), nullable=True)

    # Status tracking
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered = Column(Boolean, default=True, nullable=False)
    delivery_error = Column(Text, nullable=True)
    status = Column(
        SQLEnum(MessageStatus, name="messagestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MessageStatus.SENT,
        nullable=False,
        index=True,
    )

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="patron_messages")
    sender = relationship("User", foreign_keys=[sender_id])


class NoteAudit(Base):

    __tablename__ = "note_audits"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(
        Integer, ForeignKey("patron_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action = Column(String(50), nullable=False)  # 'created', 'updated', 'deleted', 'restored'
    changed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # What changed (for updates)
    previous_content = Column(Text, nullable=True)
    new_content = Column(Text, nullable=True)
    previous_priority = Column(String(20), nullable=True)
    new_priority = Column(String(20), nullable=True)
    previous_category = Column(String(50), nullable=True)
    new_category = Column(String(50), nullable=True)

    # Audit metadata
    change_reason = Column(Text, nullable=True)  # Why the change was made, server_default=func.now(), nullable=False)

    # Relationships
    note = relationship("PatronNote", back_populates="note_audits")
    changed_by = relationship("User")


class NoteTemplate(Base):

    __tablename__ = "note_templates"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    content_template = Column(Text, nullable=False)  # Template text (can include placeholders)

    # Template organization
    category = Column(
        SQLEnum(NoteCategory, name="notecategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=NoteCategory.GENERAL,
        nullable=False,
        index=True,
    )
    priority = Column(
        SQLEnum(NotePriority, name="notepriority", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=NotePriority.NORMAL,
        nullable=False,
    )

    # Usage metadata
    usage_count = Column(Integer, default=0, nullable=False)  # Track popularity
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)  # Soft deactivation

    # Audit
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User")


class PatronPreference(Base):

    __tablename__ = "patron_preferences"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Print preferences
    prefers_large_print = Column(Boolean, default=False, nullable=False)
    prefers_audio_format = Column(Boolean, default=False, nullable=False)
    prefers_braille = Column(Boolean, default=False, nullable=False)

    # Item handling preferences
    handle_fragile_items_with_care = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag for fragile items; staff should check items before checkout"
    )
    limited_mobility_assistance_needed = Column(Boolean, default=False, nullable=False)
    needs_extra_time_checkout = Column(Boolean, default=False, nullable=False)

    # Additional notes about preferences
    preference_notes = Column(Text, nullable=True)

    # Metadata
    set_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="preferences")
    set_by = relationship("User", foreign_keys=[set_by_id])
