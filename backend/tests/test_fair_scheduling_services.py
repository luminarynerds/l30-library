# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Fair Scheduling Services:
- Exhaustion Tracking Service (fatigue calculation and levels)
- Call-Out Coverage Service (urgency classification)
- Payroll Integration Service (payroll record helpers)

Uses MagicMock for db session since the services use synchronous
db.query() patterns. Tests focus on pure-logic methods and scoring
algorithms that can be verified without a live database.
"""

import pytest
from datetime import date, time, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

from app.models.staff_schedule_fairness import (
    FairnessShiftType, ShiftStatus,
)
from app.models.fair_scheduling import (
    FatigueLevel, CalloutUrgency,
    EmploymentType,
)


# =============================================================================
# Helper: lightweight shift stub for testing helper methods
# =============================================================================

class FakeShift:
    """Lightweight shift stub matching StaffShift attributes used in calculations."""

    def __init__(
        self,
        shift_date,
        scheduled_start=time(9, 0),
        scheduled_end=time(17, 0),
        scheduled_hours=8.0,
        actual_hours=None,
        shift_type=FairnessShiftType.MIDDAY,
        status=ShiftStatus.COMPLETED,
        is_weekend=False,
        is_holiday=False,
        is_overtime=False,
    ):
        self.shift_date = shift_date
        self.scheduled_start = scheduled_start
        self.scheduled_end = scheduled_end
        self.scheduled_hours = scheduled_hours
        self.actual_hours = actual_hours if actual_hours is not None else scheduled_hours
        self.shift_type = shift_type
        self.status = status
        self.is_weekend = is_weekend
        self.is_holiday = is_holiday
        self.is_overtime = is_overtime


# =============================================================================
# EXHAUSTION / FATIGUE TRACKING TESTS
# =============================================================================

class TestFatigueScoreCalculation:
    """Tests for the fatigue score formula and level classification."""

    @pytest.fixture
    def service(self):
        from app.services.exhaustion_tracking_service import ExhaustionTrackingService
        mock_db = MagicMock()
        return ExhaustionTrackingService(mock_db)

    def test_zero_fatigue_for_no_work(self, service):
        """Staff with no recent work should have zero fatigue."""
        score = service._compute_fatigue_score(
            consecutive_days=0,
            hours_7d=0.0,
            closing_7d=0,
            short_turnarounds=0,
            overtime_30d=0.0,
            days_since_off=0,
            max_hours=40,
            max_consec=5,
        )
        assert score == 0.0

    def test_moderate_fatigue_for_normal_week(self, service):
        """A normal 40h week should produce moderate fatigue."""
        score = service._compute_fatigue_score(
            consecutive_days=5,
            hours_7d=40.0,
            closing_7d=1,
            short_turnarounds=0,
            overtime_30d=0.0,
            days_since_off=5,
            max_hours=40,
            max_consec=5,
        )
        # 5 consecutive at 5 max = 100 * 0.25 = 25
        # 40h at 40 max = 100 * 0.25 = 25
        # 1 closing of 3 = 33.3 * 0.15 = 5
        # 0 turnarounds = 0
        # 0 overtime = 0
        # 5 days since off at 5 max = 100 * 0.10 = 10
        # total ≈ 65
        assert 50 <= score <= 80

    def test_critical_fatigue_for_overworked(self, service):
        """Extremely overworked staff should hit critical fatigue."""
        score = service._compute_fatigue_score(
            consecutive_days=7,
            hours_7d=55.0,
            closing_7d=5,
            short_turnarounds=3,
            overtime_30d=25.0,
            days_since_off=7,
            max_hours=40,
            max_consec=5,
        )
        assert score >= 80  # Should be CRITICAL level

    def test_score_capped_at_100(self, service):
        """Fatigue score should never exceed 100."""
        score = service._compute_fatigue_score(
            consecutive_days=20,
            hours_7d=100.0,
            closing_7d=10,
            short_turnarounds=10,
            overtime_30d=50.0,
            days_since_off=20,
            max_hours=40,
            max_consec=5,
        )
        assert score <= 100.0

    def test_score_to_level_low(self, service):
        assert service._score_to_level(0) == FatigueLevel.LOW
        assert service._score_to_level(15) == FatigueLevel.LOW
        assert service._score_to_level(30) == FatigueLevel.LOW

    def test_score_to_level_moderate(self, service):
        assert service._score_to_level(31) == FatigueLevel.MODERATE
        assert service._score_to_level(45) == FatigueLevel.MODERATE
        assert service._score_to_level(55) == FatigueLevel.MODERATE

    def test_score_to_level_high(self, service):
        assert service._score_to_level(56) == FatigueLevel.HIGH
        assert service._score_to_level(70) == FatigueLevel.HIGH
        assert service._score_to_level(80) == FatigueLevel.HIGH

    def test_score_to_level_critical(self, service):
        assert service._score_to_level(81) == FatigueLevel.CRITICAL
        assert service._score_to_level(100) == FatigueLevel.CRITICAL


class TestFatigueHelperMethods:
    """Tests for helper calculations in the exhaustion service."""

    @pytest.fixture
    def service(self):
        from app.services.exhaustion_tracking_service import ExhaustionTrackingService
        mock_db = MagicMock()
        return ExhaustionTrackingService(mock_db)

    def test_count_consecutive_days_all_consecutive(self, service):
        """Consecutive days with no gaps."""
        today = date(2024, 3, 8)
        shifts = [
            FakeShift(shift_date=today - timedelta(days=i))
            for i in range(5)
        ]
        assert service._count_consecutive_days(shifts, today) == 5

    def test_count_consecutive_days_with_gap(self, service):
        """Gap in schedule resets consecutive count."""
        today = date(2024, 3, 8)
        shifts = [
            FakeShift(shift_date=today),
            FakeShift(shift_date=today - timedelta(days=1)),
            # gap on day -2
            FakeShift(shift_date=today - timedelta(days=3)),
        ]
        assert service._count_consecutive_days(shifts, today) == 2

    def test_count_consecutive_days_no_shifts(self, service):
        """No shifts means 0 consecutive days."""
        assert service._count_consecutive_days([], date(2024, 3, 8)) == 0

    def test_sum_hours_in_range(self, service):
        """Sum hours only within the specified date range."""
        today = date(2024, 3, 8)
        shifts = [
            FakeShift(shift_date=today, scheduled_hours=8.0),
            FakeShift(shift_date=today - timedelta(days=1), scheduled_hours=6.0),
            FakeShift(shift_date=today - timedelta(days=10), scheduled_hours=8.0),  # Out of range
        ]
        total = service._sum_hours(shifts, today - timedelta(days=7), today)
        assert total == 14.0

    def test_count_shift_type(self, service):
        """Count only closing shifts in range."""
        today = date(2024, 3, 8)
        shifts = [
            FakeShift(shift_date=today, shift_type=FairnessShiftType.CLOSING),
            FakeShift(shift_date=today - timedelta(days=1), shift_type=FairnessShiftType.CLOSING),
            FakeShift(shift_date=today - timedelta(days=2), shift_type=FairnessShiftType.MIDDAY),
            FakeShift(shift_date=today - timedelta(days=3), shift_type=FairnessShiftType.OPENING),
        ]
        count = service._count_shift_type(
            shifts, FairnessShiftType.CLOSING,
            today - timedelta(days=7), today
        )
        assert count == 2

    def test_count_short_turnarounds(self, service):
        """Detect shifts with <10 hour gap."""
        shifts = [
            FakeShift(
                shift_date=date(2024, 3, 7),
                scheduled_start=time(14, 0),
                scheduled_end=time(22, 0),
            ),
            FakeShift(
                shift_date=date(2024, 3, 8),
                scheduled_start=time(7, 0),  # 9h gap < 10h
                scheduled_end=time(15, 0),
            ),
        ]
        assert service._count_short_turnarounds(shifts) == 1

    def test_no_short_turnarounds_with_gap(self, service):
        """Adequate gap between shifts (12h) should not count."""
        shifts = [
            FakeShift(
                shift_date=date(2024, 3, 7),
                scheduled_start=time(9, 0),
                scheduled_end=time(17, 0),
            ),
            FakeShift(
                shift_date=date(2024, 3, 8),
                scheduled_start=time(9, 0),  # 16h gap > 10h
                scheduled_end=time(17, 0),
            ),
        ]
        assert service._count_short_turnarounds(shifts) == 0

    def test_calculate_overtime(self, service):
        """Sum only overtime-flagged shifts."""
        shifts = [
            FakeShift(shift_date=date(2024, 3, 7), scheduled_hours=8.0, is_overtime=True),
            FakeShift(shift_date=date(2024, 3, 8), scheduled_hours=8.0, is_overtime=False),
            FakeShift(shift_date=date(2024, 3, 9), scheduled_hours=4.0, is_overtime=True),
        ]
        assert service._calculate_overtime(shifts, 1) == 12.0

    def test_days_since_last_off(self, service):
        """Count backwards from date until a gap is found."""
        today = date(2024, 3, 8)
        shifts = [
            FakeShift(shift_date=today),
            FakeShift(shift_date=today - timedelta(days=1)),
            FakeShift(shift_date=today - timedelta(days=2)),
            # Day off on day -3
        ]
        assert service._days_since_last_off(shifts, today) == 3


# =============================================================================
# CALL-OUT COVERAGE TESTS
# =============================================================================

class TestCalloutUrgencyClassification:
    """Tests for urgency classification based on lead time."""

    @pytest.fixture
    def service(self):
        from app.services.callout_coverage_service import CalloutCoverageService
        mock_db = MagicMock()
        return CalloutCoverageService(mock_db)

    def test_emergency_under_4_hours(self, service):
        assert service._determine_urgency(2) == CalloutUrgency.EMERGENCY

    def test_emergency_at_boundary(self, service):
        assert service._determine_urgency(3.9) == CalloutUrgency.EMERGENCY

    def test_high_4_to_24_hours(self, service):
        assert service._determine_urgency(4) == CalloutUrgency.HIGH
        assert service._determine_urgency(12) == CalloutUrgency.HIGH
        assert service._determine_urgency(23.9) == CalloutUrgency.HIGH

    def test_medium_24_to_48_hours(self, service):
        assert service._determine_urgency(24) == CalloutUrgency.MEDIUM
        assert service._determine_urgency(36) == CalloutUrgency.MEDIUM
        assert service._determine_urgency(47.9) == CalloutUrgency.MEDIUM

    def test_low_over_48_hours(self, service):
        assert service._determine_urgency(48) == CalloutUrgency.LOW
        assert service._determine_urgency(72) == CalloutUrgency.LOW
        assert service._determine_urgency(168) == CalloutUrgency.LOW


# =============================================================================
# PAYROLL CALCULATION TESTS
# =============================================================================

class TestPayrollHelpers:
    """Tests for payroll export formatting helpers."""

    @pytest.fixture
    def service(self):
        from app.services.payroll_integration_service import PayrollIntegrationService
        mock_db = MagicMock()
        return PayrollIntegrationService(mock_db)

    def test_csv_export_format(self, service):
        """Test CSV export produces correct header and rows."""

        class FakeRecord:
            staff_id = 1
            shift_id = 10
            regular_hours = 8.0
            overtime_hours = 0.0
            holiday_hours = 0.0
            weekend_differential_hours = 0.0
            evening_differential_hours = 0.0
            overtime_multiplier = 1.5
            holiday_multiplier = 2.0
            weekend_differential = 1.1
            evening_differential = 1.15
            hourly_rate_at_pay = Decimal("20.00")
            regular_pay = Decimal("160.00")
            overtime_pay = Decimal("0.00")
            holiday_pay = Decimal("0.00")
            weekend_differential_pay = Decimal("0.00")
            evening_differential_pay = Decimal("0.00")
            total_pay = Decimal("160.00")
            scheduled_hours = 8.0
            actual_hours = 8.0
            pay_period_start = date(2024, 3, 4)
            pay_period_end = date(2024, 3, 10)
            discrepancy_notes = None

        csv_data = service._export_csv([FakeRecord()])

        assert "Staff ID" in csv_data
        assert "Regular Hours" in csv_data
        assert "Total Pay" in csv_data
        assert "8.0" in csv_data
        assert "160.00" in csv_data

    def test_csv_export_empty(self, service):
        """Empty records should still produce header."""
        csv_data = service._export_csv([])
        assert "Staff ID" in csv_data

    def test_json_export_format(self, service):
        """Test JSON export produces valid structure."""
        import json

        class FakeRecord:
            staff_id = 1
            shift_id = 10
            regular_hours = 8.0
            overtime_hours = 0.0
            holiday_hours = 0.0
            weekend_differential_hours = 0.0
            evening_differential_hours = 0.0
            overtime_multiplier = 1.5
            holiday_multiplier = 2.0
            weekend_differential = 1.1
            evening_differential = 1.15
            hourly_rate_at_pay = Decimal("20.00")
            regular_pay = Decimal("160.00")
            overtime_pay = Decimal("0.00")
            holiday_pay = Decimal("0.00")
            weekend_differential_pay = Decimal("0.00")
            evening_differential_pay = Decimal("0.00")
            total_pay = Decimal("160.00")
            scheduled_hours = 8.0
            actual_hours = 8.0

        class FakeBatch:
            batch_id = "PAY-TEST-001"
            pay_period_start = date(2024, 3, 4)
            pay_period_end = date(2024, 3, 10)

        json_data = service._export_json([FakeRecord()], FakeBatch())

        parsed = json.loads(json_data)
        assert parsed["batch_id"] == "PAY-TEST-001"
        assert "records" in parsed
        assert len(parsed["records"]) == 1
        assert parsed["records"][0]["staff_id"] == 1
        assert parsed["records"][0]["regular_hours"] == 8.0
        assert parsed["records"][0]["total_pay"] == "160.00"

    def test_json_export_empty(self, service):
        """Empty records should produce valid JSON."""
        import json

        class FakeBatch:
            batch_id = "PAY-EMPTY"
            pay_period_start = date(2024, 3, 4)
            pay_period_end = date(2024, 3, 10)

        json_data = service._export_json([], FakeBatch())
        parsed = json.loads(json_data)
        assert parsed["batch_id"] == "PAY-EMPTY"
        assert parsed["records"] == []


# =============================================================================
# CONSTRAINT SOLVER INTEGRATION (via dataclass logic, no DB)
# =============================================================================

class TestSolverFullRun:
    """Test the solver's full _solve method with in-memory data."""

    def test_solve_assigns_all_staff_fairly(self):
        """Run the solver with small data and verify fair assignment."""
        from app.services.constraint_schedule_solver import (
            ConstraintScheduleSolver, ShiftSlot, StaffMember, StaffAvailability,
        )
        from app.models.staff_schedule_fairness import FairnessShiftType, PreferenceType
        from app.models.fair_scheduling import EmploymentType, ScheduleGenerationStatus

        mock_db = MagicMock()
        solver = ConstraintScheduleSolver(mock_db)
        config = solver._default_config()
        # Use min_staff=1 so 4 staff can cover 8 slots across 2 days
        config["min_staff_per_shift"] = 1

        # 2 days, 4 shifts/day = 8 slots × 1 min_staff = 8 assignments needed
        slots = solver._generate_shift_slots(1, date(2024, 3, 4), date(2024, 3, 5), config)

        # 4 staff members with all skills
        staff = [
            StaffMember(
                staff_id=i, name=f"Staff{i}", employment_type=EmploymentType.FULL_TIME,
                skills=["cash_register", "opening_procedures", "closing_procedures"],
                min_hours=20, max_hours=40, contracted_hours=40,
                seniority_level=3, max_consecutive_days=5,
                min_hours_between_shifts=10, max_weekend_shifts_per_month=4,
                max_closing_shifts_per_week=3, desirable_shift_score=50,
            ) for i in range(4)
        ]

        availability = {s.staff_id: [] for s in staff}
        historical = {s.staff_id: {"overall_score": 50} for s in staff}

        result = solver._solve(slots, staff, availability, historical, config)

        assert result.status in (
            ScheduleGenerationStatus.OPTIMAL,
            ScheduleGenerationStatus.FEASIBLE,
        )
        assert len(result.assignments) > 0
        assert result.fairness_score > 0

        # Verify each assignment has an explanation
        for assignment in result.assignments:
            assert assignment.explanation_text
            assert assignment.contributing_factors

    def test_solve_with_skill_constraints(self):
        """Staff without required skills should not be assigned to skill-required slots."""
        from app.services.constraint_schedule_solver import (
            ConstraintScheduleSolver, ShiftSlot, StaffMember,
        )
        from app.models.staff_schedule_fairness import FairnessShiftType

        mock_db = MagicMock()
        solver = ConstraintScheduleSolver(mock_db)

        # One opening slot requiring opening_procedures
        slots = [ShiftSlot(
            slot_id=0, branch_id=1, shift_date=date(2024, 3, 4),
            shift_type=FairnessShiftType.OPENING, start_time=time(8, 0),
            end_time=time(13, 0), hours=5.0, is_weekend=False, is_holiday=False,
            required_skills=["opening_procedures"], min_staff=1,
        )]

        # One staff with the skill, one without
        staff = [
            StaffMember(
                staff_id=0, name="Skilled", employment_type=EmploymentType.FULL_TIME,
                skills=["opening_procedures"], min_hours=20, max_hours=40,
                contracted_hours=40, seniority_level=3, max_consecutive_days=5,
                min_hours_between_shifts=10, max_weekend_shifts_per_month=4,
                max_closing_shifts_per_week=3, desirable_shift_score=50,
            ),
            StaffMember(
                staff_id=1, name="Unskilled", employment_type=EmploymentType.FULL_TIME,
                skills=["cash_register"], min_hours=20, max_hours=40,
                contracted_hours=40, seniority_level=3, max_consecutive_days=5,
                min_hours_between_shifts=10, max_weekend_shifts_per_month=4,
                max_closing_shifts_per_week=3, desirable_shift_score=50,
            ),
        ]

        availability = {0: [], 1: []}
        historical = {0: {"overall_score": 50}, 1: {"overall_score": 50}}
        config = solver._default_config()

        result = solver._solve(slots, staff, availability, historical, config)

        # Only the skilled staff should be assigned
        assigned_ids = {a.staff.staff_id for a in result.assignments}
        assert 0 in assigned_ids
        assert 1 not in assigned_ids

    def test_solve_honors_preferences(self):
        """Staff with preferred shift types should be favored for those slots."""
        from app.services.constraint_schedule_solver import (
            ConstraintScheduleSolver, ShiftSlot, StaffMember, StaffAvailability,
        )
        from app.models.staff_schedule_fairness import FairnessShiftType, PreferenceType

        mock_db = MagicMock()
        solver = ConstraintScheduleSolver(mock_db)

        slots = [ShiftSlot(
            slot_id=0, branch_id=1, shift_date=date(2024, 3, 4),
            shift_type=FairnessShiftType.OPENING, start_time=time(8, 0),
            end_time=time(13, 0), hours=5.0, is_weekend=False, is_holiday=False,
            min_staff=1,
        )]

        staff = [
            StaffMember(
                staff_id=i, name=f"S{i}", employment_type=EmploymentType.FULL_TIME,
                skills=[], min_hours=20, max_hours=40, contracted_hours=40,
                seniority_level=3, max_consecutive_days=5,
                min_hours_between_shifts=10, max_weekend_shifts_per_month=4,
                max_closing_shifts_per_week=3, desirable_shift_score=50,
            ) for i in range(2)
        ]

        # Staff 0 prefers opening, staff 1 has no preference
        availability = {
            0: [StaffAvailability(
                staff_id=0, day_of_week=None, shift_type=FairnessShiftType.OPENING,
                preference=PreferenceType.PREFERRED,
            )],
            1: [],
        }
        historical = {0: {"overall_score": 50}, 1: {"overall_score": 50}}
        config = solver._default_config()

        result = solver._solve(slots, staff, availability, historical, config)

        # Staff 0 should be assigned (preference bonus)
        if result.assignments:
            assert result.assignments[0].staff.staff_id == 0
