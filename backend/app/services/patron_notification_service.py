# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import DomainEvent
from app.models.notification import (
    PatronNotification,
    PatronNotificationCategory,
    NotificationType,
)

logger = get_logger(__name__)


class NotificationQueueService:

    async def create_notification_from_event(
        self,
        patron_id: str,
        category: str,
        title: str,
        message: str,
        event: DomainEvent,
        related_loan_id: str | None = None,
        related_hold_id: str | None = None,
        related_fine_id: str | None = None,
        related_item_title: str | None = None,
        action_url: str | None = None,
        action_label: str | None = None,
    ) -> PatronNotification | None:
        from app.core.database import get_async_session

        try:
            async with get_async_session() as db:
                # Idempotency check: skip if already processed this event
                existing = await db.execute(
                    select(PatronNotification.id).where(
                        PatronNotification.source_event_id == event.event_id
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    logger.debug(
                        f"Notification already exists for event {event.event_id}, skipping"
                    )
                    return None

                notification = PatronNotification(
                    patron_id=int(patron_id) if patron_id else 0,
                    category=PatronNotificationCategory(category),
                    title=title,
                    message=message,
                    source_event_type=event.event_type,
                    source_event_id=event.event_id,
                    related_loan_id=related_loan_id,
                    related_hold_id=related_hold_id,
                    related_fine_id=related_fine_id,
                    related_item_title=related_item_title,
                    action_url=action_url,
                    action_label=action_label,
                )

                db.add(notification)
                await db.commit()
                await db.refresh(notification)

                logger.info(
                    f"Patron notification created: id={notification.id}, "
                    f"patron={patron_id}, category={category}, "
                    f"event={event.event_type}[{event.event_id}]"
                )
                return notification

        except Exception as e:
            logger.error(
                f"Failed to create patron notification for event "
                f"{event.event_type}[{event.event_id}]: {e}",
                exc_info=True,
            )
            return None

    @staticmethod
    async def get_notifications(
        patron_id: int,
        db: AsyncSession,
        unread_only: bool = False,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PatronNotification], int]:
        conditions = [
            PatronNotification.patron_id == patron_id,
            PatronNotification.is_dismissed == False,  # noqa: E712
        ]

        if unread_only:
            conditions.append(PatronNotification.is_read == False)  # noqa: E712

        if category:
            conditions.append(
                PatronNotification.category == PatronNotificationCategory(category)
            )

        where_clause = and_(*conditions)

        # Get total count
        count_result = await db.execute(
            select(func.count(PatronNotification.id)).where(where_clause)
        )
        total = count_result.scalar() or 0

        # Get paginated results
        result = await db.execute(
            select(PatronNotification)
            .where(where_clause)
            .order_by(PatronNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        notifications = list(result.scalars().all())

        return notifications, total

    @staticmethod
    async def get_unread_count(patron_id: int, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(PatronNotification.id)).where(
                and_(
                    PatronNotification.patron_id == patron_id,
                    PatronNotification.is_read == False,  # noqa: E712
                    PatronNotification.is_dismissed == False,  # noqa: E712
                )
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def mark_as_read(
        notification_id: int,
        patron_id: int,
        db: AsyncSession,
    ) -> PatronNotification | None:
        result = await db.execute(
            select(PatronNotification).where(
                and_(
                    PatronNotification.id == notification_id,
                    PatronNotification.patron_id == patron_id,
                )
            )
        )
        notification = result.scalar_one_or_none()

        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(notification)

        return notification

    @staticmethod
    async def mark_all_as_read(patron_id: int, db: AsyncSession) -> int:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            update(PatronNotification)
            .where(
                and_(
                    PatronNotification.patron_id == patron_id,
                    PatronNotification.is_read == False,  # noqa: E712
                )
            )
            .values(is_read=True, read_at=now)
        )
        await db.commit()
        return result.rowcount

    @staticmethod
    async def dismiss_notification(
        notification_id: int,
        patron_id: int,
        db: AsyncSession,
    ) -> PatronNotification | None:
        result = await db.execute(
            select(PatronNotification).where(
                and_(
                    PatronNotification.id == notification_id,
                    PatronNotification.patron_id == patron_id,
                )
            )
        )
        notification = result.scalar_one_or_none()

        if notification and not notification.is_dismissed:
            notification.is_dismissed = True
            notification.dismissed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(notification)

        return notification


# Singleton instance
patron_notification_service = NotificationQueueService()

# Alias for backward compatibility
PatronNotificationService = NotificationQueueService


async def record_in_app_notification(
    db: AsyncSession,
    *,
    patron_id: int,
    category: PatronNotificationCategory,
    title: str,
    message: str,
    source_event_type: str,
    source_event_id: str,
    related_loan_id: str | None = None,
    related_hold_id: str | None = None,
    related_fine_id: str | None = None,
    related_item_title: str | None = None,
    action_url: str | None = None,
    action_label: str | None = None,
) -> bool:
    existing = await db.execute(
        select(PatronNotification.id).where(
            PatronNotification.source_event_id == source_event_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False

    db.add(
        PatronNotification(
            patron_id=patron_id,
            category=category,
            title=title,
            message=message,
            source_event_type=source_event_type,
            source_event_id=source_event_id,
            related_loan_id=related_loan_id,
            related_hold_id=related_hold_id,
            related_fine_id=related_fine_id,
            related_item_title=related_item_title,
            action_url=action_url,
            action_label=action_label,
        )
    )
    return True
