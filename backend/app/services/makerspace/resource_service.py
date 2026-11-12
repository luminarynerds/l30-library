# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.makerspace import (
    MakerspaceResource, MakerspaceReservation,
    ResourceType, ResourceStatus, MakerspaceReservationStatus,
)
from .base_service import BaseMakerspaceService

logger = get_logger(__name__)


class MakerspaceResourceService(BaseMakerspaceService[MakerspaceResource]):

    model = MakerspaceResource

    @staticmethod
    async def get_all(
        db: AsyncSession,
        *,
        resource_type: ResourceType | None = None,
        status: ResourceStatus | None = None,
        is_active: bool = True,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[MakerspaceResource], int]:
        query = select(MakerspaceResource)
        count_query = select(func.count(MakerspaceResource.id))

        if is_active is not None:
            query = query.where(MakerspaceResource.is_active == is_active)
            count_query = count_query.where(MakerspaceResource.is_active == is_active)

        if resource_type:
            query = query.where(MakerspaceResource.resource_type == resource_type)
            count_query = count_query.where(MakerspaceResource.resource_type == resource_type)

        if status:
            query = query.where(MakerspaceResource.status == status)
            count_query = count_query.where(MakerspaceResource.status == status)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page).order_by(MakerspaceResource.name)

        result = await db.execute(query)
        resources = list(result.scalars().all())

        return resources, total

    @staticmethod
    async def get_by_id(db: AsyncSession, resource_id: int) -> MakerspaceResource | None:
        result = await db.execute(
            select(MakerspaceResource)
            .options(selectinload(MakerspaceResource.certification_type))
            .where(MakerspaceResource.id == resource_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        data: dict,
        created_by_id: int | None = None
    ) -> MakerspaceResource:
        resource = MakerspaceResource(**data, created_by_id=created_by_id)
        db.add(resource)
        await db.commit()
        await db.refresh(resource)
        return resource

    @staticmethod
    async def update(
        db: AsyncSession,
        resource: MakerspaceResource,
        data: dict
    ) -> MakerspaceResource:
        for key, value in data.items():
            if value is not None:
                setattr(resource, key, value)
        await db.commit()
        await db.refresh(resource)
        return resource

    @staticmethod
    async def get_availability(
        db: AsyncSession,
        resource_id: int,
        target_date: date,
        slot_duration_minutes: int = 60
    ) -> list[dict]:
        resource = await MakerspaceResourceService.get_by_id(db, resource_id)
        if not resource:
            return []

        # Check if resource is available on this day
        weekday = target_date.weekday()
        if weekday not in (resource.available_days or []):
            return []

        # Get existing reservations for this day
        day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        day_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        result = await db.execute(
            select(MakerspaceReservation)
            .where(MakerspaceReservation.resource_id == resource_id)
            .where(MakerspaceReservation.status.in_([
                MakerspaceReservationStatus.pending,
                MakerspaceReservationStatus.confirmed,
                MakerspaceReservationStatus.checked_in
            ]))
            .where(MakerspaceReservation.start_time < day_end)
            .where(MakerspaceReservation.end_time > day_start)
        )
        existing_reservations = result.scalars().all()

        # Parse available hours
        available_from = datetime.strptime(resource.available_from, "%H:%M").time()
        available_until = datetime.strptime(resource.available_until, "%H:%M").time()

        slots = []
        current_time = datetime.combine(target_date, available_from).replace(tzinfo=timezone.utc)
        end_time = datetime.combine(target_date, available_until).replace(tzinfo=timezone.utc)

        while current_time < end_time:
            slot_end = current_time + timedelta(minutes=slot_duration_minutes)
            if slot_end > end_time:
                break

            # Check if slot overlaps with any existing reservation
            is_available = True
            overlapping_reservation = None

            for reservation in existing_reservations:
                if (current_time < reservation.end_time and slot_end > reservation.start_time):
                    is_available = False
                    overlapping_reservation = reservation.id
                    break

            slots.append({
                "start_time": current_time,
                "end_time": slot_end,
                "is_available": is_available,
                "reservation_id": overlapping_reservation
            })

            current_time = slot_end + timedelta(minutes=resource.buffer_minutes)

        return slots

    @staticmethod
    async def update_status(
        db: AsyncSession,
        resource: MakerspaceResource,
        status: ResourceStatus,
        notes: str | None = None
    ) -> MakerspaceResource:
        resource.status = status
        if notes:
            resource.status_notes = notes
        await db.commit()
        await db.refresh(resource)
        return resource
