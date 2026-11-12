# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import Enum, StrEnum
from typing import Optional

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint, func
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class ThreatLevel(StrEnum):
    SHELTER_IN_PLACE = "shelter_in_place"  # Immediate threat nearby, lockdown
    EVACUATION = "evacuation"               # Must leave building
    ALL_CLEAR = "all_clear"                 # Threat resolved


class ThreatType(StrEnum):
    ACTIVE_SHOOTER = "active_shooter"
    ARMED_INTRUDER = "armed_intruder"
    BOMB_THREAT = "bomb_threat"
    CHEMICAL_BIOLOGICAL = "chemical_biological"
    STRUCTURAL_EMERGENCY = "structural_emergency"
    OTHER = "other"


class ThreatAlert(Base):
    __tablename__ = "threat_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Alert metadata
    threat_type = Column(
        SQLEnum(ThreatType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        default=ThreatType.OTHER
    )
    threat_level = Column(
        SQLEnum(ThreatLevel, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        default=ThreatLevel.SHELTER_IN_PLACE
    )

    # Location information
    branch_id = Column(Integer, index=True)
    location_description = Column(String(255))
    specific_area = Column(String(255))  # e.g., "Front entrance", "South wing"
    latitude = Column(Float)
    longitude = Column(Float)

    # Threat details
    description = Column(Text)
    external_information = Column(Text)  # Information from law enforcement/911
    threat_location_address = Column(String(500))

    # 911 Dispatch
    dispatch_called = Column(Boolean, default=False, index=True)
    dispatch_time = Column(DateTime(timezone=True))
    dispatch_call_id = Column(String(100))  # Reference to 911 call
    dispatch_notes = Column(Text)

    # Response status
    lockdown_initiated = Column(Boolean, default=False, index=True)
    lockdown_time = Column(DateTime(timezone=True))
    evacuation_initiated = Column(Boolean, default=False, index=True)
    evacuation_time = Column(DateTime(timezone=True))

    # Staff accountability
    total_staff_expected = Column(Integer, default=0)
    staff_checked_in = Column(Integer, default=0)
    staff_checked_in_safe = Column(Integer, default=0)
    staff_unaccounted = Column(Integer, default=0)

    # Patron accountability
    total_patrons_expected = Column(Integer, default=0)
    patrons_accounted = Column(Integer, default=0)

    # Children programs
    children_present = Column(Boolean, default=False)
    children_count = Column(Integer, default=0)
    parent_notification_sent = Column(Boolean, default=False)
    parent_notification_time = Column(DateTime(timezone=True))

    # Media response
    media_responders_notified = Column(Boolean, default=False)
    media_notification_time = Column(DateTime(timezone=True))
    media_statement = Column(Text)
    information_hotline = Column(String(20))  # Phone number

    # All-clear
    all_clear_issued = Column(Boolean, default=False, index=True)
    all_clear_time = Column(DateTime(timezone=True))
    all_clear_initiated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Created by
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_by = relationship("User", foreign_keys=[created_by_id])

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    staff_checkins = relationship("StaffCheckIn", back_populates="threat_alert", cascade="all, delete-orphan")
    evacuations = relationship("EvacuationEvent", back_populates="threat_alert", cascade="all, delete-orphan")
    reunifications = relationship("ReunificationEvent", back_populates="threat_alert", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<ThreatAlert(id={self.id}, type={self.threat_type}, "
            f"level={self.threat_level}, created_at={self.created_at})>"
        )


class StaffCheckIn(Base):
    __tablename__ = "staff_checkins"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    threat_alert_id = Column(
        Integer,
        ForeignKey("threat_alerts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    threat_alert = relationship("ThreatAlert", back_populates="staff_checkins")

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    user = relationship("User", foreign_keys=[user_id])

    # Status
    is_safe = Column(Boolean, nullable=False, default=False, index=True)
    location = Column(String(255))  # Where staff member is sheltering
    notes = Column(Text)

    # Timestamps
    checked_in_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<StaffCheckIn(id={self.id}, user_id={self.user_id}, "
            f"is_safe={self.is_safe}, checked_in_at={self.checked_in_at})>"
        )


class EvacuationRoute(Base):
    __tablename__ = "evacuation_routes"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    branch_id = Column(Integer, index=True)

    # Route details
    route_name = Column(String(100), nullable=False)  # e.g., "Main Exit Route"
    description = Column(Text)
    starting_point = Column(String(255), nullable=False)  # e.g., "Front entrance area"
    exit_point = Column(String(255), nullable=False)  # e.g., "South parking lot"
    rally_point_id = Column(Integer, ForeignKey("rally_points.id", ondelete="SET NULL"))
    rally_point = relationship("RallyPoint", back_populates="evacuation_routes")

    # Route mapping
    waypoints = Column(JSON, default=list)  # List of checkpoints/turns
    estimated_duration_seconds = Column(Integer)  # Time to evacuate
    capacity = Column(Integer)  # Max people per route

    # Status
    is_active = Column(Boolean, default=True, index=True)
    last_tested = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<EvacuationRoute(id={self.id}, name={self.route_name})>"


class RallyPoint(Base):
    __tablename__ = "rally_points"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    branch_id = Column(Integer, index=True)

    # Location
    name = Column(String(100), nullable=False)  # e.g., "North Parking Lot"
    description = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500))

    # Capacity
    max_capacity = Column(Integer)  # Expected max occupants
    covered = Column(Boolean, default=False)  # Weather protection

    # Details
    assembly_instructions = Column(Text)  # What to do at rally point
    is_primary = Column(Boolean, default=False)  # Primary assembly point
    is_active = Column(Boolean, default=True, index=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    evacuation_routes = relationship("EvacuationRoute", back_populates="rally_point")

    def __repr__(self) -> str:
        return f"<RallyPoint(id={self.id}, name={self.name}, primary={self.is_primary})>"


class EvacuationEvent(Base):
    __tablename__ = "evacuation_events"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    threat_alert_id = Column(
        Integer,
        ForeignKey("threat_alerts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    threat_alert = relationship("ThreatAlert", back_populates="evacuations")

    evacuation_route_id = Column(Integer, ForeignKey("evacuation_routes.id", ondelete="SET NULL"))
    rally_point_id = Column(Integer, ForeignKey("rally_points.id", ondelete="SET NULL"))

    # Status
    people_evacuated = Column(Integer, default=0)
    people_sheltering = Column(Integer, default=0)

    # Timestamps
    evacuation_initiated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_confirmed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<EvacuationEvent(id={self.id}, threat_alert_id={self.threat_alert_id}, "
            f"evacuated={self.people_evacuated})>"
        )


class ReunificationEvent(Base):
    __tablename__ = "reunification_events"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    threat_alert_id = Column(
        Integer,
        ForeignKey("threat_alerts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    threat_alert = relationship("ThreatAlert", back_populates="reunifications")

    # Child information
    child_patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    child_patron = relationship("User", foreign_keys=[child_patron_id])

    # Parent/Guardian
    parent_patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    parent_patron = relationship("User", foreign_keys=[parent_patron_id])
    parent_contact_name = Column(String(255))
    parent_contact_phone = Column(String(20))

    # Status
    child_accounted = Column(Boolean, default=False)
    child_safe_location = Column(String(255))
    child_reunified = Column(Boolean, default=False, index=True)
    reunification_time = Column(DateTime(timezone=True))
    reunified_with = Column(String(255))  # Name of person who picked up

    # Verification
    id_verified = Column(Boolean, default=False)
    authorization_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return (
            f"<ReunificationEvent(id={self.id}, child_id={self.child_patron_id}, "
            f"reunified={self.child_reunified})>"
        )


class MediaResponseProtocol(Base):
    __tablename__ = "media_response_protocols"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    branch_id = Column(Integer, index=True)

    # Protocol info
    name = Column(String(100), nullable=False)  # e.g., "Active Threat Response"
    description = Column(Text)

    # Statements
    initial_statement = Column(Text, nullable=False)  # Immediate response
    holding_statement = Column(Text, nullable=False)  # While incident ongoing
    resolution_statement = Column(Text, nullable=False)  # After all-clear
    condolence_statement = Column(Text)  # If casualties (optional)

    # Contacts
    authorized_spokespersons = Column(JSON, default=list)  # [{name, title, phone, email}]
    media_contact_number = Column(String(20))
    information_hotline = Column(String(20))

    # Coordination
    coordinate_with_agencies = Column(JSON, default=list)  # Police, fire, school district, etc.

    # Status
    is_active = Column(Boolean, default=True, index=True)
    last_reviewed = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<MediaResponseProtocol(id={self.id}, name={self.name})>"


class AllClearAnnouncement(Base):
    __tablename__ = "allclear_announcements"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    threat_alert_id = Column(
        Integer,
        ForeignKey("threat_alerts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    threat_alert = relationship("ThreatAlert")

    # Details
    announcement_text = Column(Text, nullable=False)
    announced_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Delivery methods
    announced_via_intercom = Column(Boolean, default=False)
    announced_via_email = Column(Boolean, default=False)
    announced_via_sms = Column(Boolean, default=False)
    announced_via_app = Column(Boolean, default=False)

    # Confirmation
    staff_confirmed = Column(Integer, default=0)  # Number of staff acknowledging
    patrons_notified_count = Column(Integer, default=0)

    # Timestamps
    announced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<AllClearAnnouncement(id={self.id}, threat_alert_id={self.threat_alert_id}, "
            f"announced_at={self.announced_at})>"
        )


class ThreatResponsePlan(Base):
    __tablename__ = "threat_response_plans"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    branch_id = Column(Integer, index=True, unique=True)

    # Contact information
    emergency_contact_name = Column(String(255), nullable=False)
    emergency_contact_phone = Column(String(20), nullable=False)
    emergency_contact_email = Column(String(255))

    # Law enforcement liaison
    law_enforcement_liaison_name = Column(String(255))
    law_enforcement_liaison_phone = Column(String(20))
    law_enforcement_dispatch_center = Column(String(255))
    law_enforcement_dispatch_phone = Column(String(20))

    # Additional agencies
    fire_department_contact = Column(String(255))
    fire_department_phone = Column(String(20))
    school_district_contact = Column(String(255))  # If near schools
    school_district_phone = Column(String(20))

    # Facility details
    total_occupancy_capacity = Column(Integer)
    main_entrance_address = Column(String(500), nullable=False)
    alternative_entrance_address = Column(String(500))

    # Security
    security_personnel_assigned = Column(Integer, default=0)
    access_control_enabled = Column(Boolean, default=True)
    cctv_enabled = Column(Boolean, default=True)

    # Training
    last_drill_date = Column(DateTime(timezone=True))
    next_scheduled_drill = Column(DateTime(timezone=True))
    staff_trained_count = Column(Integer, default=0)

    # Configuration
    is_active = Column(Boolean, default=True, index=True)
    last_reviewed = Column(DateTime(timezone=True))
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ThreatResponsePlan(branch_id={self.branch_id})>"
