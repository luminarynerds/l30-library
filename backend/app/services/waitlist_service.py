# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.computer import ComputerWaitlist, ComputerWaitlistStatus, Computer

logger = get_logger(__name__)


async def join_waitlist(
    db: AsyncSession,
    patron_id: int,
    computer_id: int,
    desired_duration_minutes: int = 60,
) -> ComputerWaitlist:
    # Check not already on waitlist
    existing = await db.execute(
        select(ComputerWaitlist).where(
            and_(
                ComputerWaitlist.patron_id == patron_id,
                ComputerWaitlist.computer_id == computer_id,
                ComputerWaitlist.status == ComputerWaitlistStatus.pending,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already on waitlist for this computer"
        )

    # Get current max position
    result = await db.execute(
        select(func.max(ComputerWaitlist.queue_position)).where(
            and_(
                ComputerWaitlist.computer_id == computer_id,
                ComputerWaitlist.status == ComputerWaitlistStatus.pending,
            )
        )
    )
    max_pos = result.scalar() or 0

    now = datetime.now(timezone.utc)
    entry = ComputerWaitlist(
        computer_id=computer_id,
        patron_id=patron_id,
        desired_start_time=now,
        desired_duration_minutes=desired_duration_minutes,
        queue_position=max_pos + 1,
        status=ComputerWaitlistStatus.pending,
        expires_at=now + timedelta(hours=24),
    )

    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    logger.info(f"Patron {patron_id} joined waitlist for computer {computer_id} at position {entry.queue_position}")
    return entry


async def get_position(
    db: AsyncSession,
    patron_id: int,
    computer_id: Optional[int] = None,
) -> Optional[ComputerWaitlist]:
    query = select(ComputerWaitlist).where(
        and_(
            ComputerWaitlist.patron_id == patron_id,
            ComputerWaitlist.status == ComputerWaitlistStatus.pending,
        )
    )
    if computer_id:
        query = query.where(ComputerWaitlist.computer_id == computer_id)

    result = await db.execute(query.order_by(ComputerWaitlist.created_at.desc()).limit(1))
    return result.scalar_one_or_none()


async def advance_waitlist(db: AsyncSession, computer_id: int) -> Optional[ComputerWaitlist]:
    result = await db.execute(
        select(ComputerWaitlist).where(
            and_(
                ComputerWaitlist.computer_id == computer_id,
                ComputerWaitlist.status == ComputerWaitlistStatus.pending,
            )
        ).order_by(ComputerWaitlist.queue_position).limit(1)
    )
    next_entry = result.scalar_one_or_none()

    if next_entry:
        next_entry.status = ComputerWaitlistStatus.notified
        next_entry.notified_at = datetime.now(timezone.utc)
        next_entry.notification_method = "in_person"
        await db.commit()
        await db.refresh(next_entry)
        logger.info(f"Notified patron {next_entry.patron_id} from waitlist for computer {computer_id}")

    return next_entry
