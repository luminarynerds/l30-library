# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....models.user import User
from ....schemas.user import UserResponse, UserUpdate
from ....schemas.patron import PatronResponse
from .helpers import get_current_user

logger = get_logger(__name__)

router = APIRouter()


# Fields a patron is allowed to change about themselves via PUT /auth/me.
# Anything outside this set (notably patron_type and date_of_birth, which gate
# COPPA / minor-only AI guardrails) is silently ignored — it must be changed
# by an admin endpoint or by patron_lifecycle_jobs, never by the patron.
_SELF_EDITABLE_FIELDS = frozenset({
    "first_name",
    "last_name",
    "phone",
    "address",
    "track_reading_history",
    "aggregate_recommendations_opt_out",
    "emergency_contact_name",
    "emergency_contact_phone",
    "preferred_contact_method",
    "language_preference",
    "accessibility_needs",
    "pronouns",
    "custom_fields",
})


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile."""
    from sqlalchemy import select, exists
    from ....models.board.member import BoardMember

    is_board = await db.scalar(
        select(exists().where(
            BoardMember.user_id == current_user.id,
            BoardMember.is_current.is_(True),
        ))
    )
    response = UserResponse.model_validate(current_user)
    response.is_board_member = is_board or False
    return response


@router.put("/me", response_model=UserResponse)
@limiter.limit("10/minute")
async def update_me(
    request: Request,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile.

    Mass-assignment guard: only fields in _SELF_EDITABLE_FIELDS are written.
    UserUpdate intentionally still exposes patron_type and date_of_birth so
    admin endpoints and patron_lifecycle_jobs can use the same schema; here
    we filter them out so a patron cannot self-promote (e.g. minor -> adult)
    and bypass minor-only AI guardrails until the lifecycle scheduler runs.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    rejected = [k for k in update_data if k not in _SELF_EDITABLE_FIELDS]
    if rejected:
        logger.warning(
            "update_me: ignoring non-self-editable fields for user_id=%s fields=%s",
            current_user.id,
            rejected,
        )

    for field, value in update_data.items():
        if field not in _SELF_EDITABLE_FIELDS:
            continue
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.patch("/me/ui-mode", response_model=PatronResponse)
@limiter.limit("10/minute")
async def update_ui_mode(
    request: Request,
    ui_mode: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update authenticated user's UI mode preference."""
    if ui_mode not in ['essentials', 'full']:
        raise HTTPException(status_code=400, detail="Please choose either 'essentials' or 'full' for your display mode.")

    current_user.ui_mode = ui_mode
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return PatronResponse.model_validate(current_user)
