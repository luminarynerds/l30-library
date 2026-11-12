# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ...models.job_failure import JobSeverity
from ..job_failure_service import JobExecutionContext

logger = get_logger(__name__)


async def process_computer_no_shows() -> None:
    async with JobExecutionContext(
        job_id="computer_no_show_processing",
        job_name="Computer No-Show Processing",
        severity=JobSeverity.LOW,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            from ..computer_service import process_computer_no_shows as _process
            processed = await _process(db)
            await db.commit()

        ctx.add_metric("no_shows_processed", processed)
        ctx.items_processed = processed
        ctx.items_succeeded = processed
        if processed:
            logger.info(
                "Computer no-show processing completed",
                extra={"no_shows_processed": processed},
            )


async def process_computer_auto_logouts() -> None:
    async with JobExecutionContext(
        job_id="computer_auto_logout_processing",
        job_name="Computer Auto-Logout Processing",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            from ..computer_service import process_computer_auto_logouts as _process
            processed = await _process(db)
            await db.commit()

        ctx.add_metric("sessions_auto_logged_out", processed)
        ctx.items_processed = processed
        ctx.items_succeeded = processed
        if processed:
            logger.info(
                "Computer auto-logout processing completed",
                extra={"sessions_auto_logged_out": processed},
            )
