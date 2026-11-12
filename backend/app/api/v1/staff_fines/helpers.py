# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff Fines - Helper functions for fine operations."""

from app.core.logging import get_logger
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....models.audit_log import AuditLog, AuditAction
from ....models.fine import Fine, PaymentPlanFrequency
from ....models.user import User

logger = get_logger(__name__)


def _track_payment(payment_type: str, amount: Decimal, staff_id: int) -> None:
    try:
        from ....core.metrics import increment
        increment("payment_total", {"type": payment_type, "status": "success"})
        increment("payment_amount_cents_total", {"type": payment_type}, int(amount * 100))
    except Exception as e:  # noqa: BLE001  # metric emit best-effort
        logger.warning(
            "Failed to emit payment metrics for %s (amount: %s): %s",
            payment_type,
            amount,
            e,
            exc_info=False
        )
        # Don't raise - payment still recorded in DB, but metrics emission failed
    logger.info(
        f"Payment recorded: {payment_type}",
        extra={"payment_type": payment_type, "amount": str(amount), "staff_id": staff_id},
    )


def generate_receipt_number() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:6].upper()
    return f"RCP-{timestamp}-{unique_id}"


def calculate_next_payment_date(frequency: PaymentPlanFrequency, from_date: datetime = None) -> datetime:
    base_date = from_date or datetime.now(timezone.utc)
    if frequency == PaymentPlanFrequency.weekly:
        return base_date + timedelta(weeks=1)
    elif frequency == PaymentPlanFrequency.biweekly:
        return base_date + timedelta(weeks=2)
    else:  # monthly
        # Add approximately one month
        return base_date + timedelta(days=30)


async def create_fine_audit_log(
    db: AsyncSession,
    action: AuditAction,
    staff_user: User,
    patron_user: User,
    fine: Fine,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    try:
        # Extract IP and user agent from request if available
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", None)

        audit_log = AuditLog(
            admin_id=staff_user.id,
            target_user_id=patron_user.id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_log)
        await db.flush()  # Ensure log is persisted even if main transaction rolls back
        logger.info(
            f"Audit log created for fine {fine.id}: action={action.value}, "
            f"staff={staff_user.id}, patron={patron_user.id}"
        )
        return audit_log
    except Exception as e:
        # Log the error but don't fail the main operation
        logger.error(
            f"Failed to create audit log for fine {fine.id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record audit trail for this operation",
        ) from e
