# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff Fines - Patron fine history endpoint."""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.fine import (
    Fine,
    FinePaymentHistory,
    FineStatus,
)
from ....models.user import User
from ....schemas.fine import (
    FineHistoryResponse,
    FineResponse,
    PaymentHistoryResponse,
)
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/staff", tags=["staff-fines"])


@router.get("/patrons/{patron_id}/fines/history", response_model=FineHistoryResponse)
async def get_patron_fine_history(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get full fine history for a patron including all fines and payment records."""
    # Get patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    # Get all fines for patron
    fines_result = await db.execute(
        select(Fine)
        .where(Fine.user_id == patron_id)
        .order_by(Fine.created_at.desc())
    )
    fines = fines_result.scalars().all()

    # Get all payments for patron's fines
    fine_ids = [f.id for f in fines]
    payments = []
    if fine_ids:
        payments_result = await db.execute(
            select(FinePaymentHistory, User)
            .outerjoin(User, FinePaymentHistory.processed_by_id == User.id)
            .where(FinePaymentHistory.fine_id.in_(fine_ids))
            .order_by(FinePaymentHistory.created_at.desc())
        )
        payments_rows = payments_result.all()
        payments = [
            PaymentHistoryResponse(
                id=payment.id,
                fine_id=payment.fine_id,
                user_id=payment.user_id,
                amount=payment.amount,
                payment_method=payment.payment_method,
                notes=payment.notes,
                receipt_number=payment.receipt_number,
                processed_by_id=payment.processed_by_id,
                processed_by_name=f"{staff.first_name} {staff.last_name}" if staff else None,
                created_at=payment.created_at,
            )
            for payment, staff in payments_rows
        ]

    # Calculate totals
    total_fines_amount = sum(f.amount for f in fines)
    total_paid_amount = sum(f.amount_paid for f in fines)
    current_balance = sum(
        f.amount - f.amount_paid
        for f in fines
        if f.status in [FineStatus.unpaid, FineStatus.partial]
    )

    fine_responses = [
        FineResponse(
            id=f.id,
            user_id=f.user_id,
            checkout_id=f.checkout_id,
            fine_type=f.fine_type,
            status=f.status,
            amount=f.amount,
            amount_paid=f.amount_paid,
            balance=f.amount - f.amount_paid,
            description=f.description,
            notes=f.notes,
            created_at=f.created_at,
            paid_at=f.paid_at,
            waived_at=f.waived_at,
            waived_by_id=f.waived_by_id,
            patron_name=f"{patron.first_name} {patron.last_name}",
            patron_email=patron.email,
            patron_library_card=patron.library_card,
        )
        for f in fines
    ]

    return FineHistoryResponse(
        patron_id=patron_id,
        patron_name=f"{patron.first_name} {patron.last_name}",
        fines=fine_responses,
        payments=payments,
        total_count=len(fines),
        total_fines_amount=total_fines_amount,
        total_paid_amount=total_paid_amount,
        current_balance=current_balance,
    )
