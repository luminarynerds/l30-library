from datetime import date
import pytest
from app.models.release_tracker import ReleaseSource, TrackerAuthor, TrackerBook


@pytest.mark.asyncio
async def test_featured_upcoming_returns_only_featured_upcoming(staff_client, test_db):
    author = TrackerAuthor(name="Editorial / Various", is_active=False)
    test_db.add(author); await test_db.commit(); await test_db.refresh(author)
    rows = [
        ("LR Featured", ReleaseSource.LIBRARYREADS.value, True, "upcoming", date(2099, 1, 1)),
        ("RSS NotFeatured", ReleaseSource.EDITORIAL_RSS.value, False, "upcoming", date(2099, 1, 1)),
        ("LR Released", ReleaseSource.LIBRARYREADS.value, True, "released", date(2000, 1, 1)),
    ]
    for title, src, feat, status, rd in rows:
        b = TrackerBook(author_id=author.id, title=title, source=src, is_featured=feat, status=status, release_date=rd)
        b.set_normalized_title(); test_db.add(b)
    await test_db.commit()

    resp = await staff_client.get("/api/v1/releases/featured-upcoming")
    assert resp.status_code == 200
    titles = [i["title"] for i in resp.json()["items"]]
    assert titles == ["LR Featured"]
    assert resp.json()["items"][0]["source"] == "libraryreads"
    assert resp.json()["items"][0]["library_status"] in {"new", "owned", "on_order"}


@pytest.mark.asyncio
async def test_featured_upcoming_is_public(client, test_db):
    resp = await client.get("/api/v1/releases/featured-upcoming")
    assert resp.status_code == 200
