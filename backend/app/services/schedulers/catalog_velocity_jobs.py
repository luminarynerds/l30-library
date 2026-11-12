# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from sqlalchemy import text

from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ...models.job_failure import JobSeverity
from ..job_failure_service import JobExecutionContext

logger = get_logger(__name__)


async def refresh_catalog_velocity_mv() -> None:
    async with JobExecutionContext(
        job_id="refresh_catalog_velocity_mv",
        job_name="Refresh catalog_circulation_velocity_mv",
        severity=JobSeverity.LOW,
    ) as ctx:
        logger.info("catalog_velocity_mv refresh starting")
        async with AsyncSessionLocal() as db:
            await db.execute(
                text(
                    "REFRESH MATERIALIZED VIEW CONCURRENTLY "
                    "catalog_circulation_velocity_mv"
                )
            )
            await db.commit()

            count_result = await db.execute(
                text("SELECT COUNT(*) FROM catalog_circulation_velocity_mv")
            )
            row_count = int(count_result.scalar() or 0)
            ctx.add_metric("rows", row_count)
            ctx.items_processed = row_count
            ctx.items_succeeded = row_count
            logger.info(
                "catalog_velocity_mv refresh complete: %d rows", row_count
            )
