# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import hashlib
from app.core.logging import get_logger
import re
from datetime import date, datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.parent_onboarding import (
    HomeVisitAccessNotes,
    HomeVisitGeocodeCache,
    ParentHomeVisit,
)
from app.models.user import User
from app.schemas.parent_onboarding import (
    DayPlanLeg,
    DayPlanResponse,
    DayPlanStop,
    HomeVisitAccessNotesRead,
)

logger = get_logger(__name__)


# Cache freshness for Nominatim entries. Manual overrides never expire.
GEOCODE_TTL_DAYS = 90

# Public-instance courtesy: at least 1s between Nominatim hits per process.
# Process-local lock; if we ever run multiple backend pods we move to Redis.
_NOMINATIM_LOCK = asyncio.Lock()
_NOMINATIM_MIN_INTERVAL = 1.0
_last_nominatim_at: float = 0.0

# Haversine speed assumptions for the OSRM fallback. Conservative urban
# numbers; the UI tags the leg's provider so staff know it's an estimate.
HAVERSINE_DRIVE_KMH = 30.0
HAVERSINE_WALK_KMH = 5.0


def _normalize_address(address: str) -> str:
    text = address.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = text.rstrip(".,")
    return text


def _hash_address(address: str) -> str:
    return hashlib.sha256(_normalize_address(address).encode("utf-8")).hexdigest()


async def _wait_for_nominatim_slot() -> None:
    global _last_nominatim_at
    async with _NOMINATIM_LOCK:
        now = asyncio.get_event_loop().time()
        wait = _NOMINATIM_MIN_INTERVAL - (now - _last_nominatim_at)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_nominatim_at = asyncio.get_event_loop().time()


async def get_or_geocode_address(
    db: AsyncSession,
    address: str,
) -> Optional[tuple[float, float]]:
    if not address or not address.strip():
        return None

    address_hash = _hash_address(address)
    stmt = select(HomeVisitGeocodeCache).where(
        HomeVisitGeocodeCache.address_hash == address_hash
    )
    row = (await db.execute(stmt)).scalar_one_or_none()

    if row is not None:
        is_manual = row.provider == "manual"
        cutoff = datetime.now(timezone.utc) - timedelta(days=GEOCODE_TTL_DAYS)
        is_fresh = is_manual or (row.geocoded_at and row.geocoded_at > cutoff)
        if is_fresh:
            return (float(row.lat), float(row.lng))

    # Cache miss or stale -- hit Nominatim. Failure leaves the (possibly
    # stale) cached value alone; we'll just return what we have.
    coords = await _nominatim_lookup(address)
    if coords is None:
        if row is not None:
            return (float(row.lat), float(row.lng))
        return None

    lat, lng = coords
    if row is None:
        db.add(
            HomeVisitGeocodeCache(
                address_hash=address_hash,
                address_raw=address,
                lat=lat,
                lng=lng,
                provider="nominatim",
            )
        )
    else:
        # Refresh in place; do NOT downgrade a 'manual' entry.
        if row.provider != "manual":
            row.lat = lat
            row.lng = lng
            row.geocoded_at = datetime.now(timezone.utc)
    await db.flush()
    return (lat, lng)


async def upsert_manual_geocode(
    db: AsyncSession,
    address: str,
    lat: float,
    lng: float,
) -> None:
    address_hash = _hash_address(address)
    stmt = select(HomeVisitGeocodeCache).where(
        HomeVisitGeocodeCache.address_hash == address_hash
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        db.add(
            HomeVisitGeocodeCache(
                address_hash=address_hash,
                address_raw=address,
                lat=lat,
                lng=lng,
                provider="manual",
            )
        )
    else:
        row.lat = lat
        row.lng = lng
        row.provider = "manual"
        row.geocoded_at = datetime.now(timezone.utc)
    await db.flush()


async def _nominatim_lookup(address: str) -> Optional[tuple[float, float]]:
    settings = get_settings()
    contact = getattr(settings, "support_email", None) or "l30@example.com"
    user_agent = f"l30/home-visit-day-plan ({contact})"

    await _wait_for_nominatim_slot()

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": user_agent},
            )
            if resp.status_code != 200:
                logger.warning(
                    "Nominatim returned %s for address %r", resp.status_code, address
                )
                return None
            data = resp.json()
            if not data:
                return None
            return (float(data[0]["lat"]), float(data[0]["lon"]))
    except (httpx.HTTPError, KeyError, ValueError, IndexError) as exc:
        logger.warning("Nominatim lookup failed for %r: %s", address, exc)
        return None


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    c = 2 * asin(sqrt(a))
    return r_km * c


async def _osrm_route(
    a_lat: float, a_lng: float, b_lat: float, b_lng: float
) -> Optional[tuple[float, float, float]]:
    base = "https://router.project-osrm.org"
    coords = f"{a_lng},{a_lat};{b_lng},{b_lat}"

    async def _one(profile: str) -> Optional[tuple[float, float]]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{base}/route/v1/{profile}/{coords}",
                    params={"overview": "false"},
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                if data.get("code") != "Ok" or not data.get("routes"):
                    return None
                r = data["routes"][0]
                return (r["distance"] / 1000.0, r["duration"] / 60.0)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("OSRM %s request failed: %s", profile, exc)
            return None

    drive = await _one("driving")
    walk = await _one("foot")
    if drive is None or walk is None:
        return None
    return (drive[0], drive[1], walk[1])


