# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.reading import (
    ReadingAchievement,
    ReadingLogEntry,
    ReadingProgram,
    ReadingRegistration,
)


# Badge definitions with requirements
BADGE_DEFINITIONS: Dict[str, Dict] = {
    # Book milestones
    "first-book": {
        "name": "First Page Turner",
        "description": "Completed your first book in this program!",
        "type": "books",
        "threshold": 1,
    },
    "bookworm-5": {
        "name": "Bookworm",
        "description": "Read 5 books - you're on a roll!",
        "type": "books",
        "threshold": 5,
    },
    "book-champion-10": {
        "name": "Book Champion",
        "description": "Read 10 books - incredible dedication!",
        "type": "books",
        "threshold": 10,
    },
    "literary-legend-25": {
        "name": "Literary Legend",
        "description": "Read 25 books - you're a reading superstar!",
        "type": "books",
        "threshold": 25,
    },
    # Minutes milestones
    "quick-reader-60": {
        "name": "Quick Reader",
        "description": "Logged your first hour of reading!",
        "type": "minutes",
        "threshold": 60,
    },
    "dedicated-reader-300": {
        "name": "Dedicated Reader",
        "description": "5 hours of reading logged - great progress!",
        "type": "minutes",
        "threshold": 300,
    },
    "reading-marathon-600": {
        "name": "Reading Marathon",
        "description": "10 hours of reading - marathon reader!",
        "type": "minutes",
        "threshold": 600,
    },
    "reading-master-1200": {
        "name": "Reading Expert",
        "description": "20 hours of reading - you're an expert!",
        "type": "minutes",
        "threshold": 1200,
    },
    # Pages milestones
    "page-turner-100": {
        "name": "Page Turner",
        "description": "Read 100 pages - great start!",
        "type": "pages",
        "threshold": 100,
    },
    "page-devourer-500": {
        "name": "Page Devourer",
        "description": "500 pages consumed - unstoppable!",
        "type": "pages",
        "threshold": 500,
    },
    "page-master-1000": {
        "name": "Page Expert",
        "description": "1000 pages read - legendary achievement!",
        "type": "pages",
        "threshold": 1000,
    },
    # Streak milestones
    "streak-starter-3": {
        "name": "Streak Starter",
        "description": "Logged reading 3 days in a row!",
        "type": "streak",
        "threshold": 3,
    },
    "weekly-warrior-7": {
        "name": "Weekly Warrior",
        "description": "7-day reading streak - incredible consistency!",
        "type": "streak",
        "threshold": 7,
    },
    "fortnight-focus-14": {
        "name": "Fortnight Focus",
        "description": "14-day reading streak - amazing dedication!",
        "type": "streak",
        "threshold": 14,
    },
    "monthly-marvel-30": {
        "name": "Monthly Marvel",
        "description": "30-day reading streak - you're a reading hero!",
        "type": "streak",
        "threshold": 30,
    },
    # Special achievements
    "goal-achiever": {
        "name": "Goal Achiever",
        "description": "Completed your reading goal for this program!",
        "type": "goal",
        "threshold": 100,  # 100% completion
    },
    "overachiever": {
        "name": "Overachiever",
        "description": "Exceeded your goal by 50%!",
        "type": "goal",
        "threshold": 150,
    },
    "reviewer-5": {
        "name": "Book Reviewer",
        "description": "Rated 5 books - thanks for sharing your thoughts!",
        "type": "ratings",
        "threshold": 5,
    },
}


