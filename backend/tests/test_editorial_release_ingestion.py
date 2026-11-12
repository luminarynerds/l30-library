from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.release_tracker import ReleaseSource, TrackerAuthor, TrackerBook
from app.schemas.release_tracker import EditorialTitle
from app.services.editorial_release_ingestion import EditorialReleaseIngestionService


def _title(**kw) -> EditorialTitle:
    base = dict(source=ReleaseSource.LIBRARYREADS.value, title="A Title",
                author_name="Clear, James", isbn_13="9780062316097",
                release_date=date(2099, 1, 1), is_featured=True)
    base.update(kw)
    return EditorialTitle(**base)


@pytest.mark.asyncio
async def test_ingest_creates_book_and_inactive_author(test_db):
    svc = EditorialReleaseIngestionService(test_db)
    stats = await svc.ingest([_title()])
    assert stats.books_added == 1

    book = (await test_db.execute(select(TrackerBook))).scalars().one()
    await test_db.refresh(book)
    assert book.source == "libraryreads"
    assert book.is_featured is True
    assert book.status == "upcoming"

    author = (await test_db.execute(
        select(TrackerAuthor).where(TrackerAuthor.id == book.author_id))).scalar_one()
    await test_db.refresh(author)
    assert author.is_active is False
    assert author.name == "Clear, James"


@pytest.mark.asyncio
async def test_ingest_is_idempotent_on_isbn(test_db):
    svc = EditorialReleaseIngestionService(test_db)
    await svc.ingest([_title()])
    await svc.ingest([_title(blurb="second run")])
    count = (await test_db.execute(select(func.count()).select_from(TrackerBook))).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_editorial_merges_into_existing_author_scanned_book(test_db):
    author = TrackerAuthor(name="Clear, James", is_active=True)
    test_db.add(author)
    await test_db.commit()
    await test_db.refresh(author)
    existing = TrackerBook(author_id=author.id, title="A Title",
                           isbn_13="9780062316097", source=ReleaseSource.AUTHOR_SCAN.value,
                           is_featured=False)
    existing.set_normalized_title()
    test_db.add(existing)
    await test_db.commit()

    svc = EditorialReleaseIngestionService(test_db)
    stats = await svc.ingest([_title(blurb="A staff pick.", blurb_credit="Sam")])
    assert stats.books_updated == 1
    assert stats.books_added == 0

    refreshed = (await test_db.execute(select(TrackerBook))).scalars().one()
    await test_db.refresh(refreshed)
    assert refreshed.is_featured is True
    assert refreshed.blurb == "A staff pick."
    assert refreshed.source == "libraryreads"


@pytest.mark.asyncio
async def test_ingest_uses_sentinel_author_when_name_missing(test_db):
    svc = EditorialReleaseIngestionService(test_db)
    await svc.ingest([_title(author_name=None, isbn_13="9781250000000")])
    author = (await test_db.execute(
        select(TrackerAuthor).where(TrackerAuthor.name == EditorialReleaseIngestionService.SENTINEL_AUTHOR_NAME))).scalar_one()
    assert author.is_active is False


@pytest.mark.asyncio
async def test_fuzzy_dedup_without_isbn(test_db):
    svc = EditorialReleaseIngestionService(test_db)
    # No ISBN -> dedup must fall through to fuzzy title + date window (same author).
    await svc.ingest([_title(isbn_13=None, title="The Great Gatsby", release_date=date(2099, 1, 1))])
    # Near-identical title, same author, within 60 days -> deduped (no new row).
    await svc.ingest([_title(isbn_13=None, title="The Great Gatsby!", release_date=date(2099, 1, 15))])
    count = (await test_db.execute(select(func.count()).select_from(TrackerBook))).scalar_one()
    assert count == 1
    # Clearly different title -> new row.
    await svc.ingest([_title(isbn_13=None, title="A Completely Different Book", release_date=date(2099, 1, 1))])
    count2 = (await test_db.execute(select(func.count()).select_from(TrackerBook))).scalar_one()
    assert count2 == 2
