# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Nightly timesheet sweep: close punches left open past local end-of-day."""
from datetime import datetime, timezone

from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ..time_entry_service import close_dangling_punches

logger = get_logger(__name__)


async def sweep_dangling_punches() -> None:
    """Auto-close dangling punches so weekly totals stop growing without bound
    and stale presence rows drop off the desk schedule. Closed days stay
    flagged for manager review via the auto-close note."""
    try:
        async with AsyncSessionLocal() as db:
            closed = await close_dangling_punches(db, datetime.now(timezone.utc))
            await db.commit()
        if closed:
            logger.info("Dangling-punch sweep closed %d open day(s)", closed)
    except Exception:  # noqa: BLE001  # job boundary - log, scheduler retries nightly
        logger.exception("Dangling-punch sweep failed")
