# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.computer import (
    Computer, ComputerReservation, ComputerStatus,
    ComputerReservationStatus, SessionExtensionRequest, ExtensionStatus,
)
from app.models.cipa_compliance import ComputerSession

logger = get_logger(__name__)


async def start_session(
    db: AsyncSession,
    patron_id: int,
    computer_id: int,
    duration_minutes: int = 60,
) -> ComputerReservation:
    # Check computer is available
    computer = await db.get(Computer, computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    if computer.status != ComputerStatus.available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Computer is currently {computer.status}"
        )

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(minutes=min(duration_minutes, computer.max_session_minutes))

    reservation = ComputerReservation(
        computer_id=computer_id,
        patron_id=patron_id,
        reserved_start_time=now,
        reserved_end_time=end_time,
        session_duration_minutes=duration_minutes,
        status=ComputerReservationStatus.in_session,
        checked_in_at=now,
        actual_start_time=now,
    )

    computer.status = ComputerStatus.in_use

    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)

    logger.info(f"Session started for patron {patron_id} on computer {computer_id}")
    return reservation


async def get_current_session(
    db: AsyncSession,
    patron_id: int,
) -> Optional[ComputerReservation]:
    result = await db.execute(
        select(ComputerReservation).where(
            and_(
                ComputerReservation.patron_id == patron_id,
                ComputerReservation.status == ComputerReservationStatus.in_session,
            )
        )
    )
    return result.scalar_one_or_none()


async def extend_session(
    db: AsyncSession,
    patron_id: int,
    extra_minutes: int = 30,
) -> ComputerReservation:
    # Lock the reservation row to prevent concurrent extension limit bypass
    result = await db.execute(
        select(ComputerReservation).where(
            and_(
                ComputerReservation.patron_id == patron_id,
                ComputerReservation.status == ComputerReservationStatus.in_session,
            )
        ).with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="No active session found")

    computer = await db.get(Computer, reservation.computer_id)
    if not computer or not computer.is_extendable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session extension is not available for this computer"
        )

    if reservation.extensions_used >= (computer.max_extensions_per_day or 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum extensions reached"
        )

    max_ext = computer.max_extension_minutes or 60
    extra_minutes = min(extra_minutes, max_ext)

    new_end_time = reservation.reserved_end_time + timedelta(minutes=extra_minutes)
    reservation.reserved_end_time = new_end_time
    reservation.extended_until = new_end_time
    reservation.extensions_used += 1
    reservation.extension_requested = True

    await db.commit()
    await db.refresh(reservation)

    logger.info(f"Session extended by {extra_minutes}min for patron {patron_id}")
    return reservation


async def end_session(
    db: AsyncSession,
    patron_id: int,
) -> ComputerReservation:
    # Lock the reservation to prevent concurrent end_session calls
    result = await db.execute(
        select(ComputerReservation).where(
            and_(
                ComputerReservation.patron_id == patron_id,
                ComputerReservation.status == ComputerReservationStatus.in_session,
            )
        ).with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="No active session found")

    now = datetime.now(timezone.utc)
    reservation.status = ComputerReservationStatus.completed
    reservation.actual_end_time = now

    # Lock computer row before status change
    comp_result = await db.execute(
        select(Computer).where(Computer.id == reservation.computer_id).with_for_update()
    )
    computer = comp_result.scalar_one_or_none()
    if computer:
        computer.status = ComputerStatus.available

    await db.commit()
    await db.refresh(reservation)

    logger.info(f"Session ended for patron {patron_id}")
    return reservation


async def expire_sessions(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ComputerReservation).where(
            and_(
                ComputerReservation.status == ComputerReservationStatus.in_session,
                ComputerReservation.reserved_end_time <= now,
            )
        ).with_for_update(skip_locked=True)
    )
    expired = list(result.scalars().all())

    count = 0
    for reservation in expired:
        reservation.status = ComputerReservationStatus.completed
        reservation.actual_end_time = now
        comp_result = await db.execute(
            select(Computer).where(Computer.id == reservation.computer_id).with_for_update()
        )
        computer = comp_result.scalar_one_or_none()
        if computer:
            computer.status = ComputerStatus.available
        count += 1

    if count > 0:
        await db.commit()
        logger.info(f"Auto-expired {count} computer sessions")

    return count


async def process_no_shows(db: AsyncSession, grace_minutes: int = 15) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=grace_minutes)
    result = await db.execute(
        select(ComputerReservation).where(
            and_(
                ComputerReservation.status == ComputerReservationStatus.confirmed,
                ComputerReservation.reserved_start_time <= cutoff,
                ComputerReservation.checked_in_at.is_(None),
            )
        ).with_for_update(skip_locked=True)
    )
    no_shows = list(result.scalars().all())

    count = 0
    for reservation in no_shows:
        reservation.status = ComputerReservationStatus.no_show
        comp_result = await db.execute(
            select(Computer).where(Computer.id == reservation.computer_id).with_for_update()
        )
        computer = comp_result.scalar_one_or_none()
        if computer and computer.status == ComputerStatus.reserved:
            computer.status = ComputerStatus.available
        count += 1

    if count > 0:
        await db.commit()
        logger.info(f"Processed {count} no-shows")

    return count