class ReadingAchievementService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_award_achievements(
        self, user_id: int, program_id: int, registration_id: int
    ) -> List[ReadingAchievement]:
        # Get current stats
        stats = await self._get_user_stats(registration_id)

        # Get existing achievements
        existing = await self._get_existing_achievements(user_id, program_id)
        existing_ids = {a.badge_id for a in existing}

        # Get registration for goal checking
        reg_result = await self.db.execute(
            select(ReadingRegistration).where(ReadingRegistration.id == registration_id)
        )
        registration = reg_result.scalar_one_or_none()

        # Get program for goal type
        program_result = await self.db.execute(
            select(ReadingProgram).where(ReadingProgram.id == program_id)
        )
        program = program_result.scalar_one_or_none()

        new_achievements = []

        for badge_id, badge_def in BADGE_DEFINITIONS.items():
            # Skip if already earned
            if badge_id in existing_ids:
                continue

            # Check if badge requirements are met
            earned = self._check_badge_earned(
                badge_def, stats, registration, program
            )

            if earned:
                achievement = ReadingAchievement(
                    user_id=user_id,
                    program_id=program_id,
                    badge_id=badge_id,
                    badge_name=badge_def["name"],
                    badge_description=badge_def["description"],
                )
                self.db.add(achievement)
                new_achievements.append(achievement)

        if new_achievements:
            await self.db.commit()
            for ach in new_achievements:
                await self.db.refresh(ach)

        return new_achievements

    async def _get_user_stats(self, registration_id: int) -> Dict:
        # Get log entries
        entries_result = await self.db.execute(
            select(ReadingLogEntry).where(
                ReadingLogEntry.registration_id == registration_id
            )
        )
        entries = entries_result.scalars().all()

        # Calculate stats
        total_books = sum(e.books_read for e in entries)
        total_minutes = sum(e.minutes_read for e in entries)
        total_pages = sum(e.pages_read for e in entries)
        ratings_count = sum(1 for e in entries if e.rating is not None)

        # Calculate streak
        streak = self._calculate_streak(entries)

        return {
            "books": total_books,
            "minutes": total_minutes,
            "pages": total_pages,
            "streak": streak,
            "ratings": ratings_count,
            "entries": len(entries),
        }

    def _calculate_streak(self, entries: List[ReadingLogEntry]) -> int:
        if not entries:
            return 0

        # Get unique dates, sorted descending
        dates = sorted(
            set(e.logged_at.date() for e in entries),
            reverse=True
        )

        if not dates:
            return 0

        # Check if most recent is today or yesterday
        today = date.today()
        if dates[0] < today - timedelta(days=1):
            return 0  # Streak broken

        # Count consecutive days
        streak = 1
        for i in range(1, len(dates)):
            expected = dates[i - 1] - timedelta(days=1)
            if dates[i] == expected:
                streak += 1
            else:
                break

        return streak

    async def _get_existing_achievements(
        self, user_id: int, program_id: int
    ) -> List[ReadingAchievement]:
        result = await self.db.execute(
            select(ReadingAchievement).where(
                and_(
                    ReadingAchievement.user_id == user_id,
                    ReadingAchievement.program_id == program_id,
                )
            )
        )
        return list(result.scalars().all())

    def _check_badge_earned(
        self,
        badge_def: Dict,
        stats: Dict,
        registration: Optional[ReadingRegistration],
        program: Optional[ReadingProgram],
    ) -> bool:
        badge_type = badge_def["type"]
        threshold = badge_def["threshold"]

        if badge_type == "books":
            return stats["books"] >= threshold
        elif badge_type == "minutes":
            return stats["minutes"] >= threshold
        elif badge_type == "pages":
            return stats["pages"] >= threshold
        elif badge_type == "streak":
            return stats["streak"] >= threshold
        elif badge_type == "ratings":
            return stats["ratings"] >= threshold
        elif badge_type == "goal":
            # Check goal completion percentage
            if not registration or not registration.goal_target or not program:
                return False

            goal_target = registration.goal_target
            goal_type = program.reading_goal_type

            if goal_type == "minutes":
                progress = (stats["minutes"] / goal_target) * 100
            elif goal_type == "books":
                progress = (stats["books"] / goal_target) * 100
            elif goal_type == "pages":
                progress = (stats["pages"] / goal_target) * 100
            else:
                return False

            return progress >= threshold

        return False

    async def get_available_badges(self, program_id: int) -> List[Dict]:
        return [
            {
                "badge_id": badge_id,
                "name": badge_def["name"],
                "description": badge_def["description"],
                "type": badge_def["type"],
                "threshold": badge_def["threshold"],
            }
            for badge_id, badge_def in BADGE_DEFINITIONS.items()
        ]

    async def get_user_achievement_progress(
        self, user_id: int, program_id: int, registration_id: int
    ) -> List[Dict]:
        stats = await self._get_user_stats(registration_id)
        existing = await self._get_existing_achievements(user_id, program_id)
        existing_ids = {a.badge_id for a in existing}

        # Get registration for goal checking
        reg_result = await self.db.execute(
            select(ReadingRegistration).where(ReadingRegistration.id == registration_id)
        )
        registration = reg_result.scalar_one_or_none()

        # Get program for goal type
        program = None
        if registration:
            program_result = await self.db.execute(
                select(ReadingProgram).where(ReadingProgram.id == registration.program_id)
            )
            program = program_result.scalar_one_or_none()

        # Calculate goal progress percentage for goal badges
        goal_progress = 0
        if registration and registration.goal_target and registration.goal_target > 0 and program:
            if program.reading_goal_type == "minutes":
                goal_progress = (stats["minutes"] / registration.goal_target) * 100
            elif program.reading_goal_type == "books":
                goal_progress = (stats["books"] / registration.goal_target) * 100
            elif program.reading_goal_type == "pages":
                goal_progress = (stats["pages"] / registration.goal_target) * 100

        progress_list = []
        for badge_id, badge_def in BADGE_DEFINITIONS.items():
            badge_type = badge_def["type"]
            threshold = badge_def["threshold"]

            # Calculate current value
            if badge_type == "books":
                current = stats["books"]
            elif badge_type == "minutes":
                current = stats["minutes"]
            elif badge_type == "pages":
                current = stats["pages"]
            elif badge_type == "streak":
                current = stats["streak"]
            elif badge_type == "ratings":
                current = stats["ratings"]
            elif badge_type == "goal":
                # Goal badges use progress percentage as current value
                current = round(goal_progress, 1)
            else:
                current = 0

            progress_list.append({
                "badge_id": badge_id,
                "name": badge_def["name"],
                "description": badge_def["description"],
                "type": badge_type,
                "threshold": threshold,
                "current": current,
                "progress_percentage": min((current / threshold) * 100, 100) if threshold > 0 else 0,
                "earned": badge_id in existing_ids,
                "earned_at": next(
                    (a.unlocked_at for a in existing if a.badge_id == badge_id),
                    None
                ),
            })

        return progress_list
