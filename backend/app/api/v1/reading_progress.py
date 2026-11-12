# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading progress API — log and track page-level reading progress."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.reading_progress import MilestoneEarned, ProgressLog, ProgressLogResponse, ProgressLogWithMilestone
from ...services.reading_progress_service import ReadingProgressService
from .auth import get_current_user

router = APIRouter(tags=["reading-progress"])


@router.get("/reading-progress/all/latest", response_model=List[ProgressLogResponse])
async def get_all_latest_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get latest progress for all books."""
    return await ReadingProgressService.get_all_latest(db, current_user.id)


@router.post("/reading-progress/{catalog_item_id}", response_model=ProgressLogWithMilestone, status_code=201)
async def log_reading_progress(
    catalog_item_id: int,
    data: ProgressLog,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a reading progress entry. Returns milestone if one was earned."""
    entry, milestone_data = await ReadingProgressService.log_progress(
        db, current_user.id, catalog_item_id,
        data.current_page, data.total_pages, data.percent, data.note,
    )
    response = ProgressLogWithMilestone.model_validate(entry)
    if milestone_data:
        response.milestone_earned = MilestoneEarned(**milestone_data)
    return response


@router.get("/reading-progress/{catalog_item_id}", response_model=List[ProgressLogResponse])
async def get_progress_history(
    catalog_item_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get progress history for a specific book."""
    return await ReadingProgressService.get_history(
        db, current_user.id, catalog_item_id, limit
    )


@router.get("/reading-progress/{catalog_item_id}/pace", response_model=Optional[dict])
async def get_reading_pace(
    catalog_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reading pace stats (requires 3+ entries)."""
    return await ReadingProgressService.compute_pace(
        db, current_user.id, catalog_item_id
    )
