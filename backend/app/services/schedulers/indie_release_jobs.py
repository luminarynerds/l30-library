# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.services.indie_release_ingestion import ingest_indie
from app.services.recruitment_digest_service import send_recruitment_digest

logger = get_logger(__name__)


async def process_indie_release_ingestion() -> None:
    """Weekly: buzz-gated indie sources (Mastodon hashtags + itch.io books) into the tracker."""
    logger.info("Starting indie release ingestion job")
    try:
        async with AsyncSessionLocal() as db:
            stats = await ingest_indie(db)
            logger.info("Indie release ingestion completed",
                        extra={"added": stats.books_added, "found": stats.books_found, "errors": stats.errors})
    except Exception as e:
        logger.error(f"Indie release ingestion job failed: {e}", exc_info=True)
        raise


async def process_recruitment_digest() -> None:
    """Weekly: email the MetisLib indie recruitment digest (no-op when unconfigured/empty)."""
    logger.info("Starting recruitment digest job")
    try:
        async with AsyncSessionLocal() as db:
            sent = await send_recruitment_digest(db)
            logger.info("Recruitment digest job completed", extra={"sent": sent})
    except Exception as e:
        logger.error(f"Recruitment digest job failed: {e}", exc_info=True)
        raise
