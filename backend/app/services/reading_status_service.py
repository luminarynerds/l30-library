# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.catalog import CatalogItem
from ..models.reading_status import ReadingStatus, ShelfStatus


class ReadingStatusService:

    @staticmethod
    async def get_user_statuses(
        db: AsyncSession,
        user_id: int,
        status_filter: Optional[ShelfStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReadingStatus]:
        query = (
            select(ReadingStatus)
            .options(selectinload(ReadingStatus.catalog_item))
            .where(ReadingStatus.user_id == user_id)
        )
        if status_filter:
            query = query.where(ReadingStatus.status == status_filter)
        query = query.order_by(ReadingStatus.updated_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def set_status(
        db: AsyncSession,
        user_id: int,
        catalog_item_id: int,
        status: ShelfStatus,
        private_notes: Optional[str] = None,
        personal_tags: Optional[list[str]] = None,
    ) -> tuple["ReadingStatus", Optional[dict]]:
        # Check catalog item exists
        item = await db.execute(
            select(CatalogItem).where(CatalogItem.id == catalog_item_id)
        )
        if not item.scalar_one_or_none():
            raise ValueError("Catalog item not found")

        # Upsert
        result = await db.execute(
            select(ReadingStatus).where(
                ReadingStatus.user_id == user_id,
                ReadingStatus.catalog_item_id == catalog_item_id,
            )
        )
        reading_status = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        is_new = reading_status is None
        old_status = reading_status.status if reading_status else None
        status_changed = is_new or old_status != status

        if reading_status:
            reading_status.status = status
            if private_notes is not None:
                reading_status.private_notes = private_notes
            if personal_tags is not None:
                reading_status.personal_tags = personal_tags
            # Auto-timestamp transitions
            if status == ShelfStatus.currently_reading and old_status and old_status != ShelfStatus.currently_reading:
                reading_status.started_at = reading_status.started_at or now
            if status in (ShelfStatus.finished, ShelfStatus.did_not_finish):
                reading_status.finished_at = now
        else:
            reading_status = ReadingStatus(
                user_id=user_id,
                catalog_item_id=catalog_item_id,
                status=status,
                private_notes=private_notes,
                personal_tags=personal_tags or [],
            )
            if status == ShelfStatus.currently_reading:
                reading_status.started_at = now
            if status in (ShelfStatus.finished, ShelfStatus.did_not_finish):
                reading_status.finished_at = now
            db.add(reading_status)

        await db.flush()

        milestone_data = None
        if status_changed:
            # Activity logging — only when status actually changed
            from .reading_activity_service import ReadingActivityService
            from ..models.reading_status import ShelfStatus as _SS
            status_label = {
                _SS.want_to_read: "Want to Read",
                _SS.currently_reading: "Currently Reading",
                _SS.on_hold: "On Hold",
                _SS.finished: "Finished",
                _SS.did_not_finish: "Did Not Finish",
            }.get(status, str(status))

            activity_type = "book_finished" if status == ShelfStatus.finished else "status_changed"
            await ReadingActivityService.log_activity(
                db, user_id, activity_type,
                f"Moved to {status_label}",
                catalog_item_id=catalog_item_id,
                metadata={"new_status": status.value},
            )

            # Milestone check
            from .reading_milestone_service import ReadingMilestoneService
            milestone = await ReadingMilestoneService.check_and_award(
                db, user_id, trigger="status_change"
            )
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
        await db.refresh(reading_status)

        # Reload with relationship
        result = await db.execute(
            select(ReadingStatus)
            .options(selectinload(ReadingStatus.catalog_item))
            .where(ReadingStatus.id == reading_status.id)
        )
        return result.scalar_one(), milestone_data

    @staticmethod
    async def remove_status(db: AsyncSession, user_id: int, catalog_item_id: int) -> bool:
        result = await db.execute(
            select(ReadingStatus).where(
                ReadingStatus.user_id == user_id,
                ReadingStatus.catalog_item_id == catalog_item_id,
            )
        )
        reading_status = result.scalar_one_or_none()
        if not reading_status:
            return False
        await db.delete(reading_status)
        await db.commit()
        return True

    @staticmethod
    async def get_stats(db: AsyncSession, user_id: int) -> dict:
        # Counts per status
        result = await db.execute(
            select(ReadingStatus.status, func.count(ReadingStatus.id))
            .where(ReadingStatus.user_id == user_id)
            .group_by(ReadingStatus.status)
        )
        counts = {s.value: 0 for s in ShelfStatus}
        for status, count in result:
            counts[status.value] = count

        # Finished this year
        year_start = datetime(datetime.now().year, 1, 1, tzinfo=timezone.utc)
        result = await db.execute(
            select(func.count(ReadingStatus.id)).where(
                ReadingStatus.user_id == user_id,
                ReadingStatus.status == ShelfStatus.finished,
                ReadingStatus.finished_at >= year_start,
            )
        )
        counts["finished_this_year"] = result.scalar() or 0

        return counts
