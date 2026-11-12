# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Multi-select item-type filter (`item_types`) on GET /catalog/search.

`item_types` OR-joins several ItemType values in one request, so a UI tab
like "DVDs" can match both `dvd` and `bluray`. The singular `item_type`
param is unchanged.
"""
import pytest
from httpx import AsyncClient

from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)


pytestmark = pytest.mark.asyncio


async def _seed_item(db, *, title: str, item_type: ItemType) -> CatalogItem:
    """Seed a publicly-visible catalog item for search-endpoint tests."""
    item = CatalogItem(
        title=title,
        author="Author",
        item_type=item_type,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
    )
    db.add(item)
    await db.flush()
    return item


async def test_item_types_or_join(client: AsyncClient, db_session):
    """item_types returns items matching ANY listed type; others excluded."""
    await _seed_item(db_session, title="A Disc", item_type=ItemType.dvd)
    await _seed_item(db_session, title="A Blu", item_type=ItemType.bluray)
    await _seed_item(db_session, title="A Book", item_type=ItemType.book)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search",
        params=[("item_types", "dvd"), ("item_types", "bluray")],
    )
    assert resp.status_code == 200, resp.text
    titles = {row["title"] for row in resp.json()["items"]}
    assert titles == {"A Disc", "A Blu"}


async def test_item_types_empty_is_noop(client: AsyncClient, db_session):
    """Omitting item_types applies no type filter (empty list != match-none)."""
    await _seed_item(db_session, title="N Disc", item_type=ItemType.dvd)
    await _seed_item(db_session, title="N Book", item_type=ItemType.book)
    await db_session.commit()

    resp = await client.get("/api/v1/catalog/search")
    assert resp.status_code == 200, resp.text
    titles = {row["title"] for row in resp.json()["items"]}
    assert titles == {"N Disc", "N Book"}