async def compute_leg(
    a_lat: float, a_lng: float, b_lat: float, b_lng: float
) -> DayPlanLeg:
    osrm = await _osrm_route(a_lat, a_lng, b_lat, b_lng)
    if osrm is not None:
        distance_km, drive_min, walk_min = osrm
        return DayPlanLeg(
            drive_minutes=max(1, round(drive_min)),
            walk_minutes=max(1, round(walk_min)),
            distance_km=round(distance_km, 2),
            provider="osrm",
        )

    distance_km = _haversine_km(a_lat, a_lng, b_lat, b_lng)
    drive_min = (distance_km / HAVERSINE_DRIVE_KMH) * 60
    walk_min = (distance_km / HAVERSINE_WALK_KMH) * 60
    return DayPlanLeg(
        drive_minutes=max(1, round(drive_min)),
        walk_minutes=max(1, round(walk_min)),
        distance_km=round(distance_km, 2),
        provider="haversine",
    )


async def get_or_create_access_notes(
    db: AsyncSession, patron_id: int
) -> HomeVisitAccessNotes:
    stmt = select(HomeVisitAccessNotes).where(
        HomeVisitAccessNotes.patron_id == patron_id
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is not None:
        return row
    row = HomeVisitAccessNotes(patron_id=patron_id)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def staff_has_visit_access(
    db: AsyncSession, staff_id: int, patron_id: int
) -> bool:
    today = date.today()
    stmt = (
        select(ParentHomeVisit.id)
        .where(ParentHomeVisit.visitor_id == staff_id)
        .where(ParentHomeVisit.patron_id == patron_id)
        .where(ParentHomeVisit.scheduled_date >= today)
        .where(ParentHomeVisit.status.in_(["scheduled", "confirmed"]))
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def assemble_day_plan(
    db: AsyncSession,
    *,
    visitor_id: int,
    plan_date: date,
) -> DayPlanResponse:
    stmt = (
        select(ParentHomeVisit)
        .where(ParentHomeVisit.visitor_id == visitor_id)
        .where(ParentHomeVisit.scheduled_date == plan_date)
        .where(ParentHomeVisit.status.in_(["scheduled", "confirmed"]))
        .options(selectinload(ParentHomeVisit.patron))
    )
    visits = list((await db.execute(stmt)).scalars().all())

    # Geocode any visit missing lat/lng. Each lookup writes to the cache;
    # subsequent calls for the same day return immediately.
    for v in visits:
        if (v.geocoded_lat is None or v.geocoded_lng is None) and v.address:
            coords = await get_or_geocode_address(db, v.address)
            if coords is not None:
                v.geocoded_lat, v.geocoded_lng = coords
                await db.flush()

    # Order: manual sort first (1..N), then auto by scheduled_time, with
    # un-timed visits last in id order so they're stable.
    def _order_key(v: ParentHomeVisit) -> tuple[int, int, str, int]:
        if v.day_plan_sort_index is not None:
            return (0, v.day_plan_sort_index, "", v.id)
        return (1, 0, v.scheduled_time or "99:99", v.id)

    visits.sort(key=_order_key)

    # Pre-fetch access notes by patron_id in one IN query to avoid N+1.
    patron_ids = [v.patron_id for v in visits]
    notes_map: dict[int, HomeVisitAccessNotes] = {}
    if patron_ids:
        notes_stmt = select(HomeVisitAccessNotes).where(
            HomeVisitAccessNotes.patron_id.in_(patron_ids)
        )
        for n in (await db.execute(notes_stmt)).scalars().all():
            notes_map[n.patron_id] = n

    stops: list[DayPlanStop] = []
    warnings: list[str] = []
    total_drive = 0
    total_distance = 0.0
    prev: Optional[ParentHomeVisit] = None

    for idx, v in enumerate(visits, start=1):
        lat = float(v.geocoded_lat) if v.geocoded_lat is not None else None
        lng = float(v.geocoded_lng) if v.geocoded_lng is not None else None
        if lat is None or lng is None:
            warnings.append(f"no_geocode_for_visit_{v.id}")

        leg: Optional[DayPlanLeg] = None
        if prev is not None and lat is not None and lng is not None:
            prev_lat = float(prev.geocoded_lat) if prev.geocoded_lat is not None else None
            prev_lng = float(prev.geocoded_lng) if prev.geocoded_lng is not None else None
            if prev_lat is not None and prev_lng is not None:
                leg = await compute_leg(prev_lat, prev_lng, lat, lng)
                total_drive += leg.drive_minutes
                total_distance += leg.distance_km

        notes_row = notes_map.get(v.patron_id)
        access_notes = (
            HomeVisitAccessNotesRead.model_validate(notes_row) if notes_row else None
        )

        patron_name: Optional[str] = None
        if v.patron is not None:
            patron_name = " ".join(
                filter(None, [v.patron.first_name, v.patron.last_name])
            ).strip() or None

        stops.append(
            DayPlanStop(
                visit_id=v.id,
                sort_index=idx,
                scheduled_time=v.scheduled_time,
                patron_id=v.patron_id,
                patron_name=patron_name,
                address=v.address,
                lat=lat,
                lng=lng,
                purpose=v.purpose,
                status=v.status,
                access_notes=access_notes,
                leg_from_previous=leg,
                manual_order=v.day_plan_sort_index is not None,
            )
        )
        prev = v

    return DayPlanResponse(
        date=plan_date,
        visitor_id=visitor_id,
        stops=stops,
        total_drive_minutes=total_drive,
        total_distance_km=round(total_distance, 2),
        warnings=warnings,
    )
