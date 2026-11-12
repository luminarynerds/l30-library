# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.makerspace import (
    MakerspaceEquipmentMaintenance,
    ResourceStatus, MaintenanceType, MaintenanceStatus,
)
from .base_service import BaseMakerspaceService

logger = get_logger(__name__)


class MaintenanceService(BaseMakerspaceService[MakerspaceEquipmentMaintenance]):

    model = MakerspaceEquipmentMaintenance

    @staticmethod
    async def get_maintenance_records(
        db: AsyncSession,
        *,
        resource_id: int | None = None,
        maintenance_type: MaintenanceType | None = None,
        status: MaintenanceStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[list[MakerspaceEquipmentMaintenance], int]:
        query = select(MakerspaceEquipmentMaintenance)
        count_query = select(func.count(MakerspaceEquipmentMaintenance.id))

        if resource_id:
            query = query.where(MakerspaceEquipmentMaintenance.resource_id == resource_id)
            count_query = count_query.where(MakerspaceEquipmentMaintenance.resource_id == resource_id)

        if maintenance_type:
            query = query.where(MakerspaceEquipmentMaintenance.maintenance_type == maintenance_type)
            count_query = count_query.where(MakerspaceEquipmentMaintenance.maintenance_type == maintenance_type)

        if status:
            query = query.where(MakerspaceEquipmentMaintenance.status == status)
            count_query = count_query.where(MakerspaceEquipmentMaintenance.status == status)

        if start_date:
            query = query.where(MakerspaceEquipmentMaintenance.scheduled_date >= start_date)
            count_query = count_query.where(MakerspaceEquipmentMaintenance.scheduled_date >= start_date)

        if end_date:
            query = query.where(MakerspaceEquipmentMaintenance.scheduled_date <= end_date)
            count_query = count_query.where(MakerspaceEquipmentMaintenance.scheduled_date <= end_date)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = (
            query
            .options(selectinload(MakerspaceEquipmentMaintenance.resource))
            .offset(offset)
            .limit(per_page)
            .order_by(MakerspaceEquipmentMaintenance.scheduled_date)
        )

        result = await db.execute(query)
        records = list(result.scalars().all())

        return records, total

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        maintenance_id: int
    ) -> MakerspaceEquipmentMaintenance | None:
        result = await db.execute(
            select(MakerspaceEquipmentMaintenance)
            .options(selectinload(MakerspaceEquipmentMaintenance.resource))
            .where(MakerspaceEquipmentMaintenance.id == maintenance_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def schedule(
        db: AsyncSession,
        scheduled_by_id: int,
        data: dict
    ) -> MakerspaceEquipmentMaintenance:
        maintenance = MakerspaceEquipmentMaintenance(
            scheduled_by_id=scheduled_by_id,
            status=MaintenanceStatus.scheduled,
            **data
        )
        db.add(maintenance)
        await db.commit()
        await db.refresh(maintenance)
        return maintenance

    @staticmethod
    async def start(
        db: AsyncSession,
        maintenance: MakerspaceEquipmentMaintenance,
        performed_by_id: int
    ) -> MakerspaceEquipmentMaintenance:
        # Import here to avoid circular imports
        from .resource_service import MakerspaceResourceService

        if maintenance.status not in [MaintenanceStatus.scheduled, MaintenanceStatus.overdue]:
            raise ValueError(f"Cannot start maintenance in {maintenance.status} status")

        maintenance.status = MaintenanceStatus.in_progress
        maintenance.started_at = datetime.now(timezone.utc)
        maintenance.performed_by_id = performed_by_id

        # Update resource status
        resource = await MakerspaceResourceService.get_by_id(db, maintenance.resource_id)
        if resource:
            resource.status = ResourceStatus.maintenance

        await db.commit()
        await db.refresh(maintenance)
        return maintenance

    @staticmethod
    async def complete(
        db: AsyncSession,
        maintenance: MakerspaceEquipmentMaintenance,
        findings: str | None = None,
        parts_replaced: str | None = None,
        parts_cost: Decimal = Decimal("0.00"),
        labor_hours: Decimal = Decimal("0.00"),
        next_maintenance_date: date | None = None,
        notes: str | None = None
    ) -> MakerspaceEquipmentMaintenance:
        # Import here to avoid circular imports
        from .resource_service import MakerspaceResourceService

        if maintenance.status != MaintenanceStatus.in_progress:
            raise ValueError(f"Cannot complete maintenance in {maintenance.status} status")

        maintenance.status = MaintenanceStatus.completed
        maintenance.completed_at = datetime.now(timezone.utc)
        maintenance.findings = findings
        maintenance.parts_replaced = parts_replaced
        maintenance.parts_cost = parts_cost
        maintenance.labor_hours = labor_hours
        maintenance.notes = notes

        # Update resource
        resource = await MakerspaceResourceService.get_by_id(db, maintenance.resource_id)
        if resource:
            resource.status = ResourceStatus.available
            resource.last_maintenance_date = date.today()

            if next_maintenance_date:
                resource.next_maintenance_date = next_maintenance_date
                maintenance.next_maintenance_date = next_maintenance_date
            elif resource.maintenance_interval_days:
                resource.next_maintenance_date = date.today() + timedelta(
                    days=resource.maintenance_interval_days
                )

        await db.commit()
        await db.refresh(maintenance)
        return maintenance

    @staticmethod
    async def get_overdue(
        db: AsyncSession
    ) -> list[MakerspaceEquipmentMaintenance]:
        today = date.today()
        result = await db.execute(
            select(MakerspaceEquipmentMaintenance)
            .options(selectinload(MakerspaceEquipmentMaintenance.resource))
            .where(MakerspaceEquipmentMaintenance.status == MaintenanceStatus.scheduled)
            .where(MakerspaceEquipmentMaintenance.scheduled_date < today)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_upcoming(
        db: AsyncSession,
        days: int = 7
    ) -> list[MakerspaceEquipmentMaintenance]:
        today = date.today()
        deadline = today + timedelta(days=days)
        result = await db.execute(
            select(MakerspaceEquipmentMaintenance)
            .options(selectinload(MakerspaceEquipmentMaintenance.resource))
            .where(MakerspaceEquipmentMaintenance.status == MaintenanceStatus.scheduled)
            .where(MakerspaceEquipmentMaintenance.scheduled_date >= today)
            .where(MakerspaceEquipmentMaintenance.scheduled_date <= deadline)
            .order_by(MakerspaceEquipmentMaintenance.scheduled_date)
        )
        return list(result.scalars().all())
