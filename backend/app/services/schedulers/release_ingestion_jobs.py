# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)


async def process_release_ingestion() -> None:
    logger.info("Starting release ingestion job")
    try:
        async with AsyncSessionLocal() as db:
            from app.services.release_ingestion import ReleaseIngestionService

            service = ReleaseIngestionService(db)
            stats = await service.process_all_authors(force=False)

            logger.info(
                "Release ingestion job completed",
                extra={
                    "authors_scanned": stats.authors_scanned,
                    "books_found": stats.books_found,
                    "books_added": stats.books_added,
                    "books_updated": stats.books_updated,
                    "duplicates_skipped": stats.duplicates_skipped,
                    "errors": stats.errors,
                },
            )
    except Exception as e:
        logger.error(
            f"Release ingestion job failed: {e}",
            exc_info=True,
        )
        raise
