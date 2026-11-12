# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading activity API — patron reading activity feed."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.reading_activity import ReadingActivityList, ReadingActivityResponse
from ...services.reading_activity_service import ReadingActivityService
from .auth import get_current_user

router = APIRouter(tags=["reading-activity"])


@router.get("/reading-activity", response_model=ReadingActivityList)
async def get_reading_activity(
    limit: int = Query(5, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent reading activity for current user."""
    items, total = await ReadingActivityService.get_recent(
        db, current_user.id, limit=limit, offset=offset
    )
    return ReadingActivityList(
        items=[ReadingActivityResponse.model_validate(i) for i in items],
        total=total,
    )
