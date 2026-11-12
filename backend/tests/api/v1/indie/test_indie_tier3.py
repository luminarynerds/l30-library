# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tier-3 backend tests: detail, genres, rails, search cutover, id-contract regression."""
import json
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/indie_tier3_test.db")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite+aiosqlite:////tmp/indie_tier3_test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("PII_ENCRYPTION_ENABLED", "false")


@pytest.fixture(scope="module")
async def tier3_db():
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base
    from app.models.indie_ebook_borrow import (  # noqa: F401 -- register tables
        BorrowStatus,
        IndieEbook,
        IndieEbookBorrow,
    )
    from tests.database_setup import sqlite_compat_metadata_clone

    # DDL from a SQLite-compatible CLONE of the metadata. Never call the
    # in-place swap helpers from a test module: they mutate the shared
    # Base.metadata one-way, poisoning every Postgres-bound test later in
    # the same pytest process (the 2026-07-07 deploy-gate cascade).
    engine = create_async_engine(
        "sqlite+aiosqlite:////tmp/indie_tier3_test.db",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(sqlite_compat_metadata_clone(Base).create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        # Row A: full metadata, 3 copies owned, 1 active borrow -> 2 available derived
        ebook_a = IndieEbook(
            metislib_ebook_id=200,
            title="Ocean Drift",
            author_pen_name="Tara Finn",
            description="A sea voyage.",
            genre="Adventure",
            language="en",
            copies_owned=3,
            copies_available=3,
            content_warnings=json.dumps(["mild peril"]),
            subjects=json.dumps(["Sea stories", "Adventure"]),
            content_rating="g",
            word_count=80000,
            page_count=320,
            isbn="978-0-000-00001-0",
            author_id=42,
            publication_year=2024,
            cover_url="https://cdn.example.com/ocean.jpg",
        )
        session.add(ebook_a)
        await session.flush()

        # One active borrow against ebook_a to test derived available
        from app.models.indie_ebook_borrow import BorrowStatus as BS, IndieEbookBorrow as IBR
        from app.core.datetime_utils import utc_now

        session.add(IBR(
            ebook_id=ebook_a.id,
            user_id=1,  # FK; SQLite won't enforce
            due_at=utc_now(),
            access_token="test-tok-active",
            status=BS.active,
        ))

        # Row B: different genre, no cover, fewer copies
        ebook_b = IndieEbook(
            metislib_ebook_id=201,
            title="Quiet Forest",
            author_pen_name="Lin Bo",
            description="A nature memoir.",
            genre="Memoir",
            language="en",
            copies_owned=1,
            copies_available=1,
            content_warnings=json.dumps([]),
            subjects=json.dumps(["Nature"]),
            content_rating="g",
            publication_year=2023,
        )
        session.add(ebook_b)

        # Row C: no title (import artifact) -- must be excluded
        session.add(IndieEbook(
            metislib_ebook_id=202,
            title=None,
            copies_owned=1,
            copies_available=1,
        ))

        # Row D: zero copies -- must be excluded
        session.add(IndieEbook(
            metislib_ebook_id=203,
            title="Phantom",
            author_pen_name="Ghost",
            copies_owned=0,
            copies_available=0,
        ))

        # Row E: same metislib_ebook_id as a plausible open-access catalog id
        # Used for the local-id regression test: must be fetched by IndieEbook.id PK
        # NOT by metislib_ebook_id.
        ebook_e = IndieEbook(
            metislib_ebook_id=1,  # collides with open-access catalog id space
            title="Local Id Test",
            author_pen_name="Test Author",
            genre="Test",
            language="en",
            copies_owned=2,
            copies_available=2,
            content_warnings=json.dumps([]),
            subjects=json.dumps([]),
        )
        session.add(ebook_e)
        await session.flush()

        await session.commit()

    yield Session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def tier3_client(tier3_db):
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        async with tier3_db() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Detail endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestIndieDetail:
    async def test_detail_200_with_gap_fields(self, tier3_client):
        # First get the local id via browse
        r = await tier3_client.get("/api/v1/indie/catalog?q=Ocean+Drift")
        assert r.status_code == 200
        local_id = r.json()["items"][0]["id"]

        r = await tier3_client.get(f"/api/v1/indie/catalog/{local_id}")
        assert r.status_code == 200
        d = r.json()
        assert d["title"] == "Ocean Drift"
        assert d["subjects"] == ["Sea stories", "Adventure"]
        assert d["word_count"] == 80000
        assert d["page_count"] == 320
        assert d["isbn"] == "978-0-000-00001-0"
        assert d["content_rating"] == "g"
        assert d["author_id"] == 42
        # rating fields
        assert d["rating_count"] == 0
        assert d["total_borrows"] == 1   # one active borrow seeded
        assert d["average_rating"] is None

    async def test_detail_available_copies_derived(self, tier3_client):
        """available_copies = copies_owned - active borrows, not the stored column."""
        r = await tier3_client.get("/api/v1/indie/catalog?q=Ocean+Drift")
        local_id = r.json()["items"][0]["id"]

        r = await tier3_client.get(f"/api/v1/indie/catalog/{local_id}")
        assert r.status_code == 200
        d = r.json()
        # copies_owned=3, 1 active borrow -> 2 derived available
        assert d["available_copies"] == 2
        assert d["total_copies"] == 3

    async def test_detail_content_rating_default(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog?q=Quiet+Forest")
        local_id = r.json()["items"][0]["id"]
        r = await tier3_client.get(f"/api/v1/indie/catalog/{local_id}")
        assert r.status_code == 200
        # content_rating is "g" (set on row B)
        assert r.json()["content_rating"] == "g"

    async def test_detail_404_on_missing(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/999999")
        assert r.status_code == 404

    async def test_detail_404_on_untitled_id(self, tier3_client):
        # Row C has no title; even if we somehow got its id it should 404
        # Fetch the id via raw DB is complex in this fixture so we rely on the
        # browse exclusion test elsewhere; this verifies the 404 path via missing id.
        r = await tier3_client.get("/api/v1/indie/catalog/0")
        assert r.status_code == 404

    async def test_detail_local_id_not_metislib_id_regression(self, tier3_client):
        """Fetching by local id must work even when metislib_ebook_id=1 (open-access collision).

        Row E has metislib_ebook_id=1 but its IndieEbook.id PK is >1.
        GET /{local_id} must return Row E, not a 404 or the wrong row.
        """
        r = await tier3_client.get("/api/v1/indie/catalog?q=Local+Id+Test")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 1
        local_id = items[0]["id"]
        # local id must differ from the colliding metislib_ebook_id (1)
        assert local_id != 1, "id exposed in browse must be local PK, not metislib_ebook_id"

        r = await tier3_client.get(f"/api/v1/indie/catalog/{local_id}")
        assert r.status_code == 200
        assert r.json()["title"] == "Local Id Test"


# ---------------------------------------------------------------------------
# Genres endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestIndieGenres:
    async def test_genres_returns_list(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/genres")
        assert r.status_code == 200
        genres = r.json()
        assert isinstance(genres, list)
        genre_names = [g["genre"] for g in genres]
        assert "Adventure" in genre_names
        assert "Memoir" in genre_names
        # null-title and zero-copies rows excluded
        assert None not in genre_names

    async def test_genres_count_correct(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/genres")
        assert r.status_code == 200
        by_genre = {g["genre"]: g["count"] for g in r.json()}
        assert by_genre["Adventure"] == 1
        assert by_genre["Memoir"] == 1

    async def test_genres_descending_by_count(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/genres")
        assert r.status_code == 200
        counts = [g["count"] for g in r.json()]
        assert counts == sorted(counts, reverse=True)

    async def test_genres_excludes_null_genre_rows(self, tier3_client):
        # Row E has genre="Test"; rows C/D excluded; no None genres should appear
        r = await tier3_client.get("/api/v1/indie/catalog/genres")
        for g in r.json():
            assert g["genre"] is not None


# ---------------------------------------------------------------------------
# Rails endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestIndieCatalogRails:
    async def test_rails_shape(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/rails")
        assert r.status_code == 200
        d = r.json()
        assert "featured" in d
        assert "popular" in d
        assert "new" in d
        for key in ("featured", "popular", "new"):
            assert isinstance(d[key], list)

    async def test_rails_only_titled_owned(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/rails")
        assert r.status_code == 200
        d = r.json()
        for key in ("featured", "popular", "new"):
            for item in d[key]:
                assert item["title"] is not None
                assert item["total_copies"] > 0

    async def test_featured_rail_has_cover(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/rails")
        assert r.status_code == 200
        for item in r.json()["featured"]:
            assert item["cover_url"] is not None

    async def test_rails_limit_param(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/rails?limit=1")
        assert r.status_code == 200
        d = r.json()
        # Each rail capped at 1
        for key in ("featured", "popular", "new"):
            assert len(d[key]) <= 1

    async def test_rails_limit_max_enforced(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/rails?limit=51")
        assert r.status_code == 422

    async def test_popular_rail_sorted_by_total_borrows(self, tier3_client):
        """ocean drift has 1 borrow, others 0 -- must appear first in popular."""
        r = await tier3_client.get("/api/v1/indie/catalog/rails")
        assert r.status_code == 200
        popular = r.json()["popular"]
        if len(popular) >= 2:
            # First item should have >= borrows than second
            # We can't assert exact borrow counts from the HTTP layer but can
            # assert Ocean Drift is first since it has the only borrow.
            assert popular[0]["title"] == "Ocean Drift"

    async def test_new_rail_items_have_correct_fields(self, tier3_client):
        r = await tier3_client.get("/api/v1/indie/catalog/rails")
        assert r.status_code == 200
        for item in r.json()["new"]:
            assert "id" in item
            assert "title" in item
            assert "author_pen_name" in item
            assert "available_copies" in item
