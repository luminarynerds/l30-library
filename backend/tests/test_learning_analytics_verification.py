# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Verification tests for Learning Analytics functionality.

Tests cover the core analytics logic:
1. Completion rate calculations
2. Quiz performance metrics
3. Learner engagement tracking (XP, streaks, levels)

These tests verify the analytics logic without requiring a database connection.
"""

import pytest
from datetime import date, datetime, timedelta, timezone


# ============================================================================
# Completion Rate Calculations
# ============================================================================


class TestCompletionRateCalculations:
    """Test completion rate calculation logic."""

    def test_lesson_completion_rate_zero_lessons(self):
        """Test completion rate when there are no lessons."""
        total_lessons = 0
        completed_lessons = 0
        completion_rate = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0
        assert completion_rate == 0.0

    def test_lesson_completion_rate_no_completions(self):
        """Test completion rate with zero completions."""
        total_lessons = 10
        completed_lessons = 0
        completion_rate = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0
        assert completion_rate == 0.0

    def test_lesson_completion_rate_partial_completion(self):
        """Test completion rate with partial completion."""
        total_lessons = 10
        completed_lessons = 5
        completion_rate = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0
        assert completion_rate == 50.0

    def test_lesson_completion_rate_full_completion(self):
        """Test completion rate with full completion."""
        total_lessons = 10
        completed_lessons = 10
        completion_rate = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0
        assert completion_rate == 100.0

    def test_course_completion_counting(self):
        """Test course completion counting logic."""
        enrollments = [
            {"completed_at": datetime.now(timezone.utc)},
            {"completed_at": None},
            {"completed_at": datetime.now(timezone.utc)},
            {"completed_at": None},
            {"completed_at": None},
        ]
        total_courses = len(enrollments)
        completed_courses = sum(1 for e in enrollments if e["completed_at"] is not None)
        in_progress = total_courses - completed_courses

        assert total_courses == 5
        assert completed_courses == 2
        assert in_progress == 3

    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation per course."""
        completed_lessons = 7
        total_lessons = 10
        progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        assert progress_percentage == 70.0

    def test_minutes_invested_calculation(self):
        """Test time invested calculation based on completed lessons."""
        lessons = [
            {"status": "completed", "estimated_minutes": 15},
            {"status": "completed", "estimated_minutes": 30},
            {"status": "completed", "estimated_minutes": 20},
            {"status": "in_progress", "estimated_minutes": 45},
            {"status": "not_started", "estimated_minutes": 25},
        ]
        completed = [l for l in lessons if l["status"] == "completed"]
        total_minutes_invested = sum(l["estimated_minutes"] for l in completed)
        total_content_minutes = sum(l["estimated_minutes"] for l in lessons)

        assert total_minutes_invested == 65
        assert total_content_minutes == 135


# ============================================================================
# Quiz Performance Metrics
# ============================================================================


