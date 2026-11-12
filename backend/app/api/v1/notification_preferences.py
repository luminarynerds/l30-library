# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Notification Preferences API Endpoints

Provides granular notification preference management including
per-type channel controls, digest mode, and quiet hours.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.notification_preferences import (
    NotificationPreferencesResponse,
    UpdateNotificationPreferencesRequest,
    DigestConfig,
    QuietHoursConfig,
    FullNotificationSettings,
)
from app.services.notification_preferences_service import NotificationPreferencesService
from app.core.database import get_db
from .auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/preferences", response_model=FullNotificationSettings)
async def get_notification_settings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete notification settings including preferences, digest, and quiet hours."""
    return await NotificationPreferencesService.get_full_settings(user_id=current_user.id, db=db)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    body: UpdateNotificationPreferencesRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk update notification channel preferences."""
    return await NotificationPreferencesService.update_preferences(
        user_id=current_user.id, preferences=body.preferences, db=db
    )


@router.get("/digest-config", response_model=DigestConfig)
async def get_digest_config(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get digest configuration."""
    return await NotificationPreferencesService.get_digest_config(user_id=current_user.id, db=db)


@router.put("/digest-config", response_model=DigestConfig)
async def update_digest_config(
    body: DigestConfig,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update digest configuration."""
    return await NotificationPreferencesService.update_digest_config(user_id=current_user.id, config=body, db=db)


@router.get("/quiet-hours", response_model=QuietHoursConfig)
async def get_quiet_hours(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get quiet hours configuration."""
    return await NotificationPreferencesService.get_quiet_hours(user_id=current_user.id, db=db)


@router.put("/quiet-hours", response_model=QuietHoursConfig)
async def update_quiet_hours(
    body: QuietHoursConfig,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update quiet hours configuration."""
    return await NotificationPreferencesService.update_quiet_hours(user_id=current_user.id, config=body, db=db)
