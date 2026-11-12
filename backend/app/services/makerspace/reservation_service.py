# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.makerspace import (
    MakerspaceReservation, MakerspaceResource,
    ResourceStatus, MakerspaceReservationStatus,
)
from .base_service import BaseMakerspaceService

logger = get_logger(__name__)


class ReservationService(BaseMakerspaceService[MakerspaceReservation]):

    model = MakerspaceReservation

    @staticmethod
    async def get_reservations(
        db: AsyncSession,
        *,
        user_id: int | None = None,
        resource_id: int | None = None,
        status: MakerspaceReservationStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[list[MakerspaceReservation], int]:
        query = select(MakerspaceReservation)
        count_query = select(func.count(MakerspaceReservation.id))

        if user_id:
            query = query.where(MakerspaceReservation.user_id == user_id)
            count_query = count_query.where(MakerspaceReservation.user_id == user_id)

        if resource_id:
            query = query.where(MakerspaceReservation.resource_id == resource_id)
            count_query = count_query.where(MakerspaceReservation.resource_id == resource_id)

        if status:
            query = query.where(MakerspaceReservation.status == status)
            count_query = count_query.where(MakerspaceReservation.status == status)

        if start_date:
            start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            query = query.where(MakerspaceReservation.start_time >= start_dt)
            count_query = count_query.where(MakerspaceReservation.start_time >= start_dt)

        if end_date:
            end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
            query = query.where(MakerspaceReservation.end_time <= end_dt)
            count_query = count_query.where(MakerspaceReservation.end_time <= end_dt)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = (
            query
            .options(
                selectinload(MakerspaceReservation.resource),
                selectinload(MakerspaceReservation.user)
            )
            .offset(offset)
            .limit(per_page)
            .order_by(MakerspaceReservation.start_time)
        )

        result = await db.execute(query)
        reservations = list(result.scalars().all())

        return reservations, total

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        reservation_id: int
    ) -> MakerspaceReservation | None:
        result = await db.execute(
            select(MakerspaceReservation)
            .options(
                selectinload(MakerspaceReservation.resource),
                selectinload(MakerspaceReservation.user)
            )
            .where(MakerspaceReservation.id == reservation_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        resource_id: int,
        start_time: datetime,
        end_time: datetime,
        project_name: str | None = None,
        project_description: str | None = None,
        notes: str | None = None
    ) -> MakerspaceReservation:
        # Import here to avoid circular imports
        from .resource_service import MakerspaceResourceService
        from .certification_service import CertificationService

        # Get the resource
        resource = await MakerspaceResourceService.get_by_id(db, resource_id)
        if not resource:
            raise ValueError("Resource not found")

        if resource.status != ResourceStatus.available:
            raise ValueError(f"Resource is not available (status: {resource.status})")

        # Check certification if required
        if resource.requires_certification and resource.certification_type_id:
            is_certified = await CertificationService.check_user_certified(
                db, user_id, resource.certification_type_id
            )
            if not is_certified:
                raise ValueError("User is not certified to use this equipment")

        # Check for overlapping reservations with row-level lock to prevent
        # double-booking race conditions between concurrent transactions
        existing = await db.execute(
            select(MakerspaceReservation)
            .where(MakerspaceReservation.resource_id == resource_id)
            .where(MakerspaceReservation.status.in_([
                MakerspaceReservationStatus.pending,
                MakerspaceReservationStatus.confirmed,
                MakerspaceReservationStatus.checked_in
            ]))
            .where(MakerspaceReservation.start_time < end_time)
            .where(MakerspaceReservation.end_time > start_time)
            .with_for_update()
        )
        if existing.scalars().first():
            raise ValueError("Time slot conflict: resource already booked for this period")

        # Calculate estimated cost
        duration_hours = Decimal((end_time - start_time).total_seconds()) / Decimal(3600)
        estimated_cost = (resource.hourly_cost * duration_hours) + resource.setup_fee

        reservation = MakerspaceReservation(
            user_id=user_id,
            resource_id=resource_id,
            start_time=start_time,
            end_time=end_time,
            project_name=project_name,
            project_description=project_description,
            notes=notes,
            estimated_cost=estimated_cost,
            status=MakerspaceReservationStatus.pending
        )

        db.add(reservation)
        await db.commit()
        await db.refresh(reservation)
        return reservation

    @staticmethod
    async def approve(
        db: AsyncSession,
        reservation: MakerspaceReservation,
        approved_by_id: int,
        notes: str | None = None
    ) -> MakerspaceReservation:
        if reservation.status != MakerspaceReservationStatus.pending:
            raise ValueError(f"Cannot approve reservation in {reservation.status} status")

        reservation.status = MakerspaceReservationStatus.confirmed
        reservation.approved_by_id = approved_by_id
        reservation.approved_at = datetime.now(timezone.utc)
        if notes:
            reservation.staff_notes = notes

        await db.commit()
        await db.refresh(reservation)
        return reservation

    @staticmethod
    async def check_in(
        db: AsyncSession,
        reservation: MakerspaceReservation,
        notes: str | None = None
    ) -> MakerspaceReservation:
        if reservation.status not in [MakerspaceReservationStatus.pending, MakerspaceReservationStatus.confirmed]:
            raise ValueError(f"Cannot check in reservation in {reservation.status} status")

        reservation.status = MakerspaceReservationStatus.checked_in
        reservation.checked_in_at = datetime.now(timezone.utc)
        if notes:
            reservation.notes = (reservation.notes or "") + f"\nCheck-in: {notes}"

        # Update resource status
        if reservation.resource:
            reservation.resource.status = ResourceStatus.in_use

        await db.commit()
        await db.refresh(reservation)
        return reservation

    @staticmethod
    async def check_out(
        db: AsyncSession,
        reservation: MakerspaceReservation,
        notes: str | None = None,
        consumables_used: list[dict] | None = None
    ) -> MakerspaceReservation:
        # Import here to avoid circular imports
        from .resource_service import MakerspaceResourceService
        from .consumable_service import ConsumableService

        if reservation.status != MakerspaceReservationStatus.checked_in:
            raise ValueError(f"Cannot check out reservation in {reservation.status} status")

        reservation.status = MakerspaceReservationStatus.completed
        reservation.checked_out_at = datetime.now(timezone.utc)
        if notes:
            reservation.notes = (reservation.notes or "") + f"\nCheck-out: {notes}"

        # Calculate actual cost based on actual time
        if reservation.checked_in_at:
            actual_duration = Decimal(
                (reservation.checked_out_at - reservation.checked_in_at).total_seconds()
            ) / Decimal(3600)

            resource = await MakerspaceResourceService.get_by_id(db, reservation.resource_id)
            if resource:
                reservation.actual_cost = (
                    resource.hourly_cost * actual_duration
                ) + resource.setup_fee

        # Record consumables used
        consumables_total = Decimal("0.00")
        if consumables_used:
            for item in consumables_used:
                usage = await ConsumableService.record_usage(
                    db,
                    consumable_id=item["consumable_id"],
                    quantity=item["quantity_used"],
                    reservation_id=reservation.id,
                    resource_id=reservation.resource_id
                )
                consumables_total += usage.cost

        reservation.consumables_cost = consumables_total
        reservation.actual_cost = (reservation.actual_cost or Decimal("0.00")) + consumables_total

        # Update resource status
        if reservation.resource:
            reservation.resource.status = ResourceStatus.available

        await db.commit()
        await db.refresh(reservation)
        return reservation

    @staticmethod
    async def cancel(
        db: AsyncSession,
        reservation: MakerspaceReservation,
        cancelled_by_id: int,
        reason: str | None = None
    ) -> MakerspaceReservation:
        if reservation.status in [
            MakerspaceReservationStatus.completed,
            MakerspaceReservationStatus.cancelled,
            MakerspaceReservationStatus.no_show
        ]:
            raise ValueError(f"Cannot cancel reservation in {reservation.status} status")

        reservation.status = MakerspaceReservationStatus.cancelled
        reservation.cancelled_at = datetime.now(timezone.utc)
        reservation.cancelled_by_id = cancelled_by_id
        reservation.cancellation_reason = reason

        # Update resource status if was checked in
        if reservation.resource and reservation.resource.status == ResourceStatus.in_use:
            reservation.resource.status = ResourceStatus.available

        await db.commit()
        await db.refresh(reservation)
        return reservation

    @staticmethod
    async def mark_no_show(
        db: AsyncSession,
        reservation: MakerspaceReservation
    ) -> MakerspaceReservation:
        if reservation.status not in [MakerspaceReservationStatus.pending, MakerspaceReservationStatus.confirmed]:
            raise ValueError(f"Cannot mark as no-show: reservation is in {reservation.status} status")

        reservation.status = MakerspaceReservationStatus.no_show
        await db.commit()
        await db.refresh(reservation)
        return reservation
