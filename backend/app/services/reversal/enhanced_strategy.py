# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.audit_log import AuditAction, AuditLog
from ...models.circulation import Checkout, Hold, HoldStatus
from ...models.fine import Fine, FineStatus
from ...models.user import User, PatronStatus
from ...models.version_history import VersionHistory, EntityType, ChangeType
from .base import (
    ReversalResult,
    UNDO_HOLD_WINDOW_MINUTES,
    UNDO_RENEWAL_WINDOW_DAYS,
    UNDO_FINE_PAYMENT_WINDOW_DAYS,
)

logger = get_logger(__name__)


class EnhancedReversalStrategy:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def undo_hold_placement(
        self,
        hold_id: int,
        performer: User,
        reason: str = "User requested cancellation",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(Hold)
            .where(Hold.id == hold_id)
            .with_for_update()
        )
        hold = result.scalar_one_or_none()

        if not hold:
            return ReversalResult(
                success=False,
                message=f"Hold {hold_id} not found",
            )

        now = datetime.now(timezone.utc)
        time_since_hold = now - hold.created_at
        if time_since_hold > timedelta(minutes=UNDO_HOLD_WINDOW_MINUTES):
            return ReversalResult(
                success=False,
                message=f"Hold is outside the undo window ({UNDO_HOLD_WINDOW_MINUTES} minutes)",
                warnings=["Hold cannot be undone after 30 minutes"],
            )

        if hold.status != HoldStatus.pending:
            return ReversalResult(
                success=False,
                message=f"Cannot undo hold with status '{hold.status}'",
                warnings=["Only pending holds can be undone"],
            )

        old_status = hold.status
        hold.status = HoldStatus.cancelled
        hold.cancelled_at = now

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=hold.user_id,
            action=AuditAction.CIRCULATION_UNDO_HOLD,
            details={
                "hold_id": hold_id,
                "item_id": hold.item_id,
                "old_status": old_status,
                "new_status": HoldStatus.cancelled,
                "reason": reason,
            },
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(f"Undo hold {hold_id} for patron {hold.user_id} by {performer.id}")

        return ReversalResult(
            success=True,
            message=f"Successfully cancelled hold {hold_id}",
            audit_log_id=audit_log.id,
            reverted_changes={"hold_status": old_status},
        )

    async def undo_renewal(
        self,
        checkout_id: int,
        performer: User,
        reason: str = "Patron requested undo",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(Checkout)
            .where(Checkout.id == checkout_id)
            .with_for_update()
        )
        checkout = result.scalar_one_or_none()

        if not checkout:
            return ReversalResult(
                success=False,
                message=f"Checkout {checkout_id} not found",
            )

        if checkout.renewal_count <= 0:
            return ReversalResult(
                success=False,
                message="This checkout has not been renewed",
                warnings=["Cannot undo a renewal on an unrenewe checkout"],
            )

        if checkout.last_renewed_at is None:
            return ReversalResult(
                success=False,
                message="No renewal history found",
            )

        now = datetime.now(timezone.utc)
        time_since_renewal = now - checkout.last_renewed_at
        if time_since_renewal > timedelta(days=UNDO_RENEWAL_WINDOW_DAYS):
            return ReversalResult(
                success=False,
                message=f"Renewal is outside the undo window ({UNDO_RENEWAL_WINDOW_DAYS} day(s))",
                warnings=["Renewal cannot be undone"],
            )

        old_due_date = checkout.due_date
        old_renewal_count = checkout.renewal_count

        checkout.renewal_count -= 1
        checkout.due_date = old_due_date - timedelta(days=14)
        checkout.last_renewed_at = None

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=checkout.user_id,
            action=AuditAction.CIRCULATION_UNDO_RENEWAL,
            details={
                "checkout_id": checkout_id,
                "item_id": checkout.item_id,
                "old_renewal_count": old_renewal_count,
                "new_renewal_count": checkout.renewal_count,
                "old_due_date": old_due_date.isoformat(),
                "new_due_date": checkout.due_date.isoformat(),
                "reason": reason,
            },
        )
        self.db.add(audit_log)
        await self.db.flush()

        return ReversalResult(
            success=True,
            message=f"Successfully undid renewal for checkout {checkout_id}",
            audit_log_id=audit_log.id,
            reverted_changes={
                "renewal_count": old_renewal_count,
                "due_date": old_due_date.isoformat(),
            },
        )

    async def undo_fine_payment(
        self,
        fine_id: int,
        performer: User,
        reason: str = "Payment reversal requested",
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

        if fine.status != FineStatus.paid:
            return ReversalResult(
                success=False,
                message=f"Fine status is '{fine.status}' - only paid fines can have payments reversed",
            )

        now = datetime.now(timezone.utc)
        if fine.paid_at:
            time_since_payment = now - fine.paid_at
            if time_since_payment > timedelta(days=UNDO_FINE_PAYMENT_WINDOW_DAYS):
                return ReversalResult(
                    success=False,
                    message=f"Payment is outside the undo window ({UNDO_FINE_PAYMENT_WINDOW_DAYS} days)",
                    warnings=["Payment cannot be reversed"],
                )

        old_status = fine.status
        old_amount_paid = fine.amount_paid

        fine.status = FineStatus.unpaid
        fine.amount_paid = 0
        fine.paid_at = None

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=fine.user_id,
            action=AuditAction.FINE_PAYMENT_REVERSED,
            details={
                "fine_id": fine_id,
                "old_status": old_status.value,
                "new_status": FineStatus.unpaid.value,
                "amount_refunded": old_amount_paid,
                "reason": reason,
            },
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(f"Reversed fine payment {fine_id} for patron {fine.user_id}")

        return ReversalResult(
            success=True,
            message=f"Successfully reversed payment for fine {fine_id}. Amount refunded: ${old_amount_paid:.2f}",
            audit_log_id=audit_log.id,
            reverted_changes={
                "status": old_status.value,
                "amount_paid": old_amount_paid,
            },
        )

    async def undo_patron_suspension(
        self,
        user_id: int,
        performer: User,
        reason: str = "Suspension reversed",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
        )
        user = result.scalar_one_or_none()

        if not user:
            return ReversalResult(
                success=False,
                message=f"User {user_id} not found",
            )

        old_status = user.patron_status
        if old_status == PatronStatus.active:
            return ReversalResult(
                success=False,
                message="Patron is already active",
                warnings=["No suspension to reverse"],
            )

        user.patron_status = PatronStatus.ACTIVE
        user.suspended_until = None

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=user_id,
            action=AuditAction.PATRON_SUSPENSION_REVERSED,
            details={
                "patron_id": user_id,
                "old_status": old_status.value,
                "new_status": PatronStatus.active.value,
                "reason": reason,
            },
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(f"Reversed patron suspension for {user_id}")

        return ReversalResult(
            success=True,
            message=f"Successfully restored patron {user_id} to active status",
            audit_log_id=audit_log.id,
            reverted_changes={"patron_status": old_status.value},
        )

    async def soft_delete_recovery(
        self,
        entity_type: EntityType,
        entity_id: int,
        performer: User,
        reason: str = "Recovery requested",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(VersionHistory)
            .where(
                VersionHistory.entity_type == entity_type,
                VersionHistory.entity_id == entity_id,
                VersionHistory.change_type == ChangeType.DELETE,
            )
            .order_by(VersionHistory.version_number.desc())
            .limit(1)
        )
        deletion_record = result.scalar_one_or_none()

        if not deletion_record:
            return ReversalResult(
                success=False,
                message=f"{entity_type.value} {entity_id} has not been deleted",
            )

        if not deletion_record.is_deleted:
            return ReversalResult(
                success=False,
                message="Entity has already been recovered",
            )

        recovery = VersionHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=ChangeType.RESTORE,
            version_number=deletion_record.version_number + 1,
            changed_by_user_id=performer.id,
            entity_state=deletion_record.entity_state,
            change_reason=reason,
        )
        self.db.add(recovery)

        audit_log = AuditLog(
            admin_id=performer.id,
            action=AuditAction.PATRON_RESTORE,
            details={
                "entity_type": entity_type.value,
                "entity_id": entity_id,
                "recovered_from_version": deletion_record.version_number,
                "reason": reason,
            },
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(f"Recovered soft-deleted {entity_type.value} {entity_id}")

        return ReversalResult(
            success=True,
            message=f"Successfully recovered {entity_type.value} {entity_id}",
            audit_log_id=audit_log.id,
            reverted_changes={
                "entity_type": entity_type.value,
                "entity_id": entity_id,
                "status": "recovered",
            },
        )
