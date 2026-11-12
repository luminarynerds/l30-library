# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

# From time_config - circulation suspension thresholds
from ..core.time_config import TimeConfig
# From financial_config - fine thresholds
from ..core.financial_config import FinancialConfig
from ..core.error_codes import ErrorCode
from ..core.exceptions import ConflictError
from ..models.circulation import Checkout, CheckoutStatus
from ..models.fine import (
    CheckClearanceStatus, Fine, FinePaymentHistory, FineStatus, FineType, PaymentMethod,
)
from ..models.user import PatronStatus, User
from app.core.datetime_utils import utc_now
from app.services import operations_audit_service as ops_audit
from app.models.operations_audit_log import OperationType

logger = get_logger(__name__)


# Configuration constants for suspension thresholds (From time_config and financial_config)
_time_config = TimeConfig()
OVERDUE_SUSPENSION_DAYS = _time_config.circulation.overdue_suspension_days  # From time_config.circulation
FINE_SUSPENSION_THRESHOLD = Decimal(str(FinancialConfig.FINE_MAX_PER_USER))  # From financial_config


# =============================================================================
# SUSPENSION CHECKING
# =============================================================================


async def check_patron_suspension_status(
    patron: User, db: AsyncSession
) -> Tuple[bool, Optional[str], Optional[ErrorCode]]:
    # Check if patron is deceased
    if patron.patron_status == PatronStatus.DECEASED:
        return False, "This account belongs to a deceased patron. All circulation operations are blocked.", ErrorCode.PATRON_DECEASED

    # Check if patron is blocked (administrative)
    if patron.patron_status == PatronStatus.BLOCKED:
        reason = patron.block_reason or "Account is blocked by library staff"
        return False, reason, ErrorCode.PATRON_BLOCKED

    # Check if patron is suspended
    if patron.patron_status == PatronStatus.SUSPENDED:
        # First check if suspension should be auto-lifted
        if patron.should_lift_suspension():
            # Auto-lift the suspension
            await lift_suspension(patron, db, auto=True)
            return True, None, None

        reason = patron.suspension_reason or "Account is temporarily suspended"
        if patron.suspended_until:
            until_str = patron.suspended_until.strftime("%B %d, %Y")
            reason = f"{reason}. Suspension expires on {until_str}."
        return False, reason, ErrorCode.PATRON_ACCOUNT_SUSPENDED

    # Check legacy is_active flag for backwards compatibility
    if not patron.is_active:
        return False, "Account is inactive", ErrorCode.PATRON_BLOCKED

    return True, None, None


async def check_and_auto_suspend_for_overdue(
    user_id: int, db: AsyncSession
) -> Tuple[bool, int]:
    threshold_date = utc_now() - timedelta(days=OVERDUE_SUSPENSION_DAYS)

    # Count items overdue beyond threshold
    stmt = select(func.count(Checkout.id)).where(
        and_(
            Checkout.user_id == user_id,
            Checkout.status == CheckoutStatus.overdue,
            Checkout.due_date < threshold_date,
            Checkout.returned_at.is_(None),
        )
    )

    result = await db.execute(stmt)
    overdue_count = result.scalar() or 0

    if overdue_count == 0:
        return True, 0

    # Get user to check current status and potentially suspend
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        return True, 0

    # If user is active, auto-suspend them
    if user.patron_status == PatronStatus.ACTIVE:
        await suspend_patron(
            patron=user,
            db=db,
            reason=f"Automatic suspension: {overdue_count} item(s) overdue for more than {OVERDUE_SUSPENSION_DAYS} days",
            suspended_by_id=None,  # Auto-suspension
            suspended_until=None,  # No auto-expiry; lifts when items returned
        )

    logger.info(
        f"Circulation blocked for user {user_id}: {overdue_count} item(s) "
        f"overdue for more than {OVERDUE_SUSPENSION_DAYS} days"
    )

    return False, overdue_count


