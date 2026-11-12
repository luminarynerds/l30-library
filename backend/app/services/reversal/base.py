# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Dict, List, Optional, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.audit_log import AuditAction, AuditLog
from ...models.user import User

logger = get_logger(__name__)


# =============================================================================
# Unified Result Model
# =============================================================================


@dataclass
class ReversalResult:
    success: bool
    message: str
    audit_log_id: Optional[int] = None
    reverted_changes: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    # Extra fields for domain-specific data (patron recovery, etc.)
    patron_id: Optional[int] = None
    recovered_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "message": self.message,
            "audit_log_id": self.audit_log_id,
            "reverted_changes": self.reverted_changes,
            "warnings": self.warnings,
        }
        if self.patron_id is not None:
            result["patron_id"] = self.patron_id
        if self.recovered_data:
            result["recovered_data"] = self.recovered_data
        return result


@dataclass
class CanRevertResult:
    can_revert: bool
    reason: str
    action_type: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_revert": self.can_revert,
            "reason": self.reason,
            "action_type": self.action_type,
            "details": self.details,
            "warnings": self.warnings,
        }


class ReversalType(StrEnum):

    # Audit reversals
    AUDIT_USER_UPDATE = "audit_user_update"
    AUDIT_LOCK_USER = "audit_lock_user"
    AUDIT_UNLOCK_USER = "audit_unlock_user"
    AUDIT_PRIVACY_CHANGE = "audit_privacy_change"
    AUDIT_PATRON_MERGE = "audit_patron_merge"

    # Circulation reversals
    UNDO_CHECKOUT = "undo_checkout"
    REVERSE_RETURN = "reverse_return"
    REVERT_ITEM_STATUS = "revert_item_status"

    # Enhanced reversals
    UNDO_HOLD = "undo_hold"
    UNDO_RENEWAL = "undo_renewal"
    UNDO_FINE_PAYMENT = "undo_fine_payment"
    UNDO_PATRON_SUSPENSION = "undo_patron_suspension"
    SOFT_DELETE_RECOVERY = "soft_delete_recovery"

    # Fine reversals
    UNDO_FINE_WAIVER = "undo_fine_waiver"
    REVERSE_FINE_PAYMENT = "reverse_fine_payment"

    # Patron recovery
    RESTORE_PATRON = "restore_patron"
    UNBLOCK_PATRON = "unblock_patron"
    UNSUSPEND_PATRON = "unsuspend_patron"


# =============================================================================
# Time Window Constants
# =============================================================================

UNDO_CHECKOUT_WINDOW_MINUTES = 5
UNDO_HOLD_WINDOW_MINUTES = 30
UNDO_RENEWAL_WINDOW_DAYS = 1
UNDO_FINE_PAYMENT_WINDOW_DAYS = 7


# =============================================================================
# Audit Reversal Constants (from audit_reversal_service)
# =============================================================================

NON_REVERSIBLE_ACTIONS = frozenset([
    AuditAction.CREATE_USER,
    AuditAction.DELETE_USER,
    AuditAction.GDPR_DELETION_COMPLETED,
    AuditAction.GDPR_DATA_EXPORTED,
    AuditAction.RESET_PASSWORD,
    AuditAction.CHANGE_ROLE,
    AuditAction.BULK_LOCK,
    AuditAction.BULK_UNLOCK,
    AuditAction.BULK_ACTIVATE,
    AuditAction.BULK_DEACTIVATE,
    AuditAction.BULK_DELETE,
    AuditAction.CHILD_TO_ADULT_TRANSITION,
    AuditAction.ACTIVATE_USER,
    AuditAction.DEACTIVATE_USER,
    AuditAction.REVERT_USER_UPDATE,
    AuditAction.REVERT_LOCK_USER,
    AuditAction.REVERT_UNLOCK_USER,
    AuditAction.REVERT_PRIVACY_CHANGE,
    AuditAction.REVERT_PATRON_MERGE,
    # Informational / read-only actions
    AuditAction.LOGOUT,
    AuditAction.VIEWED,
    # Already-revert or already-recovery actions
    AuditAction.REVERT_FINE_WAIVE,
    AuditAction.FINE_PAYMENT_REVERSED,
    AuditAction.PATRON_RESTORATION,
    AuditAction.PATRON_RESTORE,
    AuditAction.PATRON_SUSPENSION_REVERSED,
    AuditAction.SETTINGS_REVERTED,
    # GDPR / legal - cannot be undone
    AuditAction.GDPR_DELETION_REQUESTED,
    AuditAction.GDPR_DELETION_CANCELLED,
    AuditAction.STAFF_INITIATED_DELETION,
    AuditAction.REDACTION_STARTED,
    # Circulation undo/revert actions - already the result of an undo
    AuditAction.CIRCULATION_UNDO_CHECKOUT,
    AuditAction.CIRCULATION_UNDO_HOLD,
    AuditAction.CIRCULATION_UNDO_RENEWAL,
    AuditAction.CIRCULATION_REVERSE_RETURN,
    AuditAction.CIRCULATION_REVERT_ITEM_STATUS,
    # Fee estimation - no state change to reverse
    AuditAction.FEE_ESTIMATED,
    # Governance formal records - cannot un-create official records
    AuditAction.BOARD_MEMBER_CREATED,
    AuditAction.COMMITTEE_CREATED,
    AuditAction.MEETING_CREATED,
    AuditAction.MOTION_CREATED,
    AuditAction.MOTION_SECONDED,
    AuditAction.MINUTES_APPROVED,
    AuditAction.VOTE_CREATED,
    AuditAction.VOTE_OPENED,
    AuditAction.VOTE_CAST,
    AuditAction.VOTE_CLOSED,
    # Formal records management - cannot un-file official records
    AuditAction.ACTION_ITEM_CREATED,
    AuditAction.REQUEST_RECEIVED,
    AuditAction.REQUEST_ACKNOWLEDGED,
    AuditAction.REQUEST_DENIED,
    AuditAction.RECORDS_RELEASED,
    AuditAction.APPEAL_FILED,
    AuditAction.APPEAL_DECIDED,
    AuditAction.DOCUMENT_PUBLISHED,
    AuditAction.STRATEGIC_GOAL_CREATED,
])

