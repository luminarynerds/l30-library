# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from ..core.encryption import EncryptedString, EncryptedText


class ChallengeStatus(StrEnum):
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    COMMITTEE_REVIEW = "committee_review"
    BOARD_REVIEW = "board_review"
    RESOLVED_RETAINED = "resolved_retained"
    RESOLVED_RESTRICTED = "resolved_restricted"
    RESOLVED_REMOVED = "resolved_removed"
    WITHDRAWN = "withdrawn"


class ChallengeOutcome(StrEnum):
    RETAINED = "retained"  # Book stays in collection unchanged
    RETAINED_WITH_CHANGES = "retained_with_changes"  # Kept but moved/relabeled
    RESTRICTED = "restricted"  # Limited access (e.g., parent permission required)
    REMOVED = "removed"  # Removed from collection
    WITHDRAWN = "withdrawn"  # Challenger withdrew the complaint
    PENDING = "pending"  # Not yet resolved


class ChallengeReason(StrEnum):
    SEXUAL_CONTENT = "sexual_content"
    LGBTQ_CONTENT = "lgbtq_content"
    VIOLENCE = "violence"
    LANGUAGE = "language"
    RELIGIOUS_VIEWPOINT = "religious_viewpoint"
    POLITICAL_VIEWPOINT = "political_viewpoint"
    AGE_INAPPROPRIATE = "age_inappropriate"
    RACISM = "racism"
    DRUGS_ALCOHOL = "drugs_alcohol"
    ANTI_FAMILY = "anti_family"
    OCCULT_SUPERNATURAL = "occult_supernatural"
    OTHER = "other"


class BookChallenge(TimestampMixin, Base):
    __tablename__ = "book_challenges"

    id = Column(Integer, primary_key=True, index=True)

    # Book information (may or may not link to catalog)
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String(500), nullable=False)
    author = Column(String(255), nullable=True)
    isbn = Column(String(20), nullable=True)

    # Challenge details
    status = Column(
        SQLEnum(ChallengeStatus, values_callable=lambda x: [e.value for e in x]),
        default=ChallengeStatus.RECEIVED,
        nullable=False,
        index=True,
    )
    primary_reason = Column(
        SQLEnum(ChallengeReason, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    additional_reasons = Column(Text, nullable=True)  # JSON array of additional reasons
    # Encrypted at rest: this is a named person's stated objection to a book,
    # which for a library sits close to circulation data in sensitivity.
    # Ciphertext is longer than plaintext, hence the widened columns.
    # SQL equality, LIKE and ORDER BY do not work on these; see
    # core/encryption.py. The staff search deliberately no longer filters on
    # challenger_name for that reason.
    challenger_complaint = Column(EncryptedText, nullable=True)

    # Challenger information (optional, for internal tracking only)
    challenger_name = Column(EncryptedString(500), nullable=True)
    challenger_is_patron = Column(Boolean, default=True)
    challenger_contact = Column(EncryptedString(500), nullable=True)

    # Review process
    date_received = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date_resolved = Column(DateTime(timezone=True), nullable=True)
    outcome = Column(
        SQLEnum(ChallengeOutcome, values_callable=lambda x: [e.value for e in x]),
        default=ChallengeOutcome.PENDING,
        nullable=False,
    )

    # Resolution details
    resolution_summary = Column(Text, nullable=True)
    committee_notes = Column(Text, nullable=True)  # Internal staff notes

    # Public story (for intellectual freedom page)
    is_public = Column(Boolean, default=False, index=True)
    public_title = Column(String(255), nullable=True)  # Title for public display
    public_summary = Column(Text, nullable=True)  # Sanitized public summary
    lessons_learned = Column(Text, nullable=True)  # What we learned from this

    # Staff who handled the challenge
    assigned_staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata

    # Relationships
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])
    assigned_staff = relationship("User", foreign_keys=[assigned_staff_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


class BookChallengeNote(TimestampMixin, Base):
    __tablename__ = "book_challenge_notes"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(
        Integer, ForeignKey("book_challenges.id", ondelete="CASCADE"), nullable=False, index=True
    )

    note = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=True)  # True = staff only, False = can be public

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    challenge = relationship("BookChallenge", backref="notes")
    created_by = relationship("User")


class IntellectualFreedomResource(TimestampMixin, Base):
    __tablename__ = "intellectual_freedom_resources"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Markdown content
    url = Column(String(500), nullable=True)  # External link

    resource_type = Column(
        String(50), nullable=False
    )  # 'article', 'video', 'external_link', 'policy'
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
