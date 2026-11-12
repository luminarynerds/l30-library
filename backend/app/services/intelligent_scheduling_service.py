# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib.parse import quote

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.event import Event
from ..models.event_registration import EventRegistration
from ..models.equipment import Equipment, EquipmentReservation
from ..models.home_delivery import DeliveryVolunteer, VolunteerSchedule, DeliveryVolunteerStatus
from ..models.room import ReservationStatus as RoomReservationStatus
from ..models.room import RoomReservation
from ..models.user import User

ACTIVE_ROOM_RESERVATION_STATUSES = [
    RoomReservationStatus.pending,
    RoomReservationStatus.confirmed,
    RoomReservationStatus.checked_in,
]

ACTIVE_EQUIPMENT_RESERVATION_STATUSES = ["pending", "confirmed", "ready_for_pickup"]


@dataclass
class DateTimeWindow:
    start: datetime
    end: datetime


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class IntelligentSchedulingService:

    @staticmethod
    async def room_conflicts(
        db: AsyncSession,
        room_id: int,
        start_time: datetime,
        end_time: datetime,
        turnover_minutes: int = 0,
    ) -> list[dict[str, Any]]:
        buffered_start = _to_utc(start_time) - timedelta(minutes=max(0, turnover_minutes))
        buffered_end = _to_utc(end_time) + timedelta(minutes=max(0, turnover_minutes))

        result = await db.execute(
            select(RoomReservation)
            .where(RoomReservation.room_id == room_id)
            .where(RoomReservation.status.in_(ACTIVE_ROOM_RESERVATION_STATUSES))
            .where(RoomReservation.start_time < buffered_end)
            .where(RoomReservation.end_time > buffered_start)
            .order_by(RoomReservation.start_time)
        )
        return [
            {
                "reservation_id": r.id,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "start_time": r.start_time,
                "end_time": r.end_time,
                "conflict_type": "turnover_conflict" if turnover_minutes else "overlap",
            }
            for r in result.scalars().all()
        ]

    @staticmethod
    async def volunteer_shift_gaps(
        db: AsyncSession,
        volunteer_id: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        result = await db.execute(
            select(VolunteerSchedule)
            .where(VolunteerSchedule.volunteer_id == volunteer_id)
            .where(VolunteerSchedule.date >= start_date)
            .where(VolunteerSchedule.date <= end_date)
            .order_by(VolunteerSchedule.date)
        )
        schedules = result.scalars().all()
        available_dates = {s.date for s in schedules if s.is_available}

        gaps: list[dict[str, Any]] = []
        cursor = start_date
        while cursor <= end_date:
            if cursor not in available_dates:
                gaps.append({"date": cursor, "reason": "no_shift_assigned"})
            cursor += timedelta(days=1)
        return gaps

    @staticmethod
    async def event_suggestions(
        db: AsyncSession,
        category: str | None,
        lookback_days: int,
        top_n: int = 3,
    ) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(days=max(30, lookback_days))

        attendance_count = func.count(EventRegistration.id)
        dow = func.extract("dow", Event.start_time)
        hour = func.extract("hour", Event.start_time)

        query = (
            select(
                dow.label("dow"),
                hour.label("hour"),
                func.avg(attendance_count).label("avg_attendance"),
                func.count(Event.id).label("sample_size"),
            )
            .select_from(Event)
            .outerjoin(
                EventRegistration,
                and_(
                    EventRegistration.event_id == Event.id,
                    EventRegistration.status == "confirmed",
                ),
            )
            .where(Event.start_time >= since)
            .group_by(dow, hour)
            .having(func.count(Event.id) >= 1)
            .order_by(func.avg(attendance_count).desc(), func.count(Event.id).desc())
            .limit(max(1, min(top_n, 10)))
        )

        if category:
            query = query.where(Event.category == category)

        rows = (await db.execute(query)).all()
        dow_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        suggestions = []
        for row in rows:
            dow_idx = int(row.dow) if row.dow is not None else 1
            suggestions.append(
                {
                    "day_of_week": dow_names[dow_idx],
                    "hour": int(row.hour) if row.hour is not None else 12,
                    "average_attendance": round(float(row.avg_attendance or 0), 2),
                    "sample_size": int(row.sample_size or 0),
                }
            )
        return suggestions

    @staticmethod
    async def repeat_program_schedule(
        db: AsyncSession,
        source_year: int,
        target_year: int,
        series_name: str | None,
    ) -> list[dict[str, Any]]:
        source_start = datetime(source_year, 6, 1, tzinfo=timezone.utc)
        source_end = datetime(source_year, 9, 1, tzinfo=timezone.utc)

        query = (
            select(Event)
            .where(Event.start_time >= source_start)
            .where(Event.start_time < source_end)
            .order_by(Event.start_time)
        )
        if series_name:
            query = query.where(Event.series_name == series_name)

        events = (await db.execute(query)).scalars().all()
        repeats = []
        for event in events:
            delta_days = (event.start_time.date() - source_start.date()).days
            new_start = datetime(target_year, 6, 1, tzinfo=timezone.utc) + timedelta(days=delta_days)
            new_start = new_start.replace(
                hour=event.start_time.hour,
                minute=event.start_time.minute,
                second=0,
                microsecond=0,
            )
            new_end = None
            if event.end_time:
                duration = event.end_time - event.start_time
                new_end = new_start + duration

            repeats.append(
                {
                    "template_event_id": event.id,
                    "title": event.title,
                    "suggested_start_time": new_start,
                    "suggested_end_time": new_end,
                    "location": event.location,
                }
            )
        return repeats

    @staticmethod
    async def volunteer_shift_matching(
        db: AsyncSession,
        requested_date: date,
        start_time: time,
        end_time: time,
    ) -> list[dict[str, Any]]:
        day_name = requested_date.strftime("%A")
        volunteers = (
            await db.execute(
                select(DeliveryVolunteer, User)
                .join(User, User.id == DeliveryVolunteer.user_id)
                .where(DeliveryVolunteer.status == DeliveryVolunteerStatus.active)
                .where(or_(DeliveryVolunteer.available_days.is_(None), DeliveryVolunteer.available_days.any(day_name)))
                .order_by(DeliveryVolunteer.total_volunteer_hours.asc())
                .limit(20)
            )
        ).all()

        schedule_rows = (
            await db.execute(
                select(VolunteerSchedule)
                .where(VolunteerSchedule.date == requested_date)
                .where(VolunteerSchedule.volunteer_id.in_([v.id for v, _ in volunteers] or [-1]))
            )
        ).scalars().all()
        schedule_map = {s.volunteer_id: s for s in schedule_rows}

        matches = []
        for volunteer, user in volunteers:
            schedule = schedule_map.get(volunteer.id)
            if schedule and not schedule.is_available:
                continue
            matches.append(
                {
                    "volunteer_id": volunteer.id,
                    "name": f"{user.first_name} {user.last_name}",
                    "available_time_start": schedule.time_start if schedule else volunteer.available_time_start,
                    "available_time_end": schedule.time_end if schedule else volunteer.available_time_end,
                    "max_deliveries_per_day": volunteer.max_deliveries_per_day,
                }
            )
        return matches

    @staticmethod
    async def equipment_availability(
        db: AsyncSession,
        equipment_ids: list[int],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        if not equipment_ids:
            return []

        equipment_rows = (
            await db.execute(select(Equipment).where(Equipment.id.in_(equipment_ids)))
        ).scalars().all()

        reservation_rows = (
            await db.execute(
                select(EquipmentReservation)
                .where(EquipmentReservation.equipment_id.in_(equipment_ids))
                .where(EquipmentReservation.status.in_(ACTIVE_EQUIPMENT_RESERVATION_STATUSES))
                .where(EquipmentReservation.start_date <= end_date)
                .where(EquipmentReservation.end_date >= start_date)
            )
        ).scalars().all()

        by_equipment: dict[int, list[EquipmentReservation]] = {}
        for reservation in reservation_rows:
            by_equipment.setdefault(reservation.equipment_id, []).append(reservation)

        return [
            {
                "equipment_id": equipment.id,
                "equipment_name": equipment.name,
                "is_available": len(by_equipment.get(equipment.id, [])) == 0,
                "conflicts": [
                    {
                        "reservation_id": r.id,
                        "start_date": r.start_date,
                        "end_date": r.end_date,
                        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                    }
                    for r in by_equipment.get(equipment.id, [])
                ],
            }
            for equipment in equipment_rows
        ]

    @staticmethod
    async def find_time(
        db: AsyncSession,
        participant_ids: list[int],
        date_window: DateTimeWindow,
        duration_minutes: int,
    ) -> list[dict[str, Any]]:
        if not participant_ids:
            return []

        start_utc = _to_utc(date_window.start)
        end_utc = _to_utc(date_window.end)
        duration = timedelta(minutes=max(15, duration_minutes))

        blocks = (
            await db.execute(
                select(RoomReservation)
                .where(RoomReservation.patron_id.in_(participant_ids))
                .where(RoomReservation.status.in_(ACTIVE_ROOM_RESERVATION_STATUSES))
                .where(RoomReservation.start_time < end_utc)
                .where(RoomReservation.end_time > start_utc)
                .order_by(RoomReservation.start_time)
            )
        ).scalars().all()

        candidates: list[dict[str, Any]] = []
        slot = start_utc
        while slot + duration <= end_utc and len(candidates) < 8:
            slot_end = slot + duration
            conflict = any(b.start_time < slot_end and b.end_time > slot for b in blocks)
            if not conflict:
                candidates.append({"start_time": slot, "end_time": slot_end})
            slot += timedelta(minutes=30)
        return candidates

    @staticmethod
    def calendar_sync_links(
        title: str,
        start_time: datetime,
        end_time: datetime,
        details: str | None = None,
        location: str | None = None,
    ) -> dict[str, str]:
        start = _to_utc(start_time).strftime("%Y%m%dT%H%M%SZ")
        end = _to_utc(end_time).strftime("%Y%m%dT%H%M%SZ")

        base_google = "https://calendar.google.com/calendar/render?action=TEMPLATE"
        google = (
            f"{base_google}&text={quote(title)}"
            f"&dates={start}/{end}"
            f"&details={quote(details or '')}"
            f"&location={quote(location or '')}"
        )

        # Outlook Web deep link (OWA)
        outlook = (
            "https://outlook.office.com/calendar/0/deeplink/compose"
            f"?path=/calendar/action/compose&rru=addevent&subject={quote(title)}"
            f"&startdt={quote(_to_utc(start_time).isoformat())}"
            f"&enddt={quote(_to_utc(end_time).isoformat())}"
            f"&body={quote(details or '')}"
            f"&location={quote(location or '')}"
        )

        return {
            "google_calendar_url": google,
            "outlook_calendar_url": outlook,
            "provider_support": "google_outlook_deeplinks",
        }
