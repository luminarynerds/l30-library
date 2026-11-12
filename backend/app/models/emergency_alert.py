# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class EmergencyAlertType(StrEnum):
    MEDICAL_EMERGENCY = "medical_emergency"  # General medical emergency
    CARDIAC_EVENT = "cardiac_event"  # Suspected heart attack, arrhythmia
    RESPIRATORY_DISTRESS = "respiratory_distress"  # Choking, asthma, difficulty breathing
    SEVERE_INJURY = "severe_injury"  # Trauma, bleeding, fractures
    ALLERGIC_REACTION = "allergic_reaction"  # Known/suspected allergic reaction
    UNCONSCIOUS_UNRESPONSIVE = "unconscious_unresponsive"  # Loss of consciousness
    ACUTE_MENTAL_HEALTH = "acute_mental_health"  # Severe psychiatric crisis


class EmergencyAlertSeverity(StrEnum):
    LIFE_THREATENING = "life_threatening"  # Unconscious, cardiac, severe respiratory
    URGENT = "urgent"  # Severe injury, respiratory distress, allergic reaction
    SERIOUS = "serious"  # Stable medical emergency


class EmergencyAlertStatus(StrEnum):
    ACTIVE = "active"
    EMERGENCY_SERVICES_CALLED = "emergency_services_called"
    STAFF_RESPONDING = "staff_responding"
    STABILIZED = "stabilized"
    TRANSFERRED = "transferred"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class MedicalEmergencyAlert(Base):
    __tablename__ = "medical_emergency_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Who needs help
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True, index=True  # Nullable for non-patron emergencies (staff, visitor)
    )

    # Where is the emergency
    location = Column(String(200), nullable=False, index=True)  # e.g., "Main Branch - Reading Room 3A"
    branch_id = Column(Integer, nullable=True)

    # Emergency classification
    emergency_type = Column(
        String(50),
        nullable=False, index=True
    )
    severity = Column(
        String(50),
        default=EmergencyAlertSeverity.URGENT, nullable=False
    )
    status = Column(
        String(50),
        default=EmergencyAlertStatus.ACTIVE, nullable=False, index=True
    )

    # Medical context
    # Examples:
    # cardiac_event: {"symptoms": ["chest pain", "shortness of breath"], "conscious": true}
    # respiratory_distress: {"type": "choking", "can_speak": false}
    # severe_injury: {"location": "head", "bleeding": true, "consciousness": "alert"}
    # allergic_reaction: {"known_allergy": "peanuts", "symptoms": ["hives", "swelling"]}
    medical_context = Column(Text, nullable=True)

    # First response information
    caller_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    caller_description = Column(Text, nullable=True)  # Witness account

    # 911 status
    emergency_services_called = Column(Boolean, default=False, index=True)
    emergency_services_called_at = Column(DateTime(timezone=True), nullable=True)
    emergency_services_eta_minutes = Column(Integer, nullable=True)  # ETA provided by 911 dispatch

    # Response tracking
    first_responder_staff_ids = Column(Text, nullable=True)  # JSON array of staff IDs responding
    aed_used = Column(Boolean, default=False)
    aed_location_id = Column(Integer, ForeignKey("aed_locations.id", ondelete="SET NULL"), nullable=True)
    first_aid_kit_location_id = Column(Integer, ForeignKey("first_aid_kit_locations.id", ondelete="SET NULL"), nullable=True)

    # Timestamps, server_default=func.now(), nullable=False, index=True)
    emergency_services_called_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Audit trail
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id])
    caller = relationship("User", foreign_keys=[caller_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
    # DISABLED: # DISABLED: branch relationship
    aed_location = relationship("AEDLocation")
    first_aid_kit_location = relationship("FirstAidKitLocation")


class StaffMedicalTraining(Base):
    __tablename__ = "staff_medical_training"

    id = Column(Integer, primary_key=True, index=True)

    staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True
    )

    # Training certifications
    cpr_certified = Column(Boolean, default=False)
    cpr_expiration_date = Column(DateTime(timezone=True), nullable=True)

    first_aid_certified = Column(Boolean, default=False)
    first_aid_expiration_date = Column(DateTime(timezone=True), nullable=True)

    aed_trained = Column(Boolean, default=False)
    aed_training_date = Column(DateTime(timezone=True), nullable=True)

    # Availability and scope
    available_for_emergency_response = Column(Boolean, default=True)
    medical_response_notes = Column(Text, nullable=True)  # e.g., "Available evenings/weekends only"

    # Timestamps, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    staff = relationship("User", backref="medical_training")


class PatronMedicalInfo(Base):
    __tablename__ = "patron_medical_info"

    id = Column(Integer, primary_key=True, index=True)

    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True
    )

    # Critical medical information
    allergies = Column(Text, nullable=True)  # Comma-separated or JSON
    medical_conditions = Column(Text, nullable=True)  # Diabetes, heart disease, etc.
    medications = Column(Text, nullable=True)  # Current medications
    medical_notes = Column(Text, nullable=True)  # Important medical context

    # Emergency contact escalation
    emergency_contact_1_name = Column(String(100), nullable=True)
    emergency_contact_1_phone = Column(String(20), nullable=True)
    emergency_contact_1_relationship = Column(String(50), nullable=True)

    emergency_contact_2_name = Column(String(100), nullable=True)
    emergency_contact_2_phone = Column(String(20), nullable=True)
    emergency_contact_2_relationship = Column(String(50), nullable=True)

    # Physician information
    primary_physician_name = Column(String(100), nullable=True)
    primary_physician_phone = Column(String(20), nullable=True)
    medical_record_number = Column(String(50), nullable=True)

    # Privacy
    visible_to_staff = Column(Boolean, default=False)  # Patron must opt-in to share with staff, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    patron = relationship("User", backref="medical_info")


class AEDLocation(Base):
    __tablename__ = "aed_locations"

    id = Column(Integer, primary_key=True, index=True)

    branch_id = Column(
        Integer,
        nullable=False, index=True
    )

    location_description = Column(String(200), nullable=False)  # e.g., "Main entrance, left wall"
    room_number = Column(String(50), nullable=True)
    floor = Column(String(50), nullable=True)

    # GPS/coordinates for mapping
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Accessibility information
    access_instructions = Column(Text, nullable=True)  # "Locked glass case, code in staff office"
    visible_signage = Column(Boolean, default=True)
    directional_signage = Column(Boolean, default=True)

    # Maintenance
    last_inspection_date = Column(DateTime(timezone=True), nullable=True)
    battery_installed = Column(DateTime(timezone=True), nullable=True)
    pads_installed = Column(DateTime(timezone=True), nullable=True)
    in_service = Column(Boolean, default=True, index=True)

    # Relationships
    # DISABLED: # DISABLED: branch relationship


class FirstAidKitLocation(Base):
    __tablename__ = "first_aid_kit_locations"

    id = Column(Integer, primary_key=True, index=True)

    branch_id = Column(
        Integer,
        nullable=False, index=True
    )

    location_description = Column(String(200), nullable=False)  # e.g., "Behind front desk"
    room_number = Column(String(50), nullable=True)
    floor = Column(String(50), nullable=True)

    # Access information
    access_instructions = Column(Text, nullable=True)
    visible_signage = Column(Boolean, default=True)
    staff_trained = Column(Boolean, default=False)

    # Kit contents and status
    kit_type = Column(String(50), default="standard")  # standard, comprehensive, portable
    last_checked_date = Column(DateTime(timezone=True), nullable=True)
    in_service = Column(Boolean, default=True, index=True)

    # Relationships
    # DISABLED: # DISABLED: branch relationship