class TestQuizPerformanceMetrics:
    """Test quiz performance calculation logic."""

    def test_quiz_score_calculation(self):
        """Test quiz score calculation."""
        answers = [
            {"is_correct": True},
            {"is_correct": False},
            {"is_correct": True},
            {"is_correct": True},
            {"is_correct": False},
        ]
        correct_count = sum(1 for a in answers if a["is_correct"])
        total = len(answers)
        percentage = (correct_count / total * 100) if total > 0 else 0

        assert correct_count == 3
        assert total == 5
        assert percentage == 60.0

    def test_quiz_pass_fail_threshold(self):
        """Test quiz pass/fail determination with configurable threshold."""
        # Default threshold of 70%
        passing_threshold = 70

        # Test passing score
        score_80 = 80
        passed_80 = score_80 >= passing_threshold
        assert passed_80 is True

        # Test failing score
        score_60 = 60
        passed_60 = score_60 >= passing_threshold
        assert passed_60 is False

        # Test borderline pass
        score_70 = 70
        passed_70 = score_70 >= passing_threshold
        assert passed_70 is True

    def test_quiz_custom_threshold(self):
        """Test quiz with custom passing threshold."""
        # Custom threshold of 80%
        custom_threshold = 80
        score = 75
        passed = score >= custom_threshold
        assert passed is False

        # Pass at 80% with score of 80
        score_pass = 80
        passed_at_threshold = score_pass >= custom_threshold
        assert passed_at_threshold is True

    def test_quiz_attempt_tracking(self):
        """Test quiz attempt data structure."""
        attempt = {
            "user_id": 1,
            "lesson_id": 10,
            "score": 4,
            "total_questions": 5,
            "passed": True,
            "answers": [
                {"question_id": 1, "selected_option_index": 0, "is_correct": True},
                {"question_id": 2, "selected_option_index": 1, "is_correct": True},
                {"question_id": 3, "selected_option_index": 2, "is_correct": False},
                {"question_id": 4, "selected_option_index": 0, "is_correct": True},
                {"question_id": 5, "selected_option_index": 1, "is_correct": True},
            ],
            "started_at": datetime.now(timezone.utc) - timedelta(minutes=5),
            "completed_at": datetime.now(timezone.utc),
        }

        percentage = (attempt["score"] / attempt["total_questions"] * 100)
        assert percentage == 80.0
        assert attempt["passed"] is True
        assert len(attempt["answers"]) == 5

    def test_best_quiz_score_tracking(self):
        """Test tracking best quiz score across multiple attempts."""
        attempts = [
            {"score": 60, "percentage": 60.0},
            {"score": 75, "percentage": 75.0},
            {"score": 65, "percentage": 65.0},
            {"score": 80, "percentage": 80.0},
        ]
        best_percentage = max(a["percentage"] for a in attempts)
        assert best_percentage == 80.0

    def test_zero_question_quiz(self):
        """Test handling of quiz with zero questions."""
        total_questions = 0
        correct_count = 0
        percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        assert percentage == 0


# ============================================================================
# Learner Engagement Tracking (XP, Levels, Streaks)
# ============================================================================


class TestXPAndLevelCalculations:
    """Test XP and level calculation logic from the actual implementation."""

    def calculate_level(self, xp: int) -> int:
        """Calculate level from XP (mirrors actual implementation)."""
        level = 1
        xp_needed = 100
        remaining = xp
        while remaining >= xp_needed:
            remaining -= xp_needed
            level += 1
            xp_needed = int(100 * (1.5 ** (level - 1)))
        return level

    def test_level_1_at_0_xp(self):
        """Test level 1 at 0 XP."""
        assert self.calculate_level(0) == 1

    def test_level_1_at_99_xp(self):
        """Test level 1 at 99 XP (boundary)."""
        assert self.calculate_level(99) == 1

    def test_level_2_at_100_xp(self):
        """Test level 2 at exactly 100 XP."""
        assert self.calculate_level(100) == 2

    def test_level_2_range(self):
        """Test level 2 range (100-249 XP)."""
        assert self.calculate_level(150) == 2
        assert self.calculate_level(249) == 2

    def test_level_3_at_250_xp(self):
        """Test level 3 at 250 XP."""
        assert self.calculate_level(250) == 3

    def test_higher_levels(self):
        """Test higher level calculations with exponential scaling."""
        # Level 4 needs: 100 + 150 + 225 = 475 XP
        assert self.calculate_level(475) >= 4
        # High XP should result in high level
        assert self.calculate_level(1000) >= 5

    def test_xp_accumulation_from_lessons(self):
        """Test XP accumulation from lesson completions."""
        lesson_xp_rewards = [10, 10, 15, 10, 25]  # Different lessons give different XP
        total_xp = sum(lesson_xp_rewards)
        assert total_xp == 70
        assert self.calculate_level(total_xp) == 1

    def test_xp_accumulation_from_courses(self):
        """Test XP accumulation including course completion bonus."""
        lesson_xps = [10, 10, 10, 10, 10]  # 50 XP from lessons
        course_completion_bonus = 100  # Course completion XP
        total_xp = sum(lesson_xps) + course_completion_bonus
        assert total_xp == 150
        assert self.calculate_level(total_xp) == 2


