import pytest

from app.services.release_sources import indie_itchio_source as src


@pytest.mark.asyncio
async def test_collects_books_skips_seen_and_nonbooks(monkeypatch):
    async def fake_fetch_feed(url):
        return [
            {"url": "https://itch/seen", "title": "Seen Book", "body": "a zine"},
            {"url": "https://itch/game", "title": "Jumpy Game", "body": "a platformer"},
            {"url": "https://itch/book", "title": "Tide Letters by Mo Finch", "body": "prose novella"},
        ]
    async def fake_classify(text):
        return {"title": "Tide Letters", "author": "Mo Finch"} if "novella" in text else None
    monkeypatch.setattr(src, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(src, "extract_itch_book", fake_classify)

    out = await src.collect_new_books(seen_urls={"https://itch/seen"})
    assert [p["url"] for p in out] == ["https://itch/game", "https://itch/book"]
    assert out[0]["extracted"] == []          # examined non-book: returned so it gets marked processed
    assert out[1]["extracted"] == [{"title": "Tide Letters", "author": "Mo Finch"}]
    assert out[1]["outlet"] == "itchio-books"


@pytest.mark.asyncio
async def test_caps_examined_items(monkeypatch):
    async def fake_fetch_feed(url):
        return [{"url": f"https://itch/{i}", "title": f"T{i}", "body": "b"} for i in range(30)]
    async def fake_classify(text):
        return None
    monkeypatch.setattr(src, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(src, "extract_itch_book", fake_classify)
    out = await src.collect_new_books(seen_urls=set(), max_posts=12)
    assert len(out) == 12
