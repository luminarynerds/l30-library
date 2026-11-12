import pytest

from app.services.schedulers import editorial_release_jobs as jobs


@pytest.mark.asyncio
async def test_process_editorial_release_ingestion_runs(monkeypatch):
    calls = {"fetched": False, "ingested": 0}

    from app.services.release_sources.libraryreads_source import LibraryReadsSource
    from app.services.editorial_release_ingestion import EditorialReleaseIngestionService
    from app.schemas.release_tracker import IngestionStats

    async def fake_fetch(self, month=None):
        calls["fetched"] = True
        return []

    async def fake_ingest(self, titles):
        calls["ingested"] = len(titles)
        return IngestionStats(authors_scanned=0, books_found=0, books_added=0,
                              books_updated=0, duplicates_skipped=0, errors=0)

    monkeypatch.setattr(LibraryReadsSource, "fetch", fake_fetch)
    monkeypatch.setattr(EditorialReleaseIngestionService, "ingest", fake_ingest)

    await jobs.process_editorial_release_ingestion()
    assert calls["fetched"] is True
