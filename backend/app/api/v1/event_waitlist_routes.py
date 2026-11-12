# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public event waitlist routes."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...core.turnstile import verify_turnstile
from ...models.event import Event
from ...models.event_registration import EventRegistration, EventRegistrationStatus
from ...models.event_waitlist import (
    ACTIVE_WAITLIST_STATUSES,
    EventWaitlistEntry,
    WaitlistStatus,
)
from ...schemas.event_registration import RegistrationResponse
from ...schemas.event_waitlist import (
    WaitlistJoinRequest,
    WaitlistJoinResponse,
    WaitlistPositionResponse,
)
from ...services.notifications.types import NotificationType as NType
from .event_helpers import normalize_email, send_event_email

router = APIRouter()


@router.post(
    "/{event_id}/waitlist",
    response_model=WaitlistJoinResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def join_waitlist(  # noqa: role-check -- public waitlist join, Turnstile-gated
    request: Request,
    event_id: int,
    payload: WaitlistJoinRequest,
    db: AsyncSession = Depends(get_db),
):
    """Join the waitlist for a full, published event."""
    remote_ip = request.client.host if request.client else None
    if not await verify_turnstile(payload.turnstile_token, remote_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Bot verification failed"
        )

    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .where(Event.is_published == True)  # noqa: E712
        .with_for_update()
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    now = datetime.now(timezone.utc)
    if event.start_time <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot join waitlist for an event that has already started",
        )
    if not event.registration_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event does not require registration",
        )
    if not event.max_attendees:
        _waitlist_redirect_409(event_id, "event_has_unlimited_capacity")

    count_result = await db.execute(
        select(func.count(EventRegistration.id))
        .where(EventRegistration.event_id == event_id)
        .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
    )
    confirmed_count = count_result.scalar() or 0
    if confirmed_count < event.max_attendees:
        _waitlist_redirect_409(event_id, "event_has_spots")

    normalized_email = normalize_email(payload.email)
    existing = await db.execute(
        select(EventWaitlistEntry)
        .where(EventWaitlistEntry.event_id == event_id)
        .where(func.lower(EventWaitlistEntry.email) == normalized_email)
        .where(EventWaitlistEntry.status.in_(ACTIVE_WAITLIST_STATUSES))
    )
    existing_entry = existing.scalar_one_or_none()
    if existing_entry:
        position = await _compute_waitlist_position(db, event_id, existing_entry.id)
        return WaitlistJoinResponse(
            id=existing_entry.id,
            event_id=event_id,
            email=existing_entry.email,
            position=position,
            status=existing_entry.status,
            created_at=existing_entry.created_at,
            cancel_token=existing_entry.cancel_token or "",
        )

    entry = EventWaitlistEntry(
        event_id=event_id,
        email=normalized_email,
        name=payload.name,
        registrant_count=payload.registrant_count,
        notes=payload.notes,
        status=WaitlistStatus.WAITING.value,
        cancel_token=secrets.token_urlsafe(32),
    )
    db.add(entry)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        retry = await db.execute(
            select(EventWaitlistEntry)
            .where(EventWaitlistEntry.event_id == event_id)
            .where(func.lower(EventWaitlistEntry.email) == normalized_email)
            .where(EventWaitlistEntry.status.in_(ACTIVE_WAITLIST_STATUSES))
        )
        retry_entry = retry.scalar_one_or_none()
        if not retry_entry:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Could not join waitlist",
            ) from None
        position = await _compute_waitlist_position(db, event_id, retry_entry.id)
        return WaitlistJoinResponse(
            id=retry_entry.id,
            event_id=event_id,
            email=retry_entry.email,
            position=position,
            status=retry_entry.status,
            created_at=retry_entry.created_at,
            cancel_token=retry_entry.cancel_token or "",
        )
    await db.refresh(entry)
    position = await _compute_waitlist_position(db, event_id, entry.id)

    await send_event_email(
        NType.EVENT_WAITLIST_JOINED,
        normalized_email,
        {
            "patron_name": payload.name or "",
            "event_title": event.title,
            "event_date": event.start_time.strftime("%B %d, %Y"),
            "event_time": event.start_time.strftime("%I:%M %p"),
            "event_location": event.location or "See event details",
            "position": position,
        },
        db,
    )

    return WaitlistJoinResponse(
        id=entry.id,
        event_id=event_id,
        email=entry.email,
        position=position,
        status=entry.status,
        created_at=entry.created_at,
        cancel_token=entry.cancel_token or "",
    )


