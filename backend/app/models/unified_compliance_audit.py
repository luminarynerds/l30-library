# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# Enums
# ============================================================================

class RegulationType(StrEnum):
    CIPA = "cipa"
    COPPA = "coppa"
    FERPA = "ferpa"
    GDPR = "gdpr"
    ADA = "ada"
    PCI_DSS = "pci_dss"
    STATE_LIBRARY = "state_library"
    STATE_PRIVACY = "state_privacy"
    FOIA = "foia"
    ECPA = "ecpa"
    CUSTOM = "custom"


class RequirementStatus(StrEnum):
    not_implemented = "not_implemented"
    in_progress = "in_progress"
    implemented = "implemented"
    verified = "verified"
    non_compliant = "non_compliant"
    waiver_granted = "waiver_granted"
    not_applicable = "not_applicable"


class VerificationMethod(StrEnum):
    automated_scan = "automated_scan"
    manual_review = "manual_review"
    external_audit = "external_audit"
    self_attestation = "self_attestation"
    document_review = "document_review"
    system_check = "system_check"
    penetration_test = "penetration_test"


class ViolationSeverity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    informational = "informational"


class ViolationStatus(StrEnum):
    detected = "detected"
    confirmed = "confirmed"
    investigating = "investigating"
    remediating = "remediating"
    resolved = "resolved"
    accepted_risk = "accepted_risk"
    false_positive = "false_positive"


class RetentionAction(StrEnum):
    delete = "delete"
    anonymize = "anonymize"
    archive = "archive"
    flag_for_review = "flag_for_review"


class ComplianceIncidentSeverity(StrEnum):
    critical = "critical"
    major = "major"
    minor = "minor"
    near_miss = "near_miss"


class IncidentStatus(StrEnum):
    reported = "reported"
    triaging = "triaging"
    investigating = "investigating"
    containing = "containing"
    remediating = "remediating"
    resolved = "resolved"
    closed = "closed"


class IncidentCategory(StrEnum):
    data_breach = "data_breach"
    unauthorized_access = "unauthorized_access"
    policy_violation = "policy_violation"
    improper_disclosure = "improper_disclosure"
    retention_failure = "retention_failure"
    consent_violation = "consent_violation"
    filtering_failure = "filtering_failure"
    records_request_error = "records_request_error"
    training_lapse = "training_lapse"
    system_misconfiguration = "system_misconfiguration"
    other = "other"


class AccessType(StrEnum):
    view = "view"
    search = "search"
    export = "export"
    modify = "modify"
    delete = "delete"
    print_record = "print"
    bulk_access = "bulk_access"


class DataCategory(StrEnum):
    patron_pii = "patron_pii"
    minor_data = "minor_data"
    checkout_history = "checkout_history"
    financial_records = "financial_records"
    reading_history = "reading_history"
    computer_usage = "computer_usage"
    law_enforcement = "law_enforcement"
    staff_records = "staff_records"
    incident_data = "incident_data"
    system_config = "system_config"


class ReportType(StrEnum):
    cipa_erate = "cipa_erate"
    coppa_annual = "coppa_annual"
    ferpa_audit = "ferpa_audit"
    data_retention = "data_retention"
    law_enforcement_transparency = "law_enforcement_transparency"
    public_records_summary = "public_records_summary"
    board_executive = "board_executive"
    staff_access_review = "staff_access_review"
    incident_summary = "incident_summary"
    violation_summary = "violation_summary"
    state_compliance = "state_compliance"
    full_audit = "full_audit"


class ReportStatus(StrEnum):
    generating = "generating"
    generated = "generated"
    reviewed = "reviewed"
    approved = "approved"
    submitted = "submitted"
    archived = "archived"


# ============================================================================
# Compliance Requirement Registry
# ============================================================================

