# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select

from ...core.config import get_settings
from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ...models.notification_failure import (
    FailedNotificationRecord,
    NotificationChannel,
    NotificationFailureStatus,
)

settings = get_settings()
logger = get_logger(__name__)


async def process_failed_notification_retries() -> None:
    stats = {"processed": 0, "retried_ok": 0, "retried_fail": 0, "abandoned": 0}
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # Find records ready for retry
        stmt = (
            select(FailedNotificationRecord)
            .where(
                and_(
                    FailedNotificationRecord.status == NotificationFailureStatus.PENDING,
                    FailedNotificationRecord.next_retry_at <= now,
                    FailedNotificationRecord.retry_count < FailedNotificationRecord.max_retries,
                )
            )
            .with_for_update(skip_locked=True)
            .limit(50)
        )

        result = await db.execute(stmt)
        records = result.scalars().all()

        if not records:
            return

        for record in records:
            stats["processed"] += 1
            record.retry_count += 1
            record.last_retry_at = now
            record.status = NotificationFailureStatus.RETRYING

            try:
                # We can't replay the original email content (it's not stored for
                # privacy reasons), so we log a warning for manual follow-up.
                # In a full implementation, you'd store encrypted content or a
                # reference to a template + params for replay.
                #
                # For now, this job serves two purposes:
                # 1. Track retry attempts and escalate to ABANDONED
                # 2. Provide visibility into the DLQ via metrics/logs

                if record.retry_count >= record.max_retries:
                    record.status = NotificationFailureStatus.ABANDONED
                    stats["abandoned"] += 1
                    logger.warning(
                        f"Notification abandoned after {record.retry_count} retries",
                        extra={
                            "channel": str(record.channel) if record.channel else "unknown",
                            "template": record.template_name,
                            "recipient_hint": record.recipient_hint,
                            "original_error": record.error_message[:200],
                        },
                    )
                else:
                    # Calculate next retry with exponential backoff
                    delay_seconds = min(30 * (2 ** record.retry_count), 3600)  # max 1 hour
                    record.next_retry_at = now + timedelta(seconds=delay_seconds)
                    record.status = NotificationFailureStatus.PENDING
                    stats["retried_fail"] += 1

            except Exception as e:
                logger.error(
                    f"Error processing notification retry for record {record.id}: {e}",
                    exc_info=True,
                )
                record.status = NotificationFailureStatus.PENDING
                record.next_retry_at = now + timedelta(minutes=10)

        await db.commit()

    if stats["processed"] > 0:
        logger.info(
            "Notification retry processing completed",
            extra=stats,
        )
