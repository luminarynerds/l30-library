# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ..notifications.batching import BatchNotificationService

logger = get_logger(__name__)


async def process_notification_queue() -> None:
    async with AsyncSessionLocal() as db:
        try:
            result = await BatchNotificationService.send_queued_notifications(
                db, batch_size=50
            )

            sent = result.get("sent", 0)
            failed = result.get("failed", 0)

            if sent > 0 or failed > 0:
                logger.info(
                    "Notification queue processed",
                    extra={"sent": sent, "failed": failed},
                )
        except Exception as e:
            await db.rollback()
            logger.error(f"Notification queue processing failed: {e}", exc_info=True)
