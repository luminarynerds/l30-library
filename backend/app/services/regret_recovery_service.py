# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Dict, List, Optional

logger = get_logger(__name__)


class RecoveryDifficulty(StrEnum):
    SELF_SERVICE = "self_service"        # User can undo it themselves
    STAFF_HELP = "staff_help"            # Needs a staff member
    ADMIN_HELP = "admin_help"            # Needs an admin
    IT_HELP = "it_help"                  # Needs IT/database access
    IMPOSSIBLE = "impossible"            # Truly gone forever


class ActionSeverity(StrEnum):
    LOW = "low"              # Removing a favorite, unfollowing
    MEDIUM = "medium"        # Deleting a list, canceling a reservation
    HIGH = "high"            # Deleting a catalog item, removing a patron
    CRITICAL = "critical"    # GDPR deletion, bulk operations, account deletion


@dataclass
class RecoveryWindow:
    timeframe: str                            # Human-readable: "5 minutes", "1 hour", etc.
    seconds: int                              # Machine-readable duration in seconds
    difficulty: RecoveryDifficulty
    method: str                               # How to recover
    available: bool = True                    # Whether this recovery path exists


@dataclass
class RegretRecoveryTimeline:
    action_key: str                           # e.g. "delete_catalog_item"
    action_label: str                         # e.g. "Delete catalog item"
    severity: ActionSeverity
    requires_confirmation: bool               # Should we show a confirmation dialog?
    requires_typed_confirmation: bool         # Must they type "DELETE" or similar?
    soft_delete: bool                         # Is the data soft-deleted (recoverable)?
    windows: List[RecoveryWindow] = field(default_factory=list)
    what_is_lost: str = ""                    # Human-readable description of what's gone
    what_is_kept: str = ""                    # What's preserved (audit trail, etc.)
    reassurance: str = ""                     # Empathetic message for the user

    def to_dict(self) -> dict:
        return {
            "action_key": self.action_key,
            "action_label": self.action_label,
            "severity": str(self.severity),
            "requires_confirmation": self.requires_confirmation,
            "requires_typed_confirmation": self.requires_typed_confirmation,
            "soft_delete": self.soft_delete,
            "windows": [
                {
                    "timeframe": w.timeframe,
                    "seconds": w.seconds,
                    "difficulty": str(w.difficulty),
                    "method": w.method,
                    "available": w.available,
                }
                for w in self.windows
            ],
            "what_is_lost": self.what_is_lost,
            "what_is_kept": self.what_is_kept,
            "reassurance": self.reassurance,
        }


# =============================================================================
# The Registry: Every destructive action mapped to its recovery timeline
# =============================================================================

_RECOVERY_REGISTRY: Dict[str, RegretRecoveryTimeline] = {}


def _register(timeline: RegretRecoveryTimeline) -> None:
    _RECOVERY_REGISTRY[timeline.action_key] = timeline


