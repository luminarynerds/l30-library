# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff Fines - Fine analytics, payment history list, and check clearance endpoints."""

from app.core.logging import get_logger
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.rate_limit import limiter
from ....models.audit_log import AuditLog, AuditAction
from ....models.fine import (
    CheckClearanceStatus,
    Fine,
    FinePaymentHistory,
    FineStatus,
    FineType,
    PaymentMethod,
)
from ....models.user import User
from ....schemas.fine import (
    FineAccumulationPoint,
    FineAnalyticsByType,
    FineAnalyticsResponse,
    PatronFinePatterns,
    PaymentHistoryResponse,
    PaymentHistoryListResponse,
)
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/staff", tags=["staff-fines"])


@router.get("/patrons/{patron_id}/fines/analytics", response_model=FineAnalyticsResponse)
async def get_patron_fine_analytics(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get fine analytics for a patron including breakdown, trends, and patterns."""
    # Get patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    # Get all fines
    fines_result = await db.execute(
        select(Fine).where(Fine.user_id == patron_id)
    )
    fines = fines_result.scalars().all()

    # Calculate current balance
    current_balance = sum(
        f.amount - f.amount_paid
        for f in fines
        if f.status in [FineStatus.unpaid, FineStatus.partial]
    )

    # Breakdown by type
    type_breakdown = defaultdict(lambda: {"count": 0, "amount": Decimal("0.00")})
    total_fines_amount = Decimal("0.00")

    for fine in fines:
        type_breakdown[fine.fine_type]["count"] += 1
        type_breakdown[fine.fine_type]["amount"] += fine.amount
        total_fines_amount += fine.amount

    breakdown_by_type = [
        FineAnalyticsByType(
            fine_type=fine_type,
            count=data["count"],
            total_amount=data["amount"],
            percentage=float((data["amount"] / total_fines_amount) * 100) if total_fines_amount > 0 else 0,
        )
        for fine_type, data in type_breakdown.items()
    ]

    # Accumulation history (last 12 months)
    twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=365)
    accumulation_result = await db.execute(
        select(
            func.to_char(Fine.created_at, 'YYYY-MM').label('month'),
            func.sum(Fine.amount).label('amount'),
            func.count(Fine.id).label('count'),
        )
        .where(
            Fine.user_id == patron_id,
            Fine.created_at >= twelve_months_ago,
        )
        .group_by(text('month'))
        .order_by(text('month'))
    )
    accumulation_rows = accumulation_result.all()

    accumulation_history = [
        FineAccumulationPoint(
            date=row.month,
            amount=row.amount or Decimal("0.00"),
            count=row.count or 0,
        )
        for row in accumulation_rows
    ]

    # Pattern analysis
    total_lifetime_paid = sum(f.amount_paid for f in fines)
    total_lifetime_fines = total_fines_amount

    # Find most common fine type
    most_common_type = None
    max_count = 0
    for fine_type, data in type_breakdown.items():
        if data["count"] > max_count:
            max_count = data["count"]
            most_common_type = fine_type

    # Check for frequent late returns (more than 3 overdue fines in last 6 months)
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
    recent_overdue = sum(
        1 for f in fines
        if f.fine_type == FineType.overdue and f.created_at >= six_months_ago
    )
    frequent_late_returns = recent_overdue >= 3

    patterns = PatronFinePatterns(
        frequent_late_returns=frequent_late_returns,
        average_days_overdue=None,  # Would require checkout data
        most_common_fine_type=most_common_type,
        total_lifetime_fines=total_lifetime_fines,
        total_lifetime_paid=total_lifetime_paid,
        average_fine_amount=total_lifetime_fines / len(fines) if fines else None,
    )

    # Calculate average patron balance for comparison
    avg_balance_result = await db.execute(
        select(func.avg(
            func.coalesce(Fine.amount - Fine.amount_paid, 0)
        )).where(
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        )
    )
    avg_balance = avg_balance_result.scalar() or Decimal("0.00")

    # Comparison
    if current_balance > avg_balance * Decimal("1.1"):
        comparison = "above"
    elif current_balance < avg_balance * Decimal("0.9"):
        comparison = "below"
    else:
        comparison = "average"

    unpaid_count = sum(
        1 for f in fines
        if f.status in [FineStatus.unpaid, FineStatus.partial]
    )

    return FineAnalyticsResponse(
        patron_id=patron_id,
        patron_name=f"{patron.first_name} {patron.last_name}",
        current_balance=current_balance,
        total_fines_count=len(fines),
        unpaid_fines_count=unpaid_count,
        breakdown_by_type=breakdown_by_type,
        accumulation_history=accumulation_history,
        patterns=patterns,
        average_patron_balance=avg_balance,
        comparison_to_average=comparison,
    )


@router.get("/patrons/{patron_id}/payments", response_model=PaymentHistoryListResponse)
async def get_patron_payments(
    patron_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all payment records for a patron."""
    # Get patron
    await get_or_404(db, User, patron_id, "Patron not found")

    # Get patron's fine IDs
    fine_ids_result = await db.execute(
        select(Fine.id).where(Fine.user_id == patron_id)
    )
    fine_ids = [row[0] for row in fine_ids_result.all()]

    if not fine_ids:
        return PaymentHistoryListResponse(
            payments=[],
            total_count=0,
            total_amount=Decimal("0.00"),
        )

    # Get payments
    payments_result = await db.execute(
        select(FinePaymentHistory, User)
        .outerjoin(User, FinePaymentHistory.processed_by_id == User.id)
        .where(FinePaymentHistory.fine_id.in_(fine_ids))
        .order_by(FinePaymentHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    payments_rows = payments_result.all()

    # Get total count and amount
    count_result = await db.execute(
        select(func.count(FinePaymentHistory.id)).where(
            FinePaymentHistory.fine_id.in_(fine_ids)
        )
    )
    total_count = count_result.scalar() or 0

    total_amount_result = await db.execute(
        select(func.sum(FinePaymentHistory.amount)).where(
            FinePaymentHistory.fine_id.in_(fine_ids)
        )
    )
    total_amount = total_amount_result.scalar() or Decimal("0.00")

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

    return PaymentHistoryListResponse(
        payments=payments,
        total_count=total_count,
        total_amount=total_amount,
    )


# =============================================================================
# CHECK CLEARANCE ENDPOINTS (Exploit #7 countermeasure)
# =============================================================================


@router.post("/payments/{payment_id}/check-bounced", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def mark_check_bounced(
    request: Request,
    payment_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a check payment as bounced. Reverses the payment and re-suspends the patron."""
    from ....services.suspension_service import handle_bounced_check

    try:
        payment = await handle_bounced_check(payment_id, db, staff_user.id)

        # Audit log
        audit_log = AuditLog(
            admin_id=staff_user.id,
            target_user_id=payment.user_id,
            action=AuditAction.CHECK_BOUNCED,
            details={
                "payment_id": payment_id,
                "fine_id": payment.fine_id,
                "amount": str(payment.amount),
                "receipt_number": payment.receipt_number,
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(audit_log)
        await db.commit()

        return {
            "message": "Check marked as bounced. Payment reversed and patron re-suspended.",
            "payment_id": payment_id,
            "amount_reversed": str(payment.amount),
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/payments/{payment_id}/check-cleared", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def mark_check_cleared(
    request: Request,
    payment_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a check payment as cleared. May auto-lift patron suspension if balance is resolved."""
    from ....services.suspension_service import handle_check_cleared

    try:
        payment = await handle_check_cleared(payment_id, db, staff_user.id)

        # Audit log
        audit_log = AuditLog(
            admin_id=staff_user.id,
            target_user_id=payment.user_id,
            action=AuditAction.CHECK_CLEARED,
            details={
                "payment_id": payment_id,
                "fine_id": payment.fine_id,
                "amount": str(payment.amount),
                "receipt_number": payment.receipt_number,
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(audit_log)
        await db.commit()

        return {
            "message": "Check marked as cleared.",
            "payment_id": payment_id,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/payments/pending-checks", status_code=status.HTTP_200_OK)
async def list_pending_checks(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all check payments awaiting clearance."""
    result = await db.execute(
        select(FinePaymentHistory, User)
        .outerjoin(User, FinePaymentHistory.user_id == User.id)
        .where(
            FinePaymentHistory.payment_method == PaymentMethod.check,
            FinePaymentHistory.check_clearance_status == CheckClearanceStatus.pending,
        )
        .order_by(FinePaymentHistory.created_at.asc())
    )
    rows = result.all()

    return {
        "pending_checks": [
            {
                "payment_id": payment.id,
                "fine_id": payment.fine_id,
                "patron_id": payment.user_id,
                "patron_name": f"{user.first_name} {user.last_name}" if user else None,
                "amount": str(payment.amount),
                "receipt_number": payment.receipt_number,
                "created_at": payment.created_at.isoformat() if payment.created_at else None,
            }
            for payment, user in rows
        ],
        "total": len(rows),
    }
