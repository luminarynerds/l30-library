# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
from app.core.logging import get_logger
from decimal import Decimal
from math import ceil
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select, update, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# From circulation_config - uses time_config and financial_config
from ..core.circulation_config import OVERDUE_GRACE_HOURS
# From time_config - for overdue thresholds
from ..core.time_config import TimeConfig
from ..models.circulation import Checkout, CheckoutStatus
from ..models.fine import Fine, FineStatus, FineType
from ..models.multi_branch import BranchClosure, BranchItemCopy
from ..models.permission import RoleSettings
from ..models.user import User
from app.core.datetime_utils import utc_now
from . import operations_audit_service as ops_audit
from .reports.cache_invalidator import invalidate_financial_reports

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Cents <-> Dollars conversion helpers (domain <-> service/model boundary)
# ---------------------------------------------------------------------------

def cents_to_dollars(cents: int) -> Decimal:
    return Decimal(cents) / Decimal(100)


def dollars_to_cents(dollars: Decimal) -> int:
    return int((dollars * Decimal(100)).to_integral_value())


# Configuration constants (these can be overridden by FinePolicy)
# FINE-FREE LIBRARY: Late fees are $0.00
# Lost/damaged items still incur replacement costs (handled separately)
# From time_config and financial_config
_time_config = TimeConfig()
FINE_FREE_MODE = True  # Primary switch for fine-free operation
OVERDUE_FINE_PER_DAY = Decimal("0.00")  # No late fees - we're fine-free!

# Accountability: Items overdue more than this many days will pause checkout privileges
# This is a soft block (not monetary) - returns item and privileges are restored
# From time_config.circulation
OVERDUE_CHECKOUT_PAUSE_DAYS = _time_config.circulation.overdue_suspension_days


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def count_closure_days(
    db: AsyncSession,
    range_start: date,
    range_end: date,
    branch_id: int | None = None,
) -> int:
    if range_end < range_start:
        return 0

    filters = [BranchClosure.is_system_wide.is_(True)]
    if branch_id is not None:
        filters.append(BranchClosure.branch_id == branch_id)

    result = await db.execute(
        select(BranchClosure).where(
            or_(*filters),
            # Only load closures that overlap the overdue window.
            # Annual closures are exempt from date filtering because their
            # stored dates are templates projected onto each year in Python.
            or_(
                BranchClosure.is_annual.is_(True),
                and_(
                    BranchClosure.end_date >= range_start,
                    BranchClosure.start_date <= range_end,
                ),
            ),
        )
    )
    closures = result.scalars().all()

    closed: set[date] = set()
    one_day = timedelta(days=1)

    for closure in closures:
        if closure.start_date is None or closure.end_date is None:
            continue
        if closure.is_annual:
            # Project month/day onto each year that intersects the range.
            start_md = (closure.start_date.month, closure.start_date.day)
            end_md = (closure.end_date.month, closure.end_date.day)
            for year in range(range_start.year, range_end.year + 1):
                try:
                    start_dt = date(year, *start_md)
                    end_dt = date(year, *end_md)
                except ValueError:
                    # Feb 29 in a non-leap year, etc.
                    continue
                # Annual closures may wrap year-end (Dec 31 -> Jan 2); if so,
                # treat as two segments.
                if end_dt < start_dt:
                    _accumulate_dates(closed, start_dt, date(year, 12, 31),
                                      range_start, range_end, one_day)
                    with contextlib.suppress(ValueError):
                        _accumulate_dates(closed, date(year, 1, 1), end_dt,
                                          range_start, range_end, one_day)
                else:
                    _accumulate_dates(closed, start_dt, end_dt,
                                      range_start, range_end, one_day)
        else:
            _accumulate_dates(closed, closure.start_date, closure.end_date,
                              range_start, range_end, one_day)

    return len(closed)


def _accumulate_dates(
    sink: set[date],
    span_start: date,
    span_end: date,
    range_start: date,
    range_end: date,
    one_day: timedelta,
) -> None:
    cur = max(span_start, range_start)
    stop = min(span_end, range_end)
    while cur <= stop:
        sink.add(cur)
        cur += one_day


async def _resolve_checkout_branch_id(
    checkout: Checkout, db: AsyncSession
) -> int | None:
    """Best-effort current branch of the checked-out copy, for closure-day
    filtering. Returns None (system-wide-only) when the copy isn't tracked
    to a branch -- e.g. a single-branch library, or a checkout with no
    item_copy_id.
    """
    if checkout.item_copy_id is None:
        return None
    result = await db.execute(
        select(BranchItemCopy.current_branch_id).where(
            BranchItemCopy.item_copy_id == checkout.item_copy_id
        )
    )
    return result.scalar_one_or_none()


