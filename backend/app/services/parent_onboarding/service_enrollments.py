# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding – Service Enrollment and Partner Agency services.

Pure move from _legacy.py.
"""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.parent_onboarding import (
    EnrollmentFacilitationStatus, PartnerAgency, ServiceEnrollmentFacilitation,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ServiceEnrollmentService:

    @staticmethod
    async def create_enrollment(
        db: AsyncSession, data: dict
    ) -> ServiceEnrollmentFacilitation:
        enrollment = ServiceEnrollmentFacilitation(**data)
        db.add(enrollment)
        await db.flush()
        await db.refresh(enrollment)
        logger.info("Created service enrollment %s for patron %s", enrollment.id, data.get("patron_id"))
        return enrollment

    @staticmethod
    async def list_enrollments(
        db: AsyncSession,
        *,
        patron_id: Optional[int] = None,
        status: Optional[EnrollmentFacilitationStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ServiceEnrollmentFacilitation], int]:
        query = select(ServiceEnrollmentFacilitation)
        count_query = select(func.count(ServiceEnrollmentFacilitation.id))

        if patron_id:
            query = query.where(ServiceEnrollmentFacilitation.patron_id == patron_id)
            count_query = count_query.where(ServiceEnrollmentFacilitation.patron_id == patron_id)
        if status:
            query = query.where(ServiceEnrollmentFacilitation.status == status)
            count_query = count_query.where(ServiceEnrollmentFacilitation.status == status)

        total = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(ServiceEnrollmentFacilitation.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all()), total


class PartnerAgencyService:

    @staticmethod
    async def search(
        db: AsyncSession,
        *,
        q: Optional[str] = None,
        limit: int = 20,
    ) -> list[PartnerAgency]:
        query = select(PartnerAgency).where(PartnerAgency.is_active.is_(True))
        if q:
            # ilike on both name and slug -- agencies are often referenced
            # both ways ("WIC" vs "eastside-wic-clinic"). Cap at 20 results;
            # this is an autocomplete, not a report.
            pattern = f"%{q.strip()}%"
            query = query.where(
                (PartnerAgency.name.ilike(pattern))
                | (PartnerAgency.slug.ilike(pattern))
            )
        query = query.order_by(PartnerAgency.name).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get(db: AsyncSession, agency_id: int) -> Optional[PartnerAgency]:
        result = await db.execute(
            select(PartnerAgency).where(PartnerAgency.id == agency_id)
        )
        return result.scalar_one_or_none()
