# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron-facing per-series endpoints.

Routes here are mounted at `/events` (same prefix as the per-event router).
They MUST be included BEFORE app.api.v1.events.router in registry.py so the
literal `/events/series/{series_id}` path takes precedence over the
`/events/{event_id:int}` route (otherwise the int-coercion attempt on a
string series id 422s before FastAPI reaches the series route).
See: feedback_l30_fastapi_literal_before_param_route.
"""
from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.event import Event
from ...models.event_registration import EventRegistration, EventRegistrationStatus
from ...schemas.event_series import (
    SeriesDetailResponse,
    SeriesOccurrence,
    SeriesRegistrationCreate,
    SeriesRegistrationOutcome,
    SeriesRegistrationResponse,
)
from .events import normalize_email, verify_turnstile

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events", "series"])


async def _load_upcoming_series_events(
    db: AsyncSession, series_id: str, *, lock: bool = False
) -> list[Event]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(Event)
        .where(Event.series_id == series_id)
        .where(Event.is_published == True)  # noqa: E712
        .where(Event.start_time > now)
        .order_by(Event.start_time.asc())
    )
    if lock:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _recurrence_summary(occurrences: list[Event]) -> str | None:
    if not occurrences:
        return None
    if len(occurrences) == 1:
        return "One upcoming session"
    last = occurrences[-1]
    return (
        f"{len(occurrences)} upcoming sessions through "
        f"{last.start_time.strftime('%b %d, %Y')}"
    )


@router.get("/series/{series_id}", response_model=SeriesDetailResponse)
async def get_series(series_id: str, db: AsyncSession = Depends(get_db)):
    """Series metadata + upcoming occurrences.

    Metadata (title/description/audience/...) is derived from the next
    upcoming occurrence so it reflects current state without a series table.
    """
    occurrences = await _load_upcoming_series_events(db, series_id)
    if not occurrences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Series not found or has no upcoming occurrences",
        )

    representative = occurrences[0]

    occurrence_responses: list[SeriesOccurrence] = []
    for ev in occurrences:
        spots_remaining: int | None = None
        if ev.max_attendees is not None:
            count_result = await db.execute(
                select(func.count(EventRegistration.id))
                .where(EventRegistration.event_id == ev.id)
                .where(
                    EventRegistration.status
                    == EventRegistrationStatus.CONFIRMED.value
                )
            )
            confirmed = count_result.scalar() or 0
            spots_remaining = max(0, ev.max_attendees - confirmed)
        occurrence_responses.append(
            SeriesOccurrence(
                event_id=ev.id,
                start_time=ev.start_time,
                end_time=ev.end_time,
                location=ev.location,
                is_published=ev.is_published,
                max_attendees=ev.max_attendees,
                spots_remaining=spots_remaining,
                registration_required=ev.registration_required,
            )
        )

    return SeriesDetailResponse(
        series_id=series_id,
        series_name=representative.series_name or "Event Series",
        description=representative.description,
        category=representative.category,
        audience=representative.audience,
        min_age=representative.min_age,
        max_age=representative.max_age,
        presenters=representative.presenters,
        recurrence_summary=_recurrence_summary(occurrences),
        upcoming_count=len(occurrences),
        occurrences=occurrence_responses,
    )


@router.post(
    "/series/{series_id}/register",
    response_model=SeriesRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/hour")
async def register_for_series(  # noqa: role-check -- public series registration, Turnstile-gated
    request: Request,
    series_id: str,
    registration: SeriesRegistrationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a patron for every upcoming occurrence in a series.

    Idempotent: re-running with the same email returns the same final state
    (each already-registered occurrence is reported as such, no duplicate
    rows are created). Per-occurrence outcomes are reported so the UI can
    show the patron exactly what changed.

    Capacity behavior matches single-event register: full occurrences are
    waitlisted rather than rejected.
    """
    remote_ip = request.client.host if request.client else None
    if not await verify_turnstile(registration.turnstile_token, remote_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot verification failed",
        )

    occurrences = await _load_upcoming_series_events(db, series_id, lock=True)
    if not occurrences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Series not found or has no upcoming occurrences",
        )

    normalized_email = normalize_email(registration.patron_email)
    series_name = occurrences[0].series_name or "Event Series"

    outcomes: list[SeriesRegistrationOutcome] = []
    registered_count = 0
    already_count = 0
    waitlisted_count = 0
    failed_count = 0

    for ev in occurrences:
        if not ev.registration_required:
            outcomes.append(
                SeriesRegistrationOutcome(
                    event_id=ev.id,
                    start_time=ev.start_time,
                    status="error",
                    error="Event does not require registration",
                )
            )
            failed_count += 1
            continue

        existing = await db.execute(
            select(EventRegistration)
            .where(EventRegistration.event_id == ev.id)
            .where(
                func.lower(EventRegistration.patron_email) == normalized_email
            )
            .where(
                EventRegistration.status.in_(
                    [
                        EventRegistrationStatus.CONFIRMED.value,
                        EventRegistrationStatus.WAITLISTED.value,
                    ]
                )
            )
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row is not None:
            outcomes.append(
                SeriesRegistrationOutcome(
                    event_id=ev.id,
                    start_time=ev.start_time,
                    status="already_registered",
                    registration_id=existing_row.id,
                )
            )
            already_count += 1
            continue

        reg_status = EventRegistrationStatus.CONFIRMED.value
        if ev.max_attendees is not None:
            count_result = await db.execute(
                select(func.count(EventRegistration.id))
                .where(EventRegistration.event_id == ev.id)
                .where(
                    EventRegistration.status
                    == EventRegistrationStatus.CONFIRMED.value
                )
            )
            confirmed = count_result.scalar() or 0
            if confirmed >= ev.max_attendees:
                reg_status = EventRegistrationStatus.WAITLISTED.value

        photo_release = (
            registration.photo_release_granted
            if ev.photos_will_be_taken
            else None
        )

        new_reg = EventRegistration(
            event_id=ev.id,
            patron_name=registration.patron_name,
            patron_email=normalized_email,
            patron_phone=registration.patron_phone,
            status=reg_status,
            reminder_requested=registration.reminder_requested,
            accommodation_requested=registration.accommodation_requested,
            accommodation_details=registration.accommodation_details,
            photo_release_granted=photo_release,
        )
        db.add(new_reg)
        try:
            await db.flush()
        except IntegrityError:
            # Concurrent registration from another tab — partial unique index
            # blocks the duplicate. Translate to already_registered.
            await db.rollback()
            outcomes.append(
                SeriesRegistrationOutcome(
                    event_id=ev.id,
                    start_time=ev.start_time,
                    status="already_registered",
                )
            )
            already_count += 1
            continue

        if reg_status == EventRegistrationStatus.WAITLISTED.value:
            outcomes.append(
                SeriesRegistrationOutcome(
                    event_id=ev.id,
                    start_time=ev.start_time,
                    status="waitlisted",
                    registration_id=new_reg.id,
                )
            )
            waitlisted_count += 1
        else:
            outcomes.append(
                SeriesRegistrationOutcome(
                    event_id=ev.id,
                    start_time=ev.start_time,
                    status="registered",
                    registration_id=new_reg.id,
                )
            )
            registered_count += 1

    await db.commit()

    logger.info(
        "series_registration",
        extra={
            "series_id": series_id,
            "patron_email": normalized_email,
            "total_upcoming": len(occurrences),
            "registered": registered_count,
            "already_registered": already_count,
            "waitlisted": waitlisted_count,
            "failed": failed_count,
        },
    )

    return SeriesRegistrationResponse(
        series_id=series_id,
        series_name=series_name,
        total_upcoming=len(occurrences),
        registered_count=registered_count,
        already_registered_count=already_count,
        waitlisted_count=waitlisted_count,
        failed_count=failed_count,
        outcomes=outcomes,
    )
