# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guest passes and legacy per-computer waitlist routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User, UserRole
from ...schemas.computer import (
    GuestPassCreateRequest,
    GuestPassPublicResponse,
    GuestPassResponse,
    WaitlistResponse,
)
from ...services import computer_service
from .dependencies import get_current_user

_STAFF_ROLES = (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN)

router = APIRouter()


@router.post("/guest-passes", response_model=GuestPassResponse, status_code=201)
async def create_guest_pass(
    request: GuestPassCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GuestPassResponse:
    """Create a guest pass for a non-cardholder."""
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    guest_pass = await computer_service.create_guest_pass(
        db,
        guest_name=request.guest_name,
        guest_email=request.guest_email,
        guest_phone=request.guest_phone,
        max_sessions=request.max_sessions,
        max_duration_minutes=request.max_duration_minutes_per_session,
        issued_by_staff_id=current_user.id,
        allowed_computer_types=request.allowed_computer_types,
    )

    await db.commit()
    return GuestPassResponse.model_validate(guest_pass)


@router.get("/guest-passes/{pass_code}", response_model=GuestPassPublicResponse)
async def validate_guest_pass(
    pass_code: str,
    db: AsyncSession = Depends(get_db),
) -> GuestPassPublicResponse:
    """Validate a guest pass without exposing sensitive fields."""
    guest_pass = await computer_service.validate_guest_pass(db, pass_code)

    if not guest_pass:
        raise HTTPException(status_code=404, detail="Invalid guest pass")

    return GuestPassPublicResponse.from_guest_pass(guest_pass)


@router.post("/waitlist", response_model=WaitlistResponse, status_code=201)
async def join_waitlist(
    computer_id: int = Query(...),
    desired_start_time: datetime = Query(...),
    duration_minutes: int = Query(..., gt=0),
    is_guest: bool = Query(False),
    guest_phone: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> WaitlistResponse:
    """Add a patron or guest to a computer's waitlist."""
    patron_id = current_user.id if current_user else None

    waitlist_entry = await computer_service.add_to_waitlist(
        db,
        computer_id=computer_id,
        patron_id=patron_id,
        desired_start_time=desired_start_time,
        duration_minutes=duration_minutes,
        is_guest=is_guest,
        guest_phone=guest_phone,
    )

    if not waitlist_entry:
        raise HTTPException(status_code=404, detail="Computer not found")

    await db.commit()
    return WaitlistResponse.model_validate(waitlist_entry)


@router.get("/computers/{computer_id}/waitlist", response_model=dict)
async def get_waitlist(
    computer_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the waitlist queue for a computer."""
    queue = await computer_service.get_waitlist_queue(db, computer_id)

    return {
        "computer_id": computer_id,
        "queue_length": len(queue),
        "queue": [WaitlistResponse.model_validate(w) for w in queue],
    }
