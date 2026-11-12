# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Nudges API - Contextual nudge delivery and interaction tracking"""
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...services.nudge_service import get_active_nudges_for_patron, record_nudge_event
from .auth import get_current_user

router = APIRouter(prefix="/nudges", tags=["nudges"])


class NudgeContent(BaseModel):
    title: str | None = None
    body: str
    cta_label: str | None = None
    cta_route: str | None = None


class NudgeResponse(BaseModel):
    id: int
    slug: str
    delivery_type: str
    delivery_placement: str
    content: NudgeContent
    priority: int


class NudgeEventRequest(BaseModel):
    action: str = Field(..., pattern="^(shown|dismissed|acted_on)$")


@router.get("/active", response_model=list[NudgeResponse])
async def get_active_nudges(
    page_context: str = Query(default="global", max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    nudges = await get_active_nudges_for_patron(
        db=db,
        patron_id=current_user.id,
        page_context=page_context,
        nudge_frequency="normal",
    )
    return nudges


@router.post("/{nudge_id}/event", status_code=status.HTTP_204_NO_CONTENT)
async def post_nudge_event(
    nudge_id: int,
    body: NudgeEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await record_nudge_event(
        db=db,
        patron_id=current_user.id,
        nudge_id=nudge_id,
        action=body.action,
    )
