# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class AuditAction(StrEnum):
    # User account management
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    REVERT_USER_UPDATE = "revert_user_update"
    LOCK_USER = "lock_user"
    UNLOCK_USER = "unlock_user"
    ACTIVATE_USER = "activate_user"
    DEACTIVATE_USER = "deactivate_user"
    RESET_PASSWORD = "reset_password"
    CHANGE_ROLE = "change_role"
    LOGOUT = "logout"

    # Bulk operations
    BULK_LOCK = "bulk_lock"
    BULK_UNLOCK = "bulk_unlock"
    BULK_ACTIVATE = "bulk_activate"
    BULK_DEACTIVATE = "bulk_deactivate"
    BULK_DELETE = "bulk_delete"

    # Revert operations
    REVERT_LOCK_USER = "revert_lock_user"
    REVERT_UNLOCK_USER = "revert_unlock_user"
    REVERT_FINE_WAIVE = "revert_fine_waive"
    REVERT_PRIVACY_CHANGE = "revert_privacy_change"
    REVERT_PATRON_MERGE = "revert_patron_merge"

    # GDPR-related deletion actions
    GDPR_DELETION_REQUESTED = "gdpr_deletion_requested"
    GDPR_DELETION_CANCELLED = "gdpr_deletion_cancelled"
    GDPR_DELETION_COMPLETED = "gdpr_deletion_completed"
    GDPR_DATA_EXPORTED = "gdpr_data_exported"
    STAFF_INITIATED_DELETION = "staff_initiated_deletion"

    # Age-based automatic transitions
    CHILD_TO_ADULT_TRANSITION = "child_to_adult_transition"

    # Patron account operations
    PATRON_MERGE = "patron_merge"
    PATRON_RESTORATION = "patron_restoration"
    PATRON_RESTORE = "patron_restore"
    PATRON_SUSPENSION_REVERSED = "patron_suspension_reversed"

    # Circulation operations
    CIRCULATION_UNDO_CHECKOUT = "circulation_undo_checkout"
    CIRCULATION_UNDO_HOLD = "circulation_undo_hold"
    CIRCULATION_UNDO_RENEWAL = "circulation_undo_renewal"
    CIRCULATION_REVERSE_RETURN = "circulation_reverse_return"
    CIRCULATION_REVERT_ITEM_STATUS = "circulation_revert_item_status"

    # Fine operations
    FEE_ESTIMATED = "fee_estimated"
    FEE_PAID = "fee_paid"
    FEE_WAIVED = "fee_waived"
    FINE_PAYMENT_REVERSED = "fine_payment_reversed"
    CHECK_BOUNCED = "check_bounced"
    CHECK_CLEARED = "check_cleared"

    # Card operations
    CARD_REPORTED_STOLEN = "card_reported_stolen"
    CARD_REPLACED = "card_replaced"

    # Fraud detection alerts
    WAIVER_FREQUENCY_ALERT = "waiver_frequency_alert"
    CLAIMS_RETURNED_ESCALATION = "claims_returned_escalation"

    # Loan operations
    EXTENSION_GRANTED = "extension_granted"

    # Privacy settings
    PRIVACY_SETTING_CHANGED = "privacy_setting_changed"
    PRIVACY_CHANGE_FAVORITES = "privacy_change_favorites"
    PRIVACY_CHANGE_READING_LIST = "privacy_change_reading_list"
    PRIVACY_CHANGE_GENERIC = "privacy_change_generic"

    # Content management
    CONTENT_FLAGGED = "content_flagged"
    CONTENT_MODERATED = "content_moderated"
    CONTENT_REMOVED = "content_removed"

    # Board and governance
    BOARD_MEMBER_CREATED = "board_member_created"
    COMMITTEE_CREATED = "committee_created"
    MEETING_CREATED = "meeting_created"
    MEETING_UPDATED = "meeting_updated"
    MEETING_CANCELLED = "meeting_cancelled"
    MOTION_CREATED = "motion_created"
    MOTION_SECONDED = "motion_seconded"
    MINUTES_APPROVED = "minutes_approved"
    VOTE_CREATED = "vote_created"
    VOTE_OPENED = "vote_opened"
    VOTE_CAST = "vote_cast"
    VOTE_CLOSED = "vote_closed"

    # Records and requests
    ACTION_ITEM_CREATED = "action_item_created"
    ACTION_ITEM_STATUS_CHANGED = "action_item_status_changed"
    REQUEST_RECEIVED = "request_received"
    REQUEST_ACKNOWLEDGED = "request_acknowledged"
    REQUEST_DENIED = "request_denied"
    RECORDS_RELEASED = "records_released"

    # Appeals and decisions
    APPEAL_FILED = "appeal_filed"
    APPEAL_DECIDED = "appeal_decided"

    # Document and reporting
    DOCUMENT_PUBLISHED = "document_published"
    STRATEGIC_GOAL_CREATED = "strategic_goal_created"

    # Administrative
    STATUS_CHANGED = "status_changed"
    NOTE_ADDED = "note_added"
    VIEWED = "viewed"
    SETTINGS_REVERTED = "settings_reverted"
    REDACTION_STARTED = "redaction_started"

    # Account Security
    TWO_FA_ENABLED = "two_fa_enabled"
    TWO_FA_DISABLED = "two_fa_disabled"
    TWO_FA_VERIFY_SUCCESS = "two_fa_verify_success"
    TWO_FA_VERIFY_FAILED = "two_fa_verify_failed"
    RECOVERY_CODE_USED = "recovery_code_used"
    RECOVERY_CODES_REGENERATED = "recovery_codes_regenerated"
    RECOVERY_EMAIL_ADDED = "recovery_email_added"
    RECOVERY_EMAIL_VERIFIED = "recovery_email_verified"
    RECOVERY_EMAIL_REMOVED = "recovery_email_removed"
    SECURITY_ALERT_SENT = "security_alert_sent"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_LOCKED = "login_locked"
    PASSWORD_CHANGED = "password_changed"
    SESSION_REVOKED = "session_revoked"
    ALL_SESSIONS_REVOKED = "all_sessions_revoked"
    NEW_DEVICE_DETECTED = "new_device_detected"

    # Impact measurement (Phase 1: governance — outcome indicators + claims)
    OUTCOME_INDICATOR_CREATED = "outcome_indicator_created"
    OUTCOME_INDICATOR_APPROVED = "outcome_indicator_approved"
    OUTCOME_INDICATOR_RETIRED = "outcome_indicator_retired"
    CLAIM_CREATED = "claim_created"
    CLAIM_REVIEWED = "claim_reviewed"
    CLAIM_PROMOTED = "claim_promoted"
    CLAIM_RETIRED = "claim_retired"

    # Integration probes
    INTEGRATION_PROBE = "integration_probe"



