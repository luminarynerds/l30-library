# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ..parent_onboarding_followup_reminder_tasks import (
    run_due_tomorrow_pass,
    run_overdue_pass,
)

logger = get_logger(__name__)


async def send_parent_onboarding_followup_due_tomorrow_reminders() -> None:
    logger.info("Starting parent-onboarding follow-up due-tomorrow reminder pass")
    try:
        async with AsyncSessionLocal() as db:
            summary = await run_due_tomorrow_pass(db)
            logger.info(
                "Parent-onboarding follow-up due-tomorrow pass complete",
                extra=summary,
            )
    except Exception:
        logger.exception(
            "Parent-onboarding follow-up due-tomorrow pass raised",
        )


async def send_parent_onboarding_followup_overdue_reminders() -> None:
    logger.info("Starting parent-onboarding follow-up overdue reminder pass")
    try:
        async with AsyncSessionLocal() as db:
            summary = await run_overdue_pass(db)
            logger.info(
                "Parent-onboarding follow-up overdue pass complete",
                extra=summary,
            )
    except Exception:
        logger.exception(
            "Parent-onboarding follow-up overdue pass raised",
        )
