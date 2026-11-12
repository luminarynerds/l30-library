# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.core.logging import get_logger

from app.models.fair_scheduling import (
    StaffFatigueRecord, FatigueLevel, StaffSchedulingProfile,
)
from app.models.staff_schedule_fairness import (
    StaffShift, FairnessShiftType, ShiftStatus,
)

logger = get_logger(__name__)


class ExhaustionTrackingService:

    def __init__(self, db: Session):
        self.db = db

    async def calculate_fatigue(
        self, staff_id: int, as_of_date: Optional[date] = None
    ) -> StaffFatigueRecord:
        check_date = as_of_date or date.today()

        # Load recent shifts
        shifts_14d = self.db.query(StaffShift).filter(
            and_(
                StaffShift.staff_id == staff_id,
                StaffShift.shift_date >= check_date - timedelta(days=14),
                StaffShift.shift_date <= check_date,
                StaffShift.status.in_([
                    ShiftStatus.ASSIGNED, ShiftStatus.CONFIRMED, ShiftStatus.COMPLETED
                ]),
            )
        ).order_by(StaffShift.shift_date).all()

        shifts_30d = self.db.query(StaffShift).filter(
            and_(
                StaffShift.staff_id == staff_id,
                StaffShift.shift_date >= check_date - timedelta(days=30),
                StaffShift.shift_date <= check_date,
                StaffShift.status.in_([
                    ShiftStatus.ASSIGNED, ShiftStatus.CONFIRMED, ShiftStatus.COMPLETED
                ]),
            )
        ).all()

        # Calculate metrics
        consecutive_days = self._count_consecutive_days(shifts_14d, check_date)
        hours_7d = self._sum_hours(shifts_14d, check_date - timedelta(days=7), check_date)
        hours_14d = self._sum_hours(shifts_14d, check_date - timedelta(days=14), check_date)
        closing_7d = self._count_shift_type(shifts_14d, FairnessShiftType.CLOSING, check_date - timedelta(days=7), check_date)
        short_turnarounds = self._count_short_turnarounds(shifts_14d)
        overtime_30d = self._calculate_overtime(shifts_30d, staff_id)
        days_since_off = self._days_since_last_off(shifts_14d, check_date)
        weekend_30d = sum(1 for s in shifts_30d if s.is_weekend)

        # Load profile for thresholds
        profile = self.db.query(StaffSchedulingProfile).filter(
            StaffSchedulingProfile.staff_id == staff_id
        ).first()
        max_hours = profile.max_hours_per_week if profile else 40
        max_consec = profile.max_consecutive_days if profile else 5

        # Calculate fatigue score
        fatigue_score = self._compute_fatigue_score(
            consecutive_days=consecutive_days,
            hours_7d=hours_7d,
            closing_7d=closing_7d,
            short_turnarounds=short_turnarounds,
            overtime_30d=overtime_30d,
            days_since_off=days_since_off,
            max_hours=max_hours,
            max_consec=max_consec,
        )

        fatigue_level = self._score_to_level(fatigue_score)

        # Determine trend
        prev_record = self.db.query(StaffFatigueRecord).filter(
            and_(
                StaffFatigueRecord.staff_id == staff_id,
                StaffFatigueRecord.record_date < check_date,
            )
        ).order_by(StaffFatigueRecord.record_date.desc()).first()

        if prev_record:
            if fatigue_score > prev_record.fatigue_score + 5:
                trend = "increasing"
            elif fatigue_score < prev_record.fatigue_score - 5:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Generate alert if needed
        alert_triggered = fatigue_level in (FatigueLevel.HIGH, FatigueLevel.CRITICAL)
        alert_message = None
        if fatigue_level == FatigueLevel.CRITICAL:
            alert_message = (
                f"CRITICAL fatigue alert: {consecutive_days} consecutive days, "
                f"{hours_7d:.1f}h in last 7 days, {short_turnarounds} short turnarounds. "
                f"Recommend immediate schedule relief."
            )
        elif fatigue_level == FatigueLevel.HIGH:
            alert_message = (
                f"High fatigue warning: {consecutive_days} consecutive days, "
                f"{hours_7d:.1f}h in last 7 days. Consider reducing upcoming shifts."
            )

        # Upsert record
        record = self.db.query(StaffFatigueRecord).filter(
            and_(
                StaffFatigueRecord.staff_id == staff_id,
                StaffFatigueRecord.record_date == check_date,
            )
        ).first()

        if not record:
            record = StaffFatigueRecord(
                staff_id=staff_id,
                record_date=check_date,
            )

        record.fatigue_level = fatigue_level
        record.fatigue_score = round(fatigue_score, 1)
        record.consecutive_days_worked = consecutive_days
        record.hours_last_7_days = round(hours_7d, 1)
        record.hours_last_14_days = round(hours_14d, 1)
        record.closing_shifts_last_7_days = closing_7d
        record.short_turnarounds_last_14_days = short_turnarounds
        record.overtime_hours_last_30_days = round(overtime_30d, 1)
        record.days_since_last_day_off = days_since_off
        record.weekend_shifts_last_30_days = weekend_30d
        record.fatigue_trend = trend
        record.alert_triggered = alert_triggered
        record.alert_message = alert_message
        record.calculated_at = datetime.now()

        self.db.add(record)
        await self.db.commit()
        return record

    async def get_team_fatigue(
        self, branch_id: int, as_of_date: Optional[date] = None
    ) -> List[Dict]:
        check_date = as_of_date or date.today()

        profiles = self.db.query(StaffSchedulingProfile).filter(
            and_(
                StaffSchedulingProfile.is_active == True,
                (StaffSchedulingProfile.branch_id == branch_id) |
                (StaffSchedulingProfile.branch_id.is_(None)),
            )
        ).all()

        results = []
        for profile in profiles:
            record = await self.calculate_fatigue(profile.staff_id, check_date)
            results.append({
                "staff_id": profile.staff_id,
                "fatigue_level": str(record.fatigue_level),
                "fatigue_score": record.fatigue_score,
                "consecutive_days": record.consecutive_days_worked,
                "hours_7d": record.hours_last_7_days,
                "trend": record.fatigue_trend,
                "alert": record.alert_message,
            })

        results.sort(key=lambda r: r["fatigue_score"], reverse=True)
        return results

    async def get_fatigue_history(
        self, staff_id: int, days: int = 30
    ) -> List[StaffFatigueRecord]:
        since = date.today() - timedelta(days=days)
        return self.db.query(StaffFatigueRecord).filter(
            and_(
                StaffFatigueRecord.staff_id == staff_id,
                StaffFatigueRecord.record_date >= since,
            )
        ).order_by(StaffFatigueRecord.record_date).all()

    def _compute_fatigue_score(
        self,
        consecutive_days: int,
        hours_7d: float,
        closing_7d: int,
        short_turnarounds: int,
        overtime_30d: float,
        days_since_off: int,
        max_hours: float,
        max_consec: int,
    ) -> float:
        # Consecutive days factor (0-100)
        consec_factor = min(100, (consecutive_days / max(max_consec, 1)) * 100)

        # Weekly hours factor (0-100)
        hours_factor = min(100, (hours_7d / max(max_hours, 1)) * 100)

        # Closing shift density (0-100)
        # More than 3 closing shifts in a week is concerning
        closing_factor = min(100, (closing_7d / 3) * 100)

        # Short turnaround factor (0-100)
        # Any short turnaround is bad, 3+ is very bad
        turnaround_factor = min(100, (short_turnarounds / 2) * 100)

        # Overtime factor (0-100)
        # > 20 hours overtime in 30 days is very concerning
        overtime_factor = min(100, (overtime_30d / 20) * 100)

        # Days since off factor (0-100)
        off_factor = min(100, (days_since_off / max(max_consec, 1)) * 100)

        score = (
            consec_factor * 0.25
            + hours_factor * 0.25
            + closing_factor * 0.15
            + turnaround_factor * 0.15
            + overtime_factor * 0.10
            + off_factor * 0.10
        )

        return min(100, max(0, score))

    def _score_to_level(self, score: float) -> FatigueLevel:
        if score <= 30:
            return FatigueLevel.LOW
        elif score <= 55:
            return FatigueLevel.MODERATE
        elif score <= 80:
            return FatigueLevel.HIGH
        return FatigueLevel.CRITICAL

    def _count_consecutive_days(self, shifts: List[StaffShift], as_of: date) -> int:
        work_dates = {s.shift_date for s in shifts}
        count = 0
        check = as_of
        while check in work_dates:
            count += 1
            check -= timedelta(days=1)
        return count

    def _sum_hours(self, shifts: List[StaffShift], start: date, end: date) -> float:
        return sum(
            s.scheduled_hours for s in shifts
            if start <= s.shift_date <= end
        )

    def _count_shift_type(
        self, shifts: List[StaffShift], shift_type: FairnessShiftType,
        start: date, end: date
    ) -> int:
        return sum(
            1 for s in shifts
            if s.shift_type == shift_type and start <= s.shift_date <= end
        )

    def _count_short_turnarounds(self, shifts: List[StaffShift]) -> int:
        sorted_shifts = sorted(shifts, key=lambda s: (s.shift_date, s.scheduled_start))
        count = 0
        for i in range(1, len(sorted_shifts)):
            prev = sorted_shifts[i - 1]
            curr = sorted_shifts[i]
            if curr.shift_date == prev.shift_date + timedelta(days=1):
                prev_end = prev.scheduled_end.hour * 60 + prev.scheduled_end.minute
                curr_start = curr.scheduled_start.hour * 60 + curr.scheduled_start.minute
                gap_hours = (24 * 60 - prev_end + curr_start) / 60
                if gap_hours < 10:
                    count += 1
        return count

    def _calculate_overtime(self, shifts: List[StaffShift], staff_id: int) -> float:
        return sum(s.scheduled_hours for s in shifts if s.is_overtime)

    def _days_since_last_off(self, shifts: List[StaffShift], as_of: date) -> int:
        work_dates = {s.shift_date for s in shifts}
        count = 0
        check = as_of
        while check in work_dates:
            count += 1
            check -= timedelta(days=1)
        return count
