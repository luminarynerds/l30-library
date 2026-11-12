# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff Fines - List, create, waive, and pay fine endpoints."""

from app.core.logging import get_logger
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.exceptions import InternalServerError
from ....core.error_codes import ErrorCode
from ....core.shortcuts import get_or_404
from ....core.rate_limit import limiter
from ....core.pii_audit import log_pii_access
from ....models.audit_log import AuditAction
from ....models.circulation import Checkout
from ....models.fine import (
    Fine,
    FinePaymentHistory,
    FineStatus,
    PaymentMethod,
)
from ....models.fine_waiver import FineWaiver, FineWaiverStatus


def _enum_value(v):
    return v.value if hasattr(v, "value") else str(v)
from ....models.user import User
from ....schemas.fine import (
    FineCreate,
    FineDetailItem,
    FineDetailResponse,
    FineListResponse,
    FinePayment,
    FinePaymentDetail,
    FineResponse,
    FineWaive,
    FineWaiverDecision,
    FineWaiverListItem,
    FineWaiverListResponse,
    FineWaiverResponse,
)
from ..auth import get_current_user
from ..dependencies import require_admin, require_staff
from .helpers import (
    _track_payment,
    create_fine_audit_log,
    generate_receipt_number,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/staff", tags=["staff-fines"])


@router.get("/fines", response_model=FineListResponse)
async def list_fines(
    patron_id: Optional[int] = Query(None, description="Filter by patron ID"),
    status: Optional[FineStatus] = Query(None, description="Filter by fine status"),
    unpaid_only: bool = Query(False, description="Show only unpaid fines"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all fines with filters."""
    query = select(Fine, User).join(User, Fine.user_id == User.id)
    count_query = select(func.count(Fine.id))
    total_unpaid_query = select(func.sum(Fine.amount - Fine.amount_paid)).where(
        Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
    )

    if patron_id:
        query = query.where(Fine.user_id == patron_id)
        count_query = count_query.where(Fine.user_id == patron_id)
        total_unpaid_query = total_unpaid_query.where(Fine.user_id == patron_id)

    if status:
        query = query.where(Fine.status == status)
        count_query = count_query.where(Fine.status == status)
    elif unpaid_only:
        query = query.where(Fine.status.in_([FineStatus.unpaid, FineStatus.partial]))
        count_query = count_query.where(
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        )

    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    unpaid_result = await db.execute(total_unpaid_query)
    total_unpaid = unpaid_result.scalar() or Decimal("0.00")

    result = await db.execute(
        query.order_by(Fine.created_at.desc()).offset(offset).limit(limit)
    )
    rows = result.all()

    fines = [
        FineResponse(
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
            patron_name=f"{user.first_name} {user.last_name}",
            patron_email=user.email,
            patron_library_card=user.library_card,
        )
        for fine, user in rows
    ]

    return FineListResponse(
        fines=fines, total_count=total_count, total_unpaid=total_unpaid
    )


@router.post("/fines", response_model=FineResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_fine(
    request: Request,
    fine_data: FineCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new fine for a patron.

    SECURITY: Rate limited to 30 requests/minute to prevent abuse.
    """
    patron = await get_or_404(db, User, fine_data.user_id, "Patron not found")

    if fine_data.checkout_id:
        checkout_result = await db.execute(
            select(Checkout).where(Checkout.id == fine_data.checkout_id)
        )
        if not checkout_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout not found")

    fine = Fine(
        user_id=fine_data.user_id,
        checkout_id=fine_data.checkout_id,
        fine_type=fine_data.fine_type,
        amount=fine_data.amount,
        description=fine_data.description,
        notes=fine_data.notes,
        status=FineStatus.unpaid,
    )
    db.add(fine)
    try:
        await db.commit()
        await db.refresh(fine)
    except Exception:
        await db.rollback()
        logger.exception("Failed to create fine")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None

    # Send fine assessment notification
    try:
        from app.services.notifications.email_sender import EmailSenderService
        from app.services.notifications.types import NotificationType as NType
        email_service = EmailSenderService()
        await email_service.send_templated(
            notification_type=NType.FINE_ASSESSMENT_NOTICE,
            recipient_email=patron.email,
            context_data={
                "patron_name": patron.first_name,
                "fine_type": fine.fine_type.value if hasattr(fine.fine_type, 'value') else str(fine.fine_type),
                "fine_amount": float(fine.amount),
                "item_title": fine.description or "Library item",
                "fine_reason": fine.notes or fine.description or "See your account for details",
            },
            user_id=patron.id,
            db=db,
        )
    except Exception as e:  # noqa: BLE001  # best-effort fine notification — fine already assessed
        logger.warning(f"Failed to send fine assessment notification: {e}")

    return FineResponse(
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
        patron_name=f"{patron.first_name} {patron.last_name}",
        patron_email=patron.email,
        patron_library_card=patron.library_card,
    )


# Self-approval auto-waive threshold. Above this, staff requests go to an
# admin queue. Admin+ can still be subject to the same gate when they ask for
# `requires_approval=true` explicitly.
_AUTO_WAIVE_LIMIT = Decimal("5.00")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _is_admin_or_above(user: User) -> bool:
    from ....models.user import UserRole
    return user.role in (UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN)


async def _apply_waiver_to_fine(
    *, db: AsyncSession, fine: Fine, amount: Decimal, actor: User, reason: str
) -> None:
    fine.amount_paid = (fine.amount_paid or Decimal("0.00")) + amount
    fine.waived_at = datetime.now(timezone.utc)
    fine.waived_by_id = actor.id
    if fine.amount_paid >= fine.amount:
        fine.status = FineStatus.waived
    else:
        # Partial waiver still leaves a balance; record stays unpaid/partial
        fine.status = FineStatus.partial
    fine.notes = (fine.notes or "") + (
        f"\n[{fine.waived_at.strftime('%Y-%m-%d %H:%M:%S')}] "
        f"Waived ${amount}: {reason}"
    )


@router.post(
    "/fines/{fine_id}/waive",
    response_model=FineWaiverResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("30/minute")
async def waive_fine(
    request: Request,
    fine_id: int,
    waive_data: FineWaive,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Waive part or all of a fine, with audit trail + optional approval gate.

    Behavior:
    - Auto-waive when actor is staff-level, amount <= $5, and
      `requires_approval=false`. Fine balance is reduced immediately.
    - Otherwise the request lands in `pending_approval` and the fine is NOT
      modified until an admin+ approves via
      `POST /staff/fine-waivers/{waiver_id}/approve`.
    - Admin+ actors can self-auto-waive at any amount (the gate exists for
      staff who can't approve their own large waivers).

    Idempotency:
    - 409 if the fine is already fully paid or already fully waived.
    - 400 if the requested amount exceeds the outstanding balance.
    """
    # Lock fine row to prevent concurrent waive/payment races.
    result = await db.execute(
        select(Fine).where(Fine.id == fine_id).with_for_update()
    )
    fine = result.scalar_one_or_none()

    if not fine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fine {fine_id} not found",
        )

    outstanding = (fine.amount or Decimal("0.00")) - (
        fine.amount_paid or Decimal("0.00")
    )

    if fine.status == FineStatus.paid or outstanding <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fine {fine_id} is already paid in full",
        )

    if fine.status == FineStatus.waived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fine {fine_id} is already fully waived",
        )

    requested = (waive_data.amount or outstanding).quantize(Decimal("0.01"))
    if requested <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Waive amount must be greater than zero",
        )
    if requested > outstanding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Requested waive ${requested} exceeds outstanding balance "
                f"${outstanding}"
            ),
        )

    patron_result = await db.execute(
        select(User).where(User.id == fine.user_id)
    )
    patron = patron_result.scalar_one_or_none()

    over_threshold = requested > _AUTO_WAIVE_LIMIT
    needs_approval = (
        waive_data.requires_approval
        or (over_threshold and not _is_admin_or_above(staff_user))
    )

    now = datetime.now(timezone.utc)
    waiver = FineWaiver(
        fine_id=fine.id,
        amount_waived=requested,
        reason=waive_data.reason,
        waived_by_user_id=staff_user.id,
    )

    try:
        if needs_approval:
            waiver.status = FineWaiverStatus.pending_approval
            db.add(waiver)
            await db.flush()
            remaining = outstanding  # fine untouched
        else:
            waiver.status = FineWaiverStatus.waived
            waiver.waived_at = now
            waiver.approved_by_user_id = staff_user.id
            waiver.approved_at = now
            db.add(waiver)
            await db.flush()
            await _apply_waiver_to_fine(
                db=db,
                fine=fine,
                amount=requested,
                actor=staff_user,
                reason=waive_data.reason,
            )

            await create_fine_audit_log(
                db=db,
                action=AuditAction.FEE_WAIVED,
                staff_user=staff_user,
                patron_user=patron or User(id=fine.user_id),
                fine=fine,
                details={
                    "waiver_id": waiver.id,
                    "fine_id": fine.id,
                    "amount_waived": str(requested),
                    "reason": waive_data.reason,
                    "auto_waived": True,
                },
                request=request,
            )
            remaining = outstanding - requested

        # PII access log: a waive reads patron-financial PII (amount, reason).
        await log_pii_access(
            db=db,
            user_id=staff_user.id,
            user_role=staff_user.role,
            endpoint=str(request.url.path),
            fields_accessed=["fine.amount", "fine.reason"],
            fields_redacted=[],
            patron_ids_accessed=[fine.user_id] if fine.user_id else None,
            ip_address=_client_ip(request),
            additional_context={
                "event_type": "fine.waive",
                "waiver_id": waiver.id,
                "fine_id": fine.id,
                "status": _enum_value(waiver.status),
            },
        )

        await db.commit()
        await db.refresh(waiver)

        if not needs_approval:
            _track_payment("waiver", requested, staff_user.id)

        logger.info(
            "Fine %s waiver %s created by staff %s: amount=$%s status=%s",
            fine_id,
            waiver.id,
            staff_user.id,
            requested,
            _enum_value(waiver.status),
        )

        # Best-effort fraud check on full auto-waivers.
        if not needs_approval and patron:
            try:
                from ....services.fraud_detection_service import (
                    check_waiver_frequency,
                )

                await check_waiver_frequency(
                    patron.id, db, staff_id=staff_user.id
                )
                await db.commit()
            except Exception as wf_err:  # noqa: BLE001  # best-effort fraud check — non-critical
                logger.debug(
                    "Waiver frequency check failed (non-critical): %s", wf_err
                )

    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("Error waiving fine %s", fine_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to waive fine due to database error",
        ) from None

    return FineWaiverResponse(
        waiver_id=waiver.id,
        fine_id=fine.id,
        amount_waived=requested,
        remaining_balance=remaining,
        status=waiver.status,
        waived_by=waiver.waived_by_user_id,
        waived_at=waiver.waived_at,
        approved_by=waiver.approved_by_user_id,
        approved_at=waiver.approved_at,
        reason=waiver.reason,
    )


@router.get(
    "/fine-waivers/pending",
    response_model=FineWaiverListResponse,
)
async def list_pending_waivers(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approval queue: all waivers awaiting admin/director decision."""
    base = (
        select(FineWaiver, Fine, User)
        .join(Fine, FineWaiver.fine_id == Fine.id)
        .outerjoin(User, FineWaiver.waived_by_user_id == User.id)
        .where(FineWaiver.status == FineWaiverStatus.pending_approval)
    )
    count_result = await db.execute(
        select(func.count(FineWaiver.id)).where(
            FineWaiver.status == FineWaiverStatus.pending_approval
        )
    )
    total = count_result.scalar() or 0

    rows_result = await db.execute(
        base.order_by(FineWaiver.created_at.asc()).limit(limit).offset(offset)
    )
    rows = rows_result.all()

    # Fetch patron names in one query.
    patron_ids = {f.user_id for _, f, _ in rows if f.user_id}
    patrons: dict[int, User] = {}
    if patron_ids:
        patron_rows = await db.execute(
            select(User).where(User.id.in_(patron_ids))
        )
        patrons = {p.id: p for p in patron_rows.scalars()}

    items = []
    for waiver, fine, requester in rows:
        patron = patrons.get(fine.user_id) if fine.user_id else None
        items.append(
            FineWaiverListItem(
                waiver_id=waiver.id,
                fine_id=fine.id,
                patron_id=fine.user_id,
                patron_name=(
                    f"{patron.first_name} {patron.last_name}"
                    if patron
                    else None
                ),
                fine_amount=fine.amount,
                amount_waived=waiver.amount_waived,
                reason=waiver.reason,
                status=waiver.status,
                waived_by_user_id=waiver.waived_by_user_id,
                waived_by_name=(
                    f"{requester.first_name} {requester.last_name}"
                    if requester
                    else None
                ),
                waived_at=waiver.waived_at,
                requested_at=waiver.created_at,
            )
        )

    return FineWaiverListResponse(waivers=items, total_count=total)


async def _decide_waiver(
    *,
    db: AsyncSession,
    request: Request,
    waiver_id: int,
    approver: User,
    approve: bool,
    notes: str | None,
) -> FineWaiverResponse:
    result = await db.execute(
        select(FineWaiver).where(FineWaiver.id == waiver_id).with_for_update()
    )
    waiver = result.scalar_one_or_none()
    if not waiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Waiver {waiver_id} not found",
        )

    if waiver.status != FineWaiverStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Waiver {waiver_id} is already {_enum_value(waiver.status)}; "
                "cannot decide again"
            ),
        )

    fine_result = await db.execute(
        select(Fine).where(Fine.id == waiver.fine_id).with_for_update()
    )
    fine = fine_result.scalar_one_or_none()
    if not fine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Underlying fine not found",
        )

    outstanding = (fine.amount or Decimal("0.00")) - (
        fine.amount_paid or Decimal("0.00")
    )
    now = datetime.now(timezone.utc)
    waiver.approved_by_user_id = approver.id
    waiver.approved_at = now

    if approve:
        # Re-validate amount against latest outstanding (in case payments
        # landed between request and approval).
        amount = waiver.amount_waived
        if amount > outstanding:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Waiver amount ${amount} now exceeds outstanding "
                    f"balance ${outstanding}; reject and recreate."
                ),
            )
        waiver.status = FineWaiverStatus.waived
        waiver.waived_at = now
        await _apply_waiver_to_fine(
            db=db,
            fine=fine,
            amount=amount,
            actor=approver,
            reason=waiver.reason,
        )
        remaining = outstanding - amount
        event_type = "fine.waive_approve"
        audit_action = AuditAction.FEE_WAIVED
    else:
        waiver.status = FineWaiverStatus.rejected
        remaining = outstanding
        event_type = "fine.waive_reject"
        audit_action = AuditAction.FEE_WAIVED  # closest existing action

    patron_result = await db.execute(
        select(User).where(User.id == fine.user_id)
    )
    patron = patron_result.scalar_one_or_none()

    try:
        await create_fine_audit_log(
            db=db,
            action=audit_action,
            staff_user=approver,
            patron_user=patron or User(id=fine.user_id),
            fine=fine,
            details={
                "waiver_id": waiver.id,
                "fine_id": fine.id,
                "amount_waived": str(waiver.amount_waived),
                "decision": "approved" if approve else "rejected",
                "approver_notes": notes,
                "reason": waiver.reason,
            },
            request=request,
        )
        await log_pii_access(
            db=db,
            user_id=approver.id,
            user_role=approver.role,
            endpoint=str(request.url.path),
            fields_accessed=["fine.amount", "fine.reason"],
            fields_redacted=[],
            patron_ids_accessed=[fine.user_id] if fine.user_id else None,
            ip_address=_client_ip(request),
            additional_context={
                "event_type": event_type,
                "waiver_id": waiver.id,
                "fine_id": fine.id,
            },
        )
        await db.commit()
        await db.refresh(waiver)
        if approve:
            _track_payment("waiver", waiver.amount_waived, approver.id)
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("Error deciding waiver %s", waiver_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record waiver decision",
        ) from None

    return FineWaiverResponse(
        waiver_id=waiver.id,
        fine_id=fine.id,
        amount_waived=waiver.amount_waived,
        remaining_balance=remaining,
        status=waiver.status,
        waived_by=waiver.waived_by_user_id,
        waived_at=waiver.waived_at,
        approved_by=waiver.approved_by_user_id,
        approved_at=waiver.approved_at,
        reason=waiver.reason,
    )


