# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repair import RepairRecord, RepairStatus, VALID_REPAIR_TRANSITIONS
from app.models.catalog import CatalogItem, ItemStatus
from app.models.acquisition import Vendor
from app.models.user import User

logger = get_logger(__name__)


class RepairService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_repairs(
        self, *, page: int = 1, per_page: int = 20,
        status: str | None = None, repair_type: str | None = None,
    ) -> tuple[list, int]:
        query = (
            select(
                RepairRecord,
                CatalogItem.title.label("item_title"),
                CatalogItem.barcode.label("item_barcode"),
                Vendor.name.label("vendor_name"),
            )
            .outerjoin(CatalogItem, CatalogItem.id == RepairRecord.catalog_item_id)
            .outerjoin(Vendor, Vendor.id == RepairRecord.vendor_id)
        )
        count_query = select(func.count(RepairRecord.id))

        if status:
            query = query.where(RepairRecord.status == status)
            count_query = count_query.where(RepairRecord.status == status)
        if repair_type:
            query = query.where(RepairRecord.repair_type == repair_type)
            count_query = count_query.where(RepairRecord.repair_type == repair_type)

        total = (await self.db.execute(count_query)).scalar() or 0
        offset = (page - 1) * per_page
        result = await self.db.execute(
            query.order_by(RepairRecord.created_at.desc()).offset(offset).limit(per_page)
        )
        return list(result.all()), total

    async def get_repair(self, repair_id: int) -> RepairRecord | None:
        result = await self.db.execute(
            select(RepairRecord).where(RepairRecord.id == repair_id)
        )
        return result.scalar_one_or_none()

    async def create_repair(self, reported_by_id: int, **kwargs) -> RepairRecord:
        record = RepairRecord(reported_by_id=reported_by_id, **kwargs)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update_repair(self, repair_id: int, updates: dict) -> RepairRecord | None:
        record = await self.get_repair(repair_id)
        if not record:
            return None
        for key, value in updates.items():
            if value is not None:
                setattr(record, key, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update_status(
        self, repair_id: int, new_status: str, staff_id: int,
        **kwargs,
    ) -> RepairRecord | None:
        record = await self.get_repair(repair_id)
        if not record:
            return None

        current = record.status.value if hasattr(record.status, "value") else record.status
        valid_next = VALID_REPAIR_TRANSITIONS.get(current, [])
        if new_status not in valid_next:
            raise ValueError(
                f"Cannot transition from '{current}' to '{new_status}'. "
                f"Valid transitions: {valid_next}"
            )

        record.status = new_status

        # Side effects
        if new_status in ("in_repair", "at_bindery"):
            record.sent_date = kwargs.get("sent_date") or date.today()
            # Update catalog item status
            if record.catalog_item_id:
                item_result = await self.db.execute(
                    select(CatalogItem).where(CatalogItem.id == record.catalog_item_id)
                )
                item = item_result.scalar_one_or_none()
                if item:
                    item.status = ItemStatus.in_processing

        elif new_status == "returned":
            record.returned_date = kwargs.get("returned_date") or date.today()

        elif new_status == "completed":
            record.completed_by_id = staff_id
            record.completed_date = date.today()
            record.actual_cost = kwargs.get("actual_cost", record.actual_cost)
            # Restore catalog item
            if record.catalog_item_id:
                item_result = await self.db.execute(
                    select(CatalogItem).where(CatalogItem.id == record.catalog_item_id)
                )
                item = item_result.scalar_one_or_none()
                if item:
                    item.status = ItemStatus.available

        elif new_status == "withdrawn":
            if record.catalog_item_id:
                item_result = await self.db.execute(
                    select(CatalogItem).where(CatalogItem.id == record.catalog_item_id)
                )
                item = item_result.scalar_one_or_none()
                if item:
                    item.status = ItemStatus.withdrawn

        if kwargs.get("notes"):
            record.repair_notes = (record.repair_notes or "") + f"\n{kwargs['notes']}" if record.repair_notes else kwargs["notes"]

        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def get_dashboard(self) -> dict:
        today = date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        stats = (await self.db.execute(select(
            func.count(RepairRecord.id).filter(RepairRecord.status == "assessed").label("assessed_count"),
            func.count(RepairRecord.id).filter(RepairRecord.status == "in_repair").label("in_repair_count"),
            func.count(RepairRecord.id).filter(RepairRecord.status == "at_bindery").label("at_bindery_count"),
            func.count(RepairRecord.id).filter(
                and_(RepairRecord.status == "completed", RepairRecord.completed_date >= month_start)
            ).label("completed_this_month"),
            func.coalesce(func.sum(RepairRecord.actual_cost).filter(
                and_(RepairRecord.status == "completed", RepairRecord.completed_date >= month_start)
            ), 0).label("total_cost_month"),
            func.coalesce(func.sum(RepairRecord.actual_cost).filter(
                and_(RepairRecord.status == "completed", RepairRecord.completed_date >= year_start)
            ), 0).label("total_cost_year"),
        ))).one()

        # Average turnaround for completed items this month
        avg_result = await self.db.execute(
            select(func.avg(
                func.extract("epoch", RepairRecord.updated_at) - func.extract("epoch", RepairRecord.created_at)
            )).where(
                RepairRecord.status == "completed",
                RepairRecord.completed_date >= month_start,
            )
        )
        avg_seconds = avg_result.scalar()
        avg_days = round(avg_seconds / 86400, 1) if avg_seconds else None

        return {
            "assessed_count": stats.assessed_count,
            "in_repair_count": stats.in_repair_count,
            "at_bindery_count": stats.at_bindery_count,
            "completed_this_month": stats.completed_this_month,
            "avg_turnaround_days": avg_days,
            "total_cost_this_month": Decimal(str(stats.total_cost_month)),
            "total_cost_this_year": Decimal(str(stats.total_cost_year)),
        }
