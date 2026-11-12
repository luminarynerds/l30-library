import pytest
from sqlalchemy import select
from app.models.release_tracker import ReleaseSource, TrackerAuthor, TrackerBook


@pytest.mark.asyncio
async def test_tracker_book_has_editorial_fields(test_db):
    author = TrackerAuthor(name="Various, Editorial", is_active=False)
    test_db.add(author)
    await test_db.commit()
    await test_db.refresh(author)

    book = TrackerBook(
        author_id=author.id,
        title="A Forthcoming Title",
        source=ReleaseSource.LIBRARYREADS.value,
        source_url="https://libraryreads.org",
        blurb="A staff pick.",
        blurb_credit="Mara Bandy Fass, Champaign PL, IL",
        is_featured=True,
    )
    book.set_normalized_title()
    test_db.add(book)
    await test_db.commit()

    row = (await test_db.execute(select(TrackerBook).where(TrackerBook.id == book.id))).scalar_one()
    await test_db.refresh(row)
    assert row.source == "libraryreads"
    assert row.source_url == "https://libraryreads.org"
    assert row.blurb == "A staff pick."
    assert row.blurb_credit.startswith("Mara")
    assert row.is_featured is True


@pytest.mark.asyncio
async def test_editorial_fields_default_when_unspecified(test_db):
    author = TrackerAuthor(name="Scan, Author", is_active=True)
    test_db.add(author)
    await test_db.commit()
    await test_db.refresh(author)

    book = TrackerBook(author_id=author.id, title="Default Source Book")
    book.set_normalized_title()
    test_db.add(book)
    await test_db.commit()
    await test_db.refresh(book)

    assert book.source == "author_scan"
    assert book.is_featured is False


def test_release_source_values_are_lowercase():
    assert ReleaseSource.AUTHOR_SCAN.value == "author_scan"
    assert ReleaseSource.LIBRARYREADS.value == "libraryreads"
    assert ReleaseSource.LJ_PREPUB.value == "lj_prepub"
    assert ReleaseSource.EDITORIAL_RSS.value == "editorial_rss"
