# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron shelf preferences API — opt-in display settings."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.patron_shelf_preferences import PatronShelfPreferences
from ...models.user import User
from ...schemas.patron_shelf_preferences import ShelfPreferencesResponse, ShelfPreferencesUpdate
from .auth import get_current_user

router = APIRouter(tags=["shelf-preferences"])


@router.get("/shelf-preferences", response_model=ShelfPreferencesResponse)
async def get_shelf_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's shelf display preferences."""
    result = await db.execute(
        select(PatronShelfPreferences).where(
            PatronShelfPreferences.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        return ShelfPreferencesResponse(show_reading_activity=False, show_pace_stats=False)
    return prefs


@router.put("/shelf-preferences", response_model=ShelfPreferencesResponse)
async def update_shelf_preferences(
    data: ShelfPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update shelf display preferences."""
    result = await db.execute(
        select(PatronShelfPreferences).where(
            PatronShelfPreferences.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if prefs:
        prefs.show_reading_activity = data.show_reading_activity
        prefs.show_pace_stats = data.show_pace_stats
    else:
        prefs = PatronShelfPreferences(
            user_id=current_user.id,
            show_reading_activity=data.show_reading_activity,
            show_pace_stats=data.show_pace_stats,
        )
        db.add(prefs)

    await db.commit()
    await db.refresh(prefs)
    return prefs
