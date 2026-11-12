# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import enum
from enum import Enum, StrEnum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, LargeBinary
from sqlalchemy.orm import relationship

from ..core.database import Base


class EvidenceType(StrEnum):
    GOVERNMENT_ID = "government_id"
    SOCIAL_PROFILE = "social_profile"
    PUBLICATION_LINK = "publication_link"


class EvidenceStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ADDITIONAL_NEEDED = "additional_needed"
    EXPIRED = "expired"


class AuthorIdentityEvidence(Base):
    __tablename__ = "author_identity_evidence"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("indie_authors.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type = Column(Enum(EvidenceType, values_callable=lambda x: [m.value for m in x]), nullable=False)
    status = Column(Enum(EvidenceStatus, values_callable=lambda x: [m.value for m in x]), default=EvidenceStatus.PENDING, nullable=False, index=True)

    # For social_profile / publication_link
    url = Column(String(500), nullable=True)

    # For government_id — encrypted file stored as bytes
    encrypted_file = Column(LargeBinary, nullable=True)
    file_content_type = Column(String(50), nullable=True)
    file_name = Column(String(200), nullable=True)

    # Review
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)

    reviewer = relationship("User", foreign_keys=[reviewer_id])
