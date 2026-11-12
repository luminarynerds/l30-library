# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import secrets
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.makerspace import (
    SafetyIncident,
    MakerspaceIncidentSeverity,
)
from .base_service import BaseMakerspaceService

logger = get_logger(__name__)


class SafetyIncidentService(BaseMakerspaceService[SafetyIncident]):

    model = SafetyIncident

    @staticmethod
    def _generate_incident_number() -> str:
        return f"INC-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

    @staticmethod
    async def get_incidents(
        db: AsyncSession,
        *,
        resource_id: int | None = None,
        severity: MakerspaceIncidentSeverity | None = None,
        is_resolved: bool | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[list[SafetyIncident], int]:
        query = select(SafetyIncident)
        count_query = select(func.count(SafetyIncident.id))

        if resource_id:
            query = query.where(SafetyIncident.resource_id == resource_id)
            count_query = count_query.where(SafetyIncident.resource_id == resource_id)

        if severity:
            query = query.where(SafetyIncident.severity == severity)
            count_query = count_query.where(SafetyIncident.severity == severity)

        if is_resolved is not None:
            query = query.where(SafetyIncident.is_resolved == is_resolved)
            count_query = count_query.where(SafetyIncident.is_resolved == is_resolved)

        if start_date:
            start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            query = query.where(SafetyIncident.incident_date >= start_dt)
            count_query = count_query.where(SafetyIncident.incident_date >= start_dt)

        if end_date:
            end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
            query = query.where(SafetyIncident.incident_date <= end_dt)
            count_query = count_query.where(SafetyIncident.incident_date <= end_dt)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = (
            query
            .options(selectinload(SafetyIncident.resource))
            .offset(offset)
            .limit(per_page)
            .order_by(SafetyIncident.incident_date.desc())
        )

        result = await db.execute(query)
        incidents = list(result.scalars().all())

        return incidents, total

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        incident_id: int
    ) -> SafetyIncident | None:
        result = await db.execute(
            select(SafetyIncident)
            .options(selectinload(SafetyIncident.resource))
            .where(SafetyIncident.id == incident_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        reported_by_id: int,
        data: dict
    ) -> SafetyIncident:
        incident = SafetyIncident(
            incident_number=SafetyIncidentService._generate_incident_number(),
            reported_by_id=reported_by_id,
            **data
        )
        db.add(incident)
        await db.commit()
        await db.refresh(incident)

        logger.warning(
            f"Safety incident reported: {incident.incident_number} - "
            f"Severity: {incident.severity}, Resource: {incident.resource_id}"
        )
        return incident

    @staticmethod
    async def update(
        db: AsyncSession,
        incident: SafetyIncident,
        data: dict
    ) -> SafetyIncident:
        for key, value in data.items():
            if value is not None:
                setattr(incident, key, value)
        await db.commit()
        await db.refresh(incident)
        return incident

    @staticmethod
    async def resolve(
        db: AsyncSession,
        incident: SafetyIncident,
        resolved_by_id: int,
        notes: str | None = None
    ) -> SafetyIncident:
        incident.is_resolved = True
        incident.resolved_at = datetime.now(timezone.utc)
        incident.resolved_by_id = resolved_by_id
        if notes:
            incident.follow_up_notes = (incident.follow_up_notes or "") + f"\nResolution: {notes}"

        await db.commit()
        await db.refresh(incident)
        return incident
