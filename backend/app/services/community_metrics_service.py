# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceSession, AttendanceCheckIn
from app.models.catalog import CatalogItem
from app.models.circulation import Checkout, Hold, HoldStatus
from app.models.community_metrics import CommunityMetricsSnapshot
from app.models.event import Event
from app.models.outreach import OutreachPartner, OutreachVisit
from app.models.reading import ReadingProgram, ReadingRegistration, ReadingLogEntry
from app.models.room import RoomReservation

logger = get_logger(__name__)

CATEGORIES = [
    "program_reach",
    "educational",
    "partnerships",
    "space_utilization",
    "cost_effectiveness",
    "collection_impact",
]


class CommunityMetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(
        self,
        start: date,
        end: date,
        branch_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        categories = {}
        for cat in CATEGORIES:
            categories[cat] = await self._get_category(cat, start, end, branch_id)
        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "transactional": await self._transactional(start, end),
            "categories": categories,
        }

    async def _transactional(self, start: date, end: date) -> Dict[str, Any]:
        """Transactional volume for the same period: the high-volume,
        low-touch counters shown as context above the mission categories."""
        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc)

        checkouts = (
            await self.db.execute(
                select(func.count(Checkout.id)).where(
                    and_(Checkout.checked_out_at >= start_dt, Checkout.checked_out_at <= end_dt)
                )
            )
        ).scalar() or 0
        returns = (
            await self.db.execute(
                select(func.count(Checkout.id)).where(
                    and_(Checkout.returned_at >= start_dt, Checkout.returned_at <= end_dt)
                )
            )
        ).scalar() or 0
        renewals = (
            await self.db.execute(
                select(func.coalesce(func.sum(Checkout.renewal_count), 0)).where(
                    and_(Checkout.checked_out_at >= start_dt, Checkout.checked_out_at <= end_dt)
                )
            )
        ).scalar() or 0
        holds_placed = (
            await self.db.execute(
                select(func.count(Hold.id)).where(
                    and_(Hold.created_at >= start_dt, Hold.created_at <= end_dt)
                )
            )
        ).scalar() or 0
        holds_filled = (
            await self.db.execute(
                select(func.count(Hold.id)).where(
                    and_(
                        Hold.status == HoldStatus.fulfilled,
                        Hold.created_at >= start_dt,
                        Hold.created_at <= end_dt,
                    )
                )
            )
        ).scalar() or 0

        return {
            "checkouts": checkouts,
            "returns": returns,
            "renewals": int(renewals),
            "holds_placed": holds_placed,
            "holds_filled": holds_filled,
        }

    async def get_trends(
        self,
        category: str,
        periods: int = 12,
        branch_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(CommunityMetricsSnapshot)
            .where(
                and_(
                    CommunityMetricsSnapshot.category == category,
                    CommunityMetricsSnapshot.period_type == "monthly",
                    CommunityMetricsSnapshot.branch_id == branch_id,
                )
            )
            .order_by(CommunityMetricsSnapshot.period_start.desc())
            .limit(periods)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "metrics": r.metrics,
            }
            for r in reversed(rows)
        ]

    async def get_summary(self, branch_id: Optional[int] = None) -> Dict[str, Any]:
        today = date.today()
        start = date(today.year, 1, 1)
        reach = await self._program_reach(start, today, branch_id)
        collection = await self._collection_impact(start, today, branch_id)
        edu = await self._educational(start, today, branch_id)
        return {
            "year": today.year,
            "total_participants": reach.get("total_participants", 0),
            "unique_patrons": reach.get("unique_patrons", 0),
            "active_programs": edu.get("active_programs", 0),
            "total_checkouts": collection.get("total_checkouts", 0),
        }

    async def _get_category(
        self,
        category: str,
        start: date,
        end: date,
        branch_id: Optional[int],
    ) -> Dict[str, Any]:
        snapshot = await self._get_snapshot(category, start, end, branch_id)
        if snapshot is not None:
            return snapshot

        dispatch = {
            "program_reach": self._program_reach,
            "educational": self._educational,
            "partnerships": self._partnerships,
            "space_utilization": self._space_utilization,
            "cost_effectiveness": self._cost_effectiveness,
            "collection_impact": self._collection_impact,
        }
        fn = dispatch.get(category)
        if fn is None:
            return {}
        return await fn(start, end, branch_id)

    async def _get_snapshot(
        self,
        category: str,
        start: date,
        end: date,
        branch_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        stmt = select(CommunityMetricsSnapshot).where(
            and_(
                CommunityMetricsSnapshot.category == category,
                CommunityMetricsSnapshot.period_start == start,
                CommunityMetricsSnapshot.period_end == end,
                CommunityMetricsSnapshot.branch_id == branch_id,
            )
        )
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            return row.metrics
        return None

    async def _program_reach(
        self,
        start: date,
        end: date,
        branch_id: Optional[int],
    ) -> Dict[str, Any]:
        checkin_stmt = select(func.count(AttendanceCheckIn.id)).join(
            AttendanceSession,
            AttendanceCheckIn.session_id == AttendanceSession.id,
        ).where(
            and_(
                AttendanceSession.session_date >= start,
                AttendanceSession.session_date <= end,
            )
        )
        result = await self.db.execute(checkin_stmt)
        total_checkins = result.scalar() or 0

        reg_stmt = select(func.count(ReadingRegistration.id)).join(
            ReadingProgram,
            ReadingRegistration.program_id == ReadingProgram.id,
        ).where(
            and_(
                ReadingProgram.start_date >= start,
                ReadingProgram.end_date <= end,
            )
        )
        result = await self.db.execute(reg_stmt)
        total_registrations = result.scalar() or 0

        unique_stmt = select(func.count(func.distinct(AttendanceCheckIn.patron_id))).join(
            AttendanceSession,
            AttendanceCheckIn.session_id == AttendanceSession.id,
        ).where(
            and_(
                AttendanceSession.session_date >= start,
                AttendanceSession.session_date <= end,
                AttendanceCheckIn.patron_id.isnot(None),
            )
        )
        result = await self.db.execute(unique_stmt)
        unique_patrons = result.scalar() or 0

        repeat_stmt = select(func.count(AttendanceCheckIn.id)).join(
            AttendanceSession,
            AttendanceCheckIn.session_id == AttendanceSession.id,
        ).where(
            and_(
                AttendanceSession.session_date >= start,
                AttendanceSession.session_date <= end,
                AttendanceCheckIn.is_repeat_attendee == True,
            )
        )
        result = await self.db.execute(repeat_stmt)
        repeat_attendees = result.scalar() or 0

        repeat_rate = round(repeat_attendees / total_checkins * 100, 1) if total_checkins > 0 else 0.0

        return {
            "total_participants": total_checkins + total_registrations,
            "total_checkins": total_checkins,
            "total_registrations": total_registrations,
            "unique_patrons": unique_patrons,
            "repeat_attendees": repeat_attendees,
            "repeat_rate_pct": repeat_rate,
        }

    async def _educational(
        self,
        start: date,
        end: date,
        branch_id: Optional[int],
    ) -> Dict[str, Any]:
        prog_stmt = select(func.count(ReadingProgram.id)).where(
            and_(
                ReadingProgram.is_active == True,
                ReadingProgram.start_date <= end,
                ReadingProgram.end_date >= start,
            )
        )
        result = await self.db.execute(prog_stmt)
        active_programs = result.scalar() or 0

        log_stmt = select(
            func.count(ReadingLogEntry.id),
            func.sum(ReadingLogEntry.minutes_read),
            func.sum(ReadingLogEntry.books_read),
        ).where(
            and_(
                ReadingLogEntry.logged_at >= datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc),
                ReadingLogEntry.logged_at <= datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc),
            )
        )
        result = await self.db.execute(log_stmt)
        row = result.one()
        total_entries = row[0] or 0
        total_minutes = int(row[1] or 0)
        total_books = int(row[2] or 0)

        reg_stmt = select(func.count(ReadingRegistration.id)).join(
            ReadingProgram,
            ReadingRegistration.program_id == ReadingProgram.id,
        ).where(
            and_(
                ReadingProgram.start_date <= end,
                ReadingProgram.end_date >= start,
            )
        )
        result = await self.db.execute(reg_stmt)
        total_registrations = result.scalar() or 0

        return {
            "active_programs": active_programs,
            "total_registrations": total_registrations,
            "total_log_entries": total_entries,
            "total_minutes_read": total_minutes,
            "total_books_read": total_books,
        }

    async def _partnerships(
        self,
        start: date,
        end: date,
        branch_id: Optional[int],
    ) -> Dict[str, Any]:
        partner_stmt = select(func.count(OutreachPartner.id)).where(
            OutreachPartner.status == "active"
        )
        result = await self.db.execute(partner_stmt)
        active_partners = result.scalar() or 0

        visit_stmt = select(
            func.count(OutreachVisit.id),
            func.sum(OutreachVisit.actual_attendees),
        ).where(
            and_(
                OutreachVisit.scheduled_date >= start,
                OutreachVisit.scheduled_date <= end,
            )
        )
        result = await self.db.execute(visit_stmt)
        row = result.one()
        total_visits = row[0] or 0
        students_reached = int(row[1] or 0)

        completed_stmt = select(func.count(OutreachVisit.id)).where(
            and_(
                OutreachVisit.scheduled_date >= start,
                OutreachVisit.scheduled_date <= end,
                OutreachVisit.status == "completed",
            )
        )
        result = await self.db.execute(completed_stmt)
        completed_visits = result.scalar() or 0

        return {
            "active_partnerships": active_partners,
            "total_visits": total_visits,
            "completed_visits": completed_visits,
            "students_reached": students_reached,
        }

    async def _space_utilization(
        self,
        start: date,
        end: date,
        branch_id: Optional[int],
    ) -> Dict[str, Any]:
        room_stmt = select(func.count(RoomReservation.id)).where(
            and_(
                func.date(RoomReservation.start_time) >= start,
                func.date(RoomReservation.start_time) <= end,
                RoomReservation.status == "confirmed",
            )
        )
        result = await self.db.execute(room_stmt)
        room_bookings = result.scalar() or 0

        event_stmt = select(func.count(Event.id)).where(
            and_(
                func.date(Event.start_time) >= start,
                func.date(Event.start_time) <= end,
                Event.is_published == True,
            )
        )
        result = await self.db.execute(event_stmt)
        total_events = result.scalar() or 0

        attendance_stmt = select(
            func.sum(AttendanceSession.total_checked_in),
        ).where(
            and_(
                AttendanceSession.session_date >= start,
                AttendanceSession.session_date <= end,
                AttendanceSession.event_id.isnot(None),
            )
        )
        result = await self.db.execute(attendance_stmt)
        event_attendance = int(result.scalar() or 0)

        return {
            "room_bookings": room_bookings,
            "total_events": total_events,
            "event_attendance": event_attendance,
        }

    async def _cost_effectiveness(
        self,
        start: date,
        end: date,
        branch_id: Optional[int],
    ) -> Dict[str, Any]:
        cost_stmt = select(
            func.sum(AttendanceSession.event_cost),
            func.sum(AttendanceSession.total_checked_in),
            func.count(AttendanceSession.id),
        ).where(
            and_(
                AttendanceSession.session_date >= start,
                AttendanceSession.session_date <= end,
                AttendanceSession.event_cost.isnot(None),
            )
        )
        result = await self.db.execute(cost_stmt)
        row = result.one()
        total_cost = float(row[0] or 0)
        total_attendance = int(row[1] or 0)
        total_sessions = int(row[2] or 0)

        cost_per_attendee = round(total_cost / total_attendance, 2) if total_attendance > 0 else 0.0
        cost_per_event = round(total_cost / total_sessions, 2) if total_sessions > 0 else 0.0

        return {
            "total_cost": total_cost,
            "total_attendance": total_attendance,
            "total_sessions_with_cost": total_sessions,
            "cost_per_attendee": cost_per_attendee,
            "cost_per_event": cost_per_event,
        }

    async def _collection_impact(
        self,
        start: date,
        end: date,
        branch_id: Optional[int],
    ) -> Dict[str, Any]:
        checkout_stmt = select(func.count(Checkout.id)).where(
            and_(
                Checkout.checked_out_at >= datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc),
                Checkout.checked_out_at <= datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc),
            )
        )
        result = await self.db.execute(checkout_stmt)
        total_checkouts = result.scalar() or 0

        collection_stmt = select(func.count(CatalogItem.id))
        result = await self.db.execute(collection_stmt)
        collection_size = result.scalar() or 0

        turnover_rate = round(total_checkouts / collection_size, 2) if collection_size > 0 else 0.0

        return {
            "total_checkouts": total_checkouts,
            "collection_size": collection_size,
            "turnover_rate": turnover_rate,
        }

    async def generate_monthly_snapshot(
        self,
        year: int,
        month: int,
        branch_id: Optional[int] = None,
    ) -> None:
        import calendar
        period_start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        period_end = date(year, month, last_day)

        dispatch = {
            "program_reach": self._program_reach,
            "educational": self._educational,
            "partnerships": self._partnerships,
            "space_utilization": self._space_utilization,
            "cost_effectiveness": self._cost_effectiveness,
            "collection_impact": self._collection_impact,
        }

        for category, fn in dispatch.items():
            try:
                metrics = await fn(period_start, period_end, branch_id)
                stmt = pg_insert(CommunityMetricsSnapshot).values(
                    period_start=period_start,
                    period_end=period_end,
                    period_type="monthly",
                    category=category,
                    metrics=metrics,
                    branch_id=branch_id,
                    computed_at=datetime.now(timezone.utc),
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_cms_period_category_branch",
                    set_={
                        "metrics": stmt.excluded.metrics,
                        "computed_at": stmt.excluded.computed_at,
                    },
                )
                await self.db.execute(stmt)
            except Exception:
                logger.exception(
                    "Failed to generate snapshot for category=%s period=%s/%s",
                    category, year, month,
                )

        await self.db.commit()
        logger.info(
            "Monthly snapshots generated: year=%d month=%d branch_id=%s",
            year, month, branch_id,
        )
