# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from decimal import Decimal
from enum import Enum, StrEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Date,
    Index,
    Text,
    text,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    ARRAY,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


# =============================================================================
# Enums
# =============================================================================


class ResourceType(StrEnum):
    printer_3d = "printer_3d"
    laser_cutter = "laser_cutter"
    cnc_router = "cnc_router"
    vinyl_cutter = "vinyl_cutter"
    embroidery_machine = "embroidery_machine"
    sewing_machine = "sewing_machine"
    soldering_station = "soldering_station"
    electronics_workbench = "electronics_workbench"
    woodworking_station = "woodworking_station"
    recording_studio = "recording_studio"
    video_editing_station = "video_editing_station"
    vr_station = "vr_station"
    other = "other"


class ResourceStatus(StrEnum):
    available = "available"
    in_use = "in_use"
    maintenance = "maintenance"
    out_of_order = "out_of_order"
    reserved = "reserved"
    retired = "retired"


class MakerspaceReservationStatus(StrEnum):
    pending = "pending"  # Awaiting staff approval
    confirmed = "confirmed"  # Approved and scheduled
    checked_in = "checked_in"  # Patron has started session
    completed = "completed"  # Session finished
    cancelled = "cancelled"  # Cancelled by patron or staff
    no_show = "no_show"  # Patron didn't show up
    expired = "expired"  # Passed without completion


class JobStatus(StrEnum):
    submitted = "submitted"  # Initial submission
    pending_review = "pending_review"  # Awaiting staff review
    rejected = "rejected"  # Staff rejected the job
    approved = "approved"  # Staff approved, awaiting queue
    queued = "queued"  # In the print queue
    in_progress = "in_progress"  # Currently printing
    paused = "paused"  # Temporarily paused
    failed = "failed"  # Print failed
    completed = "completed"  # Finished successfully
    ready_pickup = "ready_pickup"  # Ready for patron pickup
    picked_up = "picked_up"  # Patron collected the item
    cancelled = "cancelled"  # Cancelled


