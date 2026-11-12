import pytest
from sqlalchemy import select
from app.models.release_tracker import ProcessedRssPost


@pytest.mark.asyncio
async def test_processed_rss_post_roundtrip(test_db):
    p = ProcessedRssPost(url="https://themillions.com/2026/06/most-anticipated.html", outlet="millions")
    test_db.add(p)
    await test_db.commit()
    row = (await test_db.execute(select(ProcessedRssPost))).scalars().one()
    await test_db.refresh(row)
    assert row.url.endswith("most-anticipated.html")
    assert row.outlet == "millions"
    assert row.processed_at is not None
