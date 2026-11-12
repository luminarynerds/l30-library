# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board member management API endpoints."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.audit_log import audit_log_event
from ....models.board import BoardMember
from ....models.user import User, UserRole
from ....schemas.board import (
    BoardMemberCreate,
    BoardMemberResponse,
    BoardMemberUpdate,
)
from ....services.board_service import create_board_member, update_board_member
from ..auth import get_current_user

router = APIRouter(prefix="/board/members", tags=["board-members"])


# ============ Public Endpoints ============


@router.get("", response_model=List[BoardMemberResponse])
async def get_board_members(
    current_only: bool = Query(True, description="Only return current board members"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Get public board member directory."""
    offset = (page - 1) * per_page
    query = select(BoardMember)
    if current_only:
        query = query.where(BoardMember.is_current == True)
    query = query.order_by(BoardMember.position, BoardMember.full_name).offset(offset).limit(per_page)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{member_id}", response_model=BoardMemberResponse)
async def get_board_member(member_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific board member."""
    member = await get_or_404(db, BoardMember, member_id, "Board member not found")
    return member


# ============ Authenticated Endpoints (Admin) ============


@router.post("", response_model=BoardMemberResponse, status_code=status.HTTP_201_CREATED)
async def create_board_member_endpoint(
    member: BoardMemberCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new board member (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Delegate to service layer
    db_member = await create_board_member(member.model_dump(), db)
    audit_log_event(
        event_type="BOARD_MEMBER_CREATED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"member_id": db_member.id, "entity_type": "BoardMember", "full_name": db_member.full_name},
    )
    return db_member


@router.put("/{member_id}", response_model=BoardMemberResponse)
async def update_board_member_endpoint(
    member_id: int,
    member: BoardMemberUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a board member (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Delegate to service layer
    db_member = await update_board_member(member_id, member.model_dump(exclude_unset=True), db)
    audit_log_event(
        event_type="BOARD_MEMBER_UPDATED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"member_id": member_id, "entity_type": "BoardMember", "updated_fields": list(member.model_dump(exclude_unset=True).keys())},
    )
    return db_member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board_member_endpoint(
    member_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a board member (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    db_member = await get_or_404(db, BoardMember, member_id, "Board member not found")

    audit_log_event(
        event_type="BOARD_MEMBER_DELETED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="WARNING",
        details={"member_id": member_id, "entity_type": "BoardMember", "full_name": db_member.full_name},
    )
    await db.delete(db_member)
    await db.commit()
    return {"message": "Board member deleted"}
