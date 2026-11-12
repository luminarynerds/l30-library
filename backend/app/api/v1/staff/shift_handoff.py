# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shift handoff notes -- staff leave notes for the next shift."""
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....models.user import User
from ....models.shift_handoff import ShiftHandoff
from ..dependencies import require_staff

router = APIRouter(prefix="/staff/shift", tags=["staff-shift"])
logger = get_logger(__name__)


class ShiftHandoffResponse(BaseModel):
    id: int
    author_name: str
    body: str
    created_at: str


class ShiftHandoffCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=500)


@router.get("/handoff", response_model=ShiftHandoffResponse | None)
async def get_shift_handoff(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent handoff note from the last 24 hours, or null."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    try:
        result = await db.execute(
            select(ShiftHandoff)
            .options(selectinload(ShiftHandoff.author))
            .where(ShiftHandoff.created_at >= cutoff)
            .order_by(ShiftHandoff.created_at.desc())
            .limit(1)
        )
        note = result.scalar_one_or_none()

        if note is None:
            return None

        return ShiftHandoffResponse(
            id=note.id,
            author_name=note.author.first_name,
            body=note.body,
            created_at=note.created_at.isoformat(),
        )
    except Exception:
        logger.exception("Failed to fetch shift handoff")
        return None


@router.post("/handoff", response_model=ShiftHandoffResponse, status_code=status.HTTP_201_CREATED)
async def create_shift_handoff(
    payload: ShiftHandoffCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new shift handoff note."""
    note = ShiftHandoff(
        author_id=staff_user.id,
        body=payload.body,
    )
    db.add(note)
    await db.flush()

    return ShiftHandoffResponse(
        id=note.id,
        author_name=staff_user.first_name,
        body=note.body,
        created_at=note.created_at.isoformat(),
    )
