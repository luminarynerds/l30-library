# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)


async def pen_america_sync_job() -> None:
    logger.info("Starting PEN America data sync job")
    try:
        async with AsyncSessionLocal() as db:
            from app.services.pen_america_sync_service import PenAmericaSyncService

            result = await PenAmericaSyncService.sync(db)
            logger.info(
                "PEN America sync completed",
                extra=result,
            )
    except Exception as e:
        logger.error(
            f"PEN America sync job failed: {e}",
            exc_info=True,
        )
        raise


async def ban_tracker_digest_job() -> None:
    logger.info("Starting ban tracker weekly digest job")
    try:
        async with AsyncSessionLocal() as db:
            from app.services.ban_tracker_digest_service import BanTrackerDigestService

            result = await BanTrackerDigestService.send_weekly_digest(db)
            logger.info(
                "Ban tracker digest job completed",
                extra=result,
            )
    except Exception as e:
        logger.error(
            f"Ban tracker digest job failed: {e}",
            exc_info=True,
        )
        raise
