# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Payroll generation pays from the shift/punch union and regenerates idempotently."""
import csv
import io
import json
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select

from app.models.fair_scheduling import (
    EmploymentType, PayrollExportBatch, PayrollPolicy, PayrollRecord,
    StaffSchedulingProfile,
)
from app.models.staff_pay_rate import StaffPayRate
from app.models.staff_schedule_fairness import FairnessShiftType, ShiftStatus, StaffShift
from app.models.staff_time_entry import StaffTimeEntry, TimeEntryType
from app.services.payroll_integration_service import PayrollIntegrationService

PERIOD_START = date(2026, 6, 1)  # Monday
PERIOD_END = date(2026, 6, 14)  # Sunday


@pytest.fixture(autouse=True)
async def _no_policy_row(test_db):
    # Every test here starts from an absent policy row (the fallback path);
    # tests that need an edited policy insert one themselves. Also shields
    # this file from policy edits left behind by the access-control suite.
    await test_db.execute(delete(PayrollPolicy))
    await test_db.commit()
    yield


@pytest.fixture
async def test_staff(test_db):
    # Shadows the global test_staff: this module commits durably through the
    # integration session, and the shared staff@example.com row then collides
    # with (or pollutes) other files in the same run. Unique email per run.
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=f"payroll-gen-{uuid.uuid4().hex[:10]}@example.com",
        password_hash=hash_password("PayrollGen123!"),
        first_name="Payroll",
        last_name="Gen",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


def _entry(staff_id, entry_type, day, hour, minute=0, duration=None):
    # Midday UTC times keep the local (America/New_York) date == shift_date.
    return StaffTimeEntry(
        staff_id=staff_id,
        entry_type=entry_type,
        recorded_at=datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc),
        shift_date=day,
        duration_minutes=duration,
    )


def _shift(staff_id, day, scheduled_hours, status, actual_hours=None):
    return StaffShift(
        staff_id=staff_id,
        branch_id=1,
        shift_date=day,
        shift_type=FairnessShiftType.FULL_DAY,
        status=status,
        scheduled_start=time(9, 0),
        scheduled_end=time(17, 0),
        scheduled_hours=scheduled_hours,
        actual_hours=actual_hours,
    )


def _rate(staff_id, rate="20.00"):
    return StaffPayRate(
        staff_id=staff_id, hourly_rate=Decimal(rate), effective_from=date(2026, 1, 1),
    )


async def test_punch_only_day_pays_with_unscheduled_note(test_db, test_staff):
    """A worked day with punches but no shift row must pay, not silently generate $0."""
    day = date(2026, 6, 3)
    test_db.add(_rate(test_staff.id))
    # 13:00-19:30 UTC with a 30-minute break = 6.0 worked hours.
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, day, 13))
    test_db.add(_entry(test_staff.id, TimeEntryType.BREAK_START, day, 16))
    test_db.add(_entry(test_staff.id, TimeEntryType.BREAK_END, day, 16, 30, duration=30.0))
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_OUT, day, 19, 30))
    await test_db.commit()

    records = await PayrollIntegrationService(test_db).generate_payroll_records(
        None, PERIOD_START, PERIOD_END
    )

    assert len(records) == 1
    r = records[0]
    assert r.regular_hours == 6.0
    assert r.overtime_hours == 0.0
    assert r.actual_hours == 6.0
    assert r.total_pay == Decimal("120.00")
    assert "unscheduled" in r.discrepancy_notes.lower()
    anchor = await test_db.get(StaffShift, r.shift_id)
    assert anchor is not None
    assert anchor.status == ShiftStatus.UNSCHEDULED


async def test_assigned_shift_with_actuals_pays(test_db, test_staff):
    test_db.add(_rate(test_staff.id))
    test_db.add(_shift(test_staff.id, date(2026, 6, 4), 7.5, ShiftStatus.ASSIGNED, actual_hours=7.0))
    await test_db.commit()

    records = await PayrollIntegrationService(test_db).generate_payroll_records(
        None, PERIOD_START, PERIOD_END
    )

    assert len(records) == 1
    assert records[0].regular_hours == 7.0
    assert records[0].actual_hours == 7.0


