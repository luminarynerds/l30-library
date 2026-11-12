# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)


async def process_editorial_release_ingestion() -> None:
    """Weekly: pull the current LibraryReads list into the release tracker.
    (LJ Prepub is staff-triggered, not scheduled — its ToS forbids automated access.)"""
    logger.info("Starting editorial release ingestion job (LibraryReads)")
    try:
        async with AsyncSessionLocal() as db:
            from app.services.editorial_release_ingestion import EditorialReleaseIngestionService
            from app.services.release_sources.libraryreads_source import LibraryReadsSource

            titles = await LibraryReadsSource().fetch()
            stats = await EditorialReleaseIngestionService(db).ingest(titles)
            logger.info(
                "Editorial release ingestion completed",
                extra={"found": stats.books_found, "added": stats.books_added,
                       "updated": stats.books_updated, "errors": stats.errors},
            )
    except Exception as e:
        logger.error(f"Editorial release ingestion job failed: {e}", exc_info=True)
        raise
