# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff-Initiated Deletion Endpoints (for in-person GDPR requests)."""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.email import send_deletion_cancelled_email, send_staff_deletion_notification_email
from ....core.shortcuts import get_or_404
from ....models.audit_log import AuditAction
from ....models.user import User, UserRole
from ..auth import get_current_user
from ..dependencies import require_staff

from .schemas import DeletionEligibilityResponse, StaffDeletionRequest
from .helpers import DELETION_GRACE_PERIOD_DAYS, check_deletion_eligibility, create_audit_log

logger = get_logger(__name__)

router = APIRouter()


@router.post("/staff/initiate-deletion")
async def staff_initiate_deletion(
    request: Request,
    deletion_request: StaffDeletionRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Staff-initiated account deletion for in-person GDPR requests.

    This endpoint allows staff to process deletion requests made in person.
    Staff must confirm that patron identity has been verified.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    # Require identity verification confirmation
    if not deletion_request.identity_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Staff must confirm that patron identity has been verified in person"
        )

    # Get target patron
    patron = await get_or_404(db, User, deletion_request.patron_id, "Patron not found")

    # Prevent staff from deleting admin accounts
    if patron.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete admin accounts via this endpoint"
        )

    # Check if deletion already requested
    if patron.deletion_requested_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deletion already scheduled for {patron.deletion_scheduled_for.isoformat()}"
        )

    # Check eligibility
    eligibility = await check_deletion_eligibility(db, patron)
    if not eligibility.eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete account: {'; '.join(eligibility.blockers)}"
        )

    # Schedule deletion for 30 days from now
    now = datetime.now(timezone.utc)
    deletion_date = now + timedelta(days=DELETION_GRACE_PERIOD_DAYS)

    patron.deletion_requested_at = now
    patron.deletion_scheduled_for = deletion_date

    # Create audit log with staff information
    await create_audit_log(
        db=db,
        action=AuditAction.STAFF_INITIATED_DELETION,
        admin_id=current_user.id,
        target_user_id=patron.id,
        details={
            "deletion_type": "staff_initiated",
            "scheduled_for": deletion_date.isoformat(),
            "reason": deletion_request.reason,
            "identity_verified": True,
            "staff_member": current_user.full_name,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()

    # Send notification email to patron
    try:
        await send_staff_deletion_notification_email(
            to_email=patron.email,
            first_name=patron.first_name,
            staff_name=current_user.full_name,
            deletion_date=deletion_date.strftime("%B %d, %Y"),
            reason=deletion_request.reason,
        )
    except Exception as e:  # noqa: BLE001  # best-effort staff deletion notification email
        logger.warning(f"Failed to send staff deletion notification email: {e}")

    return {
        "message": "Patron deletion scheduled",
        "patron_id": patron.id,
        "deletion_scheduled_for": deletion_date.isoformat(),
        "notification_sent": True,
    }


@router.get("/staff/patron/{patron_id}/deletion-eligibility", response_model=DeletionEligibilityResponse)
async def staff_check_patron_deletion_eligibility(
    patron_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a patron is eligible for account deletion (staff endpoint).

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """
    # Get target patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    return await check_deletion_eligibility(db, patron)


@router.post("/staff/patron/{patron_id}/cancel-deletion")
async def staff_cancel_patron_deletion(
    request: Request,
    patron_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a scheduled patron deletion (staff endpoint).

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """
    # Get target patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    if not patron.deletion_requested_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No deletion request pending")

    # Create audit log
    await create_audit_log(
        db=db,
        action=AuditAction.GDPR_DELETION_CANCELLED,
        admin_id=current_user.id,
        target_user_id=patron.id,
        details={
            "cancelled_by": "staff",
            "staff_member": current_user.full_name,
            "originally_scheduled_for": patron.deletion_scheduled_for.isoformat() if patron.deletion_scheduled_for else None,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    patron.deletion_requested_at = None
    patron.deletion_scheduled_for = None
    await db.commit()

    # Send cancellation email to patron
    try:
        await send_deletion_cancelled_email(
            to_email=patron.email,
            first_name=patron.first_name,
        )
    except Exception as e:  # noqa: BLE001  # best-effort cancellation email
        logger.warning(f"Failed to send deletion cancellation email: {e}")

    return {
        "message": "Patron deletion cancelled",
        "patron_id": patron.id,
    }
