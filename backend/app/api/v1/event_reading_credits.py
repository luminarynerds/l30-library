# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff API to manage which events grant credit toward which reading programs."""

from app.core.logging import get_logger
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...core.shortcuts import get_or_404
from ...models.event import Event
from ...models.reading import EventReadingProgramCredit, ReadingProgram
from ...models.user import User
from ...schemas.reading import (
    EventReadingProgramCreditCreate,
    EventReadingProgramCreditResponse,
)
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(
    prefix="/reading-programs/events",
    tags=["reading-programs-event-credits"],
)


@router.get(
    "/{event_id}/credits",
    response_model=List[EventReadingProgramCreditResponse],
)
@limiter.limit("60/minute")
async def list_event_credits(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List the reading-program credits configured for an event."""
    await get_or_404(db, Event, event_id, "Event not found")

    rows = (
        (
            await db.execute(
                select(EventReadingProgramCredit)
                .where(EventReadingProgramCredit.event_id == event_id)
                .order_by(EventReadingProgramCredit.id.asc())
            )
        )
        .scalars()
        .all()
    )
    return [EventReadingProgramCreditResponse.model_validate(r) for r in rows]


@router.post(
    "/{event_id}/credits",
    response_model=EventReadingProgramCreditResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def create_event_credit(
    request: Request,
    event_id: int,
    payload: EventReadingProgramCreditCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Designate that attending this event grants credit toward a reading program."""
    await get_or_404(db, Event, event_id, "Event not found")
    await get_or_404(db, ReadingProgram, payload.program_id, "Reading program not found")

    if payload.minutes_credit == 0 and payload.books_credit == 0 and payload.pages_credit == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of minutes_credit / books_credit / pages_credit must be > 0.",
        )

    credit = EventReadingProgramCredit(
        event_id=event_id,
        program_id=payload.program_id,
        minutes_credit=payload.minutes_credit,
        books_credit=payload.books_credit,
        pages_credit=payload.pages_credit,
    )
    db.add(credit)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This event already grants credit for that program.",
        ) from None
    await db.refresh(credit)
    return EventReadingProgramCreditResponse.model_validate(credit)


@router.delete(
    "/credits/{credit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("20/minute")
async def delete_event_credit(
    request: Request,
    credit_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Remove an event<->program credit mapping.

    Already-granted ReadingLogEntry rows are not retracted by this call.
    """
    credit = await get_or_404(db, EventReadingProgramCredit, credit_id, "Credit not found")
    await db.delete(credit)
    await db.commit()
    return None