@router.post(
    "/fine-waivers/{waiver_id}/approve",
    response_model=FineWaiverResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("30/minute")
async def approve_waiver(
    request: Request,
    waiver_id: int,
    decision: FineWaiverDecision | None = None,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending fine-waiver. Admin / director / super_admin only."""
    notes = decision.notes if decision else None
    return await _decide_waiver(
        db=db,
        request=request,
        waiver_id=waiver_id,
        approver=admin_user,
        approve=True,
        notes=notes,
    )


@router.post(
    "/fine-waivers/{waiver_id}/reject",
    response_model=FineWaiverResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("30/minute")
async def reject_waiver(
    request: Request,
    waiver_id: int,
    decision: FineWaiverDecision | None = None,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending fine-waiver. Admin / director / super_admin only."""
    notes = decision.notes if decision else None
    return await _decide_waiver(
        db=db,
        request=request,
        waiver_id=waiver_id,
        approver=admin_user,
        approve=False,
        notes=notes,
    )


@router.post("/fines/{fine_id}/pay", response_model=FineResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def record_payment(
    request: Request,
    fine_id: int,
    payment_data: FinePayment,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """CRITICAL ENDPOINT: Record a payment toward a fine (full or partial).

    This endpoint records a general fine payment. It can be used for:
    - Full payment: payment_data.amount equals remaining balance
    - Partial payment: payment_data.amount is less than remaining balance

    For structured partial payments with receipt tracking, use /fines/{fine_id}/partial-payment instead.

    Args:
        request: HTTP request for audit logging (IP, user agent)
        fine_id: ID of the fine being paid
        payment_data: Payment amount and optional notes
        staff_user: Authenticated staff member processing the payment
        db: Database session

    Returns:
        FineResponse with updated fine status (status=paid or partial, updated balance)

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
        - Cannot pay already-paid or waived fines

    State Transitions:
        - unpaid + partial payment -> partial (status changes, amount_paid increases)
        - unpaid + full payment -> paid (status changes, paid_at timestamp set)
        - partial + payment -> paid or partial (based on whether balance remains)

    Audit Trail:
        - Records action as FEE_PAID in AuditLog
        - Captures staff member ID, patron ID, payment amount
        - Tracks status transition and new balance
        - Includes IP address and user agent for security review
    """
    # Lock fine to prevent concurrent payment race conditions
    # This ensures only one payment operation can modify this fine at a time
    result = await db.execute(
        select(Fine).where(Fine.id == fine_id).with_for_update()
    )
    fine = result.scalar_one_or_none()

    if not fine:
        logger.warning(f"Payment attempt on non-existent fine {fine_id} by staff {staff_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fine {fine_id} not found"
        )

    # Validate fine status - cannot pay already-resolved fines
    if fine.status == FineStatus.paid:
        logger.warning(
            f"Payment attempt on already-paid fine {fine_id} by staff {staff_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot pay fine {fine_id}: fine is already paid in full"
        )

    if fine.status == FineStatus.waived:
        logger.warning(
            f"Payment attempt on already-waived fine {fine_id} by staff {staff_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot pay fine {fine_id}: fine is waived"
        )

    # Get patron info for audit and response
    patron_result = await db.execute(select(User).where(User.id == fine.user_id))
    patron = patron_result.scalar_one_or_none()

    # Validate payment amount
    remaining_balance = fine.amount - fine.amount_paid
    if payment_data.amount > remaining_balance:
        logger.warning(
            f"Payment overage on fine {fine_id}: payment=${payment_data.amount} "
            f"exceeds balance=${remaining_balance} by staff {staff_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Payment of ${payment_data.amount} exceeds remaining balance of "
                f"${remaining_balance}"
            ),
        )

    # Capture state before update for audit log
    prev_status = fine.status
    prev_amount_paid = fine.amount_paid
    new_amount_paid = fine.amount_paid + payment_data.amount
    new_remaining_balance = fine.amount - new_amount_paid

    # Generate receipt number for payment tracking
    receipt_number = generate_receipt_number()

    # Create payment history record with receipt for audit trail
    payment_record = FinePaymentHistory(
        fine_id=fine.id,
        user_id=fine.user_id,
        amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        notes=payment_data.notes,
        receipt_number=receipt_number,
        processed_by_id=staff_user.id,
    )
    db.add(payment_record)

    # Update fine with payment
    fine.amount_paid = new_amount_paid

    # Determine new status
    if new_remaining_balance == 0:
        fine.status = FineStatus.paid
        fine.paid_at = datetime.now(timezone.utc)
    else:
        fine.status = FineStatus.partial

    # Add payment note with timestamp and receipt reference
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    payment_note = f"\n[{timestamp}] Payment: ${payment_data.amount}. Receipt: {receipt_number}"
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
            "receipt_number": receipt_number,
            "previous_amount_paid": str(prev_amount_paid),
            "new_amount_paid": str(new_amount_paid),
            "remaining_balance": str(new_remaining_balance),
            "previous_status": str(prev_status),
            "new_status": str(fine.status),
            "is_full_payment": new_remaining_balance == 0,
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

        # Commit payment, history record, and audit log together
        await db.commit()
        await db.refresh(fine)
        await db.refresh(payment_record)
        _track_payment("fine_payment", payment_data.amount, staff_user.id)

        log_msg = (
            f"Fine {fine_id} payment recorded by staff {staff_user.id}: "
            f"${payment_data.amount} paid, "
            f"status {str(prev_status)}->{fine.status}, "
            f"balance ${new_remaining_balance}"
        )
        logger.info(log_msg)

    except HTTPException:
        # Re-raise audit log failures
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error recording payment on fine {fine_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record payment due to database error"
        ) from e

    return FineResponse(
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


# ==================== Patron Fine Detail ====================


def _build_fine_explanation(fine, item: dict, balance) -> str:
    title = item.get("title", "Unknown item")
    item_type = item.get("item_type", "item")

    fine_type_val = fine.fine_type.value if hasattr(fine.fine_type, 'value') else fine.fine_type
    if fine_type_val == "lost_item":
        base = f"Lost item: \"{title}\" ({item_type}). Replacement fee ${fine.amount}."
    elif fine_type_val == "damaged_item":
        base = f"Damaged: \"{title}\" ({item_type}). Repair/replacement fee ${fine.amount}."
    elif fine_type_val == "overdue":
        base = f"Overdue: \"{title}\" ({item_type})."
        if fine.checkout and fine.checkout.due_date and fine.checkout.returned_at:
            days_late = (fine.checkout.returned_at.date() - fine.checkout.due_date.date()).days
            if days_late > 0:
                base += f" {days_late} day{'s' if days_late != 1 else ''} late."
    else:
        base = f"Fee: \"{title}\" ({item_type}). ${fine.amount}."

    # Add payment status
    status_val = fine.status.value if hasattr(fine.status, 'value') else str(fine.status)
    if status_val == "paid":
        base += " Paid in full."
    elif status_val == "waived":
        base += " Waived."
    elif status_val == "partial":
        base += f" ${fine.amount_paid} paid, ${balance} remaining."
    else:
        base += f" ${balance} outstanding."

    return base


@router.get("/fines/patron/{patron_id}/detail", response_model=FineDetailResponse)
async def get_patron_fines_detail(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all fines for a patron with full item/checkout context and payment history."""
    # Get patron
    patron = await db.execute(select(User).where(User.id == patron_id))
    patron_user = patron.scalar_one_or_none()
    if not patron_user:
        raise HTTPException(status_code=404, detail="Patron not found")

    # Get all fines with relationships
    fines_result = await db.execute(
        select(Fine)
        .options(
            selectinload(Fine.checkout),
            selectinload(Fine.payment_history),
            selectinload(Fine.waived_by),
        )
        .where(Fine.user_id == patron_id)
        .order_by(Fine.created_at.desc())
    )
    fines = fines_result.scalars().all()

    # For each fine, get the catalog item through the checkout
    fine_details = []
    checkout_ids = [f.checkout_id for f in fines if f.checkout_id]

    # Batch fetch catalog items through checkouts
    items_by_checkout = {}
    if checkout_ids:
        items_result = await db.execute(
            text("""
                SELECT c.id as checkout_id, ci.title, ci.author, ci.item_type, ci.barcode
                FROM checkouts c
                JOIN catalog_items ci ON c.item_id = ci.id
                WHERE c.id = ANY(:ids)
            """),
            {"ids": checkout_ids}
        )
        for row in items_result.fetchall():
            items_by_checkout[row[0]] = {
                "title": row[1], "author": row[2],
                "item_type": row[3], "barcode": row[4],
            }

    # Also batch fetch payment processor names
    processor_ids = set()
    for fine in fines:
        for payment in (fine.payment_history or []):
            if payment.processed_by_id:
                processor_ids.add(payment.processed_by_id)

    processors_by_id = {}
    if processor_ids:
        proc_result = await db.execute(select(User).where(User.id.in_(processor_ids)))
        processors_by_id = {u.id: f"{u.first_name} {u.last_name}" for u in proc_result.scalars().all()}

    total_outstanding = Decimal("0.00")

    for fine in fines:
        balance = fine.amount - fine.amount_paid
        if fine.status not in (FineStatus.paid, FineStatus.waived):
            total_outstanding += balance

        # Get item context
        item = items_by_checkout.get(fine.checkout_id, {})

        # Build explanation
        explanation = _build_fine_explanation(fine, item, balance)

        # Build payment details
        payments = []
        for p in sorted(fine.payment_history or [], key=lambda x: x.created_at):
            payments.append(FinePaymentDetail(
                id=p.id,
                amount=p.amount,
                payment_method=p.payment_method.value if hasattr(p.payment_method, 'value') else str(p.payment_method),
                notes=p.notes,
                receipt_number=p.receipt_number,
                processed_by_name=processors_by_id.get(p.processed_by_id),
                created_at=p.created_at,
            ))

        fine_details.append(FineDetailItem(
            id=fine.id,
            fine_type=fine.fine_type.value if hasattr(fine.fine_type, 'value') else str(fine.fine_type),
            status=fine.status.value if hasattr(fine.status, 'value') else str(fine.status),
            amount=fine.amount,
            amount_paid=fine.amount_paid,
            balance=balance,
            description=fine.description,
            notes=fine.notes,
            created_at=fine.created_at,
            paid_at=fine.paid_at,
            waived_at=fine.waived_at,
            waived_by_name=f"{fine.waived_by.first_name} {fine.waived_by.last_name}" if fine.waived_by else None,
            item_title=item.get("title"),
            item_author=item.get("author"),
            item_type=item.get("item_type"),
            item_barcode=item.get("barcode"),
            checked_out_at=fine.checkout.checked_out_at if fine.checkout else None,
            due_date=fine.checkout.due_date if fine.checkout else None,
            returned_at=fine.checkout.returned_at if fine.checkout else None,
            explanation=explanation,
            payments=payments,
        ))

    patron_name = f"{patron_user.first_name} {patron_user.last_name}"

    return FineDetailResponse(
        patron_id=patron_id,
        patron_name=patron_name,
        patron_email=patron_user.email,
        total_fines=len(fines),
        total_outstanding=total_outstanding,
        fines=fine_details,
    )
