# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Owned-table curation endpoints: /indie/catalog/collections and /staff-picks.

These hydrate staff curation rows (keyed on metislib_ebook_id) from the owned
indie_ebooks table with LOCAL ids -- never a live MetisLib call. Curation items
without an owned row (e.g. open-access titles) are skipped, not proxied.
"""
import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/indie_owned_curation_test.db")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite+aiosqlite:////tmp/indie_owned_curation_test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("PII_ENCRYPTION_ENABLED", "false")


@pytest.fixture(scope="module")
async def curation_db():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    from app.models.ebook_curation import (  # noqa: F401 -- registers tables
        CollectionStatus,
        EbookCollection,
        EbookCollectionItem,
        EbookFeatured,
    )
    from app.models.indie_ebook_borrow import IndieEbook  # noqa: F401
    from tests.database_setup import sqlite_compat_metadata_clone

    # DDL from a SQLite-compatible CLONE of the metadata. Never call the
    # in-place swap helpers from a test module: they mutate the shared
    # Base.metadata one-way, poisoning every Postgres-bound test later in
    # the same pytest process (the 2026-07-07 deploy-gate cascade).
    engine = create_async_engine(
        "sqlite+aiosqlite:////tmp/indie_owned_curation_test.db",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(sqlite_compat_metadata_clone(Base).create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        owned = IndieEbook(
            metislib_ebook_id=200,
            title="Muskeg Psalms",
            author_pen_name="Aila Ruoho",
            genre="Poetry",
            language="en",
            copies_owned=2,
            copies_available=2,
        )
        session.add(owned)
        session.add(IndieEbook(
            metislib_ebook_id=201,
            title="The Gilded Loom",
            author_pen_name="Priya Chandrasekaran",
            genre="Fantasy",
            language="en",
            copies_owned=1,
            copies_available=1,
        ))
        await session.commit()

        coll = EbookCollection(
            title="Deep Water Reads",
            description="Staff-curated",
            status=CollectionStatus.PUBLISHED,
            display_order=0,
        )
        session.add(coll)
        await session.flush()
        # One owned item, one unowned (e.g. an open-access title id) that must
        # be skipped rather than fetched live.
        session.add(EbookCollectionItem(collection_id=coll.id, metislib_ebook_id=200, display_order=0))
        session.add(EbookCollectionItem(collection_id=coll.id, metislib_ebook_id=999, display_order=1))

        draft = EbookCollection(
            title="Unpublished Drafts",
            status=CollectionStatus.DRAFT,
            display_order=1,
        )
        session.add(draft)
        await session.flush()
        session.add(EbookCollectionItem(collection_id=draft.id, metislib_ebook_id=200, display_order=0))

        session.add(EbookFeatured(metislib_ebook_id=201, entry_type="indie_ebook", display_order=0))
        session.add(EbookFeatured(metislib_ebook_id=998, entry_type="indie_ebook", display_order=1))
        await session.commit()

    yield Session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def curation_client(curation_db):
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        async with curation_db() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestOwnedCollections:
    async def test_published_collections_hydrate_from_owned_table(self, curation_client):
        r = await curation_client.get("/api/v1/indie/catalog/collections")
        assert r.status_code == 200
        data = r.json()
        titles = [c["title"] for c in data]
        assert "Deep Water Reads" in titles

    async def test_draft_collections_excluded(self, curation_client):
        r = await curation_client.get("/api/v1/indie/catalog/collections")
        titles = [c["title"] for c in r.json()]
        assert "Unpublished Drafts" not in titles

    async def test_unowned_items_skipped_not_proxied(self, curation_client):
        r = await curation_client.get("/api/v1/indie/catalog/collections")
        coll = next(c for c in r.json() if c["title"] == "Deep Water Reads")
        assert len(coll["items"]) == 1
        assert coll["items"][0]["title"] == "Muskeg Psalms"

    async def test_items_carry_local_ids_not_metislib_ids(self, curation_client):
        r = await curation_client.get("/api/v1/indie/catalog/collections")
        coll = next(c for c in r.json() if c["title"] == "Deep Water Reads")
        item = coll["items"][0]
        # metislib_ebook_id is 200; the local PK is a small autoincrement.
        # Serving the metislib id here is the wrong-book collision bug (#1546).
        assert item["id"] != 200


@pytest.mark.asyncio
class TestOwnedStaffPicks:
    async def test_staff_picks_hydrate_from_owned_table(self, curation_client):
        r = await curation_client.get("/api/v1/indie/catalog/staff-picks")
        assert r.status_code == 200
        titles = [i["title"] for i in r.json()]
        assert titles == ["The Gilded Loom"]

    async def test_staff_picks_carry_local_ids(self, curation_client):
        r = await curation_client.get("/api/v1/indie/catalog/staff-picks")
        item = r.json()[0]
        assert item["id"] != 201
