import pytest

from app.services.release_sources import indie_mastodon_source as src


def _toot(url, favs=0, boosts=0, bot=False, content="I wrote a book!", name="Auth Or"):
    return {
        "url": url,
        "content": f"<p>{content}</p>",
        "favourites_count": favs,
        "reblogs_count": boosts,
        "account": {"bot": bot, "display_name": name, "acct": "auth@mastodon.social"},
    }


@pytest.mark.asyncio
async def test_filters_bots_low_engagement_and_seen(monkeypatch):
    async def fake_timeline(tag, max_pages=5):
        return [
            _toot("https://m/bot", favs=9, bot=True),
            _toot("https://m/quiet", favs=1),
            _toot("https://m/seen", favs=5),
            _toot("https://m/keep", favs=3, boosts=1),
        ]
    async def fake_extract(text):
        return {"title": "Kept Book", "author": "Auth Or"}
    monkeypatch.setattr(src, "fetch_tag_timeline", fake_timeline)
    monkeypatch.setattr(src, "extract_announcement", fake_extract)

    out = await src.collect_buzzed_posts(seen_urls={"https://m/seen"}, tags=["indieauthor"])
    assert [p["url"] for p in out] == ["https://m/keep"]
    assert out[0]["outlet"] == "mastodon-indieauthor"
    assert out[0]["engagement"] == 4
    assert out[0]["extracted"] == [{"title": "Kept Book", "author": "Auth Or"}]


@pytest.mark.asyncio
async def test_caps_and_ranks_by_engagement(monkeypatch):
    async def fake_timeline(tag, max_pages=5):
        return [_toot(f"https://m/{i}", favs=i) for i in range(2, 30)]
    async def fake_extract(text):
        return None  # not announcements -> still counted as examined posts
    monkeypatch.setattr(src, "fetch_tag_timeline", fake_timeline)
    monkeypatch.setattr(src, "extract_announcement", fake_extract)

    out = await src.collect_buzzed_posts(seen_urls=set(), tags=["newrelease"], max_posts=12)
    assert len(out) == 12
    assert out[0]["engagement"] >= out[-1]["engagement"]  # ranked desc
    assert all(p["extracted"] == [] for p in out)


@pytest.mark.asyncio
async def test_author_falls_back_to_display_name(monkeypatch):
    async def fake_timeline(tag, max_pages=5):
        return [_toot("https://m/x", favs=5, name="Mx. Quill")]
    async def fake_extract(text):
        return {"title": "Nameless", "author": ""}
    monkeypatch.setattr(src, "fetch_tag_timeline", fake_timeline)
    monkeypatch.setattr(src, "extract_announcement", fake_extract)
    out = await src.collect_buzzed_posts(seen_urls=set(), tags=["indieauthor"])
    assert out[0]["extracted"] == [{"title": "Nameless", "author": "Mx. Quill"}]


@pytest.mark.asyncio
async def test_one_tag_down_does_not_abort(monkeypatch):
    async def fake_timeline(tag, max_pages=5):
        if tag == "indieauthor":
            raise RuntimeError("boom")
        return [_toot("https://m/ok", favs=5)]
    async def fake_extract(text):
        return {"title": "Ok Book", "author": "A"}
    monkeypatch.setattr(src, "fetch_tag_timeline", fake_timeline)
    monkeypatch.setattr(src, "extract_announcement", fake_extract)
    out = await src.collect_buzzed_posts(seen_urls=set(), tags=["indieauthor", "newrelease"])
    assert [p["url"] for p in out] == ["https://m/ok"]


@pytest.mark.asyncio
async def test_extraction_failure_skips_toot_without_marking(monkeypatch):
    async def fake_timeline(tag, max_pages=5):
        return [_toot("https://m/defer", favs=5)]
    async def fake_extract(text):
        raise RuntimeError("ollama down")
    monkeypatch.setattr(src, "fetch_tag_timeline", fake_timeline)
    monkeypatch.setattr(src, "extract_announcement", fake_extract)
    out = await src.collect_buzzed_posts(seen_urls=set(), tags=["indieauthor"])
    assert out == []  # toot deferred to next run, not consumed
