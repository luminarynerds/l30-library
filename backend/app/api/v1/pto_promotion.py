# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
PTO Promotion API Endpoints

Routes for PTO promotion features:
- GET /pto-promotion/dashboard - Get promotion dashboard
- POST /pto-promotion/send-balance-reminder - Send balance reminder
- POST /pto-promotion/send-planning-encouragement - Send planning encouragement
- POST /pto-promotion/send-coverage-messageable - Send coverage manageable message
- POST /pto-promotion/send-no-guilt - Send no guilt message
- POST /pto-promotion/send-strength-message - Send time off is strength message
- GET /pto-promotion/pre-vacation-triage/{request_id} - Get pre-vacation triage plan
- POST /pto-promotion/enable-auto-delegation/{request_id} - Enable auto-delegation
- GET /pto-promotion/gradual-return/{request_id} - Get gradual return plan
- POST /pto-promotion/create-celebration/{request_id} - Create celebration
- POST /pto-promotion/send-welcome-back/{request_id} - Send welcome back message
- POST /pto-promotion/batch-send-reminders - Send batch reminders (admin only)
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .dependencies import get_current_user
from app.models.user import User
from app.models.pto import PTOType, PTORequestStatus
from app.services.pto_promotion_service import PTOPromotionService
from app.schemas.pto import (
    PTOReminderResponse, PTOPromotionDashboardResponse,
    PTOPromotionTriageResponse, PTOPromotionGradualReturnResponse,
    PTOVacationCelebrationResponse,
)

router = APIRouter(prefix="/pto-promotion", tags=["pto-promotion"])