async def check_and_auto_suspend_for_fines(
    user_id: int, db: AsyncSession, threshold: Optional[Decimal] = None
) -> Tuple[bool, Decimal]:
    if threshold is None:
        threshold = FINE_SUSPENSION_THRESHOLD

    # Calculate unpaid fine balance
    stmt = select(
        func.coalesce(func.sum(Fine.amount - Fine.amount_paid), Decimal("0.00"))
    ).where(
        Fine.user_id == user_id,
        Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
    )

    result = await db.execute(stmt)
    balance = result.scalar() or Decimal("0.00")

    if balance < threshold:
        return True, balance

    # Get user to check current status and potentially suspend
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        return True, balance

    # If user is active, auto-suspend them
    if user.patron_status == PatronStatus.ACTIVE:
        await suspend_patron(
            patron=user,
            db=db,
            reason=f"Automatic suspension: Outstanding fines of ${balance:.2f} exceed ${threshold:.2f} threshold",
            suspended_by_id=None,  # Auto-suspension
            suspended_until=None,  # No auto-expiry; lifts when fines paid
        )

    logger.info(
        f"Circulation blocked for user {user_id}: fines ${balance:.2f} exceed ${threshold:.2f}"
    )

    return False, balance


# =============================================================================
# SUSPENSION MANAGEMENT
# =============================================================================


async def suspend_patron(
    patron: User,
    db: AsyncSession,
    reason: str,
    suspended_by_id: Optional[int] = None,
    suspended_until: Optional[datetime] = None,
) -> User:
    if patron.patron_status == PatronStatus.DECEASED:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Cannot suspend a deceased patron account"
        )

    if patron.patron_status == PatronStatus.BLOCKED:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Cannot suspend an already blocked account. Unblock first."
        )

    now = utc_now()

    old_status = str(patron.patron_status) if patron.patron_status else "active"

    patron.patron_status = PatronStatus.SUSPENDED
    patron.suspension_reason = reason
    patron.suspended_at = now
    patron.suspended_by_id = suspended_by_id
    patron.suspended_until = suspended_until
    patron.is_active = False  # Keep backwards compatibility

    logger.info(
        f"Patron {patron.id} suspended",
        extra={
            "patron_id": patron.id,
            "reason": reason,
            "suspended_by": suspended_by_id,
            "auto": suspended_by_id is None,
            "until": suspended_until.isoformat() if suspended_until else None,
        }
    )

    await ops_audit.log_patron_status_change(
        db, patron=patron, old_status=old_status, new_status="suspended",
        operation_type=OperationType.PATRON_SUSPENDED,
        staff=None, reason=reason,
    )

    return patron


async def lift_suspension(
    patron: User,
    db: AsyncSession,
    lifted_by_id: Optional[int] = None,
    auto: bool = False,
) -> User:
    if patron.patron_status != PatronStatus.SUSPENDED:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Patron is not currently suspended"
        )

    patron.patron_status = PatronStatus.ACTIVE
    patron.suspension_reason = None
    patron.suspended_at = None
    patron.suspended_by_id = None
    patron.suspended_until = None
    patron.is_active = True  # Keep backwards compatibility

    logger.info(
        f"Suspension lifted for patron {patron.id}",
        extra={
            "patron_id": patron.id,
            "lifted_by": lifted_by_id,
            "auto": auto,
        }
    )

    await ops_audit.log_patron_status_change(
        db, patron=patron, old_status="suspended", new_status="active",
        operation_type=OperationType.PATRON_UNSUSPENDED,
        reason="Auto-lifted" if auto else None,
    )

    return patron


async def block_patron(
    patron: User,
    db: AsyncSession,
    reason: str,
    blocked_by_id: int,
) -> User:
    if patron.patron_status == PatronStatus.DECEASED:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Cannot block a deceased patron account"
        )

    now = utc_now()

    old_status = str(patron.patron_status) if patron.patron_status else "active"

    patron.patron_status = PatronStatus.BLOCKED
    patron.block_reason = reason
    patron.blocked_at = now
    patron.blocked_by_id = blocked_by_id
    patron.is_active = False  # Keep backwards compatibility

    # Clear any suspension info since we're now blocking
    patron.suspension_reason = None
    patron.suspended_at = None
    patron.suspended_by_id = None
    patron.suspended_until = None

    logger.info(
        f"Patron {patron.id} blocked",
        extra={
            "patron_id": patron.id,
            "reason": reason,
            "blocked_by": blocked_by_id,
        }
    )

    await ops_audit.log_patron_status_change(
        db, patron=patron, old_status=old_status, new_status="blocked",
        operation_type=OperationType.PATRON_BLOCKED,
        reason=reason,
    )

    return patron


