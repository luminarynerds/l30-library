# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
import json
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Dict, List, NamedTuple, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import ProgrammingError
from app.core.logging import get_logger

from app.models.fair_scheduling import (
    PayrollRecord, PayrollExportBatch, PayrollExportStatus, PayrollPolicy,
    StaffSchedulingProfile, EmploymentType,
)
from app.models.staff_schedule_fairness import (
    StaffShift, FairnessShiftType, ShiftStatus,
)
from app.models.staff_time_entry import StaffTimeEntry, TimeEntryType
from app.models.user import User
from app.services.pay_rate_service import PayRateService
from app.services.time_entry_service import LIBRARY_TZ

logger = get_logger(__name__)

# Marker on shift rows auto-created so punch-only work can carry a payroll
# record (PayrollRecord.shift_id is NOT NULL). Keeps the "unscheduled" note
# stable even if a later punch resync flips the shift's status.
_UNSCHEDULED_SHIFT_NOTE = "Auto-created by payroll from time clock punches (no scheduled shift)"

# Pay policy lives in the single payroll_policy row (admin-edited). These
# constants, read from the PayrollRecord column defaults, are the fallback when
# the table or row is missing (e.g. mid-upgrade), so they can never drift from
# what an unconfigured record would stamp. Overtime/holiday multiply the full
# rate; weekend/evening are stored as multipliers (1.1 = +10%) and paid as the
# add-on portion.
_RECORD_DEFAULTS = PayrollRecord.__table__.columns
OVERTIME_MULTIPLIER = Decimal(str(_RECORD_DEFAULTS["overtime_multiplier"].default.arg))
HOLIDAY_MULTIPLIER = Decimal(str(_RECORD_DEFAULTS["holiday_multiplier"].default.arg))
WEEKEND_DIFFERENTIAL = Decimal(str(_RECORD_DEFAULTS["weekend_differential"].default.arg))
EVENING_DIFFERENTIAL = Decimal(str(_RECORD_DEFAULTS["evening_differential"].default.arg))
DEFAULT_OT_THRESHOLD_HOURS = 40.0
DEFAULT_EVENING_START = time(18, 0)


class _PayPolicy(NamedTuple):
    overtime_multiplier: Decimal
    holiday_multiplier: Decimal
    weekend_differential: Decimal
    evening_differential: Decimal
    default_ot_threshold_hours: float
    evening_start_local: time


_FALLBACK_POLICY = _PayPolicy(
    OVERTIME_MULTIPLIER, HOLIDAY_MULTIPLIER, WEEKEND_DIFFERENTIAL,
    EVENING_DIFFERENTIAL, DEFAULT_OT_THRESHOLD_HOURS, DEFAULT_EVENING_START,
)


class _PayableDay(NamedTuple):
    staff_id: int
    shift_date: date
    shift: Optional[StaffShift]
    hours: float
    punch_derived: bool


