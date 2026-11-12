# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, select, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import (
    AgeRange,
    AttendanceCheckIn,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceTrend,
    CheckInMethod,
    SurveyStatus,
)
from app.models.event import Event
from app.models.program import Program
from app.models.user import User

logger = get_logger(__name__)


class AttendanceService:

    # ========================================================================
    # Session Management
    # ========================================================================

    @staticmethod
    async def create_session(
        db: AsyncSession,
        session_name: str,
        session_date: date,
        staff_id: int,
        event_id: Optional[int] = None,
        program_id: Optional[int] = None,
        head_count_mode: bool = False,
        event_cost: Optional[Decimal] = None,
        cost_notes: Optional[str] = None,
        survey_enabled: bool = True,
        survey_link: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AttendanceSession:
        qr_token = str(uuid.uuid4()).replace("-", "")[:24]

        session = AttendanceSession(
            event_id=event_id,
            program_id=program_id,
            session_name=session_name,
            session_date=session_date,
            status=AttendanceSessionStatus.OPEN,
            qr_code_token=qr_token,
            head_count_mode=head_count_mode,
            event_cost=event_cost,
            cost_notes=cost_notes,
            survey_enabled=survey_enabled,
            survey_link=survey_link,
            opened_by_id=staff_id,
            notes=notes,
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_session(db: AsyncSession, session_id: int) -> Optional[AttendanceSession]:
        result = await db.execute(
            select(AttendanceSession).where(AttendanceSession.id == session_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_session_by_qr_token(db: AsyncSession, qr_token: str) -> Optional[AttendanceSession]:
        result = await db.execute(
            select(AttendanceSession).where(AttendanceSession.qr_code_token == qr_token)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def close_session(
        db: AsyncSession, session_id: int, staff_id: int
    ) -> AttendanceSession:
        result = await db.execute(
            select(AttendanceSession).where(AttendanceSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("Session not found")
        if session.status != AttendanceSessionStatus.OPEN:
            raise ValueError("Session is not open")

        session.status = AttendanceSessionStatus.CLOSED
        session.closed_by_id = staff_id
        session.closed_at = datetime.now(timezone.utc)
        await db.flush()
        return session

    @staticmethod
    async def finalize_session(
        db: AsyncSession, session_id: int
    ) -> AttendanceSession:
        result = await db.execute(
            select(AttendanceSession).where(AttendanceSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("Session not found")

        session.status = AttendanceSessionStatus.FINALIZED
        await db.flush()
        return session

    @staticmethod
    async def list_sessions(
        db: AsyncSession,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_id: Optional[int] = None,
        program_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[AttendanceSession], int]:
        query = select(AttendanceSession)
        count_query = select(func.count(AttendanceSession.id))

        if status:
            query = query.where(AttendanceSession.status == status)
            count_query = count_query.where(AttendanceSession.status == status)
        if start_date:
            query = query.where(AttendanceSession.session_date >= start_date)
            count_query = count_query.where(AttendanceSession.session_date >= start_date)
        if end_date:
            query = query.where(AttendanceSession.session_date <= end_date)
            count_query = count_query.where(AttendanceSession.session_date <= end_date)
        if event_id:
            query = query.where(AttendanceSession.event_id == event_id)
            count_query = count_query.where(AttendanceSession.event_id == event_id)
        if program_id:
            query = query.where(AttendanceSession.program_id == program_id)
            count_query = count_query.where(AttendanceSession.program_id == program_id)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.order_by(AttendanceSession.session_date.desc()).offset(offset).limit(per_page)

        result = await db.execute(query)
        sessions = list(result.scalars().all())

        return sessions, total

    # ========================================================================
    # Check-In Operations
    # ========================================================================

    @staticmethod
    async def _detect_repeat_attendee(
        db: AsyncSession,
        patron_id: Optional[int] = None,
        library_card: Optional[str] = None,
        guest_email: Optional[str] = None,
    ) -> tuple[bool, int, Optional[date]]:
        conditions = []
        if patron_id:
            conditions.append(AttendanceCheckIn.patron_id == patron_id)
        if library_card:
            conditions.append(AttendanceCheckIn.library_card_number == library_card)
        if guest_email:
            conditions.append(
                func.lower(AttendanceCheckIn.guest_email) == guest_email.lower()
            )

        if not conditions:
            return False, 0, None

        from sqlalchemy import or_
        result = await db.execute(
            select(
                func.count(AttendanceCheckIn.id),
                func.min(AttendanceCheckIn.checked_in_at),
            ).where(or_(*conditions))
        )
        row = result.one()
        count = row[0] or 0
        first_date = row[1].date() if row[1] else None

        return count > 0, count, first_date

    @staticmethod
    async def _update_session_counts(
        db: AsyncSession, session: AttendanceSession, method: CheckInMethod
    ) -> None:
        session.total_checked_in = (session.total_checked_in or 0) + 1
        if method == CheckInMethod.WALK_IN:
            session.total_walk_ins = (session.total_walk_ins or 0) + 1
        elif method == CheckInMethod.LIBRARY_CARD:
            session.total_card_scans = (session.total_card_scans or 0) + 1
        elif method == CheckInMethod.QR_CODE:
            session.total_qr_scans = (session.total_qr_scans or 0) + 1
        elif method == CheckInMethod.PRE_REGISTERED:
            session.total_pre_registered = (session.total_pre_registered or 0) + 1

    @staticmethod
    async def check_in_qr(
        db: AsyncSession,
        qr_token: str,
        patron_id: Optional[int] = None,
        guest_name: Optional[str] = None,
        guest_email: Optional[str] = None,
        age_range: str = "unknown",
    ) -> AttendanceCheckIn:
        session = await AttendanceService.get_session_by_qr_token(db, qr_token)
        if not session:
            raise ValueError("Invalid QR code")
        if session.status != AttendanceSessionStatus.OPEN:
            raise ValueError("This session is no longer accepting check-ins")

        # Detect repeat
        is_repeat, visit_count, first_date = await AttendanceService._detect_repeat_attendee(
            db, patron_id=patron_id, guest_email=guest_email
        )

        check_in = AttendanceCheckIn(
            session_id=session.id,
            patron_id=patron_id,
            guest_name=guest_name,
            guest_email=guest_email,
            check_in_method=CheckInMethod.QR_CODE,
            age_range=age_range or AgeRange.UNKNOWN,
            is_repeat_attendee=is_repeat,
            previous_visit_count=visit_count,
            first_visit_date=first_date,
        )
        db.add(check_in)
        await AttendanceService._update_session_counts(db, session, CheckInMethod.QR_CODE)
        await db.flush()
        await db.refresh(check_in)
        await _try_grant_event_credits(db, check_in)
        return check_in

    @staticmethod
    async def check_in_library_card(
        db: AsyncSession,
        session_id: int,
        library_card_number: str,
        staff_id: int,
        age_range_override: Optional[str] = None,
    ) -> AttendanceCheckIn:
        session = await AttendanceService.get_session(db, session_id)
        if not session:
            raise ValueError("Session not found")
        if session.status != AttendanceSessionStatus.OPEN:
            raise ValueError("This session is no longer accepting check-ins")

        # Look up patron by library card
        patron_result = await db.execute(
            select(User).where(User.library_card == library_card_number)
        )
        patron = patron_result.scalar_one_or_none()

        patron_id = patron.id if patron else None

        # Determine age range from patron DOB or override
        age_range = age_range_override or AgeRange.UNKNOWN
        if patron and patron.date_of_birth and not age_range_override:
            age = patron.age
            if age is not None:
                if age <= 5:
                    age_range = AgeRange.CHILD_0_5
                elif age <= 12:
                    age_range = AgeRange.CHILD_6_12
                elif age <= 17:
                    age_range = AgeRange.TEEN_13_17
                elif age <= 34:
                    age_range = AgeRange.ADULT_18_34
                elif age <= 54:
                    age_range = AgeRange.ADULT_35_54
                elif age <= 64:
                    age_range = AgeRange.ADULT_55_64
                else:
                    age_range = AgeRange.SENIOR_65_PLUS

        # Check for duplicate check-in
        if patron_id:
            existing = await db.execute(
                select(AttendanceCheckIn).where(
                    and_(
                        AttendanceCheckIn.session_id == session_id,
                        AttendanceCheckIn.patron_id == patron_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError("This patron is already checked in for this session")

        # Detect repeat
        is_repeat, visit_count, first_date = await AttendanceService._detect_repeat_attendee(
            db, patron_id=patron_id, library_card=library_card_number
        )

        check_in = AttendanceCheckIn(
            session_id=session_id,
            patron_id=patron_id,
            library_card_number=library_card_number,
            check_in_method=CheckInMethod.LIBRARY_CARD,
            checked_in_by_id=staff_id,
            age_range=age_range,
            is_repeat_attendee=is_repeat,
            previous_visit_count=visit_count,
            first_visit_date=first_date,
        )
        db.add(check_in)
        await AttendanceService._update_session_counts(db, session, CheckInMethod.LIBRARY_CARD)
        await db.flush()
        await db.refresh(check_in)
        await _try_grant_event_credits(db, check_in)
        return check_in

    @staticmethod
    async def check_in_walk_in(
        db: AsyncSession,
        session_id: int,
        staff_id: int,
        guest_name: Optional[str] = None,
        guest_email: Optional[str] = None,
        guest_phone: Optional[str] = None,
        age_range: str = "unknown",
        notes: Optional[str] = None,
    ) -> AttendanceCheckIn:
        session = await AttendanceService.get_session(db, session_id)
        if not session:
            raise ValueError("Session not found")
        if session.status != AttendanceSessionStatus.OPEN:
            raise ValueError("This session is no longer accepting check-ins")

        # Detect repeat
        is_repeat, visit_count, first_date = await AttendanceService._detect_repeat_attendee(
            db, guest_email=guest_email
        )

        check_in = AttendanceCheckIn(
            session_id=session_id,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            check_in_method=CheckInMethod.WALK_IN,
            checked_in_by_id=staff_id,
            age_range=age_range or AgeRange.UNKNOWN,
            is_repeat_attendee=is_repeat,
            previous_visit_count=visit_count,
            first_visit_date=first_date,
            notes=notes,
        )
        db.add(check_in)
        await AttendanceService._update_session_counts(db, session, CheckInMethod.WALK_IN)
        await db.flush()
        await db.refresh(check_in)
        await _try_grant_event_credits(db, check_in)
        return check_in

    @staticmethod
    async def check_in_pre_registered(
        db: AsyncSession,
        session_id: int,
        registration_id: int,
        staff_id: int,
        patron_id: Optional[int] = None,
        guest_name: Optional[str] = None,
        guest_email: Optional[str] = None,
        age_range: str = "unknown",
    ) -> AttendanceCheckIn:
        session = await AttendanceService.get_session(db, session_id)
        if not session:
            raise ValueError("Session not found")
        if session.status != AttendanceSessionStatus.OPEN:
            raise ValueError("This session is no longer accepting check-ins")

        # Idempotency guard: don't double-count if the staff member
        # re-clicks "Mark attended" on the same row.
        existing = await db.execute(
            select(AttendanceCheckIn).where(
                and_(
                    AttendanceCheckIn.session_id == session_id,
                    AttendanceCheckIn.registration_id == registration_id,
                    AttendanceCheckIn.check_in_method == CheckInMethod.PRE_REGISTERED,
                )
            )
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row:
            return existing_row

        is_repeat, visit_count, first_date = await AttendanceService._detect_repeat_attendee(
            db, patron_id=patron_id, guest_email=guest_email
        )

        check_in = AttendanceCheckIn(
            session_id=session_id,
            registration_id=registration_id,
            patron_id=patron_id,
            guest_name=guest_name,
            guest_email=guest_email,
            check_in_method=CheckInMethod.PRE_REGISTERED,
            checked_in_by_id=staff_id,
            age_range=age_range or AgeRange.UNKNOWN,
            is_repeat_attendee=is_repeat,
            previous_visit_count=visit_count,
            first_visit_date=first_date,
        )
        db.add(check_in)
        await AttendanceService._update_session_counts(db, session, CheckInMethod.PRE_REGISTERED)
        await db.flush()
        await db.refresh(check_in)
        await _try_grant_event_credits(db, check_in)
        return check_in

    @staticmethod
    async def update_head_count(
        db: AsyncSession,
        session_id: int,
        total: int,
        by_age: Optional[dict] = None,
    ) -> AttendanceSession:
        session = await AttendanceService.get_session(db, session_id)
        if not session:
            raise ValueError("Session not found")

        session.head_count_total = total
        if by_age:
            session.head_count_by_age = by_age
        await db.flush()
        return session

    @staticmethod
    async def get_session_check_ins(
        db: AsyncSession, session_id: int
    ) -> list[AttendanceCheckIn]:
        result = await db.execute(
            select(AttendanceCheckIn)
            .where(AttendanceCheckIn.session_id == session_id)
            .order_by(AttendanceCheckIn.checked_in_at.desc())
        )
        return list(result.scalars().all())

    # ========================================================================
    # Survey Distribution
    # ========================================================================

    @staticmethod
    async def send_surveys(
        db: AsyncSession,
        session_id: int,
        survey_link: Optional[str] = None,
    ) -> dict:
        session = await AttendanceService.get_session(db, session_id)
        if not session:
            raise ValueError("Session not found")

        link = survey_link or session.survey_link
        if not link:
            raise ValueError("No survey link configured")

        # Get all check-ins with email addresses
        result = await db.execute(
            select(AttendanceCheckIn).where(
                and_(
                    AttendanceCheckIn.session_id == session_id,
                    AttendanceCheckIn.survey_status == SurveyStatus.PENDING,
                )
            )
        )
        check_ins = list(result.scalars().all())

        sent = 0
        no_email = 0
        now = datetime.now(timezone.utc)

        for ci in check_ins:
            # Determine email: from patron record or guest_email
            email = ci.guest_email
            if ci.patron_id and not email:
                patron_result = await db.execute(
                    select(User.email).where(User.id == ci.patron_id)
                )
                patron_email = patron_result.scalar_one_or_none()
                email = patron_email

            if email:
                # In production: send actual email here
                ci.survey_status = SurveyStatus.SENT
                ci.survey_sent_at = now
                sent += 1
                logger.info(f"Survey sent for session {session_id}")
            else:
                no_email += 1

        session.survey_link = link
        session.survey_sent_at = now
        await db.flush()

        return {
            "session_id": session_id,
            "total_eligible": len(check_ins),
            "total_sent": sent,
            "total_failed": 0,
            "total_opted_out": no_email,
        }

    # ========================================================================
    # Analytics & Dashboard
    # ========================================================================

    @staticmethod
    async def get_dashboard(db: AsyncSession) -> dict:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Today's sessions
        today_result = await db.execute(
            select(
                func.count(AttendanceSession.id),
                func.coalesce(func.sum(AttendanceSession.total_checked_in), 0),
                func.coalesce(func.sum(AttendanceSession.head_count_total), 0),
            ).where(AttendanceSession.session_date == today)
        )
        today_row = today_result.one()
        today_sessions = today_row[0]
        today_checked_in = today_row[1]
        today_head_count = today_row[2]

        # This week
        week_result = await db.execute(
            select(
                func.coalesce(func.sum(AttendanceSession.total_checked_in), 0),
                func.coalesce(func.sum(AttendanceSession.head_count_total), 0),
            ).where(AttendanceSession.session_date >= week_start)
        )
        week_row = week_result.one()

        # This month
        month_result = await db.execute(
            select(
                func.coalesce(func.sum(AttendanceSession.total_checked_in), 0),
                func.coalesce(func.sum(AttendanceSession.head_count_total), 0),
                func.count(AttendanceSession.id),
            ).where(AttendanceSession.session_date >= month_start)
        )
        month_row = month_result.one()
        month_sessions = month_row[2] or 1

        # Average attendance per event this month
        month_total = int(month_row[0]) + int(month_row[1])
        avg_attendance = round(month_total / max(month_sessions, 1), 1)

        # Repeat attendee rate (last 30 days)
        thirty_days_ago = today - timedelta(days=30)
        repeat_result = await db.execute(
            select(
                func.count(AttendanceCheckIn.id),
                func.sum(
                    func.cast(AttendanceCheckIn.is_repeat_attendee, Integer)
                ),
            ).join(AttendanceSession).where(
                AttendanceSession.session_date >= thirty_days_ago
            )
        )
        repeat_row = repeat_result.one()
        total_checkins_30d = repeat_row[0] or 0
        repeat_count_30d = repeat_row[1] or 0
        repeat_rate = round(
            (repeat_count_30d / max(total_checkins_30d, 1)) * 100, 1
        )

        # Check-in method distribution (last 30 days)
        method_result = await db.execute(
            select(
                AttendanceCheckIn.check_in_method,
                func.count(AttendanceCheckIn.id),
            )
            .join(AttendanceSession)
            .where(AttendanceSession.session_date >= thirty_days_ago)
            .group_by(AttendanceCheckIn.check_in_method)
        )
        method_dist = {}
        top_method = "walk_in"
        top_count = 0
        for method, count in method_result.all():
            method_dist[method] = count
            if count > top_count:
                top_method = method
                top_count = count

        # Age distribution (last 30 days)
        age_result = await db.execute(
            select(
                AttendanceCheckIn.age_range,
                func.count(AttendanceCheckIn.id),
            )
            .join(AttendanceSession)
            .where(AttendanceSession.session_date >= thirty_days_ago)
            .group_by(AttendanceCheckIn.age_range)
        )
        age_dist = dict(age_result.all())

        # Recent sessions
        recent_result = await db.execute(
            select(AttendanceSession)
            .order_by(AttendanceSession.session_date.desc())
            .limit(10)
        )
        recent_sessions = list(recent_result.scalars().all())

        recent_list = []
        for s in recent_sessions:
            effective = (s.total_checked_in or 0) + (s.head_count_total or 0)
            cost_per = None
            if s.event_cost and effective > 0:
                cost_per = round(float(s.event_cost) / effective, 2)
            recent_list.append({
                "id": s.id,
                "session_name": s.session_name,
                "session_date": s.session_date.isoformat(),
                "status": s.status.value if hasattr(s.status, 'value') else s.status,
                "event_id": s.event_id,
                "program_id": s.program_id,
                "head_count_mode": s.head_count_mode,
                "total_checked_in": s.total_checked_in,
                "head_count_total": s.head_count_total,
                "effective_total": effective,
                "cost_per_attendee": cost_per,
            })

        return {
            "today_sessions": today_sessions,
            "today_total_attendance": int(today_checked_in) + int(today_head_count),
            "week_total_attendance": int(week_row[0]) + int(week_row[1]),
            "month_total_attendance": month_total,
            "avg_attendance_per_event": avg_attendance,
            "repeat_attendee_rate": repeat_rate,
            "top_check_in_method": top_method,
            "recent_sessions": recent_list,
            "age_distribution": age_dist,
            "method_distribution": method_dist,
        }

    @staticmethod
    async def get_trends(
        db: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        program_type: Optional[str] = None,
        period_type: str = "monthly",
    ) -> list[dict]:
        query = select(AttendanceTrend)

        if start_date:
            query = query.where(AttendanceTrend.period_start >= start_date)
        if end_date:
            query = query.where(AttendanceTrend.period_end <= end_date)
        if program_type:
            query = query.where(AttendanceTrend.program_type == program_type)
        if period_type:
            query = query.where(AttendanceTrend.period_type == period_type)

        query = query.order_by(AttendanceTrend.period_start.asc())

        result = await db.execute(query)
        trends = result.scalars().all()
        return [
            {
                "period_start": t.period_start.isoformat(),
                "period_end": t.period_end.isoformat(),
                "period_type": t.period_type,
                "program_type": t.program_type,
                "audience": t.audience,
                "total_sessions": t.total_sessions,
                "total_attendance": t.total_attendance,
                "avg_attendance_per_session": t.avg_attendance_per_session,
                "total_walk_ins": t.total_walk_ins,
                "total_repeat_attendees": t.total_repeat_attendees,
                "total_new_attendees": t.total_new_attendees,
                "total_cost": float(t.total_cost),
                "cost_per_attendee": float(t.cost_per_attendee),
                "age_distribution": t.age_distribution,
                "method_distribution": t.method_distribution,
            }
            for t in trends
        ]

    @staticmethod
    async def get_roi_report(
        db: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        if not start_date:
            start_date = date.today() - timedelta(days=365)
        if not end_date:
            end_date = date.today()

        # Aggregate session data
        result = await db.execute(
            select(
                func.count(AttendanceSession.id),
                func.coalesce(func.sum(AttendanceSession.total_checked_in), 0),
                func.coalesce(func.sum(AttendanceSession.head_count_total), 0),
                func.coalesce(func.sum(AttendanceSession.event_cost), 0),
            ).where(
                and_(
                    AttendanceSession.session_date >= start_date,
                    AttendanceSession.session_date <= end_date,
                )
            )
        )
        row = result.one()
        total_events = row[0]
        total_checked_in = int(row[1])
        total_head_count = int(row[2])
        total_cost = Decimal(str(row[3]))
        total_attendance = total_checked_in + total_head_count

        cost_per = Decimal("0")
        if total_attendance > 0:
            cost_per = round(total_cost / total_attendance, 2)

        # Repeat rate
        repeat_result = await db.execute(
            select(
                func.count(AttendanceCheckIn.id),
                func.sum(func.cast(AttendanceCheckIn.is_repeat_attendee, Integer)),
            )
            .join(AttendanceSession)
            .where(
                and_(
                    AttendanceSession.session_date >= start_date,
                    AttendanceSession.session_date <= end_date,
                )
            )
        )
        rr = repeat_result.one()
        total_ci = rr[0] or 0
        repeat_ci = rr[1] or 0
        repeat_rate = round((repeat_ci / max(total_ci, 1)) * 100, 1)

        # Top sessions by attendance
        top_result = await db.execute(
            select(
                AttendanceSession.session_name,
                (AttendanceSession.total_checked_in + AttendanceSession.head_count_total).label("total"),
            )
            .where(
                and_(
                    AttendanceSession.session_date >= start_date,
                    AttendanceSession.session_date <= end_date,
                )
            )
            .order_by(
                (AttendanceSession.total_checked_in + AttendanceSession.head_count_total).desc()
            )
            .limit(10)
        )
        top_programs = [
            {"name": name, "attendance": attendance}
            for name, attendance in top_result.all()
        ]

        return {
            "period_label": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "total_events": total_events,
            "total_attendance": total_attendance,
            "total_cost": float(total_cost),
            "cost_per_attendee": float(cost_per),
            "repeat_rate": repeat_rate,
            "top_programs": top_programs,
            "cost_breakdown": None,
        }


async def _try_grant_event_credits(
    db: AsyncSession, check_in: AttendanceCheckIn
) -> None:
    try:
        from app.services.event_attendance_credit_service import (
            grant_event_attendance_credits,
        )

        await grant_event_attendance_credits(db, check_in)
    except Exception:  # noqa: BLE001  -- truly last-resort, attendance must succeed
        logger.exception(
            "failed to grant event-attendance reading-program credits for check_in=%s",
            getattr(check_in, "id", "?"),
        )
