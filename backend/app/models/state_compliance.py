# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import JSON
from sqlalchemy.sql import func

from ..core.database import Base
from ..core.branding import branding


class ConfidentialityStrength(StrEnum):
    STRICT = "strict"
    STANDARD = "standard"
    LIMITED = "limited"


class StateComplianceConfig(Base):
    __tablename__ = "state_compliance_configs"

    id = Column(Integer, primary_key=True, index=True)

    # State identification
    state_code = Column(String(2), unique=True, nullable=False, index=True)  # e.g., "CA", "NY"
    state_name = Column(String(100), nullable=False)  # e.g., "California"

    # =========================================================================
    # Patron Confidentiality Laws
    # =========================================================================

    # Reference to state law
    confidentiality_statute = Column(String(255), nullable=True)  # e.g., "Cal. Gov. Code § 6267"
    confidentiality_strength = Column(
        SQLEnum(ConfidentialityStrength, name="confidentialitystrength", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ConfidentialityStrength.STANDARD,
        nullable=False
    )

    # What constitutes valid legal process for disclosure
    requires_court_order = Column(Boolean, default=True, nullable=False)
    subpoena_sufficient = Column(Boolean, default=False, nullable=False)
    grand_jury_subpoena_required = Column(Boolean, default=False, nullable=False)

    # Patron notification requirements
    patron_notification_required = Column(Boolean, default=True, nullable=False)
    patron_notification_allowed = Column(Boolean, default=True, nullable=False)  # Some gag orders override
    notification_delay_days = Column(Integer, default=0, nullable=False)  # Days to wait before notifying

    # What records are protected
    circulation_records_protected = Column(Boolean, default=True, nullable=False)
    registration_records_protected = Column(Boolean, default=True, nullable=False)
    internet_usage_protected = Column(Boolean, default=True, nullable=False)
    program_attendance_protected = Column(Boolean, default=False, nullable=False)

    # =========================================================================
    # Data Retention Periods
    # =========================================================================

    # Override default retention periods (in years, null = use system default)
    checkout_record_retention_years = Column(Integer, nullable=True)
    financial_record_retention_years = Column(Integer, nullable=True)
    patron_data_retention_after_closure_days = Column(Integer, nullable=True)
    system_log_retention_days = Column(Integer, nullable=True)

    # Minimum retention required by state law
    minimum_financial_retention_years = Column(Integer, default=7, nullable=False)

    # =========================================================================
    # Law Enforcement Response Requirements
    # =========================================================================

    # Response timeline
    le_response_deadline_days = Column(Integer, default=30, nullable=False)
    le_extension_allowed = Column(Boolean, default=True, nullable=False)
    le_extension_max_days = Column(Integer, default=30, nullable=True)

    # Required steps
    le_legal_review_required = Column(Boolean, default=True, nullable=False)
    le_director_approval_required = Column(Boolean, default=True, nullable=False)
    le_scope_narrowing_required = Column(Boolean, default=True, nullable=False)

    # State-specific response template
    le_response_template_name = Column(String(100), nullable=True)

    # =========================================================================
    # State Library Reporting
    # =========================================================================

    # State library commission info
    state_library_name = Column(String(255), nullable=True)  # e.g., "California State Library"
    state_library_id = Column(String(50), nullable=True)  # Library's ID with state commission

    # Annual report requirements
    annual_report_due_month = Column(Integer, nullable=True)  # 1-12
    annual_report_due_day = Column(Integer, nullable=True)  # 1-31

    # Required statistics (JSON array of required stat types)
    required_statistics = Column(JSON, nullable=True)
    # e.g., ["circulation", "visits", "programs", "internet_sessions", "reference"]

    # State report template
    state_report_template = Column(String(100), nullable=True)

    # =========================================================================
    # ID Verification Requirements
    # =========================================================================

    # Registration requirements
    require_photo_id_for_adult_registration = Column(Boolean, default=False, nullable=False)
    require_photo_id_for_minor_registration = Column(Boolean, default=False, nullable=False)
    require_residency_proof = Column(Boolean, default=True, nullable=False)

    # Accepted ID types (JSON array)
    accepted_id_types = Column(JSON, nullable=True)
    # e.g., ["drivers_license", "state_id", "passport", "military_id", "student_id"]

    # Residency proof types (JSON array)
    residency_proof_types = Column(JSON, nullable=True)
    # e.g., ["utility_bill", "lease", "bank_statement", "government_mail"]

    # Age thresholds
    adult_age_threshold = Column(Integer, default=18, nullable=False)
    teen_age_threshold = Column(Integer, default=13, nullable=False)  # For separate teen policies

    # Card expiration
    default_card_validity_years = Column(Integer, default=3, nullable=False)

    # =========================================================================
    # Accessibility Requirements
    # =========================================================================

    # State-specific accessibility laws beyond federal ADA
    additional_accessibility_statute = Column(String(255), nullable=True)
    accessibility_notes = Column(Text, nullable=True)

    # =========================================================================
    # Metadata
    # =========================================================================

    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    # When the configuration was last reviewed
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    last_reviewed_by_id = Column(Integer, nullable=True)

    # Audit fields, server_default=func.now())


class StateConfidentialityException(Base):
    __tablename__ = "state_confidentiality_exceptions"

    id = Column(Integer, primary_key=True, index=True)

    state_code = Column(String(2), nullable=False, index=True)

    # Exception details
    exception_name = Column(String(200), nullable=False)
    exception_description = Column(Text, nullable=True)

    # When this exception applies
    applies_to_agency_type = Column(String(100), nullable=True)  # e.g., "law_enforcement", "child_services"
    applies_to_record_type = Column(String(100), nullable=True)  # e.g., "internet_usage", "circulation"
    requires_emergency = Column(Boolean, default=False, nullable=False)
    requires_minor_involved = Column(Boolean, default=False, nullable=False)

    # Legal reference
    statute_reference = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)


