# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date

import pytest
from sqlalchemy import select

from app.models.release_tracker import ReleaseSource, TrackerAuthor, TrackerBook


@pytest.mark.asyncio
async def test_librarian_releases_filters_by_source(staff_client, test_db):
    author = TrackerAuthor(name="Editorial / Various", is_active=False)
    test_db.add(author)
    await test_db.commit()
    await test_db.refresh(author)
    for src, title in [(ReleaseSource.LIBRARYREADS.value, "LR Title"),
                       (ReleaseSource.AUTHOR_SCAN.value, "Scan Title")]:
        b = TrackerBook(author_id=author.id, title=title, source=src,
                        status="upcoming", release_date=date(2099, 1, 1),
                        is_featured=(src == ReleaseSource.LIBRARYREADS.value))
        b.set_normalized_title()
        test_db.add(b)
    await test_db.commit()

    resp = await staff_client.get("/api/v1/releases/librarian/releases?source=libraryreads")
    assert resp.status_code == 200
    data = resp.json()
    titles = [i["book"]["title"] for i in data["items"]]
    assert "LR Title" in titles and "Scan Title" not in titles
    assert data["items"][0]["book"]["source"] == "libraryreads"
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_ingest_editorial_libraryreads(staff_client, test_db, monkeypatch):
    from app.services.release_sources.libraryreads_source import LibraryReadsSource
    from app.schemas.release_tracker import EditorialTitle

    async def fake_fetch(self, month=None):
        return [EditorialTitle(source="libraryreads", title="Injected Pick",
                               author_name="Clear, James", isbn_13="9780062316097",
                               release_date=date(2099, 1, 1), is_featured=True,
                               source_url="https://libraryreads.org")]

    monkeypatch.setattr(LibraryReadsSource, "fetch", fake_fetch)

    resp = await staff_client.post("/api/v1/releases/librarian/ingest-editorial",
                                   json={"source": "libraryreads"})
    assert resp.status_code == 200
    assert resp.json()["books_added"] == 1
    book = (await test_db.execute(select(TrackerBook))).scalars().one()
    assert book.title == "Injected Pick"


@pytest.mark.asyncio
async def test_ingest_editorial_lj_requires_sheet_id(staff_client):
    resp = await staff_client.post("/api/v1/releases/librarian/ingest-editorial",
                                   json={"source": "lj_prepub"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_librarian_releases_rejects_bad_source(staff_client):
    resp = await staff_client.get("/api/v1/releases/librarian/releases?source=garbage")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_source_filter_accepts_indie_sources(staff_client):
    for source in ("indie_mastodon", "indie_itchio"):
        resp = await staff_client.get(f"/api/v1/releases/librarian/releases?source={source}")
        assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_ingest_editorial_indie_sources(staff_client, monkeypatch):
    from app.schemas.release_tracker import IngestionStats
    import app.services.indie_release_ingestion as coord
    calls = []
    async def fake_ingest(db, sources=None):
        calls.append(sources)
        return IngestionStats(authors_scanned=0, books_found=1, books_added=1,
                              books_updated=0, duplicates_skipped=0, errors=0)
    monkeypatch.setattr(coord, "ingest_indie", fake_ingest)
    for source in ("indie_mastodon", "indie_itchio"):
        resp = await staff_client.post("/api/v1/releases/librarian/ingest-editorial",
                                       json={"source": source})
        assert resp.status_code == 200, resp.text
        assert resp.json()["books_added"] == 1
    assert calls == [["indie_mastodon"], ["indie_itchio"]]
