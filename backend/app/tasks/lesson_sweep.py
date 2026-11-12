# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import asyncio
from app.core.logging import get_logger

from ..core.database import AsyncSessionLocal
from ..services.lesson_sweep_service import perform_sweep

logger = get_logger(__name__)


async def sweep_empty_lessons_job() -> None:
    async with AsyncSessionLocal() as db:
        result = await perform_sweep(db)
        logger.info(
            "lesson_sweep run finished: status=%s deleted=%s",
            result.status,
            result.deleted_count,
        )


def run() -> None:
    asyncio.run(sweep_empty_lessons_job())


if __name__ == "__main__":
    run()
