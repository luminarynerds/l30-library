# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class PanicAlertStatus(StrEnum):

    ACTIVE = "active"  # Alert sent, awaiting response
    ACKNOWLEDGED = "acknowledged"  # Staff member acknowledged
    RESOLVED = "resolved"  # Situation resolved
    CANCELLED = "cancelled"  # False alarm


class PanicAlertSource(StrEnum):

    KEYBOARD_SHORTCUT = "keyboard_shortcut"  # Ctrl+Shift+H
    PHYSICAL_BUTTON = "physical_button"  # Desk panic button
    MOBILE_GESTURE = "mobile_gesture"  # Shake gesture (future)
    HIDDEN_UI_BUTTON = "hidden_ui_button"  # Discreet UI element


class PanicAlert(Base, TimestampMixin):

    __tablename__ = "panic_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Who triggered the alert
    triggered_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Where was the staff member when they triggered it
    branch_id = Column(
        Integer, nullable=True, index=True
    )

    # How was the alert triggered
    activation_source = Column(
        SQLEnum(PanicAlertSource, name="panicalertsource", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PanicAlertSource.KEYBOARD_SHORTCUT,
        index=True,
    )

    # Current status
    status = Column(
        SQLEnum(PanicAlertStatus, name="panicalertstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PanicAlertStatus.ACTIVE,
        index=True,
    )

    # Optional context about the situation (encrypted in practice)
    situation_notes = Column(Text, nullable=True)

    # Who acknowledged/responded to the alert
    acknowledged_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Resolution notes
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata (device info, GPS coordinates if available, etc.)
    alert_metadata = Column(JSON, nullable=True)

    # Escalation tracking
    escalation_level = Column(Integer, default=0, nullable=False, index=True)
    escalated_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps provided by TimestampMixin (created_at, updated_at)

    # Relationships
    triggered_by = relationship("User", foreign_keys=[triggered_by_user_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_user_id])
    # DISABLED: # DISABLED: branch relationship


class PanicAlertNotificationPreferences(Base):

    __tablename__ = "panic_alert_notification_preferences"

    id = Column(Integer, primary_key=True, index=True)

    # Which users should receive panic alerts (e.g., managers, security)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Should they receive notifications
    receive_panic_alerts = Column(Boolean, default=False, nullable=False)

    # How to notify (email, SMS, in-app, etc.)
    notify_via_email = Column(Boolean, default=False, nullable=False)
    notify_via_sms = Column(Boolean, default=False, nullable=False)
    notify_via_in_app = Column(Boolean, default=True, nullable=False)

    # Only notify for specific branches
    notify_for_all_branches = Column(Boolean, default=True, nullable=False)
    branch_ids = Column(JSON, nullable=True)  # List of branch IDs

    # Sound/vibration on alert notification
    sound_enabled = Column(Boolean, default=False, nullable=False)
    # Which alarm tone preset to play when sound_enabled is true.
    # Validated against AlertSoundPreset values in the frontend; stored as
    # plain string here to allow adding new presets without migrations.
    sound_preference = Column(String(32), default="gentle_chime", nullable=False)
    vibration_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User")


class PanicAlertHistory(Base, TimestampMixin):

    __tablename__ = "panic_alert_history"

    id = Column(Integer, primary_key=True, index=True)

    # Which alert this history entry belongs to
    panic_alert_id = Column(
        Integer, ForeignKey("panic_alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # What action was taken
    action = Column(String(50), nullable=False, index=True)  # e.g., "triggered", "acknowledged", "escalated", "resolved"

    # Who performed the action (null for system actions)
    performed_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Old and new status (for status transitions)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)

    # Additional context about the action
    notes = Column(Text, nullable=True)
    action_metadata = Column(JSON, nullable=True)

    # Timestamps provided by TimestampMixin (created_at, updated_at)

    # Relationships
    panic_alert = relationship("PanicAlert", backref="history_entries")
    performed_by = relationship("User", foreign_keys=[performed_by_user_id])
