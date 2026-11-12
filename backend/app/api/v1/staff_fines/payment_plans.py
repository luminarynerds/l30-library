# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff Fines - Payment plan CRUD and recording payments."""

from app.core.logging import get_logger
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import InternalServerError
from ....core.error_codes import ErrorCode
from ....core.shortcuts import get_or_404
from ....core.rate_limit import limiter
from ....models.fine import (
    PaymentPlan,
    PaymentPlanFrequency,
    PaymentPlanStatus,
)
from ....models.user import User
from ....schemas.fine import (
    PartialPaymentRequest,
    PaymentPlanCreate,
    PaymentPlanResponse,
    PaymentPlanUpdate,
)
from ..dependencies import require_staff
from .helpers import calculate_next_payment_date

logger = get_logger(__name__)

router = APIRouter(prefix="/staff", tags=["staff-fines"])


@router.post("/patrons/{patron_id}/payment-plan", response_model=PaymentPlanResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_payment_plan(
    request: Request,
    patron_id: int,
    plan_data: PaymentPlanCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a payment plan for a patron with outstanding fines.

    SECURITY: Rate limited to 10 requests/minute to prevent abuse.
    """
    # Get patron
    await get_or_404(db, User, patron_id, "Patron not found")

    # Check for existing active payment plan
    existing_plan_result = await db.execute(
        select(PaymentPlan).where(
            PaymentPlan.user_id == patron_id,
            PaymentPlan.status == PaymentPlanStatus.active,
        )
    )
    if existing_plan_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patron already has an active payment plan",
        )

    # Validate installment amount
    if plan_data.installment_amount > plan_data.total_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Installment amount cannot exceed total amount",
        )

    # Calculate expected payments
    total_payments = math.ceil(float(plan_data.total_amount / plan_data.installment_amount))

    # Create payment plan
    payment_plan = PaymentPlan(
        user_id=patron_id,
        total_amount=plan_data.total_amount,
        installment_amount=plan_data.installment_amount,
        frequency=plan_data.frequency,
        status=PaymentPlanStatus.active,
        total_payments_expected=total_payments,
        next_payment_date=calculate_next_payment_date(plan_data.frequency),
        reminder_enabled=plan_data.reminder_enabled,
        notes=plan_data.notes,
        created_by_id=staff_user.id,
    )
    db.add(payment_plan)

    try:
        await db.commit()
        await db.refresh(payment_plan)
    except Exception:
        await db.rollback()
        logger.exception("Failed to create payment plan")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None

    return PaymentPlanResponse(
        id=payment_plan.id,
        user_id=payment_plan.user_id,
        total_amount=payment_plan.total_amount,
        installment_amount=payment_plan.installment_amount,
        frequency=payment_plan.frequency,
        status=payment_plan.status,
        amount_paid=payment_plan.amount_paid,
        remaining_balance=payment_plan.total_amount - payment_plan.amount_paid,
        payments_made=payment_plan.payments_made,
        total_payments_expected=payment_plan.total_payments_expected,
        progress_percentage=float((payment_plan.amount_paid / payment_plan.total_amount) * 100) if payment_plan.total_amount > 0 else 0,
        start_date=payment_plan.start_date,
        next_payment_date=payment_plan.next_payment_date,
        completed_at=payment_plan.completed_at,
        reminder_enabled=payment_plan.reminder_enabled,
        last_reminder_sent=payment_plan.last_reminder_sent,
        notes=payment_plan.notes,
        created_by_id=payment_plan.created_by_id,
        created_by_name=f"{staff_user.first_name} {staff_user.last_name}",
        created_at=payment_plan.created_at,
        updated_at=payment_plan.updated_at,
    )


@router.get("/patrons/{patron_id}/payment-plan", response_model=PaymentPlanResponse | None)
async def get_payment_plan(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get the active payment plan for a patron."""
    # Get patron
    await get_or_404(db, User, patron_id, "Patron not found")

    # Get active payment plan
    plan_result = await db.execute(
        select(PaymentPlan, User)
        .outerjoin(User, PaymentPlan.created_by_id == User.id)
        .where(
            PaymentPlan.user_id == patron_id,
            PaymentPlan.status == PaymentPlanStatus.active,
        )
    )
    row = plan_result.first()

    if not row:
        return None

    plan, creator = row

    return PaymentPlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        total_amount=plan.total_amount,
        installment_amount=plan.installment_amount,
        frequency=plan.frequency,
        status=plan.status,
        amount_paid=plan.amount_paid,
        remaining_balance=plan.total_amount - plan.amount_paid,
        payments_made=plan.payments_made,
        total_payments_expected=plan.total_payments_expected,
        progress_percentage=float((plan.amount_paid / plan.total_amount) * 100) if plan.total_amount > 0 else 0,
        start_date=plan.start_date,
        next_payment_date=plan.next_payment_date,
        completed_at=plan.completed_at,
        reminder_enabled=plan.reminder_enabled,
        last_reminder_sent=plan.last_reminder_sent,
        notes=plan.notes,
        created_by_id=plan.created_by_id,
        created_by_name=f"{creator.first_name} {creator.last_name}" if creator else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.put("/patrons/{patron_id}/payment-plan", response_model=PaymentPlanResponse)
@limiter.limit("30/minute")
async def update_payment_plan(
    request: Request,
    patron_id: int,
    update_data: PaymentPlanUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a patron's active payment plan.

    SECURITY: Rate limited to 30 requests/minute to prevent abuse.
    """
    # Get active payment plan
    plan_result = await db.execute(
        select(PaymentPlan).where(
            PaymentPlan.user_id == patron_id,
            PaymentPlan.status == PaymentPlanStatus.active,
        )
    )
    plan = plan_result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active payment plan found")

    # Update fields
    if update_data.installment_amount is not None:
        plan.installment_amount = update_data.installment_amount
        # Recalculate expected payments
        remaining = plan.total_amount - plan.amount_paid
        plan.total_payments_expected = plan.payments_made + math.ceil(float(remaining / update_data.installment_amount))

    if update_data.frequency is not None:
        plan.frequency = update_data.frequency
        plan.next_payment_date = calculate_next_payment_date(update_data.frequency)

    if update_data.reminder_enabled is not None:
        plan.reminder_enabled = update_data.reminder_enabled

    if update_data.status is not None:
        plan.status = update_data.status
        if update_data.status == PaymentPlanStatus.completed:
            plan.completed_at = datetime.now(timezone.utc)

    if update_data.notes is not None:
        plan.notes = update_data.notes

    try:
        await db.commit()
        await db.refresh(plan)
    except Exception:
        await db.rollback()
        logger.exception("Failed to update payment plan")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None

    # Get creator info
    creator = None
    if plan.created_by_id:
        creator_result = await db.execute(select(User).where(User.id == plan.created_by_id))
        creator = creator_result.scalar_one_or_none()

    return PaymentPlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        total_amount=plan.total_amount,
        installment_amount=plan.installment_amount,
        frequency=plan.frequency,
        status=plan.status,
        amount_paid=plan.amount_paid,
        remaining_balance=plan.total_amount - plan.amount_paid,
        payments_made=plan.payments_made,
        total_payments_expected=plan.total_payments_expected,
        progress_percentage=float((plan.amount_paid / plan.total_amount) * 100) if plan.total_amount > 0 else 0,
        start_date=plan.start_date,
        next_payment_date=plan.next_payment_date,
        completed_at=plan.completed_at,
        reminder_enabled=plan.reminder_enabled,
        last_reminder_sent=plan.last_reminder_sent,
        notes=plan.notes,
        created_by_id=plan.created_by_id,
        created_by_name=f"{creator.first_name} {creator.last_name}" if creator else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.post("/patrons/{patron_id}/payment-plan/payment", response_model=PaymentPlanResponse)
@limiter.limit("30/minute")
async def record_payment_plan_payment(
    request: Request,
    patron_id: int,
    payment_data: PartialPaymentRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Record a payment toward a patron's payment plan.

    SECURITY: Rate limited to 30 requests/minute to prevent abuse.
    CONCURRENCY: Uses FOR UPDATE to prevent race conditions with concurrent payments.
    """
    # Lock payment plan to prevent concurrent payment race conditions
    plan_result = await db.execute(
        select(PaymentPlan).where(
            PaymentPlan.user_id == patron_id,
            PaymentPlan.status == PaymentPlanStatus.active,
        ).with_for_update()
    )
    plan = plan_result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active payment plan found")

    # Validate payment
    remaining = plan.total_amount - plan.amount_paid
    if payment_data.amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount ${payment_data.amount} exceeds remaining balance ${remaining}",
        )

    # Update plan
    plan.amount_paid = plan.amount_paid + payment_data.amount
    plan.payments_made = plan.payments_made + 1
    plan.next_payment_date = calculate_next_payment_date(plan.frequency)

    # Check if completed
    if plan.amount_paid >= plan.total_amount:
        plan.status = PaymentPlanStatus.completed
        plan.completed_at = datetime.now(timezone.utc)

    # Add note
    payment_note = f"\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] Payment ${payment_data.amount} via {payment_data.payment_method}"
    if payment_data.notes:
        payment_note += f" - {payment_data.notes}"
    plan.notes = (plan.notes or "") + payment_note

    try:
        await db.commit()
        await db.refresh(plan)
    except Exception:
        await db.rollback()
        logger.exception("Failed to record payment")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None

    # Get creator info
    creator = None
    if plan.created_by_id:
        creator_result = await db.execute(select(User).where(User.id == plan.created_by_id))
        creator = creator_result.scalar_one_or_none()

    return PaymentPlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        total_amount=plan.total_amount,
        installment_amount=plan.installment_amount,
        frequency=plan.frequency,
        status=plan.status,
        amount_paid=plan.amount_paid,
        remaining_balance=plan.total_amount - plan.amount_paid,
        payments_made=plan.payments_made,
        total_payments_expected=plan.total_payments_expected,
        progress_percentage=float((plan.amount_paid / plan.total_amount) * 100) if plan.total_amount > 0 else 0,
        start_date=plan.start_date,
        next_payment_date=plan.next_payment_date,
        completed_at=plan.completed_at,
        reminder_enabled=plan.reminder_enabled,
        last_reminder_sent=plan.last_reminder_sent,
        notes=plan.notes,
        created_by_id=plan.created_by_id,
        created_by_name=f"{creator.first_name} {creator.last_name}" if creator else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )
