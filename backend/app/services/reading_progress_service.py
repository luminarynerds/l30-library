# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.reading_progress import ReadingProgress


class ReadingProgressService:

    @staticmethod
    async def log_progress(
        db: AsyncSession,
        user_id: int,
        catalog_item_id: int,
        current_page: Optional[int],
        total_pages: Optional[int],
        percent: int,
        note: Optional[str] = None,
    ) -> tuple[ReadingProgress, Optional[dict]]:
        entry = ReadingProgress(
            user_id=user_id,
            catalog_item_id=catalog_item_id,
            current_page=current_page,
            total_pages=total_pages,
            percent=percent,
            note=note,
        )
        db.add(entry)
        await db.flush()

        # Activity logging
        from .reading_activity_service import ReadingActivityService
        page_info = f"page {current_page}" if current_page else f"~{percent}%"
        await ReadingActivityService.log_activity(
            db, user_id, "progress_logged",
            f"Read to {page_info}",
            catalog_item_id=catalog_item_id,
            metadata={"current_page": current_page, "percent": percent},
        )

        # Milestone check
        from .reading_milestone_service import ReadingMilestoneService
        milestone = await ReadingMilestoneService.check_and_award(
            db, user_id, trigger="progress"
        )
        milestone_data = None
        if milestone:
            await ReadingActivityService.log_activity(
                db, user_id, "milestone_earned",
                f"Earned: {milestone.title}",
                metadata={"milestone_key": milestone.milestone_key},
            )
            milestone_data = {
                "id": milestone.id,
                "title": milestone.title,
                "description": milestone.description,
                "milestone_key": milestone.milestone_key,
            }

        await db.commit()
        await db.refresh(entry)
        return entry, milestone_data

    @staticmethod
    async def get_history(
        db: AsyncSession,
        user_id: int,
        catalog_item_id: int,
        limit: int = 20,
    ) -> list[ReadingProgress]:
        result = await db.execute(
            select(ReadingProgress)
            .where(
                ReadingProgress.user_id == user_id,
                ReadingProgress.catalog_item_id == catalog_item_id,
            )
            .order_by(ReadingProgress.logged_at.desc(), ReadingProgress.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_latest(
        db: AsyncSession,
        user_id: int,
        catalog_item_id: int,
    ) -> Optional[ReadingProgress]:
        result = await db.execute(
            select(ReadingProgress)
            .where(
                ReadingProgress.user_id == user_id,
                ReadingProgress.catalog_item_id == catalog_item_id,
            )
            .order_by(ReadingProgress.logged_at.desc(), ReadingProgress.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_latest(
        db: AsyncSession,
        user_id: int,
    ) -> list[ReadingProgress]:
        subq = (
            select(
                ReadingProgress.catalog_item_id,
                func.max(ReadingProgress.id).label("max_id"),
            )
            .where(ReadingProgress.user_id == user_id)
            .group_by(ReadingProgress.catalog_item_id)
            .subquery()
        )
        result = await db.execute(
            select(ReadingProgress)
            .join(
                subq,
                (ReadingProgress.id == subq.c.max_id),
            )
            .where(ReadingProgress.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def compute_pace(
        db: AsyncSession,
        user_id: int,
        catalog_item_id: int,
    ) -> Optional[dict]:
        entries = await ReadingProgressService.get_history(
            db, user_id, catalog_item_id, limit=100
        )
        if len(entries) < 3:
            return None

        latest = entries[0]
        earliest = entries[-1]
        days = max((latest.logged_at - earliest.logged_at).days, 1)
        pages_read = (latest.current_page or 0) - (earliest.current_page or 0)

        if pages_read <= 0 or not latest.total_pages:
            return None

        avg_pages_per_day = round(pages_read / days, 1)
        remaining = latest.total_pages - (latest.current_page or 0)
        est_days = round(remaining / avg_pages_per_day) if avg_pages_per_day > 0 else None
        est_date = (
            (datetime.now(timezone.utc) + timedelta(days=est_days)).strftime("%b %d")
            if est_days
            else None
        )

        return {
            "avg_pages_per_day": avg_pages_per_day,
            "estimated_finish_date": est_date,
            "entries_count": len(entries),
        }
