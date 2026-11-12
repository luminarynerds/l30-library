# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ..saved_search_notifier import notify_saved_searches

logger = get_logger(__name__)


async def run_saved_search_notifier() -> None:
    async with AsyncSessionLocal() as session:
        try:
            result = await notify_saved_searches(session)
        except Exception:
            logger.exception(
                "saved_search_notifier: nightly run raised unhandled exception"
            )
            return

    if result.feature_disabled:
        # Don't spam the success log when the feature is off.
        return

    logger.info(
        "saved_search_notifier.scheduled: processed=%d notified=%d "
        "no_matches=%d throttled=%d failed=%d in_app=%d emails=%d",
        result.rows_processed,
        result.rows_notified,
        result.rows_skipped_no_matches,
        result.rows_skipped_throttle,
        result.rows_failed,
        result.in_app_sent,
        result.emails_sent,
    )
