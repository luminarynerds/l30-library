# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""End-of-Shift Checklist API"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ...core.database import get_db
from .dependencies import require_staff, require_admin, get_current_user
from ...models.end_of_shift import (
    DailyWin, ShiftChecklistSession, ChecklistItem, ChecklistTemplate,
    ChecklistCategory, ChecklistItemStatus
)
from ...models.user import User
from app.core.datetime_utils import utc_now
from app.services.time_entry_service import sync_shift_actuals
from zoneinfo import ZoneInfo

LIBRARY_TZ = ZoneInfo("America/New_York")


def _local_shift_date(dt: datetime):
    """Bucket a shift to the library's local calendar day, matching time entries."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LIBRARY_TZ).date()


router = APIRouter()

# Pydantic schemas
class ChecklistItemSchema(BaseModel):
    id: int | None = None
    category: str
    title: str
    description: str | None = None
    status: str = "pending"
    order: int = 0
    required: bool = False
    notes: str | None = None

class ShiftChecklistSessionSchema(BaseModel):
    id: int | None = None
    items_completed: int
    total_items: int
    is_completed: bool
    checklist_items: list[ChecklistItemSchema] = []
    notes: str | None = None

class DailyWinSchema(BaseModel):
    description: str
    is_public: bool = False
    emoji: str = "🎉"

# Default checklist template
DEFAULT_CHECKLIST_ITEMS = [
    # Wrap up category
    {"category": "wrap_up", "title": "Close out open tabs/tasks", "description": "Review browser tabs and task list - close anything non-essential", "order": 1, "required": True},
    {"category": "wrap_up", "title": "Document unfinished work", "description": "Clearly note what's incomplete and where you left off", "order": 2, "required": True},
    {"category": "wrap_up", "title": "Log accomplishments", "description": "What did you accomplish today? Celebrate small wins!", "order": 3, "required": True},

    # Handoff category
    {"category": "handoff", "title": "Hand off in-progress items", "description": "Ensure next shift knows about active work and context", "order": 1, "required": True},
    {"category": "handoff", "title": "Brief colleague on key issues", "description": "Leave notes for colleagues or the next shift", "order": 2, "required": True},
    {"category": "handoff", "title": "Ensure next shift is covered", "description": "Confirm coverage and that someone knows what's happening", "order": 3, "required": False},

    # Tomorrow category
    {"category": "tomorrow", "title": "Clear tomorrow's priorities", "description": "Write down 3 key things to focus on next shift", "order": 1, "required": False},
    {"category": "tomorrow", "title": "Review calendar for tomorrow", "description": "Check meetings, events, and scheduled tasks", "order": 2, "required": False},

    # Mental transition category
    {"category": "mental", "title": "Mental transition ritual", "description": "Take a moment to mentally close out work (deep breath, brief walk, etc.)", "order": 1, "required": False},
    {"category": "mental", "title": "Don't carry work home", "description": "Leave work concerns at work - permission to disconnect", "order": 2, "required": False},

    # Celebration category
    {"category": "celebration", "title": "Celebrate your daily wins", "description": "Recognize what you did well today - no win is too small!", "order": 1, "required": False},
]

@router.post("/staff/shift-sessions", response_model=ShiftChecklistSessionSchema)
async def create_shift_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new end-of-shift checklist session"""
    session = ShiftChecklistSession(
        organization_id=(current_user.home_library_system_id or 1),
        staff_id=current_user.id,
        shift_date=utc_now().replace(tzinfo=None),
    )
    db.add(session)
    await db.flush()

    # Create checklist items from template
    items_to_add = []
    for template_item in DEFAULT_CHECKLIST_ITEMS:
        item = ChecklistItem(
            session_id=session.id,
            category=template_item["category"],
            title=template_item["title"],
            description=template_item.get("description"),
            order=template_item.get("order", 0),
            required=template_item.get("required", False),
        )
        items_to_add.append(item)
        db.add(item)

    session.total_items = len(items_to_add)
    await db.commit()
    await db.refresh(session, ["checklist_items"])

    return {
        "id": session.id,
        "items_completed": session.items_completed,
        "total_items": session.total_items,
        "is_completed": session.is_completed,
        "checklist_items": [
            ChecklistItemSchema(
                id=item.id,
                category=item.category,
                title=item.title,
                description=item.description,
                status=item.status,
                order=item.order,
                required=item.required,
                notes=item.notes,
            )
            for item in session.checklist_items
        ],
    }

