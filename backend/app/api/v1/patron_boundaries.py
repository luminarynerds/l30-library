# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Boundary Management API

API for managing patron boundaries, out-of-scope requests, templates, and escalations.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from .dependencies import require_staff, require_admin, get_current_user
from ...models.patron_boundaries import (
    AppealStatus,
    BoundaryEscalation,
    BoundaryPolicy,
    BoundaryStatus,
    BoundaryTemplate,
    BoundaryType,
    EscalationLevel,
    OutOfScopeRequest,
    PatronBoundary,
    UnreasonableDemandLog,
)
from ...models.user import User

router = APIRouter()


# Patron-facing endpoints
@router.get("/boundaries/my-boundaries")
async def get_my_boundaries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active boundaries for the current patron"""
    result = await db.execute(
        select(PatronBoundary).where(
            and_(
                PatronBoundary.patron_id == current_user.id,
                PatronBoundary.is_deleted == False,
                PatronBoundary.status.in_([BoundaryStatus.ACTIVE, BoundaryStatus.UNDER_REVIEW]),
            )
        )
    )
    boundaries = result.scalars().all()

    return {
        "boundaries": [
            {
                "id": b.id,
                "type": b.boundary_type,
                "title": b.title,
                "description": b.description,
                "status": b.status,
                "start_date": b.start_date.isoformat() if b.start_date else None,
                "end_date": b.end_date.isoformat() if b.end_date else None,
                "can_appeal": b.can_appeal,
            }
            for b in boundaries
        ]
    }


# Staff endpoints
@router.post("/staff/patron-boundaries")
async def create_patron_boundary(
    patron_id: int,
    boundary_type: BoundaryType,
    title: str,
    description: str,
    specific_restrictions: Optional[dict] = None,
    end_date: Optional[datetime] = None,
    is_permanent: bool = False,
    supporting_evidence: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new patron boundary (staff only)"""
    boundary = PatronBoundary(
        organization_id=(current_user.home_library_system_id or 1),
        patron_id=patron_id,
        boundary_type=boundary_type,
        title=title,
        description=description,
        specific_restrictions=specific_restrictions,
        end_date=end_date,
        is_permanent=is_permanent,
        supporting_evidence=supporting_evidence,
        created_by_id=current_user.id,
        status=BoundaryStatus.PENDING_APPROVAL,
    )

    db.add(boundary)
    await db.commit()
    await db.refresh(boundary)

    return {
        "message": "Boundary created",
        "boundary": {
            "id": boundary.id,
            "patron_id": boundary.patron_id,
            "type": boundary.boundary_type,
            "title": boundary.title,
            "status": boundary.status,
        },
    }


