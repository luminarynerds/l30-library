# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.fine import Fine, FineStatus
from ..models.user import User, UserRole


# =============================================================================
# Generic Helpers
# =============================================================================


async def _fetch_patrons_by_ids(
    db: AsyncSession,
    patron_ids: list[int],
) -> list[User]:
    result = await db.execute(
        select(User).where(
            User.id.in_(patron_ids),
            User.role == UserRole.PATRON,
        )
    )
    return list(result.scalars().all())


def _collect_missing_ids(
    requested_ids: list[int],
    processed_ids: set[int],
    failed_ids: list[int],
) -> list[int]:
    for patron_id in requested_ids:
        if patron_id not in processed_ids and patron_id not in failed_ids:
            failed_ids.append(patron_id)
    return failed_ids


# =============================================================================
# Bulk Block / Unblock
# =============================================================================


async def bulk_block_patrons(
    db: AsyncSession,
    patron_ids: list[int],
    blocked: bool,
    reason: str | None = None,
) -> dict[str, Any]:
    patrons = await _fetch_patrons_by_ids(db, patron_ids)

    processed_ids: set[int] = set()
    failed_ids: list[int] = []

    for patron in patrons:
        try:
            patron.is_active = not blocked
            processed_ids.add(patron.id)
        except Exception:  # noqa: BLE001 - per-iteration boundary — single patron failure must not crash bulk block
            failed_ids.append(patron.id)

    # Collect IDs that were not found in the database
    _collect_missing_ids(patron_ids, processed_ids, failed_ids)

    await db.commit()

    action = "blocked" if blocked else "unblocked"
    return {
        "success": len(failed_ids) == 0,
        "processed_count": len(processed_ids),
        "failed_ids": failed_ids,
        "message": f"Successfully {action} {len(processed_ids)} patron(s)",
    }


# =============================================================================
# Bulk Waive Fines
# =============================================================================


async def bulk_waive_fines(
    db: AsyncSession,
    patron_ids: list[int],
    staff_user_id: int,
    reason: str = "Amnesty Day - Bulk Fine Waiver",
) -> dict[str, Any]:
    result = await db.execute(
        select(Fine).where(
            Fine.user_id.in_(patron_ids),
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
        )
    )
    fines = result.scalars().all()

    fines_waived = 0
    total_amount = Decimal("0.00")
    processed_patron_ids: set[int] = set()
    failed_ids: list[int] = []

    for fine in fines:
        try:
            remaining_balance = fine.amount - fine.amount_paid
            total_amount += remaining_balance
            fine.status = FineStatus.waived
            fine.waived_at = datetime.now(timezone.utc)
            fine.waived_by_id = staff_user_id
            fine.notes = (fine.notes or "") + f"\nBulk waived: {reason}"
            fines_waived += 1
            processed_patron_ids.add(fine.user_id)
        except Exception:  # noqa: BLE001 - per-iteration boundary — single fine failure must not crash bulk waive
            if fine.user_id not in failed_ids:
                failed_ids.append(fine.user_id)

    await db.commit()

    return {
        "success": len(failed_ids) == 0,
        "patrons_processed": len(processed_patron_ids),
        "fines_waived": fines_waived,
        "total_amount_waived": total_amount,
        "failed_ids": failed_ids,
        "message": (
            f"Waived {fines_waived} fine(s) totaling ${total_amount:.2f} "
            f"for {len(processed_patron_ids)} patron(s)"
        ),
    }


# =============================================================================
# Bulk Notify
# =============================================================================


async def bulk_send_notification(
    db: AsyncSession,
    patron_ids: list[int],
    subject: str,
    message: str,
    notification_type: str = "general",
) -> dict[str, Any]:
    result = await db.execute(
        select(User).where(
            User.id.in_(patron_ids),
            User.role == UserRole.PATRON,
            User.email.isnot(None),
        )
    )
    patrons = result.scalars().all()

    sent_count = 0
    failed_ids: list[int] = []

    for patron in patrons:
        try:
            # Simulated email sending - in production, integrate with email service
            # await send_email(patron.email, subject, message)
            sent_count += 1
        except Exception:  # noqa: BLE001 - per-iteration boundary — single notification failure must not crash bulk notify
            failed_ids.append(patron.id)

    # Find patron IDs that were not found
    found_ids = {p.id for p in patrons}
    _collect_missing_ids(patron_ids, found_ids, failed_ids)

    return {
        "success": len(failed_ids) == 0,
        "sent_count": sent_count,
        "failed_ids": failed_ids,
        "message": f"Notification queued for {sent_count} patron(s)",
    }


# =============================================================================
# Validation Helpers
# =============================================================================


def validate_bulk_request(patron_ids: list[int], max_size: int = 100) -> None:
    if not patron_ids:
        raise ValueError("No patron IDs provided")
    if len(patron_ids) > max_size:
        raise ValueError(f"Maximum {max_size} patrons per bulk operation")