# ---------------------------------------------------------------------------
# PATRON / USER operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="deactivate_user",
    action_label="Deactivate patron account",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=True,
    what_is_lost="Patron loses login access immediately.",
    what_is_kept="All patron data, checkout history, and account details are preserved.",
    reassurance="This is reversible. The account can be reactivated at any time.",
    windows=[
        RecoveryWindow("5 minutes", 300, RecoveryDifficulty.SELF_SERVICE,
                        "Use the Undo button or visit Admin > Users to reactivate."),
        RecoveryWindow("1 hour", 3600, RecoveryDifficulty.STAFF_HELP,
                        "Any staff member can reactivate through Admin > Users."),
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.STAFF_HELP,
                        "Any staff member can reactivate through Admin > Users."),
        RecoveryWindow("1 week", 604800, RecoveryDifficulty.ADMIN_HELP,
                        "An admin can reactivate. Account data is fully intact."),
        RecoveryWindow("Beyond 1 week", 0, RecoveryDifficulty.ADMIN_HELP,
                        "Account can still be reactivated indefinitely. Data is never purged unless GDPR deletion is requested."),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="lock_user",
    action_label="Lock patron account",
    severity=ActionSeverity.MEDIUM,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=True,
    what_is_lost="Patron cannot log in while locked.",
    what_is_kept="All data is preserved. This is a status change, not a deletion.",
    reassurance="Locking is fully reversible. Unlock at any time.",
    windows=[
        RecoveryWindow("5 minutes", 300, RecoveryDifficulty.SELF_SERVICE,
                        "Use Undo or navigate to Admin > Users > Unlock."),
        RecoveryWindow("1 hour", 3600, RecoveryDifficulty.STAFF_HELP,
                        "Any staff member can unlock the account."),
        RecoveryWindow("Any time", 0, RecoveryDifficulty.STAFF_HELP,
                        "Account can be unlocked at any time by staff."),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="suspend_patron",
    action_label="Suspend patron",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=True,
    what_is_lost="Patron loses borrowing privileges during suspension.",
    what_is_kept="Account, history, and all data remain intact.",
    reassurance="Suspensions can be reversed at any time through the undo system.",
    windows=[
        RecoveryWindow("5 minutes", 300, RecoveryDifficulty.SELF_SERVICE,
                        "Use the Undo button to reverse immediately."),
        RecoveryWindow("1 hour", 3600, RecoveryDifficulty.STAFF_HELP,
                        "Staff can reverse the suspension in Admin > Patrons."),
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.ADMIN_HELP,
                        "An admin can reverse the suspension and restore privileges."),
        RecoveryWindow("Any time", 0, RecoveryDifficulty.ADMIN_HELP,
                        "Suspensions are reversible at any time."),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_account_gdpr",
    action_label="Permanently delete account (GDPR)",
    severity=ActionSeverity.CRITICAL,
    requires_confirmation=True,
    requires_typed_confirmation=True,
    soft_delete=False,
    what_is_lost="All personal data is permanently erased or anonymized. This cannot be undone.",
    what_is_kept="Anonymized checkout and financial records are retained for legal compliance.",
    reassurance="This is permanent and required by law when requested. A 72-hour cooling-off period applies for scheduled deletions.",
    windows=[
        RecoveryWindow("72 hours (scheduled)", 259200, RecoveryDifficulty.SELF_SERVICE,
                        "If using scheduled deletion, cancel before the grace period ends."),
        RecoveryWindow("After execution", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Once executed, personal data is permanently gone. This is by design (GDPR Article 17).",
                        available=False),
    ],
))

# ---------------------------------------------------------------------------
# CATALOG operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="delete_catalog_item",
    action_label="Delete catalog item",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The catalog record and its metadata are removed from the database.",
    what_is_kept="Checkout history referencing this item is preserved. Audit logs record the deletion.",
    reassurance="Consider withdrawing the item instead of deleting, which keeps the record for historical reference.",
    windows=[
        RecoveryWindow("5 minutes", 300, RecoveryDifficulty.SELF_SERVICE,
                        "Use the Undo system to restore from version history."),
        RecoveryWindow("1 hour", 3600, RecoveryDifficulty.ADMIN_HELP,
                        "An admin can restore from version history if snapshots exist."),
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups (taken daily)."),
        RecoveryWindow("1 week", 604800, RecoveryDifficulty.IT_HELP,
                        "IT can restore from weekly backup archives."),
        RecoveryWindow("Beyond 1 week", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Record must be re-created manually from MARC records or other sources.",
                        available=False),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_event",
    action_label="Delete event",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The event and all registrations are removed. Registered patrons are not notified automatically.",
    what_is_kept="Audit trail records the deletion.",
    reassurance="Consider canceling the event instead, which notifies registrants and preserves the record.",
    windows=[
        RecoveryWindow("5 minutes", 300, RecoveryDifficulty.ADMIN_HELP,
                        "An admin may be able to restore from version history."),
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IT_HELP,
                        "The event must be re-created manually.",
                        available=False),
    ],
))

