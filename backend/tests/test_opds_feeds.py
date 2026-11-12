# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the OPDS 1.2 / OPDS 2.0 navigation + acquisition feeds.

The OPDS spec is permissive about a lot of things and strict about a few
(media types, link rels, pagination semantics, ID stability). These tests
pin the strict parts so we don't accidentally regress and silently break
Aldiko Next, KOReader, Thorium, or Palace.

We don't run a network OPDS validator in CI -- those validators routinely
go down, and we never want a third-party outage to red-bar our pipeline.
Instead the tests parse the XML with lxml and assert structural invariants
straight from the spec.
"""
from __future__ import annotations

import os

import pytest
from lxml import etree

# Some tests depend on Postgres-only behavior (full-text search,
# subject_links eager-load through the joined CatalogItemSubject). The L30
# test conftest falls back to SQLite when the test Postgres isn't
# reachable, so we mark those tests skip-on-sqlite rather than break the
# fallback path that runs in dev.
_USING_SQLITE = "sqlite" in os.environ.get("DATABASE_URL", "sqlite")
requires_postgres = pytest.mark.skipif(
    _USING_SQLITE,
    reason="Requires Postgres (FTS, full subject join behavior).",
)

from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)
from app.models.subject import CatalogItemSubject, Subject

ATOM = "{http://www.w3.org/2005/Atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
OPENSEARCH_NS = "http://a9.com/-/spec/opensearch/1.1/"

OPDS_NAV_TYPE = "application/atom+xml;profile=opds-catalog;kind=navigation"
OPDS_ACQ_TYPE = "application/atom+xml;profile=opds-catalog;kind=acquisition"
OPDS_JSON_TYPE = "application/opds+json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_item(
    title: str,
    *,
    author: str = "Doe, Jane",
    item_type: ItemType = ItemType.book,
    status: ItemStatus = ItemStatus.available,
    cataloging_status: CatalogingStatus = CatalogingStatus.CATALOGED,
    sensitivity_level: SensitivityLevel = SensitivityLevel.PUBLIC,
    cover_url: str | None = "https://covers.openlibrary.org/b/id/1.jpg",
    description: str | None = "A test description.",
    publisher: str | None = "Test Press",
    isbn: str | None = "9780000000001",
    publication_year: int | None = 2020,
) -> CatalogItem:
    return CatalogItem(
        title=title,
        author=author,
        item_type=item_type,
        status=status,
        cataloging_status=cataloging_status,
        sensitivity_level=sensitivity_level,
        cover_url=cover_url,
        description=description,
        publisher=publisher,
        isbn=isbn,
        publication_year=publication_year,
    )


@pytest.fixture
async def public_items(test_db):
    """A small mixed corpus visible to anonymous OPDS browsers."""
    items = [
        _make_item("Alpha Book", author="Adams, Ann", item_type=ItemType.book),
        _make_item(
            "Beta Audio",
            author="Brown, Ben",
            item_type=ItemType.audiobook,
            isbn="9780000000002",
        ),
        _make_item(
            "Gamma Ebook",
            author="Chen, Charles",
            item_type=ItemType.ebook,
            isbn="9780000000003",
        ),
        _make_item(
            "Delta Book",
            author="9 Numeric, Author",
            item_type=ItemType.book,
            isbn="9780000000004",
        ),
    ]
    for it in items:
        test_db.add(it)
    await test_db.commit()
    for it in items:
        await test_db.refresh(it)
    return items


@pytest.fixture
async def hidden_items(test_db):
    """Items the public OPDS feed must NEVER return."""
    items = [
        _make_item(
            "Confidential",
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            isbn="9780000001000",
        ),
        _make_item(
            "Sensitive",
            sensitivity_level=SensitivityLevel.SENSITIVE,
            isbn="9780000001001",
        ),
        _make_item(
            "Withdrawn",
            status=ItemStatus.withdrawn,
            isbn="9780000001002",
        ),
        _make_item(
            "Still cataloging",
            cataloging_status=CatalogingStatus.IN_PROGRESS,
            isbn="9780000001003",
        ),
    ]
    for it in items:
        test_db.add(it)
    await test_db.commit()
    for it in items:
        await test_db.refresh(it)
    return items


@pytest.fixture
async def subject_with_items(test_db, public_items):
    """Pin a Subject to a couple of items so subject browse has data."""
    subj = Subject(label="Mystery fiction", slug="mystery-fiction")
    test_db.add(subj)
    await test_db.commit()
    await test_db.refresh(subj)
    for pos, it in enumerate(public_items[:2]):
        test_db.add(
            CatalogItemSubject(
                catalog_item_id=it.id,
                subject_id=subj.id,
                position=pos,
            )
        )
    await test_db.commit()
    return subj


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_atom(body: bytes) -> etree._Element:
    return etree.fromstring(body)


def _link_rels(feed: etree._Element) -> list[str]:
    return [link.get("rel") for link in feed.findall(f"{ATOM}link")]


def _entries(feed: etree._Element) -> list[etree._Element]:
    return feed.findall(f"{ATOM}entry")


# ---------------------------------------------------------------------------
# Root navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpdsRoot:
    async def test_root_returns_navigation_feed(self, client, public_items):
        response = await client.get("/api/v1/catalog/opds")
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith(OPDS_NAV_TYPE)
        feed = _parse_atom(response.content)
        assert feed.tag == f"{ATOM}feed"
        # All five nav subsections + search live on the root.
        titles = {e.findtext(f"{ATOM}title") for e in _entries(feed)}
        assert {
            "New additions",
            "Popular titles",
            "Browse by subject",
            "Browse by author",
            "Browse by format",
            "Search the catalog",
        }.issubset(titles)
        # rel=self always present.
        assert "self" in _link_rels(feed)

    async def test_root_json_negotiation(self, client, public_items):
        response = await client.get(
            "/api/v1/catalog/opds",
            headers={"accept": OPDS_JSON_TYPE},
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith(OPDS_JSON_TYPE)
        body = response.json()
        # OPDS 2.0 navigation has metadata + links + navigation arrays.
        assert "metadata" in body
        assert "links" in body
        assert "navigation" in body
        titles = {n["title"] for n in body["navigation"]}
        assert "New additions" in titles


# ---------------------------------------------------------------------------
# Acquisition feed: /opds/new
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpdsNew:
    async def test_new_returns_acquisition_feed(
        self, client, public_items, hidden_items
    ):
        response = await client.get("/api/v1/catalog/opds/new")
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith(OPDS_ACQ_TYPE)
        feed = _parse_atom(response.content)
        titles = {e.findtext(f"{ATOM}title") for e in _entries(feed)}
        # Only public + cataloged + non-withdrawn items appear.
        assert "Alpha Book" in titles
        assert "Beta Audio" in titles
        for hidden in ("Confidential", "Sensitive", "Withdrawn", "Still cataloging"):
            assert hidden not in titles, (
                f"{hidden!r} leaked into public OPDS feed"
            )

    async def test_entry_has_borrow_and_image_links(
        self, client, public_items
    ):
        response = await client.get("/api/v1/catalog/opds/new")
        feed = _parse_atom(response.content)
        for entry in _entries(feed):
            rels = [link.get("rel") for link in entry.findall(f"{ATOM}link")]
            assert "http://opds-spec.org/acquisition/borrow" in rels, (
                f"Missing borrow link on {entry.findtext(f'{ATOM}title')!r}"
            )
            # public_items all have cover_url set, so image links present.
            assert "http://opds-spec.org/image" in rels
            assert "http://opds-spec.org/image/thumbnail" in rels

    async def test_opensearch_total_results_element(
        self, client, public_items
    ):
        response = await client.get("/api/v1/catalog/opds/new")
        feed = _parse_atom(response.content)
        total_el = feed.find(f"{OPENSEARCH}totalResults")
        assert total_el is not None
        # >= rather than == because the test session DB may carry items
        # from fixtures in adjacent test files (the cleanup pass in
        # conftest is best-effort). What matters here is the element is
        # present and parses as an int >= our seeded count.
        assert int(total_el.text) >= len(public_items)

    async def test_pagination_first_page_has_no_previous(
        self, client, public_items
    ):
        # per_page=2 with >=4 items guarantees a "next" page; using a
        # very small per_page keeps the assertion robust against any
        # ambient items in the test DB.
        response = await client.get(
            "/api/v1/catalog/opds/new?page=1&per_page=2"
        )
        feed = _parse_atom(response.content)
        rels = _link_rels(feed)
        assert "previous" not in rels
        assert "first" not in rels
        assert "next" in rels
        assert "last" in rels

    async def test_pagination_last_page_has_no_next(
        self, client, public_items, test_db
    ):
        # Compute the last page from the actual DB count so this test is
        # robust against ambient rows from earlier fixtures.
        from sqlalchemy import select, func
        from app.models.catalog import (
            CatalogItem,
            CatalogingStatus,
            ItemStatus,
            SensitivityLevel,
        )
        per_page = 2
        total = (
            await test_db.execute(
                select(func.count(CatalogItem.id)).where(
                    CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
                    CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC,
                    CatalogItem.status != ItemStatus.withdrawn,
                )
            )
        ).scalar() or 0
        last_page = max(1, (total + per_page - 1) // per_page)
        response = await client.get(
            f"/api/v1/catalog/opds/new?page={last_page}&per_page={per_page}"
        )
        feed = _parse_atom(response.content)
        rels = _link_rels(feed)
        assert "next" not in rels
        assert "last" not in rels
        if last_page > 1:
            assert "previous" in rels
            assert "first" in rels


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpdsSubjects:
    @requires_postgres
    async def test_subjects_nav_lists_present_subject(
        self, client, subject_with_items
    ):
        response = await client.get("/api/v1/catalog/opds/subjects")
        assert response.status_code == 200, response.text
        feed = _parse_atom(response.content)
        titles = [e.findtext(f"{ATOM}title") for e in _entries(feed)]
        assert any(t and "Mystery fiction" in t for t in titles), titles

    @requires_postgres
    async def test_subject_acquisition_returns_only_tagged_items(
        self, client, subject_with_items, public_items
    ):
        response = await client.get(
            "/api/v1/catalog/opds/subjects/mystery-fiction"
        )
        assert response.status_code == 200, response.text
        feed = _parse_atom(response.content)
        titles = {e.findtext(f"{ATOM}title") for e in _entries(feed)}
        # We pinned the first two public_items to the subject.
        assert "Alpha Book" in titles
        assert "Beta Audio" in titles
        # ...but NOT the un-tagged ones.
        assert "Gamma Ebook" not in titles
        assert "Delta Book" not in titles

    async def test_unknown_subject_404s(self, client):
        response = await client.get(
            "/api/v1/catalog/opds/subjects/does-not-exist"
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Author prefix browse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpdsByAuthor:
    async def test_by_author_nav_returns_az(self, client):
        response = await client.get("/api/v1/catalog/opds/by-author")
        assert response.status_code == 200
        feed = _parse_atom(response.content)
        titles = [e.findtext(f"{ATOM}title") for e in _entries(feed)]
        # A-Z (26), 0-9, OTHER.
        assert len(titles) == 28
        assert "A" in titles
        assert "Z" in titles

    async def test_letter_prefix_filters_authors(
        self, client, public_items
    ):
        response = await client.get("/api/v1/catalog/opds/by-author/a")
        feed = _parse_atom(response.content)
        titles = {e.findtext(f"{ATOM}title") for e in _entries(feed)}
        # Adams, Ann -- Alpha Book.
        assert "Alpha Book" in titles
        # No B-, C-, 9-authored items.
        assert "Beta Audio" not in titles

    async def test_digit_prefix(self, client, public_items):
        response = await client.get("/api/v1/catalog/opds/by-author/0-9")
        feed = _parse_atom(response.content)
        titles = {e.findtext(f"{ATOM}title") for e in _entries(feed)}
        # "9 Numeric, Author" starts with a digit.
        assert "Delta Book" in titles

    async def test_invalid_prefix_400s(self, client):
        response = await client.get("/api/v1/catalog/opds/by-author/zz")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpdsFormats:
    async def test_formats_nav(self, client):
        response = await client.get("/api/v1/catalog/opds/formats")
        feed = _parse_atom(response.content)
        titles = {e.findtext(f"{ATOM}title") for e in _entries(feed)}
        assert {"Book", "Ebook", "Audiobook"} == titles

    async def test_format_audiobook_only(self, client, public_items):
        response = await client.get("/api/v1/catalog/opds/formats/audiobook")
        feed = _parse_atom(response.content)
        titles = {e.findtext(f"{ATOM}title") for e in _entries(feed)}
        assert "Beta Audio" in titles
        assert "Alpha Book" not in titles
        assert "Gamma Ebook" not in titles

    async def test_unknown_format_404s(self, client):
        response = await client.get("/api/v1/catalog/opds/formats/sonnet")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Search + OpenSearch description doc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpdsSearch:
    async def test_no_query_returns_opensearch_description(self, client):
        response = await client.get("/api/v1/catalog/opds/search")
        assert response.status_code == 200, response.text
        assert "opensearchdescription+xml" in response.headers["content-type"]
        root = _parse_atom(response.content)
        assert root.tag.endswith("OpenSearchDescription")
        urls = root.findall(f"{{{OPENSEARCH_NS}}}Url")
        assert urls, "OpenSearch doc must include at least one <Url> template"
        templates = [u.get("template") for u in urls]
        assert all("{searchTerms}" in t for t in templates)

    @requires_postgres
    async def test_query_returns_acquisition_feed(
        self, client, public_items
    ):
        response = await client.get("/api/v1/catalog/opds/search?q=Alpha")
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith(OPDS_ACQ_TYPE)
        feed = _parse_atom(response.content)
        titles = {e.findtext(f"{ATOM}title") for e in _entries(feed)}
        assert "Alpha Book" in titles


# ---------------------------------------------------------------------------
# Legacy /catalog.xml back-compat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLegacyFlatFeed:
    async def test_legacy_route_still_returns_feed(
        self, client, public_items
    ):
        response = await client.get(
            "/api/v1/catalog/opds/catalog.xml"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(OPDS_ACQ_TYPE)
        feed = _parse_atom(response.content)
        assert feed.tag == f"{ATOM}feed"