REVERSIBLE_ACTIONS = frozenset([
    AuditAction.UPDATE_USER,
    AuditAction.LOCK_USER,
    AuditAction.UNLOCK_USER,
    AuditAction.PRIVACY_CHANGE_READING_LIST,
    AuditAction.PRIVACY_CHANGE_FAVORITES,
    AuditAction.PRIVACY_CHANGE_GENERIC,
    AuditAction.PATRON_MERGE,
    # Fine operations - can be reversed if fine record exists
    AuditAction.FEE_WAIVED,
    AuditAction.FEE_PAID,
    # Loan extension - can be revoked if loan still active
    AuditAction.EXTENSION_GRANTED,
    # Privacy setting changes - can be reverted to old value
    AuditAction.PRIVACY_SETTING_CHANGED,
    # Content moderation - can be undone if content still exists
    AuditAction.CONTENT_FLAGGED,
    AuditAction.CONTENT_MODERATED,
    AuditAction.CONTENT_REMOVED,
    # Governance updates - can revert to previous state
    AuditAction.MEETING_UPDATED,
    AuditAction.MEETING_CANCELLED,
    # Administrative record updates - can revert status/note changes
    AuditAction.ACTION_ITEM_STATUS_CHANGED,
    AuditAction.NOTE_ADDED,
    AuditAction.STATUS_CHANGED,
])

ACTION_TO_REVERT_ACTION = {
    AuditAction.UPDATE_USER: AuditAction.REVERT_USER_UPDATE,
    AuditAction.LOCK_USER: AuditAction.REVERT_LOCK_USER,
    AuditAction.UNLOCK_USER: AuditAction.REVERT_UNLOCK_USER,
    AuditAction.PRIVACY_CHANGE_READING_LIST: AuditAction.REVERT_PRIVACY_CHANGE,
    AuditAction.PRIVACY_CHANGE_FAVORITES: AuditAction.REVERT_PRIVACY_CHANGE,
    AuditAction.PRIVACY_CHANGE_GENERIC: AuditAction.REVERT_PRIVACY_CHANGE,
    AuditAction.PATRON_MERGE: AuditAction.REVERT_PATRON_MERGE,
    AuditAction.FEE_WAIVED: AuditAction.REVERT_FINE_WAIVE,
    AuditAction.FEE_PAID: AuditAction.REVERT_FINE_WAIVE,
    AuditAction.EXTENSION_GRANTED: AuditAction.SETTINGS_REVERTED,
    AuditAction.PRIVACY_SETTING_CHANGED: AuditAction.REVERT_PRIVACY_CHANGE,
    AuditAction.CONTENT_FLAGGED: AuditAction.SETTINGS_REVERTED,
    AuditAction.CONTENT_MODERATED: AuditAction.SETTINGS_REVERTED,
    AuditAction.CONTENT_REMOVED: AuditAction.SETTINGS_REVERTED,
    AuditAction.MEETING_UPDATED: AuditAction.SETTINGS_REVERTED,
    AuditAction.MEETING_CANCELLED: AuditAction.SETTINGS_REVERTED,
    AuditAction.ACTION_ITEM_STATUS_CHANGED: AuditAction.SETTINGS_REVERTED,
    AuditAction.NOTE_ADDED: AuditAction.SETTINGS_REVERTED,
    AuditAction.STATUS_CHANGED: AuditAction.SETTINGS_REVERTED,
}


# =============================================================================
# Shared Helper Functions
# =============================================================================


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_audit_log(db: AsyncSession, audit_log_id: int) -> Optional[AuditLog]:
    result = await db.execute(
        select(AuditLog).where(AuditLog.id == audit_log_id)
    )
    return result.scalar_one_or_none()
