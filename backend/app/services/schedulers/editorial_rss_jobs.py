# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.services.editorial_rss_ingestion import ingest_rss

logger = get_logger(__name__)


async def process_editorial_rss_ingestion() -> None:
    """Weekly: extract forthcoming titles from editorial RSS (Millions/LitHub/TLT/Brown Bookshelf) into the tracker."""
    logger.info("Starting editorial RSS ingestion job")
    try:
        async with AsyncSessionLocal() as db:
            stats = await ingest_rss(db)
            logger.info("Editorial RSS ingestion completed",
                        extra={"added": stats.books_added, "found": stats.books_found, "errors": stats.errors})
    except Exception as e:
        logger.error(f"Editorial RSS ingestion job failed: {e}", exc_info=True)
        raise
