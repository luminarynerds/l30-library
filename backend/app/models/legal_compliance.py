# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint
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

class LegalDocumentType(StrEnum):
    policy = "policy"
    procedure = "procedure"
    regulation = "regulation"
    statute = "statute"
    ordinance = "ordinance"
    guideline = "guideline"
    agreement = "agreement"
    contract = "contract"
    memo = "memo"
    resolution = "resolution"
    bylaw = "bylaw"
    handbook = "handbook"
    code_of_conduct = "code_of_conduct"


class DocumentCategory(StrEnum):
    governance = "governance"
    hr_employment = "hr_employment"
    patron_services = "patron_services"
    privacy_data = "privacy_data"
    intellectual_property = "intellectual_property"
    facilities = "facilities"
    finance = "finance"
    safety_security = "safety_security"
    technology = "technology"
    collections = "collections"
    accessibility = "accessibility"
    youth_services = "youth_services"
    procurement = "procurement"
    volunteer_management = "volunteer_management"


class LegalDocumentStatus(StrEnum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    active = "active"
    archived = "archived"
    superseded = "superseded"
    obsolete = "obsolete"


class ComplianceStatus(StrEnum):
    compliant = "compliant"
    partially_compliant = "partially_compliant"
    non_compliant = "non_compliant"
    not_applicable = "not_applicable"
    under_review = "under_review"
    pending_action = "pending_action"


class RequirementType(StrEnum):
    federal_law = "federal_law"
    state_law = "state_law"
    local_ordinance = "local_ordinance"
    accreditation = "accreditation"
    certification = "certification"
    industry_standard = "industry_standard"
    contractual = "contractual"
    internal_policy = "internal_policy"
    grant_requirement = "grant_requirement"


class ReviewFrequency(StrEnum):
    annual = "annual"
    biannual = "biannual"
    quarterly = "quarterly"
    monthly = "monthly"
    as_needed = "as_needed"
    triennial = "triennial"


class ReviewStatus(StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    approved = "approved"
    rejected = "rejected"
    deferred = "deferred"


class LegalAlertSeverity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"
    warning = "warning"


class AlertStatus(StrEnum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"
    dismissed = "dismissed"
    escalated = "escalated"


class LegalChangeType(StrEnum):
    new_regulation = "new_regulation"
    amendment = "amendment"
    repeal = "repeal"
    interpretation = "interpretation"
    deadline_change = "deadline_change"
    enforcement_update = "enforcement_update"


class EnforcementAction(StrEnum):
    warning = "warning"
    training_required = "training_required"
    policy_review = "policy_review"
    corrective_action = "corrective_action"
    suspension = "suspension"
    termination = "termination"
    escalation = "escalation"


class AuditEventType(StrEnum):
    created = "created"
    updated = "updated"
    deleted = "deleted"
    approved = "approved"
    rejected = "rejected"
    published = "published"
    archived = "archived"
    reviewed = "reviewed"
    version_created = "version_created"
    status_changed = "status_changed"


# ============================================================================
# Phase 1: Core Legal Document Management
# ============================================================================

class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, index=True)

    # Document identification
    title = Column(String(500), nullable=False, index=True)
    document_number = Column(String(100), unique=True, index=True)
    document_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    category = Column(
        SQLEnum(DocumentCategory, name="documentcategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Content
    description = Column(Text)
    purpose = Column(Text)
    scope = Column(Text)

    # Status
    status = Column(
        SQLEnum(LegalDocumentStatus, name="legaldocumentstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=LegalDocumentStatus.draft,
        nullable=False,
        index=True
    )

    # Versioning
    current_version_id = Column(
        Integer,
        ForeignKey("document_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True
    )

    # Effective dates
    effective_date = Column(Date, index=True)
    expiration_date = Column(Date, index=True)
    last_reviewed_date = Column(Date)
    next_review_date = Column(Date, index=True)

    # Authority and ownership
    authority_source = Column(String(200))  # Law, regulation, board decision
    authority_citation = Column(Text)  # Legal citation
    responsible_department = Column(String(200))
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Related documents
    supersedes_document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="SET NULL"),
        nullable=True
    )
    parent_document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="SET NULL"),
        nullable=True
    )

    # Tags and keywords
    tags = Column(ARRAY(String), default=[])
    keywords = Column(ARRAY(String), default=[])

    # Approval workflow
    approval_required = Column(Boolean, default=True)
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at = Column(DateTime(timezone=True))

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    current_version = relationship("app.models.legal_compliance.DocumentVersion", foreign_keys=[current_version_id], post_update=True)
    versions = relationship("app.models.legal_compliance.DocumentVersion", back_populates="document", foreign_keys="app.models.legal_compliance.DocumentVersion.document_id")
    supersedes = relationship("LegalDocument", foreign_keys=[supersedes_document_id], remote_side="LegalDocument.id")
    parent_document = relationship("LegalDocument", foreign_keys=[parent_document_id], remote_side="LegalDocument.id")
    compliance_links = relationship("ComplianceDocumentLink", back_populates="document")
    review_cycles = relationship("DocumentReviewCycle", back_populates="document")
    audit_logs = relationship("DocumentAuditLog", back_populates="document")

    __table_args__ = (
        Index("ix_legal_docs_status_category", "status", "category"),
        Index("ix_legal_docs_next_review", "next_review_date"),
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)

    # Document reference
    document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Version info
    version_number = Column(String(50), nullable=False)
    major_version = Column(Integer, nullable=False)
    minor_version = Column(Integer, nullable=False)

    # Content
    content = Column(Text)  # Full document content or reference
    file_url = Column(String(500))
    file_hash = Column(String(128))  # SHA-256 hash for integrity

    # Change tracking
    change_summary = Column(Text, nullable=False)
    changes_from_previous = Column(JSONB, default={})  # Structured change log

    # Status
    is_current = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    document = relationship("LegalDocument", back_populates="versions", foreign_keys=[document_id])
    created_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_doc_version"),
        Index("ix_doc_version_current", "document_id", "is_current"),
    )


# ============================================================================
# Phase 2: Compliance Tracking and Requirements
# ============================================================================

class LegalComplianceRequirement(Base):
    __tablename__ = "legal_compliance_requirements"

    id = Column(Integer, primary_key=True, index=True)

    # Requirement identification
    title = Column(String(500), nullable=False, index=True)
    requirement_code = Column(String(100), unique=True, index=True)
    requirement_type = Column(
        SQLEnum(RequirementType, name="requirementtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Description
    description = Column(Text, nullable=False)
    legal_citation = Column(Text)
    jurisdiction = Column(String(200))  # Federal, State, Local

    # Compliance details
    compliance_status = Column(
        SQLEnum(ComplianceStatus, name="compliancestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ComplianceStatus.under_review,
        nullable=False,
        index=True
    )

    # Dates
    effective_date = Column(Date, nullable=False, index=True)
    deadline_date = Column(Date, index=True)
    last_assessed_date = Column(Date)
    next_assessment_date = Column(Date, index=True)

    # Responsibility
    responsible_department = Column(String(200))
    compliance_officer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Risk assessment
    risk_level = Column(String(50))  # Critical, High, Medium, Low
    penalties_for_noncompliance = Column(Text)

    # Implementation
    implementation_notes = Column(Text)
    evidence_required = Column(JSONB, default=[])  # List of evidence needed

    # Checklist items
    checklist_items = Column(JSONB, default=[])  # Structured checklist

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    compliance_officer = relationship("User", foreign_keys=[compliance_officer_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    document_links = relationship("ComplianceDocumentLink", back_populates="requirement")
    checklist_item_records = relationship("ComplianceChecklistItem", back_populates="requirement")

    __table_args__ = (
        Index("ix_compliance_req_status_deadline", "compliance_status", "deadline_date"),
        Index("ix_compliance_req_next_assessment", "next_assessment_date"),
    )


class ComplianceDocumentLink(Base):
    __tablename__ = "compliance_document_links"

    id = Column(Integer, primary_key=True, index=True)

    # Links
    requirement_id = Column(
        Integer,
        ForeignKey("legal_compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationship details
    relationship_type = Column(String(100))  # implements, references, supports
    notes = Column(Text)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    requirement = relationship("LegalComplianceRequirement", back_populates="document_links")
    document = relationship("LegalDocument", back_populates="compliance_links")
    created_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("requirement_id", "document_id", name="uq_compliance_doc_link"),
    )


class ComplianceChecklistItem(Base):
    __tablename__ = "compliance_checklist_items"

    id = Column(Integer, primary_key=True, index=True)

    # Requirement reference
    requirement_id = Column(
        Integer,
        ForeignKey("legal_compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Item details
    item_text = Column(Text, nullable=False)
    item_order = Column(Integer, default=0)

    # Completion tracking
    is_completed = Column(Boolean, default=False)
    completed_date = Column(Date)
    completed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Evidence
    evidence_description = Column(Text)
    evidence_file_url = Column(String(500))

    # Notes
    notes = Column(Text)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    requirement = relationship("LegalComplianceRequirement", back_populates="checklist_item_records")
    completed_by = relationship("User")

    __table_args__ = (
        Index("ix_compliance_checklist_req_order", "requirement_id", "item_order"),
    )


# ============================================================================
# Phase 3: Audit Logging and Review Cycles
# ============================================================================

class DocumentAuditLog(Base):
    __tablename__ = "document_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Document reference
    document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Event details
    event_type = Column(
        SQLEnum(AuditEventType, name="auditeventtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    event_description = Column(Text, nullable=False)

    # Changes
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    field_changes = Column(JSONB)  # Specific fields changed

    # Actor
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    user_role = Column(String(100))
    ip_address = Column(String(50))

    # Context
    additional_context = Column(JSONB)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    document = relationship("LegalDocument", back_populates="audit_logs")
    user = relationship("User")

    __table_args__ = (
        Index("ix_audit_log_doc_event", "document_id", "event_type"),
        Index("ix_audit_log_created", "created_at"),
    )


class DocumentReviewCycle(Base):
    __tablename__ = "document_review_cycles"

    id = Column(Integer, primary_key=True, index=True)

    # Document reference
    document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Review cycle info
    review_frequency = Column(
        SQLEnum(ReviewFrequency, name="reviewfrequency", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Dates
    scheduled_date = Column(Date, nullable=False, index=True)
    started_date = Column(Date)
    completed_date = Column(Date)
    due_date = Column(Date, index=True)

    # Status
    status = Column(
        SQLEnum(ReviewStatus, name="doc_reviewstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ReviewStatus.pending,
        nullable=False,
        index=True
    )

    # Responsibility
    assigned_to_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    review_committee = Column(ARRAY(Integer))  # User IDs

    # Outcome
    outcome_summary = Column(Text)
    recommendations = Column(JSONB, default=[])
    action_items = Column(JSONB, default=[])

    # Notifications
    reminder_sent = Column(Boolean, default=False)
    last_reminder_date = Column(Date)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    document = relationship("LegalDocument", back_populates="review_cycles")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviews = relationship("DocumentReview", back_populates="review_cycle")

    __table_args__ = (
        Index("ix_review_cycle_status_due", "status", "due_date"),
        Index("ix_review_cycle_scheduled", "scheduled_date"),
    )


class DocumentReview(Base):
    __tablename__ = "document_reviews"

    id = Column(Integer, primary_key=True, index=True)

    # Review cycle reference
    review_cycle_id = Column(
        Integer,
        ForeignKey("document_review_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Reviewer
    reviewer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Review details
    review_date = Column(Date, nullable=False)
    status = Column(
        SQLEnum(ReviewStatus, name="reviewstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Findings
    findings = Column(Text)
    recommendations = Column(Text)
    requires_update = Column(Boolean, default=False)

    # Specific issues
    legal_accuracy_rating = Column(Integer)  # 1-5
    clarity_rating = Column(Integer)  # 1-5
    completeness_rating = Column(Integer)  # 1-5

    # Comments
    comments = Column(JSONB, default=[])  # Structured comments

    # Approval
    approved = Column(Boolean)
    approval_notes = Column(Text)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    review_cycle = relationship("DocumentReviewCycle", back_populates="reviews")
    reviewer = relationship("User")

    __table_args__ = (
        Index("ix_doc_review_cycle_reviewer", "review_cycle_id", "reviewer_id"),
    )


# ============================================================================
# Phase 4: Dashboard Metrics, Alerts, and Regulatory Tracking
# ============================================================================

class ComplianceDashboardMetric(Base):
    __tablename__ = "compliance_dashboard_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Time period
    metric_date = Column(Date, nullable=False, index=True)
    metric_type = Column(String(100), nullable=False, index=True)  # daily, weekly, monthly

    # Document metrics
    total_documents = Column(Integer, default=0)
    active_documents = Column(Integer, default=0)
    documents_pending_review = Column(Integer, default=0)
    documents_overdue_review = Column(Integer, default=0)
    documents_expiring_soon = Column(Integer, default=0)

    # Compliance metrics
    total_requirements = Column(Integer, default=0)
    compliant_requirements = Column(Integer, default=0)
    non_compliant_requirements = Column(Integer, default=0)
    pending_requirements = Column(Integer, default=0)
    compliance_rate = Column(Float)  # Percentage

    # Review metrics
    scheduled_reviews = Column(Integer, default=0)
    completed_reviews = Column(Integer, default=0)
    overdue_reviews = Column(Integer, default=0)

    # Alert metrics
    active_alerts = Column(Integer, default=0)
    critical_alerts = Column(Integer, default=0)

    # Trend data
    trend_data = Column(JSONB)  # Historical trends

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("metric_date", "metric_type", name="uq_metric_date_type"),
        Index("ix_dashboard_metric_date_type", "metric_date", "metric_type"),
    )


class ComplianceAlert(Base):
    __tablename__ = "compliance_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Alert details
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(
        SQLEnum(LegalAlertSeverity, name="monitoringalertseverity", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Status
    status = Column(
        SQLEnum(AlertStatus, name="alertstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=AlertStatus.active,
        nullable=False,
        index=True
    )

    # Related entities
    document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    requirement_id = Column(
        Integer,
        ForeignKey("legal_compliance_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    review_cycle_id = Column(
        Integer,
        ForeignKey("document_review_cycles.id", ondelete="SET NULL"),
        nullable=True
    )

    # Alert metadata
    alert_type = Column(String(100))  # review_overdue, expiring_soon, non_compliant, etc.
    due_date = Column(Date, index=True)

    # Actions
    action_required = Column(Text)
    action_url = Column(String(500))

    # Assignment
    assigned_to_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Resolution
    acknowledged_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    document = relationship("LegalDocument")
    requirement = relationship("LegalComplianceRequirement")
    review_cycle = relationship("DocumentReviewCycle")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

    __table_args__ = (
        Index("ix_alert_severity_status", "severity", "status"),
        Index("ix_alert_due_date", "due_date"),
    )


class RegulatoryChange(Base):
    __tablename__ = "regulatory_changes"

    id = Column(Integer, primary_key=True, index=True)

    # Change identification
    title = Column(String(500), nullable=False, index=True)
    change_type = Column(
        SQLEnum(LegalChangeType, name="changetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Details
    description = Column(Text, nullable=False)
    legal_citation = Column(Text)
    jurisdiction = Column(String(200))
    issuing_authority = Column(String(200))

    # Dates
    announcement_date = Column(Date, nullable=False, index=True)
    effective_date = Column(Date, index=True)
    compliance_deadline = Column(Date, index=True)

    # Impact assessment
    impact_level = Column(String(50))  # Critical, High, Medium, Low
    affected_departments = Column(ARRAY(String))
    estimated_implementation_cost = Column(Float)

    # Analysis
    impact_analysis = Column(Text)
    required_actions = Column(JSONB, default=[])

    # Status
    is_reviewed = Column(Boolean, default=False)
    reviewed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True))

    # Implementation
    implementation_status = Column(String(100))
    implementation_notes = Column(Text)

    # Related requirements
    related_requirement_ids = Column(JSONB, default=[])

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_reg_change_effective_deadline", "effective_date", "compliance_deadline"),
        Index("ix_reg_change_announcement", "announcement_date"),
    )


class PolicyEnforcementTracking(Base):
    __tablename__ = "policy_enforcement_tracking"

    id = Column(Integer, primary_key=True, index=True)

    # Document reference
    document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Incident details
    incident_date = Column(Date, nullable=False, index=True)
    incident_description = Column(Text, nullable=False)
    policy_section_violated = Column(String(200))

    # Involved parties
    staff_member_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    department = Column(String(200))

    # Enforcement action
    action_taken = Column(
        SQLEnum(EnforcementAction, name="enforcementaction", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    action_date = Column(Date, nullable=False)
    action_details = Column(Text)

    # Follow-up
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(Date)
    follow_up_notes = Column(Text)

    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolution_date = Column(Date)
    resolution_notes = Column(Text)

    # Confidentiality
    is_confidential = Column(Boolean, default=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    document = relationship("LegalDocument")
    staff_member = relationship("User", foreign_keys=[staff_member_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_enforcement_incident_date", "incident_date"),
        Index("ix_enforcement_resolved", "is_resolved"),
    )
