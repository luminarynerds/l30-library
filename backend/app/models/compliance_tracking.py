# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from datetime import datetime, date
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# Enums - Compliance Statuses
# ============================================================================

class TrackingComplianceStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    compliant = "compliant"
    non_compliant = "non_compliant"
    needs_review = "needs_review"
    expired = "expired"


class ADAStatus(StrEnum):
    compliant = "compliant"
    partial = "partial"
    non_compliant = "non_compliant"
    under_remediation = "under_remediation"
    exemption_granted = "exemption_granted"


class CIPAStatus(StrEnum):
    compliant = "compliant"
    monitoring_required = "monitoring_required"
    non_compliant = "non_compliant"
    pending_implementation = "pending_implementation"


class COPPAStatus(StrEnum):
    compliant = "compliant"
    minor_collection_prohibited = "minor_collection_prohibited"
    parental_consent_required = "parental_consent_required"
    needs_audit = "needs_audit"


class PCIStatus(StrEnum):
    not_applicable = "not_applicable"
    compliant = "compliant"
    non_compliant = "non_compliant"
    in_remediation = "in_remediation"
    assessment_pending = "assessment_pending"


class StateComplianceStatus(StrEnum):
    compliant = "compliant"
    non_compliant = "non_compliant"
    partial_compliance = "partial_compliance"
    under_review = "under_review"
    waiver_obtained = "waiver_obtained"


class InsuranceType(StrEnum):
    general_liability = "general_liability"
    property_insurance = "property_insurance"
    cyber_liability = "cyber_liability"
    directors_officers = "directors_officers"
    employee_injury = "employee_injury"
    volunteer_liability = "volunteer_liability"
    coverage_gap = "coverage_gap"


class SafetyInspectionType(StrEnum):
    fire_safety = "fire_safety"
    building_code = "building_code"
    emergency_preparedness = "emergency_preparedness"
    equipment_safety = "equipment_safety"
    electrical = "electrical"
    plumbing = "plumbing"
    accessibility = "accessibility"
    hazmat = "hazmat"


class CertificationType(StrEnum):
    cpr_first_aid = "cpr_first_aid"
    food_handler = "food_handler"
    mental_health_training = "mental_health_training"
    background_check = "background_check"
    mandatory_reporter = "mandatory_reporter"
    accessibility_training = "accessibility_training"
    data_protection = "data_protection"
    library_mls = "library_mls"
    specialized_skill = "specialized_skill"


class PolicyReviewStatus(StrEnum):
    current = "current"
    pending_review = "pending_review"
    under_revision = "under_revision"
    approved = "approved"
    archived = "archived"


class AuditItemStatus(StrEnum):
    not_applicable = "not_applicable"
    ready = "ready"
    needs_work = "needs_work"
    critical = "critical"
    completed = "completed"


# ============================================================================
# ADA Accessibility Compliance
# ============================================================================

class ADACompliance(Base):
    __tablename__ = "ada_compliance"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Overall status
    status = Column(
        SQLEnum(ADAStatus, name="adastatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ADAStatus.partial,
        nullable=False
    )

    # Assessment details
    last_assessment_date = Column(Date, nullable=True)
    next_assessment_due = Column(Date, nullable=True)
    assessment_provider = Column(String(200), nullable=True)

    # Accessibility features
    physical_accessibility = Column(Boolean, default=False)  # Wheelchair ramps, elevators, etc.
    adaptive_technology = Column(Boolean, default=False)  # Screen readers, etc.
    accessible_bathrooms = Column(Boolean, default=False)
    accessible_parking = Column(Boolean, default=False)
    service_animal_policy = Column(Boolean, default=False)
    braille_materials = Column(Boolean, default=False)
    large_print_available = Column(Boolean, default=False)
    audio_formats_available = Column(Boolean, default=False)
    accessible_website = Column(Boolean, default=False)  # WCAG 2.1 AA
    accessible_catalog = Column(Boolean, default=False)

    # Remediation
    identified_gaps = Column(JSONB, default=dict)  # { gap: remediation_plan, ... }
    remediation_in_progress = Column(Boolean, default=False)
    remediation_budget = Column(Float, nullable=True)

    # Documentation
    ada_coordinator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ada_policy_document = Column(String(500), nullable=True)  # File path/URL
    accessibility_statement = Column(Text, nullable=True)

    # Audit trail
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_ada_compliance_org", "organization_id"),
        Index("ix_ada_compliance_status", "status"),
        Index("ix_ada_compliance_due_date", "next_assessment_due"),
    )


