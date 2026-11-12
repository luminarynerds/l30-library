# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import secrets
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.error_codes import ErrorCode
from ..core.exceptions import BusinessLogicError, ConflictError, ResourceNotFoundError
from ..models.audit_log import AuditAction, AuditLog
from ..models.circulation import Checkout, CheckoutStatus
from ..models.fine import Fine, FineStatus
from ..models.lost_damaged import ClaimsReturnedDispute, ClaimDisputeStatus
from ..models.user import PatronStatus, User
from app.core.datetime_utils import utc_now
from app.core.branding import branding

logger = get_logger(__name__)

# Configurable thresholds
WAIVER_ALERT_THRESHOLD = 5  # Alert when a patron has 5+ waivers in a year
CLAIMS_DENIED_ESCALATION_THRESHOLD = 3  # Escalate when patron has 3+ denied claims


# =============================================================================
# STOLEN CARD WORKFLOW
# =============================================================================


async def report_card_stolen(
    patron_id: int,
    db: AsyncSession,
    staff_id: int,
    notes: str = "",
    issue_replacement: bool = True,
) -> dict:
    patron_result = await db.execute(
        select(User).where(User.id == patron_id).with_for_update()
    )
    patron = patron_result.scalar_one_or_none()

    if not patron:
        raise ResourceNotFoundError(
            code=ErrorCode.CATALOG_ITEM_NOT_FOUND,
            message="Patron not found",
        )

    now = utc_now()
    old_card = patron.library_card
    new_card = None

    if issue_replacement:
        # Generate a new unique card number
        chars = string.ascii_uppercase + string.digits
        new_card = f"{branding.CARD_PREFIX}-{(''.join(secrets.choice(chars) for _ in range(6)))}"
        patron.library_card = new_card

    # Count charges that were incurred while card was potentially in someone else's
    # hands. Flag any checkouts/fines created recently (last 30 days) for staff review.
    thirty_days_ago = now - timedelta(days=30)

    recent_checkouts_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.user_id == patron_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
            Checkout.due_date >= thirty_days_ago,
        )
    )
    flagged_checkout_count = recent_checkouts_result.scalar() or 0

    recent_fines_result = await db.execute(
        select(func.count(Fine.id)).where(
            Fine.user_id == patron_id,
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
            Fine.created_at >= thirty_days_ago,
        )
    )
    flagged_fine_count = recent_fines_result.scalar() or 0

    # Create audit log
    audit_log = AuditLog(
        admin_id=staff_id,
        target_user_id=patron_id,
        action=AuditAction.CARD_REPORTED_STOLEN,
        details={
            "old_card": old_card,
            "new_card": new_card,
            "report_timestamp": now.isoformat(),
            "notes": notes,
            "flagged_checkouts": flagged_checkout_count,
            "flagged_fines": flagged_fine_count,
        },
    )
    db.add(audit_log)

    if new_card:
        replace_log = AuditLog(
            admin_id=staff_id,
            target_user_id=patron_id,
            action=AuditAction.CARD_REPLACED,
            details={
                "old_card": old_card,
                "new_card": new_card,
                "reason": "stolen_card_replacement",
            },
        )
        db.add(replace_log)

    await db.flush()

    logger.warning(
        f"Card reported stolen for patron {patron_id}",
        extra={
            "patron_id": patron_id,
            "old_card": old_card,
            "new_card": new_card,
            "staff_id": staff_id,
            "flagged_checkouts": flagged_checkout_count,
            "flagged_fines": flagged_fine_count,
        },
    )

    return {
        "patron_id": patron_id,
        "old_card": old_card,
        "new_card": new_card,
        "report_timestamp": now,
        "flagged_checkouts": flagged_checkout_count,
        "flagged_fines": flagged_fine_count,
        "notes": notes,
    }


# =============================================================================
# WAIVER FREQUENCY ALERTS
# =============================================================================