async def unblock_patron(
    patron: User,
    db: AsyncSession,
    unblocked_by_id: int,
) -> User:
    if patron.patron_status not in [PatronStatus.BLOCKED, PatronStatus.SUSPENDED]:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Patron is not currently blocked or suspended"
        )

    old_status = str(patron.patron_status) if patron.patron_status else "blocked"

    patron.patron_status = PatronStatus.ACTIVE
    patron.block_reason = None
    patron.blocked_at = None
    patron.blocked_by_id = None
    patron.suspension_reason = None
    patron.suspended_at = None
    patron.suspended_by_id = None
    patron.suspended_until = None
    patron.is_active = True  # Keep backwards compatibility

    logger.info(
        f"Patron {patron.id} unblocked",
        extra={
            "patron_id": patron.id,
            "unblocked_by": unblocked_by_id,
        }
    )

    await ops_audit.log_patron_status_change(
        db, patron=patron, old_status=old_status, new_status="active",
        operation_type=OperationType.PATRON_UNBLOCKED,
    )

    return patron


# =============================================================================
# AUTO-LIFT SUSPENSION CHECKS
# =============================================================================


async def check_and_lift_on_return(
    user_id: int, db: AsyncSession
) -> Optional[User]:
    # Get user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user or user.patron_status != PatronStatus.SUSPENDED:
        return None

    # Check if suspension was for overdue items
    if not user.suspension_reason or "overdue" not in user.suspension_reason.lower():
        return None

    # Check if there are still long-overdue items
    threshold_date = utc_now() - timedelta(days=OVERDUE_SUSPENSION_DAYS)
    stmt = select(func.count(Checkout.id)).where(
        and_(
            Checkout.user_id == user_id,
            Checkout.status == CheckoutStatus.overdue,
            Checkout.due_date < threshold_date,
            Checkout.returned_at.is_(None),
        )
    )

    result = await db.execute(stmt)
    overdue_count = result.scalar() or 0

    if overdue_count == 0:
        # All long-overdue items returned, lift suspension
        await lift_suspension(user, db, auto=True)
        return user

    return None


async def check_and_lift_on_fine_payment(
    user_id: int, db: AsyncSession, threshold: Optional[Decimal] = None
) -> Optional[User]:
    if threshold is None:
        threshold = FINE_SUSPENSION_THRESHOLD

    # Get user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user or user.patron_status != PatronStatus.SUSPENDED:
        return None

    # Check if suspension was for fines
    if not user.suspension_reason or "fine" not in user.suspension_reason.lower():
        return None

    # Check current fine balance
    stmt = select(
        func.coalesce(func.sum(Fine.amount - Fine.amount_paid), Decimal("0.00"))
    ).where(
        Fine.user_id == user_id,
        Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
    )

    result = await db.execute(stmt)
    balance = result.scalar() or Decimal("0.00")

    if balance < threshold:
        # Before lifting, check if any pending check payments exist for this user.
        # If a check hasn't cleared yet, don't lift the suspension — the balance
        # might bounce back up when the check is marked as bounced.
        pending_checks = await has_pending_check_payments(user_id, db)
        if pending_checks:
            logger.info(
                f"Suspension NOT auto-lifted for user {user_id}: "
                f"pending check payment(s) awaiting clearance"
            )
            return None

        # Fines below threshold, lift suspension
        await lift_suspension(user, db, auto=True)
        return user

    return None


