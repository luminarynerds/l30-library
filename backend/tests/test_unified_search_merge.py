# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for unified-search merge/total/pagination (pure, no DB/network)."""
from __future__ import annotations

from app.services.unified_search_service import (
    MAX_MERGE_WINDOW,
    UnifiedSearchResult,
    ContentSource,
    ContentFormat,
    _merge_and_paginate,
)


def _mk(title, *, author=None, year=None, isbn=None, score=1.0,
        source=ContentSource.LOCAL):
    return UnifiedSearchResult(
        id=f"{source.value}:{title}", source=source, source_id=title,
        title=title, author=author, format=ContentFormat.BOOK,
        publication_year=year, isbn=isbn, relevance_score=score,
    )


def test_merged_total_is_sum_of_source_totals():
    local = ([_mk("A"), _mk("B")], 1949)
    indie = ([_mk("C", source=ContentSource.INDIE)], 178)
    page, total, has_more = _merge_and_paginate(
        [local, indie], offset=0, limit=20,
        sort_by="title", sort_direction="asc", deduplicate=True,
    )
    assert total == 1949 + 178
    assert has_more is True


def test_sorts_by_requested_key_across_sources():
    local = ([_mk("Zed", year=2000), _mk("Apple", year=1990)], 2)
    indie = ([_mk("Mango", year=1995, source=ContentSource.INDIE)], 1)
    page, _total, _hm = _merge_and_paginate(
        [local, indie], offset=0, limit=10,
        sort_by="title", sort_direction="asc", deduplicate=True,
    )
    assert [r.title for r in page] == ["Apple", "Mango", "Zed"]


def test_year_desc_sort():
    local = ([_mk("old", year=1990), _mk("new", year=2024)], 2)
    page, _t, _h = _merge_and_paginate(
        [local], offset=0, limit=10,
        sort_by="year", sort_direction="desc", deduplicate=True,
    )
    assert [r.title for r in page] == ["new", "old"]


def test_relevance_sort_when_no_sort_key():
    local = ([_mk("low", score=0.1), _mk("high", score=0.9)], 2)
    page, _t, _h = _merge_and_paginate(
        [local], offset=0, limit=10,
        sort_by=None, sort_direction=None, deduplicate=True,
    )
    assert [r.title for r in page] == ["high", "low"]


def test_dedup_by_isbn_keeps_one():
    local = ([_mk("Dup", isbn="111")], 1)
    indie = ([_mk("Dup", isbn="111", source=ContentSource.INDIE)], 1)
    page, total, _h = _merge_and_paginate(
        [local, indie], offset=0, limit=10,
        sort_by="title", sort_direction="asc", deduplicate=True,
    )
    assert len(page) == 1
    assert total == 2


def test_offset_slices_page():
    local = ([_mk(f"t{i:02d}") for i in range(5)], 5)
    page, _t, _h = _merge_and_paginate(
        [local], offset=2, limit=2,
        sort_by="title", sort_direction="asc", deduplicate=True,
    )
    assert [r.title for r in page] == ["t02", "t03"]


def test_has_more_false_at_window_edge():
    local = ([_mk(f"t{i:04d}") for i in range(50)], 5000)
    _page, total, has_more = _merge_and_paginate(
        [local], offset=MAX_MERGE_WINDOW - 10, limit=10,
        sort_by="title", sort_direction="asc", deduplicate=True,
    )
    assert total == 5000
    assert has_more is False


import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_indie_returns_results_and_true_total(test_db):
    """_search_indie_ebooks reads the owned indie_ebooks table directly --
    the MetisLib client call was removed in the Tier-3 cutover (see
    app/services/unified_search_service.py:524 docstring: "MetisLib client
    call removed (Tier-3 cutover)"). It no longer proxies MetisLib's catalog
    API, so there's nothing left to mock via get_metislib_client; seed the
    local table instead.
    """
    from app.services.unified_search_service import UnifiedSearchService
    from app.models.indie_ebook_borrow import IndieEbook

    test_db.add(IndieEbook(
        title="Indie One", author_pen_name="A", isbn="999",
        publication_year=2024, copies_owned=1,
    ))
    await test_db.commit()

    svc = UnifiedSearchService(db=test_db)
    results, total = await svc._search_indie_ebooks("*", None, 100)
    assert total == 1
    assert len(results) == 1 and results[0].title == "Indie One"


@pytest.mark.asyncio
async def test_indie_failure_returns_empty_zero():
    from app.services.unified_search_service import UnifiedSearchService
    svc = UnifiedSearchService(db=None)
    boom = AsyncMock(side_effect=RuntimeError("metislib down"))
    with patch("app.services.metislib_client.get_metislib_client",
               return_value=AsyncMock(search_catalog=boom)):
        results, total = await svc._search_indie_ebooks("*", None, 100)
    assert results == [] and total == 0


@pytest.mark.asyncio
async def test_local_returns_results_and_true_total():
    from app.services.unified_search_service import UnifiedSearchService
    svc = UnifiedSearchService(db=None)
    fake_exec = AsyncMock(return_value={
        "items": [
            {"id": 1, "title": "Local A", "author": "Z", "item_type": "book",
             "isbn": "111", "publication_year": 2020, "status": "available"},
        ],
        "total": 1949,
    })
    with patch("app.api.v1.catalog.helpers._execute_catalog_search", fake_exec):
        results, total = await svc._search_local_catalog("*", None, 100)
    assert total == 1949
    assert len(results) == 1 and results[0].title == "Local A"
    _args, kwargs = fake_exec.call_args
    assert kwargs["per_page"] == min(100, MAX_MERGE_WINDOW)


@pytest.mark.asyncio
async def test_search_merges_true_totals_and_paginates():
    from app.services.unified_search_service import UnifiedSearchService
    svc = UnifiedSearchService(db=None)
    local = ([_mk("Apple", year=1990), _mk("Zed", year=2000)], 1949)
    indie = ([_mk("Mango", year=1995, source=ContentSource.INDIE)], 178)
    with patch.object(svc, "_search_local_catalog", AsyncMock(return_value=local)), \
         patch.object(svc, "_search_indie_ebooks", AsyncMock(return_value=indie)):
        resp = await svc.search(
            "*", limit=2, offset=0,
            sort_by="title", sort_direction="asc",
        )
    assert resp.total_results == 1949 + 178
    assert resp.has_more is True
    assert [r.title for r in resp.results] == ["Apple", "Mango"]
    assert resp.source_counts == {"local": 1949, "indie": 178}


@pytest.mark.asyncio
async def test_indie_pages_through_metislib_100_cap(test_db):
    """Requesting a small limit still reports the true total, not just the
    capped page size.

    REWRITTEN: the original test exercised MetisLib's 100-per-page API cap
    and this method's page-looping logic to gather all results despite it.
    That pagination logic no longer exists -- the Tier-3 cutover replaced
    the remote MetisLib call with a single local query
    (`.limit(min(limit, MAX_MERGE_WINDOW))`, see
    app/services/unified_search_service.py:524). What's left worth testing:
    the count query (true total) is independent of the results query
    (which is subject to `limit`), so a small `limit` still reports the
    real total row count.
    """
    from app.services.unified_search_service import UnifiedSearchService
    from app.models.indie_ebook_borrow import IndieEbook

    for i in range(5):
        test_db.add(IndieEbook(title=f"E{i}", copies_owned=1))
    await test_db.commit()

    svc = UnifiedSearchService(db=test_db)
    results, total = await svc._search_indie_ebooks("*", None, 3)
    assert total == 5
    assert len(results) == 3
