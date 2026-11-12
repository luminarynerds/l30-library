# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.reading_milestone import ReadingMilestone
from ..models.reading_status import ReadingStatus, ShelfStatus

logger = get_logger(__name__)

# Milestone thresholds for books finished
BOOKS_FINISHED_THRESHOLDS = [1, 5, 10, 25, 50, 100]

# Reading goal percentage thresholds
GOAL_THRESHOLDS = [25, 50, 75, 100]


class ReadingMilestoneService:

    @staticmethod
    async def check_and_award(
        db: AsyncSession,
        user_id: int,
        trigger: str = "general",
    ) -> Optional[ReadingMilestone]:
        first_awarded: Optional[ReadingMilestone] = None

        # Check books finished milestones
        finished_count_result = await db.execute(
            select(func.count(ReadingStatus.id))
            .where(
                ReadingStatus.user_id == user_id,
                ReadingStatus.status == ShelfStatus.finished,
            )
        )
        finished_count = finished_count_result.scalar() or 0

        for threshold in BOOKS_FINISHED_THRESHOLDS:
            if finished_count >= threshold:
                milestone = await ReadingMilestoneService._try_award(
                    db,
                    user_id,
                    milestone_type="books_finished",
                    milestone_key=f"books_finished_{threshold}",
                    title=f"{threshold} {'Book' if threshold == 1 else 'Books'} Finished!",
                    description=f"You've finished {threshold} {'book' if threshold == 1 else 'books'}. Keep going!",
                )
                if milestone and first_awarded is None:
                    first_awarded = milestone

        # Check genre explored milestones
        milestone = await ReadingMilestoneService._check_genre_explored(
            db, user_id
        )
        if milestone and first_awarded is None:
            first_awarded = milestone

        # Check reading goal percentage milestones
        milestone = await ReadingMilestoneService._check_goal_progress(
            db, user_id, finished_count
        )
        if milestone and first_awarded is None:
            first_awarded = milestone

        # Check first progress log milestone
        if trigger == "progress":
            from ..models.reading_progress import ReadingProgress
            progress_count_result = await db.execute(
                select(func.count(ReadingProgress.id))
                .where(ReadingProgress.user_id == user_id)
            )
            progress_count = progress_count_result.scalar() or 0
            if progress_count == 1:
                milestone = await ReadingMilestoneService._try_award(
                    db,
                    user_id,
                    milestone_type="first_progress",
                    milestone_key="first_progress",
                    title="First Reading Log!",
                    description="You logged your first reading progress. Your reading journey begins!",
                )
                if milestone and first_awarded is None:
                    first_awarded = milestone

        return first_awarded

    @staticmethod
    async def _check_genre_explored(
        db: AsyncSession,
        user_id: int,
    ) -> Optional[ReadingMilestone]:
        from ..models.catalog import CatalogItem

        result = await db.execute(
            select(CatalogItem.subjects)
            .join(ReadingStatus, ReadingStatus.catalog_item_id == CatalogItem.id)
            .where(
                ReadingStatus.user_id == user_id,
                ReadingStatus.status == ShelfStatus.finished,
                CatalogItem.subjects.isnot(None),
                CatalogItem.subjects != "",
            )
        )
        subjects_list = result.scalars().all()

        seen_genres: set[str] = set()
        for subjects in subjects_list:
            for part in subjects.split(","):
                genre = part.strip()
                if genre:
                    seen_genres.add(genre)

        first_awarded: Optional[ReadingMilestone] = None
        for genre in sorted(seen_genres):
            genre_slug = genre.lower().replace(" ", "-")
            milestone = await ReadingMilestoneService._try_award(
                db,
                user_id,
                milestone_type="genre_explored",
                milestone_key=f"genre_explored_{genre_slug}",
                title=f"Genre Explorer: {genre}!",
                description=f"You finished your first book in {genre}. Keep exploring!",
            )
            if milestone:
                logger.info(
                    "Genre explored milestone awarded: user_id=%s genre=%s",
                    user_id,
                    genre,
                )
                if first_awarded is None:
                    first_awarded = milestone

        return first_awarded

    @staticmethod
    async def _check_goal_progress(
        db: AsyncSession,
        user_id: int,
        finished_count: int,
    ) -> Optional[ReadingMilestone]:
        from datetime import datetime, timezone

        from ..models.reading_goal import ReadingGoal

        current_year = datetime.now(timezone.utc).year

        result = await db.execute(
            select(ReadingGoal).where(
                ReadingGoal.user_id == user_id,
                ReadingGoal.year == current_year,
            )
        )
        goal = result.scalar_one_or_none()
        if not goal or goal.target_books <= 0:
            return None

        year_start = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        finished_this_year_result = await db.execute(
            select(func.count(ReadingStatus.id)).where(
                ReadingStatus.user_id == user_id,
                ReadingStatus.status == ShelfStatus.finished,
                ReadingStatus.finished_at >= year_start,
            )
        )
        finished_this_year = finished_this_year_result.scalar() or 0

        pct = (finished_this_year / goal.target_books) * 100

        first_awarded: Optional[ReadingMilestone] = None
        for threshold in GOAL_THRESHOLDS:
            if pct >= threshold:
                milestone = await ReadingMilestoneService._try_award(
                    db,
                    user_id,
                    milestone_type="goal_percent",
                    milestone_key=f"goal_{threshold}_pct",
                    title=f"Reading Goal: {threshold}% Complete!",
                    description=f"You've reached {threshold}% of your {current_year} reading goal ({finished_this_year}/{goal.target_books} books).",
                )
                if milestone:
                    logger.info(
                        "Goal milestone awarded: user_id=%s threshold=%s%%",
                        user_id,
                        threshold,
                    )
                    if first_awarded is None:
                        first_awarded = milestone

        return first_awarded

    @staticmethod
    async def _try_award(
        db: AsyncSession,
        user_id: int,
        milestone_type: str,
        milestone_key: str,
        title: str,
        description: str,
    ) -> Optional[ReadingMilestone]:
        existing = await db.execute(
            select(ReadingMilestone).where(
                ReadingMilestone.user_id == user_id,
                ReadingMilestone.milestone_key == milestone_key,
            )
        )
        if existing.scalar_one_or_none():
            return None

        milestone = ReadingMilestone(
            user_id=user_id,
            milestone_type=milestone_type,
            milestone_key=milestone_key,
            title=title,
            description=description,
        )
        db.add(milestone)
        await db.flush()
        logger.info("Milestone awarded: user_id=%s key=%s", user_id, milestone_key)
        return milestone

    @staticmethod
    async def get_milestones(
        db: AsyncSession,
        user_id: int,
        include_dismissed: bool = False,
    ) -> list[ReadingMilestone]:
        query = select(ReadingMilestone).where(ReadingMilestone.user_id == user_id)
        if not include_dismissed:
            query = query.where(ReadingMilestone.dismissed == False)  # noqa: E712
        query = query.order_by(ReadingMilestone.earned_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def dismiss_milestone(
        db: AsyncSession,
        user_id: int,
        milestone_id: int,
    ) -> bool:
        result = await db.execute(
            select(ReadingMilestone).where(
                ReadingMilestone.id == milestone_id,
                ReadingMilestone.user_id == user_id,
            )
        )
        milestone = result.scalar_one_or_none()
        if not milestone:
            return False
        milestone.dismissed = True
        await db.commit()
        return True