# ---------------------------------------------------------------------------
# CIRCULATION operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="undo_checkout",
    action_label="Undo checkout",
    severity=ActionSeverity.MEDIUM,
    requires_confirmation=False,
    requires_typed_confirmation=False,
    soft_delete=True,
    what_is_lost="The checkout is reversed; the item returns to available status.",
    what_is_kept="The checkout attempt is logged in the audit trail.",
    reassurance="Checkout undos are routine and fully supported within the safety window.",
    windows=[
        RecoveryWindow("5 minutes", 300, RecoveryDifficulty.SELF_SERVICE,
                        "Staff can undo the checkout using the Undo button."),
        RecoveryWindow("Beyond 5 minutes", 0, RecoveryDifficulty.STAFF_HELP,
                        "Simply check the item out again to the patron.",
                        available=True),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="cancel_hold",
    action_label="Cancel a hold",
    severity=ActionSeverity.MEDIUM,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=True,
    what_is_lost="The patron's place in the hold queue is lost.",
    what_is_kept="The hold request is recorded in the audit trail.",
    reassurance="A new hold can be placed, but the patron will go to the back of the queue.",
    windows=[
        RecoveryWindow("30 minutes", 1800, RecoveryDifficulty.SELF_SERVICE,
                        "Use the Undo system to restore the hold and queue position."),
        RecoveryWindow("Beyond 30 minutes", 0, RecoveryDifficulty.STAFF_HELP,
                        "Place a new hold. Queue position cannot be restored."),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="undo_fine_payment",
    action_label="Reverse fine payment",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=True,
    what_is_lost="The payment is reversed; the fine becomes unpaid again.",
    what_is_kept="Both the original payment and reversal are recorded in the audit trail.",
    reassurance="Financial reversals are logged for accounting purposes and require admin approval.",
    windows=[
        RecoveryWindow("7 days", 604800, RecoveryDifficulty.ADMIN_HELP,
                        "An admin can reverse a fine payment within 7 days."),
        RecoveryWindow("Beyond 7 days", 0, RecoveryDifficulty.IT_HELP,
                        "Requires manual financial adjustment by IT or accounting.",
                        available=False),
    ],
))

# ---------------------------------------------------------------------------
# CONTENT operations (favorites, lists, reviews)
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="remove_favorite",
    action_label="Remove from favorites",
    severity=ActionSeverity.LOW,
    requires_confirmation=False,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The item is removed from your favorites list.",
    what_is_kept="Nothing — favorites are simple bookmarks with no history.",
    reassurance="You can re-add any item to your favorites at any time.",
    windows=[
        RecoveryWindow("Any time", 0, RecoveryDifficulty.SELF_SERVICE,
                        "Simply favorite the item again."),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_reading_list",
    action_label="Delete reading list",
    severity=ActionSeverity.MEDIUM,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The reading list and all items in it are deleted.",
    what_is_kept="The items themselves still exist in the catalog.",
    reassurance="The list must be recreated manually, but the books are still in the catalog.",
    windows=[
        RecoveryWindow("5 minutes", 300, RecoveryDifficulty.ADMIN_HELP,
                        "An admin may restore from version history."),
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "The list must be recreated manually.",
                        available=False),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_review",
    action_label="Delete review",
    severity=ActionSeverity.LOW,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The review text and rating are permanently removed.",
    what_is_kept="Audit trail records that a review existed.",
    reassurance="You can write a new review at any time.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT may be able to restore from backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Write a new review.",
                        available=False),
    ],
))

# ---------------------------------------------------------------------------
# STAFF / ADMIN operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="delete_announcement",
    action_label="Delete announcement",
    severity=ActionSeverity.MEDIUM,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The announcement is removed from all displays.",
    what_is_kept="Audit trail records the deletion.",
    reassurance="A new announcement can be created with the same content.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Recreate the announcement manually.",
                        available=False),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_branch",
    action_label="Delete branch location",
    severity=ActionSeverity.CRITICAL,
    requires_confirmation=True,
    requires_typed_confirmation=True,
    soft_delete=False,
    what_is_lost="All branch configuration, hours, and associated data.",
    what_is_kept="Items and patrons assigned to this branch are preserved but orphaned.",
    reassurance="This is extremely rare. Please verify with your director first.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("1 week", 604800, RecoveryDifficulty.IT_HELP,
                        "IT can restore from weekly archives."),
        RecoveryWindow("Beyond 1 week", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Branch must be reconfigured from scratch.",
                        available=False),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_role",
    action_label="Delete staff role",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=True,
    soft_delete=False,
    what_is_lost="The role and all its permission assignments are removed.",
    what_is_kept="Users previously assigned this role retain their other roles.",
    reassurance="Recreate the role and reassign permissions if needed.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Role must be recreated manually.",
                        available=False),
    ],
))