class StateReportTemplate(Base):
    __tablename__ = "state_report_templates"

    id = Column(Integer, primary_key=True, index=True)

    state_code = Column(String(2), nullable=False, index=True)
    template_name = Column(String(100), nullable=False, unique=True)
    template_description = Column(Text, nullable=True)

    # Report structure (JSON)
    # Maps our internal fields to state report fields
    field_mappings = Column(JSON, nullable=False)
    # e.g., {"total_circulation": "Q1_Circulation", "visits": "Q2_DoorCount"}

    # Required fields (JSON array)
    required_fields = Column(JSON, nullable=True)

    # Optional calculated fields (JSON array of formulas)
    calculated_fields = Column(JSON, nullable=True)
    # e.g., [{"name": "per_capita_circulation", "formula": "total_circulation / population"}]

    # Output format
    output_format = Column(String(20), default="xlsx", nullable=False)  # xlsx, csv, xml

    # Submission info
    submission_portal_url = Column(String(500), nullable=True)
    submission_instructions = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # Version tracking
    version = Column(String(20), nullable=True)  # e.g., "2025-2026"
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)


# Default configurations for common states
DEFAULT_STATE_CONFIGS = [
    {
        "state_code": "CA",
        "state_name": "California",
        "confidentiality_statute": "Cal. Gov. Code § 6267",
        "confidentiality_strength": ConfidentialityStrength.STRICT,
        "requires_court_order": True,
        "subpoena_sufficient": False,
        "patron_notification_required": True,
        "checkout_record_retention_years": 5,
        "require_photo_id_for_adult_registration": True,
        "state_library_name": "California State Library",
        "annual_report_due_month": 10,
        "annual_report_due_day": 15,
        "additional_accessibility_statute": "Unruh Civil Rights Act",
    },
    {
        "state_code": "TX",
        "state_name": "Texas",
        "confidentiality_statute": "Tex. Gov. Code § 552.124",
        "confidentiality_strength": ConfidentialityStrength.STANDARD,
        "requires_court_order": True,
        "grand_jury_subpoena_required": True,
        "patron_notification_required": True,
        "state_library_name": "Texas State Library and Archives Commission",
        "annual_report_due_month": 9,
        "annual_report_due_day": 30,
    },
    {
        "state_code": "NY",
        "state_name": "New York",
        "confidentiality_statute": "CPLR § 4509",
        "confidentiality_strength": ConfidentialityStrength.STRICT,
        "requires_court_order": True,
        "patron_notification_required": True,
        "state_library_name": "New York State Library",
        "annual_report_due_month": 12,
        "annual_report_due_day": 31,
    },
    {
        "state_code": "FL",
        "state_name": "Florida",
        "confidentiality_statute": "Fla. Stat. § 257.261",
        "confidentiality_strength": ConfidentialityStrength.STANDARD,
        "requires_court_order": True,
        "patron_notification_required": True,
        "state_library_name": "Florida Department of State, Division of Library and Information Services",
        "annual_report_due_month": 11,
        "annual_report_due_day": 1,
    },
    {
        "state_code": "IL",
        "state_name": "Illinois",
        "confidentiality_statute": "75 ILCS 70/1",
        "confidentiality_strength": ConfidentialityStrength.STRICT,
        "requires_court_order": True,
        "patron_notification_required": True,
        "patron_notification_allowed": True,
        "state_library_name": "Illinois State Library",
        "annual_report_due_month": 3,
        "annual_report_due_day": 1,
        "additional_accessibility_statute": "Illinois Human Rights Act",
    },
]


