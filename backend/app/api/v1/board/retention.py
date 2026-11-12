# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board records retention API -- schedules, legal holds, dispositions."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.audit_log import audit_log_event
from ....models.board.retention import (
    BoardLegalHold,
    BoardRecordDisposition,
    BoardRecordRetentionSchedule,
)
from ....models.board_audit_log import BoardAuditLog, BoardAuditAction
from ....models.user import User, UserRole
from ....schemas.board import (
    LegalHoldCreate,
    LegalHoldReleaseRequest,
    LegalHoldResponse,
    RetentionScheduleResponse,
    RetentionScheduleUpdate,
)
from ..auth import get_current_user

router = APIRouter(prefix="/board/retention", tags=["board-retention"])


@router.get("/schedules", response_model=List[RetentionScheduleResponse])
async def list_retention_schedules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all board record retention schedules."""
    result = await db.execute(
        select(BoardRecordRetentionSchedule).order_by(
            BoardRecordRetentionSchedule.record_type
        )
    )
    return result.scalars().all()


@router.put("/schedules/{record_type}", response_model=RetentionScheduleResponse)
async def update_retention_schedule(
    record_type: str,
    body: RetentionScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a retention schedule (director only)."""
    if current_user.role not in [UserRole.DIRECTOR, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Director access required")

    result = await db.execute(
        select(BoardRecordRetentionSchedule).where(
            BoardRecordRetentionSchedule.record_type == record_type
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"No retention schedule for record type '{record_type}'")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(schedule, key, value)
    schedule.configured_by_id = current_user.id
    schedule.configured_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.post("/legal-holds", response_model=LegalHoldResponse, status_code=201)
async def place_legal_hold(
    body: LegalHoldCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Place a legal hold on board records (director/legal only)."""
    if current_user.role not in [UserRole.DIRECTOR, UserRole.LEGAL, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Director or legal access required")

    hold = BoardLegalHold(
        title=body.title,
        reason=body.reason,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        placed_by_id=current_user.id,
    )
    db.add(hold)

    audit_entry = BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.LEGAL_HOLD_PLACED,
        entity_type="BoardLegalHold",
        entity_id=0,
        details={
            "title": body.title,
            "reason": body.reason,
            "scope_entity_type": body.entity_type,
            "scope_entity_id": body.entity_id,
        },
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(hold)
    audit_entry.entity_id = hold.id
    await db.commit()

    audit_log_event(
        event_type="BOARD_LEGAL_HOLD_PLACED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="CRITICAL",
        details={"hold_id": hold.id, "entity_type": "BoardLegalHold", "title": body.title, "reason": body.reason, "scope_entity_type": body.entity_type, "scope_entity_id": body.entity_id},
    )

    return hold


@router.get("/legal-holds", response_model=List[LegalHoldResponse])
async def list_legal_holds(
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List legal holds (authenticated users)."""
    query = select(BoardLegalHold)
    if active_only:
        query = query.where(BoardLegalHold.is_active == True)
    query = query.order_by(BoardLegalHold.placed_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/legal-holds/{hold_id}/release", response_model=LegalHoldResponse)
async def release_legal_hold(
    hold_id: int,
    body: LegalHoldReleaseRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Release a legal hold (director/legal only)."""
    if current_user.role not in [UserRole.DIRECTOR, UserRole.LEGAL, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Director or legal access required")

    hold = await get_or_404(db, BoardLegalHold, hold_id, "Legal hold not found")

    if not hold.is_active:
        raise HTTPException(status_code=400, detail="Legal hold has already been released")

    hold.is_active = False
    hold.released_at = datetime.now(timezone.utc)
    hold.released_by_id = current_user.id
    hold.release_reason = body.reason

    audit_entry = BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.LEGAL_HOLD_RELEASED,
        entity_type="BoardLegalHold",
        entity_id=hold.id,
        details={
            "title": hold.title,
            "release_reason": body.reason,
        },
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(hold)

    audit_log_event(
        event_type="BOARD_LEGAL_HOLD_RELEASED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="CRITICAL",
        details={"hold_id": hold.id, "entity_type": "BoardLegalHold", "title": hold.title, "release_reason": body.reason},
    )

    return hold
