# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading status API endpoints — shelf tracking for patrons."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.reading_status import ShelfStatus
from ...models.user import User
from ...schemas.reading_status import (
    MilestoneEarnedBrief,
    ReadingStatusResponse,
    ReadingStatusSet,
    ReadingStatusWithMilestone,
    ReadingStatsResponse,
)
from ...services.reading_status_service import ReadingStatusService
from .auth import get_current_user

router = APIRouter(tags=["reading-status"])


@router.get("/reading-status", response_model=List[ReadingStatusResponse])
async def get_my_reading_statuses(
    status_filter: Optional[ShelfStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's books organized by reading status."""
    return await ReadingStatusService.get_user_statuses(
        db, current_user.id, status_filter=status_filter, limit=limit, offset=offset
    )


@router.put("/reading-status/{catalog_item_id}", response_model=ReadingStatusWithMilestone)
async def set_reading_status(
    catalog_item_id: int,
    data: ReadingStatusSet,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set or update reading status for a catalog item. Returns milestone if one was earned."""
    try:
        reading_status, milestone_data = await ReadingStatusService.set_status(
            db, current_user.id, catalog_item_id, data.status, data.private_notes, data.personal_tags
        )
        response = ReadingStatusWithMilestone.model_validate(reading_status)
        if milestone_data:
            response.milestone_earned = MilestoneEarnedBrief(**milestone_data)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/reading-status/{catalog_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_reading_status(
    catalog_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a catalog item from all shelves."""
    removed = await ReadingStatusService.remove_status(db, current_user.id, catalog_item_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Reading status not found")


@router.get("/reading-status/stats", response_model=ReadingStatsResponse)
async def get_reading_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get shelf counts and yearly reading stats."""
    stats = await ReadingStatusService.get_stats(db, current_user.id)
    return ReadingStatsResponse(**stats)
