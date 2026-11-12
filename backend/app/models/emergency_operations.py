# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============ OFFLINE MODE & DATA SYNC ============

class OfflineModeStatus(StrEnum):
    ONLINE = "online"  # Normal operations
    DEGRADED = "degraded"  # Partial service degradation
    OFFLINE = "offline"  # Full system offline
    RECOVERY = "recovery"  # Syncing data back online


class OfflineMode(Base):
    __tablename__ = "offline_modes"

    id = Column(Integer, primary_key=True, index=True)

    # Mode status
    status = Column(
        String(50),
        default=OfflineModeStatus.ONLINE, nullable=False, index=True
    )

    # Activation details
    activated_at = Column(DateTime(timezone=True), nullable=True, index=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    reason = Column(String(200), nullable=True)  # e.g., "Power outage", "Internet down", "Ransomware attack"

    # Scope of outage
    affected_services = Column(JSON, nullable=True)  # ["circulation", "catalog", "patron_accounts"]
    affected_branches = Column(JSON, nullable=True)  # [1, 2, 3] branch IDs or null for all
    is_building_wide = Column(Boolean, default=False)

    # Mode configuration
    enable_paper_checkout = Column(Boolean, default=True)  # Allow paper-based circulation
    enable_phone_renewals = Column(Boolean, default=True)  # Phone-based renewals
    enable_hold_bypass = Column(Boolean, default=False)  # Skip hold validation
    sync_on_restore = Column(Boolean, default=True)  # Auto-sync when restored

    # Recovery info
    estimated_restoration_time = Column(DateTime(timezone=True), nullable=True)
    recovery_priority = Column(String(50), default="normal")  # critical, high, normal

    # Audit
    activated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deactivated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    activated_by = relationship("User", foreign_keys=[activated_by_id])
    deactivated_by = relationship("User", foreign_keys=[deactivated_by_id])


class PaperBackupForm(Base):
    __tablename__ = "paper_backup_forms"

    id = Column(Integer, primary_key=True, index=True)

    # Form type
    form_type = Column(
        String(50), nullable=False, index=True
    )  # checkout, return, renewal, hold, waiver

    # Template information
    form_name = Column(String(100), nullable=False)
    form_description = Column(Text, nullable=True)
    form_template = Column(Text, nullable=True)  # HTML template or JSON schema
    is_active = Column(Boolean, default=True, index=True)

    # Print configuration
    pages_required = Column(Integer, default=1)
    print_instructions = Column(Text, nullable=True)
    barcode_required = Column(Boolean, default=True)
    signature_required = Column(Boolean, default=True)

    # Tracking
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User")


class PaperBackupSubmission(Base):
    __tablename__ = "paper_backup_submissions"

    id = Column(Integer, primary_key=True, index=True)

    # Form reference
    form_id = Column(Integer, ForeignKey("paper_backup_forms.id", ondelete="CASCADE"), nullable=False)

    # Transaction details
    form_type = Column(String(50), nullable=False, index=True)
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    staff_initials = Column(String(10), nullable=False)

    # Patron/Item info
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    item_barcode = Column(String(100), nullable=True)
    item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)
    patron_name = Column(String(100), nullable=True)  # Fallback if ID unavailable

    # Form content
    form_data = Column(JSON, nullable=False)  # All submitted fields
    notes = Column(Text, nullable=True)

    # Sync status
    synced = Column(Boolean, default=False, index=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_conflict = Column(Text, nullable=True)  # Conflict if item already returned, etc.
    sync_resolution = Column(String(50), nullable=True)  # manual_review, auto_accepted, rejected

    # File tracking
    form_image_url = Column(String(255), nullable=True)  # Scanned paper form
    form_image_backup_url = Column(String(255), nullable=True)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    form = relationship("PaperBackupForm")
    patron = relationship("User", foreign_keys=[patron_id])
    item = relationship("CatalogItem")
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


class DataSyncQueue(Base):
    __tablename__ = "data_sync_queue"

    id = Column(Integer, primary_key=True, index=True)

    # Sync details
    sync_source = Column(String(50), nullable=False, index=True)  # paper_forms, local_cache, offline_device
    entity_type = Column(String(50), nullable=False, index=True)  # checkout, hold, renewal, etc.
    entity_id = Column(String(100), nullable=True)
    entity_data = Column(JSON, nullable=False)

    # Priority and status
    priority = Column(Integer, default=0)  # Higher = process first
    status = Column(String(50), default="pending", index=True)  # pending, processing, synced, failed
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Error tracking
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    processed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    processed_by = relationship("User", foreign_keys=[processed_by_id])


# ============ EMERGENCY CONTACT CASCADE ============

class EmergencyContactCascade(Base):
    __tablename__ = "emergency_contact_cascades"

    id = Column(Integer, primary_key=True, index=True)

    # Cascade configuration
    cascade_name = Column(String(100), nullable=False, unique=True, index=True)
    cascade_description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # Trigger configuration
    auto_trigger_events = Column(JSON, nullable=True)  # ["building_closure", "power_outage", "data_loss"]
    manual_approval_required = Column(Boolean, default=True)
    max_contact_levels = Column(Integer, default=5)

    # Template
    message_template = Column(Text, nullable=True)
    include_affected_services = Column(Boolean, default=True)
    include_estimated_restoration = Column(Boolean, default=True)
    include_interim_procedures = Column(Boolean, default=True)

    # Execution tracking
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User")


class OperationContactCascade(Base):
    __tablename__ = "operation_contact_cascades"

    id = Column(Integer, primary_key=True, index=True)

    cascade_id = Column(
        Integer, ForeignKey("emergency_contact_cascades.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Contact hierarchy
    level = Column(Integer, nullable=False)  # 1 = first contact, 2 = second, etc.
    contact_role = Column(String(100), nullable=False)  # Library Director, Assistant Director, etc.

    # Contact information
    contact_name = Column(String(100), nullable=False)
    contact_email = Column(String(100), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_phone_backup = Column(String(20), nullable=True)
    contact_method = Column(String(50), default="email")  # email, sms, phone_call, all

    # Notification rules
    condition_triggers = Column(JSON, nullable=True)  # When to notify this contact
    wait_time_seconds = Column(Integer, default=0)  # Wait before notifying next level
    retry_attempts = Column(Integer, default=2)

    # Auto-escalation
    escalate_if_no_response = Column(Boolean, default=True)
    escalation_timeout_minutes = Column(Integer, default=10)

    # Availability
    available_start_time = Column(String(10), nullable=True)  # HH:MM format
    available_end_time = Column(String(10), nullable=True)
    available_days = Column(String(50), nullable=True)  # Mon,Tue,Wed,Thu,Fri

    # Status
    is_active = Column(Boolean, default=True, index=True)
    order_index = Column(Integer, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    cascade = relationship("EmergencyContactCascade", backref="contacts")


class CascadeExecutionLog(Base):
    __tablename__ = "cascade_execution_logs"

    id = Column(Integer, primary_key=True, index=True)

    cascade_id = Column(
        Integer, ForeignKey("emergency_contact_cascades.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Execution details
    trigger_reason = Column(String(100), nullable=False)
    initiated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    initiated_at = Column(DateTime(timezone=True), default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Contacts reached
    total_contacts_to_reach = Column(Integer, default=0)
    total_contacts_reached = Column(Integer, default=0)
    contacts_not_reached = Column(Integer, default=0)

    # Status summary
    execution_summary = Column(JSON, nullable=True)  # Level 1: successful, Level 2: failed, etc.

    # Relationships
    cascade = relationship("EmergencyContactCascade")
    initiated_by = relationship("User")


class CascadeContactNotification(Base):
    __tablename__ = "cascade_contact_notifications"

    id = Column(Integer, primary_key=True, index=True)

    execution_log_id = Column(
        Integer, ForeignKey("cascade_execution_logs.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    contact_id = Column(Integer, ForeignKey("operation_contact_cascades.id", ondelete="CASCADE"), nullable=False)

    # Notification attempt
    attempt_number = Column(Integer, default=1)
    contacted_at = Column(DateTime(timezone=True), nullable=True)
    method_used = Column(String(50), nullable=True)  # email, sms, phone_call
    response_status = Column(String(50), default="pending")  # pending, reached, no_answer, declined

    # Response
    contact_response = Column(Text, nullable=True)
    response_received_at = Column(DateTime(timezone=True), nullable=True)

    # Next action
    next_escalation_time = Column(DateTime(timezone=True), nullable=True)
    escalate_to_next_contact = Column(Boolean, default=False)

    # Relationships
    execution_log = relationship("CascadeExecutionLog")
    contact = relationship("OperationContactCascade")


# ============ BUILDING CLOSURE COMMUNICATION ============

class BuildingClosureReason(StrEnum):
    WEATHER = "weather"
    POWER_OUTAGE = "power_outage"
    SYSTEM_FAILURE = "system_failure"
    SECURITY_INCIDENT = "security_incident"
    NATURAL_DISASTER = "natural_disaster"
    PANDEMIC = "pandemic"
    INFRASTRUCTURE_DAMAGE = "infrastructure_damage"
    SCHEDULED_MAINTENANCE = "scheduled_maintenance"
    OTHER = "other"


class BuildingClosure(Base):
    __tablename__ = "building_closures"

    id = Column(Integer, primary_key=True, index=True)

    # Closure details
    closure_reason = Column(
        String(50),
        nullable=False, index=True
    )
    reason_details = Column(Text, nullable=False)
    severity_level = Column(String(20), default="moderate")  # minimal, moderate, severe, critical

    # Timeline
    closure_start = Column(DateTime(timezone=True), nullable=False, index=True)
    estimated_reopening = Column(DateTime(timezone=True), nullable=True)
    actual_reopening = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # Affected areas
    branches_affected = Column(JSON, nullable=True)  # [1, 2, 3] or null for all
    areas_affected = Column(JSON, nullable=True)  # ["Main Floor", "Children's Area"]

    # Communication status
    patrons_notified = Column(Boolean, default=False)
    staff_notified = Column(Boolean, default=False)
    volunteers_notified = Column(Boolean, default=False)
    board_notified = Column(Boolean, default=False)

    # Communication details
    patron_message = Column(Text, nullable=True)
    staff_message = Column(Text, nullable=True)
    public_message = Column(Text, nullable=True)
    website_update = Column(Text, nullable=True)

    # Media/communication channels
    email_sent = Column(Boolean, default=False)
    sms_sent = Column(Boolean, default=False)
    social_media_posted = Column(Boolean, default=False)
    emergency_alert_issued = Column(Boolean, default=False)

    # Services status
    services_affected = Column(JSON, nullable=True)  # ["circulation", "catalog", "events"]
    services_unavailable = Column(JSON, nullable=True)
    interim_services = Column(Text, nullable=True)  # What services remain available

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


# ============ SERVICE CONTINUITY PRIORITIES ============

class ServicePriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ServiceContinuityPriority(Base):
    __tablename__ = "service_continuity_priorities"

    id = Column(Integer, primary_key=True, index=True)

    # Service definition
    service_name = Column(String(100), nullable=False, unique=True, index=True)
    service_description = Column(Text, nullable=True)
    service_category = Column(String(50), nullable=False)  # circulation, catalog, patron_services, etc.

    # Priority level
    priority = Column(
        String(50),
        nullable=False, index=True
    )

    # Continuity requirements
    rto_minutes = Column(Integer, nullable=False)  # Recovery Time Objective
    rpo_minutes = Column(Integer, nullable=False)  # Recovery Point Objective (data loss acceptable)
    max_acceptable_downtime = Column(Integer, nullable=False)  # Minutes

    # Fallback procedures
    has_paper_process = Column(Boolean, default=False)
    has_phone_process = Column(Boolean, default=False)
    manual_workaround = Column(Text, nullable=True)
    estimated_manual_capacity = Column(String(100), nullable=True)  # e.g., "80% of normal"

    # Resource requirements
    required_staff_roles = Column(JSON, nullable=True)  # ["Circulation Librarian", "Asst Manager"]
    required_equipment = Column(JSON, nullable=True)  # ["Scanner", "Printer"]
    critical_forms = Column(JSON, nullable=True)  # ["Checkout", "Return", "Renewal"]

    # Dependencies
    depends_on_services = Column(JSON, nullable=True)  # Service IDs this depends on
    supports_services = Column(JSON, nullable=True)  # Service IDs this enables

    # Monitoring
    is_monitored = Column(Boolean, default=True)
    status_check_frequency_minutes = Column(Integer, default=5)

    # Status


# ============ COLLECTION RECOVERY ============

class DamageAssessmentStatus(StrEnum):
    NOT_ASSESSED = "not_assessed"
    ASSESSED = "assessed"
    SALVAGEABLE = "salvageable"
    UNSALVAGEABLE = "unsalvageable"
    UNDER_TREATMENT = "under_treatment"
    RECOVERED = "recovered"


class CollectionRecoveryProject(Base):
    __tablename__ = "collection_recovery_projects"

    id = Column(Integer, primary_key=True, index=True)

    # Project info
    project_name = Column(String(100), nullable=False, unique=True, index=True)
    project_description = Column(Text, nullable=True)
    disaster_type = Column(String(100), nullable=False)  # Fire, Water, Mold, Theft, etc.
    disaster_date = Column(DateTime(timezone=True), nullable=False)

    # Scope
    affected_areas = Column(JSON, nullable=False)  # Rooms/collections affected
    estimated_items_affected = Column(Integer, nullable=True)
    total_items_assessed = Column(Integer, default=0)
    items_salvaged = Column(Integer, default=0)
    items_lost = Column(Integer, default=0)

    # Timeline
    project_start = Column(DateTime(timezone=True), default=func.now())
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    actual_completion = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # Resources
    lead_staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)

    # Process details
    assessment_procedure = Column(Text, nullable=True)
    treatment_procedures = Column(Text, nullable=True)
    reintegration_plan = Column(Text, nullable=True)

    # Documentation
    has_photos = Column(Boolean, default=False)
    has_video = Column(Boolean, default=False)
    documentation_location = Column(String(255), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    lead_staff = relationship("User")
    vendor = relationship("Vendor")


class DamagedItem(Base):
    __tablename__ = "damaged_items"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer, ForeignKey("collection_recovery_projects.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Item identification
    item_id = Column(Integer, ForeignKey("item_copies.id", ondelete="SET NULL"), nullable=True)
    item_barcode = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    author = Column(String(100), nullable=True)

    # Damage assessment
    damage_type = Column(String(100), nullable=False)  # Water damage, burn, mold, etc.
    damage_severity = Column(String(20), nullable=False)  # Minor, moderate, severe
    damage_description = Column(Text, nullable=False)
    damage_photo_url = Column(String(255), nullable=True)

    # Assessment outcome
    assessment_status = Column(
        String(50),
        default=DamageAssessmentStatus.NOT_ASSESSED, nullable=False, index=True
    )

    # Salvage decision
    is_salvageable = Column(Boolean, nullable=True)
    salvage_method = Column(String(100), nullable=True)  # Air drying, freezing, professional restoration
    estimated_repair_cost = Column(Float, nullable=True)
    replacement_cost = Column(Float, nullable=True)

    # Recovery status
    recovery_status = Column(String(50), default="pending")  # pending, in_progress, complete, disposed
    date_assessed = Column(DateTime(timezone=True), nullable=True)
    date_recovered = Column(DateTime(timezone=True), nullable=True)
    assessed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Insurance
    included_in_claim = Column(Boolean, default=False)
    claim_amount = Column(Float, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("CollectionRecoveryProject")
    item = relationship("ItemCopy")
    assessed_by = relationship("User")


# ============ INSURANCE DOCUMENTATION ============

class InsuranceDocumentation(Base):
    __tablename__ = "insurance_documentations"

    id = Column(Integer, primary_key=True, index=True)

    # Incident details
    incident_date = Column(DateTime(timezone=True), nullable=False)
    incident_type = Column(String(100), nullable=False)  # Fire, Water, Theft, etc.
    incident_description = Column(Text, nullable=False)
    incident_location = Column(String(200), nullable=True)

    # Claim information
    claim_number = Column(String(50), unique=True, index=True)
    insurance_company = Column(String(100), nullable=False)
    agent_name = Column(String(100), nullable=False)
    agent_phone = Column(String(20), nullable=False)
    agent_email = Column(String(100), nullable=False)

    # Financial impact
    initial_damage_estimate = Column(Float, nullable=False)
    final_damage_amount = Column(Float, nullable=True)
    claimed_amount = Column(Float, nullable=True)
    approved_amount = Column(Float, nullable=True)
    reimbursed_amount = Column(Float, nullable=True)

    # Documentation status
    documentation_complete = Column(Boolean, default=False, index=True)
    claim_submitted = Column(Boolean, default=False)
    claim_submitted_date = Column(DateTime(timezone=True), nullable=True)
    claim_approved = Column(Boolean, default=False)
    claim_approved_date = Column(DateTime(timezone=True), nullable=True)

    # Required documents checklist
    has_incident_report = Column(Boolean, default=False)
    has_photos = Column(Boolean, default=False)
    has_inventory_list = Column(Boolean, default=False)
    has_repair_estimates = Column(Boolean, default=False)
    has_receipts = Column(Boolean, default=False)
    has_expert_assessment = Column(Boolean, default=False)

    # Document storage
    documents_location = Column(String(255), nullable=True)
    claims_file_location = Column(String(255), nullable=True)

    # Timeline
    claim_deadline = Column(DateTime(timezone=True), nullable=True)
    expected_resolution_date = Column(DateTime(timezone=True), nullable=True)

    # Assigned contact
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    assigned_to = relationship("User")


# ============ POST-DISASTER ASSESSMENT ============

class DisasterAssessmentPhase(StrEnum):
    INITIAL = "initial"  # First hours assessment
    DETAILED = "detailed"  # 24-48 hours comprehensive assessment
    RECOVERY_PLANNING = "recovery_planning"  # Planning phase
    RECOVERY_EXECUTION = "recovery_execution"  # Active recovery


class PostDisasterAssessment(Base):
    __tablename__ = "post_disaster_assessments"

    id = Column(Integer, primary_key=True, index=True)

    # Assessment details
    assessment_date = Column(DateTime(timezone=True), default=func.now(), nullable=False, index=True)
    disaster_type = Column(String(100), nullable=False)
    disaster_date = Column(DateTime(timezone=True), nullable=False)

    # Assessment scope
    phase = Column(
        String(50),
        default=DisasterAssessmentPhase.INITIAL, nullable=False
    )
    areas_assessed = Column(JSON, nullable=False)  # Rooms/sections assessed
    assessment_team = Column(JSON, nullable=False)  # Staff IDs

    # Infrastructure assessment
    building_exterior_damage = Column(Integer, default=0)  # Percentage damage 0-100
    building_interior_damage = Column(Integer, default=0)
    roof_damage = Column(Text, nullable=True)
    structural_integrity = Column(String(50), nullable=True)  # Safe, compromised, hazardous
    utilities_status = Column(JSON, nullable=True)  # {electricity: status, water: status, HVAC: status}

    # Safety hazards
    hazards_identified = Column(JSON, nullable=True)  # ["Broken glass", "Mold", "Chemical spill"]
    hazard_severity_level = Column(String(50), nullable=True)  # None, Minor, Moderate, Severe
    safety_recommendations = Column(Text, nullable=True)

    # Collection assessment
    collection_damage_estimate_percent = Column(Float, nullable=True)
    materials_affected = Column(JSON, nullable=True)  # Types: books, periodicals, media, etc.
    mold_presence = Column(Boolean, default=False)
    mold_extent = Column(Text, nullable=True)

    # Technology assessment
    servers_operational = Column(Boolean, nullable=True)
    network_operational = Column(Boolean, nullable=True)
    backup_systems_operational = Column(Boolean, nullable=True)
    data_integrity_status = Column(String(100), nullable=True)

    # Service capability assessment
    patron_services_available = Column(Boolean, default=False)
    circulation_possible = Column(Boolean, default=False)
    estimated_service_restoration_hours = Column(Integer, nullable=True)

    # Financial impact estimate
    estimated_property_damage = Column(Float, nullable=True)
    estimated_content_loss = Column(Float, nullable=True)
    estimated_income_loss = Column(Float, nullable=True)
    estimated_recovery_cost = Column(Float, nullable=True)

    # Photos and documentation
    photo_count = Column(Integer, default=0)
    documentation_notes = Column(Text, nullable=True)
    photos_location = Column(String(255), nullable=True)

    # Recommendations
    immediate_actions_required = Column(Text, nullable=True)
    short_term_recovery_plan = Column(Text, nullable=True)
    long_term_recovery_plan = Column(Text, nullable=True)

    # Assessment completion
    assessment_complete = Column(Boolean, default=False)
    lead_assessor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    lead_assessor = relationship("User")


# ============ COMMUNITY RESOURCE HUB ============

class CommunityResourceHub(Base):
    __tablename__ = "community_resource_hubs"

    id = Column(Integer, primary_key=True, index=True)

    # Hub identification
    hub_name = Column(String(100), nullable=False, unique=True, index=True)
    branch_id = Column(Integer, nullable=False)
    location_description = Column(String(255), nullable=False)

    # Hub purpose
    hub_purposes = Column(JSON, nullable=False)  # ["Emergency shelter", "Charging station", "Water/food"]
    emergency_types = Column(JSON, nullable=False)  # ["Natural disaster", "Power outage", "Pandemic"]

    # Capacity and resources
    max_capacity = Column(Integer, nullable=False)
    has_generator_backup = Column(Boolean, default=False)
    has_internet_connectivity = Column(Boolean, default=False)
    has_water_supply = Column(Boolean, default=False)
    has_food_storage = Column(Boolean, default=False)
    has_medical_supplies = Column(Boolean, default=False)
    has_charging_stations = Column(Boolean, default=False)
    has_meeting_spaces = Column(Boolean, default=False)

    # Staffing
    required_staff_count = Column(Integer, default=0)
    required_staff_roles = Column(JSON, nullable=True)
    volunteer_coordinator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Activation status
    is_active = Column(Boolean, default=False, index=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    activation_reason = Column(String(100), nullable=True)

    # Resource checklist
    supplies_stocked = Column(Boolean, default=False)
    equipment_tested = Column(Boolean, default=False)
    staff_trained = Column(Boolean, default=False)
    emergency_procedures_reviewed = Column(Boolean, default=False)

    # Communication
    activation_message = Column(Text, nullable=True)
    operating_hours = Column(String(100), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(100), nullable=True)

    # Resources availability
    resources_available = Column(JSON, nullable=True)  # List of available resources
    services_offered = Column(JSON, nullable=True)  # Services provided

    # Documentation
    activation_procedures = Column(Text, nullable=True)
    resource_inventory = Column(Text, nullable=True)
    staff_assignments = Column(JSON, nullable=True)  # {role: staff_id}

    # Status tracking
    current_capacity_used = Column(Integer, default=0)
    visitors_served_count = Column(Integer, default=0)
    supplies_consumption_rate = Column(String(50), nullable=True)  # Rate of supply consumption
    activated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    # DISABLED: # DISABLED: branch relationship
    volunteer_coordinator = relationship("User", foreign_keys=[volunteer_coordinator_id])
    activated_by = relationship("User", foreign_keys=[activated_by_id])