async def check_and_create_overdue_fine(
    checkout: Checkout, db: AsyncSession, user: User | None = None
) -> Fine | None:
    if checkout.status not in [CheckoutStatus.active, CheckoutStatus.overdue]:
        return None

    now = utc_now()
    due_date = ensure_utc(checkout.due_date)

    if due_date >= now:
        return None

    # Calculate overdue time with optional grace period
    overdue_delta = now - due_date
    overdue_hours = overdue_delta.total_seconds() / 3600

    # Apply grace period if configured
    if overdue_hours <= OVERDUE_GRACE_HOURS:
        return None

    # Round up partial days (any part of a day after grace period counts as full day)
    overdue_days = ceil((overdue_hours - OVERDUE_GRACE_HOURS) / 24)
    if overdue_days <= 0:
        return None

    # Don't fine for library-closed days. Range is the calendar window the
    # patron could have returned the item: from the day after the due date
    # through today (or the last day of the overdue window, equivalently).
    # Counts system-wide closures plus closures at the checked-out copy's
    # own branch (falls back to system-wide-only if the branch can't be
    # resolved).
    branch_id = await _resolve_checkout_branch_id(checkout, db)
    closure_days = await count_closure_days(
        db,
        range_start=due_date.date() + timedelta(days=1),
        range_end=now.date(),
        branch_id=branch_id,
    )
    if closure_days:
        overdue_days = max(0, overdue_days - closure_days)
        if overdue_days <= 0:
            return None

    # Get user if not provided
    if user is None:
        user_result = await db.execute(select(User).where(User.id == checkout.user_id))
        user = user_result.scalar_one_or_none()

    if not user:
        return None

    # Check if user's role uses reading minutes instead of fines
    settings_result = await db.execute(
        select(RoleSettings).where(RoleSettings.role == user.role)
    )
    settings = settings_result.scalar_one_or_none()

    if settings and settings.use_reading_minutes:
        # Add reading minutes instead of monetary fine
        # Only add minutes for NEW overdue days (prevents duplicate additions)
        already_processed = checkout.last_overdue_days_processed or 0
        new_days = overdue_days - already_processed

        if new_days > 0:
            minutes_to_add = new_days * settings.minutes_per_day_overdue
            # Use atomic increment with cap to prevent lost updates from concurrent operations
            # This uses a SQL expression that atomically updates the value
            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(
                    reading_minutes_owed=func.least(
                        User.reading_minutes_owed + minutes_to_add,
                        settings.max_reading_minutes_owed
                    )
                )
            )
            # Track that we've processed these days
            checkout.last_overdue_days_processed = overdue_days

        checkout.status = CheckoutStatus.overdue
        return None  # No monetary fine created

    # Check if user is fine-exempt
    if settings and settings.fine_exempt:
        return None

    # FINE-FREE MODE: Don't create monetary fines for overdue items
    # We still mark the checkout as overdue for tracking/accountability
    checkout.status = CheckoutStatus.overdue

    if FINE_FREE_MODE:
        # In fine-free mode, we don't create fines for late returns
        # Accountability is handled through checkout pauses (see check_overdue_block)
        logger.debug(
            f"Fine-free mode: Skipping fine creation for checkout {checkout.id} "
            f"(overdue {overdue_days} days)"
        )
        return None

    # Legacy fine creation (only runs if FINE_FREE_MODE is False)
    # Check if fine already exists for this checkout
    existing_fine_result = await db.execute(
        select(Fine).where(
            Fine.checkout_id == checkout.id, Fine.fine_type == FineType.overdue
        )
    )
    existing_fine = existing_fine_result.scalar_one_or_none()

    # new_amount is Decimal (dollars) - suitable for the Fine model's Numeric column.
    # If sourcing from a domain event with cent amounts, use cents_to_dollars() instead.
    new_amount = OVERDUE_FINE_PER_DAY * overdue_days

    if existing_fine:
        # Update existing fine if overdue period has increased
        # Handle partial payments: only update if new amount exceeds current total
        # and fine is not fully paid
        if new_amount > existing_fine.amount and existing_fine.status in [
            FineStatus.unpaid,
            FineStatus.partial,
        ]:
            existing_fine.amount = new_amount
            existing_fine.description = f"Overdue by {overdue_days} day(s)"
            # Update status based on payment state
            if existing_fine.amount_paid > 0:
                existing_fine.status = FineStatus.partial
        return existing_fine

    fine = Fine(
        user_id=checkout.user_id,
        checkout_id=checkout.id,
        amount=new_amount,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        description=f"Overdue by {overdue_days} day(s)",
    )
    db.add(fine)
    try:
        await db.flush()
    except IntegrityError:
        # Concurrent request already inserted a fine for this checkout+date.
        # Roll back the failed insert and return the existing fine.
        await db.rollback()
        existing_result = await db.execute(
            select(Fine).where(
                Fine.checkout_id == checkout.id, Fine.fine_type == FineType.overdue
            )
        )
        return existing_result.scalar_one_or_none()

    # Audit: record the fine assessment
    await ops_audit.log_fine_assessed(db, patron=user, fine=fine, checkout=checkout)

    # Stage the in-app feed row transactionally with the fine creation.
    await record_fine_assessed_in_app(fine, checkout, db)
    return fine


