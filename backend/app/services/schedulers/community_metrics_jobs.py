# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date

from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger

logger = get_logger(__name__)


async def generate_community_metrics_snapshots() -> None:
    from ...services.community_metrics_service import CommunityMetricsService

    today = date.today()
    # Previous month
    if today.month == 1:
        year = today.year - 1
        month = 12
    else:
        year = today.year
        month = today.month - 1

    logger.info(
        "Generating community metrics snapshots",
        extra={"year": year, "month": month},
    )

    try:
        async with AsyncSessionLocal() as db:
            service = CommunityMetricsService(db)
            # Generate for all branches (branch_id=None = all)
            await service.generate_monthly_snapshot(year, month, branch_id=None)
            logger.info(
                "Community metrics snapshots complete",
                extra={"year": year, "month": month},
            )
    except Exception:
        logger.exception(
            "Failed to generate community metrics snapshots",
            extra={"year": year, "month": month},
        )
