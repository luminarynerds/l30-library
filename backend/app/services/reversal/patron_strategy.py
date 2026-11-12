# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.audit_log import AuditAction, AuditLog
from ...models.user import User, PatronStatus
from .base import ReversalResult

logger = get_logger(__name__)


class PatronRecoveryStrategy:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def restore_deactivated_patron(
        self,
        patron_id: int,
        performer: User,
        reason: str = "Account restoration - error recovery",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(User)
            .where(User.id == patron_id)
            .with_for_update()
        )
        patron = result.scalar_one_or_none()

        if not patron:
            return ReversalResult(
                success=False,
                message=f"Patron {patron_id} not found",
            )

        old_is_active = patron.is_active
        old_patron_status = patron.patron_status

        if patron.is_active and patron.patron_status == PatronStatus.ACTIVE:
            return ReversalResult(
                success=False,
                message=f"Patron {patron_id} is already active",
                warnings=["No restoration needed - patron account is already active"],
                patron_id=patron_id,
            )

        patron.is_active = True
        patron.patron_status = PatronStatus.ACTIVE

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=patron_id,
            action=AuditAction.PATRON_RESTORE,
            details={
                "patron_id": patron_id,
                "patron_name": patron.full_name,
                "patron_email": patron.email,
                "old_is_active": old_is_active,
                "new_is_active": True,
                "old_patron_status": old_patron_status,
                "new_patron_status": PatronStatus.ACTIVE,
                "reason": reason,
            },
            ip_address=None,
            user_agent=None,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(
            f"Restored deactivated patron {patron_id} ({patron.email}) by staff {performer.id}"
        )

        return ReversalResult(
            success=True,
            message=f"Successfully restored patron {patron_id} ({patron.full_name}).",
            patron_id=patron_id,
            audit_log_id=audit_log.id,
            recovered_data={
                "is_active": old_is_active,
                "patron_status": old_patron_status,
            },
        )

    async def unblock_patron(
        self,
        patron_id: int,
        performer: User,
        reason: str = "Block removal - error recovery",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(User)
            .where(User.id == patron_id)
            .with_for_update()
        )
        patron = result.scalar_one_or_none()

        if not patron:
            return ReversalResult(
                success=False,
                message=f"Patron {patron_id} not found",
            )

        old_patron_status = patron.patron_status
        old_block_reason = patron.block_reason
        old_blocked_at = patron.blocked_at
        old_blocked_by_id = patron.blocked_by_id

        if patron.patron_status != PatronStatus.BLOCKED:
            return ReversalResult(
                success=False,
                message=f"Patron {patron_id} is not blocked (status: {patron.patron_status})",
                warnings=["Patron is not blocked - no unblock needed"],
                patron_id=patron_id,
            )

        patron.patron_status = PatronStatus.ACTIVE
        patron.block_reason = None
        patron.blocked_at = None
        patron.blocked_by_id = None

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=patron_id,
            action=AuditAction.REVERT_UNLOCK_USER,
            details={
                "patron_id": patron_id,
                "patron_name": patron.full_name,
                "patron_email": patron.email,
                "old_patron_status": old_patron_status,
                "new_patron_status": PatronStatus.ACTIVE,
                "old_block_reason": old_block_reason,
                "old_blocked_at": old_blocked_at.isoformat() if old_blocked_at else None,
                "old_blocked_by_id": old_blocked_by_id,
                "reason": reason,
            },
            ip_address=None,
            user_agent=None,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(
            f"Unblocked patron {patron_id} ({patron.email}) by staff {performer.id}"
        )

        return ReversalResult(
            success=True,
            message=f"Successfully unblocked patron {patron_id} ({patron.full_name}).",
            patron_id=patron_id,
            audit_log_id=audit_log.id,
            recovered_data={
                "patron_status": old_patron_status,
                "block_reason": old_block_reason,
            },
        )

    async def unsuspend_patron(
        self,
        patron_id: int,
        performer: User,
        reason: str = "Suspension removal - error recovery",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(User)
            .where(User.id == patron_id)
            .with_for_update()
        )
        patron = result.scalar_one_or_none()

        if not patron:
            return ReversalResult(
                success=False,
                message=f"Patron {patron_id} not found",
            )

        old_patron_status = patron.patron_status
        old_suspension_reason = patron.suspension_reason
        old_suspended_at = patron.suspended_at
        old_suspended_until = patron.suspended_until
        old_suspended_by_id = patron.suspended_by_id

        if patron.patron_status != PatronStatus.SUSPENDED:
            return ReversalResult(
                success=False,
                message=f"Patron {patron_id} is not suspended (status: {patron.patron_status})",
                warnings=["Patron is not suspended - no unsuspension needed"],
                patron_id=patron_id,
            )

        patron.patron_status = PatronStatus.ACTIVE
        patron.suspension_reason = None
        patron.suspended_at = None
        patron.suspended_until = None
        patron.suspended_by_id = None

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=patron_id,
            action=AuditAction.REVERT_UNLOCK_USER,
            details={
                "patron_id": patron_id,
                "patron_name": patron.full_name,
                "patron_email": patron.email,
                "old_patron_status": old_patron_status,
                "new_patron_status": PatronStatus.ACTIVE,
                "old_suspension_reason": old_suspension_reason,
                "old_suspended_at": old_suspended_at.isoformat() if old_suspended_at else None,
                "old_suspended_until": old_suspended_until.isoformat() if old_suspended_until else None,
                "old_suspended_by_id": old_suspended_by_id,
                "reason": reason,
            },
            ip_address=None,
            user_agent=None,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(
            f"Unsuspended patron {patron_id} ({patron.email}) by staff {performer.id}"
        )

        return ReversalResult(
            success=True,
            message=f"Successfully unsuspended patron {patron_id} ({patron.full_name}).",
            patron_id=patron_id,
            audit_log_id=audit_log.id,
            recovered_data={
                "patron_status": old_patron_status,
                "suspension_reason": old_suspension_reason,
            },
        )

    async def list_recoverable_patrons(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(User)
            .where(
                (User.is_active == False) |
                (User.patron_status.in_([PatronStatus.SUSPENDED, PatronStatus.BLOCKED]))
            )
            .offset(offset)
            .limit(limit)
        )
        patrons = result.scalars().all()

        return [
            {
                "id": p.id,
                "email": p.email,
                "name": p.full_name,
                "is_active": p.is_active,
                "patron_status": p.patron_status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in patrons
        ]