async def record_fine_assessed_in_app(
    fine: Fine, checkout: Checkout, db: AsyncSession
) -> None:
    try:
        from app.models.notification import PatronNotificationCategory
        from .patron_notification_service import record_in_app_notification
        from app.core.frontend_routes import routes

        if fine.id is None:
            return
        amount = Decimal(str(fine.amount or 0))
        item_title = None
        if checkout.item_id is not None:
            from ..models.catalog import CatalogItem

            item = await db.get(CatalogItem, checkout.item_id)
            item_title = item.title if item is not None else None
        if item_title:
            message = (
                f'A ${amount:.2f} fine was assessed for "{item_title}". '
                "You can pay it online from your account."
            )
        else:
            message = (
                f"A ${amount:.2f} fine was assessed on your account. "
                "You can pay it online from your account."
            )

        await record_in_app_notification(
            db,
            patron_id=fine.user_id,
            category=PatronNotificationCategory.FINE_ASSESSED,
            title=f"A ${amount:.2f} fine was assessed",
            message=message,
            source_event_type="FineAssessed",
            source_event_id=f"fine_assessed:{fine.id}",
            related_fine_id=str(fine.id),
            related_loan_id=str(checkout.id) if checkout.id is not None else None,
            related_item_title=item_title,
            action_url=routes.account_fines,
            action_label="Pay fine",
        )
    except Exception as e:  # noqa: BLE001 -- in-app notification staging must not block fine assessment commit
        logger.error(
            "Failed to stage in-app fine-assessed notification",
            extra={"fine_id": fine.id, "user_id": fine.user_id, "error": str(e)},
        )


async def get_user_fines_summary(
    user_id: int, db: AsyncSession
) -> dict:
    # Calculate outstanding (unpaid/partial fines)
    outstanding_result = await db.execute(
        select(
            func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0),
            func.count(Fine.id),
        ).where(
            Fine.user_id == user_id,
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        )
    )
    outstanding_row = outstanding_result.one()

    # Calculate paid
    paid_result = await db.execute(
        select(func.coalesce(func.sum(Fine.amount_paid), 0), func.count(Fine.id)).where(
            Fine.user_id == user_id, Fine.status == FineStatus.paid
        )
    )
    paid_row = paid_result.one()

    # Calculate waived
    waived_result = await db.execute(
        select(func.count(Fine.id)).where(
            Fine.user_id == user_id, Fine.status == FineStatus.waived
        )
    )
    waived_count = waived_result.scalar() or 0

    total_outstanding = Decimal(str(outstanding_row[0]))
    total_paid = Decimal(str(paid_row[0]))

    return {
        "total_outstanding": total_outstanding,
        "total_paid": total_paid,
        "outstanding_count": outstanding_row[1],
        "paid_count": paid_row[1],
        "waived_count": waived_count,
        "total_balance": total_outstanding,
    }


async def record_fine_payment(
    fine_id: int,
    amount: Decimal,
    db: AsyncSession,
    payment_method: str = "online",
    notes: str = "",
    staff_id: int | None = None,
) -> Fine:
    # Get fine with lock to prevent concurrent payment race conditions
    fine_result = await db.execute(
        select(Fine).where(Fine.id == fine_id).with_for_update()
    )
    fine = fine_result.scalar_one_or_none()

    if not fine:
        raise ValueError(f"Fine {fine_id} not found")

    if amount <= Decimal("0.00"):
        raise ValueError(f"Payment amount must be positive, got {amount}")

    # Calculate new amounts
    payment_amount = min(amount, fine.balance)
    # When forwarding to the domain aggregate (PatronAccount.record_payment),
    # convert Decimal dollars to int cents:
    #   payment_cents = dollars_to_cents(payment_amount)
    fine.amount_paid += payment_amount

    # Update status
    if fine.balance <= Decimal("0.00"):
        fine.status = FineStatus.paid
        fine.paid_at = utc_now()
    else:
        fine.status = FineStatus.partial

    # Add notes if provided
    if notes:
        fine.notes = (fine.notes or "") + f"\n[{utc_now().isoformat()}] {payment_method}: {notes}"

    # Flush so the payment survives a caller's refresh() before commit
    await db.flush()

    logger.info(
        f"Recorded payment for fine {fine_id}",
        extra={"amount": str(payment_amount), "remaining_balance": str(fine.balance)},
    )


    # Auto-log to cash drawer if payment is cash
    if payment_method == "cash" and staff_id:
        try:
            from . import cash_drawer_service
            from ..models.cash_drawer import TransactionDirection, TransactionCategory
            active_session = await cash_drawer_service.find_active_session_for_staff(db, staff_id)
            if active_session:
                await cash_drawer_service.log_transaction(
                    db,
                    session_id=active_session.id,
                    staff_id=staff_id,
                    direction=TransactionDirection.inflow,
                    category=TransactionCategory.fine_payment,
                    amount=payment_amount,
                    description=f"Fine #{fine.id} payment",
                    reference_type="fine",
                    reference_id=fine.id,
                )
            else:
                logger.info("Cash payment recorded but no active drawer session for staff %s", staff_id)
        except Exception:
            logger.exception("Failed to auto-log cash payment to drawer")

    # Invalidate financial report cache after payment
    await invalidate_financial_reports()

    return fine