class LocalComplianceConfig(Base):
    __tablename__ = "local_compliance_configs"

    id = Column(Integer, primary_key=True, index=True)

    # Location identification
    state_code = Column(String(2), nullable=False, index=True)
    jurisdiction_type = Column(String(20), nullable=False)  # county, city, district, township
    jurisdiction_name = Column(String(200), nullable=False)  # e.g., "New York City", "Los Angeles County"
    jurisdiction_code = Column(String(50), nullable=True, index=True)  # FIPS code or custom ID

    # =========================================================================
    # Local Ordinances and Requirements
    # =========================================================================

    # Local privacy ordinances
    local_privacy_ordinance = Column(String(255), nullable=True)
    local_privacy_ordinance_url = Column(String(500), nullable=True)
    privacy_stricter_than_state = Column(Boolean, default=False, nullable=False)

    # Local data retention overrides (only if stricter than state)
    local_retention_override = Column(Boolean, default=False, nullable=False)
    checkout_record_retention_years = Column(Integer, nullable=True)
    financial_record_retention_years = Column(Integer, nullable=True)

    # Local ID requirements
    require_local_residency = Column(Boolean, default=False, nullable=False)
    local_residency_proof_types = Column(JSON, nullable=True)  # Additional accepted proofs
    non_resident_fee = Column(String(20), nullable=True)  # e.g., "$50/year"
    non_resident_allowed = Column(Boolean, default=True, nullable=False)

    # Local accessibility requirements
    local_accessibility_ordinance = Column(String(255), nullable=True)
    accessibility_contact_required = Column(Boolean, default=False, nullable=False)
    accessibility_contact_email = Column(String(255), nullable=True)
    accessibility_contact_phone = Column(String(20), nullable=True)

    # =========================================================================
    # Local Reporting Requirements
    # =========================================================================

    # Local library system/district info
    local_library_system = Column(String(255), nullable=True)  # e.g., "Brooklyn Public Library"
    local_system_id = Column(String(50), nullable=True)

    # Local reports (in addition to state)
    local_reports_required = Column(Boolean, default=False, nullable=False)
    local_report_types = Column(JSON, nullable=True)  # e.g., ["quarterly_usage", "annual_budget"]
    local_report_due_dates = Column(JSON, nullable=True)  # e.g., {"quarterly_usage": "15th of following month"}

    # =========================================================================
    # Special Programs and Requirements
    # =========================================================================

    # Local programs that may have compliance implications
    sanctuary_city_policies = Column(Boolean, default=False, nullable=False)  # Affects LE request handling
    local_children_programs = Column(JSON, nullable=True)  # Special programs for minors
    local_senior_programs = Column(JSON, nullable=True)  # Special programs for seniors
    local_ada_accommodations = Column(JSON, nullable=True)  # Local-specific accommodations

    # =========================================================================
    # Metadata
    # =========================================================================

    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    effective_date = Column(Date, nullable=True)

    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    last_reviewed_by_id = Column(Integer, nullable=True)


class RegulationMonitoringSource(StrEnum):
    STATE_LIBRARY = "state_library"
    STATE_LEGISLATURE = "state_legislature"
    FEDERAL = "federal"
    ALA = "ala"  # American Library Association
    LOCAL_GOVERNMENT = "local_government"
    COURT_DECISION = "court_decision"
    MANUAL = "manual"


