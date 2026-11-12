import pytest
from app.services.schedulers import editorial_rss_jobs as jobs


@pytest.mark.asyncio
async def test_process_editorial_rss_runs(monkeypatch):
    called = {"ran": False}
    from app.schemas.release_tracker import IngestionStats
    async def fake_ingest(db):
        called["ran"] = True
        return IngestionStats(authors_scanned=0, books_found=0, books_added=0,
                              books_updated=0, duplicates_skipped=0, errors=0)
    monkeypatch.setattr(jobs, "ingest_rss", fake_ingest)
    await jobs.process_editorial_rss_ingestion()
    assert called["ran"] is True
