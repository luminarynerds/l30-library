import pytest
from sqlalchemy import select

from app.models.release_tracker import ProcessedRssPost, ReleaseSource, TrackerBook
from app.schemas.release_tracker import EditorialTitle
from app.services import indie_release_ingestion as coord


def _post(url, outlet, extracted, engagement=4):
    return {"url": url, "outlet": outlet, "title": "t", "engagement": engagement, "extracted": extracted}


async def _fake_resolve(title, author, source, source_url=None, blurb_credit=None):
    return EditorialTitle(
        source=source, title=title, author_name=author or None,
        source_url=source_url, blurb_credit=blurb_credit,
        isbn_13=None, release_date=None, is_date_exact=False, is_featured=False,
    )


@pytest.mark.asyncio
async def test_ingest_indie_creates_rows_and_marks_processed(test_db, monkeypatch):
    async def fake_mastodon(seen_urls, **kw):
        return [
            _post("https://m/a", "mastodon-indieauthor", [{"title": "Book A", "author": "A. Uthor"}]),
            _post("https://m/b", "mastodon-newrelease", []),  # examined, nothing extracted
        ]
    async def fake_itch(seen_urls, **kw):
        return [_post("https://itch/c", "itchio-books", [{"title": "Book C", "author": "C. Reator"}], engagement=0)]
    monkeypatch.setattr(coord, "collect_buzzed_posts", fake_mastodon)
    monkeypatch.setattr(coord, "collect_new_books", fake_itch)
    monkeypatch.setattr(coord, "resolve", _fake_resolve)

    stats = await coord.ingest_indie(test_db)
    assert stats.books_added == 2

    books = (await test_db.execute(select(TrackerBook))).scalars().all()
    by_title = {b.title: b for b in books}
    a = by_title["Book A"]
    assert a.source == ReleaseSource.INDIE_MASTODON.value
    assert a.source_url == "https://m/a"
    assert a.blurb_credit == "Mastodon buzz: 4 interactions"
    assert a.is_featured is False
    c = by_title["Book C"]
    assert c.source == ReleaseSource.INDIE_ITCHIO.value
    assert c.blurb_credit is None

    processed = {p.url for p in (await test_db.execute(select(ProcessedRssPost))).scalars().all()}
    assert processed == {"https://m/a", "https://m/b", "https://itch/c"}


@pytest.mark.asyncio
async def test_ingest_indie_single_source_and_seen_skip(test_db, monkeypatch):
    test_db.add(ProcessedRssPost(url="https://m/old", outlet="mastodon-indieauthor"))
    await test_db.commit()
    captured = {}
    async def fake_mastodon(seen_urls, **kw):
        captured["seen"] = set(seen_urls)
        return []
    async def fake_itch(seen_urls, **kw):
        raise AssertionError("itch must not run when sources=[indie_mastodon]")
    monkeypatch.setattr(coord, "collect_buzzed_posts", fake_mastodon)
    monkeypatch.setattr(coord, "collect_new_books", fake_itch)
    monkeypatch.setattr(coord, "resolve", _fake_resolve)
    stats = await coord.ingest_indie(test_db, sources=[ReleaseSource.INDIE_MASTODON.value])
    assert stats.books_added == 0
    assert "https://m/old" in captured["seen"]


@pytest.mark.asyncio
async def test_one_connector_down_does_not_abort(test_db, monkeypatch):
    async def fake_mastodon(seen_urls, **kw):
        raise RuntimeError("instance down")
    async def fake_itch(seen_urls, **kw):
        return [_post("https://itch/c", "itchio-books", [{"title": "Book C", "author": "C"}], engagement=0)]
    monkeypatch.setattr(coord, "collect_buzzed_posts", fake_mastodon)
    monkeypatch.setattr(coord, "collect_new_books", fake_itch)
    monkeypatch.setattr(coord, "resolve", _fake_resolve)
    stats = await coord.ingest_indie(test_db)
    assert stats.books_added == 1
