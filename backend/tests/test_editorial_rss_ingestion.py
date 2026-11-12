import pytest
from sqlalchemy import func, select
from app.models.release_tracker import ProcessedRssPost, TrackerBook
from app.schemas.release_tracker import EditorialTitle
from app.services import editorial_rss_ingestion as coord
from app.models.release_tracker import ReleaseSource


@pytest.mark.asyncio
async def test_ingest_rss_creates_books_and_marks_processed(test_db, monkeypatch):
    async def fake_collect(seen_urls, feeds=None):
        assert seen_urls == set()
        return [{"url": "https://m/new", "outlet": "millions", "title": "Anticipated",
                 "extracted": [{"title": "Book A", "author": "Auth A"}]}]
    async def fake_resolve(title, author):
        return EditorialTitle(source=ReleaseSource.EDITORIAL_RSS.value, title=title,
                              author_name=author, isbn_13="9780000000001", is_featured=False)
    monkeypatch.setattr(coord, "collect_new_posts", fake_collect)
    monkeypatch.setattr(coord, "resolve", fake_resolve)

    stats = await coord.ingest_rss(test_db)
    assert stats.books_added == 1
    book = (await test_db.execute(select(TrackerBook))).scalars().one()
    assert book.source == "editorial_rss"
    assert book.is_featured is False
    seen = (await test_db.execute(select(ProcessedRssPost))).scalars().one()
    assert seen.url == "https://m/new"


@pytest.mark.asyncio
async def test_ingest_rss_is_idempotent(test_db, monkeypatch):
    async def fake_collect(seen_urls, feeds=None):
        if "https://m/new" in seen_urls:
            return []
        return [{"url": "https://m/new", "outlet": "millions", "title": "A",
                 "extracted": [{"title": "Book A", "author": "Auth A"}]}]
    async def fake_resolve(title, author):
        return EditorialTitle(source=ReleaseSource.EDITORIAL_RSS.value, title=title,
                              author_name=author, isbn_13="9780000000001", is_featured=False)
    monkeypatch.setattr(coord, "collect_new_posts", fake_collect)
    monkeypatch.setattr(coord, "resolve", fake_resolve)

    await coord.ingest_rss(test_db)
    await coord.ingest_rss(test_db)
    book_count = (await test_db.execute(select(func.count()).select_from(TrackerBook))).scalar_one()
    assert book_count == 1


@pytest.mark.asyncio
async def test_ingest_rss_marks_empty_extraction_posts(test_db, monkeypatch):
    async def fake_collect(seen_urls, feeds=None):
        if "https://m/essay" in seen_urls:
            return []
        return [{"url": "https://m/essay", "outlet": "lithub", "title": "Essay", "extracted": []}]
    async def fake_resolve(title, author):
        raise AssertionError("resolve must not be called for an empty-extraction post")
    monkeypatch.setattr(coord, "collect_new_posts", fake_collect)
    monkeypatch.setattr(coord, "resolve", fake_resolve)
    await coord.ingest_rss(test_db)
    seen = (await test_db.execute(select(ProcessedRssPost))).scalars().one()
    assert seen.url == "https://m/essay"
    book_count = (await test_db.execute(select(func.count()).select_from(TrackerBook))).scalar_one()
    assert book_count == 0
