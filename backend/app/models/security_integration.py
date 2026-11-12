# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class SystemType(StrEnum):
    CAMERA = "camera"
    DOOR_LOCK = "door_lock"
    ALARM = "alarm"
    EMERGENCY_LIGHTING = "emergency_lighting"
    PA_SYSTEM = "pa_system"
    HVAC = "hvac"
    VISITOR_MANAGEMENT = "visitor_management"


class IntegrationStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class SecuritySystem(Base):
    __tablename__ = "security_systems"

    id = Column(Integer, primary_key=True, index=True)

    # System identification
    system_type = Column(
        String(50),
        nullable=False, index=True
    )
    system_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Location
    location = Column(String(200), nullable=True)
    zone = Column(String(100), nullable=True)  # Building, Floor, Section
    area = Column(String(100), nullable=True)

    # Status
    status = Column(
        String(50),
        default=IntegrationStatus.ACTIVE, nullable=False
    )

    # Integration details
    api_endpoint = Column(String(500), nullable=True)
    api_key = Column(String(500), nullable=True)  # Should be encrypted in production
    webhook_url = Column(String(500), nullable=True)

    # Connection settings
    is_connected = Column(Boolean, default=False, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    connection_timeout_seconds = Column(Integer, default=30)

    # Configuration
    config = Column(JSON, nullable=True)  # System-specific configuration, server_default=func.now())

    # Relationships
    system_logs = relationship("SecuritySystemLog", back_populates="security_system", cascade="all, delete-orphan")
    integration_logs = relationship("SecurityIntegrationLog", back_populates="security_system", cascade="all, delete-orphan")


class CameraSystem(Base):
    __tablename__ = "camera_systems"

    id = Column(Integer, primary_key=True, index=True)

    security_system_id = Column(
        Integer, ForeignKey("security_systems.id", ondelete="CASCADE"),
        nullable=False
    )

    # Camera details
    camera_id = Column(String(100), nullable=False, unique=True)
    camera_name = Column(String(200), nullable=False)
    location = Column(String(200), nullable=True)
    angle = Column(String(100), nullable=True)  # Front, side, overhead

    # Feed information
    stream_url = Column(String(500), nullable=True)
    recording_enabled = Column(Boolean, default=False, nullable=False)
    recording_storage = Column(String(200), nullable=True)  # Local, cloud, NAS

    # Recording settings for panic events
    auto_record_on_alert = Column(Boolean, default=True, nullable=False)
    retention_days = Column(Integer, default=30, nullable=False)

    # Relationships
    security_system = relationship("SecuritySystem")
    recordings = relationship("CameraRecording", back_populates="camera_system")


class CameraRecording(Base):
    __tablename__ = "camera_recordings"

    id = Column(Integer, primary_key=True, index=True)

    camera_system_id = Column(
        Integer, ForeignKey("camera_systems.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Recording details
    recording_id = Column(String(100), nullable=False)
    panic_alert_id = Column(Integer, nullable=True, index=True)  # Associated panic alert

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Storage
    file_path = Column(String(500), nullable=True)
    file_size_mb = Column(Float, nullable=True)
    storage_location = Column(String(200), nullable=True)

    # Relationships
    camera_system = relationship("CameraSystem", back_populates="recordings")


class DoorLock(Base):
    __tablename__ = "door_locks"

    id = Column(Integer, primary_key=True, index=True)

    security_system_id = Column(
        Integer, ForeignKey("security_systems.id", ondelete="CASCADE"),
        nullable=False
    )

    # Lock details
    lock_id = Column(String(100), nullable=False, unique=True)
    lock_name = Column(String(200), nullable=False)
    location = Column(String(200), nullable=True)
    door_name = Column(String(200), nullable=True)

    # Lock state
    is_locked = Column(Boolean, default=True, nullable=False)
    is_accessible = Column(Boolean, default=True, nullable=False)
    last_state_change = Column(DateTime(timezone=True), nullable=True)

    # Control settings
    can_control_remotely = Column(Boolean, default=True, nullable=False)
    lock_on_alert = Column(Boolean, default=True, nullable=False)
    unlock_on_alert = Column(Boolean, default=False, nullable=False)

    # Relationships
    security_system = relationship("SecuritySystem")
    lock_events = relationship("DoorLockEvent", back_populates="door_lock")


class DoorLockEvent(Base):
    __tablename__ = "door_lock_events"

    id = Column(Integer, primary_key=True, index=True)

    door_lock_id = Column(
        Integer, ForeignKey("door_locks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Event details
    event_type = Column(String(50), nullable=False)  # locked, unlocked, failed
    action_reason = Column(String(200), nullable=True)  # panic_alert, manual, auto
    panic_alert_id = Column(Integer, nullable=True, index=True)

    triggered_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    succeeded = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    door_lock = relationship("DoorLock", back_populates="lock_events")
    triggered_by = relationship("User")


class AlarmSystemIntegration(Base):
    __tablename__ = "alarm_system_integrations"

    id = Column(Integer, primary_key=True, index=True)

    security_system_id = Column(
        Integer, ForeignKey("security_systems.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )

    # Alarm provider details
    provider_name = Column(String(200), nullable=True)
    account_id = Column(String(200), nullable=True)
    account_number = Column(String(100), nullable=True)

    # Arming settings
    auto_arm_on_alert = Column(Boolean, default=True, nullable=False)
    arm_delay_seconds = Column(Integer, default=60, nullable=False)
    disarm_code = Column(String(50), nullable=True)  # Should be encrypted

    # Zone mapping
    zones = Column(JSON, nullable=True)  # {"zone_id": "zone_name", ...}, server_default=func.now())

    # Relationships
    security_system = relationship("SecuritySystem")


class EmergencyLight(Base):
    __tablename__ = "emergency_lights"

    id = Column(Integer, primary_key=True, index=True)

    security_system_id = Column(
        Integer, ForeignKey("security_systems.id", ondelete="CASCADE"),
        nullable=False
    )

    # Light details
    light_id = Column(String(100), nullable=False, unique=True)
    light_name = Column(String(200), nullable=False)
    location = Column(String(200), nullable=True)
    zone = Column(String(100), nullable=True)

    # State
    is_on = Column(Boolean, default=False, nullable=False)
    brightness_percent = Column(Integer, default=100, nullable=False)

    # Control settings
    activate_on_alert = Column(Boolean, default=True, nullable=False)
    strobe_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    security_system = relationship("SecuritySystem")


class PASystem(Base):
    __tablename__ = "pa_systems"

    id = Column(Integer, primary_key=True, index=True)

    security_system_id = Column(
        Integer, ForeignKey("security_systems.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )

    # System details
    system_id = Column(String(100), nullable=False)
    system_name = Column(String(200), nullable=False)
    zones = Column(JSON, nullable=True)  # List of broadcast zones

    # Announcement templates
    announcement_templates = Column(JSON, nullable=True)  # Pre-recorded announcements

    # Settings
    auto_broadcast_on_alert = Column(Boolean, default=True, nullable=False)
    broadcast_zones = Column(JSON, nullable=True)  # Default zones to broadcast to, server_default=func.now())

    # Relationships
    security_system = relationship("SecuritySystem")


class HVACControl(Base):
    __tablename__ = "hvac_controls"

    id = Column(Integer, primary_key=True, index=True)

    security_system_id = Column(
        Integer, ForeignKey("security_systems.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )

    # System details
    system_id = Column(String(100), nullable=False)
    system_name = Column(String(200), nullable=False)
    zones = Column(JSON, nullable=True)

    # Smoke control
    activate_smoke_extraction_on_alert = Column(Boolean, default=True, nullable=False)
    smoke_detection_threshold = Column(Float, nullable=True)

    # Temperature control
    emergency_temperature_override = Column(Boolean, default=False, nullable=False)
    emergency_temperature_celsius = Column(Float, nullable=True)

    # Damper control
    close_intake_dampers_on_alert = Column(Boolean, default=True, nullable=False)

    # Relationships
    security_system = relationship("SecuritySystem")


class VisitorManagement(Base):
    __tablename__ = "visitor_management_systems"

    id = Column(Integer, primary_key=True, index=True)

    security_system_id = Column(
        Integer, ForeignKey("security_systems.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )

    # System details
    system_id = Column(String(100), nullable=False)
    system_name = Column(String(200), nullable=False)
    api_endpoint = Column(String(500), nullable=True)

    # Lockout settings
    lockout_on_alert = Column(Boolean, default=True, nullable=False)
    lockout_duration_minutes = Column(Integer, default=30, nullable=False)
    quarantine_check_in_on_alert = Column(Boolean, default=True, nullable=False)

    # Relationships
    security_system = relationship("SecuritySystem")


class SecuritySystemLog(Base):
    __tablename__ = "security_system_logs"

    id = Column(Integer, primary_key=True, index=True)

    security_system_id = Column(
        Integer, ForeignKey("security_systems.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Log details
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    security_system = relationship("SecuritySystem", back_populates="system_logs")


class SecurityIntegrationLog(Base):
    __tablename__ = "security_integration_logs"

    id = Column(Integer, primary_key=True, index=True)

    panic_alert_id = Column(
        Integer, ForeignKey("panic_alerts.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    security_system_id = Column(
        Integer, ForeignKey("security_systems.id", ondelete="SET NULL"),
        nullable=True
    )

    # Action details
    action_type = Column(String(100), nullable=False)  # activate_camera, lock_door, arm_alarm, etc.
    status = Column(String(50), default="pending", nullable=False)  # pending, success, failed
    response_data = Column(JSON, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Relationships
    panic_alert = relationship("PanicAlert")
    security_system = relationship("SecuritySystem", back_populates="integration_logs")
