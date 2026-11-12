# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import json
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.reading_activity import ReadingActivity

logger = get_logger(__name__)


class ReadingActivityService:

    @staticmethod
    async def log_activity(
        db: AsyncSession,
        user_id: int,
        activity_type: str,
        summary: str,
        catalog_item_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> ReadingActivity:
        entry = ReadingActivity(
            user_id=user_id,
            catalog_item_id=catalog_item_id,
            activity_type=activity_type,
            summary=summary,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        db.add(entry)
        await db.flush()
        return entry

    @staticmethod
    async def get_recent(
        db: AsyncSession,
        user_id: int,
        limit: int = 5,
        offset: int = 0,
    ) -> tuple[list[ReadingActivity], int]:
        # Get total count
        count_result = await db.execute(
            select(func.count(ReadingActivity.id))
            .where(ReadingActivity.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Get paginated results
        result = await db.execute(
            select(ReadingActivity)
            .where(ReadingActivity.user_id == user_id)
            .order_by(ReadingActivity.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def log_book_returned(
        db: AsyncSession,
        user_id: int,
        catalog_item_id: int,
        title: str,
    ) -> None:
        try:
            from .organization_features_service import OrganizationFeaturesService
            if not await OrganizationFeaturesService.is_feature_enabled(db, "reading_shelf_enabled"):
                return

            from ..models.reading_status import ReadingStatus, ShelfStatus

            result = await db.execute(
                select(ReadingStatus).where(
                    ReadingStatus.user_id == user_id,
                    ReadingStatus.catalog_item_id == catalog_item_id,
                    ReadingStatus.status == ShelfStatus.currently_reading,
                )
            )
            if result.scalar_one_or_none() is None:
                return

            await ReadingActivityService.log_activity(
                db,
                user_id=user_id,
                activity_type="book_returned",
                summary=f"Returned \u201c{title}\u201d",
                catalog_item_id=catalog_item_id,
            )
        except Exception:  # noqa: BLE001 -- activity log non-critical: return commit must not depend on log success
            logger.warning(
                "Failed to log book_returned activity for user %s item %s",
                user_id,
                catalog_item_id,
            )

    @staticmethod
    async def log_ebook_expired(
        db: AsyncSession,
        user_id: int,
        title: str,
        catalog_item_id: Optional[int] = None,
    ) -> None:
        try:
            from .organization_features_service import OrganizationFeaturesService
            if not await OrganizationFeaturesService.is_feature_enabled(db, "reading_shelf_enabled"):
                return

            await ReadingActivityService.log_activity(
                db,
                user_id=user_id,
                activity_type="ebook_expired",
                summary=f"Ebook loan expired: \u201c{title}\u201d",
                catalog_item_id=catalog_item_id,
            )
        except Exception:  # noqa: BLE001 -- activity log non-critical: ebook expiry must not depend on log success
            logger.warning(
                "Failed to log ebook_expired activity for user %s title %s",
                user_id,
                title,
            )
