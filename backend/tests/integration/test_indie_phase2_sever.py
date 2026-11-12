# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 2 sever: indie search + EPUB serving come from L30-owned data."""
import json

import pytest

from app.core.datetime_utils import utc_now
from app.models.indie_ebook_borrow import BorrowStatus, IndieEbook, IndieEbookBorrow


@pytest.mark.asyncio
async def test_indie_search_reads_owned(db_session):
    from app.services.unified_search_service import UnifiedSearchService

    db_session.add(IndieEbook(
        metislib_ebook_id=9300, title="Searchable Owned", author_pen_name="S Author",
        description="a unique searchable description", genre="Fiction", language="en",
        file_format="epub", content_warnings=json.dumps([]), subjects=json.dumps([]),
        copies_owned=2, copies_available=2,
    ))
    await db_session.flush()

    svc = UnifiedSearchService(db_session)
    results, total = await svc._search_indie_ebooks("Searchable", None, 50)

    assert "Searchable Owned" in [r.title for r in results]
    assert total >= 1
    # id must be the local L30 pk (source_id), not metislib_ebook_id (9300)
    owned_result = next(r for r in results if r.title == "Searchable Owned")
    assert owned_result.source_id != "9300", (
        "source_id must be the local IndieEbook.id PK, not metislib_ebook_id"
    )
    assert owned_result.id.startswith("indie:")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_download_serves_local_epub(client, db_session, test_patron, tmp_path):
    from app.api.v1.auth import get_current_user
    from app.main import app

    epub = tmp_path / "9301.epub"
    epub.write_bytes(b"PK\x03\x04local-epub-bytes")
    ebook = IndieEbook(
        metislib_ebook_id=9301, title="Readable", author_pen_name="A",
        genre="Fiction", language="en", file_format="epub",
        content_warnings=json.dumps([]), subjects=json.dumps([]),
        copies_owned=1, copies_available=1, file_path=str(epub),
    )
    db_session.add(ebook)
    await db_session.flush()
    borrow = IndieEbookBorrow(
        ebook_id=ebook.id, user_id=test_patron.id, due_at=utc_now(),
        access_token="local-serve-token", status=BorrowStatus.active,
    )
    db_session.add(borrow)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: test_patron
    try:
        resp = await client.get("/api/v1/indie/lending/download/local-serve-token")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/epub+zip"
    assert resp.content.startswith(b"PK")
