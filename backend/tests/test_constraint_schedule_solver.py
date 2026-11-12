# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the Fair Scheduling Constraint Solver.

Tests the constraint-based schedule generation including:
- Shift slot generation
- Hard constraint enforcement (max hours, clopening, skills)
- Soft constraint scoring (preferences, fairness, fatigue)
- Schedule explanation generation
- Overall solver integration

Uses MagicMock for db since the methods under test use pure logic
on dataclass inputs rather than querying the database directly.
"""

import pytest
from datetime import date, time, timedelta
from unittest.mock import MagicMock

from app.models.staff_schedule_fairness import (
    FairnessShiftType, PreferenceType,
)
from app.models.fair_scheduling import (
    ScheduleExplanationType, EmploymentType,
)
from app.services.constraint_schedule_solver import (
    ConstraintScheduleSolver, ShiftSlot, StaffMember, StaffAvailability,
)


@pytest.fixture
def solver():
    """Create a solver with a mocked db session."""
    mock_db = MagicMock()
    return ConstraintScheduleSolver(mock_db)


@pytest.fixture
def default_staff():
    """Create a default full-time staff member for testing."""
    return StaffMember(
        staff_id=1, name="Test", employment_type=EmploymentType.FULL_TIME,
        skills=["cash_register"], min_hours=35, max_hours=40,
        contracted_hours=40, seniority_level=1, max_consecutive_days=5,
        min_hours_between_shifts=10, max_weekend_shifts_per_month=4,
        max_closing_shifts_per_week=3, desirable_shift_score=50,
    )


@pytest.fixture
def default_slot():
    """Create a default midday shift slot for testing."""
    return ShiftSlot(
        slot_id=1, branch_id=1, shift_date=date(2024, 3, 8),
        shift_type=FairnessShiftType.MIDDAY, start_time=time(10, 0),
        end_time=time(15, 0), hours=5.0, is_weekend=False, is_holiday=False,
    )


class TestShiftSlotGeneration:
    """Tests for generating shift slots from configuration."""

    def test_generates_slots_for_each_day(self, solver):
        """Test that slots are generated for every day in the period."""
        config = solver._default_config()
        start = date(2024, 3, 4)  # Monday
        end = date(2024, 3, 10)   # Sunday

        slots = solver._generate_shift_slots(1, start, end, config)

        days = 7
        shifts_per_day = len(config["shifts_per_day"])
        assert len(slots) == days * shifts_per_day

    def test_weekend_detection(self, solver):
        """Test that weekend shifts are properly marked."""
        config = solver._default_config()
        start = date(2024, 3, 4)   # Monday
        end = date(2024, 3, 10)    # Sunday

        slots = solver._generate_shift_slots(1, start, end, config)

        saturday_slots = [s for s in slots if s.shift_date == date(2024, 3, 9)]
        sunday_slots = [s for s in slots if s.shift_date == date(2024, 3, 10)]
        monday_slots = [s for s in slots if s.shift_date == date(2024, 3, 4)]

        assert all(s.is_weekend for s in saturday_slots)
        assert all(s.is_weekend for s in sunday_slots)
        assert not any(s.is_weekend for s in monday_slots)

    def test_holiday_detection(self, solver):
        """Test that holidays are properly marked in slots."""
        config = solver._default_config()
        config["holiday_dates"] = ["2024-03-05"]

        slots = solver._generate_shift_slots(1, date(2024, 3, 4), date(2024, 3, 6), config)

        holiday_slots = [s for s in slots if s.shift_date == date(2024, 3, 5)]
        non_holiday_slots = [s for s in slots if s.shift_date == date(2024, 3, 4)]

        assert all(s.is_holiday for s in holiday_slots)
        assert not any(s.is_holiday for s in non_holiday_slots)

    def test_desirable_shift_marking(self, solver):
        """Test that desirable shifts are correctly identified based on config type string."""
        config = solver._default_config()
        config["desirable_shifts"] = ["opening"]

        slots = solver._generate_shift_slots(1, date(2024, 3, 4), date(2024, 3, 4), config)

        # Verify desirable marking: the shift_type string "opening" in config
        # determines is_desirable, regardless of the FairnessShiftType enum mapping
        desirable = [s for s in slots if s.is_desirable]
        not_desirable = [s for s in slots if not s.is_desirable]

        # Exactly one shift type is "opening" in the default config
        assert len(desirable) >= 1
        assert len(not_desirable) >= 1


class TestHardConstraints:
    """Tests for hard constraint enforcement."""

    def test_max_hours_prevents_assignment(self, solver, default_staff, default_slot):
        """Staff at max hours should not be assigned more shifts."""
        # Staff already at 38 hours, 5 more would exceed 40
        staff_hours = {1: 38.0}
        staff_days = {1: set()}
        staff_last_shift = {1: None}
        staff_weekend_count = {1: 0}

        result = solver._check_hard_constraints(
            default_staff, default_slot, staff_hours, staff_days,
            staff_last_shift, staff_weekend_count, [], {},
        )
        assert result is False

    def test_consecutive_days_limit(self, solver, default_staff, default_slot):
        """Staff at max consecutive days should not get another day."""
        # 5 consecutive days already
        staff_days = {1: {
            date(2024, 3, 3), date(2024, 3, 4), date(2024, 3, 5),
            date(2024, 3, 6), date(2024, 3, 7),
        }}
        staff_hours = {1: 25.0}
        staff_last_shift = {1: (date(2024, 3, 7), time(17, 0))}
        staff_weekend_count = {1: 0}

        result = solver._check_hard_constraints(
            default_staff, default_slot, staff_hours, staff_days,
            staff_last_shift, staff_weekend_count, [], {},
        )
        assert result is False

    def test_clopening_prevention(self, solver, default_staff):
        """Closing-then-opening with <10hr gap should be blocked."""
        # Morning shift after a late night
        slot = ShiftSlot(
            slot_id=1, branch_id=1, shift_date=date(2024, 3, 8),
            shift_type=FairnessShiftType.OPENING, start_time=time(7, 0),
            end_time=time(12, 0), hours=5.0, is_weekend=False, is_holiday=False,
        )

        # Last shift ended at 22:00 previous day -> 9 hour gap < 10
        staff_days = {1: {date(2024, 3, 7)}}
        staff_hours = {1: 8.0}
        staff_last_shift = {1: (date(2024, 3, 7), time(22, 0))}
        staff_weekend_count = {1: 0}

        result = solver._check_hard_constraints(
            default_staff, slot, staff_hours, staff_days,
            staff_last_shift, staff_weekend_count, [], {},
        )
        assert result is False

    def test_unavailability_blocks_assignment(self, solver, default_staff):
        """Staff marked unavailable should not be assigned."""
        slot = ShiftSlot(
            slot_id=1, branch_id=1, shift_date=date(2024, 3, 9),  # Saturday
            shift_type=FairnessShiftType.MIDDAY, start_time=time(10, 0),
            end_time=time(15, 0), hours=5.0, is_weekend=True, is_holiday=False,
        )

        availability = {1: [StaffAvailability(
            staff_id=1, day_of_week="saturday", shift_type=None,
            preference=PreferenceType.UNAVAILABLE,
        )]}

        staff_hours = {1: 0.0}
        staff_days = {1: set()}
        staff_last_shift = {1: None}
        staff_weekend_count = {1: 0}

        result = solver._check_hard_constraints(
            default_staff, slot, staff_hours, staff_days,
            staff_last_shift, staff_weekend_count, [], availability,
        )
        assert result is False

    def test_skill_requirement_blocks_unqualified(self, solver):
        """Staff without required skills should not be assigned."""
        staff = StaffMember(
            staff_id=1, name="Test", employment_type=EmploymentType.FULL_TIME,
            skills=["cash_register"],  # Missing opening_procedures
            min_hours=35, max_hours=40, contracted_hours=40,
            seniority_level=1, max_consecutive_days=5,
            min_hours_between_shifts=10, max_weekend_shifts_per_month=4,
            max_closing_shifts_per_week=3, desirable_shift_score=50,
        )
        slot = ShiftSlot(
            slot_id=1, branch_id=1, shift_date=date(2024, 3, 8),
            shift_type=FairnessShiftType.OPENING, start_time=time(8, 0),
            end_time=time(13, 0), hours=5.0, is_weekend=False, is_holiday=False,
            required_skills=["opening_procedures", "alarm_codes"],
        )

        staff_hours = {1: 0.0}
        staff_days = {1: set()}
        staff_last_shift = {1: None}
        staff_weekend_count = {1: 0}

        result = solver._check_hard_constraints(
            staff, slot, staff_hours, staff_days,
            staff_last_shift, staff_weekend_count, [], {},
        )
        assert result is False

    def test_valid_assignment_passes_constraints(self, solver, default_staff, default_slot):
        """A valid assignment should pass all hard constraints."""
        staff_hours = {1: 20.0}
        staff_days = {1: {date(2024, 3, 6), date(2024, 3, 7)}}
        staff_last_shift = {1: (date(2024, 3, 7), time(15, 0))}
        staff_weekend_count = {1: 1}

        result = solver._check_hard_constraints(
            default_staff, default_slot, staff_hours, staff_days,
            staff_last_shift, staff_weekend_count, [], {},
        )
        assert result is True


class TestScoringFunctions:
    """Tests for soft constraint scoring."""

    def test_preference_score_preferred(self, solver, default_staff):
        """Preferred shifts should get high score."""
        slot = ShiftSlot(
            slot_id=1, branch_id=1, shift_date=date(2024, 3, 4),
            shift_type=FairnessShiftType.OPENING, start_time=time(8, 0),
            end_time=time(13, 0), hours=5.0, is_weekend=False, is_holiday=False,
        )

        avail = [StaffAvailability(
            staff_id=1, day_of_week=None, shift_type=FairnessShiftType.OPENING,
            preference=PreferenceType.PREFERRED,
        )]

        score = solver._compute_preference_score(default_staff, slot, avail)
        assert score == 1.0

    def test_preference_score_no_preference(self, solver, default_staff, default_slot):
        """No preference should give neutral score."""
        score = solver._compute_preference_score(default_staff, default_slot, [])
        assert score == 0.5

    def test_fatigue_score_rested_staff(self, solver, default_staff, default_slot):
        """Well-rested staff should have high fatigue score (good)."""
        staff_hours = {1: 0.0}
        staff_days = {1: set()}
        staff_last_shift = {1: None}

        score = solver._compute_fatigue_score(
            default_staff, default_slot, staff_hours, staff_days, staff_last_shift
        )
        assert score >= 0.9  # Should be near perfect (rested)

    def test_fatigue_score_tired_staff(self, solver, default_staff, default_slot):
        """Heavily worked staff should have low fatigue score (bad)."""
        staff_hours = {1: 38.0}  # Near max
        staff_days = {1: {
            date(2024, 3, 4), date(2024, 3, 5), date(2024, 3, 6),
            date(2024, 3, 7),
        }}
        staff_last_shift = {1: (date(2024, 3, 7), time(21, 0))}

        score = solver._compute_fatigue_score(
            default_staff, default_slot, staff_hours, staff_days, staff_last_shift
        )
        assert score < 0.4  # Should be low (tired)

    def test_coverage_score_full_skill_match(self, solver):
        """Full skill match should get high coverage score."""
        staff = StaffMember(
            staff_id=1, name="Test", employment_type=EmploymentType.FULL_TIME,
            skills=["cash_register", "opening_procedures"],
            min_hours=35, max_hours=40, contracted_hours=40,
            seniority_level=1, max_consecutive_days=5,
            min_hours_between_shifts=10, max_weekend_shifts_per_month=4,
            max_closing_shifts_per_week=3, desirable_shift_score=50,
        )
        slot = ShiftSlot(
            slot_id=1, branch_id=1, shift_date=date(2024, 3, 8),
            shift_type=FairnessShiftType.OPENING, start_time=time(8, 0),
            end_time=time(13, 0), hours=5.0, is_weekend=False, is_holiday=False,
            required_skills=["cash_register", "opening_procedures"],
        )

        score = solver._compute_coverage_score(staff, slot)
        assert score == 1.0

    def test_coverage_score_no_skills_required(self, solver, default_staff, default_slot):
        """Slots with no skill requirements should give decent score."""
        score = solver._compute_coverage_score(default_staff, default_slot)
        assert score == 0.7


class TestFairnessCalculation:
    """Tests for overall fairness score calculation."""

    def test_equal_distribution_high_fairness(self, solver):
        """Equal distribution should produce high fairness score."""
        staff = [
            StaffMember(
                staff_id=i, name=f"S{i}", employment_type=EmploymentType.FULL_TIME,
                skills=[], min_hours=35, max_hours=40, contracted_hours=40,
                seniority_level=1, max_consecutive_days=5,
                min_hours_between_shifts=10, max_weekend_shifts_per_month=4,
                max_closing_shifts_per_week=3, desirable_shift_score=50,
            ) for i in range(4)
        ]

        # Equal hours and distributions
        staff_hours = {0: 35.0, 1: 35.0, 2: 35.0, 3: 35.0}
        staff_weekend_count = {0: 2, 1: 2, 2: 2, 3: 2}
        staff_desirable_count = {0: 3, 1: 3, 2: 3, 3: 3}

        score = solver._calculate_overall_fairness(
            staff, staff_hours, staff_weekend_count, staff_desirable_count
        )
        assert score >= 90.0

    def test_unequal_distribution_low_fairness(self, solver):
        """Unequal distribution should produce lower fairness score."""
        staff = [
            StaffMember(
                staff_id=i, name=f"S{i}", employment_type=EmploymentType.FULL_TIME,
                skills=[], min_hours=35, max_hours=40, contracted_hours=40,
                seniority_level=1, max_consecutive_days=5,
                min_hours_between_shifts=10, max_weekend_shifts_per_month=4,
                max_closing_shifts_per_week=3, desirable_shift_score=50,
            ) for i in range(4)
        ]

        # Very unequal distribution
        staff_hours = {0: 40.0, 1: 40.0, 2: 10.0, 3: 10.0}
        staff_weekend_count = {0: 0, 1: 0, 2: 8, 3: 8}
        staff_desirable_count = {0: 10, 1: 10, 2: 0, 3: 0}

        score = solver._calculate_overall_fairness(
            staff, staff_hours, staff_weekend_count, staff_desirable_count
        )
        assert score < 80.0


class TestExplanationGeneration:
    """Tests for schedule explanation/transparency features."""

    def test_explanation_type_determination(self, solver):
        """Test that dominant factor determines explanation type."""
        factors = [
            {"factor": "preference_match", "weight": 0.25, "score": 1.0, "detail": "Preferred"},
            {"factor": "fairness_balance", "weight": 0.35, "score": 0.3, "detail": "Below avg"},
            {"factor": "skill_coverage", "weight": 0.25, "score": 0.5, "detail": "Match"},
            {"factor": "fatigue_prevention", "weight": 0.15, "score": 0.8, "detail": "Rested"},
        ]

        explanation_type = solver._determine_explanation_type(factors)
        # preference_match has highest weighted score (0.25 * 1.0 = 0.25)
        assert explanation_type == ScheduleExplanationType.PREFERENCE_HONORED

    def test_explanation_text_includes_reasons(self, solver, default_staff):
        """Test that explanation text includes top contributing factors."""
        slot = ShiftSlot(
            slot_id=1, branch_id=1, shift_date=date(2024, 3, 8),
            shift_type=FairnessShiftType.OPENING, start_time=time(8, 0),
            end_time=time(13, 0), hours=5.0, is_weekend=False, is_holiday=False,
        )

        factors = [
            {"factor": "preference_match", "weight": 0.25, "score": 1.0, "detail": "Preferred morning shifts"},
            {"factor": "fairness_balance", "weight": 0.35, "score": 0.9, "detail": "Below avg hours"},
            {"factor": "skill_coverage", "weight": 0.25, "score": 0.8, "detail": "Skills: cash register"},
            {"factor": "fatigue_prevention", "weight": 0.15, "score": 0.9, "detail": "Well rested"},
        ]

        text = solver._build_explanation_text(default_staff, slot, factors, 0.85)
        assert "Preferred morning shifts" in text
        assert "score" in text


class TestUtilityMethods:
    """Tests for solver utility methods."""

    def test_times_overlap_true(self, solver):
        assert solver._times_overlap(time(9, 0), time(13, 0), time(12, 0), time(17, 0)) is True

    def test_times_overlap_false(self, solver):
        assert solver._times_overlap(time(9, 0), time(12, 0), time(14, 0), time(17, 0)) is False

    def test_times_overlap_adjacent(self, solver):
        assert solver._times_overlap(time(9, 0), time(13, 0), time(13, 0), time(17, 0)) is False

    def test_consecutive_days_count(self, solver):
        days = {date(2024, 3, 4), date(2024, 3, 5), date(2024, 3, 6)}
        assert solver._count_consecutive_days(days, date(2024, 3, 7)) == 3

    def test_consecutive_days_gap(self, solver):
        days = {date(2024, 3, 4), date(2024, 3, 5), date(2024, 3, 7)}  # Gap on 6th
        assert solver._count_consecutive_days(days, date(2024, 3, 8)) == 1

    def test_availability_matches_slot_day(self, solver):
        avail = StaffAvailability(
            staff_id=1, day_of_week="monday", shift_type=None,
            preference=PreferenceType.PREFERRED,
        )
        slot = ShiftSlot(
            slot_id=1, branch_id=1, shift_date=date(2024, 3, 4),  # Monday
            shift_type=FairnessShiftType.MIDDAY, start_time=time(10, 0),
            end_time=time(15, 0), hours=5.0, is_weekend=False, is_holiday=False,
        )
        assert solver._availability_matches_slot(avail, slot) is True

    def test_availability_mismatch_day(self, solver):
        avail = StaffAvailability(
            staff_id=1, day_of_week="tuesday", shift_type=None,
            preference=PreferenceType.PREFERRED,
        )
        slot = ShiftSlot(
            slot_id=1, branch_id=1, shift_date=date(2024, 3, 4),  # Monday
            shift_type=FairnessShiftType.MIDDAY, start_time=time(10, 0),
            end_time=time(15, 0), hours=5.0, is_weekend=False, is_holiday=False,
        )
        assert solver._availability_matches_slot(avail, slot) is False

    def test_availability_matches_shift_type(self, solver):
        avail = StaffAvailability(
            staff_id=1, day_of_week=None, shift_type=FairnessShiftType.OPENING,
            preference=PreferenceType.PREFERRED,
        )
        opening_slot = ShiftSlot(
            slot_id=1, branch_id=1, shift_date=date(2024, 3, 4),
            shift_type=FairnessShiftType.OPENING, start_time=time(8, 0),
            end_time=time(13, 0), hours=5.0, is_weekend=False, is_holiday=False,
        )
        closing_slot = ShiftSlot(
            slot_id=2, branch_id=1, shift_date=date(2024, 3, 4),
            shift_type=FairnessShiftType.CLOSING, start_time=time(14, 0),
            end_time=time(20, 0), hours=6.0, is_weekend=False, is_holiday=False,
        )
        assert solver._availability_matches_slot(avail, opening_slot) is True
        assert solver._availability_matches_slot(avail, closing_slot) is False

    def test_empty_staff_has_perfect_fairness(self, solver):
        """Empty staff list should return 100% fairness."""
        score = solver._calculate_overall_fairness([], {}, {}, {})
        assert score == 100.0
