# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.audit_log import AuditAction, AuditLog
from ...models.circulation import Checkout, CheckoutStatus
from ...models.fine import Fine, FineStatus
from ...models.user import User, UserRole
from .base import (
    CanRevertResult,
    ReversalResult,
    NON_REVERSIBLE_ACTIONS,
    REVERSIBLE_ACTIONS,
    get_user,
    get_audit_log,
)

logger = get_logger(__name__)


class AuditReversalStrategy:
    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Public Interface
    # =========================================================================

    async def check_can_revert(self, audit_log_id: int) -> CanRevertResult:
        audit_log = await get_audit_log(self.db, audit_log_id)

        if not audit_log:
            return CanRevertResult(
                can_revert=False,
                reason="Audit log entry not found",
            )

        action = audit_log.action

        if action in NON_REVERSIBLE_ACTIONS:
            return CanRevertResult(
                can_revert=False,
                reason=f"Action type '{action.value}' cannot be reversed",
                action_type=action.value,
            )

        if action not in REVERSIBLE_ACTIONS:
            return CanRevertResult(
                can_revert=False,
                reason=f"Action type '{action.value}' is not supported for reversal",
                action_type=action.value,
            )

        if action == AuditAction.UPDATE_USER:
            return await self._check_can_revert_user_update(audit_log)
        elif action == AuditAction.LOCK_USER:
            return await self._check_can_revert_lock_user(audit_log)
        elif action == AuditAction.UNLOCK_USER:
            return await self._check_can_revert_unlock_user(audit_log)
        elif action in [
            AuditAction.PRIVACY_CHANGE_READING_LIST,
            AuditAction.PRIVACY_CHANGE_FAVORITES,
            AuditAction.PRIVACY_CHANGE_GENERIC,
        ]:
            return await self._check_can_revert_privacy_change(audit_log)
        elif action == AuditAction.PATRON_MERGE:
            return await self._check_can_revert_patron_merge(audit_log)
        elif action in [AuditAction.FEE_WAIVED, AuditAction.FEE_PAID]:
            return await self._check_can_revert_fine_action(audit_log)
        elif action == AuditAction.EXTENSION_GRANTED:
            return await self._check_can_revert_extension_granted(audit_log)
        elif action == AuditAction.PRIVACY_SETTING_CHANGED:
            return await self._check_can_revert_privacy_setting_changed(audit_log)
        elif action in [
            AuditAction.CONTENT_FLAGGED,
            AuditAction.CONTENT_MODERATED,
            AuditAction.CONTENT_REMOVED,
        ]:
            return await self._check_can_revert_content_action(audit_log)
        elif action in [AuditAction.MEETING_UPDATED, AuditAction.MEETING_CANCELLED]:
            return await self._check_can_revert_meeting_action(audit_log)
        elif action == AuditAction.ACTION_ITEM_STATUS_CHANGED:
            return await self._check_can_revert_action_item_status_changed(audit_log)
        elif action == AuditAction.NOTE_ADDED:
            return await self._check_can_revert_note_added(audit_log)
        elif action == AuditAction.STATUS_CHANGED:
            return await self._check_can_revert_status_changed(audit_log)

        return CanRevertResult(
            can_revert=False,
            reason="Reversal not implemented for this action type",
            action_type=action.value,
        )

    async def revert(
        self,
        audit_log_id: int,
        admin_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ReversalResult:
        can_revert_result = await self.check_can_revert(audit_log_id)
        if not can_revert_result.can_revert:
            return ReversalResult(
                success=False,
                message=can_revert_result.reason,
                warnings=can_revert_result.warnings,
            )

        audit_log = await get_audit_log(self.db, audit_log_id)
        if not audit_log:
            return ReversalResult(
                success=False,
                message="Audit log entry not found",
            )

        action = audit_log.action

        if action == AuditAction.UPDATE_USER:
            return await self._revert_user_update(audit_log, admin_id, ip_address, user_agent)
        elif action == AuditAction.LOCK_USER:
            return await self._revert_lock_user(audit_log, admin_id, ip_address, user_agent)
        elif action == AuditAction.UNLOCK_USER:
            return await self._revert_unlock_user(audit_log, admin_id, ip_address, user_agent)
        elif action in [
            AuditAction.PRIVACY_CHANGE_READING_LIST,
            AuditAction.PRIVACY_CHANGE_FAVORITES,
            AuditAction.PRIVACY_CHANGE_GENERIC,
        ]:
            return await self._revert_privacy_change(audit_log, admin_id, ip_address, user_agent)
        elif action == AuditAction.PATRON_MERGE:
            return await self._revert_patron_merge(audit_log, admin_id, ip_address, user_agent)
        elif action in [AuditAction.FEE_WAIVED, AuditAction.FEE_PAID]:
            return await self._revert_fine_action(audit_log, admin_id, ip_address, user_agent)
        elif action == AuditAction.EXTENSION_GRANTED:
            return await self._revert_extension_granted(audit_log, admin_id, ip_address, user_agent)
        elif action == AuditAction.PRIVACY_SETTING_CHANGED:
            return await self._revert_privacy_setting_changed(
                audit_log, admin_id, ip_address, user_agent
            )
        elif action in [
            AuditAction.CONTENT_FLAGGED,
            AuditAction.CONTENT_MODERATED,
            AuditAction.CONTENT_REMOVED,
        ]:
            return await self._revert_content_action(audit_log, admin_id, ip_address, user_agent)
        elif action in [AuditAction.MEETING_UPDATED, AuditAction.MEETING_CANCELLED]:
            return await self._revert_meeting_action(audit_log, admin_id, ip_address, user_agent)
        elif action == AuditAction.ACTION_ITEM_STATUS_CHANGED:
            return await self._revert_action_item_status_changed(
                audit_log, admin_id, ip_address, user_agent
            )
        elif action == AuditAction.NOTE_ADDED:
            return await self._revert_note_added(audit_log, admin_id, ip_address, user_agent)
        elif action == AuditAction.STATUS_CHANGED:
            return await self._revert_status_changed(audit_log, admin_id, ip_address, user_agent)

        return ReversalResult(
            success=False,
            message="Reversal not implemented for this action type",
        )

    # =========================================================================
    # Private Check Methods
    # =========================================================================

    async def _check_can_revert_user_update(self, audit_log: AuditLog) -> CanRevertResult:
        warnings = []

        if audit_log.target_user_id:
            user = await get_user(self.db, audit_log.target_user_id)
            if not user:
                return CanRevertResult(
                    can_revert=False,
                    reason="Target user no longer exists",
                    action_type=str(audit_log.action),
                )
        else:
            return CanRevertResult(
                can_revert=False,
                reason="No target user ID in audit log",
                action_type=str(audit_log.action),
            )

        details = audit_log.details or {}
        changes = details.get("changes", {})

        if not changes:
            return CanRevertResult(
                can_revert=False,
                reason="No change details stored in audit log - cannot determine what to revert",
                action_type=str(audit_log.action),
            )

        revertable_fields = []
        for field_name, change in changes.items():
            if isinstance(change, dict) and "old" in change:
                revertable_fields.append(field_name)
            else:
                warnings.append(f"Field '{field_name}' missing old value - will be skipped")

        if not revertable_fields:
            return CanRevertResult(
                can_revert=False,
                reason="No revertable fields found in change details",
                action_type=str(audit_log.action),
            )

        return CanRevertResult(
            can_revert=True,
            reason=f"Can revert changes to fields: {', '.join(revertable_fields)}",
            action_type=str(audit_log.action),
            details={"revertable_fields": revertable_fields, "changes": changes},
            warnings=warnings,
        )

    async def _check_can_revert_lock_user(self, audit_log: AuditLog) -> CanRevertResult:
        if not audit_log.target_user_id:
            return CanRevertResult(
                can_revert=False,
                reason="No target user ID in audit log",
                action_type=str(audit_log.action),
            )

        user = await get_user(self.db, audit_log.target_user_id)
        if not user:
            return CanRevertResult(
                can_revert=False,
                reason="Target user no longer exists",
                action_type=str(audit_log.action),
            )

        if not user.is_locked():
            return CanRevertResult(
                can_revert=False,
                reason="User is not currently locked - may have already been unlocked",
                action_type=str(audit_log.action),
            )

        return CanRevertResult(
            can_revert=True,
            reason="Can unlock the user to revert the lock action",
            action_type=str(audit_log.action),
            details={"user_email": user.email, "locked_until": str(user.locked_until)},
        )

    async def _check_can_revert_unlock_user(self, audit_log: AuditLog) -> CanRevertResult:
        warnings = []

        if not audit_log.target_user_id:
            return CanRevertResult(
                can_revert=False,
                reason="No target user ID in audit log",
                action_type=str(audit_log.action),
            )

        user = await get_user(self.db, audit_log.target_user_id)
        if not user:
            return CanRevertResult(
                can_revert=False,
                reason="Target user no longer exists",
                action_type=str(audit_log.action),
            )

        if user.is_locked():
            return CanRevertResult(
                can_revert=False,
                reason="User is already locked - may have been locked again",
                action_type=str(audit_log.action),
            )

        warnings.append("Re-locking will use a new lock duration (100 years from now)")

        return CanRevertResult(
            can_revert=True,
            reason="Can re-lock the user to revert the unlock action",
            action_type=str(audit_log.action),
            details={"user_email": user.email},
            warnings=warnings,
        )

    async def _check_can_revert_privacy_change(self, audit_log: AuditLog) -> CanRevertResult:
        details = audit_log.details or {}

        if "old_privacy" not in details:
            return CanRevertResult(
                can_revert=False,
                reason="Old privacy setting not stored in audit log",
                action_type=str(audit_log.action),
            )

        resource_type = details.get("resource_type", "unknown")
        resource_id = details.get("resource_id")

        if not resource_id:
            return CanRevertResult(
                can_revert=False,
                reason="Resource ID not stored in audit log",
                action_type=str(audit_log.action),
            )

        return CanRevertResult(
            can_revert=True,
            reason=f"Can revert privacy setting for {resource_type} to '{details.get('old_privacy')}'",
            action_type=str(audit_log.action),
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "old_privacy": details.get("old_privacy"),
                "new_privacy": details.get("new_privacy"),
            },
        )

    async def _check_can_revert_patron_merge(self, audit_log: AuditLog) -> CanRevertResult:
        details = audit_log.details or {}
        warnings = [
            "Patron merge reversal is a complex operation",
            "Some data may not be fully reversible (e.g., merged transaction history)",
            "Manual review is recommended after reversal",
        ]

        # merge_patron_records (api/v1/staff/patrons_account.py) writes these as
        # primary/secondary. Reading source/target_user_id meant both keys were
        # always None, so every patron merge was permanently unrevertible.
        # source = merged FROM (secondary), target = merged INTO (primary).
        source_user_id = details.get("secondary_patron_id")
        target_user_id = details.get("primary_patron_id")

        if not source_user_id or not target_user_id:
            return CanRevertResult(
                can_revert=False,
                reason="Merge details (source/target user IDs) not stored in audit log",
                action_type=str(audit_log.action),
            )

        pre_merge_state = details.get("pre_merge_state")
        if not pre_merge_state:
            warnings.append("Pre-merge state not stored - reversal may be incomplete")

        return CanRevertResult(
            can_revert=True,
            reason="Patron merge can potentially be reverted - manual review recommended",
            action_type=str(audit_log.action),
            details={
                "source_user_id": source_user_id,
                "target_user_id": target_user_id,
                "has_pre_merge_state": bool(pre_merge_state),
            },
            warnings=warnings,
        )

    async def _check_can_revert_fine_action(self, audit_log: AuditLog) -> CanRevertResult:
        details = audit_log.details or {}
        fine_id = details.get("fine_id")

        if not fine_id:
            return CanRevertResult(
                can_revert=False,
                reason="No fine ID stored in audit log - cannot locate fine record",
                action_type=str(audit_log.action),
            )

        result = await self.db.execute(select(Fine).where(Fine.id == fine_id))
        fine = result.scalar_one_or_none()

        if not fine:
            return CanRevertResult(
                can_revert=False,
                reason=f"Fine record {fine_id} no longer exists",
                action_type=str(audit_log.action),
            )

        # Guard: the fine's current status must still be what the audit action
        # set it to. If the fine has been modified since (e.g. waived then paid),
        # reverting would clobber subsequent state.
        expected_status_after_action = {
            AuditAction.FEE_WAIVED: FineStatus.waived,
            AuditAction.FEE_PAID: FineStatus.paid,
        }.get(audit_log.action)

        if expected_status_after_action is not None and fine.status != expected_status_after_action:
            return CanRevertResult(
                can_revert=False,
                reason=(
                    f"Fine {fine_id} is currently '{fine.status}' — it has been modified "
                    f"since the '{audit_log.action}' action and cannot be safely reverted"
                ),
                action_type=str(audit_log.action),
                details={
                    "fine_id": fine_id,
                    "current_status": str(fine.status),
                    "expected_status": str(expected_status_after_action),
                },
            )

        previous_status = details.get("previous_status")
        if not previous_status:
            return CanRevertResult(
                can_revert=False,
                reason="Previous fine status not stored in audit log - cannot determine revert target",
                action_type=str(audit_log.action),
            )

        return CanRevertResult(
            can_revert=True,
            reason=f"Can revert fine {fine_id} from '{fine.status}' back to '{previous_status}'",
            action_type=str(audit_log.action),
            details={
                "fine_id": fine_id,
                "current_status": str(fine.status),
                "previous_status": previous_status,
            },
        )

    async def _check_can_revert_extension_granted(self, audit_log: AuditLog) -> CanRevertResult:
        details = audit_log.details or {}
        checkout_id = details.get("checkout_id")
        old_due_date = details.get("old_due_date") or details.get("previous_due_date")

        if not checkout_id:
            return CanRevertResult(
                can_revert=False,
                reason="No checkout ID stored in audit log - cannot locate loan record",
                action_type=str(audit_log.action),
            )

        if not old_due_date:
            return CanRevertResult(
                can_revert=False,
                reason="Previous due date not stored in audit log - cannot determine revert target",
                action_type=str(audit_log.action),
            )

        result = await self.db.execute(select(Checkout).where(Checkout.id == checkout_id))
        checkout = result.scalar_one_or_none()

        if not checkout:
            return CanRevertResult(
                can_revert=False,
                reason=f"Checkout record {checkout_id} no longer exists",
                action_type=str(audit_log.action),
            )

        if checkout.status != CheckoutStatus.active:
            return CanRevertResult(
                can_revert=False,
                reason=f"Checkout is no longer active (status: {checkout.status}) - cannot revert extension",
                action_type=str(audit_log.action),
            )

        return CanRevertResult(
            can_revert=True,
            reason=f"Can revert due date for checkout {checkout_id} to '{old_due_date}'",
            action_type=str(audit_log.action),
            details={
                "checkout_id": checkout_id,
                "old_due_date": old_due_date,
                "new_due_date": details.get("new_due_date"),
            },
        )

    async def _check_can_revert_privacy_setting_changed(
        self, audit_log: AuditLog
    ) -> CanRevertResult:
        details = audit_log.details or {}

        old_value = details.get("old_value") or details.get("old_privacy")
        if old_value is None:
            return CanRevertResult(
                can_revert=False,
                reason="Previous privacy setting not stored in audit log - cannot determine revert target",
                action_type=str(audit_log.action),
            )

        setting_name = details.get("setting_name") or details.get("field") or "privacy_setting"

        return CanRevertResult(
            can_revert=True,
            reason=f"Can revert privacy setting '{setting_name}' to previous value '{old_value}'",
            action_type=str(audit_log.action),
            details={
                "setting_name": setting_name,
                "old_value": old_value,
                "new_value": details.get("new_value") or details.get("new_privacy"),
            },
        )

    async def _check_can_revert_content_action(self, audit_log: AuditLog) -> CanRevertResult:
        details = audit_log.details or {}
        content_id = details.get("content_id") or details.get("resource_id")
        content_type = details.get("content_type") or details.get("resource_type", "content")

        if not content_id:
            return CanRevertResult(
                can_revert=False,
                reason="No content ID stored in audit log - cannot locate content record",
                action_type=str(audit_log.action),
            )

        warnings = []
        if audit_log.action == AuditAction.CONTENT_REMOVED:
            warnings.append(
                "Content removal reversal requires the content to still exist in the system"
            )
            warnings.append("If content was permanently deleted, reversal may not be possible")

        return CanRevertResult(
            can_revert=True,
            reason=f"Can revert {str(audit_log.action).lower()} for {content_type} {content_id}",
            action_type=str(audit_log.action),
            details={
                "content_id": content_id,
                "content_type": content_type,
                "previous_state": details.get("previous_state") or details.get("old_state"),
            },
            warnings=warnings,
        )

    async def _check_can_revert_meeting_action(self, audit_log: AuditLog) -> CanRevertResult:
        details = audit_log.details or {}
        meeting_id = details.get("meeting_id") or details.get("resource_id")

        if not meeting_id:
            return CanRevertResult(
                can_revert=False,
                reason="No meeting ID stored in audit log - cannot locate meeting record",
                action_type=str(audit_log.action),
            )

        old_state = (
            details.get("old_state") or details.get("previous_state") or details.get("changes", {})
        )
        if not old_state:
            return CanRevertResult(
                can_revert=False,
                reason="Previous meeting state not stored in audit log - cannot determine revert target",
                action_type=str(audit_log.action),
            )

        return CanRevertResult(
            can_revert=True,
            reason=f"Can revert meeting {meeting_id} to previous state",
            action_type=str(audit_log.action),
            details={
                "meeting_id": meeting_id,
                "previous_state": old_state,
            },
        )

    async def _check_can_revert_action_item_status_changed(
        self, audit_log: AuditLog
    ) -> CanRevertResult:
        details = audit_log.details or {}
        item_id = (
            details.get("action_item_id") or details.get("item_id") or details.get("resource_id")
        )
        previous_status = details.get("previous_status") or details.get("old_status")

        if not item_id:
            return CanRevertResult(
                can_revert=False,
                reason="No action item ID stored in audit log - cannot locate item record",
                action_type=str(audit_log.action),
            )

        if not previous_status:
            return CanRevertResult(
                can_revert=False,
                reason="Previous status not stored in audit log - cannot determine revert target",
                action_type=str(audit_log.action),
            )

        return CanRevertResult(
            can_revert=True,
            reason=f"Can revert action item {item_id} status to '{previous_status}'",
            action_type=str(audit_log.action),
            details={
                "item_id": item_id,
                "previous_status": previous_status,
                "new_status": details.get("new_status"),
            },
        )

    async def _check_can_revert_note_added(self, audit_log: AuditLog) -> CanRevertResult:
        details = audit_log.details or {}
        note_id = details.get("note_id") or details.get("resource_id")
        note_content = details.get("note") or details.get("content") or details.get("note_content")

        if not note_id and not note_content:
            return CanRevertResult(
                can_revert=False,
                reason="No note ID or content stored in audit log - cannot identify note to remove",
                action_type=str(audit_log.action),
            )

        return CanRevertResult(
            can_revert=True,
            reason="Can mark note as retracted in the audit record",
            action_type=str(audit_log.action),
            details={
                "note_id": note_id,
                "note_content": note_content,
            },
            warnings=[
                "Note retraction creates an audit record but may not delete the note from the system"
            ],
        )

    async def _check_can_revert_status_changed(self, audit_log: AuditLog) -> CanRevertResult:
        details = audit_log.details or {}
        resource_id = details.get("resource_id") or details.get("entity_id")
        resource_type = details.get("resource_type") or details.get("entity_type", "record")
        previous_status = details.get("previous_status") or details.get("old_status")

        if not resource_id:
            return CanRevertResult(
                can_revert=False,
                reason="No resource ID stored in audit log - cannot locate record",
                action_type=str(audit_log.action),
            )

        if not previous_status:
            return CanRevertResult(
                can_revert=False,
                reason="Previous status not stored in audit log - cannot determine revert target",
                action_type=str(audit_log.action),
            )

        return CanRevertResult(
            can_revert=True,
            reason=f"Can revert {resource_type} {resource_id} status to '{previous_status}'",
            action_type=str(audit_log.action),
            details={
                "resource_id": resource_id,
                "resource_type": resource_type,
                "previous_status": previous_status,
                "new_status": details.get("new_status"),
            },
        )

    # =========================================================================
    # Private Revert Methods
    # =========================================================================

    async def _revert_user_update(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        result = await self.db.execute(
            select(User).where(User.id == audit_log.target_user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            return ReversalResult(
                success=False,
                message="Target user not found",
            )

        details = audit_log.details or {}
        changes = details.get("changes", {})

        reverted_changes = {}
        warnings = []

        for field_name, change in changes.items():
            if not isinstance(change, dict) or "old" not in change:
                warnings.append(f"Skipped field '{field_name}' - no old value stored")
                continue

            old_value = change["old"]
            current_value = getattr(user, field_name, None)

            if field_name == "role" and old_value:
                try:
                    old_value = UserRole(old_value)
                except ValueError:
                    warnings.append(f"Invalid role value '{old_value}' - skipped")
                    continue

            current_for_compare = (
                current_value.value if hasattr(current_value, "value") else current_value
            )

            setattr(user, field_name, old_value)
            reverted_changes[field_name] = {
                "reverted_from": current_for_compare,
                "reverted_to": old_value.value if hasattr(old_value, "value") else old_value,
            }

        if not reverted_changes:
            return ReversalResult(
                success=False,
                message="No fields could be reverted",
                warnings=warnings,
            )

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=user.id,
            action=AuditAction.REVERT_USER_UPDATE,
            details={
                "original_audit_log_id": audit_log.id,
                "reverted_changes": reverted_changes,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted user update (audit_log_id={audit_log.id}) for user {user.id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "user_id": user.id,
                "admin_id": admin_id,
                "reverted_changes": reverted_changes,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted user update for user {user.email}",
            audit_log_id=reversal_audit.id,
            reverted_changes=reverted_changes,
            warnings=warnings,
        )

    async def _revert_lock_user(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        user = await get_user(self.db, audit_log.target_user_id)
        if not user:
            return ReversalResult(
                success=False,
                message="Target user not found",
            )

        if not user.is_locked():
            return ReversalResult(
                success=False,
                message="User is not currently locked",
            )

        old_locked_until = user.locked_until

        user.locked_until = None
        user.failed_login_attempts = 0

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=user.id,
            action=AuditAction.REVERT_LOCK_USER,
            details={
                "original_audit_log_id": audit_log.id,
                "email": user.email,
                "previous_locked_until": old_locked_until.isoformat() if old_locked_until else None,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted lock user (audit_log_id={audit_log.id}) - unlocked user {user.id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "user_id": user.id,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully unlocked user {user.email} (reverting lock action)",
            audit_log_id=reversal_audit.id,
            reverted_changes={"locked_until": {"from": str(old_locked_until), "to": None}},
        )

    async def _revert_unlock_user(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        user = await get_user(self.db, audit_log.target_user_id)
        if not user:
            return ReversalResult(
                success=False,
                message="Target user not found",
            )

        if user.is_locked():
            return ReversalResult(
                success=False,
                message="User is already locked",
            )

        new_locked_until = datetime.now(timezone.utc) + timedelta(days=36500)
        user.locked_until = new_locked_until

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=user.id,
            action=AuditAction.REVERT_UNLOCK_USER,
            details={
                "original_audit_log_id": audit_log.id,
                "email": user.email,
                "new_locked_until": new_locked_until.isoformat(),
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted unlock user (audit_log_id={audit_log.id}) - re-locked user {user.id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "user_id": user.id,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully re-locked user {user.email} (reverting unlock action)",
            audit_log_id=reversal_audit.id,
            reverted_changes={"locked_until": {"from": None, "to": str(new_locked_until)}},
            warnings=["User has been locked indefinitely (100 years)"],
        )

    async def _revert_privacy_change(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}

        resource_type = details.get("resource_type")
        resource_id = details.get("resource_id")
        old_privacy = details.get("old_privacy")
        new_privacy = details.get("new_privacy")

        if not all([resource_type, resource_id, old_privacy is not None]):
            return ReversalResult(
                success=False,
                message="Missing required data for privacy reversal",
            )

        is_public = old_privacy == "public"

        reverted = False
        warnings = []

        if resource_type == "reading_list":
            reverted = await self._revert_reading_list_privacy(resource_id, is_public)
        elif resource_type == "strain_list":
            reverted = await self._revert_strain_list_privacy(resource_id, is_public)
        elif resource_type == "favorites":
            warnings.append("Favorites privacy reversal requires user preferences update")
            reverted = False
        else:
            warnings.append(f"Unknown resource type '{resource_type}' - reversal not supported")
            reverted = False

        if not reverted:
            return ReversalResult(
                success=False,
                message=f"Could not revert privacy for {resource_type} (ID: {resource_id})",
                warnings=warnings,
            )

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=audit_log.target_user_id,
            action=AuditAction.REVERT_PRIVACY_CHANGE,
            details={
                "original_audit_log_id": audit_log.id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "reverted_from": new_privacy,
                "reverted_to": old_privacy,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted privacy change (audit_log_id={audit_log.id}) for {resource_type} {resource_id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted {resource_type} privacy from '{new_privacy}' to '{old_privacy}'",
            audit_log_id=reversal_audit.id,
            reverted_changes={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "privacy": {"from": new_privacy, "to": old_privacy},
            },
            warnings=warnings,
        )

    async def _revert_reading_list_privacy(self, list_id: int, is_public: bool) -> bool:
        from ...models.reading_list import ReadingList

        result = await self.db.execute(select(ReadingList).where(ReadingList.id == list_id))
        reading_list = result.scalar_one_or_none()

        if not reading_list:
            return False

        reading_list.is_public = is_public
        return True

    async def _revert_strain_list_privacy(self, list_id: int, is_public: bool) -> bool:
        return False

    async def _revert_patron_merge(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}
        warnings = [
            "Patron merge reversal is a best-effort operation",
            "Some merged data (e.g., transaction history) may not be fully separated",
        ]

        # merge_patron_records (api/v1/staff/patrons_account.py) writes these as
        # primary/secondary. Reading source/target_user_id meant both keys were
        # always None, so every patron merge was permanently unrevertible.
        # source = merged FROM (secondary), target = merged INTO (primary).
        source_user_id = details.get("secondary_patron_id")
        target_user_id = details.get("primary_patron_id")
        pre_merge_state = details.get("pre_merge_state", {})

        if not source_user_id or not target_user_id:
            return ReversalResult(
                success=False,
                message="Missing source or target user ID in merge details",
            )

        result = await self.db.execute(
            select(User).where(User.id == source_user_id).with_for_update()
        )
        source_user = result.scalar_one_or_none()
        result = await self.db.execute(
            select(User).where(User.id == target_user_id).with_for_update()
        )
        target_user = result.scalar_one_or_none()

        if not target_user:
            return ReversalResult(
                success=False,
                message="Target user from merge no longer exists",
            )

        reverted_items = {}

        if pre_merge_state and source_user:
            source_state = pre_merge_state.get("source_user", {})
            for field_name, value in source_state.items():
                if hasattr(source_user, field_name):
                    try:
                        setattr(source_user, field_name, value)
                        reverted_items[f"source_{field_name}"] = value
                    except (AttributeError, TypeError, ValueError) as e:
                        warnings.append(f"Could not restore source user field '{field_name}': {e}")

            if not source_user.is_active:
                source_user.is_active = True
                reverted_items["source_is_active"] = True
        elif not source_user:
            warnings.append("Source user no longer exists - cannot restore source account")

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=target_user_id,
            action=AuditAction.REVERT_PATRON_MERGE,
            details={
                "original_audit_log_id": audit_log.id,
                "source_user_id": source_user_id,
                "target_user_id": target_user_id,
                "reverted_items": reverted_items,
                "warnings": warnings,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted patron merge (audit_log_id={audit_log.id})",
            extra={
                "original_audit_log_id": audit_log.id,
                "source_user_id": source_user_id,
                "target_user_id": target_user_id,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message="Patron merge reversal completed with warnings - manual review recommended",
            audit_log_id=reversal_audit.id,
            reverted_changes=reverted_items,
            warnings=warnings,
        )

    async def _revert_fine_action(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}
        fine_id = details.get("fine_id")
        previous_status = details.get("previous_status")

        if not fine_id or not previous_status:
            return ReversalResult(
                success=False,
                message="Missing fine ID or previous status in audit log details",
            )

        result = await self.db.execute(select(Fine).where(Fine.id == fine_id).with_for_update())
        fine = result.scalar_one_or_none()

        if not fine:
            return ReversalResult(
                success=False,
                message=f"Fine record {fine_id} not found",
            )

        current_status = str(fine.status)

        try:
            fine.status = FineStatus(previous_status)
        except ValueError:
            return ReversalResult(
                success=False,
                message=f"Invalid previous status value '{previous_status}'",
            )

        if audit_log.action == AuditAction.FEE_WAIVED:
            fine.waived_at = None
            fine.waived_by_id = None

        if audit_log.action == AuditAction.FEE_PAID:
            prev_amount_paid = details.get("previous_amount_paid")
            if prev_amount_paid is not None:
                try:
                    fine.amount_paid = Decimal(str(prev_amount_paid))
                except (InvalidOperation, ValueError, TypeError) as e:
                    logger.warning("Failed to restore previous amount_paid during reversal: %s", e)
            fine.paid_at = None

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=audit_log.target_user_id,
            action=AuditAction.REVERT_FINE_WAIVE,
            details={
                "original_audit_log_id": audit_log.id,
                "fine_id": fine_id,
                "reverted_from": current_status,
                "reverted_to": previous_status,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted fine action (audit_log_id={audit_log.id}) for fine {fine_id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "fine_id": fine_id,
                "admin_id": admin_id,
                "reverted_from": current_status,
                "reverted_to": previous_status,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted fine {fine_id} status from '{current_status}' to '{previous_status}'",
            audit_log_id=reversal_audit.id,
            reverted_changes={
                "fine_id": fine_id,
                "status": {"from": current_status, "to": previous_status},
            },
        )

    async def _revert_extension_granted(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}
        checkout_id = details.get("checkout_id")
        old_due_date = details.get("old_due_date") or details.get("previous_due_date")

        if not checkout_id or not old_due_date:
            return ReversalResult(
                success=False,
                message="Missing checkout ID or previous due date in audit log details",
            )

        result = await self.db.execute(
            select(Checkout).where(Checkout.id == checkout_id).with_for_update()
        )
        checkout = result.scalar_one_or_none()

        if not checkout:
            return ReversalResult(
                success=False,
                message=f"Checkout record {checkout_id} not found",
            )

        current_due_date = checkout.due_date

        try:
            if isinstance(old_due_date, str):
                checkout.due_date = datetime.fromisoformat(old_due_date)
            else:
                checkout.due_date = old_due_date
        except (ValueError, TypeError) as e:
            return ReversalResult(
                success=False,
                message=f"Invalid due date format in audit log: {e}",
            )

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=audit_log.target_user_id,
            action=AuditAction.SETTINGS_REVERTED,
            details={
                "original_audit_log_id": audit_log.id,
                "checkout_id": checkout_id,
                "reverted_from": current_due_date.isoformat() if current_due_date else None,
                "reverted_to": old_due_date,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted extension granted (audit_log_id={audit_log.id}) for checkout {checkout_id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "checkout_id": checkout_id,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted loan extension for checkout {checkout_id}",
            audit_log_id=reversal_audit.id,
            reverted_changes={
                "checkout_id": checkout_id,
                "due_date": {
                    "from": current_due_date.isoformat() if current_due_date else None,
                    "to": old_due_date,
                },
            },
        )

    async def _revert_privacy_setting_changed(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}

        old_value = details.get("old_value") or details.get("old_privacy")
        new_value = details.get("new_value") or details.get("new_privacy")
        setting_name = details.get("setting_name") or details.get("field") or "privacy_setting"

        if old_value is None:
            return ReversalResult(
                success=False,
                message="Missing previous privacy setting value in audit log details",
            )

        if not audit_log.target_user_id:
            return ReversalResult(
                success=False,
                message="No target user ID in audit log — cannot apply privacy setting revert",
            )
        user = await get_user(self.db, audit_log.target_user_id)
        if not user:
            return ReversalResult(
                success=False,
                message="Target user not found",
            )
        if not hasattr(user, setting_name):
            return ReversalResult(
                success=False,
                message=f"User has no attribute '{setting_name}' — cannot revert privacy setting",
            )
        setattr(user, setting_name, old_value)

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=audit_log.target_user_id,
            action=AuditAction.REVERT_PRIVACY_CHANGE,
            details={
                "original_audit_log_id": audit_log.id,
                "setting_name": setting_name,
                "reverted_from": new_value,
                "reverted_to": old_value,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted privacy setting change (audit_log_id={audit_log.id})",
            extra={
                "original_audit_log_id": audit_log.id,
                "setting_name": setting_name,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted privacy setting '{setting_name}' from '{new_value}' to '{old_value}'",
            audit_log_id=reversal_audit.id,
            reverted_changes={
                "setting_name": setting_name,
                "privacy": {"from": new_value, "to": old_value},
            },
        )

    async def _revert_content_action(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}
        content_id = details.get("content_id") or details.get("resource_id")
        content_type = details.get("content_type") or details.get("resource_type", "content")
        previous_state = details.get("previous_state") or details.get("old_state")

        if not content_id:
            return ReversalResult(
                success=False,
                message="Missing content ID in audit log details",
            )

        warnings = []
        if audit_log.action == AuditAction.CONTENT_REMOVED:
            warnings.append(
                "Content removal reversal is best-effort - content may not be fully restorable"
            )

        reverted_changes = {
            "content_id": content_id,
            "content_type": content_type,
            "action_reverted": str(audit_log.action),
        }
        if previous_state:
            reverted_changes["restored_state"] = previous_state

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=audit_log.target_user_id,
            action=AuditAction.SETTINGS_REVERTED,
            details={
                "original_audit_log_id": audit_log.id,
                "content_id": content_id,
                "content_type": content_type,
                "action_reverted": str(audit_log.action),
                "restored_state": previous_state,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted content action (audit_log_id={audit_log.id}) for {content_type} {content_id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "content_id": content_id,
                "content_type": content_type,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted {audit_log.action} for {content_type} {content_id}",
            audit_log_id=reversal_audit.id,
            reverted_changes=reverted_changes,
            warnings=warnings,
        )

    async def _revert_meeting_action(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}
        meeting_id = details.get("meeting_id") or details.get("resource_id")
        old_state = (
            details.get("old_state") or details.get("previous_state") or details.get("changes", {})
        )

        if not meeting_id or not old_state:
            return ReversalResult(
                success=False,
                message="Missing meeting ID or previous state in audit log details",
            )

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=audit_log.target_user_id,
            action=AuditAction.SETTINGS_REVERTED,
            details={
                "original_audit_log_id": audit_log.id,
                "meeting_id": meeting_id,
                "restored_state": old_state,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted meeting action (audit_log_id={audit_log.id}) for meeting {meeting_id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "meeting_id": meeting_id,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted {audit_log.action} for meeting {meeting_id}",
            audit_log_id=reversal_audit.id,
            reverted_changes={
                "meeting_id": meeting_id,
                "action_reverted": str(audit_log.action),
                "restored_state": old_state,
            },
        )

    async def _revert_action_item_status_changed(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}
        item_id = (
            details.get("action_item_id") or details.get("item_id") or details.get("resource_id")
        )
        previous_status = details.get("previous_status") or details.get("old_status")
        new_status = details.get("new_status")

        if not item_id or not previous_status:
            return ReversalResult(
                success=False,
                message="Missing action item ID or previous status in audit log details",
            )

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=audit_log.target_user_id,
            action=AuditAction.SETTINGS_REVERTED,
            details={
                "original_audit_log_id": audit_log.id,
                "action_item_id": item_id,
                "reverted_from": new_status,
                "reverted_to": previous_status,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted action item status change (audit_log_id={audit_log.id}) for item {item_id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "item_id": item_id,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted action item {item_id} status from '{new_status}' to '{previous_status}'",
            audit_log_id=reversal_audit.id,
            reverted_changes={
                "action_item_id": item_id,
                "status": {"from": new_status, "to": previous_status},
            },
        )

    async def _revert_note_added(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}
        note_id = details.get("note_id") or details.get("resource_id")
        note_content = details.get("note") or details.get("content") or details.get("note_content")

        if not note_id:
            return ReversalResult(
                success=False,
                message="No note ID in audit log — cannot locate note to remove",
            )

        from ...models.patron_communication import PatronNote

        result = await self.db.execute(
            select(PatronNote).where(PatronNote.id == note_id, PatronNote.is_deleted.is_(False))
        )
        note = result.scalar_one_or_none()
        if not note:
            return ReversalResult(
                success=False,
                message=f"Note {note_id} not found or already deleted",
            )
        note.soft_delete(user_id=admin_id, reason="Admin reversal of NOTE_ADDED action")

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=audit_log.target_user_id,
            action=AuditAction.SETTINGS_REVERTED,
            details={
                "original_audit_log_id": audit_log.id,
                "note_id": note_id,
                "note_content": note_content,
                "retraction_reason": "Admin reversal of NOTE_ADDED action",
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted note added (audit_log_id={audit_log.id}), note_id={note_id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "note_id": note_id,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Note {note_id} has been removed and audit trail updated",
            audit_log_id=reversal_audit.id,
            reverted_changes={
                "note_id": note_id,
                "action": "note_deleted",
            },
        )

    async def _revert_status_changed(
        self,
        audit_log: AuditLog,
        admin_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> ReversalResult:
        details = audit_log.details or {}
        resource_id = details.get("resource_id") or details.get("entity_id")
        resource_type = details.get("resource_type") or details.get("entity_type", "record")
        previous_status = details.get("previous_status") or details.get("old_status")
        new_status = details.get("new_status")

        if not resource_id or not previous_status:
            return ReversalResult(
                success=False,
                message="Missing resource ID or previous status in audit log details",
            )

        reversal_audit = AuditLog(
            admin_id=admin_id,
            target_user_id=audit_log.target_user_id,
            action=AuditAction.SETTINGS_REVERTED,
            details={
                "original_audit_log_id": audit_log.id,
                "resource_id": resource_id,
                "resource_type": resource_type,
                "reverted_from": new_status,
                "reverted_to": previous_status,
                "original_action": str(audit_log.action),
                "original_action_date": audit_log.created_at.isoformat()
                if audit_log.created_at
                else None,
            },
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.db.add(reversal_audit)
        await self.db.flush()

        logger.info(
            f"Reverted status change (audit_log_id={audit_log.id}) for {resource_type} {resource_id}",
            extra={
                "original_audit_log_id": audit_log.id,
                "resource_id": resource_id,
                "resource_type": resource_type,
                "admin_id": admin_id,
            },
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted {resource_type} {resource_id} status from '{new_status}' to '{previous_status}'",
            audit_log_id=reversal_audit.id,
            reverted_changes={
                "resource_id": resource_id,
                "resource_type": resource_type,
                "status": {"from": new_status, "to": previous_status},
            },
        )
