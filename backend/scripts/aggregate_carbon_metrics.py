#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Hourly carbon metrics aggregation script.
Run via cron: 0 * * * * docker exec l30-backend python scripts/aggregate_carbon_metrics.py
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal as async_session
from app.services.carbon_metrics_service import aggregate_hour


MOUNTED_LOG_PATH = "/var/log/l30-nginx/access.log"
FALLBACK_LOG_PATH = "/var/log/nginx/access.log"


async def main():
    now = datetime.now(timezone.utc)
    hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

    log_path = MOUNTED_LOG_PATH if Path(MOUNTED_LOG_PATH).exists() else FALLBACK_LOG_PATH

    async with async_session() as db:
        records = await aggregate_hour(db, log_path, hour_start)
        if records:
            print(f"Aggregated {records} carbon metric records for {hour_start.isoformat()}")
        else:
            print(f"No new data to aggregate for {hour_start.isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
