# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from ...models.makerspace import (
    ConsumableItem, ConsumableUsage,
)
from .base_service import BaseMakerspaceService

logger = get_logger(__name__)


class ConsumableService(BaseMakerspaceService[ConsumableItem]):

    model = ConsumableItem

    @staticmethod
    async def get_all(
        db: AsyncSession,
        *,
        category: str | None = None,
        material_type: str | None = None,
        is_active: bool = True,
        low_stock_only: bool = False,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[list[ConsumableItem], int]:
        query = select(ConsumableItem)
        count_query = select(func.count(ConsumableItem.id))

        if is_active is not None:
            query = query.where(ConsumableItem.is_active == is_active)
            count_query = count_query.where(ConsumableItem.is_active == is_active)

        if category:
            query = query.where(ConsumableItem.category == category)
            count_query = count_query.where(ConsumableItem.category == category)

        if material_type:
            query = query.where(ConsumableItem.material_type == material_type)
            count_query = count_query.where(ConsumableItem.material_type == material_type)

        if low_stock_only:
            query = query.where(
                ConsumableItem.quantity_in_stock <= ConsumableItem.reorder_threshold
            )
            count_query = count_query.where(
                ConsumableItem.quantity_in_stock <= ConsumableItem.reorder_threshold
            )

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page).order_by(ConsumableItem.name)

        result = await db.execute(query)
        consumables = list(result.scalars().all())

        return consumables, total

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        consumable_id: int
    ) -> ConsumableItem | None:
        result = await db.execute(
            select(ConsumableItem).where(ConsumableItem.id == consumable_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        data: dict
    ) -> ConsumableItem:
        consumable = ConsumableItem(**data)
        db.add(consumable)
        await db.commit()
        await db.refresh(consumable)
        return consumable

    @staticmethod
    async def update(
        db: AsyncSession,
        consumable: ConsumableItem,
        data: dict
    ) -> ConsumableItem:
        for key, value in data.items():
            if value is not None:
                setattr(consumable, key, value)
        await db.commit()
        await db.refresh(consumable)
        return consumable

    @staticmethod
    async def adjust_stock(
        db: AsyncSession,
        consumable: ConsumableItem,
        quantity: Decimal,
        reason: str
    ) -> ConsumableItem:
        new_quantity = consumable.quantity_in_stock + quantity
        if new_quantity < 0:
            raise ValueError("Stock cannot be negative")

        consumable.quantity_in_stock = new_quantity
        await db.commit()
        await db.refresh(consumable)

        logger.info(
            f"Stock adjusted for {consumable.name}: {quantity} ({reason}). "
            f"New quantity: {new_quantity}"
        )
        return consumable

    @staticmethod
    async def record_usage(
        db: AsyncSession,
        consumable_id: int,
        quantity: Decimal,
        job_id: int | None = None,
        reservation_id: int | None = None,
        resource_id: int | None = None,
        recorded_by_id: int | None = None
    ) -> ConsumableUsage:
        consumable = await ConsumableService.get_by_id(db, consumable_id)
        if not consumable:
            raise ValueError("Consumable not found")

        if quantity > consumable.quantity_in_stock:
            raise ValueError("Insufficient stock")

        # Calculate cost
        cost = quantity * consumable.price_per_unit

        # Create usage record
        usage = ConsumableUsage(
            consumable_id=consumable_id,
            job_id=job_id,
            reservation_id=reservation_id,
            resource_id=resource_id,
            quantity_used=quantity,
            cost=cost,
            recorded_by_id=recorded_by_id
        )
        db.add(usage)

        # Update stock
        consumable.quantity_in_stock -= quantity

        await db.commit()
        await db.refresh(usage)
        return usage

    @staticmethod
    async def get_low_stock_items(
        db: AsyncSession
    ) -> list[ConsumableItem]:
        result = await db.execute(
            select(ConsumableItem)
            .where(ConsumableItem.is_active == True)
            .where(ConsumableItem.quantity_in_stock <= ConsumableItem.reorder_threshold)
            .order_by(ConsumableItem.quantity_in_stock)
        )
        return list(result.scalars().all())
