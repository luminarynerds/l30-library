# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, DateTime, Index, Integer, String, Text
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class CardApplicationStatus(StrEnum):
    pending = "pending"
    under_review = "under_review"
    approved = "approved"
    denied = "denied"


class LibraryCardApplication(Base):
    __tablename__ = "library_card_applications"

    id = Column(Integer, primary_key=True, index=True)

    # Applicant information (stored even if user doesn't exist yet)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Application details
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(DateTime(timezone=True), nullable=True)

    # Address information
    address_line1 = Column(String(200), nullable=False)
    address_line2 = Column(String(200), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    zip_code = Column(String(20), nullable=False)

    # Identification for verification
    id_type = Column(String(50), nullable=True)  # e.g., "driver_license", "passport", "utility_bill"
    id_number_last4 = Column(String(4), nullable=True)  # Last 4 digits only for privacy

    # Application status
    status = Column(
        SQLEnum(CardApplicationStatus, name="cardapplicationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CardApplicationStatus.pending,
        nullable=False
    )

    # Processing information
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    denial_reason = Column(Text, nullable=True)

    # Generated card number (assigned upon approval)
    assigned_card_number = Column(String(50), nullable=True, unique=True, index=True)

    # Random token for unauthenticated status lookup via emailed link.
    # Nullable so legacy rows (pre-Issue #1028) just have no public link;
    # those patrons must contact the library directly.
    check_token = Column(String(64), nullable=True, unique=True, index=True)

    # Timestamps, server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="card_applications")
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        Index("ix_card_applications_status_submitted", "status", "submitted_at"),
        Index("ix_card_applications_email_status", "email", "status"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_pending(self) -> bool:
        return self.status == CardApplicationStatus.pending

    @property
    def is_approved(self) -> bool:
        return self.status == CardApplicationStatus.approved

    @property
    def is_denied(self) -> bool:
        return self.status == CardApplicationStatus.denied