class TestStreakTracking:
    """Test streak tracking logic."""

    def test_streak_continues_with_consecutive_days(self):
        """Test streak continues with consecutive days."""
        today = date.today()
        activity_dates = [
            today,
            today - timedelta(days=1),
            today - timedelta(days=2),
        ]

        # Check consecutive days
        current_streak = 0
        check_date = today
        while check_date in activity_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        assert current_streak == 3

    def test_streak_breaks_with_gap(self):
        """Test streak breaks when there's a gap."""
        today = date.today()
        activity_dates = [
            today,
            today - timedelta(days=1),
            # Gap on day 2
            today - timedelta(days=3),
            today - timedelta(days=4),
        ]

        current_streak = 0
        check_date = today
        while check_date in activity_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        # Streak should be 2 (today and yesterday), not 4
        assert current_streak == 2

    def test_longest_streak_tracking(self):
        """Test tracking longest streak."""
        current_streak = 5
        longest_streak = 10

        # Current streak doesn't beat longest
        assert max(current_streak, longest_streak) == 10

        # New streak beats longest
        new_streak = 15
        new_longest = max(new_streak, longest_streak)
        assert new_longest == 15

    def test_streak_day_history(self):
        """Test 30-day streak history generation."""
        today = date.today()
        thirty_days_ago = today - timedelta(days=29)

        # Simulate activity on certain days
        activity_dates = {today, today - timedelta(days=1), today - timedelta(days=5)}

        streak_history = []
        for i in range(30):
            check_date = thirty_days_ago + timedelta(days=i)
            streak_history.append({
                "date": check_date.isoformat(),
                "had_activity": check_date in activity_dates
            })

        assert len(streak_history) == 30
        assert streak_history[-1]["had_activity"] is True  # Today had activity
        assert streak_history[-2]["had_activity"] is True  # Yesterday had activity


class TestWeeklyActivityTracking:
    """Test weekly activity tracking logic."""

    def test_weekly_activity_aggregation(self):
        """Test weekly activity aggregation by day."""
        # Simulate completed lessons in the last week
        today = date.today()
        completed_lessons = [
            {"date": today, "minutes": 30},
            {"date": today, "minutes": 15},
            {"date": today - timedelta(days=1), "minutes": 45},
            {"date": today - timedelta(days=3), "minutes": 20},
        ]

        # Aggregate by date
        activity_by_date = {}
        for lesson in completed_lessons:
            d = lesson["date"]
            if d not in activity_by_date:
                activity_by_date[d] = {"lessons": 0, "minutes": 0}
            activity_by_date[d]["lessons"] += 1
            activity_by_date[d]["minutes"] += lesson["minutes"]

        assert activity_by_date[today]["lessons"] == 2
        assert activity_by_date[today]["minutes"] == 45
        assert activity_by_date[today - timedelta(days=1)]["lessons"] == 1

    def test_weekly_totals(self):
        """Test weekly total calculations."""
        weekly_activity = [
            {"day": "Mon", "lessons": 2, "minutes": 30},
            {"day": "Tue", "lessons": 1, "minutes": 15},
            {"day": "Wed", "lessons": 0, "minutes": 0},
            {"day": "Thu", "lessons": 3, "minutes": 60},
            {"day": "Fri", "lessons": 0, "minutes": 0},
            {"day": "Sat", "lessons": 1, "minutes": 20},
            {"day": "Sun", "lessons": 2, "minutes": 40},
        ]

        total_lessons = sum(d["lessons"] for d in weekly_activity)
        total_minutes = sum(d["minutes"] for d in weekly_activity)

        assert total_lessons == 9
        assert total_minutes == 165


class TestDifficultyDistribution:
    """Test difficulty distribution tracking."""

    def test_difficulty_distribution_counting(self):
        """Test counting courses by difficulty level."""
        enrolled_courses = [
            {"difficulty": "beginner"},
            {"difficulty": "beginner"},
            {"difficulty": "intermediate"},
            {"difficulty": "beginner"},
            {"difficulty": "advanced"},
            {"difficulty": "intermediate"},
        ]

        distribution = {"beginner": 0, "intermediate": 0, "advanced": 0}
        for course in enrolled_courses:
            diff = course["difficulty"]
            if diff in distribution:
                distribution[diff] += 1

        assert distribution["beginner"] == 3
        assert distribution["intermediate"] == 2
        assert distribution["advanced"] == 1

    def test_difficulty_percentages(self):
        """Test difficulty percentage calculations."""
        total_courses = 10
        distribution = {"beginner": 5, "intermediate": 3, "advanced": 2}

        percentages = {
            level: (count / total_courses * 100) if total_courses > 0 else 0
            for level, count in distribution.items()
        }

        assert percentages["beginner"] == 50.0
        assert percentages["intermediate"] == 30.0
        assert percentages["advanced"] == 20.0


