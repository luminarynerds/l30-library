# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from ..core.database import Base


class SystemStatus(StrEnum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    SLOW = "slow"
    PARTIAL_OUTAGE = "partial_outage"
    MAJOR_OUTAGE = "major_outage"
    MAINTENANCE = "maintenance"


class IssueComponent(StrEnum):
    DATABASE = "database"
    CACHE = "cache"
    SEARCH = "search"
    CIRCULATION = "circulation"
    CATALOG = "catalog"
    AUTHENTICATION = "authentication"
    API = "api"
    FRONTEND = "frontend"
    PAYMENT_GATEWAY = "payment_gateway"
    EMAIL = "email"
    SMS = "sms"
    PRINTING = "printing"
    RFID = "rfid"
    NETWORK = "network"
    SELF_CHECKOUT = "self_checkout"


class StaffNotificationType(StrEnum):
    ISSUE_DETECTED = "issue_detected"
    ISSUE_UPDATED = "issue_updated"
    ISSUE_RESOLVED = "issue_resolved"
    DEGRADATION_WARNING = "degradation_warning"
    OUTAGE_ALERT = "outage_alert"
    RECOVERY_COMPLETE = "recovery_complete"
    MAINTENANCE_SCHEDULED = "maintenance_scheduled"
    MAINTENANCE_STARTING = "maintenance_starting"
    OFFLINE_MODE_ACTIVATED = "offline_mode_activated"
    OFFLINE_MODE_DEACTIVATED = "offline_mode_deactivated"


class PaperBackupType(StrEnum):
    CHECKOUT_FORM = "checkout_form"
    RETURN_FORM = "return_form"
    PATRON_REGISTRATION = "patron_registration"
    HOLD_REQUEST = "hold_request"
    FINE_PAYMENT = "fine_payment"
    ROOM_RESERVATION = "room_reservation"
    EVENT_SIGNUP = "event_signup"
    GENERAL_REFERENCE = "general_reference"


class SystemStatusLog(Base):
    __tablename__ = "system_status_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Status details
    status = Column(SQLEnum(SystemStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    component = Column(SQLEnum(IssueComponent, values_callable=lambda x: [e.value for e in x]), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Human-friendly message for patrons (no jargon, no blame)
    patron_message = Column(Text, nullable=True)
    # Internal technical details for staff
    technical_details = Column(Text, nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    estimated_fix_time = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Communication
    is_public = Column(Boolean, default=True)  # Visible to patrons
    is_scheduled = Column(Boolean, default=False)  # Planned maintenance
    notified_staff = Column(Boolean, default=False)
    notified_patrons = Column(Boolean, default=False)
    staff_notified_at = Column(DateTime, nullable=True)
    patrons_notified_at = Column(DateTime, nullable=True)

    # Recovery alert tracking
    recovery_alert_sent = Column(Boolean, default=False)
    recovery_alert_sent_at = Column(DateTime, nullable=True)

    # Graceful degradation - which features remain available
    available_features = Column(JSON, nullable=True)  # List of features still working
    degraded_features = Column(JSON, nullable=True)  # List of features impacted
    offline_alternatives = Column(JSON, nullable=True)  # Paper/manual alternatives

    # Staff tracking
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Resolution
    resolution_notes = Column(Text, nullable=True)

    # Relationships
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


class SystemHealthMetrics(Base):
    __tablename__ = "system_health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Timing
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Performance metrics
    response_time_p50_ms = Column(Float, nullable=True)
    response_time_p95_ms = Column(Float, nullable=True)
    response_time_p99_ms = Column(Float, nullable=True)

    # Resource usage
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)

    # Database health
    db_connection_pool_used = Column(Integer, nullable=True)
    db_connection_pool_available = Column(Integer, nullable=True)
    db_query_latency_ms = Column(Float, nullable=True)

    # Cache health
    cache_hit_rate_percent = Column(Float, nullable=True)
    cache_latency_ms = Column(Float, nullable=True)

    # Error rates
    error_rate_percent = Column(Float, nullable=True)
    error_count = Column(Integer, default=0)

    # Flags
    is_degraded = Column(Boolean, default=False, index=True)
    is_slow = Column(Boolean, default=False, index=True)
    slow_reason = Column(String(255), nullable=True)


class StaffStatusNotification(Base):
    __tablename__ = "staff_status_notifications"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Link to the issue
    issue_id = Column(Integer, ForeignKey("system_status_logs.id", ondelete="CASCADE"), nullable=True)

    # Notification details
    notification_type = Column(SQLEnum(StaffNotificationType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # What staff should tell patrons (scripted talking points)
    patron_talking_points = Column(Text, nullable=True)
    # What manual workarounds are available
    workaround_instructions = Column(Text, nullable=True)

    # Delivery tracking    sent_at = Column(DateTime, nullable=True)
    channels = Column(JSON, nullable=True)  # ["dashboard", "email", "sms"]

    # Acknowledgment tracking
    acknowledged_by = Column(JSON, nullable=True)  # List of staff user IDs who acknowledged

    # Relationships
    issue = relationship("SystemStatusLog", foreign_keys=[issue_id])


class PaperBackupProcedure(Base):
    __tablename__ = "paper_backup_procedures"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Procedure details
    backup_type = Column(SQLEnum(PaperBackupType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Step-by-step instructions for staff
    instructions = Column(Text, nullable=False)
    # Printable form template (HTML content)
    form_template = Column(Text, nullable=True)

    # When to use this procedure
    trigger_conditions = Column(Text, nullable=True)  # e.g., "When circulation system is down"
    applicable_components = Column(JSON, nullable=True)  # Which components trigger this

    # Status
    is_active = Column(Boolean, default=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Version control
    version = Column(Integer, default=1)
    # Relationships
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


class OfflineModeSession(Base):
    __tablename__ = "offline_mode_sessions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Session info
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    started_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Trigger
    trigger_issue_id = Column(Integer, ForeignKey("system_status_logs.id", ondelete="SET NULL"), nullable=True)
    trigger_reason = Column(String(255), nullable=True)

    # Sync status
    pending_transactions = Column(Integer, default=0)
    synced_transactions = Column(Integer, default=0)
    failed_transactions = Column(Integer, default=0)
    sync_completed_at = Column(DateTime, nullable=True)
    sync_errors = Column(JSON, nullable=True)

    # Relationships
    started_by = relationship("User", foreign_keys=[started_by_id])
    trigger_issue = relationship("SystemStatusLog", foreign_keys=[trigger_issue_id])


class AutoSaveEntry(Base):
    __tablename__ = "auto_save_entries"

    id = Column(Integer, primary_key=True, index=True)

    # Who and what
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    context_type = Column(String(100), nullable=False)  # e.g., "checkout", "catalog_edit", "patron_edit"
    context_id = Column(String(255), nullable=True)  # Related entity ID

    # Saved data
    saved_data = Column(JSON, nullable=False)
    saved_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Recovery
    recovered = Column(Boolean, default=False)
    recovered_at = Column(DateTime, nullable=True)
    expired = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
