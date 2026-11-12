# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from .notifications import (
    UnifiedNotificationService,
    NotificationType,
    NotificationTemplate,
    NotificationContent,
    NotificationChannel,
    NotificationRecipient,
    NotificationResult,
    NotificationConfig,
    notification_factory,
    notification_service,
)


class DeliveryNotificationService(UnifiedNotificationService):

    def __init__(self, config: Optional[NotificationConfig] = None):
        super().__init__()
        self.config = config or NotificationConfig()


class DeliveryNotificationScheduler:

    def __init__(self, notification_service_instance, db):
        self._unified = notification_service_instance
        self.db = db

    async def send_delivery_reminders(self):
        return await self._unified.send_delivery_reminders(self.db)

    async def send_feedback_requests(self):
        feedback_delay = getattr(self._unified, 'config', None)
        delay_hours = feedback_delay.feedback_delay_hours if feedback_delay else 24
        return await self._unified.send_feedback_requests(self.db, delay_hours)


__all__ = [
    "DeliveryNotificationService",
    "DeliveryNotificationScheduler",
    "NotificationType",
    "NotificationTemplate",
    "NotificationContent",
    "NotificationChannel",
    "NotificationRecipient",
    "NotificationResult",
    "NotificationConfig",
    "notification_factory",
]
