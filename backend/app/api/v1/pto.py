# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
PTO Management API endpoints

Routes:
- GET /pto/balance - Get user's PTO balance
- GET /pto/reminders - Get PTO reminders
- POST /pto/requests - Create PTO request
- GET /pto/requests - List PTO requests
- GET /pto/requests/{id} - Get specific request
- PUT /pto/requests/{id} - Update request
- POST /pto/requests/{id}/approve - Approve request
- POST /pto/requests/{id}/deny - Deny request
- GET /pto/upcoming - Get upcoming approved PTO
- POST /pto/requests/{id}/celebrate - Create vacation celebration
- GET /pto/requests/{id}/delegation - Get delegation info
- GET /pto/requests/{id}/inbox-return - Get gradual inbox return schedule
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from .dependencies import get_current_user, require_staff
from app.models.user import User
from app.models.pto import PTOType, PTORequestStatus
from app.services.pto_service import PTOService
from app.schemas.pto import (
    PTORequestCreate, PTORequestUpdate, PTORequestResponse,
    PTOBalanceResponse, PTOApprovalRequest, PTOReminderResponse,
    PTOVacationCelebrationResponse, PTODelegationResponse,
    PTOInboxReturnResponse,
)

router = APIRouter(prefix="/pto", tags=["pto"])


