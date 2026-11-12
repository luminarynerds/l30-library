# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy.ext.asyncio import AsyncSession

from .notifications import notification_service as _unified


class AlertNotificationService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def notify_privacy_alert(self, alert) -> bool:
        return await _unified.notify_privacy_alert(alert, self.db)

    async def notify_moderation_alert(self, alert) -> bool:
        return await _unified.notify_moderation_alert(alert, self.db)

    async def send_daily_digest(self) -> bool:
        return await _unified.send_daily_digest(self.db)
