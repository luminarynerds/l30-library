# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from enum import Enum, StrEnum
from typing import Optional

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, String, Text, Float, func, Index
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class BuildingStatus(StrEnum):
    OPEN = "open"                    # Building is open and staffed
    CLOSING = "closing"              # Building closing procedures in progress
    CLOSED = "closed"                # Building is closed, after-hours
    EMERGENCY = "emergency"          # Emergency conditions active


class IncidentType(StrEnum):
    INTRUSION = "intrusion"          # Unauthorized entry
    ALARM = "alarm"                  # Alarm system triggered
    FIRE = "fire"                    # Fire detected
    MEDICAL = "medical"              # Medical emergency
    SUSPICIOUS_ACTIVITY = "suspicious"  # Suspicious behavior
    ENVIRONMENTAL = "environmental" # Hazard (flood, gas, etc.)
    EQUIPMENT_FAILURE = "equipment"  # Critical equipment failure
    SECURITY_BREACH = "breach"       # Security system compromise
    OTHER = "other"                  # Unclassified


class IncidentSeverity(StrEnum):
    LOW = "low"                      # Monitor situation
    MEDIUM = "medium"                # Notify on-call manager
    HIGH = "high"                    # Police non-emergency
    CRITICAL = "critical"            # Call 911


class ResponseType(StrEnum):
    INTERNAL_ONLY = "internal"       # Staff/manager only
    SECURITY_COMPANY = "security"    # Security company dispatch
    POLICE_NONEMERGENCY = "police_nonemergency"  # Police (non-emergency)
    POLICE_EMERGENCY = "police_emergency"  # 911 dispatch
    COMBINED = "combined"            # Multiple responders


class ContactType(StrEnum):
    SECURITY_PRIMARY = "security_primary"
    SECURITY_BACKUP = "security_backup"
    MANAGER_ONCALL = "manager_oncall"
    POLICE_NONEMERGENCY = "police_nonemergency"
    POLICE_DISPATCH = "police_dispatch"
    FACILITIES = "facilities"
    EXECUTIVE = "executive"


class FollowUpStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BuildingStatusLog(Base):
    __tablename__ = "building_status_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Status information
    status = Column(
        SQLEnum(BuildingStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        default=BuildingStatus.OPEN
    )

    # Who changed it
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    changed_by = relationship("User", foreign_keys=[changed_by_id])

    # Reason for status change
    reason = Column(Text)

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

    # Index for efficient status lookups
    __table_args__ = (
        Index("ix_building_status_logs_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<BuildingStatusLog(id={self.id}, status={self.status}, "
            f"created_at={self.created_at})>"
        )


class EmergencyIncident(Base):
    __tablename__ = "emergency_incidents"

    id = Column(Integer, primary_key=True, index=True)

    # Incident classification
    incident_type = Column(
        SQLEnum(IncidentType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    severity = Column(
        SQLEnum(IncidentSeverity, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Response protocol
    response_type = Column(
        SQLEnum(ResponseType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Location and context
    location_description = Column(String(255))
    building_status_at_incident = Column(
        SQLEnum(BuildingStatus, values_callable=lambda x: [e.value for e in x]),
        default=BuildingStatus.CLOSED
    )

    # Reporter information
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    reporter_name = Column(String(255))
    reporter_contact = Column(String(255))

    # Incident details
    description = Column(Text, nullable=False)
    additional_details = Column(JSON, default=dict)

    # System integrations
    camera_footage_available = Column(Boolean, default=False)
    camera_footage_urls = Column(JSON, default=list)  # URLs to access footage
    alarm_triggered = Column(Boolean, default=False)
    alarm_panel_id = Column(String(100))

    # Door/lock status
    doors_unlocked_count = Column(Integer, default=0)
    door_status_details = Column(JSON, default=dict)  # {door_id: status}

    # Response status
    response_initiated = Column(Boolean, default=False)
    response_initiated_at = Column(DateTime(timezone=True))

    # Incident resolution
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

    # Timeline tracking
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
    notifications = relationship("EmergencyNotification", back_populates="incident")
    follow_ups = relationship("IncidentFollowUp", back_populates="incident")

    # Index for efficient lookups
    __table_args__ = (
        Index("ix_emergency_incidents_severity_resolved", "severity", "resolved"),
        Index("ix_emergency_incidents_created", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<EmergencyIncident(id={self.id}, type={self.incident_type}, "
            f"severity={self.severity}, resolved={self.resolved})>"
        )


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)

    # Contact type
    contact_type = Column(
        SQLEnum(ContactType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Contact information
    name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(255))
    title = Column(String(100))
    organization = Column(String(255))

    # Linked user if applicable
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    user = relationship("User")

    # Availability
    is_active = Column(Boolean, default=True, index=True)
    available_24h = Column(Boolean, default=False)

    # Escalation info
    escalation_level = Column(
        Integer,
        default=1
    )  # 1=primary, 2=secondary, etc.

    # Additional configuration
    notes = Column(Text)
    external_system_id = Column(String(100))  # ID in external dispatch system

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return (
            f"<EmergencyContact(id={self.id}, type={self.contact_type}, "
            f"name={self.name})>"
        )


class OnCallSchedule(Base):
    __tablename__ = "oncall_schedules"

    id = Column(Integer, primary_key=True, index=True)

    # Manager assignment
    manager_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    manager = relationship("User", foreign_keys=[manager_id])

    # Schedule dates
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Escalation level (lower number = contacted first)
    escalation_level = Column(Integer, default=1, index=True)

    # Contact override (use different contact for this schedule period)
    phone_override = Column(String(20))
    email_override = Column(String(255))

    # Notes for this rotation
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Index for active schedule lookups
    __table_args__ = (
        Index("ix_oncall_schedules_dates", "start_date", "end_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<OnCallSchedule(id={self.id}, manager_id={self.manager_id}, "
            f"start={self.start_date}, end={self.end_date})>"
        )


class EmergencyNotification(Base):
    __tablename__ = "emergency_notifications"

    id = Column(Integer, primary_key=True, index=True)

    # Incident reference
    incident_id = Column(
        Integer, ForeignKey("emergency_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    incident = relationship("EmergencyIncident", back_populates="notifications")

    # Recipient information
    contact_id = Column(
        Integer, ForeignKey("emergency_contacts.id", ondelete="SET NULL")
    )
    contact = relationship("EmergencyContact")

    recipient_name = Column(String(255), nullable=False)
    recipient_phone = Column(String(20))
    recipient_email = Column(String(255))

    # Notification details
    notification_type = Column(String(50))  # sms, call, email
    notification_body = Column(Text)

    # Delivery status
    sent_successfully = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    delivery_error = Column(Text)

    # Response tracking
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True))
    response_notes = Column(Text)

    # Retry tracking
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    # Index for follow-up queries
    __table_args__ = (
        Index("ix_emergency_notifications_incident_sent", "incident_id", "sent_successfully"),
    )

    def __repr__(self) -> str:
        return (
            f"<EmergencyNotification(id={self.id}, incident_id={self.incident_id}, "
            f"recipient={self.recipient_name})>"
        )


class IncidentFollowUp(Base):
    __tablename__ = "incident_followups"

    id = Column(Integer, primary_key=True, index=True)

    # Incident reference
    incident_id = Column(
        Integer, ForeignKey("emergency_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    incident = relationship("EmergencyIncident", back_populates="follow_ups")

    # Task details
    task_description = Column(Text, nullable=False)
    task_category = Column(String(50))  # investigation, repair, notification, review

    # Assignment
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])

    # Status
    status = Column(
        SQLEnum(FollowUpStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=FollowUpStatus.PENDING,
        index=True
    )

    # Timeline
    due_date = Column(DateTime(timezone=True), index=True)
    completed_at = Column(DateTime(timezone=True))

    # Details
    completion_notes = Column(Text)
    priority = Column(Integer, default=1)  # 1=high, 2=medium, 3=low

    # Additional tracking
    estimated_hours = Column(Float)
    actual_hours = Column(Float)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Index for dashboard queries
    __table_args__ = (
        Index("ix_incident_followups_status_due", "status", "due_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<IncidentFollowUp(id={self.id}, incident_id={self.incident_id}, "
            f"status={self.status})>"
        )


class SystemSecurityCheck(Base):
    __tablename__ = "system_security_checks"

    id = Column(Integer, primary_key=True, index=True)

    # Incident reference (optional - can be used for status checks)
    incident_id = Column(
        Integer, ForeignKey("emergency_incidents.id", ondelete="SET NULL")
    )

    # Building system statuses
    all_doors_locked = Column(Boolean, default=True)
    cameras_operational = Column(Boolean, default=True)
    alarm_armed = Column(Boolean, default=True)
    alarm_triggered = Column(Boolean, default=False)

    # Detailed status
    door_status = Column(JSON, default=dict)  # {door_name: {locked: bool, alarm: bool}}
    camera_status = Column(JSON, default=dict)  # {camera_id: {operational: bool, accessible: bool}}
    alarm_status_details = Column(JSON, default=dict)

    # Last verified time
    verified_at = Column(DateTime(timezone=True))
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Remote access
    remote_access_available = Column(Boolean, default=False)
    camera_review_url = Column(String(500))
    access_log_url = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return (
            f"<SystemSecurityCheck(id={self.id}, doors_locked={self.all_doors_locked}, "
            f"cameras_ok={self.cameras_operational})>"
        )
