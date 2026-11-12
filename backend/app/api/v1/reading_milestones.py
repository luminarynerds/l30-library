# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading milestones API — patron achievements and celebrations."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.reading_milestone import ReadingMilestoneResponse
from ...services.reading_milestone_service import ReadingMilestoneService
from .auth import get_current_user

router = APIRouter(tags=["reading-milestones"])


@router.get("/reading-milestones", response_model=List[ReadingMilestoneResponse])
async def get_milestones(
    include_dismissed: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get earned milestones for current user."""
    return await ReadingMilestoneService.get_milestones(
        db, current_user.id, include_dismissed=include_dismissed
    )


@router.post("/reading-milestones/{milestone_id}/dismiss", status_code=204)
async def dismiss_milestone(
    milestone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss a milestone (hides from feed, does not delete)."""
    dismissed = await ReadingMilestoneService.dismiss_milestone(
        db, current_user.id, milestone_id
    )
    if not dismissed:
        raise HTTPException(status_code=404, detail="Milestone not found")