@router.get("/staff/shift-sessions/current", response_model=ShiftChecklistSessionSchema)
async def get_current_shift_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get the current shift's checklist session"""
    today = utc_now().date()
    result = await db.execute(
        select(ShiftChecklistSession)
        .where(
            and_(
                ShiftChecklistSession.staff_id == current_user.id,
                ShiftChecklistSession.shift_date >= datetime.combine(today, datetime.min.time()),
                ShiftChecklistSession.shift_date < datetime.combine(today, datetime.max.time()),
            )
        )
        .options(selectinload(ShiftChecklistSession.checklist_items))
        .order_by(ShiftChecklistSession.shift_date.desc())
    )
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active shift session")

    return {
        "id": session.id,
        "items_completed": session.items_completed,
        "total_items": session.total_items,
        "is_completed": session.is_completed,
        "checklist_items": [
            ChecklistItemSchema(
                id=item.id,
                category=item.category,
                title=item.title,
                description=item.description,
                status=item.status,
                order=item.order,
                required=item.required,
                notes=item.notes,
            )
            for item in session.checklist_items
        ],
    }

@router.patch("/staff/checklist-items/{item_id}")
async def update_checklist_item(
    item_id: int,
    status: str,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark checklist item as complete/skipped"""
    result = await db.execute(
        select(ChecklistItem)
        .join(ShiftChecklistSession)
        .where(
            and_(
                ChecklistItem.id == item_id,
                ShiftChecklistSession.staff_id == current_user.id,
            )
        )
    )
    item = result.scalars().first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found")

    item.status = status
    item.notes = notes
    if status in ["completed", "skipped"]:
        item.completed_at = utc_now()

    # Update session completion counts
    session = item.session
    if status == "completed":
        session.items_completed += 1

    # Check if all required items are complete
    await db.refresh(session, ["checklist_items"])
    required_incomplete = any(
        i.required and i.status != "completed"
        for i in session.checklist_items
    )
    session.is_completed = not required_incomplete
    if session.is_completed and not session.completed_at:
        session.completed_at = utc_now()

    await db.commit()
    return {"status": "updated", "item_id": item_id}

@router.post("/staff/daily-wins", response_model=dict)
async def log_daily_win(
    request: DailyWinSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Log a daily accomplishment and celebration"""
    # Get current shift session
    today = utc_now().date()
    result = await db.execute(
        select(ShiftChecklistSession)
        .where(
            and_(
                ShiftChecklistSession.staff_id == current_user.id,
                ShiftChecklistSession.shift_date >= datetime.combine(today, datetime.min.time()),
                ShiftChecklistSession.shift_date < datetime.combine(today, datetime.max.time()),
            )
        )
    )
    session = result.scalars().first()

    win = DailyWin(
        organization_id=(current_user.home_library_system_id or 1),
        staff_id=current_user.id,
        session_id=session.id if session else None,
        win_description=request.description,
        is_public=request.is_public,
        celebration_emoji=request.emoji,
    )
    db.add(win)
    await db.commit()
    await db.refresh(win)
    return {
        "message": "Daily win logged! 🎉",
        "win_id": win.id,
        "emoji": win.celebration_emoji,
    }

@router.get("/staff/daily-wins", response_model=dict)
async def get_daily_wins(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get staff member's recent daily wins"""
    result = await db.execute(
        select(DailyWin)
        .where(DailyWin.staff_id == current_user.id)
        .order_by(DailyWin.win_date.desc())
        .limit(limit)
    )
    wins = result.scalars().all()
    return {
        "wins": [
            {
                "id": w.id,
                "description": w.win_description,
                "emoji": w.celebration_emoji,
                "is_public": w.is_public,
                "date": w.win_date.isoformat(),
            }
            for w in wins
        ]
    }

@router.post("/staff/shift-sessions/{session_id}/complete")
async def complete_shift_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark shift session as completely finished"""
    result = await db.execute(
        select(ShiftChecklistSession)
        .where(
            and_(
                ShiftChecklistSession.id == session_id,
                ShiftChecklistSession.staff_id == current_user.id,
            )
        )
    )
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift session not found")

    # Verify all required items are complete
    await db.refresh(session, ["checklist_items"])
    required_incomplete = any(
        i.required and i.status != "completed"
        for i in session.checklist_items
    )

    if required_incomplete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete shift - required checklist items are incomplete"
        )

    session.is_completed = True
    session.shift_end_time = utc_now()
    session.completed_at = utc_now()

    # Sync actual hours to StaffShift
    try:
        shift_date = _local_shift_date(session.shift_date)
        await sync_shift_actuals(db, current_user.id, shift_date)
    except Exception:  # noqa: BLE001  # non-critical timesheet sync — shift completion already saved
        pass  # Non-critical -- timesheet sync failure should not block shift completion

    await db.commit()
    return {"message": "Shift session completed. Permission to leave on time granted! 👋", "session_id": session_id}
