# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Index, Integer, Numeric,
    String, Text, UniqueConstraint, text
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EquipmentType(StrEnum):
    LAPTOP = "laptop"
    HOTSPOT = "hotspot"
    PROJECTOR = "projector"
    TABLET = "tablet"
    E_READER = "e_reader"
    CAMERA = "camera"
    AUDIO_RECORDER = "audio_recorder"
    CALCULATOR = "calculator"
    CHARGER = "charger"
    HEADPHONES = "headphones"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    WEBCAM = "webcam"
    MICROPHONE = "microphone"
    TRIPOD = "tripod"
    LIGHT_KIT = "light_kit"
    GAMING_CONSOLE = "gaming_console"
    VR_HEADSET = "vr_headset"
    TELESCOPE = "telescope"
    MAKERSPACE = "makerspace"
    LENDING = "lending"
    OTHER = "other"


class EquipmentStatus(StrEnum):
    AVAILABLE = "available"
    CHECKED_OUT = "checked_out"
    RESERVED = "reserved"
    IN_MAINTENANCE = "in_maintenance"
    DAMAGED = "damaged"
    LOST = "lost"
    RETIRED = "retired"


class EquipmentCondition(StrEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    NEEDS_REPAIR = "needs_repair"
    NON_FUNCTIONAL = "non_functional"


class EquipmentMaintenanceType(StrEnum):
    ROUTINE_CHECK = "routine_check"
    CLEANING = "cleaning"
    SOFTWARE_UPDATE = "software_update"
    HARDWARE_REPAIR = "hardware_repair"
    BATTERY_REPLACEMENT = "battery_replacement"
    SCREEN_REPAIR = "screen_repair"
    ACCESSORY_REPLACEMENT = "accessory_replacement"
    CALIBRATION = "calibration"
    DEEP_CLEAN = "deep_clean"
    DIAGNOSTIC = "diagnostic"
    OTHER = "other"


class EquipmentMaintenanceStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AgreementStatus(StrEnum):
    PENDING = "pending"
    SIGNED = "signed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class EquipmentReservationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    READY_FOR_PICKUP = "ready_for_pickup"
    CHECKED_OUT = "checked_out"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    EXPIRED = "expired"


class Equipment(Base):

    __tablename__ = "equipment"
    __table_args__ = (
        UniqueConstraint("serial_number", name="uq_equipment_serial_number"),
        UniqueConstraint("barcode", name="uq_equipment_barcode"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Basic identification
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    equipment_type = Column(
        String(50),
        nullable=False,
        index=True,
    )

    # Unique identifiers
    serial_number = Column(String(100), nullable=True, index=True)
    barcode = Column(String(50), nullable=False, index=True)
    asset_tag = Column(String(50), nullable=True, index=True)

    # Brand/Model info
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    model_year = Column(Integer, nullable=True)

    # Status and condition
    status = Column(
        String(50),
        default=EquipmentStatus.AVAILABLE,
        nullable=False,
    )
    condition = Column(
        String(50),
        default=EquipmentCondition.GOOD,
        nullable=False,
    )

    # Lending rules
    requires_agreement = Column(Boolean, default=True, nullable=False)
    max_checkout_days = Column(Integer, default=7, nullable=False)
    fine_per_day = Column(Numeric(10, 2), default=Decimal("5.00"), nullable=False)
    max_renewals = Column(Integer, default=1, nullable=False)

    # Deposit requirements
    deposit_required = Column(Boolean, default=False, nullable=False)
    deposit_amount = Column(Numeric(10, 2), nullable=True)
    deposit_refundable = Column(Boolean, default=True, nullable=False)

    # Return instructions (patron-facing)
    return_instructions = Column(Text, nullable=True)

    # Financial
    replacement_cost = Column(Numeric(10, 2), nullable=True)
    purchase_price = Column(Numeric(10, 2), nullable=True)
    purchase_date = Column(Date, nullable=True)
    warranty_expires = Column(Date, nullable=True)

    # Maintenance
    maintenance_schedule_days = Column(Integer, default=90, nullable=True)
    last_maintenance_date = Column(Date, nullable=True)
    next_maintenance_date = Column(Date, nullable=True)

    # Location
    location = Column(String(100), nullable=True, index=True)
    home_location = Column(String(100), nullable=True)

    # Accessories and notes
    included_accessories = Column(Text, nullable=True)  # JSON list of accessories
    notes = Column(Text, nullable=True)

    # Images
    image_url = Column(String(500), nullable=True)

    # Tracking
    total_checkouts = Column(Integer, default=0, nullable=False)
    is_high_demand = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)

    # Created by (SET NULL: preserve equipment audit trail if user deleted)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    checkouts = relationship("EquipmentCheckout", back_populates="equipment", cascade="all, delete-orphan")
    maintenance_records = relationship("EquipmentMaintenance", back_populates="equipment", cascade="all, delete-orphan")
    reservations = relationship("EquipmentReservation", back_populates="equipment", cascade="all, delete-orphan")
    condition_logs = relationship("EquipmentConditionLog", back_populates="equipment", cascade="all, delete-orphan")

    @property
    def is_available(self) -> bool:
        return self.status == EquipmentStatus.AVAILABLE

    @property
    def needs_maintenance(self) -> bool:
        if not self.next_maintenance_date:
            return False
        return date.today() >= self.next_maintenance_date


class EquipmentCheckout(Base):

    __tablename__ = "equipment_checkouts"
    __table_args__ = (
        Index(
            "ix_active_equipment_checkout",
            "equipment_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_equipment_checkouts_user_status", "user_id", "status"),
        Index("ix_equipment_checkouts_due_status", "due_date", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Core references
    equipment_id = Column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Status
    status = Column(
        SQLEnum(
            enum.Enum("EquipmentCheckoutStatus", {
                "active": "active",
                "returned": "returned",
                "overdue": "overdue",
                "lost": "lost",
            }),
            name="equipment_checkout_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default="active",
        nullable=False,
    )

    # Dates
    checked_out_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    returned_at = Column(DateTime(timezone=True), nullable=True)

    # Renewals
    renewal_count = Column(Integer, default=0, nullable=False)
    last_renewed_at = Column(DateTime(timezone=True), nullable=True)

    # Condition tracking
    condition_at_checkout = Column(
        String(50),
        nullable=True,
    )
    condition_at_return = Column(
        String(50),
        nullable=True,
    )

    # Staff notes
    checkout_notes = Column(Text, nullable=True)
    return_notes = Column(Text, nullable=True)

    # Staff processing
    checked_out_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    returned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Agreement reference
    agreement_id = Column(
        Integer, ForeignKey("equipment_agreements.id", ondelete="SET NULL"), nullable=True
    )

    # Fine tracking
    fine_amount = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    fine_paid = Column(Boolean, default=False, nullable=False)

    # Deposit tracking
    deposit_amount = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    deposit_collected = Column(Boolean, default=False, nullable=False)
    deposit_collected_at = Column(DateTime(timezone=True), nullable=True)
    deposit_refunded = Column(Boolean, default=False, nullable=False)
    deposit_refunded_at = Column(DateTime(timezone=True), nullable=True)
    deposit_refund_amount = Column(Numeric(10, 2), nullable=True)  # May differ if damage deducted
    deposit_deduction_reason = Column(Text, nullable=True)  # Reason for partial/no refund

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    equipment = relationship("Equipment", back_populates="checkouts")
    user = relationship("User", foreign_keys=[user_id], backref="equipment_checkouts")
    checked_out_by = relationship("User", foreign_keys=[checked_out_by_id])
    returned_to = relationship("User", foreign_keys=[returned_to_id])
    agreement = relationship("EquipmentAgreement")


class EquipmentAgreement(Base):

    __tablename__ = "equipment_agreements"
    __table_args__ = (
        Index("ix_equipment_agreements_user_status", "user_id", "status"),
    )

    id = Column(Integer, primary_key=True)

    # Patron
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Agreement details
    agreement_version = Column(String(20), default="1.0", nullable=False)
    status = Column(
        String(50),
        default=AgreementStatus.PENDING,
        nullable=False,
    )

    # Agreement content
    agreement_text = Column(Text, nullable=False)

    # Signature
    signature = Column(String(255), nullable=True)  # Digital signature or typed name
    signed_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6

    # Validity
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)

    # Equipment type coverage (null = all types)
    equipment_types_covered = Column(String(500), nullable=True)  # Comma-separated types

    # Staff processing (SET NULL: preserve agreement history)
    processed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Revocation (SET NULL: preserve revocation history)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revocation_reason = Column(Text, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="equipment_agreements")
    processed_by = relationship("User", foreign_keys=[processed_by_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_id])

    @property
    def is_valid(self) -> bool:
        if self.status != AgreementStatus.SIGNED:
            return False
        now = datetime.now(timezone.utc)
        if self.valid_until and now > self.valid_until:
            return False
        return True


class EquipmentMaintenance(Base):

    __tablename__ = "equipment_maintenance"
    __table_args__ = (
        Index("ix_equipment_maintenance_equipment_status", "equipment_id", "status"),
    )

    id = Column(Integer, primary_key=True)

    # Equipment reference
    equipment_id = Column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )

    # Maintenance type
    maintenance_type = Column(
        String(50),
        nullable=False,
    )

    # Status
    status = Column(
        String(50),
        default=EquipmentMaintenanceStatus.SCHEDULED,
        nullable=False,
    )

    # Description
    description = Column(Text, nullable=True)
    issues_found = Column(Text, nullable=True)
    work_performed = Column(Text, nullable=True)

    # Scheduling
    scheduled_date = Column(Date, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Condition before/after
    condition_before = Column(
        String(50),
        nullable=True,
    )
    condition_after = Column(
        String(50),
        nullable=True,
    )

    # Cost
    parts_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    labor_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    external_vendor = Column(String(255), nullable=True)
    vendor_invoice = Column(String(100), nullable=True)

    # Performed by (SET NULL: preserve maintenance history)
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Follow-up
    requires_followup = Column(Boolean, default=False, nullable=False)
    followup_notes = Column(Text, nullable=True)
    followup_date = Column(Date, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    equipment = relationship("Equipment", back_populates="maintenance_records")
    performed_by = relationship("User", foreign_keys=[performed_by_id])

    @property
    def total_cost(self) -> Decimal:
        return (self.parts_cost or Decimal("0")) + (self.labor_cost or Decimal("0"))


class EquipmentReservation(Base):

    __tablename__ = "equipment_reservations"
    __table_args__ = (
        Index("ix_equipment_reservations_user_status", "user_id", "status"),
        Index("ix_equipment_reservations_equipment_dates", "equipment_id", "start_date", "end_date"),
        Index(
            "ix_active_equipment_reservation",
            "equipment_id", "user_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'confirmed', 'ready_for_pickup')"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Core references
    equipment_id = Column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Status
    status = Column(
        String(50),
        default=EquipmentReservationStatus.PENDING,
        nullable=False,
    )

    # Reservation period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Queue position (for waitlist)
    position = Column(Integer, default=1, nullable=False)

    # Notifications
    notified_at = Column(DateTime(timezone=True), nullable=True)
    pickup_deadline = Column(DateTime(timezone=True), nullable=True)

    # Purpose (optional, for high-demand items)
    purpose = Column(Text, nullable=True)

    # Staff processing
    confirmed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # Cancellation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    equipment = relationship("Equipment", back_populates="reservations")
    user = relationship("User", foreign_keys=[user_id], backref="equipment_reservations")
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])


class EquipmentConditionLog(Base):

    __tablename__ = "equipment_condition_logs"

    id = Column(Integer, primary_key=True)

    # Equipment reference
    equipment_id = Column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )

    # Condition change
    previous_condition = Column(
        String(50),
        nullable=False,
    )
    new_condition = Column(
        String(50),
        nullable=False,
    )

    # Context (checkout return, maintenance, inspection, etc.)
    change_reason = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    # Related records
    checkout_id = Column(Integer, ForeignKey("equipment_checkouts.id", ondelete="SET NULL"), nullable=True)
    maintenance_id = Column(Integer, ForeignKey("equipment_maintenance.id", ondelete="SET NULL"), nullable=True)

    # Photos
    photo_url = Column(Text, nullable=True)

    # Recorded by (SET NULL: preserve condition log history)
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    equipment = relationship("Equipment", back_populates="condition_logs")
    checkout = relationship("EquipmentCheckout")
    maintenance = relationship("EquipmentMaintenance")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])


class EquipmentAlert(Base):

    __tablename__ = "equipment_alerts"
    __table_args__ = (
        Index("ix_equipment_alerts_status_priority", "status", "priority"),
    )

    id = Column(Integer, primary_key=True)

    # Alert type
    alert_type = Column(
        SQLEnum(
            enum.Enum("EquipmentAlertType", {
                "overdue": "overdue",
                "severely_overdue": "severely_overdue",
                "maintenance_due": "maintenance_due",
                "condition_degraded": "condition_degraded",
                "reservation_ready": "reservation_ready",
                "reservation_expired": "reservation_expired",
                "lost_item": "lost_item",
                "damaged_item": "damaged_item",
            }),
            name="equipment_alert_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Priority (equipment overdue is more urgent than books)
    priority = Column(
        SQLEnum(
            enum.Enum("AlertPriority", {
                "low": "low",
                "medium": "medium",
                "high": "high",
                "urgent": "urgent",
            }),
            name="alert_priority_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default="medium",
        nullable=False,
    )

    # Status
    status = Column(
        SQLEnum(
            enum.Enum("AlertStatus", {
                "active": "active",
                "acknowledged": "acknowledged",
                "resolved": "resolved",
                "dismissed": "dismissed",
            }),
            name="alert_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default="active",
        nullable=False,
    )

    # References
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=True)
    checkout_id = Column(Integer, ForeignKey("equipment_checkouts.id", ondelete="SET NULL"), nullable=True)
    reservation_id = Column(Integer, ForeignKey("equipment_reservations.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Message
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)

    # Escalation
    days_overdue = Column(Integer, nullable=True)
    escalation_level = Column(Integer, default=0, nullable=False)
    last_escalated_at = Column(DateTime(timezone=True), nullable=True)

    # Resolution (SET NULL: preserve alert history)
    acknowledged_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    equipment = relationship("Equipment")
    checkout = relationship("EquipmentCheckout")
    reservation = relationship("EquipmentReservation")
    user = relationship("User", foreign_keys=[user_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


# Default agreement text template
DEFAULT_EQUIPMENT_AGREEMENT = """
EQUIPMENT LENDING AGREEMENT

By signing this agreement, I acknowledge and agree to the following terms:

1. RESPONSIBILITY: I accept full responsibility for the equipment checked out to me.

2. CARE: I agree to handle the equipment with care and return it in the same condition as received.

3. REPLACEMENT COST: I understand that I am responsible for the replacement cost if the equipment is lost, stolen, or damaged beyond normal wear.

4. TIMELY RETURN: I agree to return the equipment by the due date. Late returns may result in fines and/or suspension of borrowing privileges.

5. REPORTING ISSUES: I agree to report any problems or damage to the equipment immediately.

6. PROHIBITED USE: I agree not to use the equipment for any illegal activities or to access inappropriate content.

7. NO MODIFICATIONS: I agree not to modify, alter, or install unauthorized software on the equipment.

8. PRIVACY: I understand that the library may reset devices after return and any data left on the device will be deleted.

I have read and understand this agreement and agree to abide by its terms.
"""

# Laptop-specific lending agreement template
_LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "My Library")

LAPTOP_LENDING_AGREEMENT = f"""
LAPTOP LENDING AGREEMENT
{_LIBRARY_NAME}

By signing this agreement, I acknowledge and agree to the following terms and conditions
for the borrowing of a library laptop computer:

1. RESPONSIBILITY: I accept full responsibility for the laptop checked out to me, including
   the power adapter, carrying case, and any other included accessories.

2. CARE AND HANDLING: I agree to:
   a. Handle the laptop with care and keep it in the provided carrying case during transport.
   b. Keep food and beverages away from the laptop at all times.
   c. Store the laptop in a safe, dry location and not expose it to extreme temperatures.
   d. Not leave the laptop unattended in a vehicle or public place.

3. SOFTWARE RESTRICTIONS: I agree to:
   a. Not install, download, or modify any software on the laptop.
   b. Not change any system settings, passwords, or configurations.
   c. Not attempt to bypass any security settings or content filters.

4. ACCEPTABLE USE: I agree to:
   a. Use the laptop only for lawful purposes.
   b. Not access, download, or distribute inappropriate, illegal, or copyrighted content.
   c. Not use the laptop for any commercial or for-profit purposes.

5. DATA AND PRIVACY: I understand that:
   a. The library will perform a full system reset upon the laptop's return.
   b. Any personal data, files, or accounts saved on the laptop will be permanently deleted.
   c. I am responsible for backing up any personal work before returning the laptop.
   d. The library is not responsible for any data loss.

6. INTERNET USE: I understand that the laptop may provide internet access and I agree to
   comply with the library's Internet Use Policy at all times.

7. REPLACEMENT COST: I understand that I am financially responsible for the full replacement
   cost of the laptop and accessories if lost, stolen, or damaged beyond normal wear and tear.

8. TIMELY RETURN: I agree to return the laptop and all accessories by the due date.
   Late returns will incur fines and may result in suspension of borrowing privileges.

9. DAMAGE REPORTING: I agree to immediately report any damage, malfunction, or loss
   to library staff. I will not attempt to repair the laptop myself.

10. CHECKOUT PERIOD: The standard laptop checkout period is 7 days with a maximum of
    1 renewal, subject to availability. I agree to return the laptop promptly if recalled.

I have read and understand this Laptop Lending Agreement and agree to abide by all terms
and conditions. I understand that failure to comply may result in fines, loss of borrowing
privileges, and/or liability for repair or replacement costs.
"""

# Map of equipment-type-specific agreement templates
EQUIPMENT_AGREEMENT_TEMPLATES: dict[str, str] = {
    EquipmentType.LAPTOP.value: LAPTOP_LENDING_AGREEMENT,
}


def get_agreement_template(equipment_type: "EquipmentType | None" = None) -> str:
    if equipment_type is not None:
        type_value = equipment_type.value if hasattr(equipment_type, "value") else equipment_type
        template = EQUIPMENT_AGREEMENT_TEMPLATES.get(type_value)
        if template:
            return template
    return DEFAULT_EQUIPMENT_AGREEMENT
