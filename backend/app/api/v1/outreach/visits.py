# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Outreach Visit scheduling, completion, and cancellation endpoints."""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.logging import get_logger
from ....models.outreach import (
    OutreachPartner, OutreachVisit, VisitStatus
)
from ....models.user import User
from ....schemas.outreach import (
    OutreachVisitCreate, OutreachVisitUpdate, OutreachVisitComplete,
    OutreachVisitCancel, OutreachVisitResponse, OutreachVisitListResponse,
)
from .helpers import require_staff

logger = get_logger(__name__)

router = APIRouter()


@router.post("/visits", response_model=OutreachVisitResponse, status_code=201)
async def schedule_visit(
    visit_data: OutreachVisitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Schedule a new outreach visit."""
    # Verify partner exists
    partner_query = select(OutreachPartner).where(OutreachPartner.id == visit_data.partner_id)
    partner = (await db.execute(partner_query)).scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    visit = OutreachVisit(
        **visit_data.model_dump(),
        status=VisitStatus.SCHEDULED.value,
        created_by_id=current_user.id
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)

    logger.info(f"Scheduled outreach visit: {visit.title}",
                extra={"visit_id": visit.id, "partner_id": visit_data.partner_id})

    response = OutreachVisitResponse.model_validate(visit)
    response.partner_name = partner.name
    return response


@router.get("/visits", response_model=OutreachVisitListResponse)
async def list_visits(
    partner_id: Optional[int] = None,
    status: Optional[VisitStatus] = None,
    visit_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    lead_staff_id: Optional[int] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """List outreach visits with filtering options."""
    query = select(OutreachVisit).options(
        selectinload(OutreachVisit.partner),
        selectinload(OutreachVisit.lead_staff)
    )

    if partner_id:
        query = query.where(OutreachVisit.partner_id == partner_id)
    if status:
        query = query.where(OutreachVisit.status == status.value)
    if visit_type:
        query = query.where(OutreachVisit.visit_type == visit_type)
    if start_date:
        query = query.where(OutreachVisit.scheduled_date >= start_date)
    if end_date:
        query = query.where(OutreachVisit.scheduled_date <= end_date)
    if lead_staff_id:
        query = query.where(OutreachVisit.lead_staff_id == lead_staff_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(OutreachVisit.scheduled_date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    visits = result.scalars().all()

    visit_responses = []
    for v in visits:
        response = OutreachVisitResponse.model_validate(v)
        response.partner_name = v.partner.name if v.partner else None
        response.lead_staff_name = v.lead_staff.full_name if v.lead_staff else None
        visit_responses.append(response)

    return OutreachVisitListResponse(
        visits=visit_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/visits/{visit_id}", response_model=OutreachVisitResponse)
async def get_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get details of a specific outreach visit."""
    query = select(OutreachVisit).options(
        selectinload(OutreachVisit.partner),
        selectinload(OutreachVisit.lead_staff)
    ).where(OutreachVisit.id == visit_id)

    result = await db.execute(query)
    visit = result.scalar_one_or_none()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    response = OutreachVisitResponse.model_validate(visit)
    response.partner_name = visit.partner.name if visit.partner else None
    response.lead_staff_name = visit.lead_staff.full_name if visit.lead_staff else None
    return response


@router.patch("/visits/{visit_id}", response_model=OutreachVisitResponse)
async def update_visit(
    visit_id: int,
    update_data: OutreachVisitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Update an outreach visit."""
    query = select(OutreachVisit).options(
        selectinload(OutreachVisit.partner)
    ).where(OutreachVisit.id == visit_id)
    result = await db.execute(query)
    visit = result.scalar_one_or_none()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if field == "status" and value:
            setattr(visit, field, value.value)
        else:
            setattr(visit, field, value)

    await db.commit()
    await db.refresh(visit)

    response = OutreachVisitResponse.model_validate(visit)
    response.partner_name = visit.partner.name if visit.partner else None
    return response


@router.post("/visits/{visit_id}/complete", response_model=OutreachVisitResponse)
async def complete_visit(
    visit_id: int,
    completion_data: OutreachVisitComplete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Mark a visit as completed with outcome data."""
    query = select(OutreachVisit).options(
        selectinload(OutreachVisit.partner)
    ).where(OutreachVisit.id == visit_id)
    result = await db.execute(query)
    visit = result.scalar_one_or_none()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    if visit.status == VisitStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Visit is already completed")

    # Update with completion data
    for field, value in completion_data.model_dump(exclude_unset=True).items():
        setattr(visit, field, value)

    visit.status = VisitStatus.COMPLETED.value
    if not visit.actual_end_time:
        visit.actual_end_time = datetime.now()

    await db.commit()
    await db.refresh(visit)

    logger.info(f"Completed outreach visit: {visit.title}",
                extra={"visit_id": visit_id, "attendees": visit.actual_attendees})

    response = OutreachVisitResponse.model_validate(visit)
    response.partner_name = visit.partner.name if visit.partner else None
    return response


@router.post("/visits/{visit_id}/cancel", response_model=OutreachVisitResponse)
async def cancel_visit(
    visit_id: int,
    cancel_data: OutreachVisitCancel,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Cancel an outreach visit."""
    query = select(OutreachVisit).options(
        selectinload(OutreachVisit.partner)
    ).where(OutreachVisit.id == visit_id)
    result = await db.execute(query)
    visit = result.scalar_one_or_none()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    if visit.status in [VisitStatus.COMPLETED.value, VisitStatus.CANCELLED.value]:
        raise HTTPException(status_code=400, detail="Visit cannot be cancelled")

    visit.status = VisitStatus.CANCELLED.value
    visit.cancellation_reason = cancel_data.cancellation_reason
    visit.cancelled_by_id = current_user.id
    visit.cancelled_at = datetime.now()

    # Create rescheduled visit if requested
    if cancel_data.reschedule_date:
        visit.status = VisitStatus.RESCHEDULED.value
        new_visit = OutreachVisit(
            partner_id=visit.partner_id,
            visit_type=visit.visit_type,
            title=visit.title,
            description=visit.description,
            scheduled_date=cancel_data.reschedule_date,
            scheduled_start_time=visit.scheduled_start_time,
            scheduled_end_time=visit.scheduled_end_time,
            location_name=visit.location_name,
            location_room=visit.location_room,
            location_address=visit.location_address,
            expected_attendees=visit.expected_attendees,
            age_group=visit.age_group,
            lead_staff_id=visit.lead_staff_id,
            materials_needed=visit.materials_needed,
            parent_visit_id=visit.id,
            created_by_id=current_user.id,
            status=VisitStatus.SCHEDULED.value
        )
        db.add(new_visit)
        visit.next_visit_date = cancel_data.reschedule_date

    await db.commit()
    await db.refresh(visit)

    logger.info(f"Cancelled outreach visit: {visit.title}",
                extra={"visit_id": visit_id, "rescheduled": cancel_data.reschedule_date is not None})

    response = OutreachVisitResponse.model_validate(visit)
    response.partner_name = visit.partner.name if visit.partner else None
    return response
