# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Indie author events endpoint -- filters library events by author."""
from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.event import Event
from ...models.indie_author import IndieAuthor

logger = get_logger(__name__)

router = APIRouter(prefix="/indie/authors", tags=["indie-author-events"])


class AuthorEventResponse(BaseModel):
    id: int
    title: str
    start_time: str
    end_time: str | None
    category: str | None
    is_published: bool


class UpcomingIndieEventResponse(BaseModel):
    id: int
    title: str
    start_time: str
    end_time: str | None
    category: str | None
    author_id: int | None
    author_pen_name: str | None


@router.get("/{author_id}/events", response_model=list[AuthorEventResponse])
async def get_author_events(
    author_id: int,
    upcoming: bool = Query(True),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Get events associated with an indie author."""
    now = datetime.now(timezone.utc)
    conditions = [
        Event.indie_author_id == author_id,
        Event.is_published == True,
    ]
    if upcoming:
        conditions.append(Event.start_time >= now)
        order = Event.start_time.asc()
    else:
        conditions.append(Event.start_time < now)
        order = Event.start_time.desc()

    stmt = (
        select(Event)
        .where(and_(*conditions))
        .order_by(order)
        .limit(limit)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    return [
        AuthorEventResponse(
            id=e.id,
            title=e.title,
            start_time=e.start_time.isoformat() if e.start_time else "",
            end_time=e.end_time.isoformat() if e.end_time else None,
            category=e.category if hasattr(e, "category") else None,
            is_published=e.is_published,
        )
        for e in events
    ]


@router.get("/events/upcoming", response_model=list[UpcomingIndieEventResponse])
async def get_upcoming_indie_events(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Upcoming published events linked to any indie author, soonest first."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Event, IndieAuthor)
        .join(IndieAuthor, Event.indie_author_id == IndieAuthor.id)
        .where(
            and_(
                Event.indie_author_id.is_not(None),
                Event.is_published == True,
                Event.start_time >= now,
            )
        )
        .order_by(Event.start_time.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        UpcomingIndieEventResponse(
            id=event.id,
            title=event.title,
            start_time=event.start_time.isoformat() if event.start_time else "",
            end_time=event.end_time.isoformat() if event.end_time else None,
            category=event.category if hasattr(event, "category") else None,
            author_id=author.id,
            author_pen_name=author.pen_name,
        )
        for event, author in rows
    ]
