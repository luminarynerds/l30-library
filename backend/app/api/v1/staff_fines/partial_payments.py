# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff Fines - Partial payment endpoint."""

from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....models.audit_log import AuditAction
from ....models.fine import (
    CheckClearanceStatus,
    Fine,
    FinePaymentHistory,
    FineStatus,
    PaymentMethod,
)
from ....models.user import User
from ....schemas.fine import (
    FineResponse,
    PartialPaymentRequest,
    PartialPaymentResponse,
    PaymentHistoryResponse,
)
from ..dependencies import require_staff
from .helpers import (
    _track_payment,
    create_fine_audit_log,
    generate_receipt_number,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/staff", tags=["staff-fines"])


@router.post("/fines/{fine_id}/partial-payment", response_model=PartialPaymentResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def make_partial_payment(
    request: Request,
    fine_id: int,
    payment_data: PartialPaymentRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """CRITICAL ENDPOINT: Make a partial payment on a fine with receipt generation.

    This endpoint is optimized for partial fine payments with:
    - Automatic receipt generation with unique receipt number
    - Payment history tracking for future reference
    - Support for multiple payment methods (cash, card, check, online)
    - Can result in full payment if balance is exactly paid

    Args:
        request: HTTP request for audit logging (IP, user agent)
        fine_id: ID of the fine being paid
        payment_data: Payment amount, method, and optional notes
        staff_user: Authenticated staff member processing the payment
        db: Database session

    Returns:
        PartialPaymentResponse containing:
        - Updated fine with new status and balance
        - Payment record with receipt number
        - Receipt number for patron/staff reference

    Raises:
        404: Fine not found
        400: Fine is already paid/waived, or payment exceeds balance
        500: Database or audit log failure

    Security:
        - Rate limited to 30 requests/minute to prevent abuse
        - Requires staff role (enforced by require_staff dependency)
        - Concurrent access protected with FOR UPDATE row lock
        - Prevents payment amounts exceeding remaining balance

    Validation:
        - Fine must exist and not already paid or waived
        - Payment amount must be positive (validated by schema)
        - Payment amount cannot exceed remaining balance
        - Payment method must be valid (cash, card, check, online)

    Receipt Generation:
        - Unique receipt number format: RCP-YYYYMMDDHHmmss-XXXXXX
        - Receipt number stored in FinePaymentHistory for audit trail
        - Can be used with /fines/{fine_id}/receipt to retrieve receipt data

    State Transitions:
        - unpaid + partial payment -> partial (unless balance is zero)
        - unpaid + payment equaling balance -> paid
        - partial + partial payment -> partial or paid (based on remaining balance)

    Audit Trail:
        - Records action as FEE_PAID in AuditLog
        - Captures staff member ID, patron ID, payment amount, method
        - Tracks receipt number for receipt-based audit queries
        - Includes IP address and user agent for security review
    """
    # Lock fine to prevent concurrent payment race conditions
    # This ensures only one payment operation can modify this fine at a time
    result = await db.execute(
        select(Fine).where(Fine.id == fine_id).with_for_update()
    )
    fine = result.scalar_one_or_none()

    if not fine:
        logger.warning(f"Partial payment attempt on non-existent fine {fine_id} by staff {staff_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fine {fine_id} not found"
        )

    # Validate fine status - cannot pay already-resolved fines
    if fine.status == FineStatus.paid:
        logger.warning(
            f"Partial payment attempt on already-paid fine {fine_id} by staff {staff_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot pay fine {fine_id}: fine is already paid in full"
        )

    if fine.status == FineStatus.waived:
        logger.warning(
            f"Partial payment attempt on already-waived fine {fine_id} by staff {staff_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot pay fine {fine_id}: fine is waived"
        )

    # Get patron for audit trail and response
    patron_result = await db.execute(select(User).where(User.id == fine.user_id))
    patron = patron_result.scalar_one_or_none()

    # Validate payment amount against remaining balance
    remaining_balance = fine.amount - fine.amount_paid
    if payment_data.amount > remaining_balance:
        logger.warning(
            f"Partial payment overage on fine {fine_id}: "
            f"payment=${payment_data.amount} exceeds balance=${remaining_balance} "
            f"by staff {staff_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Payment amount ${payment_data.amount} exceeds remaining balance "
                f"${remaining_balance}"
            ),
        )

    # Generate unique receipt number
    receipt_number = generate_receipt_number()

    # Capture state before update for audit log
    amount_paid_before = fine.amount_paid
    prev_status = fine.status
    new_amount_paid = fine.amount_paid + payment_data.amount
    new_remaining = fine.amount - new_amount_paid

    # Create payment history record with receipt tracking
    # For check payments, set clearance status to pending
    check_status = None
    if payment_data.payment_method == PaymentMethod.check:
        check_status = CheckClearanceStatus.pending

    payment_record = FinePaymentHistory(
        fine_id=fine.id,
        user_id=fine.user_id,
        amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        notes=payment_data.notes,
        receipt_number=receipt_number,
        processed_by_id=staff_user.id,
        check_clearance_status=check_status,
    )
    db.add(payment_record)

    # Update fine with payment
    fine.amount_paid = new_amount_paid

    # Determine new status based on remaining balance
    if new_remaining == 0:
        fine.status = FineStatus.paid
        fine.paid_at = datetime.now(timezone.utc)
    else:
        fine.status = FineStatus.partial

    # Add detailed payment note with receipt reference
    check_warning = ""
    if payment_data.payment_method == PaymentMethod.check:
        check_warning = " [CHECK PENDING CLEARANCE]"

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    payment_note = (
        f"\n[{timestamp}] Payment: ${payment_data.amount} via "
        f"{payment_data.payment_method}. Receipt: {receipt_number}{check_warning}"
    )
    if payment_data.notes:
        payment_note += f" - {payment_data.notes}"
    fine.notes = (fine.notes or "") + payment_note

    try:
        # Create audit log entry before commit so it's in the same transaction
        audit_details = {
            "fine_id": fine.id,
            "fine_type": str(fine.fine_type),
            "payment_amount": str(payment_data.amount),
            "payment_method": payment_data.payment_method,
            "previous_amount_paid": str(amount_paid_before),
            "new_amount_paid": str(new_amount_paid),
            "remaining_balance": str(new_remaining),
            "receipt_number": receipt_number,
            "previous_status": str(prev_status),
            "new_status": str(fine.status),
            "is_full_payment": new_remaining == 0,
            "patron_id": patron.id if patron else None,
            "patron_name": f"{patron.first_name} {patron.last_name}" if patron else "Unknown",
        }
        if payment_data.notes:
            audit_details["notes"] = payment_data.notes

        await create_fine_audit_log(
            db=db,
            action=AuditAction.FEE_PAID,
            staff_user=staff_user,
            patron_user=patron or User(id=fine.user_id),
            fine=fine,
            details=audit_details,
            request=request,
        )

        # Commit payment record, audit log, and fine update together
        await db.commit()
        await db.refresh(fine)
        await db.refresh(payment_record)
        _track_payment("partial_payment", payment_data.amount, staff_user.id)

        log_msg = (
            f"Partial payment recorded on fine {fine_id}: "
            f"${payment_data.amount} via {payment_data.payment_method}, "
            f"receipt={receipt_number}, "
            f"status {str(prev_status)}->{fine.status}, "
            f"balance ${new_remaining}"
        )
        logger.info(log_msg)

    except HTTPException:
        # Re-raise audit log failures
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error processing partial payment on fine {fine_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process payment due to database error"
        ) from e

    # Build response with updated fine and payment record
    fine_response = FineResponse(
        id=fine.id,
        user_id=fine.user_id,
        checkout_id=fine.checkout_id,
        fine_type=fine.fine_type,
        status=fine.status,
        amount=fine.amount,
        amount_paid=fine.amount_paid,
        balance=fine.amount - fine.amount_paid,
        description=fine.description,
        notes=fine.notes,
        created_at=fine.created_at,
        paid_at=fine.paid_at,
        waived_at=fine.waived_at,
        waived_by_id=fine.waived_by_id,
        patron_name=f"{patron.first_name} {patron.last_name}" if patron else None,
        patron_email=patron.email if patron else None,
        patron_library_card=patron.library_card if patron else None,
    )

    payment_response = PaymentHistoryResponse(
        id=payment_record.id,
        fine_id=payment_record.fine_id,
        user_id=payment_record.user_id,
        amount=payment_record.amount,
        payment_method=payment_record.payment_method,
        notes=payment_record.notes,
        receipt_number=payment_record.receipt_number,
        processed_by_id=payment_record.processed_by_id,
        processed_by_name=f"{staff_user.first_name} {staff_user.last_name}",
        created_at=payment_record.created_at,
    )

    return PartialPaymentResponse(
        fine=fine_response,
        payment=payment_response,
        receipt_number=receipt_number,
    )