class UnifiedComplianceRequirement(Base):
    __tablename__ = "unified_compliance_requirements"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Regulation source
    regulation_type = Column(
        SQLEnum(RegulationType, name="regulationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    regulation_citation = Column(String(300), nullable=True)
    regulation_url = Column(String(500), nullable=True)

    # Requirement details
    requirement_code = Column(String(100), nullable=False)
    requirement_title = Column(String(500), nullable=False)
    requirement_description = Column(Text, nullable=False)
    applies_to_minors = Column(Boolean, default=False)

    # Implementation
    status = Column(
        SQLEnum(RequirementStatus, name="requirementstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=RequirementStatus.not_implemented,
        nullable=False,
    )
    implementation_description = Column(Text, nullable=True)
    implementation_date = Column(Date, nullable=True)
    implementation_owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    technical_controls = Column(JSONB, default=dict)
    administrative_controls = Column(JSONB, default=dict)

    # Verification
    verification_method = Column(
        SQLEnum(VerificationMethod, name="verificationmethod", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    last_verified_date = Column(Date, nullable=True)
    last_verified_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    next_verification_due = Column(Date, nullable=True)
    verification_frequency_days = Column(Integer, default=90)
    verification_evidence = Column(JSONB, default=dict)

    # Risk
    risk_if_non_compliant = Column(Text, nullable=True)
    penalty_description = Column(Text, nullable=True)
    risk_score = Column(Float, default=0.0)

    # State-specific
    state_code = Column(String(2), nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    # Relationships
    implementation_owner = relationship(
        "User", foreign_keys=[implementation_owner_id]
    )
    last_verified_by = relationship(
        "User", foreign_keys=[last_verified_by_id]
    )
    violations = relationship(
        "ComplianceViolation", back_populates="requirement",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_comp_req_org_reg", "organization_id", "regulation_type"),
        Index("ix_comp_req_status", "status"),
        Index("ix_comp_req_next_verify", "next_verification_due"),
        UniqueConstraint(
            "organization_id", "regulation_type", "requirement_code",
            name="uq_compliance_requirement"
        ),
    )


# ============================================================================
# Immutable Tamper-Evident Audit Log
# ============================================================================

class ImmutableAuditEntry(Base):
    __tablename__ = "immutable_audit_entries"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Hash chain for tamper evidence
    entry_hash = Column(String(64), nullable=False, index=True)
    previous_hash = Column(String(64), nullable=False)
    sequence_number = Column(Integer, nullable=False)

    # Who performed the action
    actor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    actor_role = Column(String(50), nullable=True)
    actor_email = Column(String(255), nullable=True)

    # What action was performed
    action = Column(String(100), nullable=False, index=True)
    action_category = Column(String(50), nullable=False, index=True)

    # What resource was affected
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(100), nullable=True)
    resource_description = Column(String(500), nullable=True)

    # Why (justification / business reason)
    justification = Column(Text, nullable=True)
    regulation_context = Column(String(100), nullable=True)

    # Change details
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(255), nullable=True)

    # Classification
    data_category = Column(
        SQLEnum(DataCategory, name="datacategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    involves_minor = Column(Boolean, default=False)
    involves_pii = Column(Boolean, default=False)

    # Immutable timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    actor = relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        Index("ix_immutable_audit_org_time", "organization_id", "created_at"),
        Index("ix_immutable_audit_actor", "actor_id", "created_at"),
        Index("ix_immutable_audit_resource", "resource_type", "resource_id"),
        Index("ix_immutable_audit_action_cat", "action_category", "created_at"),
        Index("ix_immutable_audit_sequence", "organization_id", "sequence_number"),
        Index("ix_immutable_audit_data_cat", "data_category", "created_at"),
    )

    @staticmethod
    def compute_hash(
        previous_hash: str,
        timestamp: str,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        ip_address: str,
    ) -> str:
        payload = (
            f"{previous_hash}|{timestamp}|{actor_id}|{action}"
            f"|{resource_type}|{resource_id}|{ip_address}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ============================================================================
# Compliance Violation Tracking
# ============================================================================

class ComplianceViolation(Base):
    __tablename__ = "compliance_violations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Link to requirement
    requirement_id = Column(
        Integer,
        ForeignKey("unified_compliance_requirements.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Violation details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(
        SQLEnum(ViolationSeverity, name="violationseverity", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status = Column(
        SQLEnum(ViolationStatus, name="violationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ViolationStatus.detected,
        nullable=False,
    )

    # Detection
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    detected_by = Column(String(100), nullable=False)
    detection_method = Column(String(100), nullable=True)
    scan_id = Column(String(100), nullable=True)

    # Affected scope
    affected_records_count = Column(Integer, default=0)
    affected_users_count = Column(Integer, default=0)
    involves_minors = Column(Boolean, default=False)
    affected_data_categories = Column(ARRAY(String), default=[])

    # Remediation
    assigned_to_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    remediation_plan = Column(Text, nullable=True)
    remediation_deadline = Column(Date, nullable=True)
    remediated_at = Column(DateTime(timezone=True), nullable=True)
    remediation_notes = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)

    # Risk assessment
    risk_score = Column(Float, default=0.0)
    regulatory_notification_required = Column(Boolean, default=False)
    regulatory_notification_sent = Column(Boolean, default=False)
    regulatory_notification_date = Column(Date, nullable=True)

    # Evidence
    evidence = Column(JSONB, default=dict)

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    requirement = relationship(
        "UnifiedComplianceRequirement", back_populates="violations"
    )
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])

    __table_args__ = (
        Index("ix_violation_org_sev", "organization_id", "severity"),
        Index("ix_violation_status", "status"),
        Index("ix_violation_deadline", "remediation_deadline"),
        Index("ix_violation_detected", "detected_at"),
    )


# ============================================================================
# Retention Policy Rules
# ============================================================================

class RetentionPolicyRule(Base):
    __tablename__ = "retention_policy_rules"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Rule identification
    rule_name = Column(String(300), nullable=False)
    rule_description = Column(Text, nullable=True)

    # What data this rule applies to
    data_category = Column(
        SQLEnum(DataCategory, name="datacategory_retention", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    target_table = Column(String(100), nullable=False)
    target_conditions = Column(JSONB, default=dict)

    # Retention period
    retention_days = Column(Integer, nullable=False)
    retention_basis = Column(String(200), nullable=True)

    # What happens when retention period expires
    expiry_action = Column(
        SQLEnum(RetentionAction, name="retentionaction", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Regulatory basis
    regulation_type = Column(
        SQLEnum(RegulationType, name="regulationtype_retention", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    regulation_citation = Column(String(300), nullable=True)

    # State-specific override
    state_code = Column(String(2), nullable=True)

    # Execution tracking
    is_active = Column(Boolean, default=True)
    last_executed_at = Column(DateTime(timezone=True), nullable=True)
    last_execution_count = Column(Integer, default=0)
    next_execution_at = Column(DateTime(timezone=True), nullable=True)
    execution_frequency_hours = Column(Integer, default=24)

    # Approval
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_retention_org_cat", "organization_id", "data_category"),
        Index("ix_retention_active", "is_active"),
        Index("ix_retention_next_exec", "next_execution_at"),
        UniqueConstraint(
            "organization_id", "rule_name", "state_code",
            name="uq_retention_rule"
        ),
    )


# ============================================================================
# Compliance Incident Reporting
# ============================================================================

class ComplianceIncident(Base):
    __tablename__ = "compliance_incidents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Incident identification
    incident_number = Column(String(50), unique=True, nullable=False, index=True)

    # Classification
    category = Column(
        SQLEnum(IncidentCategory, name="incidentcategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    severity = Column(
        SQLEnum(ComplianceIncidentSeverity, name="incidentseverity_comp", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status = Column(
        SQLEnum(IncidentStatus, name="incidentstatus_comp", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=IncidentStatus.reported,
        nullable=False,
    )

    # Description
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    discovery_method = Column(String(200), nullable=True)
    discovery_date = Column(DateTime(timezone=True), nullable=False)

    # Affected scope
    affected_systems = Column(ARRAY(String), default=[])
    affected_data_types = Column(ARRAY(String), default=[])
    affected_records_count = Column(Integer, default=0)
    affected_individuals_count = Column(Integer, default=0)
    involves_minors = Column(Boolean, default=False)

    # Regulations implicated
    regulations_implicated = Column(ARRAY(String), default=[])

    # People
    reported_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    incident_commander_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timeline
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    triaged_at = Column(DateTime(timezone=True), nullable=True)
    contained_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Containment
    containment_actions = Column(JSONB, default=list)
    is_contained = Column(Boolean, default=False)

    # Root cause analysis
    root_cause = Column(Text, nullable=True)
    contributing_factors = Column(JSONB, default=list)

    # Remediation
    remediation_actions = Column(JSONB, default=list)
    preventive_measures = Column(JSONB, default=list)

    # Regulatory notification
    notification_required = Column(Boolean, default=False)
    notification_deadline = Column(DateTime(timezone=True), nullable=True)
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    notification_recipients = Column(JSONB, default=list)

    # Lessons learned
    lessons_learned = Column(Text, nullable=True)
    policy_changes_needed = Column(JSONB, default=list)

    # Documentation
    evidence_files = Column(JSONB, default=list)

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    incident_commander = relationship("User", foreign_keys=[incident_commander_id])

    __table_args__ = (
        Index("ix_incident_org_status", "organization_id", "status"),
        Index("ix_incident_severity", "severity"),
        Index("ix_incident_category", "category"),
        Index("ix_incident_reported", "reported_at"),
        Index("ix_incident_notification", "notification_required", "notification_sent"),
    )


# ============================================================================
# Staff Access Log
# ============================================================================

class StaffAccessLog(Base):
    __tablename__ = "staff_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Who accessed
    staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    staff_role = Column(String(50), nullable=True)

    # What type of access
    access_type = Column(
        SQLEnum(AccessType, name="accesstype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # What data was accessed
    data_category = Column(
        SQLEnum(DataCategory, name="datacategory_access", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    resource_description = Column(String(500), nullable=True)

    # Whose data was accessed (patron)
    target_patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    target_is_minor = Column(Boolean, default=False)

    # Context
    justification = Column(Text, nullable=True)
    endpoint = Column(String(500), nullable=True)
    query_parameters = Column(JSONB, nullable=True)
    records_accessed_count = Column(Integer, default=1)

    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(255), nullable=True)

    # Anomaly flags
    is_after_hours = Column(Boolean, default=False)
    is_bulk_access = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String(500), nullable=True)

    # Timestamp
    accessed_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id])
    target_patron = relationship("User", foreign_keys=[target_patron_id])

    __table_args__ = (
        Index("ix_staff_access_staff_time", "staff_id", "accessed_at"),
        Index("ix_staff_access_org_time", "organization_id", "accessed_at"),
        Index("ix_staff_access_patron", "target_patron_id", "accessed_at"),
        Index("ix_staff_access_category", "data_category", "accessed_at"),
        Index("ix_staff_access_flagged", "is_flagged", "accessed_at"),
        Index("ix_staff_access_type", "access_type", "accessed_at"),
    )


# ============================================================================
# Compliance Report
# ============================================================================

class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Report identification
    report_type = Column(
        SQLEnum(ReportType, name="comp_reporttype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    title = Column(String(500), nullable=False)

    # Period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Status
    status = Column(
        SQLEnum(ReportStatus, name="comp_reportstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ReportStatus.generating,
        nullable=False,
    )

    # Report content (structured data)
    report_data = Column(JSONB, default=dict)
    summary = Column(Text, nullable=True)
    recommendations = Column(JSONB, default=list)

    # Metrics
    total_requirements = Column(Integer, default=0)
    compliant_count = Column(Integer, default=0)
    non_compliant_count = Column(Integer, default=0)
    violations_count = Column(Integer, default=0)
    incidents_count = Column(Integer, default=0)
    compliance_score = Column(Float, default=0.0)

    # Generation
    generated_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Review / Approval
    reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Submission (to regulator)
    submitted_to = Column(String(300), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submission_reference = Column(String(200), nullable=True)

    # File
    report_file_path = Column(String(500), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_report_org_type", "organization_id", "report_type"),
        Index("ix_report_period", "period_start", "period_end"),
        Index("ix_report_status", "status"),
    )