async def test_dangling_punch_day_is_not_paid_and_surfaces_in_summary(test_db, test_staff):
    """An open clock-in must not pay unbounded hours; the summary preflight flags it."""
    day = date(2026, 6, 5)
    test_db.add(_rate(test_staff.id))
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, day, 13))
    await test_db.commit()

    service = PayrollIntegrationService(test_db)
    records = await service.generate_payroll_records(None, PERIOD_START, PERIOD_END)
    assert records == []

    summary = await service.get_payroll_summary(None, PERIOD_START, PERIOD_END)
    flagged = summary["uncovered_punches"]
    assert len(flagged) == 1
    assert flagged[0]["staff_id"] == test_staff.id
    assert flagged[0]["status"] == "open_punch"
    assert flagged[0]["hours"] is None


async def test_regenerate_is_idempotent(test_db, test_staff):
    """Re-running generate must not duplicate records, shifts, or weekly tallies."""
    test_db.add(_rate(test_staff.id))
    punch_day = date(2026, 6, 3)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, punch_day, 13))
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_OUT, punch_day, 19))
    test_db.add(_shift(test_staff.id, date(2026, 6, 4), 8.0, ShiftStatus.COMPLETED, actual_hours=8.0))
    await test_db.commit()

    service = PayrollIntegrationService(test_db)
    first = await service.generate_payroll_records(None, PERIOD_START, PERIOD_END)
    first_hours = sorted((r.regular_hours, r.overtime_hours) for r in first)
    second = await service.generate_payroll_records(None, PERIOD_START, PERIOD_END)

    assert len(first) == len(second) == 2
    assert sorted((r.regular_hours, r.overtime_hours) for r in second) == first_hours
    record_count = (await test_db.execute(select(func.count(PayrollRecord.id)))).scalar_one()
    assert record_count == 2
    synthetic_count = (await test_db.execute(
        select(func.count(StaffShift.id)).where(StaffShift.status == ShiftStatus.UNSCHEDULED)
    )).scalar_one()
    assert synthetic_count == 1
    assert any("unscheduled" in (r.discrepancy_notes or "").lower() for r in second)


async def test_weekly_overtime_spans_period_boundary(test_db, test_staff):
    """Hours worked earlier in the ISO week, in the prior pay period, count toward OT."""
    test_db.add(_rate(test_staff.id))
    test_db.add(StaffSchedulingProfile(
        staff_id=test_staff.id,
        employment_type=EmploymentType.FULL_TIME,
        contracted_hours_per_week=40.0,
        min_hours_per_week=30.0,
        max_hours_per_week=45.0,
    ))
    # ISO week Mon 06-08 .. Sun 06-14: 30h before the boundary, 12h after it.
    for d in (8, 9, 10):
        test_db.add(_shift(test_staff.id, date(2026, 6, d), 10.0, ShiftStatus.COMPLETED, actual_hours=10.0))
    test_db.add(_shift(test_staff.id, date(2026, 6, 11), 12.0, ShiftStatus.COMPLETED, actual_hours=12.0))
    await test_db.commit()

    records = await PayrollIntegrationService(test_db).generate_payroll_records(
        None, date(2026, 6, 11), date(2026, 6, 24)
    )

    assert len(records) == 1
    assert records[0].regular_hours == 10.0
    assert records[0].overtime_hours == 2.0


async def test_missing_profile_defaults_to_40h_threshold(test_db, test_staff):
    """No scheduling profile must mean a 40h/week OT threshold, not the 25h part-time one."""
    test_db.add(_rate(test_staff.id))
    for d in (8, 9, 10):
        test_db.add(_shift(test_staff.id, date(2026, 6, d), 10.0, ShiftStatus.COMPLETED, actual_hours=10.0))
    await test_db.commit()

    records = await PayrollIntegrationService(test_db).generate_payroll_records(
        None, PERIOD_START, PERIOD_END
    )

    assert sum(r.regular_hours for r in records) == 30.0
    assert sum(r.overtime_hours for r in records) == 0.0
    assert all("no scheduling profile" in (r.discrepancy_notes or "").lower() for r in records)


