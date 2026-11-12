# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from sqlalchemy import select

from .base import BaseNotificationService
from .types import (
    NotificationType,
    NotificationChannel,
    NotificationRecipient,
    NotificationResult,
)

logger = get_logger(__name__)


class DeliveryNotificationService(BaseNotificationService):

    async def send_delivery_notification_to_recipient(
        self,
        notification_type: str,
        recipient: NotificationRecipient,
        context: dict,
        channels: Optional[List[NotificationChannel]] = None,
    ) -> List[NotificationResult]:
        if channels is None:
            channels = [recipient.preferred_channel]

        results = []

        if NotificationChannel.EMAIL in channels and recipient.email:
            try:
                await self.send_templated(
                    notification_type=NotificationType.DELIVERY_REMINDER,
                    recipient_email=recipient.email,
                    context_data=context,
                )
                results.append(
                    NotificationResult(
                        success=True,
                        channel=NotificationChannel.EMAIL,
                        recipient_id=recipient.user_id,
                        sent_at=datetime.now(timezone.utc)
                    )
                )
            except Exception as e:  # noqa: BLE001  # notification dispatch boundary - must record failure not raise across channels
                logger.error(f"Failed to send delivery notification: {e}")
                results.append(
                    NotificationResult(
                        success=False,
                        channel=NotificationChannel.EMAIL,
                        recipient_id=recipient.user_id,
                        error_message=str(e)
                    )
                )

        return results

    async def send_delivery_reminders(self, db: AsyncSession) -> List[NotificationResult]:
        from ...models.home_delivery import (
            Delivery, DeliveryStatus, HomeDeliveryEnrollment
        )

        tomorrow = date.today() + timedelta(days=1)

        result = await db.execute(
            select(Delivery)
            .options(
                joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron)
            )
            .where(
                Delivery.scheduled_date == tomorrow,
                Delivery.status.in_([
                    DeliveryStatus.scheduled,
                    DeliveryStatus.items_selected,
                    DeliveryStatus.packed
                ])
            )
        )
        deliveries = result.unique().scalars().all()

        results = []
        for delivery in deliveries:
            patron = delivery.enrollment.patron
            if not patron:
                continue

            recipient = NotificationRecipient(
                user_id=patron.id,
                email=patron.email,
                phone=getattr(patron, 'phone', None),
                name=patron.full_name
            )

            if delivery.scheduled_time_start and delivery.scheduled_time_end:
                time_window = f"{delivery.scheduled_time_start} - {delivery.scheduled_time_end}"
            elif delivery.scheduled_time_start:
                time_window = f"after {delivery.scheduled_time_start}"
            elif delivery.scheduled_time_end:
                time_window = f"before {delivery.scheduled_time_end}"
            else:
                time_window = "during business hours"

            context = {
                "patron_name": patron.first_name,
                "delivery_date": tomorrow.strftime("%A, %B %d"),
                "time_window": time_window,
                "delivery_address": delivery.delivery_address,
                "item_count": delivery.items_count or 0
            }

            notification_results = await self.send_delivery_notification_to_recipient(
                "delivery_reminder",
                recipient,
                context
            )
            results.extend(notification_results)

        return results

    async def send_feedback_requests(self, db: AsyncSession, feedback_delay_hours: int = 24) -> List[NotificationResult]:
        from ...models.home_delivery import (
            Delivery, DeliveryStatus, HomeDeliveryEnrollment
        )

        cutoff = datetime.now(timezone.utc) - timedelta(hours=feedback_delay_hours)

        result = await db.execute(
            select(Delivery)
            .options(
                joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron)
            )
            .where(
                Delivery.status == DeliveryStatus.delivered,
                Delivery.delivered_at <= cutoff,
            )
        )
        deliveries = result.unique().scalars().all()

        results = []
        for delivery in deliveries:
            patron = delivery.enrollment.patron
            if not patron:
                continue

            recipient = NotificationRecipient(
                user_id=patron.id,
                email=patron.email,
                phone=getattr(patron, 'phone', None),
                name=patron.full_name
            )

            context = {
                "patron_name": patron.first_name,
                "feedback_link": f"/home-delivery/deliveries/{delivery.id}/feedback"
            }

            notification_results = await self.send_delivery_notification_to_recipient(
                "feedback_request",
                recipient,
                context
            )
            results.extend(notification_results)

        return results
