# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reranker failure must degrade catalog search to FTS order, not 500.

The bge-reranker weights live in the l30_models volume (un-baked from the
image). A fresh deploy with an unpopulated volume makes CrossEncoder() raise
on first use; patron search has to survive that.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.catalog.helpers import _execute_catalog_search
from app.core.config import get_settings
from app.models.catalog import CatalogingStatus, CatalogItem, ItemStatus


def _require_postgres(test_db: AsyncSession) -> None:
    """FTS (search_tsv + websearch_to_tsquery) is PG-only; skip on SQLite."""
    if test_db.bind.dialect.name != "postgresql":
        pytest.skip("rerank fallback test requires Postgres FTS")


def _rerank_enabled_settings():
    return get_settings().model_copy(update={"catalog_rerank_enabled": True})


async def _seed_candidates(test_db: AsyncSession, title_stem: str, n: int = 8) -> None:
    test_db.add_all(
        [
            CatalogItem(
                title=f"{title_stem} Volume {i}",
                author="A. Botanist",
                status=ItemStatus.available,
                # Anonymous search filters to CATALOGED; default UNCATALOGED
                # would hide every fixture item.
                cataloging_status=CatalogingStatus.CATALOGED,
            )
            for i in range(n)
        ]
    )
    await test_db.commit()
    # The test schema comes from SQLAlchemy create_all, where search_tsv is a
    # plain nullable column. Prod has it GENERATED ALWAYS ... STORED
    # (20260508_search_tsv_generated_001), so populate it by hand here or FTS
    # matches nothing.
    await test_db.execute(
        text(
            "UPDATE catalog_items SET search_tsv = "
            "to_tsvector('english', coalesce(title,'') || ' ' || coalesce(author,'')) "
            "WHERE search_tsv IS NULL"
        )
    )
    await test_db.commit()


@pytest.mark.asyncio
async def test_search_survives_reranker_failure_with_fts_order(
    test_db: AsyncSession,
):
    """Reranker blowing up (missing weights) degrades to FTS order, no 500."""
    _require_postgres(test_db)
    await _seed_candidates(test_db, "Quantum Gardening")

    failing_rerank = AsyncMock(side_effect=RuntimeError("model weights missing"))
    with (
        patch(
            "app.api.v1.catalog.helpers.get_settings",
            return_value=_rerank_enabled_settings(),
        ),
        patch("app.services.catalog_reranker.rerank", failing_rerank),
    ):
        result = await _execute_catalog_search(
            test_db,
            q="quantum gardening",
            sort_by="relevance",
            rerank=True,
        )

    # The rerank branch genuinely fired (guards against a vacuous pass) ...
    failing_rerank.assert_awaited_once()
    # ... and the search still returned the FTS candidates.
    assert len(result["items"]) == 8
    assert all("Quantum Gardening" in item["title"] for item in result["items"])


@pytest.mark.asyncio
async def test_search_applies_rerank_order_when_model_healthy(
    test_db: AsyncSession,
):
    """Control: a working reranker reorders results (fallback isn't always-on).

    Distinct query from the failure test -- search responses are cached by
    query for 300s and a shared key would serve the other test's result.
    """
    _require_postgres(test_db)
    await _seed_candidates(test_db, "Stellar Beekeeping")

    async def reversed_rank(query, items):
        return [(item.id, 1.0) for item in reversed(list(items))]

    with (
        patch(
            "app.api.v1.catalog.helpers.get_settings",
            return_value=_rerank_enabled_settings(),
        ),
        patch("app.services.catalog_reranker.rerank", side_effect=reversed_rank),
    ):
        result = await _execute_catalog_search(
            test_db,
            q="stellar beekeeping",
            sort_by="relevance",
            rerank=True,
        )

    returned_ids = [item["id"] for item in result["items"]]
    assert len(returned_ids) == 8
    assert returned_ids == sorted(returned_ids, reverse=True)