@router.get("/dashboard", response_model=PTOPromotionDashboardResponse)
async def get_promotion_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get PTO promotion dashboard for current user"""
    try:
        dashboard = await PTOPromotionService.get_promotion_dashboard(db, current_user.id)
        return dashboard
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/send-balance-reminder", response_model=PTOReminderResponse)
async def send_balance_reminder(
    pto_type: PTOType = Query(PTOType.VACATION),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a balance reminder to user.
    Message: "You have X days to use"
    """
    # Non-admins can only send to themselves
    target_user_id = user_id if user_id and hasattr(current_user, "is_admin") and current_user.is_admin else current_user.id

    try:
        reminder = await PTOPromotionService.send_balance_reminder(
            db=db,
            user_id=target_user_id,
            pto_type=pto_type,
        )
        if not reminder:
            raise HTTPException(status_code=400, detail="No available PTO days for reminder")
        await db.commit()
        return reminder
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/send-planning-encouragement", response_model=PTOReminderResponse)
async def send_planning_encouragement(
    pto_type: PTOType = Query(PTOType.VACATION),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send planning encouragement message.
    Message: "Plan ahead! Taking time off ensures smooth coverage..."
    """
    target_user_id = user_id if user_id and hasattr(current_user, "is_admin") and current_user.is_admin else current_user.id

    try:
        reminder = await PTOPromotionService.send_planning_encouragement(
            db=db,
            user_id=target_user_id,
            pto_type=pto_type,
        )
        if not reminder:
            raise HTTPException(status_code=400, detail="No available PTO days for reminder")
        await db.commit()
        return reminder
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/send-coverage-manageable", response_model=PTOReminderResponse)
async def send_coverage_manageable(
    pto_type: PTOType = Query(PTOType.VACATION),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send coverage is manageable message.
    Helps reduce guilt about taking time off.
    """
    target_user_id = user_id if user_id and hasattr(current_user, "is_admin") and current_user.is_admin else current_user.id

    try:
        reminder = await PTOPromotionService.send_coverage_manageable_message(
            db=db,
            user_id=target_user_id,
            pto_type=pto_type,
        )
        if not reminder:
            raise HTTPException(status_code=400, detail="No available PTO days for reminder")
        await db.commit()
        return reminder
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/send-no-guilt", response_model=PTOReminderResponse)
async def send_no_guilt_message(
    pto_type: PTOType = Query(PTOType.VACATION),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send no guilt message.
    Message: "Taking time off is essential, not a luxury"
    """
    target_user_id = user_id if user_id and hasattr(current_user, "is_admin") and current_user.is_admin else current_user.id

    try:
        reminder = await PTOPromotionService.send_no_guilt_message(
            db=db,
            user_id=target_user_id,
            pto_type=pto_type,
        )
        if not reminder:
            raise HTTPException(status_code=400, detail="No available PTO days for reminder")
        await db.commit()
        return reminder
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/send-strength-message", response_model=PTOReminderResponse)
async def send_strength_message(
    pto_type: PTOType = Query(PTOType.VACATION),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send time off is strength message.
    Message: "Time off isn't weakness"
    """
    target_user_id = user_id if user_id and hasattr(current_user, "is_admin") and current_user.is_admin else current_user.id

    try:
        reminder = await PTOPromotionService.send_time_off_strength_message(
            db=db,
            user_id=target_user_id,
            pto_type=pto_type,
        )
        if not reminder:
            raise HTTPException(status_code=400, detail="No available PTO days for reminder")
        await db.commit()
        return reminder
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/pre-vacation-triage/{request_id}", response_model=PTOPromotionTriageResponse)
async def get_pre_vacation_triage(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get pre-vacation task triage checklist"""
    from app.models.pto import PTORequest
    from sqlalchemy import select

    request = (await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )).scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        triage = await PTOPromotionService.prepare_pre_vacation_triage(db, request_id)
        return triage
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/enable-auto-delegation/{request_id}")
async def enable_auto_delegation(
    request_id: int,
    delegation_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enable auto-delegation while away"""
    from app.models.pto import PTORequest
    from sqlalchemy import select

    request = (await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )).scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        updated_request = await PTOPromotionService.enable_auto_delegation(
            db=db,
            request_id=request_id,
            delegation_notes=delegation_notes,
        )
        await db.commit()
        return {
            "success": True,
            "message": "Auto-delegation enabled",
            "auto_delegate": updated_request.auto_delegate,
            "delegation_notes": updated_request.delegation_notes,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/gradual-return/{request_id}", response_model=PTOPromotionGradualReturnResponse)
async def get_gradual_return(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get gradual inbox return plan"""
    from app.models.pto import PTORequest
    from sqlalchemy import select

    request = (await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )).scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        plan = await PTOPromotionService.get_gradual_return_plan(db, request_id)
        return plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/create-celebration/{request_id}")
async def create_celebration(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create vacation celebration"""
    from app.models.pto import PTORequest
    from sqlalchemy import select

    request = (await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )).scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    # Only managers/admins can create celebrations
    if not hasattr(current_user, "is_manager") or not current_user.is_manager:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        celebration = await PTOPromotionService.create_celebration_notification(db, request_id)
        return {
            "success": True,
            "celebration": celebration,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/send-welcome-back/{request_id}", response_model=PTOReminderResponse)
async def send_welcome_back(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send welcome back message after vacation"""
    from app.models.pto import PTORequest
    from sqlalchemy import select

    request = (await db.execute(
        select(PTORequest).where(PTORequest.id == request_id)
    )).scalars().first()

    if not request:
        raise HTTPException(status_code=404, detail="PTO request not found")

    if request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        reminder = await PTOPromotionService.send_return_welcome_message(db, request_id)
        await db.commit()
        return reminder
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/batch-send-reminders")
async def batch_send_reminders(
    days_threshold: int = Query(10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send batch reminders (admin only)"""
    # Check if user is admin
    if not hasattr(current_user, "is_admin") or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        reminders = await PTOPromotionService.send_batch_promotion_reminders(
            db=db,
            days_threshold=days_threshold,
        )
        await db.commit()
        return {
            "success": True,
            "reminders_sent": len(reminders),
            "message": f"Sent {len(reminders)} PTO reminders to staff with {days_threshold}+ available days",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
