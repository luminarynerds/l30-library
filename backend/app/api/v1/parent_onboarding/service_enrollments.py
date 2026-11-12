# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding – Service Enrollments API

Pure move from _legacy.py. Three route handlers:
  GET  /service-enrollments
  POST /service-enrollments
  PATCH /service-enrollments/{enrollment_id}
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.parent_onboarding import ServiceEnrollmentFacilitation
from ....models.user import User
from ....schemas.parent_onboarding import (
    ServiceEnrollmentCreate, ServiceEnrollmentListResponse,
    ServiceEnrollmentResponse, ServiceEnrollmentUpdate,
)
from ....services.parent_onboarding import ServiceEnrollmentService
from ..dependencies import require_authenticated, require_staff

router = APIRouter()


@router.post("/service-enrollments", response_model=ServiceEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def create_service_enrollment(
    data: ServiceEnrollmentCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Start a service enrollment facilitation (staff-only)."""
    enrollment = await ServiceEnrollmentService.create_enrollment(db, data.model_dump())
    return ServiceEnrollmentResponse.model_validate(enrollment)


@router.get("/service-enrollments", response_model=ServiceEnrollmentListResponse)
async def list_service_enrollments(
    patron_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List service enrollments."""
    enrollments, total = await ServiceEnrollmentService.list_enrollments(
        db, patron_id=patron_id, status=status_filter,
        limit=limit, offset=offset,
    )
    return ServiceEnrollmentListResponse(
        enrollments=[ServiceEnrollmentResponse.model_validate(e) for e in enrollments],
        total=total, limit=limit, offset=offset,
    )


@router.patch("/service-enrollments/{enrollment_id}", response_model=ServiceEnrollmentResponse)
async def update_service_enrollment(
    enrollment_id: int,
    data: ServiceEnrollmentUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a service enrollment (staff-only)."""
    result = await db.execute(
        select(ServiceEnrollmentFacilitation).where(ServiceEnrollmentFacilitation.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(enrollment, key, value)
    await db.flush()
    await db.refresh(enrollment)
    return ServiceEnrollmentResponse.model_validate(enrollment)
