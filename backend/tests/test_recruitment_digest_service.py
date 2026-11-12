from datetime import datetime, timedelta, timezone

import pytest

from app.models.release_tracker import ReleaseSource, TrackerAuthor, TrackerBook
from app.services import recruitment_digest_service as svc


async def _seed(db, title, source, days_ago=1, blurb_credit=None, source_url=None):
    author = TrackerAuthor(name=f"Author of {title}")
    db.add(author)
    await db.flush()
    book = TrackerBook(
        author_id=author.id, title=title, source=source,
        blurb_credit=blurb_credit, source_url=source_url,
    )
    book.set_normalized_title()
    db.add(book)
    await db.flush()
    # backdate created_at explicitly so window logic is deterministic
    book.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    await db.commit()
    return book


@pytest.mark.asyncio
async def test_no_recipient_noop(test_db, monkeypatch):
    monkeypatch.setattr(svc, "_recipient", lambda: None)
    assert await svc.send_recruitment_digest(test_db) is False


@pytest.mark.asyncio
async def test_empty_window_no_send(test_db, monkeypatch):
    monkeypatch.setattr(svc, "_recipient", lambda: "sam@l30.org")
    sent = {}
    async def fake_send(**kw):
        sent["called"] = True
        return True
    monkeypatch.setattr(svc, "send_email", fake_send)
    await _seed(test_db, "Old Indie", ReleaseSource.INDIE_MASTODON.value, days_ago=30)
    await _seed(test_db, "Editorial", ReleaseSource.EDITORIAL_RSS.value, days_ago=1)
    assert await svc.send_recruitment_digest(test_db) is False
    assert "called" not in sent


@pytest.mark.asyncio
async def test_sends_digest_with_buzz_evidence(test_db, monkeypatch):
    monkeypatch.setattr(svc, "_recipient", lambda: "sam@l30.org")
    captured = {}
    async def fake_send(*, to_email, subject, html_content, categories=None, **kw):
        captured.update(to=to_email, subject=subject, html=html_content)
        return True
    monkeypatch.setattr(svc, "send_email", fake_send)
    await _seed(
        test_db, "Dragon Ledger", ReleaseSource.INDIE_MASTODON.value, days_ago=2,
        blurb_credit="Mastodon buzz: 9 interactions", source_url="https://m/x",
    )
    assert await svc.send_recruitment_digest(test_db) is True
    assert captured["to"] == "sam@l30.org"
    assert "1 candidate" in captured["subject"]
    assert "Dragon Ledger" in captured["html"]
    assert "Mastodon buzz: 9 interactions" in captured["html"]
    assert "https://m/x" in captured["html"]


@pytest.mark.asyncio
async def test_digest_escapes_external_html(test_db, monkeypatch):
    monkeypatch.setattr(svc, "_recipient", lambda: "sam@l30.org")
    captured = {}
    async def fake_send(*, to_email, subject, html_content, categories=None, **kw):
        captured["html"] = html_content
        return True
    monkeypatch.setattr(svc, "send_email", fake_send)
    await _seed(
        test_db, "<img src=x onerror=alert(1)>", ReleaseSource.INDIE_MASTODON.value, days_ago=1,
        source_url='https://m/x" onmouseover="alert(1)',
    )
    assert await svc.send_recruitment_digest(test_db) is True
    assert "<img" not in captured["html"]
    assert "&lt;img" in captured["html"]
    assert 'onmouseover="alert' not in captured["html"]


@pytest.mark.asyncio
async def test_dry_run_does_not_send(test_db, monkeypatch):
    monkeypatch.setattr(svc, "_recipient", lambda: "sam@l30.org")
    async def fake_send(**kw):
        raise AssertionError("must not send on dry_run")
    monkeypatch.setattr(svc, "send_email", fake_send)
    await _seed(test_db, "Quiet Book", ReleaseSource.INDIE_ITCHIO.value, days_ago=1)
    assert await svc.send_recruitment_digest(test_db, dry_run=True) is True
