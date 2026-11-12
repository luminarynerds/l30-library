import pytest

from app.models.release_tracker import ReleaseSource
from app.services.release_sources import title_resolver as tr


@pytest.mark.asyncio
async def test_resolve_carries_source_and_provenance(monkeypatch):
    class FakeFetcher:
        async def search_books(self, query, max_results=5):
            return []
    monkeypatch.setattr(tr, "GoogleBooksFetcher", FakeFetcher)
    t = await tr.resolve(
        "Dragon Ledger", "R. Vale",
        source=ReleaseSource.INDIE_MASTODON.value,
        source_url="https://m/x",
        blurb_credit="Mastodon buzz: 4 interactions",
    )
    assert t.source == "indie_mastodon"
    assert t.source_url == "https://m/x"
    assert t.blurb_credit == "Mastodon buzz: 4 interactions"
    assert t.isbn_13 is None and t.is_featured is False


@pytest.mark.asyncio
async def test_resolve_default_unchanged(monkeypatch):
    class FakeFetcher:
        async def search_books(self, query, max_results=5):
            return []
    monkeypatch.setattr(tr, "GoogleBooksFetcher", FakeFetcher)
    t = await tr.resolve("X", "Y")
    assert t.source == ReleaseSource.EDITORIAL_RSS.value
    assert t.source_url is None and t.blurb_credit is None
