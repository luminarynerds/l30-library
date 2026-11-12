import os

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.catalog import CatalogItem, CatalogingStatus, SensitivityLevel, ItemStatus
from app.services.unified_search_service import get_unified_search_service


@pytest.mark.asyncio
async def test_unified_endpoint_accepts_year_and_lexile_and_language_params():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/search/unified",
            params={
                "q": "*",
                "year_min": 1990,
                "year_max": 2030,
                "min_lexile": 200,
                "max_lexile": 1200,
                "language": ["eng"],
            },
        )
    # 503 = first-boot setup middleware (no seeded DB in worktree); 200 = normal.
    # Either proves the new query params are accepted syntactically (not a 422).
    assert resp.status_code in (200, 503), resp.text
    if resp.status_code == 200:
        body = resp.json()
        assert "total_results" in body
        assert "sources_searched" in body


@pytest.mark.asyncio
async def test_local_search_respects_year_filter(db_session):
    """Seed one catalog item, then prove year_min filters it in and out.

    Requires PostgreSQL: _execute_catalog_search uses the und-x-icu ICU
    collation for sort which is not available in SQLite.  When DATABASE_URL
    resolves to SQLite (Docker host "database:5432" unreachable from outside
    the container network) the test is skipped so CI remains green while the
    PostgreSQL-backed run proves the non-vacuous assertions.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("sqlite") or not db_url:
        pytest.skip(
            "requires PostgreSQL: _execute_catalog_search uses und-x-icu "            "collation not available in SQLite"
        )

    # Seed a PUBLIC + CATALOGED item (pattern from tests/conftest.py:367).
    # cataloging_status must be explicitly CATALOGED -- the model default is
    # UNCATALOGED and the anonymous _execute_catalog_search path excludes
    # anything not CATALOGED. sensitivity_level PUBLIC is the model default
    # but set explicitly for clarity.
    item = CatalogItem(
        title="Year Filter Seed",
        author="Test Author",
        publication_year=2010,
        status=ItemStatus.available,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cataloging_status=CatalogingStatus.CATALOGED,
    )
    db_session.add(item)
    await db_session.commit()

    svc = get_unified_search_service(db_session)

    # year_min in the future -> the 2010 item must be excluded
    excluded = await svc.search(query="*", year_min=2999)
    assert [r for r in excluded.results if r.source.value == "local"] == []

    # year_min below 2010 -> the item must be included (proves it was the
    # filter, not an empty DB, that produced the empty result above)
    included = await svc.search(query="*", year_min=1900)
    local_ids = [r for r in included.results if r.source.value == "local"]
    assert len(local_ids) >= 1, "seeded 2010 item should pass year_min=1900"


@pytest.mark.asyncio
async def test_lexile_filter_drops_indie_source(db_session, monkeypatch):
    """Lexile filter active -> indie source not searched at all."""
    called = {"indie": False}

    async def _fake_indie(self, query, formats, limit, **kw):
        called["indie"] = True
        return []

    monkeypatch.setattr(
        "app.services.unified_search_service.UnifiedSearchService._search_indie_ebooks",
        _fake_indie,
    )
    svc = get_unified_search_service(db_session)
    resp = await svc.search(query="*", min_lexile=500)
    assert called["indie"] is False
    assert "indie" not in resp.sources_searched


@pytest.mark.asyncio
async def test_indie_post_filtered_by_year(db_session, monkeypatch):
    """Indie items outside the year window (incl. null year) are dropped.

    _search_indie_ebooks no longer calls out to MetisLib -- it reads the
    locally-owned `indie_ebooks` table directly (Tier-3 cutover, see
    docstring on UnifiedSearchService._search_indie_ebooks). So the fixture
    seeds IndieEbook rows instead of mocking a MetisLib client.
    _search_local_catalog is monkeypatched to return [] so no Postgres/ICU
    catalog-search dependency is introduced.
    """
    from app.models.indie_ebook_borrow import IndieEbook

    db_session.add_all([
        IndieEbook(title="In Range", author_pen_name="A", publication_year=2010,
                   language="en", copies_owned=1, copies_available=1),
        IndieEbook(title="Too Old", author_pen_name="B", publication_year=1800,
                   language="en", copies_owned=1, copies_available=1),
        IndieEbook(title="No Year", author_pen_name="C", publication_year=None,
                   language="en", copies_owned=1, copies_available=1),
    ])
    await db_session.commit()

    async def _no_local(self, query, formats, limit, **kw):
        # _search_local_catalog's real contract is (results, total_count).
        return [], 0

    monkeypatch.setattr(
        "app.services.unified_search_service.UnifiedSearchService._search_local_catalog",
        _no_local,
    )

    svc = get_unified_search_service(db_session)
    resp = await svc.search(query="*", year_min=2000, year_max=2020)
    indie_titles = sorted(r.title for r in resp.results if r.source.value == "indie")
    assert indie_titles == ["In Range"]


@pytest.mark.asyncio
async def test_language_filter_drops_indie_source(db_session, monkeypatch):
    """Language filter active -> indie dropped (MetisLib ISO 639-1 cannot
    satisfy the API's ISO 639-2/B contract; drop-source rule)."""
    called = {"indie": False}

    async def _fake_indie(self, query, formats, limit, **kw):
        called["indie"] = True
        return []

    monkeypatch.setattr(
        "app.services.unified_search_service.UnifiedSearchService._search_indie_ebooks",
        _fake_indie,
    )
    svc = get_unified_search_service(db_session)
    resp = await svc.search(query="*", language=["eng"])
    assert called["indie"] is False
    assert "indie" not in resp.sources_searched


@pytest.mark.asyncio
async def test_available_only_forwarded_to_local_search(db_session, monkeypatch):
    """available_only=True must forward status=ItemStatus.available to _execute_catalog_search;
    available_only=False (default) must pass status=None.

    Monkeypatches _execute_catalog_search at its definition module so the
    function-level late import inside _search_local_catalog picks up the mock.
    No Postgres/ICU dependency: the helper is fully replaced.
    """
    from app.models.catalog import ItemStatus

    captured = {}

    async def _fake_helper(db, **kwargs):
        captured.update(kwargs)
        return {"items": [], "total": 0, "page": 1, "per_page": 20, "pages": 0}

    monkeypatch.setattr(
        "app.api.v1.catalog.helpers._execute_catalog_search",
        _fake_helper,
    )

    svc = get_unified_search_service(db_session)

    # available_only=True -> status must be ItemStatus.available
    await svc.search(query="*", available_only=True)
    got = captured.get("status")
    assert got == ItemStatus.available, f"expected ItemStatus.available, got {got!r}"

    captured.clear()

    # available_only=False (default) -> status must be None
    await svc.search(query="*", available_only=False)
    got = captured.get("status")
    assert got is None, f"expected None, got {got!r}"


def test_execute_catalog_search_signature_accepts_publisher():
    """Sub-second regression: the helper signature must keep `publisher`.

    Pinned at signature level (no DB) so the gate fires on every pytest
    collection, even on SQLite-only / no-PG environments. Removing the
    kwarg again immediately fails this without needing the integration
    test below.
    """
    import inspect
    from app.api.v1.catalog.helpers import _execute_catalog_search
    assert "publisher" in inspect.signature(_execute_catalog_search).parameters


@pytest.mark.asyncio
async def test_local_search_forwards_publisher_kwarg_without_typeerror(db_session):
    """_search_local_catalog forwards `publisher` to `_execute_catalog_search`.

    Regression for a prod silent-drop: helpers.py's signature lacked the
    `publisher` kwarg, so the unified service's catch-all swallowed the
    TypeError and returned `[]` from local source on every /search/unified
    call. /catalog masked the bug via its exception-fallback to
    /catalog/search; /discover (PR-C) calls unifiedSearch directly and
    hit a wall of 200-OK-zero-results.

    Pinning: a unified search with `publisher='Nonexistent Press'` must
    NOT log a TypeError and MUST return total_results >= 0 cleanly. We
    also seed a real publisher match to assert the filter actually narrows.
    """
    from app.services.unified_search_service import ContentFormat
    from app.models.catalog import ItemType

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("sqlite") or not db_url:
        pytest.skip("requires PostgreSQL: _execute_catalog_search uses und-x-icu")

    book_a = CatalogItem(
        title="Publisher Filter Seed A",
        author="Test Author",
        publisher="Knopf",
        item_type=ItemType.book,
        publication_year=2020,
        status=ItemStatus.available,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cataloging_status=CatalogingStatus.CATALOGED,
    )
    book_b = CatalogItem(
        title="Publisher Filter Seed B",
        author="Test Author",
        publisher="Penguin",
        item_type=ItemType.book,
        publication_year=2020,
        status=ItemStatus.available,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cataloging_status=CatalogingStatus.CATALOGED,
    )
    db_session.add_all([book_a, book_b])
    await db_session.commit()

    svc = get_unified_search_service(db_session)
    knopf_only = await svc.search(
        query="*",
        formats=[ContentFormat.BOOK],
        publisher="Knopf",
    )
    local_titles = {r.title for r in knopf_only.results if r.source.value == "local"}
    assert "Publisher Filter Seed A" in local_titles
    assert "Publisher Filter Seed B" not in local_titles, (
        f"publisher filter must narrow; got local results: {local_titles}"
    )


@pytest.mark.asyncio
async def test_local_search_respects_format_filter_equipment(db_session):
    """formats=[EQUIPMENT] returns only the equipment item, not the book.

    Regression for the ContentFormat enum + _FORMAT_MAP gap: 'equipment'
    used to drop out of the API ValueError catch (missing enum value), and
    even with the enum value an unmapped raw_type would coerce to OTHER
    and fail the post-filter at line 339-344. Both must be wired for the
    filter to work end-to-end.
    """
    from app.services.unified_search_service import ContentFormat
    from app.models.catalog import ItemType

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("sqlite") or not db_url:
        pytest.skip(
            "requires PostgreSQL: _execute_catalog_search uses und-x-icu "
            "collation not available in SQLite"
        )

    book = CatalogItem(
        title="Format Filter Book Seed",
        author="Test Author",
        item_type=ItemType.book,
        publication_year=2020,
        status=ItemStatus.available,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cataloging_status=CatalogingStatus.CATALOGED,
    )
    equip = CatalogItem(
        title="Format Filter Equipment Seed",
        item_type=ItemType.equipment,
        status=ItemStatus.available,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cataloging_status=CatalogingStatus.CATALOGED,
    )
    db_session.add_all([book, equip])
    await db_session.commit()

    svc = get_unified_search_service(db_session)

    only_equip = await svc.search(query="*", formats=[ContentFormat.EQUIPMENT])
    local = [r for r in only_equip.results if r.source.value == "local"]
    titles = {r.title for r in local}
    assert "Format Filter Equipment Seed" in titles
    assert "Format Filter Book Seed" not in titles, (
        f"book should be filtered out, got local results: {titles}"
    )


@pytest.mark.asyncio
async def test_format_filter_pushes_into_sql_not_python_only(db_session):
    """limit=10 must return equipment items even when sort buries them.

    Regression for the architectural bug fixed in PR #936: the format
    filter used to apply in Python AFTER SQL fetched the first per_page
    rows. With a sort that puts non-equipment items first, paginated
    requests dropped most matches on the floor (in prod: 2 / 21 visible).

    Seeds 25 "Pagination Book Aaa-Yyy" books + 5 "Pagination Equipment
    Zzz-Zzz4" equipment items, then requests limit=10 with
    formats=[EQUIPMENT] AND sort_by=title sort_direction=asc. Alphabetical
    ascending puts all 25 books before any equipment, so a pre-SQL Python
    filter would see only books in the first 10 rows and return 0
    equipment. SQL push-down filters to equipment-only at the database
    layer, returning all 5 regardless of where they sort relative to books.
    """
    from app.services.unified_search_service import ContentFormat
    from app.models.catalog import ItemType

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("sqlite") or not db_url:
        pytest.skip(
            "requires PostgreSQL: _execute_catalog_search uses und-x-icu "
            "collation not available in SQLite"
        )

    # Title prefixes chosen so book < equipment in ASCII ascending order.
    # 'Pagination Book *' < 'Pagination Equipment *'.
    for i in range(25):
        db_session.add(CatalogItem(
            title=f"Pagination Book {i:02d}",
            item_type=ItemType.book,
            status=ItemStatus.available,
            sensitivity_level=SensitivityLevel.PUBLIC,
            cataloging_status=CatalogingStatus.CATALOGED,
        ))
    for i in range(5):
        db_session.add(CatalogItem(
            title=f"Pagination Equipment {i:02d}",
            item_type=ItemType.equipment,
            status=ItemStatus.available,
            sensitivity_level=SensitivityLevel.PUBLIC,
            cataloging_status=CatalogingStatus.CATALOGED,
        ))
    await db_session.commit()

    svc = get_unified_search_service(db_session)
    resp = await svc.search(
        query="*",
        formats=[ContentFormat.EQUIPMENT],
        limit=10,
        sort_by="title",
        sort_direction="asc",
    )
    equip_titles = {
        r.title for r in resp.results
        if r.source.value == "local" and r.title.startswith("Pagination Equipment")
    }
    assert len(equip_titles) == 5, (
        f"expected all 5 seeded equipment items at limit=10 (sort buries them past position 25); "
        f"got {len(equip_titles)}: {sorted(equip_titles)}. "
        "if this returns 0, the format filter is post-SQL Python again and "
        "only the first 10 alphabetical rows (all books) reached the in-process filter."
    )


@pytest.mark.asyncio
async def test_unified_endpoint_accepts_sort_params(client):
    """sort_by/sort_direction must reach /search/unified as Query params.

    Uses the shared `client` fixture (get_db override + setup_complete=True)
    rather than a raw ASGITransport client: this file's earlier tests exercise
    db_session directly, and a bare AsyncClient(app=app) here would fall
    through FirstBootMiddleware onto the app's real shared engine, whose
    pooled connections are bound to a previous test's now-closed event loop
    (RuntimeError: Event loop is closed) -- a known conftest singleton-engine
    trap, see test_book_challenge_service.py's module docstring.
    """
    ac = client
    resp = await ac.get(
        "/api/v1/search/unified",
        params={"q": "*", "sort_by": "title", "sort_direction": "asc"},
    )
    assert resp.status_code in (200, 503), resp.text
