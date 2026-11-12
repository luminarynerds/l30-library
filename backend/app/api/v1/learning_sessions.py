# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Session scheduling API endpoints for course modules."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.session import ModuleSession, SessionRSVP
from ...models.learning import Module
from ...models.user import User
from ...schemas.session import (
    ModuleSessionCreate, ModuleSessionUpdate, ModuleSessionResponse,
    ModuleSessionWithRSVPs, RSVPCreate, SessionRSVPResponse,
)
from .auth import get_current_user
from .dependencies import is_staff_or_admin

router = APIRouter(prefix="/learning", tags=["learning-sessions"])


@router.get("/modules/{module_id}/sessions", response_model=List[ModuleSessionResponse])
async def list_module_sessions(
    module_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sessions for a module."""
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    result = await db.execute(
        select(ModuleSession)
        .options(selectinload(ModuleSession.rsvps))
        .where(ModuleSession.module_id == module_id, ModuleSession.is_cancelled == False)
        .order_by(ModuleSession.scheduled_at)
    )
    sessions = result.scalars().all()

    return [
        ModuleSessionResponse(
            **{c.name: getattr(s, c.name) for c in s.__table__.columns},
            rsvp_count=len(s.rsvps),
        )
        for s in sessions
    ]


@router.post("/modules/{module_id}/sessions", response_model=ModuleSessionResponse)
async def create_session(
    module_id: int,
    data: ModuleSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a session for a module (staff/admin only)."""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Staff access required")

    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    session = ModuleSession(
        module_id=module_id,
        title=data.title,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
        location=data.location,
        facilitator_id=data.facilitator_id,
        max_participants=data.max_participants,
        materials=data.materials,
        notes=data.notes,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ModuleSessionResponse(
        **{c.name: getattr(session, c.name) for c in session.__table__.columns},
        rsvp_count=0,
    )


@router.put("/sessions/{session_id}", response_model=ModuleSessionResponse)
async def update_session(
    session_id: int,
    data: ModuleSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a session (staff/admin only)."""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Staff access required")

    session = await db.get(ModuleSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(session, field, value)

    await db.commit()
    await db.refresh(session)

    result = await db.execute(
        select(func.count(SessionRSVP.id)).where(SessionRSVP.session_id == session_id)
    )
    rsvp_count = result.scalar() or 0

    return ModuleSessionResponse(
        **{c.name: getattr(session, c.name) for c in session.__table__.columns},
        rsvp_count=rsvp_count,
    )


@router.delete("/sessions/{session_id}")
async def cancel_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a session (staff/admin only)."""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Staff access required")

    session = await db.get(ModuleSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_cancelled = True
    await db.commit()
    return {"message": "Session cancelled"}


@router.post("/sessions/{session_id}/rsvp", response_model=SessionRSVPResponse)
async def rsvp_to_session(
    session_id: int,
    data: RSVPCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """RSVP to a session."""
    session = await db.get(ModuleSession, session_id)
    if not session or session.is_cancelled:
        raise HTTPException(status_code=404, detail="Session not found or cancelled")

    # Check capacity
    if session.max_participants and data.status == "attending":
        result = await db.execute(
            select(func.count(SessionRSVP.id)).where(
                SessionRSVP.session_id == session_id,
                SessionRSVP.status == "attending",
            )
        )
        current_count = result.scalar() or 0
        if current_count >= session.max_participants:
            raise HTTPException(status_code=409, detail="Session is full")

    # Upsert RSVP
    result = await db.execute(
        select(SessionRSVP).where(
            SessionRSVP.session_id == session_id,
            SessionRSVP.user_id == current_user.id,
        )
    )
    rsvp = result.scalar_one_or_none()

    if rsvp:
        rsvp.status = data.status
        rsvp.responded_at = datetime.now(timezone.utc)
    else:
        rsvp = SessionRSVP(
            session_id=session_id,
            user_id=current_user.id,
            status=data.status,
        )
        db.add(rsvp)

    await db.commit()
    await db.refresh(rsvp)
    return rsvp


@router.get("/sessions/upcoming", response_model=List[ModuleSessionResponse])
async def list_upcoming_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List upcoming sessions the user has RSVP'd to."""
    result = await db.execute(
        select(ModuleSession)
        .options(selectinload(ModuleSession.rsvps))
        .join(SessionRSVP, SessionRSVP.session_id == ModuleSession.id)
        .where(
            SessionRSVP.user_id == current_user.id,
            SessionRSVP.status == "attending",
            ModuleSession.is_cancelled == False,
            ModuleSession.scheduled_at >= datetime.now(timezone.utc),
        )
        .order_by(ModuleSession.scheduled_at)
    )
    sessions = result.scalars().all()

    return [
        ModuleSessionResponse(
            **{c.name: getattr(s, c.name) for c in s.__table__.columns},
            rsvp_count=len(s.rsvps),
        )
        for s in sessions
    ]