# ---------------------------------------------------------------------------
# EQUIPMENT / ROOM / RESERVATION operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="cancel_reservation",
    action_label="Cancel reservation",
    severity=ActionSeverity.MEDIUM,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=True,
    what_is_lost="The reservation slot is released and may be taken by someone else.",
    what_is_kept="The cancellation is recorded in the audit trail.",
    reassurance="A new reservation can be made if the slot is still available.",
    windows=[
        RecoveryWindow("Immediately", 0, RecoveryDifficulty.SELF_SERVICE,
                        "Make a new reservation for the same slot if still available."),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_room",
    action_label="Delete meeting room",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=True,
    soft_delete=True,
    what_is_lost="The room and all future reservations for it are removed.",
    what_is_kept="Past reservation history is preserved in the audit trail.",
    reassurance="Soft-deleted rooms can be restored by an admin.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.ADMIN_HELP,
                        "An admin can restore the soft-deleted room."),
        RecoveryWindow("Any time", 0, RecoveryDifficulty.ADMIN_HELP,
                        "Soft-deleted rooms can be restored indefinitely."),
    ],
))

# ---------------------------------------------------------------------------
# BULK operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="bulk_delete",
    action_label="Bulk delete records",
    severity=ActionSeverity.CRITICAL,
    requires_confirmation=True,
    requires_typed_confirmation=True,
    soft_delete=False,
    what_is_lost="All selected records are permanently removed.",
    what_is_kept="Audit trail records which items were deleted and by whom.",
    reassurance="Bulk operations cannot be undone. Please review the selection carefully.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups, but this affects ALL data since the backup."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Records must be recreated manually.",
                        available=False),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="bulk_deactivate",
    action_label="Bulk deactivate patrons",
    severity=ActionSeverity.CRITICAL,
    requires_confirmation=True,
    requires_typed_confirmation=True,
    soft_delete=True,
    what_is_lost="All selected patrons lose login access immediately.",
    what_is_kept="All patron data is preserved. Accounts can be individually reactivated.",
    reassurance="This is reversible but must be undone one account at a time.",
    windows=[
        RecoveryWindow("Any time", 0, RecoveryDifficulty.ADMIN_HELP,
                        "Accounts can be reactivated individually through Admin > Users."),
    ],
))

# ---------------------------------------------------------------------------
# LEARNING / PROGRAM operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="delete_course",
    action_label="Delete learning course",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The course, its modules, lessons, and enrollment records.",
    what_is_kept="Certificates already issued remain valid.",
    reassurance="Consider archiving the course instead of deleting to preserve learner progress.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Course must be recreated from scratch.",
                        available=False),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_program",
    action_label="Delete reading program",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The program and all participant progress data.",
    what_is_kept="Certificates and achievements already awarded are preserved.",
    reassurance="Consider ending the program instead of deleting to keep historical data.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Program must be recreated manually.",
                        available=False),
    ],
))

# ---------------------------------------------------------------------------
# BOARD / GOVERNANCE operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="delete_board_meeting",
    action_label="Delete board meeting record",
    severity=ActionSeverity.CRITICAL,
    requires_confirmation=True,
    requires_typed_confirmation=True,
    soft_delete=False,
    what_is_lost="Meeting record, agenda, minutes, and associated votes.",
    what_is_kept="Board member records and committee assignments remain.",
    reassurance="Board meetings are official public records. Deletion may have legal implications.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Meeting must be re-entered manually from paper records.",
                        available=False),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_motion",
    action_label="Delete board motion",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=True,
    soft_delete=False,
    what_is_lost="The motion and all associated votes.",
    what_is_kept="Meeting minutes may reference the motion.",
    reassurance="Motions are official records. Consider marking as withdrawn instead.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Motion must be re-entered manually.",
                        available=False),
    ],
))