async def waive_fine(
    fine_id: int,
    db: AsyncSession,
    waived_by_id: int,
    reason: str = "",
) -> Fine:
    # Lock fine to prevent concurrent waive/payment race conditions
    fine_result = await db.execute(
        select(Fine).where(Fine.id == fine_id).with_for_update()
    )
    fine = fine_result.scalar_one_or_none()

    if not fine:
        raise ValueError(f"Fine {fine_id} not found")

    fine.status = FineStatus.waived
    fine.waived_at = utc_now()
    fine.waived_by_id = waived_by_id

    if reason:
        fine.notes = (fine.notes or "") + f"\n[Waived: {reason}]"

    logger.info(
        f"Waived fine {fine_id}",
        extra={"reason": reason, "waived_by": waived_by_id},
    )

    # Audit: record the waiver with staff identity and amount for financial forensics
    # This is critical for answering "which staff member waived $50K in fines?"
    # We fetch the staff and patron users to capture denormalized identifiers
    staff_result = await db.execute(select(User).where(User.id == waived_by_id))
    staff_user = staff_result.scalar_one_or_none()
    patron_result = await db.execute(select(User).where(User.id == fine.user_id))
    patron_user = patron_result.scalar_one_or_none()
    if staff_user and patron_user:
        await ops_audit.log_fine_waived(
            db, patron=patron_user, fine=fine, staff=staff_user, reason=reason,
        )

    # Invalidate financial report cache after waiver
    await invalidate_financial_reports()

    return fine


async def get_user_fines(
    user_id: int,
    db: AsyncSession,
    status: FineStatus = None,
    fine_type: FineType = None,
) -> list[Fine]:
    stmt = select(Fine).where(Fine.user_id == user_id)

    if status:
        stmt = stmt.where(Fine.status == status)

    if fine_type:
        stmt = stmt.where(Fine.fine_type == fine_type)

    stmt = stmt.order_by(Fine.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_overdue_fines_requiring_action(
    db: AsyncSession,
    days_overdue_threshold: int = 30,
) -> list[Fine]:
    from datetime import timedelta

    threshold_date = utc_now() - timedelta(days=days_overdue_threshold)

    stmt = (
        select(Fine)
        .where(
            and_(
                Fine.fine_type == FineType.overdue,
                Fine.status == FineStatus.unpaid,
                Fine.created_at <= threshold_date,
            )
        )
        .order_by(Fine.amount.desc())
    )

    result = await db.execute(stmt)
    return result.scalars().all()


# =============================================================================
# FINE-FREE ACCOUNTABILITY
# =============================================================================


async def check_overdue_block(user_id: int, db: AsyncSession) -> tuple[bool, int]:
    from .suspension_service import check_and_auto_suspend_for_overdue

    # Delegate to suspension service which handles auto-suspension
    return await check_and_auto_suspend_for_overdue(user_id, db)


async def get_long_overdue_items(user_id: int, db: AsyncSession) -> list[Checkout]:
    from datetime import timedelta

    threshold_date = utc_now() - timedelta(days=OVERDUE_CHECKOUT_PAUSE_DAYS)

    stmt = (
        select(Checkout)
        .where(
            and_(
                Checkout.user_id == user_id,
                Checkout.status == CheckoutStatus.overdue,
                Checkout.due_date < threshold_date,
                Checkout.returned_at.is_(None),
            )
        )
        .order_by(Checkout.due_date)
    )

    result = await db.execute(stmt)
    return result.scalars().all()
