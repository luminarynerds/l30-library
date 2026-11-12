# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Library hours API — public read, staff write."""

import json
from app.core.logging import get_logger
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache import get_redis
from ...core.config import get_settings
from ...core.database import get_db
from ...models.homepage_content import LibraryHours, LibraryHoursOverride
from ...models.user import User
from ...schemas.homepage_content import (
    DayHoursResponse,
    HoursOverrideCreate,
    HoursOverrideResponse,
    HoursOverrideUpdate,
    IsOpenResponse,
    LibraryHoursPublicResponse,
    WeeklyHoursUpdate,
)
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/library-hours", tags=["library-hours"])


def _get_library_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().library_timezone)


def _time_to_str(t: time | None) -> str | None:
    return t.strftime("%H:%M") if t else None


def _str_to_time(s: str | None) -> time | None:
    if not s:
        return None
    parts = s.split(":")
    return time(int(parts[0]), int(parts[1]))


def _day_to_response(row: LibraryHours) -> DayHoursResponse:
    return DayHoursResponse(
        id=row.id,
        day_of_week=row.day_of_week,
        open_time=_time_to_str(row.open_time),
        close_time=_time_to_str(row.close_time),
        is_closed=row.is_closed,
        label=row.label,
    )


def _override_to_response(row: LibraryHoursOverride) -> HoursOverrideResponse:
    return HoursOverrideResponse(
        id=row.id,
        date=row.date,
        open_time=_time_to_str(row.open_time),
        close_time=_time_to_str(row.close_time),
        is_closed=row.is_closed,
        reason=row.reason,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


# ============================================================================
# Public endpoints
# ============================================================================

@router.get("/", response_model=LibraryHoursPublicResponse)
async def get_library_hours(db: AsyncSession = Depends(get_db)):
    """Public — weekly schedule + upcoming overrides (next 30 days)."""
    weekly_result = await db.execute(
        select(LibraryHours).order_by(LibraryHours.day_of_week.asc())
    )
    weekly = weekly_result.scalars().all()

    # Use library-local date so override lookups are correct near midnight
    today = datetime.now(_get_library_tz()).date()
    overrides_result = await db.execute(
        select(LibraryHoursOverride)
        .where(LibraryHoursOverride.date >= today)
        .where(LibraryHoursOverride.date <= today + timedelta(days=30))
        .order_by(LibraryHoursOverride.date.asc())
    )
    overrides = overrides_result.scalars().all()

    return LibraryHoursPublicResponse(
        weekly=[_day_to_response(d) for d in weekly],
        overrides=[_override_to_response(o) for o in overrides],
    )


# Cache for is-open: short TTL is fine; is_open transitions only at
# open/close boundaries, so up-to-IS_OPEN_TTL_S lag is acceptable for
# polling consumers (UptimeRobot, header widget). Eliminates per-request
# DB load on what was a 1200+ events/day endpoint.
_IS_OPEN_CACHE_KEY = "library-hours:is-open"
_IS_OPEN_TTL_S = 60


def _next_open_time(
    now: datetime,
    weekly: dict[int, LibraryHours],
    skip_today: bool = False,
) -> time | None:
    """The next *future* opening time from ``now``, scanning today (only if its
    opening hasn't already passed) then forward up to a week.

    ``weekly`` maps day_of_week (0=Sun..6=Sat) to a LibraryHours row. ``skip_today``
    forces the scan to start tomorrow (used when today is overridden closed or its
    override window is already over). Returns None if the library never opens in the
    next week. Note: future-dated overrides are not considered here — this reflects
    the regular weekly schedule, which is the common case.
    """
    start = 1 if skip_today else 0
    for offset in range(start, 8):
        day = now + timedelta(days=offset)
        js_dow = (day.weekday() + 1) % 7  # Python Mon=0..Sun=6 -> JS Sun=0..Sat=6
        hours = weekly.get(js_dow)
        if not hours or hours.is_closed or not hours.open_time:
            continue
        if offset == 0 and now.time() >= hours.open_time:
            continue  # today's regular opening already passed; look further forward
        return hours.open_time
    return None


async def _compute_is_open(db: AsyncSession) -> IsOpenResponse:
    now = datetime.now(_get_library_tz())
    today = now.date()
    current_time = now.time()

    # Full weekly schedule, loaded once — needed to compute the genuinely-next opening.
    weekly_rows = (await db.execute(select(LibraryHours))).scalars().all()
    weekly = {row.day_of_week: row for row in weekly_rows}

    override_result = await db.execute(
        select(LibraryHoursOverride).where(LibraryHoursOverride.date == today)
    )
    override = override_result.scalar_one_or_none()

    if override:
        if override.is_closed:
            return IsOpenResponse(
                is_open=False,
                opens_at=_time_to_str(_next_open_time(now, weekly, skip_today=True)),
                reason=override.reason or "Closed today",
            )
        if override.open_time and override.close_time:
            is_open = override.open_time <= current_time < override.close_time
            if is_open:
                return IsOpenResponse(
                    is_open=True,
                    closes_at=_time_to_str(override.close_time),
                    reason=override.reason,
                )
            # Closed under today's override: its opening if still ahead, else next day.
            opens = (
                override.open_time
                if current_time < override.open_time
                else _next_open_time(now, weekly, skip_today=True)
            )
            return IsOpenResponse(
                is_open=False,
                opens_at=_time_to_str(opens),
                reason=override.reason,
            )

    js_dow = (now.weekday() + 1) % 7  # Python Mon=0..Sun=6 -> JS Sun=0..Sat=6
    hours = weekly.get(js_dow)

    if not hours or hours.is_closed:
        return IsOpenResponse(
            is_open=False,
            opens_at=_time_to_str(_next_open_time(now, weekly)),
        )

    if hours.open_time and hours.close_time:
        is_open = hours.open_time <= current_time < hours.close_time
        return IsOpenResponse(
            is_open=is_open,
            closes_at=_time_to_str(hours.close_time) if is_open else None,
            opens_at=_time_to_str(_next_open_time(now, weekly)) if not is_open else None,
        )

    return IsOpenResponse(
        is_open=False,
        opens_at=_time_to_str(_next_open_time(now, weekly)),
    )


@router.api_route("/is-open", methods=["GET", "HEAD"], response_model=IsOpenResponse)
async def check_is_open(db: AsyncSession = Depends(get_db)):
    redis = None
    try:
        redis = await get_redis()
        if redis is not None:
            cached = await redis.get(_IS_OPEN_CACHE_KEY)
            if cached:
                try:
                    return IsOpenResponse(**json.loads(cached))
                except (ValueError, TypeError):
                    # Stale schema in cache; treat as miss and refill.
                    pass
    except Exception:  # noqa: BLE001 -- never let cache failures break the endpoint
        logger.debug("is-open cache read failed; falling through to DB", exc_info=True)
        redis = None

    response = await _compute_is_open(db)

    if redis is not None:
        try:
            await redis.setex(
                _IS_OPEN_CACHE_KEY, _IS_OPEN_TTL_S, response.model_dump_json()
            )
        except Exception:  # noqa: BLE001 -- cache write must not break the endpoint
            logger.debug("is-open cache write failed; ignoring", exc_info=True)

    return response


# ============================================================================
# Staff endpoints — weekly schedule
# ============================================================================

@router.put("/weekly")
async def update_weekly_hours(
    body: WeeklyHoursUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — bulk update all 7 days of the weekly schedule."""
    for day_data in body.days:
        result = await db.execute(
            select(LibraryHours).where(LibraryHours.day_of_week == day_data.day_of_week)
        )
        row = result.scalar_one_or_none()
        if row:
            row.open_time = _str_to_time(day_data.open_time)
            row.close_time = _str_to_time(day_data.close_time)
            row.is_closed = day_data.is_closed
            row.label = day_data.label

    await db.commit()
    return {"status": "updated", "days": 7}


# ============================================================================
# Staff endpoints — overrides
# ============================================================================

@router.get("/overrides", response_model=list[HoursOverrideResponse])
async def list_overrides(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — list all overrides (past and future)."""
    result = await db.execute(
        select(LibraryHoursOverride).order_by(LibraryHoursOverride.date.desc())
    )
    return [_override_to_response(o) for o in result.scalars().all()]


@router.post("/overrides", response_model=HoursOverrideResponse, status_code=status.HTTP_201_CREATED)
async def create_override(
    body: HoursOverrideCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — add a date-specific override."""
    existing = await db.execute(
        select(LibraryHoursOverride).where(LibraryHoursOverride.date == body.date)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Override already exists for that date")

    override = LibraryHoursOverride(
        date=body.date,
        open_time=_str_to_time(body.open_time),
        close_time=_str_to_time(body.close_time),
        is_closed=body.is_closed,
        reason=body.reason,
        created_by_id=current_user.id,
    )
    db.add(override)
    await db.commit()
    await db.refresh(override)
    return _override_to_response(override)


@router.put("/overrides/{override_id}", response_model=HoursOverrideResponse)
async def update_override(
    override_id: int,
    body: HoursOverrideUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — edit an override."""
    result = await db.execute(
        select(LibraryHoursOverride).where(LibraryHoursOverride.id == override_id)
    )
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in ("open_time", "close_time"):
            value = _str_to_time(value)
        setattr(override, key, value)

    await db.commit()
    await db.refresh(override)
    return _override_to_response(override)


@router.delete("/overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_override(
    override_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — remove an override."""
    result = await db.execute(
        select(LibraryHoursOverride).where(LibraryHoursOverride.id == override_id)
    )
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")

    await db.delete(override)
    await db.commit()
    return None
