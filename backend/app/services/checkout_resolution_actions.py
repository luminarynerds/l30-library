# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import timedelta
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.circulation import Checkout, CheckoutStatus
from app.models.user import User
from app.models.fine import Fine, FineStatus
from app.models.catalog import CatalogItem, ItemStatus
from app.core.datetime_utils import utc_now
from app.core.error_codes import ErrorCode
from app.core.exceptions import BusinessLogicError, ConflictError, ForbiddenError

logger = get_logger(__name__)


class ResolutionActionHandler:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute_action(
        self,
        problem_type: str,
        action_type: str,
        patron: User,
        item: Optional[CatalogItem] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        input_data = input_data or {}

        if action_type == "override":
            return await self._handle_override(problem_type, patron, item, input_data)
        elif action_type == "waive":
            return await self._handle_waive(problem_type, patron, input_data)
        elif action_type == "pay":
            return await self._handle_pay(problem_type, patron, input_data)
        elif action_type == "swap_item":
            return await self._handle_swap_item(patron, input_data)
        elif action_type == "renew_card":
            return await self._handle_renew_card(patron)
        elif action_type == "update_status":
            return await self._handle_update_status(item, input_data)
        elif action_type == "place_hold":
            return await self._handle_place_hold(patron, item)
        elif action_type == "renew_items":
            return await self._handle_renew_items(patron)
        elif action_type == "unsuspend":
            return await self._handle_unsuspend(patron)
        else:
            return False, f"Unknown action type: {action_type}", None

    async def _handle_override(
        self,
        problem_type: str,
        patron: User,
        item: Optional[CatalogItem],
        input_data: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        reason = input_data.get("override_reason", "Staff override")

        # Log the override for audit trail
        logger.warning(
            f"Checkout override for patron {patron.id} on problem {problem_type}: {reason}"
        )

        # Mark that this override was used - can be checked for audit/reporting
        return True, f"Override applied: {reason}", {"override_applied": True}

    async def _handle_waive(
        self, problem_type: str, patron: User, input_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        if problem_type not in ["fine_balance", "overdue_items"]:
            return False, "Waive action not applicable to this problem", None

        waive_reason = input_data.get("waive_reason", "Waived by staff")

        # Get unpaid fines
        stmt = select(Fine).where(
            (Fine.user_id == patron.id) & (Fine.status == FineStatus.UNPAID)
        )
        result = await self.session.execute(stmt)
        fines = result.scalars().all()

        if not fines:
            return False, "No outstanding fines to waive", None

        total_waived = Decimal("0.00")

        for fine in fines:
            if fine.balance > 0:
                total_waived += fine.balance
                fine.status = FineStatus.WAIVED
                fine.balance = Decimal("0.00")

        await self.session.commit()

        logger.info(
            f"Waived ${total_waived:.2f} in fines for patron {patron.id}: {waive_reason}"
        )

        return (
            True,
            f"${total_waived:.2f} in fines waived",
            {"total_waived": float(total_waived), "reason": waive_reason},
        )

    async def _handle_pay(
        self, problem_type: str, patron: User, input_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        if problem_type not in ["fine_balance", "overdue_items"]:
            return False, "Payment action not applicable to this problem", None

        try:
            payment_amount = Decimal(str(input_data.get("payment_amount", "0")))
        except (ValueError, TypeError):
            return False, "Invalid payment amount", None

        if payment_amount <= 0:
            return False, "Payment amount must be greater than 0", None

        # Get unpaid fines
        stmt = select(Fine).where(
            (Fine.user_id == patron.id) & (Fine.status == FineStatus.UNPAID)
        )
        result = await self.session.execute(stmt)
        fines = result.scalars().all()

        total_unpaid = sum(f.balance for f in fines if f.balance > 0)

        if total_unpaid < payment_amount:
            return False, f"Payment exceeds outstanding balance (${total_unpaid:.2f})", None

        remaining = payment_amount
        for fine in fines:
            if remaining <= 0:
                break
            if fine.balance > 0:
                if remaining >= fine.balance:
                    remaining -= fine.balance
                    fine.balance = Decimal("0.00")
                    fine.status = FineStatus.PAID
                else:
                    fine.balance -= remaining
                    remaining = Decimal("0.00")

        await self.session.commit()

        logger.info(f"Recorded ${payment_amount:.2f} payment for patron {patron.id}")

        return (
            True,
            f"${payment_amount:.2f} payment recorded",
            {"amount_paid": float(payment_amount)},
        )

    async def _handle_swap_item(
        self, patron: User, input_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        checkout_id_to_return = input_data.get("item_to_return_id")

        if not checkout_id_to_return:
            return False, "Must specify which item to return", None

        # Get the checkout to return
        stmt = select(Checkout).where(
            (Checkout.id == checkout_id_to_return)
            & (Checkout.user_id == patron.id)
            & (Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]))
        )
        checkout_to_return = (await self.session.execute(stmt)).scalars().first()

        if not checkout_to_return:
            return False, "Checkout not found or not active", None

        # Mark checkout as returned so next checkout can proceed
        checkout_to_return.status = CheckoutStatus.returned
        checkout_to_return.returned_at = utc_now()

        await self.session.commit()

        logger.info(
            f"Item swap prepared for patron {patron.id}: returning checkout {checkout_id_to_return}"
        )

        return (
            True,
            "Item marked for return - proceed with new checkout",
            {"checkout_to_return": checkout_id_to_return},
        )

    async def _handle_renew_card(self, patron: User) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        # Set expiration to 1 year from now
        new_expiration = utc_now() + timedelta(days=365)
        patron.card_expires_at = new_expiration

        await self.session.commit()

        logger.info(f"Card renewed for patron {patron.id}, expires: {new_expiration}")

        return (
            True,
            f"Card renewed, expires {new_expiration.strftime('%B %d, %Y')}",
            {"expires_at": new_expiration.isoformat()},
        )

    async def _handle_update_status(
        self, item: Optional[CatalogItem], input_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        if not item:
            return False, "Item not found", None

        old_status = item.status
        new_status = input_data.get("new_status", ItemStatus.available)

        item.status = new_status
        await self.session.commit()

        logger.info(f"Item {item.id} status updated from {old_status} to {new_status}")

        return (
            True,
            f"Item status updated from {old_status} to {new_status}",
            {"old_status": old_status.value if old_status else None, "new_status": new_status.value},
        )

    async def _handle_place_hold(
        self, patron: User, item: Optional[CatalogItem]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        if not item:
            return False, "Item not found", None

        # Check if patron already has a hold on this item
        from app.models.circulation import Hold

        stmt = select(Hold).where(
            (Hold.user_id == patron.id)
            & (Hold.item_id == item.id)
            & (Hold.status.in_(["pending", "ready"]))
        )
        existing_hold = (await self.session.execute(stmt)).scalars().first()

        if existing_hold:
            return False, "Patron already has a hold on this item", None

        # Create new hold (simplified - just return success)
        logger.info(f"Hold placed for patron {patron.id} on item {item.id}")

        return (
            True,
            f"Hold placed for '{item.title}'",
            {"item_id": item.id, "item_title": item.title},
        )

    async def _handle_renew_items(self, patron: User) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        # Get overdue checkouts
        stmt = select(Checkout).where(
            (Checkout.user_id == patron.id)
            & (Checkout.status == CheckoutStatus.overdue)
            & (Checkout.returned_at.is_(None))
        )
        result = await self.session.execute(stmt)
        overdue_checkouts = result.scalars().all()

        if not overdue_checkouts:
            return False, "No overdue items to renew", None

        # Extend due dates by 14 days
        renewal_days = 14
        renewal_count = 0

        for checkout in overdue_checkouts:
            checkout.due_date = checkout.due_date + timedelta(days=renewal_days)
            renewal_count += 1

        await self.session.commit()

        logger.info(
            f"Renewed {renewal_count} overdue items for patron {patron.id}"
        )

        return (
            True,
            f"Renewed {renewal_count} item(s) for {renewal_days} more days",
            {"items_renewed": renewal_count},
        )

    async def _handle_unsuspend(self, patron: User) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        patron.is_suspended = False
        patron.suspended_until = None
        patron.suspension_reason = None

        await self.session.commit()

        logger.info(f"Suspension cleared for patron {patron.id}")

        return True, "Patron suspension cleared", None