class AuditLog(Base):
    __tablename__ = "audit_logs"

    # Table arguments for composite indexes
    __table_args__ = (
        # Composite index for staff activity queries
        Index('ix_audit_logs_admin_created', 'admin_id', 'created_at'),
        # Composite index for user history queries
        Index('ix_audit_logs_target_created', 'target_user_id', 'created_at'),
        # Composite index for action type filtering with time
        Index('ix_audit_logs_action_created', 'action', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Who performed the action (admin/staff user)
    # SET NULL on delete to preserve audit trail even if admin account is deleted
    admin_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID of the admin/staff user who performed the action"
    )

    # Who was affected by the action (target user)
    # Can be null for system actions or bulk operations
    # SET NULL on delete to preserve audit trail
    target_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID of the user who was affected by the action"
    )

    # What action was performed
    action = Column(
        SQLEnum(AuditAction, name="auditaction", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        comment="Type of action performed"
    )

    # Additional context about the action
    # Flexible JSON structure for storing action-specific data
    details = Column(
        JSON,
        nullable=True,
        comment="JSON object containing old/new values, resource info, and other context"
    )

    # IP address of the admin who performed the action
    # Supports both IPv4 (15 chars) and IPv6 (45 chars)
    ip_address = Column(
        String(45),
        nullable=True,
        comment="IP address from which the action was performed"
    )

    # User agent string for additional context
    user_agent = Column(
        String(500),
        nullable=True,
        comment="Browser/client user agent string"
    )

    # Timestamp - when the action occurred
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Timestamp when the action was performed"
    )

    # Relationships
    admin = relationship(
        "User",
        foreign_keys=[admin_id],
        backref="admin_audit_logs",
        doc="The admin/staff user who performed the action"
    )
    target_user = relationship(
        "User",
        foreign_keys=[target_user_id],
        backref="user_audit_logs",
        doc="The user who was affected by the action"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, "
            f"action={self.action.value if self.action else None}, "
            f"admin_id={self.admin_id}, "
            f"target_user_id={self.target_user_id}, "
            f"created_at={self.created_at})>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "admin_email": self.admin.email if self.admin else None,
            "target_user_id": self.target_user_id,
            "target_user_email": self.target_user.email if self.target_user else None,
            "action": self.action.value if self.action else None,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
