# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board recusal declaration API - conflict-of-interest management."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.audit_log import audit_log_event
from ....models.board import BoardMember, BoardRecusalDeclaration
from ....models.board_audit_log import BoardAuditLog, BoardAuditAction
from ....models.user import User, UserRole
from ....schemas.board import RecusalDeclareRequest, RecusalResponse, RecusalWithdrawRequest
from ..auth import get_current_user

router = APIRouter(prefix="/board/recusals", tags=["board-recusals"])


@router.post("", response_model=RecusalResponse, status_code=201)
async def declare_recusal(
    body: RecusalDeclareRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Declare a conflict-of-interest recusal (board members only)."""
    member_result = await db.execute(
        select(BoardMember).where(
            and_(BoardMember.user_id == current_user.id, BoardMember.is_current == True)
        )
    )
    board_member = member_result.scalar_one_or_none()
    if not board_member:
        raise HTTPException(status_code=403, detail="Only current board members can declare recusals")

    if not body.vote_id and not body.motion_id and not body.topic_description:
        raise HTTPException(
            status_code=400,
            detail="Must specify at least one of: vote_id, motion_id, or topic_description",
        )

    if body.vote_id:
        existing = await db.execute(
            select(BoardRecusalDeclaration).where(
                and_(
                    BoardRecusalDeclaration.board_member_id == board_member.id,
                    BoardRecusalDeclaration.vote_id == body.vote_id,
                    BoardRecusalDeclaration.is_active == True,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Active recusal already exists for this vote")

    recusal = BoardRecusalDeclaration(
        board_member_id=board_member.id,
        vote_id=body.vote_id,
        motion_id=body.motion_id,
        topic_description=body.topic_description,
        reason=body.reason,
    )
    db.add(recusal)

    audit_entry = BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.RECUSAL_DECLARED,
        entity_type="BoardRecusalDeclaration",
        entity_id=0,
        details={
            "vote_id": body.vote_id,
            "motion_id": body.motion_id,
            "reason": body.reason,
            "member_name": board_member.full_name,
        },
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(recusal)

    audit_entry.entity_id = recusal.id
    await db.commit()

    audit_log_event(
        event_type="BOARD_RECUSAL_DECLARED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"recusal_id": recusal.id, "entity_type": "BoardRecusalDeclaration", "vote_id": body.vote_id, "motion_id": body.motion_id, "member_name": board_member.full_name},
    )

    return recusal


@router.get("", response_model=List[RecusalResponse])
async def list_recusals(
    vote_id: Optional[int] = Query(None),
    motion_id: Optional[int] = Query(None),
    board_member_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recusal declarations (authenticated users)."""
    query = select(BoardRecusalDeclaration)

    filters = []
    if vote_id is not None:
        filters.append(BoardRecusalDeclaration.vote_id == vote_id)
    if motion_id is not None:
        filters.append(BoardRecusalDeclaration.motion_id == motion_id)
    if board_member_id is not None:
        filters.append(BoardRecusalDeclaration.board_member_id == board_member_id)
    if active_only:
        filters.append(BoardRecusalDeclaration.is_active == True)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(BoardRecusalDeclaration.declared_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{recusal_id}/withdraw", response_model=RecusalResponse)
async def withdraw_recusal(
    recusal_id: int,
    body: RecusalWithdrawRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw a recusal declaration (original declarer or admin)."""
    recusal = await get_or_404(db, BoardRecusalDeclaration, recusal_id, "Recusal not found")

    if not recusal.is_active:
        raise HTTPException(status_code=400, detail="Recusal has already been withdrawn")

    member_result = await db.execute(
        select(BoardMember).where(BoardMember.id == recusal.board_member_id)
    )
    board_member = member_result.scalar_one_or_none()

    is_own_recusal = board_member and board_member.user_id == current_user.id
    is_admin = current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]

    if not is_own_recusal and not is_admin:
        raise HTTPException(status_code=403, detail="Only the declaring member or admin can withdraw a recusal")

    recusal.is_active = False
    recusal.withdrawn_at = datetime.now(timezone.utc)
    recusal.withdrawn_by_id = current_user.id
    recusal.withdrawn_reason = body.reason

    audit_entry = BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.RECUSAL_WITHDRAWN,
        entity_type="BoardRecusalDeclaration",
        entity_id=recusal.id,
        details={
            "withdrawn_reason": body.reason,
            "original_vote_id": recusal.vote_id,
            "original_motion_id": recusal.motion_id,
            "member_name": board_member.full_name if board_member else "Unknown",
        },
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(recusal)

    audit_log_event(
        event_type="BOARD_RECUSAL_WITHDRAWN",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"recusal_id": recusal.id, "entity_type": "BoardRecusalDeclaration", "reason": body.reason, "member_name": board_member.full_name if board_member else "Unknown"},
    )

    return recusal
