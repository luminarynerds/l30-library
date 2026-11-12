# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Authenticated computer waitlist routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.computer_booking import WaitlistJoinRequest, WaitlistPositionResponse
from ...services import waitlist_service
from .dependencies import get_current_user

router = APIRouter()


@router.post("/waitlist/join", response_model=WaitlistPositionResponse, status_code=201)
async def join_computer_waitlist(
    request: WaitlistJoinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WaitlistPositionResponse:
    """Join the waitlist queue for a computer."""
    entry = await waitlist_service.join_waitlist(
        db,
        patron_id=current_user.id,
        computer_id=request.computer_id,
        desired_duration_minutes=request.desired_duration_minutes,
    )
    return WaitlistPositionResponse.model_validate(entry)


@router.get("/waitlist/position", response_model=WaitlistPositionResponse)
async def get_waitlist_position(
    computer_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WaitlistPositionResponse:
    """Get the current patron's waitlist position."""
    entry = await waitlist_service.get_position(
        db,
        patron_id=current_user.id,
        computer_id=computer_id,
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Not on any waitlist")
    return WaitlistPositionResponse.model_validate(entry)
