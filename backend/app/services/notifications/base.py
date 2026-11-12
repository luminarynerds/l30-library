# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.email import send_email
from ...models.notification import (
    NotificationPreferences,
    NotificationQueue,
    NotificationHistory,
    NotificationStatus,
    NotificationType as DBNotificationType,
)
from ...models.user import User, UserRole
from .types import (
    NotificationType,
    NotificationChannel,
    NotificationTemplate,
    NotificationContent,
    NotificationRecipient,
    NotificationResult,
    NotificationConfig,
)
from .templates import DomainTemplateProvider

settings = get_settings()
logger = get_logger(__name__)


class BaseNotificationService:

    def __init__(self):
        self.templates = DomainTemplateProvider.get_templates()

    # =========================================================================
    # Core notification methods
    # =========================================================================

    async def send_notification(
        self,
        notification_type: NotificationType,
        recipient_email: Optional[str],
        subject: str,
        html_body: str,
        context_data: Dict,
        user_id: Optional[int] = None,
        scheduled_for: Optional[datetime] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[NotificationQueue]:
        if not recipient_email:
            logger.warning(f"No recipient email for {notification_type}")
            return None

        if scheduled_for is None:
            scheduled_for = datetime.now(timezone.utc)

        if db:
            return await self.queue_notification(
                user_id=user_id or 0,
                notification_type=self._map_to_db_type(notification_type),
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                context_data=context_data,
                scheduled_for=scheduled_for,
                db=db,
            )
        else:
            success = await send_email(
                to_email=recipient_email,
                subject=subject,
                html_content=html_body,
            )
            if not success:
                logger.error(f"Failed to send {notification_type}")
            return None

    async def send_templated(
        self,
        notification_type: NotificationType,
        recipient_email: str,
        context_data: Dict,
        db: Optional[AsyncSession] = None,
        user_id: Optional[int] = None,
        categories: Optional[List[str]] = None,
    ) -> bool:
        template = self.templates.get(notification_type)
        if not template:
            logger.warning(f"No template for {notification_type}")
            return False

        subject, body, html, sms = template.render(context_data)

        if db:
            result = await self.send_notification(
                notification_type=notification_type,
                recipient_email=recipient_email,
                subject=subject,
                html_body=html or body,
                context_data=context_data,
                user_id=user_id,
                db=db,
            )
            return result is not None
        else:
            success = await send_email(
                to_email=recipient_email,
                subject=subject,
                html_content=html or body,
                categories=categories,
            )
            if success:
                logger.info(f"Sent {notification_type.value}")
            else:
                logger.error(f"Failed to send {notification_type.value}")
            return success

    async def queue_notification(
        self,
        user_id: int,
        notification_type: DBNotificationType,
        recipient_email: str,
        subject: str,
        html_body: str,
        context_data: Dict,
        scheduled_for: Optional[datetime] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[NotificationQueue]:
        if not db:
            return None

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

    async def send_queued_notifications(
        self, db: AsyncSession, batch_size: int = 50
    ) -> Dict[str, int]:
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

            except Exception as e:
                logger.error(
                    f"Failed to send notification {notification.id}: {e}",
                    exc_info=True,
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

    # =========================================================================
    # Patron preferences
    # =========================================================================

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
        prefs = await BaseNotificationService.get_or_create_preferences(user_id, db)

        for key, value in preferences_data.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)

        await db.commit()
        await db.refresh(prefs)
        return prefs

    # =========================================================================
    # Shared helpers
    # =========================================================================

    @staticmethod
    async def _get_admin_users(db: AsyncSession) -> List[User]:
        result = await db.execute(
            select(User).where(
                User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])
            )
        )
        admins = result.scalars().all()
        if not admins:
            logger.warning("No admin users found for notification")
        return admins

    @staticmethod
    def _map_to_db_type(notification_type: NotificationType) -> DBNotificationType:
        mapping = {
            NotificationType.CHECKOUT_RECEIPT: DBNotificationType.CHECKOUT_RECEIPT,
            NotificationType.DUE_DATE_REMINDER: DBNotificationType.DUE_DATE_REMINDER,
            NotificationType.OVERDUE_NOTICE: DBNotificationType.OVERDUE_NOTICE,
            NotificationType.HOLD_READY: DBNotificationType.HOLD_READY,
            NotificationType.HOLD_EXPIRING: DBNotificationType.HOLD_EXPIRING,
            NotificationType.EVENT_REGISTRATION_CANCELLED: DBNotificationType.EVENT_REGISTRATION_CANCELLED,
        }
        return mapping.get(notification_type, DBNotificationType.CHECKOUT_RECEIPT)
