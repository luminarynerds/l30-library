# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/indie_catalog_test.db")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite+aiosqlite:////tmp/indie_catalog_test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("PII_ENCRYPTION_ENABLED", "false")


@pytest.fixture(scope="module")
async def catalog_db():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    from app.models.indie_ebook_borrow import IndieEbook
    from tests.database_setup import sqlite_compat_metadata_clone

    # DDL from a SQLite-compatible CLONE of the metadata. Never call the
    # in-place swap helpers from a test module: they mutate the shared
    # Base.metadata one-way, poisoning every Postgres-bound test later in
    # the same pytest process (the 2026-07-07 deploy-gate cascade).
    engine = create_async_engine(
        "sqlite+aiosqlite:////tmp/indie_catalog_test.db",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(sqlite_compat_metadata_clone(Base).create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        # Published row 1 -- has title and copies owned
        session.add(IndieEbook(
            metislib_ebook_id=100,
            title="Coral Depths",
            author_pen_name="Maren Solvik",
            description="A thriller set underwater.",
            genre="Thriller",
            language="en",
            copies_owned=3,
            copies_available=2,
            content_warnings='["mild violence"]',
            publication_year=2025,
        ))
        # Published row 2 -- different genre
        session.add(IndieEbook(
            metislib_ebook_id=101,
            title="Salt Flat Blues",
            author_pen_name="Dae-Jung Oh",
            description="Road trip literary fiction.",
            genre="Literary Fiction",
            language="en",
            copies_owned=1,
            copies_available=0,
            content_warnings=None,
            publication_year=2024,
        ))
        # Draft-like row -- no title (import artifact, should be excluded)
        session.add(IndieEbook(
            metislib_ebook_id=102,
            title=None,
            author_pen_name=None,
            copies_owned=1,
            copies_available=1,
        ))
        # Zero-copies row -- should be excluded (not owned)
        session.add(IndieEbook(
            metislib_ebook_id=103,
            title="Ghost Title",
            author_pen_name="Nobody",
            copies_owned=0,
            copies_available=0,
        ))
        await session.commit()

    yield Session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def catalog_client(catalog_db):
    from httpx import AsyncClient, ASGITransport
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        async with catalog_db() as session:
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
class TestIndieCatalogEndpoint:
    async def test_returns_owned_rows_only(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog")
        assert r.status_code == 200
        data = r.json()
        titles = [i["title"] for i in data["items"]]
        assert "Coral Depths" in titles
        assert "Salt Flat Blues" in titles

    async def test_excludes_no_title_rows(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog")
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["title"] is not None
            assert item["title"] != ""

    async def test_excludes_zero_copies_rows(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog")
        assert r.status_code == 200
        titles = [i["title"] for i in r.json()["items"]]
        assert "Ghost Title" not in titles

    async def test_total_is_correct(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["pages"] == 1

    async def test_id_is_l30_pk_not_metislib_id(self, catalog_client):
        # The id field MUST be the L30 IndieEbook.id (autoincremented PK),
        # NOT metislib_ebook_id. The borrow POST uses this id as ebook_id.
        r = await catalog_client.get("/api/v1/indie/catalog")
        assert r.status_code == 200
        for item in r.json()["items"]:
            # metislib_ebook_ids we seeded are 100 and 101.
            # L30 PKs will be 1, 2 (autoincremented). So id should NOT be >=100.
            assert item["id"] < 100, (
                f"item id={item['id']} looks like a MetisLib id, not the L30 PK"
            )

    async def test_search_by_title(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?q=coral")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Coral Depths"

    async def test_search_no_match(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?q=zzznomatch")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_genre_filter(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?genre=Thriller")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["genre"] == "Thriller"

    async def test_pagination(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?per_page=1&page=1")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 1
        assert data["total"] == 2
        assert data["pages"] == 2

    async def test_sort_newest(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?sort=newest")
        assert r.status_code == 200
        assert r.json()["total"] == 2

    async def test_sort_available(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?sort=available")
        assert r.status_code == 200
        items = r.json()["items"]
        # "Coral Depths" has 2 available; "Salt Flat Blues" has 0 -- should be first
        assert items[0]["title"] == "Coral Depths"

    async def test_content_warnings_parsed(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?q=coral")
        assert r.status_code == 200
        item = r.json()["items"][0]
        assert isinstance(item["content_warnings"], list)
        assert "mild violence" in item["content_warnings"]

    async def test_null_content_warnings_returns_empty_list(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?q=salt")
        assert r.status_code == 200
        item = r.json()["items"][0]
        assert item["content_warnings"] == []

    async def test_invalid_sort_rejected(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?sort=invalid")
        assert r.status_code == 422

    async def test_per_page_max_enforced(self, catalog_client):
        r = await catalog_client.get("/api/v1/indie/catalog?per_page=999")
        assert r.status_code == 422
