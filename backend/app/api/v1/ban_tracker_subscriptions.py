# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron-facing CRUD endpoints for ban-tracker subscriptions (phase 1).

Routes live under ``/api/v1/ban-tracker/subscriptions``. All endpoints
require an authenticated user and only ever return/mutate rows owned by
that user (``WHERE user_id = current_user.id``). Cross-patron access is
rejected with 404 (not 403) so the endpoint never reveals the existence
of another patron's row.

Phase 1 ships the model + CRUD only. The digest worker (phase 3) reads
``is_active`` + ``frequency`` + ``last_sent_at`` to decide whether a row
is due; the ``unsubscribe_token`` is generated here so the phase-3 email
pipeline can resolve a one-click unsubscribe via its unique index.
"""
from __future__ import annotations

from app.core.logging import get_logger
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.ban_tracker import BanTrackerSubscription
from ...models.user import User
from ...schemas.ban_tracker import (
    BanTrackerSubscriptionCreate,
    BanTrackerSubscriptionResponse,
    BanTrackerSubscriptionUpdate,
)
from .auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(
    prefix="/ban-tracker/subscriptions",
    tags=["ban-tracker-subscriptions"],
)


async def _get_owned_or_404(
    db: AsyncSession, sub_id: int, user_id: int
) -> BanTrackerSubscription:
    result = await db.execute(
        select(BanTrackerSubscription).where(
            BanTrackerSubscription.id == sub_id,
            BanTrackerSubscription.user_id == user_id,
        )
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )
    return sub


@router.get("", response_model=list[BanTrackerSubscriptionResponse])
async def list_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BanTrackerSubscription]:
    """List the current patron's ban-tracker subscriptions, newest first."""
    result = await db.execute(
        select(BanTrackerSubscription)
        .where(BanTrackerSubscription.user_id == current_user.id)
        .order_by(BanTrackerSubscription.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "",
    response_model=BanTrackerSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    payload: BanTrackerSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BanTrackerSubscription:
    """Create a subscription for the current patron.

    Rejects duplicates on (scope, state_filter, ban_type_filter) with 409.
    Duplicate detection is enforced here rather than via a Postgres UNIQUE
    constraint because NULLs in state_filter/ban_type_filter would otherwise
    silently permit duplicate rows.
    """
    dup = await db.execute(
        select(BanTrackerSubscription).where(
            BanTrackerSubscription.user_id == current_user.id,
            BanTrackerSubscription.scope == payload.scope,
            BanTrackerSubscription.state_filter == payload.state_filter,
            BanTrackerSubscription.ban_type_filter == payload.ban_type_filter,
        )
    )
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subscription with these filters already exists.",
        )

    sub = BanTrackerSubscription(
        user_id=current_user.id,
        scope=payload.scope,
        state_filter=payload.state_filter,
        ban_type_filter=payload.ban_type_filter,
        frequency=payload.frequency,
        is_active=True,
        unsubscribe_token=secrets.token_urlsafe(32),
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.get("/{sub_id}", response_model=BanTrackerSubscriptionResponse)
async def get_subscription(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BanTrackerSubscription:
    """Fetch one of the current patron's subscriptions."""
    return await _get_owned_or_404(db, sub_id, current_user.id)


@router.patch("/{sub_id}", response_model=BanTrackerSubscriptionResponse)
async def update_subscription(
    sub_id: int,
    payload: BanTrackerSubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BanTrackerSubscription:
    """Patch a subscription owned by the current patron.

    ``exclude_unset=True`` so unspecified fields preserve their current
    value (true PATCH semantics, not PUT).
    """
    sub = await _get_owned_or_404(db, sub_id, current_user.id)

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(sub, field, value)

    # Re-run the cross-field rule against the merged state in case the
    # caller patched scope but not state_filter (or vice versa).
    if sub.scope == "state" and not sub.state_filter:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="state_filter is required when scope='state'",
        )

    await db.commit()
    await db.refresh(sub)
    return sub


@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a subscription owned by the current patron."""
    sub = await _get_owned_or_404(db, sub_id, current_user.id)
    await db.delete(sub)
    await db.commit()