class RegulationChangeStatus(StrEnum):
    PROPOSED = "proposed"
    PENDING = "pending"
    ENACTED = "enacted"
    EFFECTIVE = "effective"
    REPEALED = "repealed"
    UNDER_REVIEW = "under_review"


class RegulationMonitor(Base):
    __tablename__ = "regulation_monitors"

    id = Column(Integer, primary_key=True, index=True)

    # Regulation identification
    regulation_name = Column(String(500), nullable=False)
    regulation_number = Column(String(100), nullable=True)  # e.g., "HB 1234", "SB 567"
    jurisdiction_type = Column(String(20), nullable=False)  # federal, state, local
    jurisdiction_code = Column(String(50), nullable=True)  # State code or local FIPS

    # Source and tracking
    source = Column(
        SQLEnum(RegulationMonitoringSource, name="regulationmonitoringsource", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    source_url = Column(String(500), nullable=True)
    source_feed_url = Column(String(500), nullable=True)  # RSS/Atom feed URL

    # Status tracking
    status = Column(
        SQLEnum(RegulationChangeStatus, name="regulationchangestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RegulationChangeStatus.PROPOSED
    )
    proposed_date = Column(Date, nullable=True)
    enacted_date = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=True)

    # Content
    summary = Column(Text, nullable=True)
    full_text_url = Column(String(500), nullable=True)
    impact_assessment = Column(Text, nullable=True)

    # Categorization
    affects_patron_privacy = Column(Boolean, default=False, nullable=False)
    affects_data_retention = Column(Boolean, default=False, nullable=False)
    affects_law_enforcement = Column(Boolean, default=False, nullable=False)
    affects_accessibility = Column(Boolean, default=False, nullable=False)
    affects_reporting = Column(Boolean, default=False, nullable=False)
    affects_registration = Column(Boolean, default=False, nullable=False)

    # Alert settings
    priority = Column(String(20), default="medium", nullable=False)  # low, medium, high, critical
    requires_action = Column(Boolean, default=False, nullable=False)
    action_deadline = Column(Date, nullable=True)
    action_notes = Column(Text, nullable=True)

    # Review tracking
    reviewed = Column(Boolean, default=False, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(Integer, nullable=True)
    review_notes = Column(Text, nullable=True)

    # System configuration impact
    config_changes_required = Column(JSON, nullable=True)
    # e.g., {"state_compliance_configs": {"CA": {"field": "value"}}}

    is_active = Column(Boolean, default=True, nullable=False)


class RegulationAlert(Base):
    __tablename__ = "regulation_alerts"

    id = Column(Integer, primary_key=True, index=True)

    regulation_monitor_id = Column(Integer, nullable=False, index=True)

    # Alert details
    alert_type = Column(String(50), nullable=False)  # new_regulation, status_change, deadline_approaching
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium", nullable=False)

    # Assignment
    assigned_to_id = Column(Integer, nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)

    # Resolution
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(Integer, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Notification tracking
    notification_sent = Column(Boolean, default=False, nullable=False)
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    notification_recipients = Column(JSON, nullable=True)  # List of user IDs, server_default=func.now())


class VPATConformanceLevel(StrEnum):
    SUPPORTS = "supports"
    PARTIALLY_SUPPORTS = "partially_supports"
    DOES_NOT_SUPPORT = "does_not_support"
    NOT_APPLICABLE = "not_applicable"
    NOT_EVALUATED = "not_evaluated"


class VPATReport(Base):
    __tablename__ = "vpat_reports"

    id = Column(Integer, primary_key=True, index=True)

    # Report identification
    report_name = Column(String(255), nullable=False)
    report_version = Column(String(20), nullable=False)  # e.g., "2.4"
    vpat_version = Column(String(20), default="2.4", nullable=False)  # VPAT template version

    # Product information
    product_name = Column(String(255), nullable=False, default=branding.PRODUCT_FULL_NAME)
    product_version = Column(String(50), nullable=True)
    product_description = Column(Text, nullable=True)

    # Evaluation details
    evaluation_date = Column(Date, nullable=False)
    evaluator_name = Column(String(200), nullable=True)
    evaluator_organization = Column(String(200), nullable=True)
    evaluation_methods = Column(JSON, nullable=True)  # List of testing methods used

    # Contact information
    vendor_contact_name = Column(String(200), nullable=True)
    vendor_contact_email = Column(String(255), nullable=True)
    vendor_contact_phone = Column(String(20), nullable=True)

    # Applicable standards
    wcag_version = Column(String(10), default="2.1", nullable=False)
    wcag_level = Column(String(5), default="AA", nullable=False)  # A, AA, AAA
    section_508_applicable = Column(Boolean, default=True, nullable=False)
    en_301_549_applicable = Column(Boolean, default=False, nullable=False)  # EU standard

    # Overall conformance
    overall_conformance = Column(
        SQLEnum(VPATConformanceLevel, name="vpatconformancelevel", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=VPATConformanceLevel.PARTIALLY_SUPPORTS
    )

    # Notes
    general_notes = Column(Text, nullable=True)
    legal_disclaimer = Column(Text, nullable=True)

    # Status
    is_current = Column(Boolean, default=True, nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    created_by_id = Column(Integer, nullable=True)


class VPATCriterion(Base):
    __tablename__ = "vpat_criteria"

    id = Column(Integer, primary_key=True, index=True)

    vpat_report_id = Column(Integer, nullable=False, index=True)

    # Criterion identification
    standard = Column(String(50), nullable=False)  # "WCAG", "Section508", "EN301549"
    criterion_id = Column(String(20), nullable=False)  # e.g., "1.1.1", "1.2.1"
    criterion_name = Column(String(500), nullable=False)  # e.g., "Non-text Content"
    level = Column(String(5), nullable=True)  # A, AA, AAA (for WCAG)

    # Evaluation
    conformance_level = Column(
        SQLEnum(VPATConformanceLevel, name="vpatconformancelevel", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    remarks = Column(Text, nullable=True)  # Explanation of conformance level

    # Evidence
    test_results = Column(JSON, nullable=True)  # Detailed test results
    screenshots = Column(JSON, nullable=True)  # URLs to evidence screenshots, server_default=func.now())


class ComplianceDashboardWidget(StrEnum):
    UPCOMING_DEADLINES = "upcoming_deadlines"
    REGULATION_ALERTS = "regulation_alerts"
    COMPLIANCE_SCORE = "compliance_score"
    LE_REQUESTS_PENDING = "le_requests_pending"
    RETENTION_STATUS = "retention_status"
    ACCESSIBILITY_STATUS = "accessibility_status"
    STATE_CONFIG_STATUS = "state_config_status"
    LOCAL_CONFIG_STATUS = "local_config_status"
    RECENT_CHANGES = "recent_changes"


class ComplianceDashboardConfig(Base):
    __tablename__ = "compliance_dashboard_configs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, nullable=False, unique=True, index=True)

    # Widget configuration (JSON array of enabled widgets and their order)
    enabled_widgets = Column(JSON, nullable=False)
    # e.g., ["upcoming_deadlines", "regulation_alerts", "compliance_score"]

    # Alert preferences
    email_alerts_enabled = Column(Boolean, default=True, nullable=False)
    alert_frequency = Column(String(20), default="daily", nullable=False)  # immediate, daily, weekly
    alert_priorities = Column(JSON, nullable=True)  # Which priorities to alert on

    # View preferences
    default_state_filter = Column(String(2), nullable=True)  # Default state to show
    default_date_range_days = Column(Integer, default=90, nullable=False)


# Default VPAT criteria for WCAG 2.1 AA
DEFAULT_WCAG_21_AA_CRITERIA = [
    # Perceivable
    {"criterion_id": "1.1.1", "criterion_name": "Non-text Content", "level": "A"},
    {"criterion_id": "1.2.1", "criterion_name": "Audio-only and Video-only (Prerecorded)", "level": "A"},
    {"criterion_id": "1.2.2", "criterion_name": "Captions (Prerecorded)", "level": "A"},
    {"criterion_id": "1.2.3", "criterion_name": "Audio Description or Media Alternative (Prerecorded)", "level": "A"},
    {"criterion_id": "1.2.4", "criterion_name": "Captions (Live)", "level": "AA"},
    {"criterion_id": "1.2.5", "criterion_name": "Audio Description (Prerecorded)", "level": "AA"},
    {"criterion_id": "1.3.1", "criterion_name": "Info and Relationships", "level": "A"},
    {"criterion_id": "1.3.2", "criterion_name": "Meaningful Sequence", "level": "A"},
    {"criterion_id": "1.3.3", "criterion_name": "Sensory Characteristics", "level": "A"},
    {"criterion_id": "1.3.4", "criterion_name": "Orientation", "level": "AA"},
    {"criterion_id": "1.3.5", "criterion_name": "Identify Input Purpose", "level": "AA"},
    {"criterion_id": "1.4.1", "criterion_name": "Use of Color", "level": "A"},
    {"criterion_id": "1.4.2", "criterion_name": "Audio Control", "level": "A"},
    {"criterion_id": "1.4.3", "criterion_name": "Contrast (Minimum)", "level": "AA"},
    {"criterion_id": "1.4.4", "criterion_name": "Resize Text", "level": "AA"},
    {"criterion_id": "1.4.5", "criterion_name": "Images of Text", "level": "AA"},
    {"criterion_id": "1.4.10", "criterion_name": "Reflow", "level": "AA"},
    {"criterion_id": "1.4.11", "criterion_name": "Non-text Contrast", "level": "AA"},
    {"criterion_id": "1.4.12", "criterion_name": "Text Spacing", "level": "AA"},
    {"criterion_id": "1.4.13", "criterion_name": "Content on Hover or Focus", "level": "AA"},
    # Operable
    {"criterion_id": "2.1.1", "criterion_name": "Keyboard", "level": "A"},
    {"criterion_id": "2.1.2", "criterion_name": "No Keyboard Trap", "level": "A"},
    {"criterion_id": "2.1.4", "criterion_name": "Character Key Shortcuts", "level": "A"},
    {"criterion_id": "2.2.1", "criterion_name": "Timing Adjustable", "level": "A"},
    {"criterion_id": "2.2.2", "criterion_name": "Pause, Stop, Hide", "level": "A"},
    {"criterion_id": "2.3.1", "criterion_name": "Three Flashes or Below Threshold", "level": "A"},
    {"criterion_id": "2.4.1", "criterion_name": "Bypass Blocks", "level": "A"},
    {"criterion_id": "2.4.2", "criterion_name": "Page Titled", "level": "A"},
    {"criterion_id": "2.4.3", "criterion_name": "Focus Order", "level": "A"},
    {"criterion_id": "2.4.4", "criterion_name": "Link Purpose (In Context)", "level": "A"},
    {"criterion_id": "2.4.5", "criterion_name": "Multiple Ways", "level": "AA"},
    {"criterion_id": "2.4.6", "criterion_name": "Headings and Labels", "level": "AA"},
    {"criterion_id": "2.4.7", "criterion_name": "Focus Visible", "level": "AA"},
    {"criterion_id": "2.5.1", "criterion_name": "Pointer Gestures", "level": "A"},
    {"criterion_id": "2.5.2", "criterion_name": "Pointer Cancellation", "level": "A"},
    {"criterion_id": "2.5.3", "criterion_name": "Label in Name", "level": "A"},
    {"criterion_id": "2.5.4", "criterion_name": "Motion Actuation", "level": "A"},
    # Understandable
    {"criterion_id": "3.1.1", "criterion_name": "Language of Page", "level": "A"},
    {"criterion_id": "3.1.2", "criterion_name": "Language of Parts", "level": "AA"},
    {"criterion_id": "3.2.1", "criterion_name": "On Focus", "level": "A"},
    {"criterion_id": "3.2.2", "criterion_name": "On Input", "level": "A"},
    {"criterion_id": "3.2.3", "criterion_name": "Consistent Navigation", "level": "AA"},
    {"criterion_id": "3.2.4", "criterion_name": "Consistent Identification", "level": "AA"},
    {"criterion_id": "3.3.1", "criterion_name": "Error Identification", "level": "A"},
    {"criterion_id": "3.3.2", "criterion_name": "Labels or Instructions", "level": "A"},
    {"criterion_id": "3.3.3", "criterion_name": "Error Suggestion", "level": "AA"},
    {"criterion_id": "3.3.4", "criterion_name": "Error Prevention (Legal, Financial, Data)", "level": "AA"},
    # Robust
    {"criterion_id": "4.1.1", "criterion_name": "Parsing", "level": "A"},
    {"criterion_id": "4.1.2", "criterion_name": "Name, Role, Value", "level": "A"},
    {"criterion_id": "4.1.3", "criterion_name": "Status Messages", "level": "AA"},
]
