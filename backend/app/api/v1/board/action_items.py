# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board meeting action item tracking API endpoints."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.board import BoardMeeting, BoardMember, MeetingActionItem
from ....models.user import User, UserRole
from ....schemas.board import (
    ActionItemCreate,
    ActionItemResponse,
    ActionItemStatusUpdate,
    ActionItemUpdate,
)
from ..auth import get_current_user
from ..dependencies import is_staff_or_admin

router = APIRouter(tags=["board-action-items"])


VALID_STATUS_TRANSITIONS = {
    "not_started": ["in_progress", "cancelled", "on_hold"],
    "in_progress": ["completed", "cancelled", "on_hold", "not_started"],
    "on_hold": ["in_progress", "cancelled", "not_started"],
    "completed": [],  # Cannot transition from completed
    "cancelled": [],  # Cannot transition from cancelled
}


# ============ Meeting-scoped Action Items ============


@router.get("/board/meetings/{meeting_id}/action-items", response_model=List[ActionItemResponse])
async def get_meeting_action_items(
    meeting_id: int,
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get action items for a meeting (staff/admin/board members)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="Board member or staff access required"
            )

    query = select(MeetingActionItem).where(MeetingActionItem.meeting_id == meeting_id)
    if status:
        query = query.where(MeetingActionItem.status == status)
    query = query.order_by(MeetingActionItem.created_at)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/board/meetings/{meeting_id}/action-items", response_model=ActionItemResponse)
async def create_action_item(
    meeting_id: int,
    action_item: ActionItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an action item for a meeting (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    # Verify meeting exists and is not cancelled
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(
            status_code=400, detail="Cannot add action items to a cancelled meeting"
        )

    db_action = MeetingActionItem(
        **action_item.model_dump(),
        meeting_id=meeting_id,
        status="not_started",
        assigned_by_id=current_user.id,
        created_by_id=current_user.id,
    )
    db.add(db_action)
    await db.commit()
    await db.refresh(db_action)
    return db_action


# ============ Global Action Items ============


@router.get("/board/action-items", response_model=List[ActionItemResponse])
async def get_all_action_items(
    status: Optional[str] = Query(None, description="Filter by status"),
    assigned_to_id: Optional[int] = Query(None, description="Filter by assignee"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all action items across meetings (staff/admin/board members)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="Board member or staff access required"
            )

    query = select(MeetingActionItem)
    if status:
        query = query.where(MeetingActionItem.status == status)
    if assigned_to_id:
        query = query.where(MeetingActionItem.assigned_to_id == assigned_to_id)
    if priority:
        query = query.where(MeetingActionItem.priority == priority)
    query = query.order_by(MeetingActionItem.due_date.asc().nullslast()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/board/action-items/{action_item_id}", response_model=ActionItemResponse)
async def get_action_item(
    action_item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific action item details."""
    db_action = await get_or_404(db, MeetingActionItem, action_item_id, "Action item not found")
    return db_action


@router.put("/board/action-items/{action_item_id}", response_model=ActionItemResponse)
async def update_action_item(
    action_item_id: int,
    action_item: ActionItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an action item (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_action = await get_or_404(db, MeetingActionItem, action_item_id, "Action item not found")

    for key, value in action_item.model_dump(exclude_unset=True).items():
        setattr(db_action, key, value)
    db_action.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_action)
    return db_action


@router.get("/board/action-items/{action_item_id}/status", response_model=ActionItemResponse)
async def get_action_item_status(
    action_item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current status of an action item."""
    db_action = await get_or_404(db, MeetingActionItem, action_item_id, "Action item not found")
    return db_action


@router.post("/board/action-items/{action_item_id}/status", response_model=ActionItemResponse)
async def update_action_item_status(
    action_item_id: int,
    status_update: ActionItemStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update action item status with validation (staff/admin/assignee)."""
    db_action = await get_or_404(db, MeetingActionItem, action_item_id, "Action item not found")

    # Check permissions - staff/admin or assignee can update status
    is_assignee = db_action.assigned_to_id == current_user.id
    is_staff = is_staff_or_admin(current_user)
    if not is_assignee and not is_staff:
        raise HTTPException(
            status_code=403, detail="Only staff or the assignee can update status"
        )

    # Validate status transition
    current_status = db_action.status
    new_status = status_update.status

    if new_status not in VALID_STATUS_TRANSITIONS.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{current_status}' to '{new_status}'",
        )

    db_action.status = new_status
    if status_update.notes:
        db_action.notes = (db_action.notes or "") + f"\n[{datetime.now(timezone.utc).isoformat()}] {status_update.notes}"

    if new_status == "completed":
        db_action.completed_at = datetime.now(timezone.utc)
        db_action.progress_percentage = 100
    elif new_status == "in_progress" and db_action.progress_percentage == 0:
        db_action.progress_percentage = 10

    db_action.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_action)
    return db_action


@router.delete("/board/action-items/{action_item_id}")
async def delete_action_item(
    action_item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an action item (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_action = await get_or_404(db, MeetingActionItem, action_item_id, "Action item not found")

    await db.delete(db_action)
    await db.commit()
    return {"message": "Action item deleted"}