async def test_record_pay_matches_exported_multipliers(test_db, test_staff):
    """Generation math, the stored record, and the export read the same multipliers."""
    test_db.add(_rate(test_staff.id))
    holiday = _shift(test_staff.id, date(2026, 6, 5), 8.0, ShiftStatus.COMPLETED, actual_hours=8.0)
    holiday.is_holiday = True
    evening = _shift(test_staff.id, date(2026, 6, 9), 8.0, ShiftStatus.COMPLETED, actual_hours=8.0)
    evening.actual_start = time(11, 0)
    evening.actual_end = time(19, 0)
    test_db.add_all([holiday, evening])
    await test_db.commit()

    service = PayrollIntegrationService(test_db)
    records = await service.generate_payroll_records(None, PERIOD_START, PERIOD_END)

    assert len(records) == 2
    by_shift = {r.shift_id: r for r in records}
    hol = by_shift[holiday.id]
    eve = by_shift[evening.id]
    # Pay must be computable from the multipliers persisted on the record itself.
    assert hol.holiday_pay == (
        Decimal(hol.holiday_hours) * hol.hourly_rate_at_pay * Decimal(str(hol.holiday_multiplier))
    ).quantize(Decimal("0.01"))
    assert hol.holiday_pay == Decimal("320.00")  # 8h * $20 * 2.0
    assert eve.evening_differential_pay == (
        Decimal(eve.evening_differential_hours) * eve.hourly_rate_at_pay
        * (Decimal(str(eve.evening_differential)) - 1)
    ).quantize(Decimal("0.01"))
    assert eve.evening_differential_pay == Decimal("24.00")  # 8h * $20 * 15%

    csv_rows = list(csv.DictReader(io.StringIO(service._export_csv(records))))
    hol_row = next(r for r in csv_rows if r["Shift ID"] == str(holiday.id))
    eve_row = next(r for r in csv_rows if r["Shift ID"] == str(evening.id))
    # An external system recomputing from the exported multipliers gets the exported pay.
    assert Decimal(hol_row["Holiday Pay"]) == (
        Decimal(hol_row["Holiday Hours"]) * Decimal(hol_row["Hourly Rate"])
        * Decimal(hol_row["Holiday Multiplier"])
    )
    assert Decimal(hol_row["Total Pay"]) == hol.total_pay
    assert Decimal(eve_row["Evening Diff Pay"]) == (
        Decimal(eve_row["Evening Diff Hours"]) * Decimal(eve_row["Hourly Rate"])
        * (Decimal(eve_row["Evening Diff Rate"]) - 1)
    )

    batch = PayrollExportBatch(
        batch_id="PAY-TEST", pay_period_start=PERIOD_START, pay_period_end=PERIOD_END,
    )
    json_records = json.loads(service._export_json(records, batch))["records"]
    json_hol = next(r for r in json_records if r["shift_id"] == holiday.id)
    assert Decimal(json_hol["total_pay"]) == hol.total_pay
    assert json_hol["holiday_multiplier"] == hol.holiday_multiplier


async def test_evening_differential_follows_actual_worked_window(test_db, test_staff):
    """Differential keys on when work actually ended, not the printed schedule.

    Documented approximation: once the worked window ends in the evening the
    differential covers the whole day's worked hours, not just the post-6pm
    slice -- punch data carries no break positions inside the window.
    """
    test_db.add(_rate(test_staff.id))
    left_early = _shift(test_staff.id, date(2026, 6, 2), 8.0, ShiftStatus.COMPLETED, actual_hours=7.0)
    left_early.scheduled_end = time(20, 0)
    left_early.actual_start = time(9, 0)
    left_early.actual_end = time(16, 0)
    stayed_late = _shift(test_staff.id, date(2026, 6, 3), 8.0, ShiftStatus.COMPLETED, actual_hours=9.5)
    stayed_late.actual_start = time(9, 0)
    stayed_late.actual_end = time(18, 30)
    overnight = _shift(test_staff.id, date(2026, 6, 4), 8.0, ShiftStatus.COMPLETED, actual_hours=6.0)
    overnight.actual_start = time(20, 0)
    overnight.actual_end = time(2, 0)
    test_db.add_all([left_early, stayed_late, overnight])
    await test_db.commit()

    records = await PayrollIntegrationService(test_db).generate_payroll_records(
        None, PERIOD_START, PERIOD_END
    )

    by_shift = {r.shift_id: r for r in records}
    assert by_shift[left_early.id].evening_differential_hours == 0.0
    assert by_shift[stayed_late.id].evening_differential_hours == 9.5
    assert by_shift[overnight.id].evening_differential_hours == 6.0


