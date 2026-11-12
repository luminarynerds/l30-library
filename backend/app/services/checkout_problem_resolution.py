# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.circulation import Checkout, Hold, HoldStatus
from app.models.user import User
from app.models.fine import Fine, FineStatus
from app.models.catalog import CatalogItem
from app.core.error_codes import ErrorCode
from app.core.datetime_utils import ensure_utc, utc_now


@dataclass
class ResolutionAction:
    action_type: str  # override, waive, pay, swap_item, renew_card, update_status
    label: str  # Display text for button
    description: str  # What this action will do
    required_input: Optional[str] = None  # override_reason, payment_amount, etc.
    icon: str = "check"  # UI icon


@dataclass
class ProblemDetails:
    problem_type: str  # on_hold, fine_block, card_expired, checkout_limit, item_missing, etc.
    title: str  # Brief problem description
    description: str  # Detailed explanation with context
    context: Dict[str, Any]  # Raw data: hold_patron, fine_amount, etc.
    solutions: List[str]  # Suggested solutions
    actions: List[ResolutionAction]  # Available one-click resolutions
    severity: str = "warning"  # info, warning, error, critical


class CheckoutProblemResolver:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve_problem(
        self,
        error_code: ErrorCode,
        patron: User,
        item: Optional[CatalogItem] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ProblemDetails]:
        if error_code == ErrorCode.ITEM_ON_HOLD:
            return await self._resolve_item_on_hold(item)

        elif error_code == ErrorCode.PATRON_HAS_OUTSTANDING_FINE:
            return await self._resolve_patron_has_outstanding_fine(patron, context or {})

        elif error_code == ErrorCode.PATRON_CARD_EXPIRED:
            return await self._resolve_card_expired(patron, context or {})

        elif error_code == ErrorCode.QUOTA_EXCEEDED:
            return await self._resolve_checkout_limit(patron, context or {})

        elif error_code == ErrorCode.ITEM_NOT_AVAILABLE:
            return await self._resolve_item_not_available(item, context or {})

        elif error_code == ErrorCode.PATRON_BLOCKED:
            return await self._resolve_patron_blocked(patron)

        elif error_code == ErrorCode.PATRON_DECEASED:
            return await self._resolve_patron_deceased()

        elif error_code == ErrorCode.PATRON_ACCOUNT_SUSPENDED:
            return await self._resolve_patron_suspended(patron)

        elif error_code == ErrorCode.ITEM_CHECKED_OUT:
            return await self._resolve_item_checked_out(item)

        return None

    async def _resolve_item_on_hold(self, item: Optional[CatalogItem]) -> ProblemDetails:
        if not item:
            return ProblemDetails(
                problem_type="on_hold",
                title="Item is on hold",
                description="This item is reserved for another patron.",
                context={},
                solutions=["Return this item or choose a different copy"],
                actions=[
                    ResolutionAction(
                        action_type="override",
                        label="Check Out Anyway",
                        description="Override hold and proceed with checkout. Hold will be cancelled.",
                    )
                ],
            )

        # Get hold info
        stmt = select(Hold).where(
            (Hold.item_id == item.id) & (Hold.status == HoldStatus.ready)
        )
        hold = (await self.session.execute(stmt)).scalars().first()

        hold_patron_name = "Unknown patron"
        if hold and hold.user:
            hold_patron_name = f"{hold.user.first_name} {hold.user.last_name}".strip()

        return ProblemDetails(
            problem_type="on_hold",
            title=f"This item is ON HOLD for {hold_patron_name}",
            description=f"'{item.title}' is reserved for another patron and cannot be checked out at this time.",
            context={
                "item_id": item.id,
                "item_title": item.title,
                "hold_patron": hold_patron_name,
                "hold_position": hold.position if hold else None,
            },
            solutions=[
                "Suggest the patron place a hold when available",
                "Look for another copy of this item",
            ],
            actions=[
                ResolutionAction(
                    action_type="override",
                    label="Check Out Anyway",
                    description="Override hold for this patron. The next hold will be processed when item is returned.",
                    icon="lock-open",
                )
            ],
            severity="warning",
        )

    async def _resolve_patron_has_outstanding_fine(
        self, patron: User, context: Dict[str, Any]
    ) -> ProblemDetails:
        # Get fine details
        stmt = select(Fine).where(
            (Fine.user_id == patron.id) & (Fine.status == FineStatus.UNPAID)
        )
        result = await self.session.execute(stmt)
        fines = result.scalars().all()

        total_unpaid = sum(f.balance for f in fines if f.balance > 0)
        overdue_count = context.get("overdue_count", 0)
        days_overdue = context.get("days_overdue_max", 0)

        if overdue_count > 0:
            return ProblemDetails(
                problem_type="overdue_items",
                title=f"Patron has {overdue_count} overdue item(s)",
                description=f"{patron.first_name} has {overdue_count} item(s) overdue for {days_overdue} days. Library policy blocks new checkouts until overdue items are returned.",
                context={
                    "patron_id": patron.id,
                    "overdue_count": overdue_count,
                    "days_overdue_max": days_overdue,
                },
                solutions=[
                    f"Ask patron to return the {overdue_count} overdue item(s)",
                    "Extend due dates if appropriate",
                ],
                actions=[
                    ResolutionAction(
                        action_type="override",
                        label="Override Overdue Block",
                        description="Allow checkout despite overdue items. Patron should still return overdue items.",
                        icon="exclamation-triangle",
                    ),
                    ResolutionAction(
                        action_type="renew_items",
                        label="Renew Overdue Items",
                        description="Extend due dates for all overdue items.",
                        icon="refresh",
                    ),
                ],
                severity="error",
            )
        elif total_unpaid > 0:
            return ProblemDetails(
                problem_type="fine_balance",
                title=f"Patron has ${total_unpaid:.2f} in fines",
                description=f"{patron.first_name} has an outstanding fine balance of ${total_unpaid:.2f}. Payment is required before checkout.",
                context={
                    "patron_id": patron.id,
                    "total_unpaid": float(total_unpaid),
                    "fine_count": len(fines),
                    "fines": [
                        {
                            "id": f.id,
                            "type": str(f.fine_type),
                            "amount": float(f.amount),
                            "balance": float(f.balance),
                        }
                        for f in fines
                    ],
                },
                solutions=[
                    f"Collect ${total_unpaid:.2f} payment",
                    "Waive fines if appropriate",
                    "Set up payment plan",
                ],
                actions=[
                    ResolutionAction(
                        action_type="pay",
                        label="Collect Payment",
                        description=f"Record payment of fine (${total_unpaid:.2f})",
                        required_input="payment_amount",
                        icon="credit-card",
                    ),
                    ResolutionAction(
                        action_type="waive",
                        label="Waive Fines",
                        description=f"Forgive the ${total_unpaid:.2f} fine balance",
                        required_input="waive_reason",
                        icon="gift",
                    ),
                    ResolutionAction(
                        action_type="override",
                        label="Override Fine Block",
                        description="Allow checkout despite unpaid fines.",
                        icon="lock-open",
                    ),
                ],
                severity="error",
            )

        return ProblemDetails(
            problem_type="fine_block",
            title="Fine block",
            description="Patron has outstanding fines blocking checkout",
            context={},
            solutions=["Collect payment or waive fines"],
            actions=[],
            severity="warning",
        )

    async def _resolve_card_expired(
        self, patron: User, context: Dict[str, Any]
    ) -> ProblemDetails:
        days_expired = context.get("days_expired", 0)
        expires_at = patron.card_expires_at

        if days_expired > 0:
            desc = f"{patron.first_name}'s library card expired {days_expired} days ago."
        else:
            desc = f"{patron.first_name}'s library card expired."

        return ProblemDetails(
            problem_type="card_expired",
            title=f"Card expired {days_expired} days ago",
            description=desc,
            context={
                "patron_id": patron.id,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "days_expired": days_expired,
            },
            solutions=[
                "Renew library card with valid ID",
                "Override if patron ID verified",
            ],
            actions=[
                ResolutionAction(
                    action_type="renew_card",
                    label="Renew Card Now",
                    description="Extend card expiration date",
                    icon="id-card",
                ),
                ResolutionAction(
                    action_type="override",
                    label="Verify & Proceed",
                    description="Override expired card (staff verifies ID)",
                    required_input="verification_notes",
                    icon="shield-check",
                ),
            ],
            severity="warning",
        )

    async def _resolve_checkout_limit(
        self, patron: User, context: Dict[str, Any]
    ) -> ProblemDetails:
        current_count = context.get("current_count", 0)
        max_checkouts = context.get("max_checkouts", 10)

        # Get active checkouts to show what they have. Eager-load the item:
        # a lazy co.item on the async session raises MissingGreenlet, which
        # turned the friendly at-limit message into a 500.
        stmt = (
            select(Checkout)
            .options(selectinload(Checkout.item))
            .where(
                (Checkout.user_id == patron.id) & (Checkout.returned_at.is_(None))
            )
        )
        result = await self.session.execute(stmt)
        checkouts = result.scalars().all()

        items_info = []
        for co in checkouts:
            if co.item:
                due_date = ensure_utc(co.due_date)
                items_info.append(
                    {
                        "checkout_id": co.id,
                        "item_title": co.item.title,
                        "due_date": due_date.isoformat(),
                        "days_until_due": (due_date - utc_now()).days,
                        "is_overdue": due_date < utc_now(),
                    }
                )

        return ProblemDetails(
            problem_type="checkout_limit",
            title=f"At checkout limit ({current_count}/{max_checkouts})",
            description=f"{patron.first_name} has {current_count} items checked out, which is the maximum of {max_checkouts}. An item must be returned to check out new ones.",
            context={
                "patron_id": patron.id,
                "current_count": current_count,
                "max_checkouts": max_checkouts,
                "items_checked_out": items_info,
            },
            solutions=[
                "Patron returns an item first",
                "Swap an item (return one, check out new one)",
                "Increase checkout limit if appropriate",
            ],
            actions=[
                ResolutionAction(
                    action_type="swap_item",
                    label="Which item to return?",
                    description="Patron returns an item, check out the new one in same transaction",
                    required_input="item_to_return_id",
                    icon="arrows-h",
                ),
                ResolutionAction(
                    action_type="override",
                    label="Allow Anyway",
                    description="Temporarily allow exceeding checkout limit",
                    required_input="override_reason",
                    icon="plus",
                ),
            ],
            severity="warning",
        )

    async def _resolve_item_not_available(
        self, item: Optional[CatalogItem], context: Dict[str, Any]
    ) -> ProblemDetails:
        if not item:
            return ProblemDetails(
                problem_type="item_not_available",
                title="Item is not available",
                description="The requested item cannot be checked out at this time.",
                context={},
                solutions=[],
                actions=[],
                severity="warning",
            )

        status = str(item.status) if item.status else "unknown"

        return ProblemDetails(
            problem_type="item_missing" if status == "lost" else "item_not_available",
            title=f"Item is {status.upper()}",
            description=f"'{item.title}' is marked as {status} in the system and cannot be checked out.",
            context={
                "item_id": item.id,
                "item_title": item.title,
                "status": status,
            },
            solutions=[
                "Check if item was misplaced" if status == "lost" else None,
                "Check physical condition if status is incorrect",
                "Update item status if needed",
            ],
            actions=[
                ResolutionAction(
                    action_type="update_status",
                    label="Item is available - Update status",
                    description=f"Change status from {status} to available",
                    icon="check-circle",
                ),
                ResolutionAction(
                    action_type="override",
                    label="Check Out Anyway",
                    description="Proceed despite item status (staff override)",
                    icon="lock-open",
                ),
            ],
            severity="error" if status == "lost" else "warning",
        )

    async def _resolve_item_checked_out(self, item: Optional[CatalogItem]) -> ProblemDetails:
        if not item:
            return ProblemDetails(
                problem_type="item_checked_out",
                title="Item is checked out",
                description="This item is currently checked out to another patron.",
                context={},
                solutions=[],
                actions=[],
            )

        # Find who has it checked out
        stmt = select(Checkout).where(
            (Checkout.item_id == item.id) & (Checkout.returned_at.is_(None))
        )
        checkout = (await self.session.execute(stmt)).scalars().first()

        checked_out_to = "Unknown patron"
        due_date = None
        if checkout and checkout.user:
            checked_out_to = f"{checkout.user.first_name} {checkout.user.last_name}".strip()
            due_date = checkout.due_date

        days_until_due = None
        if due_date:
            days_until_due = (due_date - utc_now()).days

        return ProblemDetails(
            problem_type="item_checked_out",
            title=f"Checked out to {checked_out_to}",
            description=f"'{item.title}' is currently checked out to {checked_out_to}.",
            context={
                "item_id": item.id,
                "item_title": item.title,
                "checked_out_to": checked_out_to,
                "due_date": due_date.isoformat() if due_date else None,
                "days_until_due": days_until_due,
            },
            solutions=[
                "Place a hold on the item for this patron",
                "Check if other copies are available",
                "Suggest patron wait until due date",
            ],
            actions=[
                ResolutionAction(
                    action_type="place_hold",
                    label="Place Hold for Patron",
                    description=f"Add patron to hold queue. Item due back in {days_until_due} days.",
                    icon="bookmark",
                ),
                ResolutionAction(
                    action_type="override",
                    label="Check Out Anyway",
                    description="Proceed despite item being checked out (staff override)",
                    icon="lock-open",
                ),
            ],
            severity="info",
        )

    async def _resolve_patron_blocked(self, patron: User) -> ProblemDetails:
        block_reason = patron.block_reason or "No reason recorded"
        blocked_date = patron.blocked_at

        return ProblemDetails(
            problem_type="patron_blocked",
            title="Patron account is BLOCKED",
            description=f"{patron.first_name}'s account has been blocked. Reason: {block_reason}",
            context={
                "patron_id": patron.id,
                "block_reason": block_reason,
                "blocked_at": blocked_date.isoformat() if blocked_date else None,
            },
            solutions=[
                "Address the blocking reason (usually patron request or legal issue)",
                "Obtain supervisor approval to unblock",
            ],
            actions=[
                ResolutionAction(
                    action_type="contact_supervisor",
                    label="Contact Supervisor",
                    description="This requires management approval",
                    icon="user-tie",
                )
            ],
            severity="critical",
        )

    async def _resolve_patron_deceased(self) -> ProblemDetails:
        return ProblemDetails(
            problem_type="patron_deceased",
            title="Patron account is DECEASED",
            description="Circulation operations are blocked for this account. Contact library management for estate-related matters.",
            context={},
            solutions=[
                "Contact library management",
                "Handle items per estate/family instructions",
            ],
            actions=[
                ResolutionAction(
                    action_type="contact_management",
                    label="Contact Management",
                    description="This requires management handling",
                    icon="phone",
                )
            ],
            severity="critical",
        )

    async def _resolve_patron_suspended(self, patron: User) -> ProblemDetails:
        suspension_reason = patron.suspension_reason or "Overdue items"
        suspended_until = patron.suspended_until

        days_remaining = None
        if suspended_until:
            days_remaining = (suspended_until - utc_now()).days

        return ProblemDetails(
            problem_type="patron_suspended",
            title="Patron account is SUSPENDED",
            description=f"{patron.first_name}'s account is suspended: {suspension_reason}",
            context={
                "patron_id": patron.id,
                "suspension_reason": suspension_reason,
                "suspended_until": suspended_until.isoformat() if suspended_until else None,
                "days_remaining": days_remaining,
            },
            solutions=[
                "Resolve the suspension reason (return overdue items, etc.)",
                f"Wait until {suspended_until.strftime('%B %d') if suspended_until else 'unknown'}",
            ],
            actions=[
                ResolutionAction(
                    action_type="override",
                    label="Override Suspension",
                    description="Allow checkout despite suspension (staff override)",
                    required_input="override_reason",
                    icon="lock-open",
                ),
                ResolutionAction(
                    action_type="unsuspend",
                    label="Clear Suspension",
                    description="Mark suspension as resolved",
                    icon="check",
                ),
            ],
            severity="error",
        )


def problem_details_to_dict(problem: ProblemDetails) -> Dict[str, Any]:
    return {
        "problem_type": problem.problem_type,
        "title": problem.title,
        "description": problem.description,
        "context": problem.context,
        "solutions": [s for s in problem.solutions if s],  # Filter None values
        "actions": [
            {
                "action_type": action.action_type,
                "label": action.label,
                "description": action.description,
                "required_input": action.required_input,
                "icon": action.icon,
            }
            for action in problem.actions
        ],
        "severity": problem.severity,
    }
