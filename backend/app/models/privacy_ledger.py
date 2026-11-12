# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# =============================================================================
# Enums
# =============================================================================


class ConsentType(StrEnum):
    ACCOUNT_CREATION = "account_creation"
    READING_HISTORY_TRACKING = "reading_history_tracking"
    EMAIL_NOTIFICATIONS = "email_notifications"
    SMS_NOTIFICATIONS = "sms_notifications"
    MARKETING_COMMUNICATIONS = "marketing_communications"
    DATA_ANALYTICS = "data_analytics"
    THIRD_PARTY_SHARING = "third_party_sharing"
    PARENTAL_CONSENT = "parental_consent"
    PHOTO_RELEASE = "photo_release"
    EVENT_PHOTOGRAPHY = "event_photography"
    STAFF_ACCESS_TO_HISTORY = "staff_access_to_history"


class ConsentMethod(StrEnum):
    WEB_FORM = "web_form"
    IN_PERSON = "in_person"
    EMAIL_CONFIRMATION = "email_confirmation"
    PHONE = "phone"
    PAPER_FORM = "paper_form"
    API = "api"
    IMPLICIT_ACCOUNT_CREATION = "implicit_account_creation"


class ConsentStatus(StrEnum):
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class DataSharingPurpose(StrEnum):
    LAW_ENFORCEMENT_REQUEST = "law_enforcement_request"
    INTERLIBRARY_LOAN = "interlibrary_loan"
    PAYMENT_PROCESSING = "payment_processing"
    EMAIL_DELIVERY = "email_delivery"
    SMS_DELIVERY = "sms_delivery"
    ANALYTICS = "analytics"
    CONSORTIUM_SHARING = "consortium_sharing"
    COLLECTION_AGENCY = "collection_agency"
    INSURANCE_CLAIM = "insurance_claim"
    LEGAL_COMPLIANCE = "legal_compliance"


class CorrectionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"


# =============================================================================
# Models
# =============================================================================


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    __table_args__ = (
        Index("ix_consent_records_user_type", "user_id", "consent_type"),
        Index("ix_consent_records_user_status", "user_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    consent_type = Column(
        SQLEnum(ConsentType, name="consenttype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    status = Column(
        SQLEnum(ConsentStatus, name="consentstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    method = Column(
        SQLEnum(ConsentMethod, name="consentmethod", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # The version of the privacy policy or terms the patron agreed to
    policy_version = Column(String(50), nullable=True)

    # IP address from which consent was given (for web-based consent)
    ip_address = Column(String(45), nullable=True)

    # User agent string (for web-based consent)
    user_agent = Column(String(500), nullable=True)

    # Free-text details (e.g., specific wording shown, staff notes)
    details = Column(JSON, nullable=True)

    # Staff member who recorded consent (for in-person consent)
    recorded_by_staff_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # When consent expires (if applicable)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    recorded_by = relationship("User", foreign_keys=[recorded_by_staff_id])


class DataSharingLog(Base):
    __tablename__ = "data_sharing_logs"

    __table_args__ = (
        Index("ix_data_sharing_user_created", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Who received the data
    recipient_name = Column(String(255), nullable=False)
    recipient_type = Column(String(100), nullable=True)  # e.g., "law_enforcement", "vendor", "consortium"

    purpose = Column(
        SQLEnum(DataSharingPurpose, name="datasharingpurpose", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # What data was shared (list of field/category names)
    data_categories = Column(JSON, nullable=False)  # e.g., ["name", "email", "checkout_history"]

    # Legal basis for sharing
    legal_basis = Column(String(255), nullable=True)  # e.g., "court_order", "patron_consent", "contractual_necessity"

    # Reference to the triggering event (e.g., law enforcement request ID, ILL ID)
    reference_id = Column(String(255), nullable=True)
    reference_type = Column(String(100), nullable=True)  # e.g., "law_enforcement_request", "interlibrary_loan"

    # Whether the patron was notified (and when)
    patron_notified = Column(Boolean, default=False, nullable=False)
    patron_notified_at = Column(DateTime(timezone=True), nullable=True)

    # Staff member who authorized/performed the sharing
    shared_by_staff_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Additional context
    notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    shared_by = relationship("User", foreign_keys=[shared_by_staff_id])


class DataCorrectionLog(Base):
    __tablename__ = "data_correction_logs"

    __table_args__ = (
        Index("ix_data_correction_user_created", "user_id", "created_at"),
        Index("ix_data_correction_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Which field was corrected
    field_name = Column(String(100), nullable=False)

    # Before and after values
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    # Why the correction was made
    reason = Column(Text, nullable=False)

    status = Column(
        SQLEnum(CorrectionStatus, name="correctionstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=CorrectionStatus.PENDING,
    )

    # Who requested the correction (patron themselves or staff on their behalf)
    requested_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Who approved/applied the correction (staff)
    processed_by_staff_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # When it was processed
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Staff notes on why correction was approved/rejected
    staff_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    processed_by = relationship("User", foreign_keys=[processed_by_staff_id])
