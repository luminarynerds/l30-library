# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Phase 1 KB enhancements: category counts + read-alike catalog matching."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.knowledge_base import _resolve_catalog_match
from app.models.catalog import CatalogItem, ItemStatus, ItemType


@pytest.mark.asyncio
async def test_resolve_catalog_match_exact(db_session: AsyncSession):
    item = CatalogItem(
        title="Project Hail Mary",
        author="Andy Weir",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cover_url="https://example.com/phm.jpg",
    )
    db_session.add(item)
    await db_session.commit()

    cid, cover = await _resolve_catalog_match(db_session, "Project Hail Mary", "Andy Weir")
    assert cid == item.id
    assert cover == "https://example.com/phm.jpg"


@pytest.mark.asyncio
async def test_resolve_catalog_match_case_insensitive(db_session: AsyncSession):
    item = CatalogItem(
        title="The Midnight Library",
        author="Matt Haig",
        item_type=ItemType.book,
        status=ItemStatus.available,
    )
    db_session.add(item)
    await db_session.commit()

    cid, cover = await _resolve_catalog_match(db_session, "the midnight LIBRARY", "matt haig")
    assert cid == item.id
    assert cover is None


@pytest.mark.asyncio
async def test_resolve_catalog_match_missing(db_session: AsyncSession):
    cid, cover = await _resolve_catalog_match(db_session, "Nonexistent Title", "Nobody")
    assert cid is None
    assert cover is None


@pytest.mark.asyncio
async def test_resolve_catalog_match_ambiguous_returns_none(db_session: AsyncSession):
    """When two catalog items share title+author, do not guess — return None."""
    db_session.add_all([
        CatalogItem(title="Dune", author="Frank Herbert", item_type=ItemType.book, status=ItemStatus.available),
        CatalogItem(title="Dune", author="Frank Herbert", item_type=ItemType.book, status=ItemStatus.available),
    ])
    await db_session.commit()
    cid, cover = await _resolve_catalog_match(db_session, "Dune", "Frank Herbert")
    assert cid is None
    assert cover is None


from httpx import AsyncClient
from app.models.knowledge_base import KnowledgeEntry


@pytest.mark.asyncio
async def test_read_alikes_include_catalog_match(client: AsyncClient, db_session: AsyncSession):
    item = CatalogItem(
        title="The Kaiju Preservation Society",
        author="John Scalzi",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cover_url="https://example.com/kps.jpg",
    )
    entry = KnowledgeEntry(
        category="Reading Programs",
        entry_type="read-alike",
        title="If You Liked Project Hail Mary",
        content="Try The Kaiju Preservation Society by John Scalzi.",
        if_you_liked="Project Hail Mary",
        if_you_liked_author="Andy Weir",
        then_try="The Kaiju Preservation Society",
        then_try_author="John Scalzi",
        reason="Both have warm, optimistic SF vibes.",
    )
    db_session.add_all([item, entry])
    await db_session.commit()

    resp = await client.get("/api/v1/knowledge/read-alikes", params={"search": "Project Hail Mary"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    rec = body[0]
    assert rec["then_try_catalog_id"] == item.id
    assert rec["then_try_cover_url"] == "https://example.com/kps.jpg"


@pytest.mark.asyncio
async def test_read_alikes_no_catalog_match_returns_none(client: AsyncClient, db_session: AsyncSession):
    entry = KnowledgeEntry(
        category="Reading Programs",
        entry_type="read-alike",
        title="If You Liked X",
        content="Try Y by Z.",
        if_you_liked="X",
        if_you_liked_author="A",
        then_try="Unmatched Title",
        then_try_author="Unknown Author",
        reason="...",
    )
    db_session.add(entry)
    await db_session.commit()

    resp = await client.get("/api/v1/knowledge/read-alikes", params={"search": "X"})
    body = resp.json()
    assert body[0]["then_try_catalog_id"] is None
    assert body[0]["then_try_cover_url"] is None


@pytest.mark.asyncio
async def test_categories_counts_endpoint(client: AsyncClient, db_session: AsyncSession):
    db_session.add_all([
        KnowledgeEntry(category="Borrowing & Returns", entry_type="faq", title="t1", content="c"),
        KnowledgeEntry(category="Borrowing & Returns", entry_type="faq", title="t2", content="c"),
        KnowledgeEntry(category="Digital Resources", entry_type="guide", title="t3", content="c"),
    ])
    await db_session.commit()

    resp = await client.get("/api/v1/knowledge/categories/counts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["categories"]["Borrowing & Returns"] == 2
    assert body["categories"]["Digital Resources"] == 1
    assert body["categories"].get("AI Tools", 0) == 0
    assert body["types"]["faq"] == 2
    assert body["types"]["guide"] == 1
