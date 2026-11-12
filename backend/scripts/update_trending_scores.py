#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Update Trending Scores Background Job

This script updates the trending_score field for all active indie ebooks.
It should be run periodically (e.g., hourly via cron) to keep trending data fresh.

Usage:
    python scripts/update_trending_scores.py

Or as a cron job:
    0 * * * * cd /opt/l30/backend && python scripts/update_trending_scores.py >> /var/log/trending_update.log 2>&1
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.services.trending_service import get_trending_service
from datetime import datetime, timezone

# Configure logging with file output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/opt/l30/backend/logs/trending_update.log', mode='a')
    ] if Path('/opt/l30/backend/logs').exists() else [logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def update_trending_scores():
    """Main function to update all trending scores."""
    start_time = datetime.now(timezone.utc)
    logger.info("="*80)
    logger.info("Starting trending scores update job")
    logger.info(f"Start time: {start_time.isoformat()}")

    try:
        # Use AsyncSessionLocal for database connection
        async with AsyncSessionLocal() as db:
            trending_service = get_trending_service()

            # Update all ebook trending scores with batch processing
            updated_count = await trending_service.bulk_update_trending_scores(
                db=db,
                batch_size=100
            )

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.info("="*80)
            logger.info("Trending scores updated successfully")
            logger.info(f"Updated ebooks: {updated_count}")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"End time: {end_time.isoformat()}")
            logger.info("="*80)

            return updated_count

    except Exception as e:
        logger.error("="*80)
        logger.error(f"Error updating trending scores: {e}", exc_info=True)
        logger.error("="*80)
        raise


async def main():
    """Entry point for the script."""
    try:
        updated_count = await update_trending_scores()
        print(f"Trending scores updated successfully: {updated_count} ebooks processed")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
