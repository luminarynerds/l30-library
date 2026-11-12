from datetime import date
import pytest
from app.schemas.release_tracker import ExternalBookResult
from app.services.release_sources import title_resolver


@pytest.mark.asyncio
async def test_resolve_uses_first_match(monkeypatch):
    async def fake_search(self, query, max_results=20):
        return [ExternalBookResult(source="google_books", source_id="g1", title="Villa Coco",
                                   authors=["Andrew Sean Greer"], isbn_13="9780385551977",
                                   release_date=date(2026, 6, 15), publisher="Avery",
                                   cover_url="http://x/c.jpg")]
    monkeypatch.setattr(title_resolver.GoogleBooksFetcher, "search_books", fake_search)
    t = await title_resolver.resolve("Villa Coco", "Andrew Sean Greer")
    assert t.source == "editorial_rss"
    assert t.isbn_13 == "9780385551977"
    assert t.release_date == date(2026, 6, 15)
    assert t.is_featured is False
    assert t.author_name == "Andrew Sean Greer"


@pytest.mark.asyncio
async def test_resolve_no_match_returns_title_only(monkeypatch):
    async def fake_search(self, query, max_results=20):
        return []
    monkeypatch.setattr(title_resolver.GoogleBooksFetcher, "search_books", fake_search)
    t = await title_resolver.resolve("Obscure Title", "Nobody")
    assert t.isbn_13 is None
    assert t.title == "Obscure Title"
    assert t.author_name == "Nobody"
    assert t.is_date_exact is False


@pytest.mark.asyncio
async def test_resolve_rejects_low_similarity_match(monkeypatch):
    async def fake_search(self, query, max_results=20):
        return [ExternalBookResult(source="google_books", source_id="g9", title="Completely Different Unrelated Book",
                                   authors=["X"], isbn_13="9781111111111")]
    monkeypatch.setattr(title_resolver.GoogleBooksFetcher, "search_books", fake_search)
    t = await title_resolver.resolve("Villa Coco", "Andrew Sean Greer")
    assert t.isbn_13 is None          # low-similarity match rejected -> title-only
    assert t.title == "Villa Coco"


@pytest.mark.asyncio
async def test_resolve_passes_through_age_rating(monkeypatch):
    async def fake_search(self, query, max_results=20):
        return [ExternalBookResult(source="google_books", source_id="g2", title="A Kids Book",
                                   authors=["K Author"], isbn_13="9782222222222", age_rating="child")]
    monkeypatch.setattr(title_resolver.GoogleBooksFetcher, "search_books", fake_search)
    t = await title_resolver.resolve("A Kids Book", "K Author")
    assert t.age_rating == "child"