# ============================================================================
# CIPA Compliance (Internet Filtering & Children's Policy)
# ============================================================================

class CIPACompliance(Base):
    __tablename__ = "cipa_compliance_tracking"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Overall status
    status = Column(
        SQLEnum(CIPAStatus, name="cipastatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CIPAStatus.compliant,
        nullable=False
    )

    # Safety measures
    blocking_filter_active = Column(Boolean, default=True)
    monitoring_software_active = Column(Boolean, default=True)
    content_blocks = Column(ARRAY(String), default=[])  # "adult", "violence", etc.

    # Policy documentation
    internet_use_policy = Column(String(500), nullable=True)  # File path
    written_policy_effective_date = Column(Date, nullable=True)
    policy_approved_by = Column(String(200), nullable=True)  # Board approval

    # Monitoring
    monitor_activity = Column(Boolean, default=True)
    monitor_behavior = Column(Boolean, default=True)
    monitor_email = Column(Boolean, default=False)

    # Education and notice
    staff_trained_on_policy = Column(Boolean, default=False)
    staff_training_date = Column(Date, nullable=True)
    minor_notification_provided = Column(Boolean, default=False)
    parent_notification_provided = Column(Boolean, default=False)

    # Exemptions and overrides
    educational_exemptions_allowed = Column(Boolean, default=True)
    authorized_staff_can_bypass = Column(Boolean, default=True)

    # Last compliance check
    last_check_date = Column(Date, nullable=True)
    next_check_due = Column(Date, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_cipa_org", "organization_id"),
        Index("ix_cipa_status", "status"),
    )


# ============================================================================
# COPPA Compliance (Children's Online Privacy Protection)
# ============================================================================

class COPPACompliance(Base):
    __tablename__ = "coppa_compliance"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Overall status
    status = Column(
        SQLEnum(COPPAStatus, name="coppastatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=COPPAStatus.compliant,
        nullable=False
    )

    # Policy and notification
    coppa_compliant_policy = Column(String(500), nullable=True)  # File path
    privacy_policy_for_minors = Column(String(500), nullable=True)  # File path
    parental_consent_process = Column(Text, nullable=True)  # Description

    # Data collection restrictions
    collect_personal_data_from_minors = Column(Boolean, default=False)
    requires_parental_consent = Column(Boolean, default=False)
    minor_data_is_encrypted = Column(Boolean, default=True)
    minor_data_retention_months = Column(Integer, default=12)  # How long retained

    # Parental access rights
    parents_can_review_data = Column(Boolean, default=True)
    parents_can_delete_data = Column(Boolean, default=True)
    parents_can_opt_out = Column(Boolean, default=True)

    # Staff training
    staff_trained_on_coppa = Column(Boolean, default=False)
    staff_training_date = Column(Date, nullable=True)
    next_training_due = Column(Date, nullable=True)

    # Data security
    data_security_audit_date = Column(Date, nullable=True)
    next_security_audit_due = Column(Date, nullable=True)
    incident_response_plan = Column(String(500), nullable=True)  # File path

    # FTC compliance
    ftc_notification_required = Column(Boolean, default=False)
    ftc_notification_sent_date = Column(Date, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_coppa_org", "organization_id"),
        Index("ix_coppa_status", "status"),
    )


# ============================================================================
# PCI Compliance (Payment Card Industry)
# ============================================================================

class PCICompliance(Base):
    __tablename__ = "pci_compliance"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Overall status
    status = Column(
        SQLEnum(PCIStatus, name="pcistatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PCIStatus.not_applicable,
        nullable=False
    )

    # Payment processing
    accepts_credit_cards = Column(Boolean, default=False)
    uses_payment_processor = Column(String(200), nullable=True)  # Stripe, Square, etc.
    payment_processor_pci_certified = Column(Boolean, default=False)

    # Card data handling
    stores_card_data = Column(Boolean, default=False)
    card_data_encrypted = Column(Boolean, default=True)
    card_data_tokenized = Column(Boolean, default=False)
    never_stores_cvv = Column(Boolean, default=True)

    # Network security
    firewall_in_place = Column(Boolean, default=False)
    antivirus_updated = Column(Boolean, default=False)
    strong_passwords_enforced = Column(Boolean, default=False)
    network_regularly_tested = Column(Boolean, default=False)

    # Compliance assessment
    assessment_type = Column(String(50), nullable=True)  # SAQ, Validation Report, etc.
    assessment_date = Column(Date, nullable=True)
    next_assessment_due = Column(Date, nullable=True)
    assessor_name = Column(String(200), nullable=True)

    # Certification
    pci_dss_level = Column(Integer, nullable=True)  # 1-4
    current_certification_expires = Column(Date, nullable=True)
    certificate_file = Column(String(500), nullable=True)  # File path

    # Incident response
    data_breach_incident_plan = Column(String(500), nullable=True)  # File path
    breach_notification_procedures = Column(Text, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_pci_org", "organization_id"),
        Index("ix_pci_status", "status"),
        Index("ix_pci_assessment_due", "next_assessment_due"),
    )


# ============================================================================
# State Library Requirements
# ============================================================================

class StateLibraryRequirement(Base):
    __tablename__ = "state_library_requirements"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    state_code = Column(String(2), nullable=False)  # e.g., "CA", "NY"

    # Requirement details
    requirement_name = Column(String(300), nullable=False)
    requirement_description = Column(Text, nullable=True)
    regulation_citation = Column(String(200), nullable=True)  # e.g., "California Education Code §18800"

    # Compliance status
    status = Column(
        SQLEnum(StateComplianceStatus, name="statecompliancestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=StateComplianceStatus.under_review,
        nullable=False
    )

    # Deadline tracking
    compliance_deadline = Column(Date, nullable=True)
    last_verified_date = Column(Date, nullable=True)
    next_verification_due = Column(Date, nullable=True)

    # Reporting
    annual_report_required = Column(Boolean, default=False)
    annual_report_due_date = Column(Date, nullable=True)
    annual_report_submitted = Column(Boolean, default=False)
    annual_report_file = Column(String(500), nullable=True)  # File path

    # Documentation
    supporting_documents = Column(JSONB, default=dict)  # { doc_type: file_path, ... }
    responsible_person_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_state_req_org", "organization_id"),
        Index("ix_state_req_state", "state_code"),
        Index("ix_state_req_status", "status"),
        Index("ix_state_req_deadline", "compliance_deadline"),
        UniqueConstraint("organization_id", "state_code", "requirement_name", name="uq_state_requirement"),
    )


# ============================================================================
# Insurance and Liability Tracking
# ============================================================================

class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Policy details
    policy_type = Column(
        SQLEnum(InsuranceType, name="insurancetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    policy_name = Column(String(200), nullable=False)
    policy_number = Column(String(100), nullable=False, unique=True)

    # Coverage details
    provider_name = Column(String(200), nullable=False)
    coverage_amount = Column(Float, nullable=False)  # In dollars
    deductible = Column(Float, nullable=False)

    # Dates
    effective_date = Column(Date, nullable=False)
    expiration_date = Column(Date, nullable=False)
    renewal_reminder_days_before = Column(Integer, default=60)  # Remind X days before expiration

    # Renewal tracking
    auto_renews = Column(Boolean, default=True)
    renewal_pending = Column(Boolean, default=False)
    renewal_quote_received = Column(Boolean, default=False)
    new_renewal_date = Column(Date, nullable=True)  # If renewed early

    # Claims history
    claims_filed = Column(Integer, default=0)
    recent_claim_date = Column(Date, nullable=True)
    claims_notes = Column(Text, nullable=True)

    # Documentation
    policy_document = Column(String(500), nullable=True)  # File path
    certificate_of_insurance = Column(String(500), nullable=True)  # File path

    # Endorsements and modifications
    endorsements = Column(JSONB, default=dict)  # { endorsement_date: description, ... }
    modifications = Column(Text, nullable=True)

    # Contact
    broker_name = Column(String(200), nullable=True)
    broker_contact = Column(String(200), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "expiration_date > effective_date",
            name="ck_insurance_policy_expiration_after_effective",
        ),
        CheckConstraint(
            "coverage_amount >= 0",
            name="ck_insurance_policy_coverage_non_negative",
        ),
        CheckConstraint(
            "deductible >= 0",
            name="ck_insurance_policy_deductible_non_negative",
        ),
        CheckConstraint(
            "claims_filed >= 0",
            name="ck_insurance_policy_claims_filed_non_negative",
        ),
        Index("ix_insurance_org", "organization_id"),
        Index("ix_insurance_type", "policy_type"),
        Index("ix_insurance_expiration", "expiration_date"),
    )


class LiabilityIncident(Base):
    __tablename__ = "liability_incidents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Incident details
    incident_date = Column(Date, nullable=False)
    incident_type = Column(String(200), nullable=False)  # Slip/fall, injury, property damage, etc.
    incident_description = Column(Text, nullable=False)
    location = Column(String(200), nullable=False)

    # Parties involved
    involved_person_name = Column(String(200), nullable=True)
    involved_person_email = Column(String(200), nullable=True)
    involved_person_phone = Column(String(20), nullable=True)
    witness_names = Column(ARRAY(String), default=[])

    # Reporting
    incident_reported_date = Column(Date, nullable=False)
    reported_to = Column(String(200), nullable=True)  # Police, etc.
    report_number = Column(String(100), nullable=True)

    # Insurance claim
    claim_filed = Column(Boolean, default=False)
    claim_number = Column(String(100), nullable=True)
    claim_filed_date = Column(Date, nullable=True)
    claim_status = Column(String(50), nullable=True)  # pending, approved, denied, settled

    # Documentation
    incident_photos = Column(JSONB, default=dict)  # { photo_type: file_path, ... }
    incident_report_file = Column(String(500), nullable=True)  # File path

    # Resolution
    resolved = Column(Boolean, default=False)
    resolution_date = Column(Date, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Follow-up
    follow_up_actions = Column(ARRAY(String), default=[])
    follow_up_complete = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_incident_org", "organization_id"),
        Index("ix_incident_date", "incident_date"),
        Index("ix_incident_claim", "claim_filed"),
    )


# ============================================================================
# Safety Inspection Management
# ============================================================================

class SafetyInspection(Base):
    __tablename__ = "safety_inspections"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Inspection details
    inspection_type = Column(
        SQLEnum(SafetyInspectionType, name="safetyinspectiontype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    location = Column(String(200), nullable=False)

    # Scheduling
    last_inspection_date = Column(Date, nullable=True)
    next_inspection_due = Column(Date, nullable=False)
    frequency_months = Column(Integer, nullable=False)  # How often required
    regulatory_requirement = Column(Boolean, default=True)  # Is it legally required?

    # Inspector information
    inspector_name = Column(String(200), nullable=True)
    inspector_company = Column(String(200), nullable=True)
    inspector_license = Column(String(100), nullable=True)
    inspector_contact = Column(String(200), nullable=True)

    # Results
    findings = Column(JSONB, default=dict)  # { finding_id: { severity, description, resolution }, ... }
    passed = Column(Boolean, default=True)
    critical_issues = Column(Integer, default=0)
    non_critical_issues = Column(Integer, default=0)

    # Remediation
    remediation_required = Column(Boolean, default=False)
    remediation_deadline = Column(Date, nullable=True)
    remediation_completed = Column(Boolean, default=False)
    remediation_completion_date = Column(Date, nullable=True)
    remediation_verified = Column(Boolean, default=False)

    # Documentation
    inspection_report = Column(String(500), nullable=True)  # File path
    photos = Column(JSONB, default=dict)  # { issue: file_path, ... }

    # Notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_inspection_org", "organization_id"),
        Index("ix_inspection_type", "inspection_type"),
        Index("ix_inspection_due_date", "next_inspection_due"),
        Index("ix_inspection_passed", "passed"),
    )


# ============================================================================
# Staff Certification and Credential Tracking
# ============================================================================

class StaffCertification(Base):
    __tablename__ = "staff_certifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Certification details
    certification_type = Column(
        SQLEnum(CertificationType, name="certificationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    certification_name = Column(String(200), nullable=False)
    issuing_organization = Column(String(200), nullable=False)

    # Dates
    obtained_date = Column(Date, nullable=False)
    expiration_date = Column(Date, nullable=True)  # NULL means doesn't expire
    is_active = Column(Boolean, default=True)

    # Renewal tracking
    renewal_required = Column(Boolean, default=False)
    renewal_frequency_months = Column(Integer, nullable=True)
    next_renewal_due = Column(Date, nullable=True)
    renewal_in_progress = Column(Boolean, default=False)

    # Documentation
    credential_number = Column(String(100), nullable=True)
    certificate_file = Column(String(500), nullable=True)  # File path
    verification_date = Column(Date, nullable=True)  # When was it verified?

    # Verification
    verified = Column(Boolean, default=False)
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_date = Column(Date, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="certifications")
    verified_by = relationship("User", foreign_keys=[verified_by_id])

    __table_args__ = (
        Index("ix_cert_user", "user_id"),
        Index("ix_cert_org", "organization_id"),
        Index("ix_cert_type", "certification_type"),
        Index("ix_cert_expiration", "expiration_date"),
        Index("ix_cert_renewal_due", "next_renewal_due"),
        UniqueConstraint("user_id", "certification_type", "issuing_organization",
                        name="uq_staff_certification"),
    )


# ============================================================================
# Policy Review Schedule
# ============================================================================

class PolicyReview(Base):
    __tablename__ = "policy_reviews"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Policy details
    policy_name = Column(String(300), nullable=False)
    policy_description = Column(Text, nullable=True)
    policy_category = Column(String(100), nullable=False)  # e.g., "Data Privacy", "Safety", etc.

    # Version tracking
    current_version = Column(String(20), default="1.0")
    last_updated_date = Column(Date, nullable=True)

    # Review schedule
    status = Column(
        SQLEnum(PolicyReviewStatus, name="policyreviewstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PolicyReviewStatus.current,
        nullable=False
    )
    review_frequency_months = Column(Integer, nullable=False)  # How often to review
    last_review_date = Column(Date, nullable=True)
    next_review_due = Column(Date, nullable=False)

    # Approval
    requires_board_approval = Column(Boolean, default=False)
    board_approval_date = Column(Date, nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Changes needed
    revision_notes = Column(Text, nullable=True)
    under_revision = Column(Boolean, default=False)
    revision_deadline = Column(Date, nullable=True)

    # Documentation
    policy_document = Column(String(500), nullable=True)  # File path
    previous_versions = Column(JSONB, default=dict)  # { version: { file_path, date }, ... }

    # Stakeholders
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewer_ids = Column(ARRAY(Integer), default=[])  # IDs of people to review

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    owner = relationship("User", foreign_keys=[owner_id])

    __table_args__ = (
        Index("ix_policy_org", "organization_id"),
        Index("ix_policy_category", "policy_category"),
        Index("ix_policy_review_due", "next_review_due"),
        Index("ix_policy_status", "status"),
    )


# ============================================================================
# Audit Readiness Checklist
# ============================================================================

class AuditReadinessChecklist(Base):
    __tablename__ = "audit_readiness_checklists"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    audit_type = Column(String(200), nullable=False)  # "Financial", "Operational", "Compliance", etc.

    # Checklist meta
    created_for_audit_date = Column(Date, nullable=True)  # When is the audit scheduled?
    checklist_created_date = Column(Date, nullable=False)
    checklist_last_updated_date = Column(Date, nullable=False)

    # Items
    items = Column(JSONB, default=dict)  # { item_id: { name, status, owner_id, due_date, notes }, ... }

    # Status tracking
    items_complete = Column(Integer, default=0)
    items_in_progress = Column(Integer, default=0)
    items_not_ready = Column(Integer, default=0)
    items_total = Column(Integer, default=0)

    completion_percentage = Column(Float, default=0.0)
    overall_ready = Column(Boolean, default=False)

    # Preparedness
    documentation_complete = Column(Boolean, default=False)
    staff_informed = Column(Boolean, default=False)
    resources_allocated = Column(Boolean, default=False)

    # Auditor info
    auditor_name = Column(String(200), nullable=True)
    auditor_company = Column(String(200), nullable=True)
    audit_start_date = Column(Date, nullable=True)
    audit_end_date = Column(Date, nullable=True)

    # Results
    audit_completed = Column(Boolean, default=False)
    audit_findings = Column(Text, nullable=True)
    audit_report_file = Column(String(500), nullable=True)  # File path

    # Follow-up
    follow_up_items = Column(JSONB, default=dict)  # { item_id: { description, owner_id, due_date }, ... }
    follow_up_complete = Column(Boolean, default=False)

    # Notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_org", "organization_id"),
        Index("ix_audit_type", "audit_type"),
        Index("ix_audit_ready", "overall_ready"),
    )


# ============================================================================
# Compliance Deadline Alert System
# ============================================================================

class ComplianceDeadlineAlert(Base):
    __tablename__ = "compliance_deadline_alerts"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Alert source
    alert_type = Column(String(100), nullable=False)  # insurance_expiration, cert_renewal, inspection_due, etc.
    source_model = Column(String(100), nullable=False)  # "InsurancePolicy", "SafetyInspection", etc.
    source_id = Column(Integer, nullable=False)  # ID of the related record

    # Deadline info
    deadline_date = Column(Date, nullable=False)
    days_until_deadline = Column(Integer, nullable=False)

    # Notification status
    alert_triggered = Column(Boolean, default=True)
    first_alert_sent = Column(Date, nullable=True)
    reminder_alerts_sent = Column(Integer, default=0)  # How many reminders
    last_alert_sent = Column(Date, nullable=True)
    final_alert_sent = Column(Boolean, default=False)

    # Notification recipients
    recipient_ids = Column(ARRAY(Integer), default=[])
    recipient_emails = Column(ARRAY(String), default=[])

    # Escalation
    escalated = Column(Boolean, default=False)
    escalated_to = Column(String(200), nullable=True)  # Director, Board, etc.
    escalation_date = Column(Date, nullable=True)

    # Resolution
    item_completed = Column(Boolean, default=False)
    completion_date = Column(Date, nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_alert_org", "organization_id"),
        Index("ix_alert_type", "alert_type"),
        Index("ix_alert_deadline", "deadline_date"),
        Index("ix_alert_triggered", "alert_triggered"),
    )