# ---------------------------------------------------------------------------
# STRATEGIC operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="delete_strategic_plan",
    action_label="Delete strategic plan",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=True,
    soft_delete=False,
    what_is_lost="The strategic plan and all associated goals and milestones.",
    what_is_kept="Board meeting references to the plan remain.",
    reassurance="Consider archiving the plan instead of deleting.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Plan must be recreated manually.",
                        available=False),
    ],
))

# ---------------------------------------------------------------------------
# COMMUNICATION operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="unsubscribe",
    action_label="Unsubscribe from notifications",
    severity=ActionSeverity.LOW,
    requires_confirmation=False,
    requires_typed_confirmation=False,
    soft_delete=True,
    what_is_lost="You will stop receiving notifications of this type.",
    what_is_kept="Your subscription preferences are saved and can be re-enabled.",
    reassurance="You can resubscribe at any time in your notification settings.",
    windows=[
        RecoveryWindow("Any time", 0, RecoveryDifficulty.SELF_SERVICE,
                        "Re-enable in Settings > Notifications."),
    ],
))

_register(RegretRecoveryTimeline(
    action_key="delete_sms_phone",
    action_label="Remove phone number for SMS",
    severity=ActionSeverity.LOW,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="Your phone number is removed and SMS notifications stop.",
    what_is_kept="Past SMS delivery records are preserved.",
    reassurance="You can add a new phone number at any time.",
    windows=[
        RecoveryWindow("Any time", 0, RecoveryDifficulty.SELF_SERVICE,
                        "Add your phone number again in Settings > SMS."),
    ],
))

# ---------------------------------------------------------------------------
# OUTREACH / PARTNER operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="delete_partner",
    action_label="Delete outreach partner",
    severity=ActionSeverity.HIGH,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="Partner organization record and all associated service data.",
    what_is_kept="Outreach visit records that reference this partner are preserved.",
    reassurance="The partner can be re-added, but historical association is lost.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Partner record must be re-created manually.",
                        available=False),
    ],
))

# ---------------------------------------------------------------------------
# SYSTEM / SETTINGS operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="revert_setting",
    action_label="Revert system setting",
    severity=ActionSeverity.MEDIUM,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=True,
    what_is_lost="The current setting value is replaced with the previous one.",
    what_is_kept="Both old and new values are recorded in version history.",
    reassurance="Settings changes are fully tracked and can be reverted again.",
    windows=[
        RecoveryWindow("Any time", 0, RecoveryDifficulty.SELF_SERVICE,
                        "Use Settings > Version History to revert to any previous value."),
    ],
))

# ---------------------------------------------------------------------------
# SIGNAGE operations
# ---------------------------------------------------------------------------

_register(RegretRecoveryTimeline(
    action_key="delete_signage",
    action_label="Delete digital signage content",
    severity=ActionSeverity.MEDIUM,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The signage content and its schedule assignments.",
    what_is_kept="Display hardware configuration remains.",
    reassurance="New signage content can be created and scheduled.",
    windows=[
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "Content must be recreated.",
                        available=False),
    ],
))


# =============================================================================
# Default timeline for unregistered actions
# =============================================================================

_DEFAULT_TIMELINE = RegretRecoveryTimeline(
    action_key="unknown",
    action_label="Delete item",
    severity=ActionSeverity.MEDIUM,
    requires_confirmation=True,
    requires_typed_confirmation=False,
    soft_delete=False,
    what_is_lost="The selected item will be removed.",
    what_is_kept="The deletion is recorded in the audit trail.",
    reassurance="If you're unsure, cancel and ask a colleague first. There's no shame in double-checking.",
    windows=[
        RecoveryWindow("5 minutes", 300, RecoveryDifficulty.ADMIN_HELP,
                        "An admin may be able to help if you act quickly."),
        RecoveryWindow("1 day", 86400, RecoveryDifficulty.IT_HELP,
                        "IT can attempt to restore from database backups."),
        RecoveryWindow("Beyond 1 day", 0, RecoveryDifficulty.IMPOSSIBLE,
                        "The item may need to be recreated manually.",
                        available=False),
    ],
)


