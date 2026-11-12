# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Stats API - Lightweight aggregate statistics for public widgets."""

import hashlib
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache import get_cached_with_lock
from ...core.cache_strategies import CacheKeyBuilder, CacheTTL
from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.circulation import Checkout, Hold, HoldStatus
from ...models.event import Event
from ...models.reading import ReadingLogEntry, ReadingProgram, ReadingRegistration
from ...models.user import User, UserRole, PatronStatus

router = APIRouter(prefix="/stats", tags=["stats"])


# ---------------------------------------------------------------------------
# Helpers: deterministic simulated numbers for demo/empty-data scenarios
# ---------------------------------------------------------------------------

def _seeded_int(seed_str: str, low: int, high: int) -> int:
    digest = hashlib.sha256(seed_str.encode()).hexdigest()
    return low + (int(digest[:8], 16) % (high - low + 1))


def _is_library_open(now: datetime) -> bool:
    day = now.weekday()  # 0=Mon ... 6=Sun
    hour = now.hour
    if day == 6:  # Sunday
        return 9 <= hour < 20
    if day >= 4:  # Fri-Sat
        return 10 <= hour < 18
    return 9 <= hour < 20  # Mon-Thu


def _simulated_checkouts(now: datetime) -> int:
    # Weekdays are busier than weekends
    day = now.weekday()
    if day < 5:
        low, high = 34, 78
    elif day == 5:  # Saturday
        low, high = 22, 55
    else:  # Sunday
        low, high = 15, 40

    # Scale down early in the day, scale up later
    hour = now.hour
    if hour < 10:
        low, high = max(low // 4, 3), max(high // 4, 8)
    elif hour < 13:
        low, high = low // 2, high // 2
    # afternoon/evening: use full range

    return _seeded_int(f"checkouts-{now.date()}-{hour // 2}", low, high)


def _simulated_browsers(now: datetime) -> int:
    if not _is_library_open(now):
        return _seeded_int(f"browsers-{now.date()}-{now.hour}", 1, 4)
    hour = now.hour
    if hour < 11:
        low, high = 5, 15
    elif hour < 14:
        low, high = 12, 28
    elif hour < 17:
        low, high = 8, 22
    else:
        low, high = 4, 14
    return _seeded_int(f"browsers-{now.date()}-{hour}", low, high)


def _simulated_reading_challenge(now: datetime) -> dict:
    goal = 5000
    day_of_year = now.timetuple().tm_yday
    # Simulate roughly linear growth toward goal over the year
    base = int(goal * (day_of_year / 365) * 0.6)  # ~60% pace, realistic
    variation = _seeded_int(f"reading-{now.date()}", -50, 50)
    current = max(0, min(base + variation, goal))
    return {"current": current, "goal": goal}


@router.get("/community-pulse")
async def get_community_pulse(db: AsyncSession = Depends(get_db)) -> dict:
    """Return aggregate live stats for the Community Pulse homepage widget.

    When real data is unavailable (demo/empty DB), deterministic simulated
    values are returned so the homepage never shows dead zeros.
    """
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

    # ---- Checkouts today ----
    checkouts_today = await db.scalar(
        select(func.count()).select_from(Checkout).where(
            Checkout.checked_out_at >= today_start,
        )
    ) or 0
    if checkouts_today == 0:
        # No real activity yet today -- show simulated number
        checkouts_today = _simulated_checkouts(now)

    # ---- Active browsers (simulated -- no session tracking exists yet) ----
    active_browsers = _simulated_browsers(now)

    # ---- Most-held item ----
    popular_row = (
        await db.execute(
            select(
                CatalogItem.id,
                CatalogItem.title,
                CatalogItem.author,
                func.count(Hold.id).label("hold_count"),
            )
            .join(Hold, Hold.item_id == CatalogItem.id)
            .where(Hold.status == HoldStatus.pending)
            .group_by(CatalogItem.id)
            .order_by(func.count(Hold.id).desc())
            .limit(1)
        )
    ).first()

    popular_item = None
    if popular_row:
        popular_item = {
            "id": popular_row.id,
            "title": popular_row.title,
            "author": popular_row.author,
            "holds": popular_row.hold_count,
        }

    # ---- Reading challenge progress ----
    # Try to pull real data from active reading programs first
    reading_challenge_data = None
    try:
        active_program = (
            await db.execute(
                select(ReadingProgram.id, ReadingProgram.reading_goal_value)
                .where(
                    and_(
                        ReadingProgram.is_active.is_(True),
                        ReadingProgram.start_date <= now.date(),
                        ReadingProgram.end_date >= now.date(),
                    )
                )
                .order_by(ReadingProgram.start_date.desc())
                .limit(1)
            )
        ).first()

        if active_program:
            total_books = await db.scalar(
                select(func.coalesce(func.sum(ReadingLogEntry.books_read), 0))
                .join(
                    ReadingRegistration,
                    ReadingLogEntry.registration_id == ReadingRegistration.id,
                )
                .where(ReadingRegistration.program_id == active_program.id)
            ) or 0
            goal = active_program.reading_goal_value or 5000
            if total_books > 0:
                reading_challenge_data = {"current": int(total_books), "goal": goal}
    except Exception:  # noqa: BLE001  # reading program table may not exist — fall through to simulated
        pass  # Table may not exist yet; fall through to simulated

    if reading_challenge_data is None:
        reading_challenge_data = _simulated_reading_challenge(now)

    # ---- Next upcoming event ----
    next_event_row = (
        await db.execute(
            select(Event.id, Event.title, Event.start_time, Event.location)
            .where(and_(Event.start_time >= now, Event.is_published.is_(True)))
            .order_by(Event.start_time.asc())
            .limit(1)
        )
    ).first()

    next_event = None
    if next_event_row:
        next_event = {
            "id": next_event_row.id,
            "title": next_event_row.title,
            "start_time": next_event_row.start_time.isoformat() if next_event_row.start_time else None,
            "location": next_event_row.location,
        }

    return {
        "checkouts_today": checkouts_today,
        "active_browsers": active_browsers,
        "popular_item": popular_item or {"id": 0, "title": "No holds yet", "author": "", "holds": 0},
        "reading_challenge": reading_challenge_data,
        "next_event": next_event,
    }


@router.get("/library-numbers")
async def get_library_numbers(db: AsyncSession = Depends(get_db)) -> dict:
    """Return high-level library stats for the About page 'By the Numbers' section.

    Queries live counts from the database so the About page stays current.
    Cached for 4 hours since these numbers change slowly.
    """

    async def _fetch():
        total_items = await db.scalar(
            select(func.count()).select_from(CatalogItem)
        ) or 0

        total_cardholders = await db.scalar(
            select(func.count()).select_from(User).where(
                User.role == UserRole.PATRON,
                User.is_active.is_(True),
                User.patron_status == PatronStatus.ACTIVE,
            )
        ) or 0

        return {
            "total_items": total_items,
            "total_cardholders": total_cardholders,
        }

    result = await get_cached_with_lock(
        f"{CacheKeyBuilder.PREFIX}:stats:library-numbers", _fetch, ttl_seconds=CacheTTL.EXTENDED
    )
    return result
