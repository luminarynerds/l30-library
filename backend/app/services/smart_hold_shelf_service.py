# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from app.core.logging import get_logger
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..core.circulation_config import HOLD_EXPIRY_DAYS
from ..models.catalog import CatalogItem
from ..models.circulation import Hold, HoldStatus
from ..models.multi_branch import Branch, BranchSettings
from ..models.user import User
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)

# Extension granted when patron says "on my way" (hours)
ON_WAY_EXTENSION_HOURS = 4
# How long the on-way flag stays active before we ignore it (hours)
ON_WAY_STALE_HOURS = 6


def generate_qr_pickup_code() -> str:
    return secrets.token_urlsafe(12)


async def assign_shelf_slot(
    hold: Hold,
    db: AsyncSession,
) -> str:
    branch_id = hold.pickup_location_id

    # Get existing occupied slots for this branch
    occupied_result = await db.execute(
        select(Hold.shelf_slot)
        .where(
            Hold.pickup_location_id == branch_id,
            Hold.status == HoldStatus.ready,
            Hold.shelf_slot.isnot(None),
        )
    )
    occupied_slots = {row[0] for row in occupied_result.all()}

    # Get branch capacity (default 500) to size the slot grid
    capacity = 500
    if branch_id:
        settings_result = await db.execute(
            select(BranchSettings).where(BranchSettings.branch_id == branch_id)
        )
        settings = settings_result.scalar_one_or_none()
        if settings and hasattr(settings, "hold_shelf_capacity") and settings.hold_shelf_capacity:
            capacity = settings.hold_shelf_capacity

    # Generate slot labels up to capacity
    # Each section letter holds 20 slots
    slots_per_section = 20
    sections_needed = (capacity // slots_per_section) + 1

    for section_idx in range(sections_needed):
        letter = chr(ord("A") + section_idx)
        for num in range(1, slots_per_section + 1):
            slot = f"{letter}-{num:02d}"
            if slot not in occupied_slots:
                hold.shelf_slot = slot
                return slot

    # Fallback: use hold ID-based slot
    fallback = f"Z-{hold.id:04d}"
    hold.shelf_slot = fallback
    return fallback


async def ensure_qr_code(hold: Hold, db: AsyncSession) -> str:
    if hold.qr_pickup_code:
        return hold.qr_pickup_code

    code = generate_qr_pickup_code()
    hold.qr_pickup_code = code
    return code


async def get_expiring_holds_sorted(
    db: AsyncSession,
    branch_id: int | None = None,
    hours_threshold: int = 48,
) -> list[Hold]:
    now = utc_now()
    threshold = now + timedelta(hours=hours_threshold)

    query = (
        select(Hold)
        .options(joinedload(Hold.user), joinedload(Hold.item))
        .where(
            Hold.status == HoldStatus.ready,
            Hold.expires_at.isnot(None),
            Hold.expires_at <= threshold,
            Hold.expires_at > now,
        )
        .order_by(Hold.expires_at.asc())
    )

    if branch_id is not None:
        query = query.where(Hold.pickup_location_id == branch_id)

    result = await db.execute(query)
    return list(result.unique().scalars().all())


async def mark_patron_on_way(
    hold: Hold,
    db: AsyncSession,
) -> datetime | None:
    now = utc_now()
    hold.patron_on_way = True
    hold.patron_on_way_at = now

    extended = None
    # Extend expiration if it's within ON_WAY_EXTENSION_HOURS of expiring
    if hold.expires_at:
        expires_utc = hold.expires_at
        if expires_utc.tzinfo is None:
            expires_utc = expires_utc.replace(tzinfo=timezone.utc)

        time_remaining = expires_utc - now
        if time_remaining < timedelta(hours=ON_WAY_EXTENSION_HOURS):
            hold.expires_at = now + timedelta(hours=ON_WAY_EXTENSION_HOURS)
            extended = hold.expires_at

    return extended


async def record_no_show(
    hold: Hold,
    db: AsyncSession,
) -> int:
    hold.no_show_count = (hold.no_show_count or 0) + 1
    hold.patron_on_way = False
    hold.patron_on_way_at = None
    return hold.no_show_count


async def requeue_hold_after_no_show(
    hold: Hold,
    db: AsyncSession,
) -> int:
    # Record the no-show
    await record_no_show(hold, db)

    # Clear ready-state fields
    hold.status = HoldStatus.pending
    hold.notified_at = None
    hold.expires_at = None
    hold.reminder_sent_at = None
    hold.shelf_slot = None
    hold.qr_pickup_code = None
    hold.patron_on_way = False
    hold.patron_on_way_at = None

    # Get the next available position for this item
    position_result = await db.execute(
        select(func.coalesce(func.max(Hold.position), 0))
        .where(
            Hold.item_id == hold.item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            Hold.id != hold.id,
        )
    )
    max_position = position_result.scalar() or 0
    hold.position = max_position + 1

    # Make item available for next hold promotion
    item_result = await db.execute(
        select(CatalogItem)
        .where(CatalogItem.id == hold.item_id)
        .with_for_update()
    )
    item = item_result.scalar_one_or_none()

    # Promote next pending hold (which may be different from this one)
    next_result = await db.execute(
        select(Hold)
        .where(
            Hold.item_id == hold.item_id,
            Hold.status == HoldStatus.pending,
            Hold.id != hold.id,
        )
        .order_by(Hold.position)
        .limit(1)
        .with_for_update()
    )
    next_hold = next_result.scalar_one_or_none()

    if next_hold:
        next_hold.status = HoldStatus.ready
        next_hold.notified_at = utc_now()
        next_hold.expires_at = utc_now() + timedelta(days=HOLD_EXPIRY_DAYS)
    if item:
        from .hold_service import recompute_title_availability

        await recompute_title_availability(item, db)

    return hold.position


async def get_shelf_capacity_with_expiring(
    branch_id: int,
    db: AsyncSession,
) -> dict:
    now = utc_now()
    end_of_today = now.replace(hour=23, minute=59, second=59)
    end_of_tomorrow = end_of_today + timedelta(days=1)

    # Get branch
    branch_result = await db.execute(
        select(Branch).where(Branch.id == branch_id)
    )
    branch = branch_result.scalar_one_or_none()
    if not branch:
        return {}

    # Get settings
    settings_result = await db.execute(
        select(BranchSettings).where(BranchSettings.branch_id == branch_id)
    )
    settings = settings_result.scalar_one_or_none()

    capacity_limit = settings.hold_shelf_capacity if settings else 500
    warning_threshold = settings.hold_shelf_warning_threshold if settings else 80

    # Count ready holds
    ready_count_result = await db.execute(
        select(func.count(Hold.id)).where(
            Hold.status == HoldStatus.ready,
            Hold.pickup_location_id == branch_id,
        )
    )
    ready_count = ready_count_result.scalar() or 0

    # Count expiring today
    expiring_today_result = await db.execute(
        select(func.count(Hold.id)).where(
            Hold.status == HoldStatus.ready,
            Hold.pickup_location_id == branch_id,
            Hold.expires_at.isnot(None),
            Hold.expires_at <= end_of_today,
            Hold.expires_at > now,
        )
    )
    expiring_today = expiring_today_result.scalar() or 0

    # Count expiring tomorrow
    expiring_tomorrow_result = await db.execute(
        select(func.count(Hold.id)).where(
            Hold.status == HoldStatus.ready,
            Hold.pickup_location_id == branch_id,
            Hold.expires_at.isnot(None),
            Hold.expires_at > end_of_today,
            Hold.expires_at <= end_of_tomorrow,
        )
    )
    expiring_tomorrow = expiring_tomorrow_result.scalar() or 0

    capacity_pct = (ready_count / capacity_limit * 100) if capacity_limit > 0 else 0

    return {
        "branch_id": branch_id,
        "branch_name": branch.name,
        "ready_holds_count": ready_count,
        "capacity_limit": capacity_limit,
        "capacity_percentage": round(capacity_pct, 2),
        "is_at_capacity": ready_count >= capacity_limit,
        "is_over_warning": capacity_pct >= warning_threshold,
        "warning_threshold_percentage": warning_threshold,
        "available_slots": max(0, capacity_limit - ready_count),
        "expiring_today_count": expiring_today,
        "expiring_tomorrow_count": expiring_tomorrow,
    }


async def auto_assign_slot_and_qr(
    hold: Hold,
    db: AsyncSession,
) -> tuple[str, str]:
    slot = await assign_shelf_slot(hold, db)
    qr_code = await ensure_qr_code(hold, db)
    return slot, qr_code


async def generate_hold_shelf_slip_data(
    hold: Hold,
    db: AsyncSession,
) -> dict:
    # Always query explicitly to avoid sync lazy-load in async context
    user_result = await db.execute(
        select(User).where(User.id == hold.user_id)
    )
    user = user_result.scalar_one_or_none()

    item_result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == hold.item_id)
    )
    item = item_result.scalar_one_or_none()

    # Get pickup location name
    pickup_name = None
    if hold.pickup_location_id:
        branch_result = await db.execute(
            select(Branch.name).where(Branch.id == hold.pickup_location_id)
        )
        pickup_name = branch_result.scalar_one_or_none()

    patron_initials = ""
    if user:
        if user.first_name:
            patron_initials += user.first_name[0].upper()
        if user.last_name:
            patron_initials += user.last_name[0].upper()

    return {
        "hold_id": hold.id,
        "item_title": item.title if item else "Unknown",
        "item_author": item.author if item else None,
        "call_number": item.call_number if item else None,
        "patron_initials": patron_initials or "?",
        "patron_name": user.full_name if user else "Unknown",
        "shelf_slot": hold.shelf_slot,
        "expires_at": hold.expires_at,
        "qr_pickup_code": hold.qr_pickup_code,
        "barcode": item.barcode if item else None,
        "pickup_location": pickup_name,
    }
