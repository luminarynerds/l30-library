# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Background job endpoints: process-expired-holds, process-overdue-fines,
resolve-checkout-problem."""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.datetime_utils import utc_now

from ....core.cache import invalidate_catalog_cache
from ....core.database import get_db
from ....core.error_codes import ErrorCode
from ....core.exceptions import InternalServerError
from ....core.shortcuts import get_or_404
from ....models.circulation import Checkout, CheckoutStatus
from ....models.fine import Fine, FineType
from ....models.user import User, UserRole
from ....schemas.circulation import (
    ProblemResolutionRequest,
    ProblemResolutionResponse,
)
from ....schemas.common import JobResponse
from ....services.checkout_service import send_pending_hold_notification
from ....services.fine_service import check_and_create_overdue_fine
from ....services.hold_service import process_expired_holds_collecting_notifications
from ..auth import get_current_user
from ..dependencies import require_admin, require_staff

logger = get_logger(__name__)

router = APIRouter()


@router.post("/holds/process-expired", response_model=JobResponse, status_code=200)
async def process_expired_holds_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process all expired holds - staff/admin only.

    This endpoint transitions expired holds to 'expired' status and
    advances the hold queue for each affected item.
    """
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="This action requires a staff account. Please ask a librarian for help.")

    expired_count, pending_notifications = await process_expired_holds_collecting_notifications(db)
    await db.commit()

    # Send hold-ready notifications AFTER commit so we never email a patron
    # about a hold that didn't actually persist (mirrors return_checkout pattern).
    notifications_sent = 0
    for notification in pending_notifications:
        try:
            await send_pending_hold_notification(notification)
            notifications_sent += 1
        except Exception:
            logger.exception(
                "Failed to send hold-ready notification after expired-hold processing"
            )

    # Invalidate catalog cache since item statuses may have changed
    if expired_count > 0:
        await invalidate_catalog_cache()

    return JobResponse(
        status="completed",
        message=f"Processed {expired_count} expired hold(s)",
        result={
            "expired_count": expired_count,
            "notifications_sent": notifications_sent,
        },
    )


@router.post("/jobs/process-expired-holds")
async def job_process_expired_holds(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Background job endpoint to process all expired holds system-wide.

    Requires admin authentication.

    This should be called periodically by a scheduler (e.g., cron, celery beat)
    to ensure expired holds are processed even when no user operations trigger them.

    Recommended frequency: every 15-60 minutes.

    Returns count of expired holds processed and items made available.
    """
    processed_count, pending_notifications = await process_expired_holds_collecting_notifications(db)
    await db.commit()

    # Send hold-ready notifications AFTER commit so we never email a patron
    # about a hold that didn't actually persist (mirrors return_checkout pattern).
    # This closes the silent-promotion gap where the cron promoted patrons to
    # 'ready' without telling them, so the hold expired before pickup.
    notifications_sent = 0
    for notification in pending_notifications:
        try:
            await send_pending_hold_notification(notification)
            notifications_sent += 1
        except Exception:
            logger.exception(
                "Failed to send hold-ready notification after expired-hold processing"
            )

    # Invalidate catalog cache since item statuses may have changed
    if processed_count > 0:
        await invalidate_catalog_cache()

    return {
        "ok": True,
        "message": f"Processed {processed_count} expired hold(s)",
        "expired_holds_processed": processed_count,
        "notifications_sent": notifications_sent,
        "triggered_by": admin_user.email,
    }


@router.post("/jobs/process-overdue-fines")
async def job_process_overdue_fines(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Background job endpoint to update fines for all overdue checkouts.

    Requires admin authentication.

    This should be called periodically by a scheduler to ensure fines
    are updated as items become more overdue, and reading minutes are
    added incrementally.

    Recommended frequency: once daily (e.g., at midnight).

    Returns count of checkouts processed and fines created/updated.
    """
    # Find all overdue checkouts with eager-loaded users to avoid N+1 queries
    now = utc_now()
    result = await db.execute(
        select(Checkout)
        .options(selectinload(Checkout.user))
        .where(
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
            Checkout.due_date < now,
        )
    )
    overdue_checkouts = result.scalars().all()

    fines_created = 0
    fines_updated = 0
    reading_minutes_added = 0
    errors = []

    for checkout in overdue_checkouts:
        # User is already loaded via selectinload
        user = checkout.user

        if not user:
            continue

        try:
            # Track reading minutes before
            old_minutes = user.reading_minutes_owed

            # Check for existing fine
            existing_fine_result = await db.execute(
                select(Fine).where(
                    Fine.checkout_id == checkout.id,
                    Fine.fine_type == FineType.overdue,
                )
            )
            existing_fine = existing_fine_result.scalar_one_or_none()
            old_fine_amount = existing_fine.amount if existing_fine else None

            # Process the checkout
            fine = await check_and_create_overdue_fine(checkout, db, user)

            # Track what changed
            if fine:
                if old_fine_amount is None:
                    fines_created += 1
                elif fine.amount > old_fine_amount:
                    fines_updated += 1

            if user.reading_minutes_owed > old_minutes:
                reading_minutes_added += user.reading_minutes_owed - old_minutes
        except Exception as e:  # noqa: BLE001  # per-checkout fine processing — record failure and continue
            logger.error(
                f"Failed to process overdue fine for checkout {checkout.id} "
                f"(user {user.id}): {e}"
            )
            errors.append({
                "checkout_id": checkout.id,
                "user_id": user.id,
                "error": str(e),
            })

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to commit overdue fine batch processing")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None

    result = {
        "ok": len(errors) == 0,
        "message": f"Processed {len(overdue_checkouts)} overdue checkout(s)",
        "checkouts_processed": len(overdue_checkouts),
        "fines_created": fines_created,
        "fines_updated": fines_updated,
        "reading_minutes_added": reading_minutes_added,
        "triggered_by": admin_user.email,
    }

    if errors:
        result["message"] = (
            f"Processed {len(overdue_checkouts)} overdue checkout(s) "
            f"with {len(errors)} error(s)"
        )
        result["errors"] = errors

    return result


@router.post("/resolve-problem")
async def resolve_checkout_problem(
    request: ProblemResolutionRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a one-click resolution for a checkout problem.

    Staff endpoint to resolve checkout issues like:
    - Override holds, expired cards, fines, checkout limits
    - Waive outstanding fines
    - Record fine payments
    - Swap items (return one, checkout new)
    - Renew patron's library card
    - Update item status

    Args:
        request: ProblemResolutionRequest with problem_type, action_type, and input_data
        staff_user: The staff user performing the action
        db: Database session

    Returns:
        ProblemResolutionResponse with success status and message
    """
    from ....services.checkout_resolution_actions import ResolutionActionHandler

    # Get patron_id from input_data (frontend sends it)
    patron_id = request.input_data.get("patron_id") if request.input_data else None
    if not patron_id:
        raise HTTPException(status_code=400, detail="A patron account is needed to complete this action. Please select a patron.")

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    handler = ResolutionActionHandler(db)
    success, message, additional_data = await handler.execute_action(
        problem_type=request.problem_type,
        action_type=request.action_type,
        patron=patron,
        input_data=request.input_data,
    )

    return ProblemResolutionResponse(
        success=success,
        message=message,
        action_type=request.action_type,
        problem_type=request.problem_type,
        additional_data=additional_data,
    )
