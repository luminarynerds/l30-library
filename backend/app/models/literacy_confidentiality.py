# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum, StrEnum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, String, Text, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class LiteracyAuditAction(StrEnum):
    DATA_ACCESSED = "data_accessed"
    ASSESSMENT_VIEWED = "assessment_viewed"
    NOTES_VIEWED = "notes_viewed"
    CONTACT_INFO_ACCESSED = "contact_info_accessed"
    CONFIDENTIAL_FIELD_ACCESSED = "confidential_field_accessed"
    SESSION_NOTES_VIEWED = "session_notes_viewed"
    GOAL_VIEWED = "goal_viewed"
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    DATA_EXPORTED = "data_exported"


class LiteracyConsentType(StrEnum):
    DATA_COLLECTION = "data_collection"  # Allow collecting learner data
    OUTCOME_REPORTING = "outcome_reporting"  # Use data in reports/publications
    PARTNER_SHARING = "partner_sharing"  # Share data with partner organizations
    PHOTO_VIDEO = "photo_video"  # Use photos/videos for promotion
    RESEARCH_USE = "research_use"  # Use anonymized data in research
    COMMUNICATION = "communication"  # Send program updates
    REFERRAL = "referral"  # Allow referrals to partners


class LiteracyConsentStatus(StrEnum):
    PENDING = "pending"  # Not yet obtained
    ACCEPTED = "accepted"  # Learner/guardian consented
    DECLINED = "declined"  # Learner/guardian declined
    REVOKED = "revoked"  # Previously granted, now revoked
    EXPIRED = "expired"  # Consent period ended


class LiteracyAuditLog(Base, TimestampMixin):
    __tablename__ = "literacy_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="SET NULL"), nullable=True)

    # ==================== ACTION TRACKING ====================
    action = Column(
        String(50),
        nullable=False,
        index=True
    )
    action_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # ==================== RESOURCE ACCESSED ====================
    resource_type = Column(String(50), nullable=True)  # "learner_profile", "assessment", "session_notes", etc.
    resource_id = Column(Integer, nullable=True)  # ID of the resource accessed
    field_accessed = Column(String(255), nullable=True)  # Specific field (for sensitive data)

    # ==================== CONTEXT ====================
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    access_reason = Column(String(255), nullable=True)  # Why they were accessing (if required)
    access_purpose = Column(String(255), nullable=True)  # e.g., "session_preparation", "assessment_review"

    # ==================== RESULT ====================
    access_granted = Column(Boolean, default=True)  # Was access allowed?
    denial_reason = Column(String(255), nullable=True)  # If access was denied

    # ==================== DETAILS ====================
    details = Column(JSON, nullable=True)  # Additional context as JSON
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    user = relationship("User", backref="literacy_audit_logs")
    learner = relationship("LiteracyLearner", backref="access_audit_logs")

    __table_args__ = (
        Index("idx_literacy_audit_learner_date", learner_id, action_date),
        Index("idx_literacy_audit_user_date", user_id, action_date),
        Index("idx_literacy_audit_action_date", action, action_date),
    )


class LiteracyConsentRecord(Base, TimestampMixin):
    __tablename__ = "literacy_consent_records"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)
    guardian_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # ==================== CONSENT DETAILS ====================
    consent_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    status = Column(
        String(50),
        default=LiteracyConsentStatus.PENDING,
        nullable=False,
        index=True
    )

    # ==================== DATES ====================
    requested_date = Column(DateTime(timezone=True), nullable=False)
    response_date = Column(DateTime(timezone=True), nullable=True)  # When consent was given/denied
    expiration_date = Column(DateTime(timezone=True), nullable=True)  # When consent expires

    # ==================== DOCUMENTATION ====================
    consent_text = Column(Text, nullable=True)  # The exact consent text presented
    consent_document_url = Column(Text, nullable=True)  # Link to signed consent form
    consent_method = Column(String(50), nullable=True)  # "digital_form", "paper_form", "verbal", "email"

    # ==================== TRACKING ====================
    ip_address = Column(String(50), nullable=True)  # Where consent was given from
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    learner = relationship("LiteracyLearner", back_populates="consent_records")
    guardian = relationship("User", backref="literacy_consents_given")

    __table_args__ = (
        Index("idx_literacy_consent_learner_type", learner_id, consent_type),
        Index("idx_literacy_consent_status", status),
    )


class LiteracyConfidentialityMask(Base):
    __tablename__ = "literacy_confidentiality_masks"

    id = Column(Integer, primary_key=True, index=True)

    # ==================== FIELD IDENTIFICATION ====================
    record_type = Column(String(100), nullable=False)  # Model/table name
    field_name = Column(String(100), nullable=False)  # Field to mask
    record_id = Column(Integer, nullable=True)  # Specific record (null = applies to all)

    # ==================== MASKING CONFIGURATION ====================
    is_masked = Column(Boolean, default=True, nullable=False)
    access_level_required = Column(String(50), nullable=True)  # "admin", "director", "staff", etc.
    mask_reason = Column(String(255), nullable=True)  # e.g., "personal_health_information", "income_level"

    # ==================== TRACKING ====================
    effective_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_literacy_mask_record_field", record_type, field_name),
    )


class LiteracyDataAccessPolicy(Base, TimestampMixin):
    __tablename__ = "literacy_data_access_policies"

    id = Column(Integer, primary_key=True, index=True)

    # ==================== POLICY IDENTIFICATION ====================
    policy_name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # ==================== ROLE-BASED ACCESS ====================
    applicable_role = Column(String(50), nullable=False)  # e.g., "STAFF", "ADMIN", "TUTOR"

    # ==================== ACCESSIBLE DATA FIELDS ====================
    # JSON structure defining what fields are accessible
    accessible_learner_fields = Column(JSON, default={}, nullable=False)
    accessible_assessment_fields = Column(JSON, default={}, nullable=False)
    accessible_session_fields = Column(JSON, default={}, nullable=False)
    accessible_confidential_fields = Column(JSON, default={}, nullable=False)

    # ==================== CONSTRAINTS ====================
    requires_consent = Column(Boolean, default=False)  # Must have explicit consent
    requires_approval = Column(Boolean, default=False)  # Requires director/admin approval
    audit_log_required = Column(Boolean, default=True)  # Always log access
    can_export_data = Column(Boolean, default=False)
    can_share_with_partners = Column(Boolean, default=False)

    # ==================== TRACKING ====================
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_literacy_policy_active", is_active),
    )


class LiteracyAccessRequest(Base, TimestampMixin):
    __tablename__ = "literacy_access_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False)

    # ==================== REQUEST DETAILS ====================
    request_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    data_requested = Column(Text, nullable=False)  # Description of what data is requested
    access_reason = Column(Text, nullable=False)  # Why the data is needed
    access_duration = Column(String(100), nullable=True)  # "one_time", "session", "project", etc.

    # ==================== APPROVAL ====================
    approved = Column(Boolean, nullable=True)  # Null = pending, True = approved, False = denied
    approval_date = Column(DateTime(timezone=True), nullable=True)
    approver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    denial_reason = Column(Text, nullable=True)

    # ==================== TRACKING ====================
    data_accessed_date = Column(DateTime(timezone=True), nullable=True)
    access_expires_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    requester = relationship("User", foreign_keys=[requester_id], backref="literacy_access_requests_made")
    learner = relationship("LiteracyLearner", backref="access_requests")
    approver = relationship("User", foreign_keys=[approver_id], backref="literacy_access_requests_approved")

    __table_args__ = (
        Index("idx_literacy_access_request_learner", learner_id),
        Index("idx_literacy_access_request_status", approved),
    )