def _waitlist_redirect_409(event_id: int, code: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": code,
            "register_url": f"/api/v1/events/{event_id}/register",
        },
    )


async def _compute_waitlist_position(db: AsyncSession, event_id: int, entry_id: int) -> int:
    rows = await db.execute(
        select(EventWaitlistEntry.id)
        .where(EventWaitlistEntry.event_id == event_id)
        .where(EventWaitlistEntry.status.in_(ACTIVE_WAITLIST_STATUSES))
        .order_by(EventWaitlistEntry.created_at)
    )
    ids = [row[0] for row in rows.all()]
    try:
        return ids.index(entry_id) + 1
    except ValueError:
        return 0


@router.get("/{event_id}/waitlist/position", response_model=WaitlistPositionResponse)
async def get_waitlist_position(
    event_id: int,
    email: str = Query(..., description="Patron email to look up"),
    db: AsyncSession = Depends(get_db),
):
    """Return a patron's 1-indexed position on an event waitlist."""
    normalized = normalize_email(email)
    result = await db.execute(
        select(EventWaitlistEntry)
        .where(EventWaitlistEntry.event_id == event_id)
        .where(func.lower(EventWaitlistEntry.email) == normalized)
        .where(EventWaitlistEntry.status.in_(ACTIVE_WAITLIST_STATUSES))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not on waitlist")
    position = await _compute_waitlist_position(db, event_id, entry.id)
    return WaitlistPositionResponse(
        event_id=event_id, email=entry.email, position=position, status=entry.status
    )


@router.delete("/{event_id}/waitlist", status_code=status.HTTP_204_NO_CONTENT)
async def leave_waitlist(  # noqa: role-check (per-entry cancel_token)
    event_id: int,
    email: str = Query(...),
    token: str = Query(..., description="cancel_token from the waitlist join response"),
    db: AsyncSession = Depends(get_db),
):
    """Remove a waitlist entry using its per-entry cancellation token."""
    normalized = normalize_email(email)
    result = await db.execute(
        select(EventWaitlistEntry)
        .where(EventWaitlistEntry.event_id == event_id)
        .where(func.lower(EventWaitlistEntry.email) == normalized)
        .where(EventWaitlistEntry.status.in_(ACTIVE_WAITLIST_STATUSES))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not on waitlist")
    if not secrets.compare_digest(entry.cancel_token or "", token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid cancel token")
    entry.status = WaitlistStatus.CANCELLED.value
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{event_id}/waitlist/claim",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def claim_waitlist_spot(  # noqa: role-check (magic-link claim_token)
    event_id: int,
    token: str = Query(..., description="claim_token from the spot-available email"),
    db: AsyncSession = Depends(get_db),
):
    """Promote a notified waitlist entry to a confirmed registration."""
    result = await db.execute(
        select(EventWaitlistEntry)
        .where(EventWaitlistEntry.event_id == event_id)
        .where(EventWaitlistEntry.claim_token == token)
        .where(EventWaitlistEntry.status == WaitlistStatus.NOTIFIED.value)
        .with_for_update()
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    now = datetime.now(timezone.utc)
    expires_at = entry.claim_token_expires_at
    if (
        expires_at is None
        or (expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at)
        < now
    ):
        entry.status = WaitlistStatus.EXPIRED.value
        await db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Claim token has expired")

    event_result = await db.execute(select(Event).where(Event.id == event_id).with_for_update())
    event = event_result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    registration = EventRegistration(
        event_id=event_id,
        patron_name=entry.name or entry.email,
        patron_email=entry.email,
        status=EventRegistrationStatus.CONFIRMED.value,
    )
    db.add(registration)
    entry.status = WaitlistStatus.CLAIMED.value
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active registration for this event",
        ) from None
    await db.refresh(registration)
    return RegistrationResponse(
        id=registration.id,
        event_id=registration.event_id,
        patron_name=registration.patron_name,
        patron_email=registration.patron_email,
        patron_phone=registration.patron_phone,
        status=registration.status,
        registered_at=registration.registered_at,
    )