class PayrollIntegrationService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _load_pay_policy(self) -> _PayPolicy:
        """The payroll_policy row's values, or the shipped defaults when the
        table or row is missing (mid-upgrade safety)."""
        try:
            row = await self.db.get(PayrollPolicy, 1)
        except ProgrammingError:
            await self.db.rollback()
            return _FALLBACK_POLICY
        if row is None:
            return _FALLBACK_POLICY
        return _PayPolicy(
            Decimal(row.overtime_multiplier),
            Decimal(row.holiday_multiplier),
            Decimal(row.weekend_differential),
            Decimal(row.evening_differential),
            float(row.default_ot_threshold_hours),
            row.evening_start_local,
        )

    async def generate_payroll_records(
        self,
        branch_id: Optional[int],
        pay_period_start: date,
        pay_period_end: date,
    ) -> List[PayrollRecord]:
        # Load once per run, before any writes, so a missing-table rollback in
        # the fallback path cannot discard work.
        policy = await self._load_pay_policy()

        # Replace this period's unapproved records so a re-run reflects punch and
        # shift corrections instead of returning stale rows. Approved records are
        # kept untouched (full approval/period locking is a deferred enhancement).
        del_stmt = delete(PayrollRecord).where(and_(
            PayrollRecord.pay_period_start == pay_period_start,
            PayrollRecord.pay_period_end == pay_period_end,
            PayrollRecord.is_approved == False,  # noqa: E712
        ))
        if branch_id:
            del_stmt = del_stmt.where(PayrollRecord.shift_id.in_(
                select(StaffShift.id).where(StaffShift.branch_id == branch_id)
            ))
        await self.db.execute(del_stmt)

        payable = await self._collect_payable_work(
            branch_id, pay_period_start, pay_period_end, create_missing_shifts=True
        )

        # Track weekly hours per staff for overtime calculation. Seed with payable
        # work earlier in the period's first ISO week so weekly overtime does not
        # reset at a mid-week pay-period boundary.
        staff_weekly_hours: Dict[int, Dict[date, float]] = {}
        week_seed_start = pay_period_start - timedelta(days=pay_period_start.weekday())
        if week_seed_start < pay_period_start:
            prior_days = await self._collect_payable_work(
                branch_id, week_seed_start, pay_period_start - timedelta(days=1),
                create_missing_shifts=False,
            )
            for day in prior_days:
                week_start = day.shift_date - timedelta(days=day.shift_date.weekday())
                weekly = staff_weekly_hours.setdefault(day.staff_id, {})
                weekly[week_start] = weekly.get(week_start, 0.0) + day.hours

        records = []
        for day in payable:
            sid = day.staff_id
            shift = day.shift

            week_start = day.shift_date - timedelta(days=day.shift_date.weekday())
            weekly = staff_weekly_hours.setdefault(sid, {})
            weekly.setdefault(week_start, 0.0)

            # Only approved records survive the refresh above; keep them as-is and
            # accumulate their hours with the same formula new records use.
            existing = (await self.db.execute(
                select(PayrollRecord).where(and_(
                    PayrollRecord.staff_id == sid,
                    PayrollRecord.shift_id == shift.id,
                ))
            )).scalars().first()
            if existing:
                records.append(existing)
                existing_hours = (
                    existing.actual_hours if existing.actual_hours is not None
                    else existing.scheduled_hours
                )
                weekly[week_start] += existing_hours or 0.0
                continue

            # Get staff profile for rate info
            profile = (await self.db.execute(
                select(StaffSchedulingProfile).where(StaffSchedulingProfile.staff_id == sid)
            )).scalars().first()

            actual_hours = day.hours
            rate = await PayRateService(self.db).get_rate_for_date(sid, day.shift_date)

            # Calculate hours breakdown
            prior_weekly = weekly[week_start]
            # Without a profile, default to the policy's weekly threshold --
            # never the part-time 25h premium.
            if profile is not None and profile.employment_type != EmploymentType.FULL_TIME:
                max_regular = 25.0
            else:
                max_regular = policy.default_ot_threshold_hours

            regular_hours = min(actual_hours, max(0, max_regular - prior_weekly))
            overtime_hours = max(0, actual_hours - regular_hours)
            holiday_hours = actual_hours if shift.is_holiday else 0.0
            weekend_diff_hours = actual_hours if shift.is_weekend and not shift.is_holiday else 0.0

            # Evening differential (work ending at/after the policy's evening
            # start). Use the actual worked window when punches synced one; an
            # end earlier than the start means the shift crossed midnight, which
            # is also evening work. Applies to the whole day's hours, not just
            # the evening slice -- punch data carries no break positions inside
            # the window.
            evening_diff_hours = 0.0
            end_t = shift.actual_end or shift.scheduled_end
            start_t = shift.actual_start or shift.scheduled_start
            if end_t and (end_t >= policy.evening_start_local or (start_t and end_t < start_t)):
                evening_diff_hours = actual_hours

            # If holiday, all hours are holiday (not regular/OT)
            if shift.is_holiday:
                holiday_hours = actual_hours
                regular_hours = 0.0
                overtime_hours = 0.0

            if rate is not None:
                D = Decimal
                regular_pay = (D(regular_hours) * rate).quantize(D("0.01"))
                overtime_pay_val = (D(overtime_hours) * rate * policy.overtime_multiplier).quantize(D("0.01"))
                holiday_pay_val = (D(holiday_hours) * rate * policy.holiday_multiplier).quantize(D("0.01"))
                weekend_diff_pay = (D(weekend_diff_hours) * rate * (policy.weekend_differential - 1)).quantize(D("0.01"))
                evening_diff_pay = (D(evening_diff_hours) * rate * (policy.evening_differential - 1)).quantize(D("0.01"))
                total_pay = regular_pay + overtime_pay_val + holiday_pay_val + weekend_diff_pay + evening_diff_pay
                no_rate_flag = None
            else:
                regular_pay = overtime_pay_val = holiday_pay_val = None
                weekend_diff_pay = evening_diff_pay = total_pay = None
                no_rate_flag = "No pay rate on file"

            record_actual = day.hours if day.punch_derived else shift.actual_hours

            base_disc = (
                f"Scheduled: {shift.scheduled_hours}h, Actual: {record_actual}h"
                if record_actual is not None and abs((record_actual or 0) - (shift.scheduled_hours or 0)) > 0.25
                else (
                    f"Missing clock-out -- defaulted to scheduled {shift.scheduled_hours}h"
                    if record_actual is None and shift.scheduled_hours is not None
                    else None
                )
            )

            unscheduled_note = None
            if shift.status == ShiftStatus.UNSCHEDULED or (shift.notes or "").startswith(_UNSCHEDULED_SHIFT_NOTE):
                unscheduled_note = "Unscheduled work day -- hours taken from the time clock"
            elif day.punch_derived:
                unscheduled_note = "Shift was never completed or confirmed -- hours taken from the time clock"

            profile_note = (
                "No scheduling profile on file -- overtime threshold defaulted to "
                f"{policy.default_ot_threshold_hours:g}h/week"
                if profile is None else None
            )

            discrepancy_notes = "; ".join(
                p for p in (base_disc, unscheduled_note, profile_note, no_rate_flag) if p
            ) or None

            record = PayrollRecord(
                staff_id=sid,
                shift_id=shift.id,
                pay_period_start=pay_period_start,
                pay_period_end=pay_period_end,
                regular_hours=round(regular_hours, 2),
                overtime_hours=round(overtime_hours, 2),
                holiday_hours=round(holiday_hours, 2),
                weekend_differential_hours=round(weekend_diff_hours, 2),
                evening_differential_hours=round(evening_diff_hours, 2),
                overtime_multiplier=float(policy.overtime_multiplier),
                holiday_multiplier=float(policy.holiday_multiplier),
                weekend_differential=float(policy.weekend_differential),
                evening_differential=float(policy.evening_differential),
                scheduled_hours=shift.scheduled_hours,
                actual_hours=record_actual,
                hourly_rate_at_pay=rate,
                regular_pay=regular_pay,
                overtime_pay=overtime_pay_val,
                holiday_pay=holiday_pay_val,
                weekend_differential_pay=weekend_diff_pay,
                evening_differential_pay=evening_diff_pay,
                total_pay=total_pay,
                discrepancy_notes=discrepancy_notes,
            )

            self.db.add(record)
            records.append(record)
            weekly[week_start] += actual_hours

        await self.db.commit()
        return records

    async def _qualifying_shifts(
        self,
        branch_id: Optional[int],
        start: date,
        end: date,
    ) -> List[StaffShift]:
        """Shifts payroll can pay: completed/confirmed, or any other live status
        that already carries actual hours from the time clock."""
        conditions = [
            StaffShift.shift_date >= start,
            StaffShift.shift_date <= end,
            or_(
                StaffShift.status.in_([ShiftStatus.COMPLETED, ShiftStatus.CONFIRMED]),
                and_(
                    StaffShift.status.in_([ShiftStatus.ASSIGNED, ShiftStatus.UNSCHEDULED]),
                    StaffShift.actual_hours.is_not(None),
                ),
            ),
        ]
        if branch_id:
            conditions.append(StaffShift.branch_id == branch_id)
        return (await self.db.execute(
            select(StaffShift).where(and_(*conditions))
            .order_by(StaffShift.staff_id, StaffShift.shift_date)
        )).scalars().all()

    async def _punch_days_in_range(
        self,
        start: date,
        end: date,
    ) -> Dict[Tuple[int, date], List[StaffTimeEntry]]:
        entries = (await self.db.execute(
            select(StaffTimeEntry)
            .where(and_(
                StaffTimeEntry.shift_date >= start,
                StaffTimeEntry.shift_date <= end,
            ))
            .order_by(StaffTimeEntry.staff_id, StaffTimeEntry.shift_date, StaffTimeEntry.recorded_at)
        )).scalars().all()
        grouped: Dict[Tuple[int, date], List[StaffTimeEntry]] = {}
        for e in entries:
            grouped.setdefault((e.staff_id, e.shift_date), []).append(e)
        return grouped

    @staticmethod
    def _punch_day_hours(entries: List[StaffTimeEntry]) -> Tuple[Optional[float], bool]:
        """Sum completed clock-in/clock-out segments minus paired break time.

        Returns (hours, has_open_punch). hours is None when the day has no
        completed segment -- an open punch is never paid blind.
        """
        worked_hours = 0.0
        segments = 0
        open_in = None
        break_minutes = 0.0
        open_break = None
        for e in entries:
            if e.entry_type == TimeEntryType.CLOCK_IN:
                if open_in is None:
                    open_in = e
            elif e.entry_type == TimeEntryType.CLOCK_OUT:
                if open_in is not None:
                    worked_hours += (e.recorded_at - open_in.recorded_at).total_seconds() / 3600.0
                    open_in = None
                    segments += 1
            elif e.entry_type == TimeEntryType.BREAK_START:
                if open_break is None:
                    open_break = e
            elif e.entry_type == TimeEntryType.BREAK_END:
                if open_break is not None:
                    break_minutes += (e.recorded_at - open_break.recorded_at).total_seconds() / 60.0
                    open_break = None
        if segments == 0:
            return None, open_in is not None
        return max(round(worked_hours - break_minutes / 60.0, 2), 0.0), open_in is not None

    async def _build_unscheduled_shift(
        self,
        staff_id: int,
        day_date: date,
        entries: List[StaffTimeEntry],
        hours: float,
        branch_id: Optional[int],
    ) -> StaffShift:
        if branch_id is None:
            branch_id = (await self.db.execute(
                select(StaffSchedulingProfile.branch_id)
                .where(StaffSchedulingProfile.staff_id == staff_id)
            )).scalars().first() or 1
        first_in = next(e for e in entries if e.entry_type == TimeEntryType.CLOCK_IN)
        last_out = [e for e in entries if e.entry_type == TimeEntryType.CLOCK_OUT][-1]
        start_local = first_in.recorded_at.astimezone(LIBRARY_TZ)
        end_local = last_out.recorded_at.astimezone(LIBRARY_TZ)
        return StaffShift(
            staff_id=staff_id,
            branch_id=branch_id,
            shift_date=day_date,
            # FULL_DAY is the only neutral label present in both the Python enum
            # and the prod PG enum (which still lacks midday/evening/special_event).
            shift_type=FairnessShiftType.FULL_DAY,
            status=ShiftStatus.UNSCHEDULED,
            scheduled_start=start_local.time(),
            scheduled_end=end_local.time(),
            scheduled_hours=0.0,
            actual_start=start_local.time(),
            actual_end=end_local.time(),
            actual_hours=hours,
            is_weekend=day_date.weekday() >= 5,
            notes=_UNSCHEDULED_SHIFT_NOTE,
        )

    async def _collect_payable_work(
        self,
        branch_id: Optional[int],
        start: date,
        end: date,
        create_missing_shifts: bool,
    ) -> List[_PayableDay]:
        """Union of payable work in the window: qualifying shifts plus punch days
        with no qualifying shift row (worked-but-unscheduled must not pay $0)."""
        days: List[_PayableDay] = []
        covered = set()
        for shift in await self._qualifying_shifts(branch_id, start, end):
            covered.add((shift.staff_id, shift.shift_date))
            hours = shift.actual_hours if shift.actual_hours is not None else shift.scheduled_hours
            days.append(_PayableDay(shift.staff_id, shift.shift_date, shift, hours or 0.0, False))

        for (sid, day_date), entries in (await self._punch_days_in_range(start, end)).items():
            if (sid, day_date) in covered:
                continue
            hours, _has_open = self._punch_day_hours(entries)
            if hours is None:
                # No completed clock-in/clock-out pair (e.g. a dangling punch).
                # Surfaced by get_payroll_summary's uncovered_punches preflight.
                continue
            anchor = (await self.db.execute(
                select(StaffShift).where(and_(
                    StaffShift.staff_id == sid,
                    StaffShift.shift_date == day_date,
                )).order_by(StaffShift.id)
            )).scalars().first()
            if anchor is None:
                if not create_missing_shifts:
                    days.append(_PayableDay(sid, day_date, None, hours, True))
                    continue
                # PayrollRecord.shift_id is NOT NULL, so punch-only work needs a
                # shift row to hang the record on; it is created marked unscheduled.
                anchor = await self._build_unscheduled_shift(sid, day_date, entries, hours, branch_id)
                self.db.add(anchor)
                await self.db.flush()
            days.append(_PayableDay(sid, day_date, anchor, hours, True))

        days.sort(key=lambda d: (d.staff_id, d.shift_date))
        return days

    async def export_payroll(
        self,
        branch_id: Optional[int],
        pay_period_start: date,
        pay_period_end: date,
        export_format: str = "csv",
        exported_by_id: Optional[int] = None,
    ) -> Tuple[PayrollExportBatch, str]:
        # Generate records if not already done
        records = await self.generate_payroll_records(branch_id, pay_period_start, pay_period_end)

        # Create batch
        batch = PayrollExportBatch(
            batch_id=f"PAY-{uuid.uuid4().hex[:12].upper()}",
            branch_id=branch_id,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            total_records=len(records),
            total_regular_hours=sum(r.regular_hours for r in records),
            total_overtime_hours=sum(r.overtime_hours for r in records),
            total_holiday_hours=sum(r.holiday_hours for r in records),
            export_format=export_format,
            exported_by_id=exported_by_id,
        )

        try:
            if export_format == "csv":
                data = self._export_csv(records)
            elif export_format == "json":
                data = self._export_json(records, batch)
            else:
                data = self._export_csv(records)  # Default to CSV

            batch.export_status = PayrollExportStatus.EXPORTED
            batch.exported_at = datetime.now()

            # Mark records as exported
            for record in records:
                record.export_status = PayrollExportStatus.EXPORTED
                record.exported_at = datetime.now()
                record.export_batch_id = batch.batch_id

        except Exception as e:  # noqa: BLE001 -- export job boundary: any failure marks batch as ERROR for retry, must not crash route
            batch.export_status = PayrollExportStatus.ERROR
            batch.error_message = str(e)
            data = ""
            logger.error(f"Payroll export failed: {e}")

        self.db.add(batch)
        await self.db.commit()
        return batch, data

    async def get_payroll_summary(
        self,
        branch_id: Optional[int],
        pay_period_start: date,
        pay_period_end: date,
    ) -> Dict:
        from sqlalchemy import select
        records = (await self.db.execute(
            select(PayrollRecord).where(and_(
                PayrollRecord.pay_period_start == pay_period_start,
                PayrollRecord.pay_period_end == pay_period_end,
            ))
        )).scalars().all()

        # Group by staff
        staff_summary = {}
        for record in records:
            sid = record.staff_id
            if sid not in staff_summary:
                user = (await self.db.execute(
                    select(User).where(User.id == sid)
                )).scalars().first()
                name = f"{user.first_name} {user.last_name}" if user and hasattr(user, 'first_name') else f"#{sid}"
                staff_summary[sid] = {
                    "staff_id": sid,
                    "name": name,
                    "regular_hours": 0,
                    "overtime_hours": 0,
                    "holiday_hours": 0,
                    "weekend_differential_hours": 0,
                    "evening_differential_hours": 0,
                    "total_hours": 0,
                    "shifts_count": 0,
                    "has_discrepancy": False,
                }
            s = staff_summary[sid]
            s["regular_hours"] += record.regular_hours
            s["overtime_hours"] += record.overtime_hours
            s["holiday_hours"] += record.holiday_hours
            s["weekend_differential_hours"] += record.weekend_differential_hours
            s["evening_differential_hours"] += record.evening_differential_hours
            s["total_hours"] += record.regular_hours + record.overtime_hours + record.holiday_hours
            s["shifts_count"] += 1
            if record.discrepancy_notes:
                s["has_discrepancy"] = True

        # Preflight: period punches not covered by any qualifying shift. Before
        # generate runs these are the days it will pay as unscheduled; after, only
        # unpayable days (open or incomplete punches) remain listed.
        covered = {
            (s.staff_id, s.shift_date)
            for s in await self._qualifying_shifts(branch_id, pay_period_start, pay_period_end)
        }
        uncovered_punches = []
        for (sid, day_date), entries in (
            await self._punch_days_in_range(pay_period_start, pay_period_end)
        ).items():
            if (sid, day_date) in covered:
                continue
            hours, has_open = self._punch_day_hours(entries)
            if hours is None:
                punch_status = "open_punch" if has_open else "incomplete"
            else:
                punch_status = "payable_unscheduled"
            uncovered_punches.append({
                "staff_id": sid,
                "shift_date": str(day_date),
                "status": punch_status,
                "hours": hours,
                "open_punch": has_open,
            })
        uncovered_punches.sort(key=lambda u: (u["shift_date"], u["staff_id"]))

        return {
            "pay_period_start": str(pay_period_start),
            "pay_period_end": str(pay_period_end),
            "total_records": len(records),
            "total_regular_hours": round(sum(r.regular_hours for r in records), 2),
            "total_overtime_hours": round(sum(r.overtime_hours for r in records), 2),
            "total_holiday_hours": round(sum(r.holiday_hours for r in records), 2),
            "staff_details": list(staff_summary.values()),
            "records_with_discrepancy": sum(1 for r in records if r.discrepancy_notes),
            "pending_approval": sum(1 for r in records if not r.is_approved),
            "uncovered_punches": uncovered_punches,
        }

    async def approve_payroll(
        self,
        pay_period_start: date,
        pay_period_end: date,
        approved_by_id: int,
        staff_id: Optional[int] = None,
    ) -> int:
        from sqlalchemy import select
        conditions = [
            PayrollRecord.pay_period_start == pay_period_start,
            PayrollRecord.pay_period_end == pay_period_end,
            PayrollRecord.is_approved == False,  # noqa: E712
        ]
        if staff_id:
            conditions.append(PayrollRecord.staff_id == staff_id)
        records = (await self.db.execute(
            select(PayrollRecord).where(and_(*conditions))
        )).scalars().all()
        for record in records:
            record.is_approved = True
            record.approved_by_id = approved_by_id
            record.approved_at = datetime.now()

        await self.db.commit()
        return len(records)

    def _export_csv(self, records: List[PayrollRecord]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Staff ID", "Shift ID", "Pay Period Start", "Pay Period End",
            "Regular Hours", "Overtime Hours", "Holiday Hours",
            "Weekend Diff Hours", "Evening Diff Hours",
            "OT Multiplier", "Holiday Multiplier",
            "Weekend Diff Rate", "Evening Diff Rate",
            "Hourly Rate", "Regular Pay", "Overtime Pay", "Holiday Pay",
            "Weekend Diff Pay", "Evening Diff Pay", "Total Pay",
            "Scheduled Hours", "Actual Hours", "Discrepancy Notes",
        ])

        def money(value):
            return value if value is not None else ""

        for r in records:
            writer.writerow([
                r.staff_id, r.shift_id, r.pay_period_start, r.pay_period_end,
                r.regular_hours, r.overtime_hours, r.holiday_hours,
                r.weekend_differential_hours, r.evening_differential_hours,
                r.overtime_multiplier, r.holiday_multiplier,
                r.weekend_differential, r.evening_differential,
                money(r.hourly_rate_at_pay), money(r.regular_pay),
                money(r.overtime_pay), money(r.holiday_pay),
                money(r.weekend_differential_pay), money(r.evening_differential_pay),
                money(r.total_pay),
                r.scheduled_hours, r.actual_hours or "", r.discrepancy_notes or "",
            ])

        return output.getvalue()

    def _export_json(self, records: List[PayrollRecord], batch: PayrollExportBatch) -> str:
        data = {
            "batch_id": batch.batch_id,
            "pay_period_start": str(batch.pay_period_start),
            "pay_period_end": str(batch.pay_period_end),
            "exported_at": datetime.now().isoformat(),
            "records": [
                {
                    "staff_id": r.staff_id,
                    "shift_id": r.shift_id,
                    "regular_hours": r.regular_hours,
                    "overtime_hours": r.overtime_hours,
                    "holiday_hours": r.holiday_hours,
                    "weekend_differential_hours": r.weekend_differential_hours,
                    "evening_differential_hours": r.evening_differential_hours,
                    "overtime_multiplier": r.overtime_multiplier,
                    "holiday_multiplier": r.holiday_multiplier,
                    "weekend_differential": r.weekend_differential,
                    "evening_differential": r.evening_differential,
                    "hourly_rate_at_pay": r.hourly_rate_at_pay,
                    "regular_pay": r.regular_pay,
                    "overtime_pay": r.overtime_pay,
                    "holiday_pay": r.holiday_pay,
                    "weekend_differential_pay": r.weekend_differential_pay,
                    "evening_differential_pay": r.evening_differential_pay,
                    "total_pay": r.total_pay,
                    "scheduled_hours": r.scheduled_hours,
                    "actual_hours": r.actual_hours,
                }
                for r in records
            ],
        }
        return json.dumps(data, indent=2, default=str)