async def test_generation_uses_edited_policy_values(test_db, test_staff):
    """Generation reads multipliers, OT threshold, and evening start from the policy row."""
    test_db.add(_rate(test_staff.id))
    test_db.add(PayrollPolicy(
        id=1,
        overtime_multiplier=Decimal("1.75"),
        holiday_multiplier=Decimal("2.50"),
        weekend_differential=Decimal("1.25"),
        evening_differential=Decimal("1.30"),
        default_ot_threshold_hours=Decimal("30.0"),
        evening_start_local=time(16, 0),
    ))
    # 30h Mon-Wed ending mid-afternoon, then 5h Thursday ending 17:00: evening
    # under the edited 16:00 start (not the default 18:00), overtime past the
    # edited 30h threshold (not the default 40h).
    for d in (8, 9, 10):
        s = _shift(test_staff.id, date(2026, 6, d), 10.0, ShiftStatus.COMPLETED, actual_hours=10.0)
        s.scheduled_end = time(15, 0)
        test_db.add(s)
    late = _shift(test_staff.id, date(2026, 6, 11), 5.0, ShiftStatus.COMPLETED, actual_hours=5.0)
    test_db.add(late)
    await test_db.commit()

    records = await PayrollIntegrationService(test_db).generate_payroll_records(
        None, PERIOD_START, PERIOD_END
    )

    assert len(records) == 4
    by_shift = {r.shift_id: r for r in records}
    late_rec = by_shift[late.id]
    assert late_rec.regular_hours == 0.0
    assert late_rec.overtime_hours == 5.0
    assert late_rec.overtime_multiplier == 1.75
    assert late_rec.overtime_pay == Decimal("175.00")  # 5h * $20 * 1.75
    assert late_rec.evening_differential_hours == 5.0  # ends 17:00 >= edited 16:00 start
    assert late_rec.evening_differential == 1.30
    assert late_rec.evening_differential_pay == Decimal("30.00")  # 5h * $20 * 30%
    assert "30h/week" in late_rec.discrepancy_notes
    early = [r for r in records if r.shift_id != late.id]
    assert sum(r.regular_hours for r in early) == 30.0
    assert all(r.evening_differential_hours == 0.0 for r in early)
    assert all(r.holiday_multiplier == 2.5 and r.weekend_differential == 1.25 for r in records)


async def test_generation_falls_back_to_defaults_without_policy_row(test_db, test_staff):
    """An empty policy table (mid-upgrade) must pay with the shipped defaults."""
    test_db.add(_rate(test_staff.id))
    shift = _shift(test_staff.id, date(2026, 6, 5), 8.0, ShiftStatus.COMPLETED, actual_hours=8.0)
    shift.is_holiday = True
    test_db.add(shift)
    await test_db.commit()

    records = await PayrollIntegrationService(test_db).generate_payroll_records(
        None, PERIOD_START, PERIOD_END
    )

    assert len(records) == 1
    r = records[0]
    assert r.overtime_multiplier == 1.5
    assert r.holiday_multiplier == 2.0
    assert r.weekend_differential == 1.1
    assert r.evening_differential == 1.15
    assert r.holiday_pay == Decimal("320.00")  # 8h * $20 * 2.0


async def test_payroll_policy_is_single_row(test_db):
    from sqlalchemy.exc import IntegrityError

    test_db.add(PayrollPolicy(id=2))
    with pytest.raises(IntegrityError):
        await test_db.commit()
    await test_db.rollback()


async def test_generate_endpoint_returns_records(admin_client, test_db, test_staff):
    test_db.add(_rate(test_staff.id))
    test_db.add(_shift(test_staff.id, date(2026, 6, 2), 8.0, ShiftStatus.COMPLETED, actual_hours=8.0))
    await test_db.commit()

    resp = await admin_client.post(
        "/api/v1/fair-scheduling/payroll/generate",
        params={"pay_period_start": "2026-06-01", "pay_period_end": "2026-06-14"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["regular_hours"] == 8.0


async def test_dashboard_survives_multiple_export_batches(admin_client, test_db):
    test_db.add(PayrollExportBatch(
        batch_id="PAY-A", pay_period_start=PERIOD_START, pay_period_end=PERIOD_END,
    ))
    test_db.add(PayrollExportBatch(
        batch_id="PAY-B", pay_period_start=PERIOD_START, pay_period_end=PERIOD_END,
    ))
    await test_db.commit()

    resp = await admin_client.get("/api/v1/fair-scheduling/dashboard", params={"branch_id": 1})

    assert resp.status_code == 200, resp.text
    assert resp.json()["payroll_status"]["latest_batch"] in ("PAY-A", "PAY-B")
