# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)


async def backfill_catalog_embeddings() -> None:
    logger.info("Starting catalog embedding backfill job")
    try:
        async with AsyncSessionLocal() as db:
            from app.services.semantic_search_service import SemanticSearchService

            service = SemanticSearchService(db)
            result = await service.generate_embeddings_batch(
                entity_type="catalog_item_combined",
                batch_size=100,
                skip_existing=True,
            )

            embedded = result.get("embedded_count", 0)
            total = result.get("total_items", 0)
            failed = result.get("failed_count", 0)

            if embedded > 0:
                logger.info(
                    f"Catalog embedding backfill completed: {embedded} new embeddings generated",
                    extra={
                        "total_items": total,
                        "embedded_count": embedded,
                        "failed_count": failed,
                    },
                )
            else:
                logger.info("Catalog embedding backfill: no new items to embed")
    except Exception as e:
        logger.error(
            f"Catalog embedding backfill job failed: {e}",
            exc_info=True,
        )
        raise
