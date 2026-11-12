# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class StaffPanicAlertStatus(StrEnum):
    ACTIVATED = "activated"      # Just triggered
    ACKNOWLEDGED = "acknowledged"  # Responder received notification
    RESPONDED = "responded"      # Responder en route or arrived
    RESOLVED = "resolved"        # Incident handled
    FALSE_ALARM = "false_alarm"  # Cancelled before responder arrival


class SafetyIncidentType(StrEnum):
    THREAT = "threat"            # Physical threat or threat of violence
    HARASSMENT = "harassment"    # Verbal harassment or hostile behavior
    ASSAULT = "assault"          # Physical assault
    DISCRIMINATION = "discrimination"  # Discriminatory treatment
    THEFT = "theft"              # Theft from staff
    UNSAFE_CONDITIONS = "unsafe_conditions"  # Safety hazards
    RETALIATION = "retaliation"  # Suspected retaliation
    OTHER = "other"              # Other safety concerns


class SafetyIncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    REPORTED = "reported"        # Initial report filed
    UNDER_REVIEW = "under_review"  # Management investigating
    ACTION_TAKEN = "action_taken"  # Corrective action implemented
    CLOSED = "closed"            # Investigation complete
    ESCALATED = "escalated"      # Escalated to union/HR


class AnonymityLevel(StrEnum):
    IDENTIFIED = "identified"    # Staff identity disclosed
    SEMI_ANONYMOUS = "semi_anonymous"  # Known to management only
    FULLY_ANONYMOUS = "fully_anonymous"  # Completely anonymous


class StaffPanicAlert(Base):
    __tablename__ = "staff_panic_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Who activated it
    staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # When and where
    activated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    location = Column(String(200), nullable=True)  # e.g., "Main Desk", "Tech Department"

    # Alert status
    status = Column(
        String(50),
        default=StaffPanicAlertStatus.ACTIVATED,
        nullable=False,
        index=True
    )

    # Who responded
    responder_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Response details
    response_notes = Column(Text, nullable=True)

    # Union notification
    union_notified = Column(Boolean, default=False, nullable=False)
    union_notified_at = Column(DateTime(timezone=True), nullable=True)

    # Data retention
    data_retention_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete for retention

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id], primaryjoin="StaffPanicAlert.staff_id == User.id")
    responder = relationship("User", foreign_keys=[responder_id], primaryjoin="StaffPanicAlert.responder_id == User.id")


class StaffIncidentReport(Base):
    __tablename__ = "staff_incident_reports"

    id = Column(Integer, primary_key=True, index=True)

    # Who reported
    reporting_staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Incident details
    incident_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    incident_date = Column(DateTime(timezone=True), nullable=False)
    incident_location = Column(String(200), nullable=True)

    severity = Column(
        String(50),
        default=SafetyIncidentSeverity.MEDIUM,
        nullable=False
    )

    status = Column(
        String(50),
        default=IncidentStatus.REPORTED,
        nullable=False,
        index=True
    )

    # Report details
    description = Column(Text, nullable=False)
    witness_ids = Column(JSON, nullable=True)  # Array of witness user IDs

    # Anonymity
    anonymity_level = Column(
        String(50),
        default=AnonymityLevel.IDENTIFIED,
        nullable=False
    )

    # Is this good-faith report (no punishment)
    is_good_faith = Column(Boolean, default=True, nullable=False)
    good_faith_reason = Column(String(500), nullable=True)

    # Management response
    management_response = Column(Text, nullable=True)
    management_response_date = Column(DateTime(timezone=True), nullable=True)
    responded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Union notification
    union_notified = Column(Boolean, default=False, nullable=False)
    union_notified_at = Column(DateTime(timezone=True), nullable=True)

    # Confidentiality tracking
    accessed_by_ids = Column(JSON, nullable=True)  # Audit trail of who viewed this

    # Timestamps, server_default=func.now(), nullable=False), onupdate=func.now(), nullable=True)

    # Data retention
    data_retention_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete for retention

    # Relationships
    reporting_staff = relationship("User", foreign_keys=[reporting_staff_id])
    responded_by = relationship("User", foreign_keys=[responded_by_id])


