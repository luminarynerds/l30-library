import pytest
from sqlalchemy import select
from app.models.release_tracker import ReleaseSource, TrackerAuthor, TrackerBook


@pytest.mark.asyncio
async def test_staff_can_feature_a_tracker_book(staff_client, test_db):
    author = TrackerAuthor(name="Editorial / Various", is_active=False)
    test_db.add(author); await test_db.commit(); await test_db.refresh(author)
    book = TrackerBook(author_id=author.id, title="RSS Pick", source=ReleaseSource.EDITORIAL_RSS.value,
                       is_featured=False, status="upcoming")
    book.set_normalized_title(); test_db.add(book); await test_db.commit(); await test_db.refresh(book)

    resp = await staff_client.patch(f"/api/v1/releases/librarian/{book.id}/feature", json={"is_featured": True})
    assert resp.status_code == 200
    assert resp.json()["is_featured"] is True
    refreshed = (await test_db.execute(select(TrackerBook).where(TrackerBook.id == book.id))).scalar_one()
    await test_db.refresh(refreshed)
    assert refreshed.is_featured is True
