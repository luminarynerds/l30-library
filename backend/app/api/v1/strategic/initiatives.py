# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strategic planning - Initiatives, milestones, and board-decision link endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.strategic import StrategicInitiative, StrategicPlan, InitiativeMilestone
from app.models.user import User
from app.schemas.strategic import (
    InitiativeCreate,
    InitiativeResponse,
    InitiativeUpdate,
    InitiativeMilestoneCreate,
    InitiativeMilestoneResponse,
    MilestoneCompleteRequest,
    BoardDecisionLinkCreate,
    BoardDecisionLinkResponse,
)
from app.services.strategic_leadership_service import (
    create_initiative,
    get_initiatives_for_plan,
    create_milestone,
    complete_milestone,
    link_board_decision,
)
from ..auth import get_current_user
from .common import require_staff, require_admin

router = APIRouter(prefix="/strategic", tags=["strategic-initiatives"])


async def _load_initiative(db: AsyncSession, initiative_id: int) -> StrategicInitiative:
    result = await db.execute(
        select(StrategicInitiative)
        .where(StrategicInitiative.id == initiative_id)
        .options(
            selectinload(StrategicInitiative.milestones),
            selectinload(StrategicInitiative.board_decisions),
            selectinload(StrategicInitiative.assigned_leader),
        )
    )
    return result.scalar_one_or_none()


@router.get("/plans/{plan_id}/initiatives", response_model=List[InitiativeResponse])
async def list_initiatives(
    plan_id: int,
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List initiatives for a strategic plan (staff/admin)."""
    require_staff(current_user)
    plan = await db.get(StrategicPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return await get_initiatives_for_plan(db, plan_id, status=status)


@router.post("/plans/{plan_id}/initiatives", response_model=InitiativeResponse, status_code=201)
async def create_initiative_endpoint(
    plan_id: int,
    initiative_data: InitiativeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an initiative to a strategic plan (staff/admin)."""
    require_staff(current_user)
    plan = await db.get(StrategicPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    initiative = await create_initiative(db, plan_id, initiative_data.model_dump(), current_user.id)
    return await _load_initiative(db, initiative.id)


@router.patch("/initiatives/{initiative_id}", response_model=InitiativeResponse)
async def update_initiative(
    initiative_id: int,
    initiative_data: InitiativeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a strategic initiative (staff/admin)."""
    require_staff(current_user)
    initiative = await db.get(StrategicInitiative, initiative_id)
    if initiative is None:
        raise HTTPException(status_code=404, detail="Initiative not found")
    for field, value in initiative_data.model_dump(exclude_unset=True).items():
        setattr(initiative, field, value)
    await db.commit()
    return await _load_initiative(db, initiative_id)


@router.delete("/initiatives/{initiative_id}", status_code=204)
async def delete_initiative(
    initiative_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a strategic initiative (admin only)."""
    require_admin(current_user)
    initiative = await db.get(StrategicInitiative, initiative_id)
    if initiative is None:
        raise HTTPException(status_code=404, detail="Initiative not found")
    await db.delete(initiative)
    await db.commit()


@router.post("/initiatives/{initiative_id}/milestones", response_model=InitiativeMilestoneResponse, status_code=201)
async def create_milestone_endpoint(
    initiative_id: int,
    milestone_data: InitiativeMilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a milestone to an initiative (staff/admin)."""
    require_staff(current_user)
    initiative = await db.get(StrategicInitiative, initiative_id)
    if initiative is None:
        raise HTTPException(status_code=404, detail="Initiative not found")
    return await create_milestone(db, initiative_id, milestone_data.model_dump())


@router.post("/milestones/{milestone_id}/complete", response_model=InitiativeMilestoneResponse)
async def complete_milestone_endpoint(
    milestone_id: int,
    body: MilestoneCompleteRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a milestone as complete (staff/admin)."""
    require_staff(current_user)
    milestone = await db.get(InitiativeMilestone, milestone_id)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    notes = body.completion_notes if body is not None else None
    return await complete_milestone(db, milestone_id, notes)


@router.post("/initiatives/{initiative_id}/board-decisions", response_model=BoardDecisionLinkResponse, status_code=201)
async def link_board_decision_endpoint(
    initiative_id: int,
    decision_data: BoardDecisionLinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Link a board decision to an initiative (staff/admin)."""
    require_staff(current_user)
    initiative = await db.get(StrategicInitiative, initiative_id)
    if initiative is None:
        raise HTTPException(status_code=404, detail="Initiative not found")
    return await link_board_decision(db, initiative_id, decision_data.model_dump())