async def has_pending_check_payments(user_id: int, db: AsyncSession) -> bool:
    stmt = select(func.count(FinePaymentHistory.id)).where(
        FinePaymentHistory.user_id == user_id,
        FinePaymentHistory.payment_method == PaymentMethod.check,
        FinePaymentHistory.check_clearance_status == CheckClearanceStatus.pending,
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    return count > 0


async def handle_bounced_check(
    payment_id: int,
    db: AsyncSession,
    staff_id: int,
) -> FinePaymentHistory:
    # Get the payment record
    result = await db.execute(
        select(FinePaymentHistory)
        .where(FinePaymentHistory.id == payment_id)
        .with_for_update()
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Payment record not found"
        )

    if payment.payment_method != PaymentMethod.check:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Only check payments can be marked as bounced"
        )

    if payment.check_clearance_status == CheckClearanceStatus.bounced:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="This check has already been marked as bounced"
        )

    if payment.check_clearance_status == CheckClearanceStatus.cleared:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Cannot bounce a check that has already cleared"
        )

    now = utc_now()

    # Mark the check as bounced
    payment.check_clearance_status = CheckClearanceStatus.bounced
    payment.check_bounced_at = now
    payment.check_bounced_by_id = staff_id
    payment.notes = (payment.notes or "") + f"\n[{now.isoformat()}] CHECK BOUNCED - reversed by staff {staff_id}"

    # Reverse the payment on the fine
    fine_result = await db.execute(
        select(Fine).where(Fine.id == payment.fine_id).with_for_update()
    )
    fine = fine_result.scalar_one_or_none()

    if fine:
        fine.amount_paid = max(Decimal("0.00"), fine.amount_paid - payment.amount)
        if fine.amount_paid <= Decimal("0.00"):
            fine.status = FineStatus.unpaid
            fine.paid_at = None
        else:
            fine.status = FineStatus.partial

        fine.notes = (fine.notes or "") + f"\n[{now.isoformat()}] Payment reversed: check bounced (receipt: {payment.receipt_number})"

    # Re-suspend the patron if they were unsuspended
    if payment.user_id:
        user_result = await db.execute(
            select(User).where(User.id == payment.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user and user.patron_status == PatronStatus.ACTIVE:
            await suspend_patron(
                patron=user,
                db=db,
                reason=f"Automatic suspension: Check payment bounced (receipt: {payment.receipt_number})",
                suspended_by_id=staff_id,
                suspended_until=None,
            )

    logger.warning(
        f"Check bounced for payment {payment_id}",
        extra={
            "payment_id": payment_id,
            "fine_id": payment.fine_id,
            "user_id": payment.user_id,
            "amount": str(payment.amount),
            "staff_id": staff_id,
        }
    )

    return payment


async def handle_check_cleared(
    payment_id: int,
    db: AsyncSession,
    staff_id: int,
) -> FinePaymentHistory:
    result = await db.execute(
        select(FinePaymentHistory)
        .where(FinePaymentHistory.id == payment_id)
        .with_for_update()
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Payment record not found"
        )

    if payment.payment_method != PaymentMethod.check:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="Only check payments can be marked as cleared"
        )

    if payment.check_clearance_status == CheckClearanceStatus.cleared:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="This check has already been marked as cleared"
        )

    now = utc_now()
    payment.check_clearance_status = CheckClearanceStatus.cleared
    payment.check_cleared_at = now

    logger.info(
        f"Check cleared for payment {payment_id}",
        extra={"payment_id": payment_id, "user_id": payment.user_id, "staff_id": staff_id}
    )

    # Now that the check has cleared, re-evaluate suspension
    if payment.user_id:
        await check_and_lift_on_fine_payment(payment.user_id, db)

    return payment


async def process_expired_suspensions(db: AsyncSession) -> int:
    now = utc_now()

    # Find all suspended users whose suspended_until date has passed
    stmt = (
        select(User)
        .where(
            User.patron_status == PatronStatus.SUSPENDED,
            User.suspended_until.isnot(None),
            User.suspended_until <= now,
        )
        .with_for_update(skip_locked=True)
    )

    result = await db.execute(stmt)
    expired_users = result.scalars().all()

    lifted_count = 0
    for user in expired_users:
        try:
            await lift_suspension(user, db, auto=True)
            lifted_count += 1
        except Exception as e:
            logger.error(
                f"Error lifting expired suspension for user {user.id}: {e}",
                exc_info=True
            )

    # Commit the changes to persist lifted suspensions
    if lifted_count > 0:
        await db.commit()
        logger.info(
            f"Auto-lifted {lifted_count} expired suspension(s)",
            extra={"lifted_count": lifted_count}
        )

    return lifted_count
