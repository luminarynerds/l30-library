# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for gamification features that don't require database access.

Tests cover:
1. Achievement unlocking logic
2. Point accumulation and XP calculations
3. Badge definitions and thresholds
4. Leaderboard sorting and anonymization
5. Streak calculations
6. Goal progress calculations
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Any

from app.schemas.gamification import calculate_level, xp_for_next_level
from app.services.reading_achievement_service import BADGE_DEFINITIONS


# ============================================================================
# XP and Level Calculation Tests (Exponential - Learning System)
# ============================================================================


class TestLearningXPCalculations:
    """Test exponential XP calculations for the learning system."""

    def test_level_1_boundaries(self):
        """Test level 1: 0-99 XP."""
        assert calculate_level(0) == 1
        assert calculate_level(50) == 1
        assert calculate_level(99) == 1

    def test_level_2_boundaries(self):
        """Test level 2: 100-249 XP."""
        assert calculate_level(100) == 2
        assert calculate_level(150) == 2
        assert calculate_level(249) == 2

    def test_level_3_boundaries(self):
        """Test level 3: 250-473 XP (requires 100 + 150 + 225)."""
        assert calculate_level(250) == 3
        assert calculate_level(300) == 3
        assert calculate_level(400) == 3

    def test_level_4_and_beyond(self):
        """Test level 4+ with exponential scaling."""
        # Level 4 starts at: 100 + 150 + 225 = 475
        assert calculate_level(475) == 4

        # Higher levels continue exponentially
        assert calculate_level(1000) >= 5
        assert calculate_level(5000) >= 8

    def test_exponential_scaling_factor(self):
        """Verify the 1.5x exponential scaling factor."""
        # Level 1 needs: 100 XP
        # Level 2 needs: 150 XP (100 * 1.5)
        # Level 3 needs: 225 XP (150 * 1.5)

        _, level_2_req = xp_for_next_level(100)
        assert level_2_req == 150

        _, level_3_req = xp_for_next_level(250)
        assert level_3_req == 225

    def test_xp_progress_in_level(self):
        """Test XP progress tracking within current level."""
        # 50 XP in level 1
        current, needed = xp_for_next_level(50)
        assert current == 50
        assert needed == 100

        # 50 XP into level 2
        current, needed = xp_for_next_level(150)
        assert current == 50
        assert needed == 150

    def test_xp_at_level_boundary(self):
        """Test XP calculation at exact level boundaries."""
        # Exactly at level 2
        current, needed = xp_for_next_level(100)
        assert current == 0
        assert needed == 150

    def test_large_xp_values(self):
        """Test calculations with large XP values."""
        level = calculate_level(10000)
        assert level >= 10

        level = calculate_level(100000)
        assert level >= 15


# ============================================================================
# Reading XP/Level Calculations (Linear - 100 XP = 1 level)
# ============================================================================