async def check_waiver_frequency(
    patron_id: int,
    db: AsyncSession,
    staff_id: Optional[int] = None,
    threshold: int = WAIVER_ALERT_THRESHOLD,
) -> Optional[AuditLog]:
    current_year = utc_now().year
    year_start = datetime(current_year, 1, 1, tzinfo=timezone.utc)

    # Count waivers this year for this patron
    waiver_count_result = await db.execute(
        select(func.count(Fine.id)).where(
            Fine.user_id == patron_id,
            Fine.status == FineStatus.waived,
            Fine.waived_at >= year_start,
        )
    )
    waiver_count = waiver_count_result.scalar() or 0

    if waiver_count < threshold:
        return None

    # Check if we already created an alert this year for this patron
    existing_alert_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.target_user_id == patron_id,
            AuditLog.action == AuditAction.WAIVER_FREQUENCY_ALERT,
            AuditLog.created_at >= year_start,
        )
    )
    existing_alert_count = existing_alert_result.scalar() or 0

    if existing_alert_count > 0:
        # Already alerted this year — don't spam
        return None

    # Get distinct staff who waived fines for this patron this year
    distinct_staff_result = await db.execute(
        select(func.count(func.distinct(Fine.waived_by_id))).where(
            Fine.user_id == patron_id,
            Fine.status == FineStatus.waived,
            Fine.waived_at >= year_start,
        )
    )
    distinct_staff_count = distinct_staff_result.scalar() or 0

    # Total amount waived this year
    waived_amount_result = await db.execute(
        select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), Decimal("0.00"))).where(
            Fine.user_id == patron_id,
            Fine.status == FineStatus.waived,
            Fine.waived_at >= year_start,
        )
    )
    waived_amount = waived_amount_result.scalar() or Decimal("0.00")

    alert = AuditLog(
        admin_id=staff_id,
        target_user_id=patron_id,
        action=AuditAction.WAIVER_FREQUENCY_ALERT,
        details={
            "waivers_this_year": waiver_count,
            "threshold": threshold,
            "distinct_staff_involved": distinct_staff_count,
            "total_amount_waived": str(waived_amount),
            "year": current_year,
            "message": (
                f"Patron has had {waiver_count} fines waived this year "
                f"(threshold: {threshold}) by {distinct_staff_count} different staff member(s). "
                f"Total waived: ${waived_amount:.2f}. Review for possible waiver-shopping."
            ),
        },
    )
    db.add(alert)
    await db.flush()

    logger.warning(
        f"Waiver frequency alert for patron {patron_id}: "
        f"{waiver_count} waivers this year by {distinct_staff_count} staff",
        extra={
            "patron_id": patron_id,
            "waiver_count": waiver_count,
            "distinct_staff": distinct_staff_count,
            "waived_amount": str(waived_amount),
        },
    )

    return alert


# =============================================================================
# CLAIMS-RETURNED ESCALATION
# =============================================================================


async def check_claims_returned_escalation(
    patron_id: int,
    db: AsyncSession,
    staff_id: Optional[int] = None,
    threshold: int = CLAIMS_DENIED_ESCALATION_THRESHOLD,
) -> Optional[AuditLog]:
    # Count denied claims for this patron (all time)
    denied_count_result = await db.execute(
        select(func.count(ClaimsReturnedDispute.id)).where(
            ClaimsReturnedDispute.patron_id == patron_id,
            ClaimsReturnedDispute.status == ClaimDisputeStatus.DENIED,
        )
    )
    denied_count = denied_count_result.scalar() or 0

    if denied_count < threshold:
        return None

    # Count total claims
    total_count_result = await db.execute(
        select(func.count(ClaimsReturnedDispute.id)).where(
            ClaimsReturnedDispute.patron_id == patron_id,
        )
    )
    total_count = total_count_result.scalar() or 0

    # Count approved claims
    approved_count = total_count - denied_count

    # Check if we already escalated for this patron at this denial count level
    # (we escalate at each threshold increment: 3, 6, 9, etc.)
    escalation_level = (denied_count // threshold)
    existing_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.target_user_id == patron_id,
            AuditLog.action == AuditAction.CLAIMS_RETURNED_ESCALATION,
        )
    )
    existing_count = existing_result.scalar() or 0

    if existing_count >= escalation_level:
        return None

    denial_rate = (denied_count / total_count * 100) if total_count > 0 else 0

    alert = AuditLog(
        admin_id=staff_id,
        target_user_id=patron_id,
        action=AuditAction.CLAIMS_RETURNED_ESCALATION,
        details={
            "denied_claims": denied_count,
            "total_claims": total_count,
            "approved_claims": approved_count,
            "denial_rate_percent": round(denial_rate, 1),
            "escalation_threshold": threshold,
            "escalation_level": escalation_level,
            "message": (
                f"Patron has {denied_count} denied claims-returned disputes out of "
                f"{total_count} total ({denial_rate:.0f}% denial rate). "
                f"This exceeds the escalation threshold of {threshold}. "
                f"Supervisor review recommended."
            ),
        },
    )
    db.add(alert)
    await db.flush()

    logger.warning(
        f"Claims-returned escalation for patron {patron_id}: "
        f"{denied_count}/{total_count} claims denied ({denial_rate:.0f}%)",
        extra={
            "patron_id": patron_id,
            "denied_count": denied_count,
            "total_count": total_count,
            "denial_rate": round(denial_rate, 1),
        },
    )

    return alert