# =============================================================================
# Public API
# =============================================================================


def get_recovery_timeline(action_key: str) -> RegretRecoveryTimeline:
    timeline = _RECOVERY_REGISTRY.get(action_key, _DEFAULT_TIMELINE)
    if timeline is _DEFAULT_TIMELINE:
        # Return a copy with the actual action key
        from copy import copy
        result = copy(timeline)
        result.action_key = action_key
        return result
    return timeline


def get_all_registered_actions() -> Dict[str, RegretRecoveryTimeline]:
    return dict(_RECOVERY_REGISTRY)


def get_actions_by_severity(severity: ActionSeverity) -> List[RegretRecoveryTimeline]:
    return [t for t in _RECOVERY_REGISTRY.values() if t.severity == severity]


# Map common API endpoint patterns to action keys for auto-detection
ENDPOINT_TO_ACTION_KEY: Dict[str, str] = {
    # Users
    "DELETE /api/v1/users/{user_id}": "deactivate_user",
    "POST /api/v1/users/{user_id}/lock": "lock_user",
    "DELETE /api/v1/privacy/account": "delete_account_gdpr",
    # Catalog
    "DELETE /api/v1/catalog/{item_id}": "delete_catalog_item",
    "DELETE /api/v1/staff/catalog/{item_id}": "delete_catalog_item",
    # Events
    "DELETE /api/v1/events/{event_id}": "delete_event",
    # Circulation
    "POST /api/v1/undo/checkout/{checkout_id}": "undo_checkout",
    "POST /api/v1/holds/{hold_id}/cancel": "cancel_hold",
    "POST /api/v1/undo/fine/{fine_id}/payment": "undo_fine_payment",
    # Content
    "DELETE /api/v1/favorites/{catalog_item_id}": "remove_favorite",
    "DELETE /api/v1/reading-lists/{list_id}": "delete_reading_list",
    "DELETE /api/v1/events/reviews/{review_id}": "delete_review",
    # Staff/Admin
    "DELETE /api/v1/announcements/{announcement_id}": "delete_announcement",
    "DELETE /api/v1/roles/{role_id}": "delete_role",
    # Equipment/Rooms
    "DELETE /api/v1/equipment/reservations/{reservation_id}": "cancel_reservation",
    "DELETE /api/v1/rooms/{room_id}": "delete_room",
    "DELETE /api/v1/staff/rooms/{room_id}": "delete_room",
    # Learning
    "DELETE /api/v1/learning/courses/{course_id}": "delete_course",
    "DELETE /api/v1/reading-programs/programs/{program_id}": "delete_program",
    # Board/Governance
    "DELETE /api/v1/board/meetings/{meeting_id}": "delete_board_meeting",
    "DELETE /api/v1/board/motions/{motion_id}": "delete_motion",
    # Strategic
    "DELETE /api/v1/strategic/plans/{plan_id}": "delete_strategic_plan",
    # Outreach
    "DELETE /api/v1/outreach/partners/{partner_id}": "delete_partner",
    # Signage
    "DELETE /api/v1/signage/content/{content_id}": "delete_signage",
    "DELETE /api/v1/signage/displays/{display_id}": "delete_signage",
    # SMS
    "DELETE /api/v1/sms/phone": "delete_sms_phone",
    # Bulk
    "POST /api/v1/staff/patrons/bulk-delete": "bulk_delete",
    "POST /api/v1/staff/patrons/bulk-deactivate": "bulk_deactivate",
}


def detect_action_key(method: str, path: str) -> str:
    import re
    # Normalize numeric path segments to {param}
    normalized = re.sub(r'/\d+', '/{id}', path)
    lookup = f"{method.upper()} {normalized}"

    # Try exact match first
    if lookup in ENDPOINT_TO_ACTION_KEY:
        return ENDPOINT_TO_ACTION_KEY[lookup]

    # Try fuzzy match (endpoint patterns use named params)
    for pattern, key in ENDPOINT_TO_ACTION_KEY.items():
        pattern_normalized = re.sub(r'/\{[^}]+\}', '/{id}', pattern)
        if lookup == pattern_normalized:
            return key

    return "unknown"