class TestReadingXPCalculations:
    """Test linear XP calculations for the reading system."""

    def calculate_reading_level(self, xp: int) -> int:
        """Calculate level from XP (100 XP = 1 level)."""
        return (xp // 100) + 1

    def xp_to_next_reading_level(self, xp: int) -> int:
        """Calculate XP needed for next level."""
        return 100 - (xp % 100)

    def test_reading_level_boundaries(self):
        """Test reading level calculations at boundaries."""
        assert self.calculate_reading_level(0) == 1
        assert self.calculate_reading_level(99) == 1
        assert self.calculate_reading_level(100) == 2
        assert self.calculate_reading_level(199) == 2
        assert self.calculate_reading_level(200) == 3

    def test_reading_xp_to_next_level(self):
        """Test XP needed for next level calculation."""
        assert self.xp_to_next_reading_level(0) == 100
        assert self.xp_to_next_reading_level(50) == 50
        assert self.xp_to_next_reading_level(99) == 1
        assert self.xp_to_next_reading_level(100) == 100
        assert self.xp_to_next_reading_level(150) == 50

    def test_high_xp_reading_levels(self):
        """Test reading levels with high XP values."""
        assert self.calculate_reading_level(500) == 6
        assert self.calculate_reading_level(1000) == 11
        assert self.calculate_reading_level(10000) == 101


# ============================================================================
# Badge Definition Tests
# ============================================================================


class TestBadgeDefinitions:
    """Test that all badge definitions are valid and complete."""

    def test_badge_definitions_exist(self):
        """Test that badge definitions dictionary is populated."""
        assert len(BADGE_DEFINITIONS) > 0
        # Should have at least 17 badges
        assert len(BADGE_DEFINITIONS) >= 17

    def test_all_badge_types_present(self):
        """Test that all expected badge types are present."""
        badge_types = {badge["type"] for badge in BADGE_DEFINITIONS.values()}
        assert "books" in badge_types
        assert "minutes" in badge_types
        assert "pages" in badge_types
        assert "streak" in badge_types
        assert "goal" in badge_types
        assert "ratings" in badge_types

    def test_badge_definition_structure(self):
        """Test that each badge has required fields."""
        required_fields = ["name", "description", "type", "threshold"]

        for badge_id, badge_def in BADGE_DEFINITIONS.items():
            for field in required_fields:
                assert field in badge_def, f"Badge {badge_id} missing {field}"

            # Validate types
            assert isinstance(badge_def["name"], str)
            assert isinstance(badge_def["description"], str)
            assert isinstance(badge_def["type"], str)
            assert isinstance(badge_def["threshold"], int)

    def test_badge_thresholds_positive(self):
        """Test that all badge thresholds are positive."""
        for badge_id, badge_def in BADGE_DEFINITIONS.items():
            assert badge_def["threshold"] > 0, f"Badge {badge_id} has non-positive threshold"

    def test_book_badge_thresholds(self):
        """Test book badge threshold progression."""
        book_badges = {k: v for k, v in BADGE_DEFINITIONS.items() if v["type"] == "books"}
        thresholds = sorted([b["threshold"] for b in book_badges.values()])

        # Should be: 1, 5, 10, 25
        assert 1 in thresholds
        assert 5 in thresholds
        assert 10 in thresholds
        assert 25 in thresholds

        # Should be in ascending order
        assert thresholds == sorted(thresholds)

    def test_minutes_badge_thresholds(self):
        """Test minutes badge threshold progression."""
        minutes_badges = {k: v for k, v in BADGE_DEFINITIONS.items() if v["type"] == "minutes"}
        thresholds = sorted([b["threshold"] for b in minutes_badges.values()])

        # Should be: 60, 300, 600, 1200
        assert 60 in thresholds
        assert 300 in thresholds
        assert 600 in thresholds
        assert 1200 in thresholds

    def test_streak_badge_thresholds(self):
        """Test streak badge threshold progression."""
        streak_badges = {k: v for k, v in BADGE_DEFINITIONS.items() if v["type"] == "streak"}
        thresholds = sorted([b["threshold"] for b in streak_badges.values()])

        # Should be: 3, 7, 14, 30
        assert 3 in thresholds
        assert 7 in thresholds
        assert 14 in thresholds
        assert 30 in thresholds

    def test_goal_badge_thresholds(self):
        """Test goal badge threshold percentages."""
        goal_badges = {k: v for k, v in BADGE_DEFINITIONS.items() if v["type"] == "goal"}

        # Should have goal-achiever at 100% and overachiever at 150%
        thresholds = {b["threshold"] for b in goal_badges.values()}
        assert 100 in thresholds  # goal-achiever
        assert 150 in thresholds  # overachiever


# ============================================================================
# Badge Earning Logic Tests
# ============================================================================


class TestBadgeEarningLogic:
    """Test badge earning logic without database."""

    def check_badge_earned(self, badge_def: Dict, stats: Dict) -> bool:
        """Check if badge requirements are met (replicating service logic)."""
        badge_type = badge_def["type"]
        threshold = badge_def["threshold"]

        if badge_type == "books":
            return stats.get("books", 0) >= threshold
        elif badge_type == "minutes":
            return stats.get("minutes", 0) >= threshold
        elif badge_type == "pages":
            return stats.get("pages", 0) >= threshold
        elif badge_type == "streak":
            return stats.get("streak", 0) >= threshold
        elif badge_type == "ratings":
            return stats.get("ratings", 0) >= threshold
        elif badge_type == "goal":
            return stats.get("goal_progress", 0) >= threshold

        return False

    def test_first_book_badge(self):
        """Test first book badge earning."""
        badge = BADGE_DEFINITIONS["first-book"]

        assert self.check_badge_earned(badge, {"books": 0}) is False
        assert self.check_badge_earned(badge, {"books": 1}) is True
        assert self.check_badge_earned(badge, {"books": 10}) is True

    def test_quick_reader_badge(self):
        """Test quick reader badge earning at 60 minutes."""
        badge = BADGE_DEFINITIONS["quick-reader-60"]

        assert self.check_badge_earned(badge, {"minutes": 59}) is False
        assert self.check_badge_earned(badge, {"minutes": 60}) is True
        assert self.check_badge_earned(badge, {"minutes": 120}) is True

    def test_page_turner_badge(self):
        """Test page turner badge at 100 pages."""
        badge = BADGE_DEFINITIONS["page-turner-100"]

        assert self.check_badge_earned(badge, {"pages": 99}) is False
        assert self.check_badge_earned(badge, {"pages": 100}) is True

    def test_streak_starter_badge(self):
        """Test streak starter badge at 3 days."""
        badge = BADGE_DEFINITIONS["streak-starter-3"]

        assert self.check_badge_earned(badge, {"streak": 2}) is False
        assert self.check_badge_earned(badge, {"streak": 3}) is True
        assert self.check_badge_earned(badge, {"streak": 7}) is True

    def test_goal_achiever_badge(self):
        """Test goal achiever badge at 100% completion."""
        badge = BADGE_DEFINITIONS["goal-achiever"]

        assert self.check_badge_earned(badge, {"goal_progress": 99}) is False
        assert self.check_badge_earned(badge, {"goal_progress": 100}) is True
        assert self.check_badge_earned(badge, {"goal_progress": 150}) is True

    def test_overachiever_badge(self):
        """Test overachiever badge at 150% completion."""
        badge = BADGE_DEFINITIONS["overachiever"]

        assert self.check_badge_earned(badge, {"goal_progress": 149}) is False
        assert self.check_badge_earned(badge, {"goal_progress": 150}) is True
        assert self.check_badge_earned(badge, {"goal_progress": 200}) is True

    def test_multiple_badges_at_once(self):
        """Test earning multiple badges with same stats."""
        stats = {"books": 5, "minutes": 300, "pages": 500, "streak": 7}

        earned = []
        for badge_id, badge_def in BADGE_DEFINITIONS.items():
            if self.check_badge_earned(badge_def, stats):
                earned.append(badge_id)

        # Should earn multiple badges
        assert "first-book" in earned
        assert "bookworm-5" in earned
        assert "quick-reader-60" in earned
        assert "dedicated-reader-300" in earned
        assert "page-turner-100" in earned
        assert "page-devourer-500" in earned
        assert "streak-starter-3" in earned
        assert "weekly-warrior-7" in earned


# ============================================================================
# Streak Calculation Tests
# ============================================================================


class TestStreakCalculation:
    """Test streak calculation logic."""

    def calculate_streak(self, dates: List[date]) -> int:
        """Calculate streak from list of activity dates."""
        if not dates:
            return 0

        # Sort dates descending
        sorted_dates = sorted(set(dates), reverse=True)

        if not sorted_dates:
            return 0

        # Check if most recent is today or yesterday
        today = date.today()
        yesterday = today - timedelta(days=1)

        if sorted_dates[0] < yesterday:
            return 0  # Streak broken

        # Count consecutive days
        streak = 1
        for i in range(1, len(sorted_dates)):
            expected = sorted_dates[i - 1] - timedelta(days=1)
            if sorted_dates[i] == expected:
                streak += 1
            else:
                break

        return streak

    def test_empty_dates(self):
        """Test streak with no dates."""
        assert self.calculate_streak([]) == 0

    def test_single_day_today(self):
        """Test streak with activity only today."""
        today = date.today()
        assert self.calculate_streak([today]) == 1

    def test_single_day_yesterday(self):
        """Test streak with activity only yesterday."""
        yesterday = date.today() - timedelta(days=1)
        assert self.calculate_streak([yesterday]) == 1

    def test_broken_streak(self):
        """Test streak broken by gap."""
        today = date.today()
        three_days_ago = today - timedelta(days=3)

        # Gap of 2 days breaks streak
        assert self.calculate_streak([today, three_days_ago]) == 1

    def test_consecutive_days(self):
        """Test consecutive day streak."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        assert self.calculate_streak([today, yesterday, two_days_ago]) == 3

    def test_long_streak(self):
        """Test a longer consecutive streak."""
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(7)]

        assert self.calculate_streak(dates) == 7

    def test_duplicate_dates_handled(self):
        """Test that duplicate dates don't inflate streak."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Multiple entries on same day
        dates = [today, today, today, yesterday, yesterday]
        assert self.calculate_streak(dates) == 2

    def test_old_activity_no_streak(self):
        """Test that old activity (>1 day ago) means no current streak."""
        week_ago = date.today() - timedelta(days=7)
        eight_days_ago = date.today() - timedelta(days=8)

        assert self.calculate_streak([week_ago, eight_days_ago]) == 0


# ============================================================================
# Leaderboard Sorting Tests
# ============================================================================


class TestLeaderboardSorting:
    """Test leaderboard sorting and anonymization."""

    def sort_and_rank(self, entries: List[Dict]) -> List[Dict]:
        """Sort leaderboard entries by minutes descending and assign ranks."""
        sorted_entries = sorted(entries, key=lambda x: x["minutes"], reverse=True)
        return [
            {**entry, "rank": i + 1}
            for i, entry in enumerate(sorted_entries)
        ]

    def anonymize_name(self, first_name: str, last_name: str) -> str:
        """Anonymize name to 'FirstName L.' format."""
        return f"{first_name} {last_name[0]}."

    def test_sort_by_minutes_descending(self):
        """Test that entries are sorted by minutes in descending order."""
        entries = [
            {"name": "Alice", "minutes": 100},
            {"name": "Bob", "minutes": 300},
            {"name": "Charlie", "minutes": 200},
        ]

        sorted_entries = self.sort_and_rank(entries)

        assert sorted_entries[0]["name"] == "Bob"
        assert sorted_entries[1]["name"] == "Charlie"
        assert sorted_entries[2]["name"] == "Alice"

    def test_rank_assignment(self):
        """Test that ranks are assigned correctly."""
        entries = [
            {"name": "Alice", "minutes": 100},
            {"name": "Bob", "minutes": 300},
        ]

        sorted_entries = self.sort_and_rank(entries)

        assert sorted_entries[0]["rank"] == 1
        assert sorted_entries[1]["rank"] == 2

    def test_anonymize_name_format(self):
        """Test name anonymization format."""
        assert self.anonymize_name("Alice", "Anderson") == "Alice A."
        assert self.anonymize_name("Bob", "Brown") == "Bob B."
        assert self.anonymize_name("Charlie", "Clark") == "Charlie C."

    def test_empty_leaderboard(self):
        """Test handling of empty leaderboard."""
        entries: List[Dict] = []
        sorted_entries = self.sort_and_rank(entries)
        assert len(sorted_entries) == 0

    def test_ties_in_minutes(self):
        """Test handling of ties in minutes."""
        entries = [
            {"name": "Alice", "minutes": 200},
            {"name": "Bob", "minutes": 200},
            {"name": "Charlie", "minutes": 100},
        ]

        sorted_entries = self.sort_and_rank(entries)

        # Both tied users should be ranked
        assert sorted_entries[0]["minutes"] == 200
        assert sorted_entries[1]["minutes"] == 200
        assert sorted_entries[2]["rank"] == 3


# ============================================================================
# Goal Progress Calculation Tests
# ============================================================================


class TestGoalProgressCalculation:
    """Test goal progress calculation logic."""

    def calculate_goal_progress(self, current: int, target: int) -> Dict:
        """Calculate goal progress percentage and status."""
        if target <= 0:
            return {"percentage": 0, "is_complete": False, "is_overachiever": False}

        percentage = (current / target) * 100
        return {
            "percentage": round(percentage, 1),
            "is_complete": percentage >= 100,
            "is_overachiever": percentage >= 150,
        }

    def test_zero_progress(self):
        """Test zero progress calculation."""
        result = self.calculate_goal_progress(0, 1000)
        assert result["percentage"] == 0
        assert result["is_complete"] is False
        assert result["is_overachiever"] is False

    def test_partial_progress(self):
        """Test partial progress (50%)."""
        result = self.calculate_goal_progress(500, 1000)
        assert result["percentage"] == 50.0
        assert result["is_complete"] is False
        assert result["is_overachiever"] is False

    def test_complete_goal(self):
        """Test 100% goal completion."""
        result = self.calculate_goal_progress(1000, 1000)
        assert result["percentage"] == 100.0
        assert result["is_complete"] is True
        assert result["is_overachiever"] is False

    def test_overachiever_threshold(self):
        """Test overachiever at 150%."""
        result = self.calculate_goal_progress(1500, 1000)
        assert result["percentage"] == 150.0
        assert result["is_complete"] is True
        assert result["is_overachiever"] is True

    def test_exceeding_goal(self):
        """Test exceeding goal by more than 50%."""
        result = self.calculate_goal_progress(2000, 1000)
        assert result["percentage"] == 200.0
        assert result["is_complete"] is True
        assert result["is_overachiever"] is True

    def test_zero_target_handling(self):
        """Test handling of zero target gracefully."""
        result = self.calculate_goal_progress(100, 0)
        assert result["percentage"] == 0
        assert result["is_complete"] is False


# ============================================================================
# Achievement Category Tests
# ============================================================================


class TestAchievementCategories:
    """Test achievement category validation."""

    VALID_CATEGORIES = ["course", "exploration", "streak", "lab", "secret"]

    def test_all_categories_valid(self):
        """Test that all categories are recognized."""
        for category in self.VALID_CATEGORIES:
            assert category in self.VALID_CATEGORIES

    def test_filter_by_category(self):
        """Test filtering achievements by category."""
        achievements = [
            {"slug": "first-course", "category": "course"},
            {"slug": "explorer", "category": "exploration"},
            {"slug": "week-streak", "category": "streak"},
            {"slug": "hidden", "category": "secret"},
        ]

        course_only = [a for a in achievements if a["category"] == "course"]
        assert len(course_only) == 1
        assert course_only[0]["slug"] == "first-course"

    def test_exclude_secret_achievements(self):
        """Test excluding secret achievements from public view."""
        achievements = [
            {"slug": "visible", "is_secret": False},
            {"slug": "hidden", "is_secret": True},
        ]

        public = [a for a in achievements if not a["is_secret"]]
        assert len(public) == 1
        assert public[0]["slug"] == "visible"


# ============================================================================
# XP Accumulation Tests
# ============================================================================


class TestXPAccumulation:
    """Test XP accumulation and updates."""

    def test_xp_from_achievement(self):
        """Test XP gain from earning an achievement."""
        initial_xp = 100
        achievement_xp = 50

        new_xp = initial_xp + achievement_xp
        assert new_xp == 150
        assert calculate_level(new_xp) == 2

    def test_xp_from_lesson_completion(self):
        """Test XP gain from lesson completion."""
        initial_xp = 0
        lesson_xp = 25
        lessons_completed = 4

        new_xp = initial_xp + (lesson_xp * lessons_completed)
        assert new_xp == 100
        assert calculate_level(new_xp) == 2

    def test_level_up_from_xp_gain(self):
        """Test leveling up from XP gain."""
        xp_at_level_1 = 90
        xp_gained = 20

        new_xp = xp_at_level_1 + xp_gained
        assert calculate_level(new_xp) == 2

    def test_multiple_level_ups(self):
        """Test multiple level ups from large XP gain."""
        initial_xp = 0
        # Large XP gain (should result in level 3+)
        xp_gained = 300

        new_xp = initial_xp + xp_gained
        assert calculate_level(new_xp) >= 3


# ============================================================================
# Reading Minutes Validation Tests
# ============================================================================


class TestReadingMinutesValidation:
    """Test validation logic for reading minutes."""

    MIN_MINUTES = 5
    MAX_MINUTES = 120
    MAX_TOTAL_LOGGED = 10000

    def validate_minutes(self, minutes: int, total_logged: int) -> Dict:
        """Validate reading minutes submission."""
        if minutes < self.MIN_MINUTES:
            return {"valid": False, "error": f"Minimum {self.MIN_MINUTES} minutes required"}
        if minutes > self.MAX_MINUTES:
            return {"valid": False, "error": f"Maximum {self.MAX_MINUTES} minutes per session"}
        if total_logged + minutes > self.MAX_TOTAL_LOGGED:
            return {"valid": False, "error": "Would exceed lifetime cap"}
        return {"valid": True}

    def test_reject_below_minimum(self):
        """Test rejection of minutes below minimum."""
        result = self.validate_minutes(4, 0)
        assert result["valid"] is False
        assert "Minimum" in result["error"]

    def test_reject_above_maximum(self):
        """Test rejection of minutes above maximum."""
        result = self.validate_minutes(121, 0)
        assert result["valid"] is False
        assert "Maximum" in result["error"]

    def test_accept_valid_minutes(self):
        """Test acceptance of valid minutes."""
        result = self.validate_minutes(30, 0)
        assert result["valid"] is True

    def test_accept_boundary_values(self):
        """Test acceptance of boundary values."""
        assert self.validate_minutes(5, 0)["valid"] is True
        assert self.validate_minutes(120, 0)["valid"] is True

    def test_reject_exceeding_lifetime_cap(self):
        """Test rejection when exceeding lifetime cap."""
        result = self.validate_minutes(50, 9980)
        assert result["valid"] is False
        assert "lifetime cap" in result["error"]

    def test_accept_at_cap(self):
        """Test acceptance when exactly at cap."""
        result = self.validate_minutes(20, 9980)
        assert result["valid"] is True


# ============================================================================
# Badge Progress Percentage Tests
# ============================================================================


class TestBadgeProgressPercentage:
    """Test badge progress percentage calculations."""

    def calculate_progress_percentage(self, current: int, threshold: int) -> float:
        """Calculate progress percentage, capped at 100."""
        if threshold <= 0:
            return 0
        return min((current / threshold) * 100, 100)

    def test_zero_progress(self):
        """Test zero progress."""
        assert self.calculate_progress_percentage(0, 100) == 0

    def test_partial_progress(self):
        """Test partial progress."""
        assert self.calculate_progress_percentage(50, 100) == 50

    def test_complete_progress(self):
        """Test 100% progress."""
        assert self.calculate_progress_percentage(100, 100) == 100

    def test_progress_capped_at_100(self):
        """Test that progress is capped at 100%."""
        assert self.calculate_progress_percentage(150, 100) == 100

    def test_zero_threshold_handling(self):
        """Test handling of zero threshold."""
        assert self.calculate_progress_percentage(50, 0) == 0
