# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Perfectionism Antidotes API Endpoints

Provides REST API for perfectionism antidotes, coaching sessions, and growth mindset tracking.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db, get_current_user
from app.services.perfectionism_antidotes_service import PerfectionismAntidotesService
from app.models.perfectionism_antidotes import AntidoteType


router = APIRouter(prefix="/perfectionism-antidotes", tags=["perfectionism-antidotes"])


# ============================================================================
# ANTIDOTES
# ============================================================================

@router.get("/antidotes", summary="Get all perfectionism antidotes")
async def get_antidotes(db: AsyncSession = Depends(get_db)):
    """Get list of all available perfectionism antidotes"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.get_all_antidotes()
    antidotes = await db.run_sync(_run)
    return {"antidotes": antidotes, "count": len(antidotes)}


@router.get("/antidotes/{antidote_type}", summary="Get specific antidote")
async def get_antidote(antidote_type: str, db: AsyncSession = Depends(get_db)):
    """Get specific antidote by type"""
    try:
        atype = AntidoteType[antidote_type.upper()]
        def _run(sync_session):
            svc = PerfectionismAntidotesService(sync_session)
            return svc.get_antidote_by_type(atype)
        antidote = await db.run_sync(_run)

        if not antidote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Antidote type {antidote_type} not found"
            )

        return {"antidote": antidote}

    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid antidote type: {antidote_type}"
        ) from None


# ============================================================================
# USER ANTIDOTE TRACKING
# ============================================================================

@router.get("/user/antidotes", summary="Get user's antidote progress")
async def get_user_antidotes(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's personal progress with antidotes"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.get_user_antidotes(current_user.id)
    antidotes = await db.run_sync(_run)
    return {"antidotes": antidotes, "count": len(antidotes)}


@router.post("/user/antidotes/{antidote_id}/track", summary="Track antidote application")
async def track_antidote(
    antidote_id: int,
    action: str = "acknowledged",
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Track that user acknowledged or applied an antidote"""
    if action not in ["acknowledged", "applied"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'acknowledged' or 'applied'"
        )

    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.track_antidote_application(current_user.id, antidote_id, action)
    result = await db.run_sync(_run)
    return {"result": result}


@router.post("/user/antidotes/{antidote_id}/favorite", summary="Mark antidote as favorite")
async def mark_favorite(
    antidote_id: int,
    is_favorite: bool = True,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark or unmark antidote as user favorite"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.mark_favorite(current_user.id, antidote_id, is_favorite)
    result = await db.run_sync(_run)
    return {"result": result}


# ============================================================================
# COACHING SESSIONS
# ============================================================================

@router.post("/coaching-sessions", summary="Create coaching session")
async def create_session(
    topic: str,
    challenge: str,
    antidote_id: Optional[int] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new coaching session for perfectionism challenges"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.create_coaching_session(
            user_id=current_user.id,
            topic=topic,
            challenge=challenge,
            antidote_id=antidote_id
        )
    session_data = await db.run_sync(_run)
    return {"session": session_data}


@router.get("/coaching-sessions", summary="Get user's coaching sessions")
async def get_sessions(
    status: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's coaching sessions"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.get_user_coaching_sessions(current_user.id, status)
    sessions = await db.run_sync(_run)
    return {"sessions": sessions, "count": len(sessions)}


@router.put("/coaching-sessions/{session_id}", summary="Update coaching session")
async def update_session(
    session_id: int,
    updates: dict,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a coaching session"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.update_coaching_session(session_id, updates)
    try:
        session_data = await db.run_sync(_run)
        return {"session": session_data}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e


# ============================================================================
# PROGRESS MILESTONES
# ============================================================================

@router.post("/milestones", summary="Record progress milestone")
async def create_milestone(
    title: str,
    what_happened: str,
    milestone_type: str = "launched_project",
    what_learned: Optional[str] = None,
    how_felt: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Record a milestone in overcoming perfectionism"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.create_milestone(
            user_id=current_user.id,
            title=title,
            what_happened=what_happened,
            milestone_type=milestone_type,
            what_learned=what_learned,
            how_felt=how_felt
        )
    milestone = await db.run_sync(_run)
    return {"milestone": milestone}


@router.get("/milestones", summary="Get user's progress milestones")
async def get_milestones(
    only_celebrated: bool = False,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's perfectionism journey milestones"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.get_user_milestones(current_user.id, only_celebrated)
    milestones = await db.run_sync(_run)
    return {"milestones": milestones, "count": len(milestones)}


@router.post("/milestones/{milestone_id}/celebrate", summary="Celebrate milestone")
async def celebrate_milestone(
    milestone_id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Celebrate and mark a milestone as celebrated"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.celebrate_milestone(milestone_id)
    try:
        milestone = await db.run_sync(_run)
        return {"milestone": milestone}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e


# ============================================================================
# DAILY REMINDERS
# ============================================================================

@router.get("/reminders/pending", summary="Get pending reminders")
async def get_pending_reminders(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get unacknowledged reminders for user"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.get_pending_reminders(current_user.id)
    reminders = await db.run_sync(_run)
    return {"reminders": reminders, "count": len(reminders)}


@router.post("/reminders/{reminder_id}/acknowledge", summary="Acknowledge reminder")
async def acknowledge_reminder(
    reminder_id: int,
    reflection: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark reminder as acknowledged with optional reflection"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.acknowledge_reminder(reminder_id, reflection)
    try:
        reminder = await db.run_sync(_run)
        return {"reminder": reminder}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e


# ============================================================================
# MANAGER BALANCE MODELING
# ============================================================================

@router.post("/manager/balance-model", summary="Create manager balance model")
async def create_balance_model(
    commitment: Optional[str] = None,
    boundaries: Optional[str] = None,
    mistake_sharing: Optional[str] = None,
    grace_examples: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Record how manager models healthy work-life balance"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.create_manager_model(
            manager_id=current_user.id,
            commitment=commitment,
            boundaries=boundaries,
            mistake_sharing=mistake_sharing,
            grace_examples=grace_examples
        )
    model = await db.run_sync(_run)
    return {"balance_model": model}


@router.get("/manager/balance-model", summary="Get manager's balance model")
async def get_balance_model(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get manager's balance modeling profile"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.get_manager_model(current_user.id)
    model = await db.run_sync(_run)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No balance model found for this manager"
        )

    return {"balance_model": model}


@router.put("/manager/balance-model", summary="Update manager's balance model")
async def update_balance_model(
    updates: dict,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update manager's balance modeling information"""
    def _run(sync_session):
        svc = PerfectionismAntidotesService(sync_session)
        return svc.update_manager_model(current_user.id, updates)
    model = await db.run_sync(_run)
    return {"balance_model": model}
