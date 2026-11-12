# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.notification import NotificationPreferences

logger = get_logger(__name__)


# =============================================================================
# Preferences Service
# =============================================================================


class PreferencesManager:

    @staticmethod
    async def get_or_create_preferences(
        user_id: int, db: AsyncSession
    ) -> NotificationPreferences:
        result = await db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()

        if not prefs:
            prefs = NotificationPreferences(user_id=user_id)
            db.add(prefs)
            await db.flush()

        return prefs

    @staticmethod
    async def update_preferences(
        user_id: int, preferences_data: dict, db: AsyncSession
    ) -> NotificationPreferences:
        prefs = await PreferencesManager.get_or_create_preferences(user_id, db)

        for key, value in preferences_data.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)

        await db.commit()
        await db.refresh(prefs)
        return prefs