@router.post("/requests", response_model=PTORequestResponse)
async def create_pto_request(
    request_data: PTORequestCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new PTO request"""
    try:
        pto_request = await PTOService.create_pto_request(
            db=db,
            user_id=staff_user.id,
            start_date=request_data.start_date,
            end_date=request_data.end_date,
            pto_type=request_data.pto_type,
            reason=request_data.reason,
            coverage_notes=request_data.coverage_notes,
            delegation_notes=request_data.delegation_notes,
            auto_delegate=request_data.auto_delegate,
            gradual_return_enabled=request_data.gradual_return_enabled,
        )
        return pto_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/balance", response_model=List[PTOBalanceResponse])
async def get_pto_balance(
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get current PTO balance for user"""
    from app.models.pto import PTOBalance
    result = await db.execute(
        select(PTOBalance).where(PTOBalance.user_id == staff_user.id)
    )
    balances = result.scalars().all()
    return balances


@router.get("/reminders", response_model=List[PTOReminderResponse])
async def get_pto_reminders(
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
    unread_only: bool = Query(False),
):
    """Get PTO reminders for user"""
    from app.models.pto import PTOReminder
    stmt = select(PTOReminder).where(PTOReminder.user_id == staff_user.id)

    if unread_only:
        stmt = stmt.where(PTOReminder.read_at.is_(None))

    result = await db.execute(stmt.order_by(PTOReminder.sent_at.desc()))
    return result.scalars().all()


@router.get("/requests", response_model=List[PTORequestResponse])
async def list_pto_requests(
    status: Optional[PTORequestStatus] = None,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List PTO requests for current user"""
    stmt = select(PTORequest).where(PTORequest.user_id == staff_user.id)

    if status:
        stmt = stmt.where(PTORequest.status == status)

    result = await db.execute(stmt.order_by(PTORequest.start_date.desc()))
    return result.scalars().all()


@router.get("/requests/{request_id}", response_model=PTORequestResponse)
async def get_pto_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get a specific PTO request"""
    from app.models.pto import PTORequest
    result = await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )
    request = result.scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if request.user_id != staff_user.id and request.coverage_manager_assigned != staff_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this request")

    return request


@router.put("/requests/{request_id}", response_model=PTORequestResponse)
async def update_pto_request(
    request_id: int,
    request_data: PTORequestUpdate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Update a PTO request (only if draft/submitted)"""
    from app.models.pto import PTORequest
    result = await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )
    request = result.scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if request.user_id != staff_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this request")

    if request.status not in [PTORequestStatus.DRAFT, PTORequestStatus.SUBMITTED]:
        raise HTTPException(status_code=400, detail="Cannot update approved or denied requests")

    # Update fields
    if request_data.start_date:
        request.start_date = request_data.start_date
    if request_data.end_date:
        request.end_date = request_data.end_date
    if request_data.reason is not None:
        request.reason = request_data.reason
    if request_data.delegation_notes is not None:
        request.delegation_notes = request_data.delegation_notes
    if request_data.auto_delegate is not None:
        request.auto_delegate = request_data.auto_delegate

    await db.flush()
    await db.refresh(request)
    return request


@router.post("/requests/{request_id}/approve", response_model=PTORequestResponse)
async def approve_pto_request(
    request_id: int,
    approval_data: PTOApprovalRequest,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Approve a PTO request (manager only)"""
    from app.models.pto import PTORequest
    result = await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )
    request = result.scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    # Check if current user is manager/has approval rights
    if not hasattr(staff_user, "is_manager") or not staff_user.is_manager:
        raise HTTPException(status_code=403, detail="Not authorized to approve PTO requests")

    try:
        approved_request = await PTOService.approve_pto_request(
            db=db,
            request_id=request_id,
            approver_id=staff_user.id,
            coverage_assessment=approval_data.coverage_assessment,
            notes=approval_data.notes,
        )
        # Create celebration
        await PTOService.create_vacation_celebration(db, request_id)

        return approved_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/requests/{request_id}/deny", response_model=PTORequestResponse)
async def deny_pto_request(
    request_id: int,
    denial_data: PTOApprovalRequest,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Deny a PTO request with reason (manager only)"""
    from app.models.pto import PTORequest
    result = await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )
    request = result.scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if not hasattr(staff_user, "is_manager") or not staff_user.is_manager:
        raise HTTPException(status_code=403, detail="Not authorized to deny PTO requests")

    try:
        denied_request = await PTOService.deny_pto_request(
            db=db,
            request_id=request_id,
            approver_id=staff_user.id,
            denial_reason=denial_data.notes or "Not provided",
            notes=denial_data.coverage_assessment,
        )
        return denied_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/upcoming", response_model=List[PTORequestResponse])
async def get_upcoming_pto(
    days_ahead: int = Query(30),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get upcoming approved PTO for team coordination"""
    return await PTOService.get_upcoming_pto(db, days_ahead)


@router.post("/requests/{request_id}/celebrate", response_model=PTOVacationCelebrationResponse)
async def celebrate_vacation(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create vacation celebration message"""
    from app.models.pto import PTOVacationCelebration
    result = await db.execute(
        select(PTOVacationCelebration).where(
            PTOVacationCelebration.pto_request_id == request_id
        )
    )
    existing = result.scalars().first()

    if existing:
        return existing

    try:
        celebration = await PTOService.create_vacation_celebration(db, request_id)
        return celebration
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/requests/{request_id}/delegation", response_model=PTODelegationResponse)
async def get_delegation_info(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get delegation information for coverage while away"""
    from app.models.pto import PTORequest
    result = await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )
    request = result.scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if request.user_id != staff_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return await PTOService.get_delegation_handoff(db, request_id)


@router.get("/requests/{request_id}/inbox-return", response_model=PTOInboxReturnResponse)
async def get_inbox_return_schedule(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get gradual inbox return schedule"""
    from app.models.pto import PTORequest
    result = await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )
    request = result.scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if request.user_id != staff_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return await PTOService.get_gradual_inbox_return_schedule(db, request_id)


@router.get("/calendar")
async def get_pto_calendar(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    Get calendar view of PTO with coverage information.
    Shows own PTO and team awareness of who's off.
    """
    from app.models.pto import PTORequest
    from sqlalchemy import and_

    # Get all approved PTO requests in date range
    stmt = select(PTORequest).where(
        and_(
            PTORequest.status == PTORequestStatus.APPROVED,
            PTORequest.start_date <= end_date,
            PTORequest.end_date >= start_date,
        )
    ).order_by(PTORequest.start_date)

    result = await db.execute(stmt)
    requests = result.scalars().all()

    # Format calendar data
    calendar_data = {}
    for request in requests:
        current = request.start_date
        while current <= request.end_date:
            date_str = current.isoformat()
            if date_str not in calendar_data:
                calendar_data[date_str] = []
            calendar_data[date_str].append({
                "id": request.id,
                "user_id": request.user_id,
                "user_name": request.user.full_name if request.user else "Unknown",
                "pto_type": str(request.pto_type),
                "partial_day_type": str(request.partial_day_type),
                "coverage_assigned": request.coverage_manager_assigned is not None,
            })
            current += timedelta(days=1)

    return {
        "calendar": calendar_data,
        "total_requests": len(requests),
    }


@router.get("/conflicts")
async def check_pto_conflicts(
    start_date: date = Query(...),
    end_date: date = Query(...),
    partial_day_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    Check for conflicts with existing PTO requests before submitting.
    Returns list of conflicting requests and suggestions.
    """
    from app.models.pto import PTORequest, PartialDayType
    from sqlalchemy import and_, or_

    # Find overlapping approved/submitted requests for same user
    stmt = select(PTORequest).where(
        and_(
            PTORequest.user_id == staff_user.id,
            PTORequest.status.in_([PTORequestStatus.APPROVED, PTORequestStatus.SUBMITTED]),
            PTORequest.start_date <= end_date,
            PTORequest.end_date >= start_date,
        )
    )

    result = await db.execute(stmt)
    conflicting = result.scalars().all()

    conflicts = []
    for req in conflicting:
        # Check if partial day overlaps
        overlap = True
        if partial_day_type == "morning_off" and req.partial_day_type == PartialDayType.LEAVE_EARLY:
            overlap = False  # No conflict
        elif partial_day_type == "leave_early" and req.partial_day_type == PartialDayType.MORNING_OFF:
            overlap = False  # No conflict

        if overlap:
            conflicts.append({
                "id": req.id,
                "start_date": req.start_date.isoformat(),
                "end_date": req.end_date.isoformat(),
                "pto_type": str(req.pto_type),
                "status": str(req.status),
            })

    return {
        "has_conflicts": len(conflicts) > 0,
        "conflicts": conflicts,
        "message": f"Found {len(conflicts)} overlapping request(s)" if conflicts else "No conflicts detected",
    }


@router.get("/team-coverage")
async def get_team_coverage(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    See who else is already off that day for team awareness.
    Helps identify who to coordinate with.
    """
    from app.models.pto import PTORequest
    from sqlalchemy import and_

    # Get all approved PTO in date range (excluding current user)
    stmt = select(PTORequest).where(
        and_(
            PTORequest.user_id != staff_user.id,
            PTORequest.status == PTORequestStatus.APPROVED,
            PTORequest.start_date <= end_date,
            PTORequest.end_date >= start_date,
        )
    ).order_by(PTORequest.start_date)

    result = await db.execute(stmt)
    team_pto = result.scalars().all()

    coverage_info = []
    for req in team_pto:
        coverage_info.append({
            "user_id": req.user_id,
            "user_name": req.user.full_name if req.user else "Unknown",
            "start_date": req.start_date.isoformat(),
            "end_date": req.end_date.isoformat(),
            "pto_type": str(req.pto_type),
            "coverage_assigned": req.coverage_manager_assigned is not None,
        })

    return {
        "team_members_off": coverage_info,
        "total_out": len(coverage_info),
    }


@router.delete("/requests/{request_id}")
async def cancel_pto_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Cancel a pending PTO request"""
    from app.models.pto import PTORequest

    result = await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )
    request = result.scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if request.user_id != staff_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this request")

    if request.status not in [PTORequestStatus.DRAFT, PTORequestStatus.SUBMITTED]:
        raise HTTPException(status_code=400, detail="Can only cancel draft or submitted requests")

    request.status = PTORequestStatus.CANCELLED
    await db.flush()
    await db.commit()

    return {"success": True, "message": "PTO request cancelled"}


# Import models
from app.models.pto import PTORequest
from datetime import timedelta