class JobPriority(StrEnum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class CertificationStatus(StrEnum):
    pending = "pending"  # Training scheduled/in progress
    active = "active"  # Certified and can use equipment
    expired = "expired"  # Certification expired
    suspended = "suspended"  # Suspended due to incident/violation
    revoked = "revoked"  # Permanently revoked


class MakerspaceIncidentSeverity(StrEnum):
    minor = "minor"  # No injury, minor issue
    moderate = "moderate"  # Minor injury or near-miss
    serious = "serious"  # Injury requiring first aid
    critical = "critical"  # Serious injury, equipment damage


class MaintenanceType(StrEnum):
    preventive = "preventive"  # Scheduled routine maintenance
    corrective = "corrective"  # Fix a known issue
    emergency = "emergency"  # Urgent repair needed
    calibration = "calibration"  # Calibration/alignment
    cleaning = "cleaning"  # Regular cleaning
    upgrade = "upgrade"  # Hardware/software upgrade


class MaintenanceStatus(StrEnum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    overdue = "overdue"


class ConsumableUnit(StrEnum):
    grams = "grams"
    kilograms = "kilograms"
    meters = "meters"
    feet = "feet"
    sheets = "sheets"
    pieces = "pieces"
    liters = "liters"
    milliliters = "milliliters"


class PaymentStatus(StrEnum):
    pending = "pending"
    paid = "paid"
    waived = "waived"
    refunded = "refunded"
    failed = "failed"


# =============================================================================
# Makerspace Resource Model
# =============================================================================


class MakerspaceResource(Base):
    __tablename__ = "makerspace_resources"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    resource_type = Column(
        SQLEnum(
            ResourceType,
            name="resourcetype",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Location & identification
    location = Column(String(200), nullable=True)
    asset_tag = Column(String(50), unique=True, nullable=True, index=True)
    serial_number = Column(String(100), nullable=True)
    manufacturer = Column(String(200), nullable=True)
    model = Column(String(200), nullable=True)

    # Status
    status = Column(
        SQLEnum(
            ResourceStatus,
            name="resourcestatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ResourceStatus.available,
        nullable=False,
    )
    status_notes = Column(Text, nullable=True)

    # Certification requirements
    requires_certification = Column(Boolean, default=True, nullable=False)
    certification_type_id = Column(
        Integer, ForeignKey("makerspace_certification_types.id", ondelete="SET NULL"), nullable=True
    )
    minimum_age = Column(Integer, default=0, nullable=False)

    # Costs
    hourly_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    setup_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Scheduling
    max_reservation_hours = Column(Integer, default=4, nullable=False)
    min_reservation_hours = Column(Integer, default=1, nullable=False)
    advance_booking_days = Column(Integer, default=14, nullable=False)
    buffer_minutes = Column(Integer, default=15, nullable=False)  # Time between reservations

    # Availability
    available_from = Column(String(5), default="09:00", nullable=False)  # HH:MM format
    available_until = Column(String(5), default="21:00", nullable=False)
    available_days = Column(ARRAY(Integer), default=[0, 1, 2, 3, 4, 5], nullable=False)  # 0=Mon

    # Technical specs (JSON string for flexibility)
    specifications = Column(Text, nullable=True)

    # Build volume for 3D printers (mm)
    build_volume_x = Column(Integer, nullable=True)
    build_volume_y = Column(Integer, nullable=True)
    build_volume_z = Column(Integer, nullable=True)

    # Supported materials/file formats (JSON arrays)
    supported_materials = Column(Text, nullable=True)  # JSON: ["PLA", "ABS", "PETG"]
    supported_file_formats = Column(Text, nullable=True)  # JSON: [".stl", ".obj", ".gcode"]

    # Image and documentation
    image_url = Column(String(500), nullable=True)
    manual_url = Column(String(500), nullable=True)
    safety_guidelines_url = Column(String(500), nullable=True)

    # Usage statistics (updated periodically)
    total_reservations = Column(Integer, default=0, nullable=False)
    total_hours_used = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    total_revenue = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Maintenance tracking
    last_maintenance_date = Column(Date, nullable=True)
    next_maintenance_date = Column(Date, nullable=True)
    maintenance_interval_days = Column(Integer, default=30, nullable=False)

    # Audit
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    certification_type = relationship(
        "MakerspaceCertificationType",
        back_populates="resources",
        foreign_keys=[certification_type_id],
    )
    reservations = relationship(
        "MakerspaceReservation",
        back_populates="resource",
        foreign_keys="MakerspaceReservation.resource_id",
    )
    jobs = relationship(
        "MakerspaceJob", back_populates="resource", foreign_keys="MakerspaceJob.resource_id"
    )
    maintenance_records = relationship(
        "MakerspaceEquipmentMaintenance",
        back_populates="resource",
        foreign_keys="MakerspaceEquipmentMaintenance.resource_id",
    )
    incidents = relationship(
        "SafetyIncident", back_populates="resource", foreign_keys="SafetyIncident.resource_id"
    )
    consumable_usage = relationship(
        "ConsumableUsage", back_populates="resource", foreign_keys="ConsumableUsage.resource_id"
    )
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_makerspace_resources_status_type", "status", "resource_type"),
        Index("ix_makerspace_resources_active", "is_active", "status"),
    )


# =============================================================================
# Certification Types & Patron Certifications
# =============================================================================


class MakerspaceCertificationType(Base):
    __tablename__ = "makerspace_certification_types"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Requirements
    training_duration_hours = Column(Numeric(5, 2), default=Decimal("1.00"), nullable=False)
    requires_safety_quiz = Column(Boolean, default=True, nullable=False)
    passing_score = Column(Integer, default=80, nullable=False)  # Percentage

    # Validity
    validity_months = Column(Integer, default=12, nullable=False)  # 0 = never expires
    renewal_training_hours = Column(Numeric(5, 2), default=Decimal("0.50"), nullable=False)

    # Cost
    certification_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    renewal_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Prerequisites (JSON array of certification_type_ids)
    prerequisites = Column(Text, nullable=True)

    # Resources this certification applies to
    resources = relationship("MakerspaceResource", back_populates="certification_type")

    # Training materials
    training_materials_url = Column(String(500), nullable=True)
    safety_video_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Patron certifications
    patron_certifications = relationship(
        "MakerspaceCertification", back_populates="certification_type"
    )


class MakerspaceCertification(Base, TimestampMixin):
    __tablename__ = "makerspace_certifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    certification_type_id = Column(
        Integer, ForeignKey("makerspace_certification_types.id", ondelete="CASCADE"), nullable=False
    )

    status = Column(
        SQLEnum(
            CertificationStatus,
            name="certificationstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CertificationStatus.pending,
        nullable=False,
    )

    # Training records
    training_completed_at = Column(DateTime(timezone=True), nullable=True)
    quiz_score = Column(Integer, nullable=True)
    quiz_attempts = Column(Integer, default=0, nullable=False)

    # Validity
    certified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Staff who certified
    certified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Suspension/revocation
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    suspended_reason = Column(Text, nullable=True)
    suspended_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Renewal tracking
    renewal_count = Column(Integer, default=0, nullable=False)
    last_renewal_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="makerspace_certifications")
    certification_type = relationship(
        "MakerspaceCertificationType", back_populates="patron_certifications"
    )
    certified_by = relationship("User", foreign_keys=[certified_by_id])
    suspended_by = relationship("User", foreign_keys=[suspended_by_id])

    __table_args__ = (
        Index(
            "ix_unique_active_certification",
            "user_id",
            "certification_type_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'active')"),
        ),
        Index("ix_makerspace_certs_user_status", "user_id", "status"),
    )


# =============================================================================
# Reservations
# =============================================================================


class MakerspaceReservation(Base):
    __tablename__ = "makerspace_reservations"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resource_id = Column(
        Integer, ForeignKey("makerspace_resources.id", ondelete="CASCADE"), nullable=False
    )

    status = Column(
        SQLEnum(
            MakerspaceReservationStatus,
            name="reservationstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MakerspaceReservationStatus.pending,
        nullable=False,
    )

    # Time slot
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    # Actual usage times (for billing)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)

    # Project details
    project_name = Column(String(200), nullable=True)
    project_description = Column(Text, nullable=True)

    # Costs
    estimated_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    actual_cost = Column(Numeric(10, 2), nullable=True)
    consumables_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Payment
    payment_status = Column(
        SQLEnum(
            PaymentStatus,
            name="makerspacepaystatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PaymentStatus.pending,
        nullable=False,
    )
    payment_id = Column(
        Integer, ForeignKey("makerspace_payments.id", ondelete="SET NULL"), nullable=True
    )

    # Staff who approved/processed
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Cancellation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)
    staff_notes = Column(Text, nullable=True)

    # Reminders
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="makerspace_reservations")
    resource = relationship("MakerspaceResource", back_populates="reservations")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    payment = relationship("MakerspacePayment", back_populates="reservation")
    consumable_usage = relationship("ConsumableUsage", back_populates="reservation")

    __table_args__ = (
        # Prevent overlapping reservations for the same resource
        Index("ix_reservation_resource_time", "resource_id", "start_time", "end_time"),
        Index("ix_reservation_user_status", "user_id", "status"),
        Index("ix_reservation_status_time", "status", "start_time"),
    )


# =============================================================================
# Job Queue (3D Printing, etc.)
# =============================================================================


class MakerspaceJob(Base):
    __tablename__ = "makerspace_jobs"

    id = Column(Integer, primary_key=True)

    # Job number for easy reference
    job_number = Column(String(20), unique=True, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resource_id = Column(
        Integer, ForeignKey("makerspace_resources.id", ondelete="SET NULL"), nullable=True
    )

    status = Column(
        SQLEnum(
            JobStatus,
            name="jobstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=JobStatus.submitted,
        nullable=False,
    )
    priority = Column(
        SQLEnum(
            JobPriority,
            name="jobpriority",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=JobPriority.normal,
        nullable=False,
    )

    # Queue position
    queue_position = Column(Integer, nullable=True)

    # Project details
    project_name = Column(String(200), nullable=False)
    project_description = Column(Text, nullable=True)

    # File information
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)  # Server path to uploaded file
    file_size_bytes = Column(Integer, nullable=True)
    file_format = Column(String(20), nullable=True)  # .stl, .gcode, etc.

    # For 3D printing
    material_type = Column(String(50), nullable=True)  # PLA, ABS, PETG
    material_color = Column(String(50), nullable=True)
    infill_percentage = Column(Integer, nullable=True)
    layer_height = Column(Numeric(4, 2), nullable=True)  # mm
    supports_needed = Column(Boolean, default=False, nullable=False)

    # Estimates
    estimated_print_time_minutes = Column(Integer, nullable=True)
    estimated_material_grams = Column(Numeric(10, 2), nullable=True)

    # Actuals
    actual_print_time_minutes = Column(Integer, nullable=True)
    actual_material_grams = Column(Numeric(10, 2), nullable=True)

    # Costs
    estimated_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    actual_cost = Column(Numeric(10, 2), nullable=True)
    material_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    machine_time_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Payment
    payment_status = Column(
        SQLEnum(
            PaymentStatus,
            name="makerspacepaystatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PaymentStatus.pending,
        nullable=False,
    )
    payment_id = Column(
        Integer, ForeignKey("makerspace_payments.id", ondelete="SET NULL"), nullable=True
    )

    # Review process
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Print progress
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)

    # Pickup
    ready_for_pickup_at = Column(DateTime(timezone=True), nullable=True)
    pickup_notified_at = Column(DateTime(timezone=True), nullable=True)
    picked_up_at = Column(DateTime(timezone=True), nullable=True)
    picked_up_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Patron contact for pickup notification
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)

    notes = Column(Text, nullable=True)
    staff_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="makerspace_jobs")
    resource = relationship("MakerspaceResource", back_populates="jobs")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    picked_up_by = relationship("User", foreign_keys=[picked_up_by_id])
    payment = relationship("MakerspacePayment", back_populates="job")
    consumable_usage = relationship("ConsumableUsage", back_populates="job")

    __table_args__ = (
        Index("ix_job_status_queue", "status", "queue_position"),
        Index("ix_job_user_status", "user_id", "status"),
        Index("ix_job_resource_status", "resource_id", "status"),
    )


# =============================================================================
# Payments
# =============================================================================


class MakerspacePayment(Base):
    __tablename__ = "makerspace_payments"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)  # cash, card, account_credit

    status = Column(
        SQLEnum(
            PaymentStatus,
            name="makerspacepaystatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PaymentStatus.pending,
        nullable=False,
    )

    # External payment reference (Stripe, Square, etc.)
    payment_reference = Column(String(100), nullable=True)
    receipt_number = Column(String(50), unique=True, nullable=True)

    # Breakdown
    machine_time_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    consumables_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    setup_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Refunds
    refund_amount = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    refund_reason = Column(Text, nullable=True)

    # Staff processing
    processed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    notes = Column(Text, nullable=True)

    # When the payment was recorded. Required by the revenue report's date
    # filter (reports_service.get_revenue_report); the column was missing, so
    # that report 500'd on MakerspacePayment.created_at.
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="makerspace_payments")
    processed_by = relationship("User", foreign_keys=[processed_by_id])
    reservation = relationship("MakerspaceReservation", back_populates="payment", uselist=False)
    job = relationship("MakerspaceJob", back_populates="payment", uselist=False)


# =============================================================================
# Consumables Inventory
# =============================================================================


class ConsumableItem(Base):
    __tablename__ = "makerspace_consumables"

    id = Column(Integer, primary_key=True)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    sku = Column(String(50), unique=True, nullable=True)

    # Type/category
    category = Column(String(100), nullable=True)  # filament, vinyl, resin

    # For materials like filament
    material_type = Column(String(50), nullable=True)  # PLA, ABS, PETG
    color = Column(String(50), nullable=True)
    diameter_mm = Column(Numeric(4, 2), nullable=True)  # 1.75, 2.85

    # Inventory
    unit = Column(
        SQLEnum(
            ConsumableUnit,
            name="consumableunit",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ConsumableUnit.grams,
        nullable=False,
    )
    quantity_in_stock = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    reorder_threshold = Column(Numeric(12, 2), default=Decimal("100.00"), nullable=False)
    reorder_quantity = Column(Numeric(12, 2), default=Decimal("1000.00"), nullable=False)

    # Costs
    cost_per_unit = Column(Numeric(10, 4), default=Decimal("0.00"), nullable=False)
    price_per_unit = Column(
        Numeric(10, 4), default=Decimal("0.00"), nullable=False
    )  # What we charge patrons

    # Supplier info
    supplier_name = Column(String(200), nullable=True)
    supplier_sku = Column(String(100), nullable=True)
    last_order_date = Column(Date, nullable=True)

    # Compatible resources (JSON array of resource_ids)
    compatible_resources = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    usage_records = relationship("ConsumableUsage", back_populates="consumable")

    __table_args__ = (Index("ix_consumable_category_type", "category", "material_type"),)


class ConsumableUsage(Base):
    __tablename__ = "makerspace_consumable_usage"

    id = Column(Integer, primary_key=True, index=True)

    consumable_id = Column(
        Integer,
        ForeignKey("makerspace_consumables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Either a job or reservation
    job_id = Column(
        Integer, ForeignKey("makerspace_jobs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    reservation_id = Column(
        Integer,
        ForeignKey("makerspace_reservations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    resource_id = Column(
        Integer, ForeignKey("makerspace_resources.id", ondelete="SET NULL"), nullable=True
    )

    quantity_used = Column(Numeric(12, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=False)

    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    consumable = relationship("ConsumableItem", back_populates="usage_records")
    job = relationship("MakerspaceJob", back_populates="consumable_usage")
    reservation = relationship("MakerspaceReservation", back_populates="consumable_usage")
    resource = relationship("MakerspaceResource", back_populates="consumable_usage")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])


# =============================================================================
# Safety Incidents
# =============================================================================


class SafetyIncident(Base):
    __tablename__ = "makerspace_safety_incidents"

    id = Column(Integer, primary_key=True)

    # Incident number for tracking
    incident_number = Column(String(20), unique=True, nullable=False)

    resource_id = Column(
        Integer, ForeignKey("makerspace_resources.id", ondelete="SET NULL"), nullable=True
    )

    # People involved
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    involved_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Incident details
    incident_date = Column(DateTime(timezone=True), nullable=False)
    severity = Column(
        SQLEnum(
            MakerspaceIncidentSeverity,
            name="incidentseverity",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MakerspaceIncidentSeverity.minor,
        nullable=False,
    )

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(200), nullable=True)

    # Injuries/damage
    injuries_reported = Column(Boolean, default=False, nullable=False)
    injury_description = Column(Text, nullable=True)
    equipment_damage = Column(Boolean, default=False, nullable=False)
    damage_description = Column(Text, nullable=True)

    # Response
    immediate_action_taken = Column(Text, nullable=True)
    first_aid_administered = Column(Boolean, default=False, nullable=False)
    emergency_services_called = Column(Boolean, default=False, nullable=False)

    # Investigation
    investigated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    investigation_notes = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)

    # Corrective actions
    corrective_actions = Column(Text, nullable=True)
    corrective_action_deadline = Column(Date, nullable=True)
    corrective_action_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Follow-up
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_notes = Column(Text, nullable=True)

    # Status
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    resource = relationship("MakerspaceResource", back_populates="incidents")
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    involved_user = relationship("User", foreign_keys=[involved_user_id])
    investigated_by = relationship("User", foreign_keys=[investigated_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

    __table_args__ = (Index("ix_incident_date_severity", "incident_date", "severity"),)


# =============================================================================
# Equipment Maintenance
# =============================================================================

# =============================================================================
# Equipment Waitlist
# =============================================================================


class MakerspaceWaitlistStatus(StrEnum):
    waiting = "waiting"
    notified = "notified"
    expired = "expired"
    cancelled = "cancelled"
    fulfilled = "fulfilled"


class MakerspaceWaitlist(Base):
    __tablename__ = "makerspace_waitlist"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(
        Integer, ForeignKey("makerspace_resources.id", ondelete="CASCADE"), nullable=False
    )

    # Desired date/time range
    preferred_date = Column(Date, nullable=False)
    preferred_start_time = Column(String(5), nullable=True)  # HH:MM format, null = any time
    preferred_end_time = Column(String(5), nullable=True)
    flexible_dates = Column(
        Boolean, default=False, nullable=False
    )  # Willing to take alternate dates

    status = Column(
        SQLEnum(
            MakerspaceWaitlistStatus,
            name="waitliststatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MakerspaceWaitlistStatus.waiting,
        nullable=False,
    )

    # Queue position (for priority)
    position = Column(Integer, nullable=True)

    # Notification tracking
    notified_at = Column(DateTime(timezone=True), nullable=True)
    notification_expires_at = Column(DateTime(timezone=True), nullable=True)  # Time to respond

    # Contact preferences
    notify_email = Column(Boolean, default=True, nullable=False)
    notify_sms = Column(Boolean, default=False, nullable=False)
    contact_phone = Column(String(20), nullable=True)

    notes = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="makerspace_waitlist_entries")
    resource = relationship("MakerspaceResource", backref="waitlist_entries")

    __table_args__ = (
        Index("ix_waitlist_resource_date", "resource_id", "preferred_date"),
        Index("ix_waitlist_user_status", "user_id", "status"),
        Index("ix_waitlist_status_position", "status", "position"),
    )


# =============================================================================
# Workshop/Class System
# =============================================================================


class WorkshopStatus(StrEnum):
    draft = "draft"
    published = "published"
    cancelled = "cancelled"
    completed = "completed"


class WorkshopLevel(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    all_levels = "all_levels"


class MakerspaceWorkshop(Base):
    __tablename__ = "makerspace_workshops"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)

    # Workshop type
    is_certification_training = Column(Boolean, default=False, nullable=False)
    certification_type_id = Column(
        Integer, ForeignKey("makerspace_certification_types.id", ondelete="SET NULL"), nullable=True
    )

    # Scheduling
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)

    # Location
    location = Column(String(200), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    is_virtual = Column(Boolean, default=False, nullable=False)
    virtual_meeting_url = Column(String(500), nullable=True)

    # Capacity
    max_participants = Column(Integer, default=10, nullable=False)
    min_participants = Column(Integer, default=1, nullable=False)
    current_participants = Column(Integer, default=0, nullable=False)
    allow_waitlist = Column(Boolean, default=True, nullable=False)
    waitlist_count = Column(Integer, default=0, nullable=False)

    # Instructor
    instructor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    instructor_name = Column(String(200), nullable=True)  # For external instructors
    instructor_bio = Column(Text, nullable=True)

    # Requirements
    skill_level = Column(
        SQLEnum(
            WorkshopLevel,
            name="workshoplevel",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=WorkshopLevel.beginner,
        nullable=False,
    )
    prerequisites = Column(Text, nullable=True)  # JSON array of certification_type_ids
    age_requirement = Column(Integer, default=0, nullable=False)
    required_materials = Column(Text, nullable=True)  # What participants should bring

    # Cost
    fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    materials_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    materials_included = Column(Boolean, default=True, nullable=False)

    # Registration
    registration_opens_at = Column(DateTime(timezone=True), nullable=True)
    registration_closes_at = Column(DateTime(timezone=True), nullable=True)
    registration_required = Column(Boolean, default=True, nullable=False)
    cancellation_deadline_hours = Column(Integer, default=24, nullable=False)

    # Status
    status = Column(
        SQLEnum(
            WorkshopStatus,
            name="workshopstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=WorkshopStatus.draft,
        nullable=False,
    )

    # Resources used in workshop
    resources_used = Column(Text, nullable=True)  # JSON array of resource_ids

    # Content
    image_url = Column(String(500), nullable=True)
    syllabus_url = Column(String(500), nullable=True)
    materials_list_url = Column(String(500), nullable=True)

    # Recurring workshops
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurrence_pattern = Column(String(50), nullable=True)  # weekly, monthly, etc.
    parent_workshop_id = Column(
        Integer, ForeignKey("makerspace_workshops.id", ondelete="SET NULL"), nullable=True
    )

    # Tags for discoverability
    tags = Column(ARRAY(String(50)), nullable=True, default=list)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    certification_type = relationship("MakerspaceCertificationType", backref="workshops")
    instructor = relationship("User", foreign_keys=[instructor_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    registrations = relationship("WorkshopRegistration", back_populates="workshop")
    room = relationship("Room")
    # Self-referential relationship with lazy loading to prevent circular reference GC issues
    parent_workshop = relationship(
        "MakerspaceWorkshop", remote_side=[id], back_populates="child_workshops", lazy="select"
    )
    child_workshops = relationship(
        "MakerspaceWorkshop", back_populates="parent_workshop", lazy="select"
    )

    __table_args__ = (
        Index("ix_workshop_status_date", "status", "start_time"),
        Index("ix_workshop_certification", "certification_type_id"),
    )


class MakerspaceRegistrationStatus(StrEnum):
    registered = "registered"
    waitlisted = "waitlisted"
    confirmed = "confirmed"
    attended = "attended"
    no_show = "no_show"
    cancelled = "cancelled"


class WorkshopRegistration(Base, TimestampMixin):
    __tablename__ = "makerspace_workshop_registrations"

    id = Column(Integer, primary_key=True, index=True)

    workshop_id = Column(
        Integer, ForeignKey("makerspace_workshops.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    status = Column(
        SQLEnum(
            MakerspaceRegistrationStatus,
            name="workshopregistrationstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MakerspaceRegistrationStatus.registered,
        nullable=False,
    )

    # Waitlist position (null if not waitlisted)
    waitlist_position = Column(Integer, nullable=True)

    # Contact info (for notifications)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)

    # Payment (if fee required)
    payment_status = Column(
        SQLEnum(
            PaymentStatus,
            name="makerspacepaystatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PaymentStatus.pending,
        nullable=False,
    )
    payment_id = Column(
        Integer, ForeignKey("makerspace_payments.id", ondelete="SET NULL"), nullable=True
    )
    amount_paid = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Attendance
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Certification awarded (if certification training)
    certification_awarded_id = Column(
        Integer, ForeignKey("makerspace_certifications.id", ondelete="SET NULL"), nullable=True
    )

    # Cancellation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    refund_issued = Column(Boolean, default=False, nullable=False)

    # Notifications
    confirmation_sent_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    workshop = relationship("MakerspaceWorkshop", back_populates="registrations")
    user = relationship("User", foreign_keys=[user_id], backref="workshop_registrations")
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])
    payment = relationship("MakerspacePayment")
    certification_awarded = relationship("MakerspaceCertification")

    __table_args__ = (
        Index(
            "ix_unique_workshop_registration",
            "workshop_id",
            "user_id",
            unique=True,
            postgresql_where=text("status NOT IN ('cancelled')"),
        ),
        Index("ix_registration_workshop_status", "workshop_id", "status"),
        Index("ix_registration_user", "user_id"),
    )


class MakerspaceEquipmentMaintenance(Base):
    __tablename__ = "makerspace_maintenance"

    id = Column(Integer, primary_key=True)

    resource_id = Column(
        Integer, ForeignKey("makerspace_resources.id", ondelete="CASCADE"), nullable=False
    )

    maintenance_type = Column(
        SQLEnum(
            MaintenanceType,
            name="maintenancetype",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MaintenanceType.preventive,
        nullable=False,
    )
    status = Column(
        SQLEnum(
            MaintenanceStatus,
            name="maintenancestatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MaintenanceStatus.scheduled,
        nullable=False,
    )

    # Schedule
    scheduled_date = Column(Date, nullable=False)
    scheduled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Task details
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    checklist = Column(Text, nullable=True)  # JSON array of tasks

    # Execution
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Findings
    findings = Column(Text, nullable=True)
    parts_replaced = Column(Text, nullable=True)  # JSON array

    # Costs
    parts_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    labor_hours = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)

    # Next maintenance
    next_maintenance_date = Column(Date, nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    resource = relationship("MakerspaceResource", back_populates="maintenance_records")
    scheduled_by = relationship("User", foreign_keys=[scheduled_by_id])
    performed_by = relationship("User", foreign_keys=[performed_by_id])

    __table_args__ = (
        Index("ix_maintenance_resource_date", "resource_id", "scheduled_date"),
        Index("ix_maintenance_status_date", "status", "scheduled_date"),
    )
