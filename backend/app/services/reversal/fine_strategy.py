# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.audit_log import AuditAction, AuditLog
from ...models.fine import Fine, FineStatus
from ...models.user import User
from .base import ReversalResult

logger = get_logger(__name__)


class FineReversalStrategy:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def undo_fine_waiver(
        self,
        fine_id: int,
        performer: User,
        reason: str = "Staff correction - waiver undone",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(Fine)
            .where(Fine.id == fine_id)
            .with_for_update()
        )
        fine = result.scalar_one_or_none()

        if not fine:
            return ReversalResult(
                success=False,
                message=f"Fine {fine_id} not found",
            )

        if fine.status != FineStatus.waived:
            return ReversalResult(
                success=False,
                message=f"Cannot undo waiver - fine status is '{fine.status}', not waived.",
                warnings=["Only waived fines can have their waiver undone"],
            )

        old_status = fine.status
        old_waived_at = fine.waived_at
        old_waived_by_id = fine.waived_by_id

        fine.status = FineStatus.unpaid
        fine.waived_at = None
        fine.waived_by_id = None

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=fine.user_id,
            action=AuditAction.REVERT_FINE_WAIVE,
            details={
                "fine_id": fine_id,
                "fine_type": fine.fine_type,
                "amount": str(fine.amount),
                "patron_id": fine.user_id,
                "checkout_id": fine.checkout_id,
                "old_status": old_status,
                "new_status": FineStatus.unpaid,
                "old_waived_at": old_waived_at.isoformat() if old_waived_at else None,
                "old_waived_by_id": old_waived_by_id,
                "reason": reason,
            },
            ip_address=None,
            user_agent=None,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(f"Undo fine waiver for fine {fine_id} by staff {performer.id}")

        return ReversalResult(
            success=True,
            message=f"Successfully undid waiver for fine {fine_id}. Fine has been restored to unpaid status.",
            audit_log_id=audit_log.id,
            reverted_changes={
                "fine_status": old_status,
                "waived_at": old_waived_at,
                "waived_by_id": old_waived_by_id,
            },
        )

    async def reverse_fine_payment(
        self,
        fine_id: int,
        amount_to_refund: Decimal,
        performer: User,
        reason: str = "Payment error",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(Fine)
            .where(Fine.id == fine_id)
            .with_for_update()
        )
        fine = result.scalar_one_or_none()

        if not fine:
            return ReversalResult(
                success=False,
                message=f"Fine {fine_id} not found",
            )

        if fine.amount_paid == Decimal("0.00"):
            return ReversalResult(
                success=False,
                message="Cannot reverse payment - fine has not been paid",
                warnings=["Amount paid is zero"],
            )

        if amount_to_refund > fine.amount_paid:
            return ReversalResult(
                success=False,
                message=f"Cannot refund ${amount_to_refund} - only ${fine.amount_paid} has been paid",
                warnings=["Refund amount exceeds amount paid"],
            )

        old_amount_paid = fine.amount_paid
        old_status = fine.status

        fine.amount_paid -= amount_to_refund

        if fine.amount_paid == Decimal("0.00"):
            fine.status = FineStatus.unpaid
            fine.paid_at = None
        elif fine.amount_paid < fine.amount:
            fine.status = FineStatus.partial

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=fine.user_id,
            action=AuditAction.CIRCULATION_REVERT_ITEM_STATUS,
            details={
                "fine_id": fine_id,
                "fine_type": fine.fine_type,
                "total_amount": str(fine.amount),
                "patron_id": fine.user_id,
                "checkout_id": fine.checkout_id,
                "old_amount_paid": str(old_amount_paid),
                "new_amount_paid": str(fine.amount_paid),
                "refunded_amount": str(amount_to_refund),
                "old_status": old_status,
                "new_status": fine.status,
                "reason": reason,
            },
            ip_address=None,
            user_agent=None,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(
            f"Reverse fine payment of ${amount_to_refund} for fine {fine_id} by staff {performer.id}"
        )

        return ReversalResult(
            success=True,
            message=f"Successfully refunded ${amount_to_refund} for fine {fine_id}.",
            audit_log_id=audit_log.id,
            reverted_changes={
                "amount_paid": old_amount_paid,
                "fine_status": old_status,
            },
        )