class AnonymousIncidentPattern(Base):
    __tablename__ = "anonymous_incident_patterns"

    id = Column(Integer, primary_key=True, index=True)

    # Pattern aggregation
    incident_type = Column(
        String(50),
        nullable=False,
        index=True
    )

    location = Column(String(200), nullable=True, index=True)

    # Time window
    date_start = Column(DateTime(timezone=True), nullable=False)
    date_end = Column(DateTime(timezone=True), nullable=False)

    # Counts (anonymized)
    report_count = Column(Integer, default=0, nullable=False)
    average_severity = Column(String(50), nullable=True)

    # Pattern notes (no identifying information)
    pattern_summary = Column(Text, nullable=True)

    # Recommended actions (director/admin only)
    recommended_actions = Column(Text, nullable=True)

    # Timestamps, server_default=func.now(), nullable=False), onupdate=func.now(), nullable=True)


class RetaliationPreventionPolicy(Base):
    __tablename__ = "retaliation_prevention_policies"

    id = Column(Integer, primary_key=True, index=True)

    # Policy identification
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=False)

    # Policy details
    policy_type = Column(String(100), nullable=False)  # e.g., "no_retaliation", "good_faith_protection"
    effective_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Policy provisions (key protections)
    key_provisions = Column(JSON, nullable=True)  # Array of provision descriptions

    # Who can use this policy
    applicable_to_roles = Column(JSON, nullable=True)  # e.g., ["STAFF", "ADMIN"]

    # Consequences of violations
    violation_consequences = Column(Text, nullable=True)

    # Union reference
    union_agreement_reference = Column(String(500), nullable=True)

    # Authority
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Audit, server_default=func.now(), nullable=False), onupdate=func.now(), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])


class StaffProtectionMeasure(Base):
    __tablename__ = "staff_protection_measures"

    id = Column(Integer, primary_key=True, index=True)

    # Who is being protected
    staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # What measure was taken
    measure_type = Column(String(100), nullable=False)  # e.g., "schedule_adjustment", "work_location_change"
    description = Column(Text, nullable=False)

    # Related to incident
    incident_report_id = Column(Integer, ForeignKey("staff_incident_reports.id", ondelete="SET NULL"), nullable=True)

    # Timeline
    effective_date = Column(DateTime(timezone=True), nullable=False)
    expected_end_date = Column(DateTime(timezone=True), nullable=True)  # Null = ongoing

    # Effectiveness tracking
    is_active = Column(Boolean, default=True, nullable=False)
    effectiveness_notes = Column(Text, nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)

    # Authority
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps, server_default=func.now(), nullable=False), onupdate=func.now(), nullable=True)

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id])
    incident_report = relationship("StaffIncidentReport")
    approved_by = relationship("User", foreign_keys=[approved_by_id])


class StaffSupportResource(Base):
    __tablename__ = "staff_support_resources"

    id = Column(Integer, primary_key=True, index=True)

    # Resource details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    resource_type = Column(String(100), nullable=False)  # e.g., "mental_health", "legal", "union", "safety"

    # Contact information
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    text_number = Column(String(20), nullable=True)

    # Availability
    hours = Column(String(500), nullable=True)  # e.g., "24/7", "Mon-Fri 9am-5pm"
    is_available_24_7 = Column(Boolean, default=False, nullable=False)
    is_anonymous = Column(Boolean, default=False, nullable=False)

    # Coverage
    is_active = Column(Boolean, default=True, nullable=False)
    is_union_resource = Column(Boolean, default=False, nullable=False)

    # Timestamps, server_default=func.now(), nullable=False), onupdate=func.now(), nullable=True)


class DataRetentionPolicy(Base):
    __tablename__ = "data_retention_policies"

    id = Column(Integer, primary_key=True, index=True)

    # Policy details
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    data_type = Column(String(100), nullable=False)  # e.g., "panic_alerts", "incident_reports"

    # Retention duration
    retention_years = Column(Integer, default=3, nullable=False)
    retention_description = Column(String(500), nullable=True)  # e.g., "3 years or duration of employment + 2 years"

    # Deletion method
    deletion_method = Column(String(100), default="soft_delete", nullable=False)  # "soft_delete" or "purge"

    # Exceptions
    has_legal_hold_exception = Column(Boolean, default=False, nullable=False)
    has_union_agreement_exception = Column(Boolean, default=False, nullable=False)

    # Authority
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    effective_date = Column(DateTime(timezone=True), nullable=False)

    # Timestamps, server_default=func.now(), nullable=False), onupdate=func.now(), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
