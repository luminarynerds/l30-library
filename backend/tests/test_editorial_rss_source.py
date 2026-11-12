import pytest
from app.services.release_sources import editorial_rss_source as src


@pytest.mark.asyncio
async def test_collect_new_posts_skips_seen_and_extracts(monkeypatch):
    async def fake_fetch_feed(url):
        return [{"url": "https://m/seen", "title": "T1", "body": "b1"},
                {"url": "https://m/new", "title": "T2", "body": "b2"}]
    async def fake_extract(text):
        return [{"title": "Book A", "author": "Auth A"}] if text == "b2" else []
    monkeypatch.setattr(src, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(src, "extract_titles", fake_extract)

    out = await src.collect_new_posts(seen_urls={"https://m/seen"}, feeds=[("millions", "u")])
    assert len(out) == 1
    post = out[0]
    assert post["url"] == "https://m/new"
    assert post["outlet"] == "millions"
    assert post["extracted"] == [{"title": "Book A", "author": "Auth A"}]


@pytest.mark.asyncio
async def test_collect_new_posts_returns_empty_extraction_posts(monkeypatch):
    async def fake_fetch_feed(url):
        return [{"url": "https://m/essay", "title": "An Essay", "body": "no books here"}]
    async def fake_extract(text):
        return []
    monkeypatch.setattr(src, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(src, "extract_titles", fake_extract)
    out = await src.collect_new_posts(seen_urls=set(), feeds=[("millions", "u")])
    assert len(out) == 1
    assert out[0]["url"] == "https://m/essay"
    assert out[0]["extracted"] == []


@pytest.mark.asyncio
async def test_collect_new_posts_caps_per_run(monkeypatch):
    async def fake_fetch_feed(url):
        return [{"url": f"https://m/{i}", "title": f"T{i}", "body": f"b{i}"} for i in range(20)]
    async def fake_extract(text):
        return [{"title": "Book", "author": "Auth"}]
    monkeypatch.setattr(src, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(src, "extract_titles", fake_extract)
    out = await src.collect_new_posts(seen_urls=set(), feeds=[("millions", "u")], max_posts=12)
    assert len(out) == 12


@pytest.mark.asyncio
async def test_collect_new_posts_skips_posts_when_extractor_down(monkeypatch):
    async def fake_fetch_feed(url):
        return [{"url": "https://m/depressed", "title": "T", "body": "b"}]
    async def fake_extract(text):
        raise RuntimeError("ollama down")
    monkeypatch.setattr(src, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(src, "extract_titles", fake_extract)
    out = await src.collect_new_posts(seen_urls=set(), feeds=[("millions", "u")])
    assert out == []  # post NOT returned -> never marked processed -> retried next run
