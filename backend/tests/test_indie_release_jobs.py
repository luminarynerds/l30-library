import pytest

from app.services.schedulers import indie_release_jobs as jobs


@pytest.mark.asyncio
async def test_process_indie_ingestion_runs(monkeypatch):
    called = {}
    from app.schemas.release_tracker import IngestionStats
    async def fake_ingest(db, sources=None):
        called["sources"] = sources
        return IngestionStats(authors_scanned=0, books_found=0, books_added=0,
                              books_updated=0, duplicates_skipped=0, errors=0)
    monkeypatch.setattr(jobs, "ingest_indie", fake_ingest)
    await jobs.process_indie_release_ingestion()
    assert called["sources"] is None  # both connectors


@pytest.mark.asyncio
async def test_process_recruitment_digest_runs(monkeypatch):
    called = {"ran": False}
    async def fake_send(db, dry_run=False):
        called["ran"] = True
        return True
    monkeypatch.setattr(jobs, "send_recruitment_digest", fake_send)
    await jobs.process_recruitment_digest()
    assert called["ran"] is True
