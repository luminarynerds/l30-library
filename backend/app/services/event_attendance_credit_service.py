# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceCheckIn, AttendanceSession
from app.models.reading import (
    EventReadingProgramCredit,
    ReadingLogEntry,
    ReadingRegistration,
)

logger = get_logger(__name__)


async def grant_event_attendance_credits(
    db: AsyncSession, check_in: AttendanceCheckIn
) -> List[ReadingLogEntry]:
    # No patron means anonymous walk-in -- nothing to credit.
    if check_in.patron_id is None:
        return []

    # Need the session to find the event.
    session = await db.get(AttendanceSession, check_in.session_id)
    if session is None or session.event_id is None:
        # Either the session is gone (shouldn't happen, FK is CASCADE) or it
        # is a program-linked session rather than an event-linked one.
        return []

    credits = (
        (
            await db.execute(
                select(EventReadingProgramCredit).where(
                    EventReadingProgramCredit.event_id == session.event_id
                )
            )
        )
        .scalars()
        .all()
    )

    if not credits:
        return []

    return await _grant_credits(db, credits, check_in.patron_id, session.event_id)


async def _grant_credits(
    db: AsyncSession,
    credits: Iterable[EventReadingProgramCredit],
    patron_id: int,
    event_id: int,
) -> List[ReadingLogEntry]:
    created: List[ReadingLogEntry] = []

    for credit in credits:
        registration = await _find_registration(db, patron_id, credit.program_id)
        if registration is None:
            continue

        entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=credit.books_credit,
            minutes_read=credit.minutes_credit,
            pages_read=credit.pages_credit,
            source="event_attendance",
            source_event_id=event_id,
        )
        # Savepoint per row so an idempotency conflict on one program does not
        # poison the parent transaction or roll back earlier grants.
        try:
            async with db.begin_nested():
                db.add(entry)
                await db.flush()
        except IntegrityError:
            logger.debug(
                "event-attendance credit already granted for "
                "registration=%s event=%s; skipping",
                registration.id,
                event_id,
            )
            continue
        created.append(entry)

    return created


async def _find_registration(
    db: AsyncSession, patron_id: int, program_id: int
) -> ReadingRegistration | None:
    result = await db.execute(
        select(ReadingRegistration)
        .where(
            ReadingRegistration.user_id == patron_id,
            ReadingRegistration.program_id == program_id,
        )
        .order_by(ReadingRegistration.registered_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
