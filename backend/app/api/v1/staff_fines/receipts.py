# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff Fines - Receipt generation endpoint."""

from app.core.logging import get_logger
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.fine import (
    Fine,
    FinePaymentHistory,
)
from ....models.user import User
from ....schemas.fine import ReceiptData
from ..dependencies import require_staff
from .helpers import generate_receipt_number

logger = get_logger(__name__)

router = APIRouter(prefix="/staff", tags=["staff-fines"])


@router.get("/fines/{fine_id}/receipt", response_model=ReceiptData)
async def get_receipt(
    fine_id: int,
    payment_id: Optional[int] = Query(None, description="Specific payment ID for receipt"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Generate receipt data for a fine payment."""
    # Get fine
    fine = await get_or_404(db, Fine, fine_id, "Fine not found")

    # Get patron
    patron_result = await db.execute(select(User).where(User.id == fine.user_id))
    patron = patron_result.scalar_one_or_none()

    # Get payment record
    if payment_id:
        payment_result = await db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.id == payment_id)
        )
    else:
        # Get most recent payment
        payment_result = await db.execute(
            select(FinePaymentHistory)
            .where(FinePaymentHistory.fine_id == fine_id)
            .order_by(FinePaymentHistory.created_at.desc())
            .limit(1)
        )

    payment = payment_result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No payment found for this fine")

    # Get staff who processed the payment
    processor = None
    if payment.processed_by_id:
        processor_result = await db.execute(
            select(User).where(User.id == payment.processed_by_id)
        )
        processor = processor_result.scalar_one_or_none()

    # Calculate amounts at time of payment
    # We need to sum all payments before this one
    prior_payments_result = await db.execute(
        select(func.sum(FinePaymentHistory.amount)).where(
            FinePaymentHistory.fine_id == fine_id,
            FinePaymentHistory.created_at < payment.created_at,
        )
    )
    prior_amount = prior_payments_result.scalar() or Decimal("0.00")

    return ReceiptData(
        receipt_number=payment.receipt_number or generate_receipt_number(),
        payment_date=payment.created_at,
        payment_amount=payment.amount,
        payment_method=payment.payment_method,
        patron_id=patron.id if patron else 0,
        patron_name=f"{patron.first_name} {patron.last_name}" if patron else "Unknown",
        patron_email=patron.email if patron else None,
        patron_library_card=patron.library_card if patron else None,
        fine_id=fine.id,
        fine_type=fine.fine_type,
        fine_description=fine.description,
        original_fine_amount=fine.amount,
        amount_paid_before=prior_amount,
        amount_paid_now=payment.amount,
        remaining_balance=fine.amount - prior_amount - payment.amount,
        staff_id=processor.id if processor else staff_user.id,
        staff_name=f"{processor.first_name} {processor.last_name}" if processor else f"{staff_user.first_name} {staff_user.last_name}",
        library_name="Lone Star Collective",
        library_address="123 Main Street, Texas",
        library_phone="(555) 123-4567",
    )