@router.get("/staff/patron-boundaries")
async def list_patron_boundaries(
    patron_id: Optional[int] = Query(None),
    status: Optional[BoundaryStatus] = Query(None),
    boundary_type: Optional[BoundaryType] = Query(None),
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List patron boundaries with filtering (staff only)"""
    query = select(PatronBoundary).where(
        PatronBoundary.organization_id == (current_user.home_library_system_id or 1)
    )

    if not include_deleted:
        query = query.where(PatronBoundary.is_deleted == False)
    if patron_id:
        query = query.where(PatronBoundary.patron_id == patron_id)
    if status:
        query = query.where(PatronBoundary.status == status)
    if boundary_type:
        query = query.where(PatronBoundary.boundary_type == boundary_type)

    query = query.order_by(PatronBoundary.created_at.desc())

    result = await db.execute(query)
    boundaries = result.scalars().all()

    return {
        "boundaries": [
            {
                "id": b.id,
                "patron_id": b.patron_id,
                "type": b.boundary_type,
                "title": b.title,
                "description": b.description,
                "status": b.status,
                "start_date": b.start_date.isoformat() if b.start_date else None,
                "end_date": b.end_date.isoformat() if b.end_date else None,
                "incident_count": b.incident_count,
                "created_by_id": b.created_by_id,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in boundaries
        ]
    }


@router.post("/staff/out-of-scope-requests")
async def log_out_of_scope_request(
    patron_id: int,
    request_description: str,
    why_out_of_scope: str,
    request_category: Optional[str] = None,
    policy_reference: Optional[str] = None,
    how_declined: Optional[str] = None,
    patron_reaction: Optional[str] = None,
    required_escalation: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Log an out-of-scope request to track patterns (staff only)"""
    # Check for related requests (pattern detection)
    prev_requests = await db.execute(
        select(OutOfScopeRequest).where(
            and_(
                OutOfScopeRequest.patron_id == patron_id,
                OutOfScopeRequest.request_category == request_category,
            )
        )
    )
    related_count = len(prev_requests.scalars().all())

    request = OutOfScopeRequest(
        organization_id=(current_user.home_library_system_id or 1),
        patron_id=patron_id,
        staff_member_id=current_user.id,
        request_description=request_description,
        why_out_of_scope=why_out_of_scope,
        request_category=request_category,
        policy_reference=policy_reference,
        how_declined=how_declined,
        patron_reaction=patron_reaction,
        required_escalation=required_escalation,
        is_repeat_request=related_count > 0,
        related_request_count=related_count,
    )

    db.add(request)
    await db.commit()
    await db.refresh(request)

    return {
        "message": "Out-of-scope request logged",
        "request": {
            "id": request.id,
            "patron_id": request.patron_id,
            "request_category": request.request_category,
            "is_repeat_request": request.is_repeat_request,
            "related_request_count": request.related_request_count,
        },
    }


@router.post("/staff/unreasonable-demands")
async def log_unreasonable_demand(
    patron_id: int,
    demand_description: str,
    unreasonable_reasons: Optional[list] = None,
    evidence_links: Optional[list] = None,
    emotional_impact_level: Optional[int] = Query(None, ge=1, le=5),
    time_wasted_minutes: Optional[int] = None,
    required_manager_intervention: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Log an unreasonable demand with evidence and impact tracking (staff only)"""
    log = UnreasonableDemandLog(
        organization_id=(current_user.home_library_system_id or 1),
        patron_id=patron_id,
        staff_member_id=current_user.id,
        demand_description=demand_description,
        unreasonable_reasons=unreasonable_reasons,
        evidence_links=evidence_links,
        emotional_impact_level=emotional_impact_level,
        time_wasted_minutes=time_wasted_minutes,
        required_manager_intervention=required_manager_intervention,
    )

    db.add(log)
    await db.commit()
    await db.refresh(log)

    return {
        "message": "Unreasonable demand logged",
        "log": {
            "id": log.id,
            "patron_id": log.patron_id,
            "incident_date": log.incident_date.isoformat() if log.incident_date else None,
            "emotional_impact_level": log.emotional_impact_level,
            "required_manager_intervention": log.required_manager_intervention,
        },
    }


@router.post("/staff/patron-boundaries/{boundary_id}/escalate")
async def escalate_boundary(
    boundary_id: int,
    to_level: EscalationLevel,
    reason: str,
    escalated_to_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Escalate a boundary to a higher authority level (staff/manager only)"""
    # Get the boundary
    boundary = await get_or_404(db, PatronBoundary, boundary_id, "Boundary not found")

    # Determine from_level based on current user role
    from_level = EscalationLevel.STAFF  # Simplified - would check actual role

    escalation = BoundaryEscalation(
        boundary_id=boundary_id,
        organization_id=(current_user.home_library_system_id or 1),
        from_level=from_level,
        to_level=to_level,
        reason=reason,
        escalated_by_id=current_user.id,
        escalated_to_id=escalated_to_id,
    )

    db.add(escalation)
    boundary.status = BoundaryStatus.ESCALATED
    await db.commit()
    await db.refresh(escalation)

    return {
        "message": "Boundary escalated",
        "escalation": {
            "id": escalation.id,
            "from_level": escalation.from_level,
            "to_level": escalation.to_level,
            "created_at": escalation.created_at.isoformat() if escalation.created_at else None,
        },
    }


@router.get("/staff/patron-boundaries/analytics")
async def get_boundary_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get analytics and pattern analysis for boundaries (director only)"""
    # This would be restricted to director role in production
    query = select(PatronBoundary).where(
        PatronBoundary.organization_id == (current_user.home_library_system_id or 1)
    )

    if start_date:
        query = query.where(PatronBoundary.created_at >= start_date)
    if end_date:
        query = query.where(PatronBoundary.created_at <= end_date)

    result = await db.execute(query)
    boundaries = result.scalars().all()

    # Calculate analytics
    total_boundaries = len(boundaries)
    by_type = {}
    by_status = {}

    for b in boundaries:
        by_type[b.boundary_type] = by_type.get(b.boundary_type, 0) + 1
        by_status[b.status] = by_status.get(b.status, 0) + 1

    return {
        "summary": {
            "total_boundaries": total_boundaries,
            "by_type": by_type,
            "by_status": by_status,
        },
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    }
