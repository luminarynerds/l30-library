# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.acquisition import Fund, FundStatus, PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from ...models.catalog import CatalogItem
from ...models.inventory import AcquisitionSource, ItemCondition, ItemCopy


class PORepository:

    @staticmethod
    async def get_purchase_order_by_id(
        db: AsyncSession,
        po_id: int,
        with_items: bool = False,
        with_relationships: bool = False,
    ) -> Optional[PurchaseOrder]:
        options = []
        if with_items:
            options.append(selectinload(PurchaseOrder.items))
        if with_relationships:
            options.extend([
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.fund),
                selectinload(PurchaseOrder.created_by),
                selectinload(PurchaseOrder.approved_by),
            ])

        query = select(PurchaseOrder).where(PurchaseOrder.id == po_id)
        if options:
            query = query.options(*options)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_purchase_orders(
        db: AsyncSession,
        status: Optional[PurchaseOrderStatus] = None,
        vendor_id: Optional[int] = None,
        fund_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[PurchaseOrder], int]:
        query = select(PurchaseOrder).options(
            selectinload(PurchaseOrder.vendor),
            selectinload(PurchaseOrder.fund),
            selectinload(PurchaseOrder.items),
        )
        count_query = select(func.count(PurchaseOrder.id))

        filters = []
        if status:
            filters.append(PurchaseOrder.status == status)
        if vendor_id:
            filters.append(PurchaseOrder.vendor_id == vendor_id)
        if fund_id:
            filters.append(PurchaseOrder.fund_id == fund_id)

        if filters:
            from sqlalchemy import and_
            combined_filter = and_(*filters)
            query = query.where(combined_filter)
            count_query = count_query.where(combined_filter)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page).order_by(PurchaseOrder.created_at.desc())

        result = await db.execute(query)
        orders = result.scalars().all()

        return orders, total

    @staticmethod
    async def get_fund_by_id(db: AsyncSession, fund_id: int) -> Optional[Fund]:
        result = await db.execute(select(Fund).where(Fund.id == fund_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_po_count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(PurchaseOrder.id)))
        return result.scalar() or 0

    @staticmethod
    async def get_po_item_by_id(
        db: AsyncSession,
        item_id: int,
        po_id: int,
    ) -> Optional[PurchaseOrderItem]:
        result = await db.execute(
            select(PurchaseOrderItem).where(
                PurchaseOrderItem.id == item_id,
                PurchaseOrderItem.purchase_order_id == po_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_po_items_by_po_id(
        db: AsyncSession,
        po_id: int,
    ) -> List[PurchaseOrderItem]:
        result = await db.execute(
            select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po_id)
        )
        return result.scalars().all()

    @staticmethod
    async def get_catalog_item_by_id(db: AsyncSession, item_id: int) -> Optional[CatalogItem]:
        result = await db.execute(select(CatalogItem).where(CatalogItem.id == item_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_item_copy_count_for_catalog(
        db: AsyncSession,
        catalog_item_id: int,
    ) -> int:
        result = await db.execute(
            select(func.count(ItemCopy.id)).where(ItemCopy.catalog_item_id == catalog_item_id)
        )
        return result.scalar() or 0

    @staticmethod
    async def create_catalog_item(
        db: AsyncSession,
        title: str,
        author: Optional[str] = None,
        isbn: Optional[str] = None,
    ) -> CatalogItem:
        item = CatalogItem(
            title=title,
            author=author,
            isbn=isbn,
        )
        db.add(item)
        await db.flush()
        return item

    @staticmethod
    async def create_item_copy(
        db: AsyncSession,
        catalog_item_id: int,
        barcode: str,
        copy_number: int,
        condition: ItemCondition,
        acquisition_source: AcquisitionSource,
        purchase_order_item_id: Optional[int] = None,
        replacement_cost: Optional[Decimal] = None,
    ) -> ItemCopy:
        item_copy = ItemCopy(
            catalog_item_id=catalog_item_id,
            barcode=barcode,
            copy_number=copy_number,
            condition=condition,
            acquisition_source=acquisition_source,
            purchase_order_item_id=purchase_order_item_id,
            replacement_cost=replacement_cost,
        )
        db.add(item_copy)
        await db.flush()
        return item_copy
