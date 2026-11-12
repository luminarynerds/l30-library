# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Circulation helper/utility functions used by endpoint modules."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.authorization import check_fine_block, get_user_role_settings
from ....core.database import get_db
from ....models.circulation import Hold, HoldStatus
from ....models.multi_branch import Branch
from ....models.user import User

HOLD_EXPIRY_DAYS = 7


async def get_user_hold_expiry(user, db):
    settings = await get_user_role_settings(user, db)
    return settings.hold_duration_days if settings else HOLD_EXPIRY_DAYS


async def check_hold_limit(user, db):
    settings = await get_user_role_settings(user, db)
    max_holds = settings.max_holds if settings else 5

    # Lock the user's active holds to prevent race condition
    result = await db.execute(
        select(Hold.id)
        .where(
            Hold.user_id == user.id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
        .with_for_update()
    )
    holds = result.scalars().all()
    current_count = len(holds)

    if current_count >= max_holds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have {current_count} items on hold, which is your maximum of {max_holds}. To place a new hold, cancel at least 1 existing hold first. Go to My Account > Holds to manage your holds.",
        )


async def validate_pickup_location(db: AsyncSession, pickup_location_id: int | None) -> None:
    if pickup_location_id is None:
        return

    branch_result = await db.execute(
        select(Branch.id).where(Branch.id == pickup_location_id)
    )
    if branch_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"That pickup location isn't available. Please choose a different branch.",
        )
