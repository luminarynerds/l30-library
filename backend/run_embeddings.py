# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One-shot script to generate embeddings for all catalog items."""
import asyncio
import sys
sys.path.insert(0, "/app")

async def main():
    from app.core.database import AsyncSessionLocal
    from app.services.semantic_search_service import SemanticSearchService

    async with AsyncSessionLocal() as session:
        service = SemanticSearchService(session)
        result = await service.generate_embeddings_batch(
            entity_type="catalog_item_combined",
            batch_size=100,
            skip_existing=True,
        )
        print(f"Done: {result}")

asyncio.run(main())
