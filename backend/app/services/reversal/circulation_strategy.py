# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.audit_log import AuditAction, AuditLog
from ...models.catalog import CatalogItem, ItemStatus
from ...models.circulation import Checkout, CheckoutStatus
from ...models.user import User
from .base import ReversalResult, UNDO_CHECKOUT_WINDOW_MINUTES

logger = get_logger(__name__)


class CirculationReversalStrategy:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def undo_checkout(
        self,
        checkout_id: int,
        performer: User,
        reason: str = "User error - accidental checkout",
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

        if checkout.status != CheckoutStatus.active:
            return ReversalResult(
                success=False,
                message=f"Cannot undo checkout with status '{checkout.status}'. Only active checkouts can be undone.",
                warnings=["Checkout has already been returned or processed"],
            )

        now = datetime.now(timezone.utc)
        time_since_checkout = now - checkout.checked_out_at
        if time_since_checkout > timedelta(minutes=UNDO_CHECKOUT_WINDOW_MINUTES):
            return ReversalResult(
                success=False,
                message=f"Cannot undo checkout - {time_since_checkout.total_seconds() / 60:.1f} minutes have passed. Undo window is {UNDO_CHECKOUT_WINDOW_MINUTES} minutes.",
                warnings=["Checkout is outside the undo window"],
            )

        item_result = await self.db.execute(
            select(CatalogItem)
            .where(CatalogItem.id == checkout.item_id)
            .with_for_update()
        )
        item = item_result.scalar_one_or_none()

        if not item:
            return ReversalResult(
                success=False,
                message="Item not found for this checkout",
                warnings=["Item may have been deleted"],
            )

        old_checkout_status = checkout.status
        old_item_status = item.status

        checkout.status = CheckoutStatus.returned
        checkout.returned_at = now
        item.status = ItemStatus.available
        # Decrement total_checkouts since this was an accidental checkout
        if item.total_checkouts and item.total_checkouts > 0:
            item.total_checkouts -= 1

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=checkout.user_id,
            action=AuditAction.CIRCULATION_UNDO_CHECKOUT,
            details={
                "checkout_id": checkout_id,
                "item_id": checkout.item_id,
                "item_barcode": item.barcode,
                "patron_id": checkout.user_id,
                "old_checkout_status": old_checkout_status,
                "new_checkout_status": CheckoutStatus.returned,
                "old_item_status": old_item_status,
                "new_item_status": ItemStatus.available,
                "time_since_checkout_minutes": time_since_checkout.total_seconds() / 60,
                "reason": reason,
            },
            ip_address=None,
            user_agent=None,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(
            f"Undo checkout {checkout_id} for patron {checkout.user_id} by staff {performer.id}"
        )

        return ReversalResult(
            success=True,
            message=f"Successfully undid checkout {checkout_id}. Item {item.barcode or checkout_id} has been returned.",
            audit_log_id=audit_log.id,
            reverted_changes={
                "checkout_status": old_checkout_status,
                "item_status": old_item_status,
            },
        )

    async def reverse_return(
        self,
        checkout_id: int,
        performer: User,
        reason: str = "User error - mistaken return",
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

        if checkout.status != CheckoutStatus.returned:
            return ReversalResult(
                success=False,
                message=f"Cannot reverse return - checkout status is '{checkout.status}', not returned.",
                warnings=["Only returned checkouts can be reversed"],
            )

        item_result = await self.db.execute(
            select(CatalogItem)
            .where(CatalogItem.id == checkout.item_id)
            .with_for_update()
        )
        item = item_result.scalar_one_or_none()

        if not item:
            return ReversalResult(
                success=False,
                message="Item not found for this checkout",
                warnings=["Item may have been deleted"],
            )

        if item.status not in [ItemStatus.available, ItemStatus.on_hold]:
            return ReversalResult(
                success=False,
                message=f"Cannot reverse return - item status is '{item.status}'. Item must be available or on hold.",
                warnings=["Item may have been checked out, lost, or damaged"],
            )

        old_checkout_status = checkout.status
        old_returned_at = checkout.returned_at
        old_item_status = item.status

        checkout.status = CheckoutStatus.active
        checkout.returned_at = None
        item.status = ItemStatus.checked_out

        audit_log = AuditLog(
            admin_id=performer.id,
            target_user_id=checkout.user_id,
            action=AuditAction.CIRCULATION_REVERSE_RETURN,
            details={
                "checkout_id": checkout_id,
                "item_id": checkout.item_id,
                "item_barcode": item.barcode,
                "patron_id": checkout.user_id,
                "old_checkout_status": old_checkout_status,
                "new_checkout_status": CheckoutStatus.active,
                "old_item_status": old_item_status,
                "new_item_status": ItemStatus.checked_out,
                "old_returned_at": old_returned_at.isoformat() if old_returned_at else None,
                "reason": reason,
            },
            ip_address=None,
            user_agent=None,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(
            f"Reverse return for checkout {checkout_id} for patron {checkout.user_id} by staff {performer.id}"
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reversed return for checkout {checkout_id}. Item is now active for patron.",
            audit_log_id=audit_log.id,
            reverted_changes={
                "checkout_status": old_checkout_status,
                "item_status": old_item_status,
                "returned_at": old_returned_at,
            },
        )

    async def revert_item_status_change(
        self,
        item_id: int,
        previous_status: ItemStatus,
        performer: User,
        reason: str = "Staff correction",
    ) -> ReversalResult:
        result = await self.db.execute(
            select(CatalogItem)
            .where(CatalogItem.id == item_id)
            .with_for_update()
        )
        item = result.scalar_one_or_none()

        if not item:
            return ReversalResult(
                success=False,
                message=f"Item {item_id} not found",
            )

        old_status = item.status
        item.status = previous_status

        audit_log = AuditLog(
            admin_id=performer.id,
            action=AuditAction.CIRCULATION_REVERT_ITEM_STATUS,
            details={
                "item_id": item_id,
                "item_barcode": item.barcode,
                "old_status": old_status,
                "new_status": previous_status,
                "reason": reason,
            },
            ip_address=None,
            user_agent=None,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(
            f"Revert item {item_id} status from {old_status} to {previous_status} by staff {performer.id}"
        )

        return ReversalResult(
            success=True,
            message=f"Successfully reverted item status from '{old_status}' to '{previous_status}'.",
            audit_log_id=audit_log.id,
            reverted_changes={"item_status": old_status},
        )