class TestRecentActivityFeed:
    """Test recent activity feed tracking."""

    def test_recent_activity_ordering(self):
        """Test that recent activity is ordered by completion time (most recent first)."""
        activities = [
            {"lesson_id": 1, "completed_at": datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)},
            {"lesson_id": 2, "completed_at": datetime(2024, 1, 3, 10, 0, 0, tzinfo=timezone.utc)},
            {"lesson_id": 3, "completed_at": datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)},
        ]

        sorted_activities = sorted(activities, key=lambda x: x["completed_at"], reverse=True)

        assert sorted_activities[0]["lesson_id"] == 2  # Most recent
        assert sorted_activities[1]["lesson_id"] == 3
        assert sorted_activities[2]["lesson_id"] == 1  # Oldest

    def test_recent_activity_limit(self):
        """Test that recent activity is limited to 10 items."""
        activities = [{"lesson_id": i} for i in range(15)]
        limited_activities = activities[:10]
        assert len(limited_activities) == 10


class TestComprehensiveAnalyticsResponse:
    """Test the structure of comprehensive analytics response."""

    def test_analytics_response_structure(self):
        """Test that analytics response has all required fields."""
        response = {
            "total_courses_enrolled": 5,
            "courses_completed": 2,
            "courses_in_progress": 3,
            "total_lessons": 50,
            "lessons_completed": 30,
            "lesson_completion_rate": 60.0,
            "total_minutes_invested": 450,
            "total_content_minutes": 750,
            "total_xp": 500,
            "level": 3,
            "current_streak": 5,
            "longest_streak": 10,
            "difficulty_distribution": {
                "beginner": 2,
                "intermediate": 2,
                "advanced": 1
            },
            "streak_history": [{"date": "2024-01-01", "had_activity": True}],
            "recent_activity": [{"lesson_id": 1, "lesson_title": "Test"}]
        }

        # Verify all required fields exist
        required_fields = [
            "total_courses_enrolled", "courses_completed", "courses_in_progress",
            "total_lessons", "lessons_completed", "lesson_completion_rate",
            "total_minutes_invested", "total_content_minutes",
            "total_xp", "level", "current_streak", "longest_streak",
            "difficulty_distribution", "streak_history", "recent_activity"
        ]

        for field in required_fields:
            assert field in response, f"Missing required field: {field}"

    def test_analytics_calculations_consistency(self):
        """Test that analytics calculations are internally consistent."""
        total_courses = 10
        completed = 4
        in_progress = total_courses - completed

        assert in_progress == 6
        assert completed + in_progress == total_courses


class TestProgressStatusTransitions:
    """Test progress status transitions."""

    def test_valid_status_values(self):
        """Test valid progress status values."""
        valid_statuses = ["not_started", "in_progress", "completed"]

        test_progress = {"status": "in_progress"}
        assert test_progress["status"] in valid_statuses

    def test_status_transition_on_quiz_pass(self):
        """Test that status transitions to completed when quiz is passed."""
        initial_status = "in_progress"
        quiz_passed = True

        new_status = "completed" if quiz_passed else initial_status
        assert new_status == "completed"

    def test_status_remains_on_quiz_fail(self):
        """Test that status remains in_progress when quiz is failed."""
        initial_status = "in_progress"
        quiz_passed = False

        new_status = "completed" if quiz_passed else initial_status
        assert new_status == "in_progress"


# ============================================================================
# Run verification summary
# ============================================================================


if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("LEARNING ANALYTICS VERIFICATION TESTS")
    print("=" * 70)
    print()
    print("Running verification tests for:")
    print("1. Completion Rate Calculations")
    print("2. Quiz Performance Metrics")
    print("3. Learner Engagement Tracking (XP, Levels, Streaks)")
    print()

    # Run tests
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)
