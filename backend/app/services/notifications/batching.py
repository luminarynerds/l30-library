# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.email import send_email

logger = get_logger(__name__)


# =============================================================================
# Batching Service
# =============================================================================


class BatchNotificationService:

    @staticmethod
    async def queue_notification(
        user_id: int,
        notification_type,
        recipient_email: str,
        subject: str,
        html_body: str,
        context_data: Dict,
        scheduled_for: Optional[datetime] = None,
        db: Optional[AsyncSession] = None,
    ):
        if not db:
            return None

        from ...models.notification import NotificationQueue

        if scheduled_for is None:
            scheduled_for = datetime.now(timezone.utc)

        notification = NotificationQueue(
            user_id=user_id,
            notification_type=notification_type,
            recipient_email=recipient_email,
            subject=subject,
            html_body=html_body,
            context_data=context_data,
            scheduled_for=scheduled_for,
        )

        db.add(notification)
        await db.flush()
        return notification

    @staticmethod
    async def send_queued_notifications(
        db: AsyncSession, batch_size: int = 50
    ) -> Dict[str, int]:
        from ...models.notification import (
            NotificationQueue,
            NotificationHistory,
            NotificationStatus,
        )

        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(NotificationQueue)
            .where(
                and_(
                    NotificationQueue.status == NotificationStatus.PENDING,
                    NotificationQueue.scheduled_for <= now,
                )
            )
            .limit(batch_size)
        )
        notifications = result.scalars().all()

        sent_count = 0
        failed_count = 0

        for notification in notifications:
            try:
                success = await send_email(
                    to_email=notification.recipient_email,
                    subject=notification.subject,
                    html_content=notification.html_body,
                )

                if success:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = now
                    sent_count += 1

                    history = NotificationHistory(
                        user_id=notification.user_id,
                        notification_type=notification.notification_type,
                        recipient_email=notification.recipient_email,
                        subject=notification.subject,
                        context_data=notification.context_data,
                        sent_at=now,
                        success=True,
                    )
                    db.add(history)
                else:
                    notification.retry_count += 1
                    if notification.retry_count >= 3:
                        notification.status = NotificationStatus.FAILED
                        notification.failed_at = now
                        notification.failure_reason = "Max retries exceeded"
                        failed_count += 1
                    else:
                        notification.scheduled_for = now + timedelta(hours=1)

            except (AttributeError, KeyError, ValueError, TypeError) as e:
                # Catch data access errors during notification processing
                # send_email() handles its own network errors and returns bool
                logger.error(
                    f"Failed to send notification {notification.id}: {e}",
                    exc_info=True,
                    extra={
                        "error_type": type(e).__name__,
                        "notification_id": notification.id,
                        "user_id": notification.user_id,
                    },
                )
                notification.retry_count += 1
                if notification.retry_count >= 3:
                    notification.status = NotificationStatus.FAILED
                    notification.failed_at = now
                    notification.failure_reason = str(e)
                    failed_count += 1
                else:
                    notification.scheduled_for = now + timedelta(hours=1)

        await db.commit()

        return {
            "processed": len(notifications),
            "sent": sent_count,
            "failed": failed_count,
            "pending_retries": len(notifications) - sent_count - failed_count,
        }
