# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.clients.metislib_opds_client import IndieFeedEntry
from app.models.indie_ebook_borrow import IndieEbook
from app.services.metislib_opds_import_service import MetisLibOpdsImporter


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _fake_pages(pages):
    """Return an async fetch_indie_feed that yields one (entries, next_href)
    tuple per call, walking `pages` in order."""
    calls = {"n": 0}

    async def _inner(*args, **kwargs):
        i = calls["n"]
        calls["n"] += 1
        if i < len(pages):
            return pages[i]
        return ([], None)

    return _inner


def _entry(**overrides):
    base = dict(
        metislib_ebook_id=164,
        title="Adventures in Parenting",
        author_pen_name="Margaux Vane",
        description="A librarian podcast turned ebook series",
        language="en",
        genre="Parenting",
        publication_year=2026,
        cover_url=None,
        acquisition_href="https://metislib.org/api/v1/opds/borrow/164",
        copies_total=5,
        copies_available=5,
        source_updated_at=None,
    )
    base.update(overrides)
    return IndieFeedEntry(**base)


@pytest.mark.asyncio
async def test_import_creates_owned_rows_and_files(db_session, tmp_path, monkeypatch):
    entry = _entry()
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04epub-bytes"))
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({"content_warnings": ["violence"]}))

    stats = await importer.import_all()

    assert stats["created"] == 1
    row = (
        await db_session.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == 164)
        )
    ).scalar_one()
    assert row.title == "Adventures in Parenting"
    assert row.author_pen_name == "Margaux Vane"
    assert row.copies_owned == 5 and row.copies_available == 5
    assert json.loads(row.content_warnings) == ["violence"]
    assert row.file_path and Path(row.file_path).read_bytes().startswith(b"PK")


@pytest.mark.asyncio
async def test_import_is_idempotent(db_session, tmp_path, monkeypatch):
    entry = _entry()
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04epub-bytes"))
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({"content_warnings": ["violence"]}))

    await importer.import_all()

    # Second run: re-patch the page generator (call counter resets), expect update-in-place.
    importer2 = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer2, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer2.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer2.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04epub-bytes"))
    monkeypatch.setattr(importer2, "_fetch_detail", _async_return({"content_warnings": ["violence"]}))

    stats2 = await importer2.import_all()

    assert stats2["updated"] >= 1
    assert stats2["created"] == 0
    rows = (
        await db_session.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == 164)
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_import_walks_multiple_pages(db_session, tmp_path, monkeypatch):
    e1 = _entry(metislib_ebook_id=164, acquisition_href="https://metislib.org/api/v1/opds/borrow/164")
    e2 = _entry(metislib_ebook_id=89, title="Velvet Ruin", acquisition_href="https://metislib.org/api/v1/opds/borrow/89")
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(
        importer.client,
        "fetch_indie_feed",
        _fake_pages([([e1], "https://metislib.org/api/v1/opds/indie?page=2"), ([e2], None)]),
    )
    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04epub-bytes"))
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({}))

    stats = await importer.import_all()

    assert stats["created"] == 2
    rows = (await db_session.execute(select(IndieEbook))).scalars().all()
    assert {r.metislib_ebook_id for r in rows} == {164, 89}


@pytest.mark.asyncio
async def test_reimport_does_not_overwrite_copies_available(db_session, tmp_path, monkeypatch):
    """Re-import must not reset local circulation state (copies_available)."""
    entry = _entry(copies_total=5, copies_available=5)
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04epub-bytes"))
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({}))

    await importer.import_all()

    # Simulate a patron borrowing: copies_available drops to 3
    row = (
        await db_session.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == 164)
        )
    ).scalar_one()
    row.copies_available = 3
    await db_session.commit()

    # Re-import same entry — feed still says available=5
    importer2 = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer2, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer2.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer2.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04epub-bytes"))
    monkeypatch.setattr(importer2, "_fetch_detail", _async_return({}))

    stats2 = await importer2.import_all()

    assert stats2["updated"] == 1
    row2 = (
        await db_session.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == 164)
        )
    ).scalar_one()
    assert row2.copies_available == 3, "re-import must not reset local circulation state"
    assert row2.copies_owned == 5, "copies_owned also preserved"


@pytest.mark.asyncio
async def test_import_all_raises_on_empty_first_page(db_session, tmp_path, monkeypatch):
    """Empty first page signals a broken/unreachable feed — must raise, not silently succeed."""
    from app.services.metislib_opds_import_service import MetisLibOpdsImportError
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([], None)]))

    with pytest.raises(MetisLibOpdsImportError):
        await importer.import_all()


