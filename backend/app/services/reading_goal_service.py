# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.reading_goal import ReadingGoal
from ..models.reading_status import ReadingStatus, ShelfStatus


class ReadingGoalService:

    @staticmethod
    async def get_goals(db: AsyncSession, user_id: int) -> list[ReadingGoal]:
        result = await db.execute(
            select(ReadingGoal)
            .where(ReadingGoal.user_id == user_id)
            .order_by(ReadingGoal.year.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def set_goal(
        db: AsyncSession, user_id: int, year: int, target_books: int
    ) -> ReadingGoal:
        result = await db.execute(
            select(ReadingGoal).where(
                ReadingGoal.user_id == user_id,
                ReadingGoal.year == year,
            )
        )
        goal = result.scalar_one_or_none()

        if goal:
            goal.target_books = target_books
        else:
            goal = ReadingGoal(
                user_id=user_id,
                year=year,
                target_books=target_books,
            )
            db.add(goal)

        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def remove_goal(db: AsyncSession, user_id: int, year: int) -> bool:
        result = await db.execute(
            select(ReadingGoal).where(
                ReadingGoal.user_id == user_id,
                ReadingGoal.year == year,
            )
        )
        goal = result.scalar_one_or_none()
        if not goal:
            return False
        await db.delete(goal)
        await db.commit()
        return True

    @staticmethod
    async def get_progress(
        db: AsyncSession, user_id: int, year: int
    ) -> dict | None:
        # Get the goal
        result = await db.execute(
            select(ReadingGoal).where(
                ReadingGoal.user_id == user_id,
                ReadingGoal.year == year,
            )
        )
        goal = result.scalar_one_or_none()
        if not goal:
            return None

        # Count finished books in that year
        year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
        year_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        result = await db.execute(
            select(func.count(ReadingStatus.id)).where(
                ReadingStatus.user_id == user_id,
                ReadingStatus.status == ShelfStatus.finished,
                ReadingStatus.finished_at >= year_start,
                ReadingStatus.finished_at < year_end,
            )
        )
        finished_count = result.scalar() or 0

        target = goal.target_books
        percent = min(finished_count / target, 1.0) if target > 0 else 0.0

        return {
            "year": year,
            "target_books": target,
            "finished_count": finished_count,
            "percent": round(percent, 3),
        }
