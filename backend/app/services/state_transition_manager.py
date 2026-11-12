# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.catalog import CatalogItem, ItemStatus
from ..models.catalog_state_event import CatalogStateEvent

logger = get_logger(__name__)


class StateTransitionManager:

    @staticmethod
    async def transition(
        db: AsyncSession,
        catalog_item_id: int,
        new_status: ItemStatus,
        reason: str,
        source_type: str,
        source_id: int | None = None,
        actor_id: int | None = None,
    ) -> CatalogStateEvent:
        result = await db.execute(
            select(CatalogItem).where(CatalogItem.id == catalog_item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError(f"CatalogItem {catalog_item_id} not found")

        old_status = item.status

        event = CatalogStateEvent(
            catalog_item_id=catalog_item_id,
            old_status=old_status.value if hasattr(old_status, "value") else str(old_status),
            new_status=new_status.value if hasattr(new_status, "value") else str(new_status),
            reason=reason,
            source_type=source_type,
            source_id=source_id,
            actor_id=actor_id,
        )
        db.add(event)

        if old_status != new_status:
            item.status = new_status
            logger.info(
                "CatalogItem %s: %s -> %s (%s)",
                catalog_item_id, old_status, new_status, source_type,
            )

        await db.flush()
        return event

    @staticmethod
    async def get_history(
        db: AsyncSession,
        catalog_item_id: int,
        limit: int = 50,
    ) -> list[CatalogStateEvent]:
        result = await db.execute(
            select(CatalogStateEvent)
            .where(CatalogStateEvent.catalog_item_id == catalog_item_id)
            .order_by(CatalogStateEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