@pytest.mark.asyncio
async def test_bad_epub_bytes_leaves_file_path_null(db_session, tmp_path, monkeypatch):
    """Empty or non-zip bytes: no file written, file_path stays NULL, metadata row present, error counted."""
    entry = _entry()
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", _async_return(b""))
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({}))

    stats = await importer.import_all()

    assert stats["errors"] == 1
    assert stats["files"] == 0
    row = (
        await db_session.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == 164)
        )
    ).scalar_one()
    assert row.title == "Adventures in Parenting"  # metadata still upserted
    assert row.file_path is None
    assert not list(tmp_path.glob("*.epub"))


@pytest.mark.asyncio
async def test_zero_byte_epub_file_is_refetched(db_session, tmp_path, monkeypatch):
    """A 0-byte existing EPUB triggers a re-fetch; valid bytes replace it."""
    entry = _entry()
    # Pre-create a 0-byte stub
    stub = tmp_path / "164.epub"
    stub.write_bytes(b"")

    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04good-epub"))
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({}))

    stats = await importer.import_all()

    assert stats["files"] == 1
    assert stats["errors"] == 0
    assert stub.read_bytes().startswith(b"PK")


@pytest.mark.asyncio
async def test_fetch_error_persists_metadata_row(db_session, tmp_path, monkeypatch):
    """When fetch_ebook_bytes raises, the metadata row is still persisted with file_path=None
    and errors is incremented. A re-run must then retry the file."""
    from app.clients.metislib_opds_client import MetisLibOpdsClientError

    entry = _entry()
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([entry], None)]))

    async def raise_fetch(*args, **kwargs):
        raise MetisLibOpdsClientError("connection refused", status_code=None)

    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", raise_fetch)
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({}))

    stats = await importer.import_all()

    assert stats["errors"] == 1
    assert stats["files"] == 0
    row = (
        await db_session.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == 164)
        )
    ).scalar_one()
    assert row.title == "Adventures in Parenting", "metadata must be present even after fetch failure"
    assert row.file_path is None, "file_path must stay NULL when fetch raised"


@pytest.mark.asyncio
async def test_existing_zero_copy_row_gets_seeded(db_session, tmp_path, monkeypatch):
    """Pre-existing thin rows with copies_owned=0 must get copies seeded on import."""
    # Pre-insert a thin row (simulates the ~50 lazy rows created before Phase 1)
    thin = IndieEbook(metislib_ebook_id=164, title="Old Title", copies_owned=0, copies_available=0)
    db_session.add(thin)
    await db_session.flush()

    entry = _entry(copies_total=5, copies_available=5)
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04epub"))
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({}))

    stats = await importer.import_all()

    assert stats["updated"] == 1
    row = (
        await db_session.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == 164)
        )
    ).scalar_one()
    assert row.copies_owned == 5, "zero-copy row must get seeded from feed"
    assert row.copies_available == 5


@pytest.mark.asyncio
async def test_existing_seeded_row_not_reset_on_reimport(db_session, tmp_path, monkeypatch):
    """Row with copies_owned=5, copies_available=2 must keep copies_available=2 on re-import."""
    seeded = IndieEbook(
        metislib_ebook_id=164,
        title="Old Title",
        copies_owned=5,
        copies_available=2,
    )
    db_session.add(seeded)
    await db_session.flush()

    entry = _entry(copies_total=5, copies_available=5)  # feed says 5 available
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04epub"))
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({}))

    stats = await importer.import_all()

    assert stats["updated"] == 1
    row = (
        await db_session.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == 164)
        )
    ).scalar_one()
    assert row.copies_available == 2, "re-import must not reset local circulation state"
    assert row.copies_owned == 5, "copies_owned must not change on re-import of seeded row"


@pytest.mark.asyncio
async def test_import_captures_gap_fields(db_session, tmp_path, monkeypatch):
    """Importer persists static gap fields from the MetisLib detail dict."""
    entry = _entry()
    importer = MetisLibOpdsImporter(db_session)
    monkeypatch.setattr(importer, "_storage_dir", tmp_path)
    monkeypatch.setattr(importer.client, "fetch_indie_feed", _fake_pages([([entry], None)]))
    monkeypatch.setattr(importer.client, "fetch_ebook_bytes", _async_return(b"PK\x03\x04epub"))
    monkeypatch.setattr(importer, "_fetch_detail", _async_return({
        "content_warnings": ["violence"],
        "subjects": ["space", "ethics"],
        "content_rating": "pg13",
        "word_count": 92000,
        "page_count": 354,
        "isbn": "978-1-23456-789-0",
        "author_id": 7,
    }))

    await importer.import_all()

    row = (
        await db_session.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == 164)
        )
    ).scalar_one()
    assert json.loads(row.subjects) == ["space", "ethics"]
    assert row.content_rating == "pg13"
    assert row.word_count == 92000
    assert row.page_count == 354
    assert row.isbn == "978-1-23456-789-0"
    assert row.author_id == 7
    assert json.loads(row.content_warnings) == ["violence"]
