# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.makerspace import (
    MakerspaceResource, MakerspaceReservation, MakerspacePayment,
    SafetyIncident,
    MakerspaceReservationStatus, PaymentStatus, MakerspaceIncidentSeverity,
)

logger = get_logger(__name__)


class MakerspaceReportsService:

    @staticmethod
    async def get_resource_utilization(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        resource_id: int | None = None
    ) -> list[dict]:
        # Import here to avoid circular imports
        from .resource_service import MakerspaceResourceService

        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Get all resources
        resource_query = select(MakerspaceResource).where(MakerspaceResource.is_active == True)
        if resource_id:
            resource_query = resource_query.where(MakerspaceResource.id == resource_id)

        resources_result = await db.execute(resource_query)
        resources = resources_result.scalars().all()

        reports = []
        for resource in resources:
            # Get completed reservations for this resource
            reservations_result = await db.execute(
                select(MakerspaceReservation)
                .where(MakerspaceReservation.resource_id == resource.id)
                .where(MakerspaceReservation.status == MakerspaceReservationStatus.completed)
                .where(MakerspaceReservation.start_time >= start_dt)
                .where(MakerspaceReservation.end_time <= end_dt)
            )
            reservations = reservations_result.scalars().all()

            total_hours_reserved = sum(
                Decimal((r.end_time - r.start_time).total_seconds()) / Decimal(3600)
                for r in reservations
            )

            total_hours_used = sum(
                Decimal((r.checked_out_at - r.checked_in_at).total_seconds()) / Decimal(3600)
                for r in reservations
                if r.checked_in_at and r.checked_out_at
            )

            total_revenue = sum(
                r.actual_cost or r.estimated_cost
                for r in reservations
            )

            # Calculate available hours in period
            total_days = (end_date - start_date).days + 1
            available_days = sum(
                1 for i in range(total_days)
                if (start_date + timedelta(days=i)).weekday() in (resource.available_days or [])
            )

            available_from = datetime.strptime(resource.available_from, "%H:%M")
            available_until = datetime.strptime(resource.available_until, "%H:%M")
            daily_hours = (available_until - available_from).seconds / 3600
            total_available_hours = Decimal(available_days * daily_hours)

            utilization = (
                (total_hours_used / total_available_hours * 100)
                if total_available_hours > 0
                else Decimal("0.00")
            )

            reports.append({
                "resource_id": resource.id,
                "resource_name": resource.name,
                "resource_type": str(resource.resource_type),
                "total_reservations": len(reservations),
                "total_hours_reserved": round(total_hours_reserved, 2),
                "total_hours_used": round(total_hours_used, 2),
                "utilization_percentage": round(utilization, 2),
                "total_revenue": round(total_revenue, 2),
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat()
            })

        return reports

    @staticmethod
    async def get_revenue_report(
        db: AsyncSession,
        start_date: date,
        end_date: date
    ) -> dict:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Get all payments in period
        payments_result = await db.execute(
            select(MakerspacePayment)
            .where(MakerspacePayment.status == PaymentStatus.paid)
            .where(MakerspacePayment.created_at >= start_dt)
            .where(MakerspacePayment.created_at <= end_dt)
        )
        payments = payments_result.scalars().all()

        total_revenue = sum(p.amount - p.refund_amount for p in payments)
        machine_time_revenue = sum(p.machine_time_fee for p in payments)
        consumables_revenue = sum(p.consumables_fee for p in payments)
        setup_fees_revenue = sum(p.setup_fee for p in payments)

        # Get completed reservations grouped by resource type
        reservations_result = await db.execute(
            select(MakerspaceReservation)
            .options(selectinload(MakerspaceReservation.resource))
            .where(MakerspaceReservation.status == MakerspaceReservationStatus.completed)
            .where(MakerspaceReservation.start_time >= start_dt)
            .where(MakerspaceReservation.end_time <= end_dt)
        )
        reservations = reservations_result.scalars().all()

        by_resource_type: dict[str, Decimal] = {}
        for r in reservations:
            if r.resource:
                rtype = str(r.resource.resource_type)
                by_resource_type[rtype] = by_resource_type.get(rtype, Decimal("0.00")) + (
                    r.actual_cost or r.estimated_cost
                )

        # Get revenue by individual resource
        by_resource: list[dict] = []
        resource_revenues: dict[int, Decimal] = {}
        for r in reservations:
            if r.resource:
                resource_revenues[r.resource.id] = resource_revenues.get(
                    r.resource.id, Decimal("0.00")
                ) + (r.actual_cost or r.estimated_cost)

        for resource_id_val, revenue in resource_revenues.items():
            resource_result = await db.execute(
                select(MakerspaceResource).where(MakerspaceResource.id == resource_id_val)
            )
            resource = resource_result.scalar_one_or_none()
            if resource:
                by_resource.append({
                    "resource_id": resource.id,
                    "resource_name": resource.name,
                    "resource_type": str(resource.resource_type),
                    "revenue": round(revenue, 2)
                })

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_revenue": round(total_revenue, 2),
            "machine_time_revenue": round(machine_time_revenue, 2),
            "consumables_revenue": round(consumables_revenue, 2),
            "setup_fees_revenue": round(setup_fees_revenue, 2),
            "certification_fees_revenue": Decimal("0.00"),  # Could be added
            "by_resource_type": {k: round(v, 2) for k, v in by_resource_type.items()},
            "by_resource": sorted(by_resource, key=lambda x: x["revenue"], reverse=True)
        }

    @staticmethod
    async def get_popular_equipment(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        limit: int = 10
    ) -> list[dict]:
        # Import here to avoid circular imports
        from .resource_service import MakerspaceResourceService

        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Aggregate reservations by resource
        result = await db.execute(
            select(
                MakerspaceReservation.resource_id,
                func.count(MakerspaceReservation.id).label("reservation_count"),
                func.sum(
                    func.extract(
                        "epoch",
                        MakerspaceReservation.end_time - MakerspaceReservation.start_time
                    ) / 3600
                ).label("total_hours"),
                func.sum(
                    func.coalesce(
                        MakerspaceReservation.actual_cost,
                        MakerspaceReservation.estimated_cost
                    )
                ).label("total_revenue")
            )
            .where(MakerspaceReservation.status == MakerspaceReservationStatus.completed)
            .where(MakerspaceReservation.start_time >= start_dt)
            .where(MakerspaceReservation.end_time <= end_dt)
            .group_by(MakerspaceReservation.resource_id)
            .order_by(func.count(MakerspaceReservation.id).desc())
            .limit(limit)
        )

        rows = result.all()
        items = []

        for row in rows:
            resource = await MakerspaceResourceService.get_by_id(db, row.resource_id)
            if resource:
                items.append({
                    "resource_id": resource.id,
                    "name": resource.name,
                    "type": str(resource.resource_type),
                    "reservation_count": row.reservation_count,
                    "hours_used": round(float(row.total_hours or 0), 2),
                    "revenue": round(float(row.total_revenue or 0), 2)
                })

        return items

    @staticmethod
    async def get_incident_summary(
        db: AsyncSession,
        start_date: date,
        end_date: date
    ) -> dict:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Get all incidents in period
        incidents_result = await db.execute(
            select(SafetyIncident)
            .options(selectinload(SafetyIncident.resource))
            .where(SafetyIncident.incident_date >= start_dt)
            .where(SafetyIncident.incident_date <= end_dt)
        )
        incidents = incidents_result.scalars().all()

        by_severity = {s.value: 0 for s in MakerspaceIncidentSeverity}
        for incident in incidents:
            by_severity[str(incident.severity)] += 1

        by_resource: dict[int, dict] = {}
        for incident in incidents:
            if incident.resource_id:
                if incident.resource_id not in by_resource:
                    by_resource[incident.resource_id] = {
                        "resource_id": incident.resource_id,
                        "name": incident.resource.name if incident.resource else "Unknown",
                        "count": 0
                    }
                by_resource[incident.resource_id]["count"] += 1

        unresolved_count = sum(1 for i in incidents if not i.is_resolved)

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_incidents": len(incidents),
            "by_severity": by_severity,
            "by_resource": list(by_resource.values()),
            "unresolved_count": unresolved_count
        }
