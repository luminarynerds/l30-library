# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""OPDS (Open Publication Distribution System) feeds.

This module exposes the L30 catalog as an OPDS 1.2 (Atom XML) and OPDS 2.0
(JSON) navigation hierarchy so patrons can browse from real OPDS readers
(Aldiko Next, Thorium, KOReader, Foliate, Palace) and so MetisLib can
federate L30 catalogs without scraping HTML.

Route map (mounted under ``/api/v1/catalog``)::

    /opds                              -> root navigation feed
    /opds/new                          -> acquisition: recent additions
    /opds/popular                      -> acquisition: most recently added
                                          (no circulation_count column yet)
    /opds/subjects                     -> navigation: A-Z subjects
    /opds/subjects/{slug}              -> acquisition: items in a subject
    /opds/by-author                    -> navigation: A-Z author prefixes
    /opds/by-author/{prefix}           -> acquisition: authors by prefix
    /opds/formats                      -> navigation: item-type buckets
    /opds/formats/{item_type}          -> acquisition: filtered by type
    /opds/search                       -> OpenSearch description doc
                                          (XML) or, with ?q=, an acquisition
                                          feed running the catalog search
    /opds/catalog.xml                  -> legacy single flat feed
                                          (kept for back-compat with the
                                          Palace registration)

Content negotiation: ``Accept: application/opds+json`` returns OPDS 2.0
JSON; anything else (including the default) returns OPDS 1.2 Atom XML.
Phase 1 is anonymous-public read-only; auth-aware feeds (patron borrows,
holds) are a Phase 2 follow-up.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import and_, distinct, func, literal, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)
from app.models.subject import CatalogItemSubject, Subject
from app.services.opds_serializers import (
    OPDS_ACQ_TYPE,
    OPDS_JSON_TYPE,
    OPDS_NAV_TYPE,
    OPENSEARCH_DESC_TYPE,
    opensearch_description,
    to_opds1_acq,
    to_opds1_nav,
    to_opds2_acq,
    to_opds2_nav,
)

from .helpers import _escape_ilike, _execute_catalog_search

router = APIRouter(prefix="/opds", tags=["opds"])

# Default & max page sizes for OPDS acquisition feeds. OPDS readers
# generally request the default page first, then paginate; keep the
# default modest so first paint stays responsive.
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

# Item types we surface as standalone format buckets.
FORMAT_BUCKETS = ("book", "ebook", "audiobook")


# ---------------------------------------------------------------------------
# Tenant / base-URL helpers
# ---------------------------------------------------------------------------


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return OPDS_JSON_TYPE in accept


# ---------------------------------------------------------------------------
# Catalog query (anonymous, public-only) -- thin SQL wrapper
# ---------------------------------------------------------------------------


def _anonymous_visibility_filter(query):
    return query.where(
        CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
        CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC,
        CatalogItem.status != ItemStatus.withdrawn,
    )


async def _fetch_items(
    db: AsyncSession,
    *,
    extra_filters: Sequence | None = None,
    order_by=None,
    page: int = 1,
    per_page: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[CatalogItem], int]:
    base = select(CatalogItem).options(selectinload(CatalogItem.images))
    count = select(func.count(CatalogItem.id))
    base = _anonymous_visibility_filter(base)
    count = _anonymous_visibility_filter(count)
    for f in extra_filters or []:
        base = base.where(f)
        count = count.where(f)

    total = (await db.execute(count)).scalar() or 0
    order_clause = order_by if order_by is not None else CatalogItem.created_at.desc()
    page_query = (
        base.order_by(order_clause)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = (await db.execute(page_query)).scalars().all()
    return list(items), total


# ---------------------------------------------------------------------------
# Pagination + response shaping
# ---------------------------------------------------------------------------


def _pagination_links(
    request: Request, page: int, per_page: int, total: int
) -> list[dict]:
    from urllib.parse import urlencode

    pages = max(1, (total + per_page - 1) // per_page)
    url = request.url
    # request.url is a starlette URL; we use query_params (Multi-Dict) for
    # parsing and rebuild via urlencode so non-page query params (e.g. ?q=)
    # survive pagination.
    base_qp = dict(request.query_params)

    def _with(new_page: int) -> str:
        qp = dict(base_qp)
        qp["page"] = str(new_page)
        qp["per_page"] = str(per_page)
        return str(url.replace(query=urlencode(qp)))

    links: list[dict] = []
    if page > 1:
        links.append({"rel": "first", "href": _with(1), "type": OPDS_ACQ_TYPE})
        links.append({"rel": "previous", "href": _with(page - 1), "type": OPDS_ACQ_TYPE})
    if page < pages:
        links.append({"rel": "next", "href": _with(page + 1), "type": OPDS_ACQ_TYPE})
        links.append({"rel": "last", "href": _with(pages), "type": OPDS_ACQ_TYPE})
    return links


def _start_and_up_links(request: Request) -> list[dict]:
    base = _base_url(request)
    return [
        {
            "rel": "start",
            "href": f"{base}/api/v1/catalog/opds",
            "type": OPDS_NAV_TYPE,
            "title": "Catalog root",
        },
        {
            "rel": "search",
            "href": f"{base}/api/v1/catalog/opds/search",
            "type": OPENSEARCH_DESC_TYPE,
            "title": "Search the catalog",
        },
    ]


def _respond_acq(
    request: Request,
    *,
    feed_id: str,
    title: str,
    items: list[CatalogItem],
    total: int,
    page: int,
    per_page: int,
    extra_links: Sequence[dict] | None = None,
) -> Response:
    base = _base_url(request)
    self_url = str(request.url)
    pag_links = list(_pagination_links(request, page, per_page, total))
    common_links = pag_links + list(extra_links or []) + _start_and_up_links(request)

    if _wants_json(request):
        return JSONResponse(
            to_opds2_acq(
                feed_id=feed_id,
                title=title,
                self_url=self_url,
                items=items,
                base_url=base,
                links=common_links,
                total=total,
                page=page,
                per_page=per_page,
            ),
            media_type=OPDS_JSON_TYPE,
        )
    return Response(
        to_opds1_acq(
            feed_id=feed_id,
            title=title,
            self_url=self_url,
            items=items,
            base_url=base,
            links=common_links,
            total=total,
            page=page,
            per_page=per_page,
        ),
        media_type=OPDS_ACQ_TYPE,
    )


def _respond_nav(
    request: Request,
    *,
    feed_id: str,
    title: str,
    entries: list[dict],
) -> Response:
    base = _base_url(request)
    self_url = str(request.url)
    links = _start_and_up_links(request)
    if _wants_json(request):
        return JSONResponse(
            to_opds2_nav(
                feed_id=feed_id,
                title=title,
                self_url=self_url,
                entries=entries,
                base_url=base,
                links=links,
            ),
            media_type=OPDS_JSON_TYPE,
        )
    return Response(
        to_opds1_nav(
            feed_id=feed_id,
            title=title,
            self_url=self_url,
            entries=entries,
            base_url=base,
            links=links,
        ),
        media_type=OPDS_NAV_TYPE,
    )


# ---------------------------------------------------------------------------
# Routes -- navigation
# ---------------------------------------------------------------------------


@router.get("", include_in_schema=True)
@router.get("/")
async def opds_root(request: Request) -> Response:
    """Root catalog navigation feed."""
    entries = [
        {
            "id": "urn:l30:opds:new",
            "title": "New additions",
            "href": "/api/v1/catalog/opds/new",
            "type": OPDS_ACQ_TYPE,
            "summary": "Recently cataloged titles.",
        },
        {
            "id": "urn:l30:opds:popular",
            "title": "Popular titles",
            "href": "/api/v1/catalog/opds/popular",
            "type": OPDS_ACQ_TYPE,
            "summary": "Currently the same as 'new' until circulation counts are tracked.",
        },
        {
            "id": "urn:l30:opds:subjects",
            "title": "Browse by subject",
            "href": "/api/v1/catalog/opds/subjects",
            "type": OPDS_NAV_TYPE,
            "summary": "Subjects from the catalog's controlled vocabulary.",
        },
        {
            "id": "urn:l30:opds:by-author",
            "title": "Browse by author",
            "href": "/api/v1/catalog/opds/by-author",
            "type": OPDS_NAV_TYPE,
            "summary": "Authors grouped by first-letter prefix.",
        },
        {
            "id": "urn:l30:opds:formats",
            "title": "Browse by format",
            "href": "/api/v1/catalog/opds/formats",
            "type": OPDS_NAV_TYPE,
            "summary": "Books, ebooks, audiobooks.",
        },
        {
            "id": "urn:l30:opds:search",
            "title": "Search the catalog",
            "href": "/api/v1/catalog/opds/search",
            "type": OPENSEARCH_DESC_TYPE,
            "summary": "OpenSearch description document.",
        },
    ]
    return _respond_nav(
        request,
        feed_id="urn:l30:opds:root",
        title="L30 library catalog",
        entries=entries,
    )


@router.get("/new")
async def opds_new(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Most recently added catalog items."""
    items, total = await _fetch_items(
        db,
        order_by=CatalogItem.created_at.desc(),
        page=page,
        per_page=per_page,
    )
    return _respond_acq(
        request,
        feed_id="urn:l30:opds:new",
        title="New additions",
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/popular")
async def opds_popular(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Most popular titles.

    There's no ``circulation_count`` column on ``catalog_items`` today, so
    the implementation falls back to recency. When the popularity rollup
    lands (TODO: track in a separate plan), swap ``order_by`` here.
    """
    items, total = await _fetch_items(
        db,
        order_by=CatalogItem.created_at.desc(),
        page=page,
        per_page=per_page,
    )
    return _respond_acq(
        request,
        feed_id="urn:l30:opds:popular",
        title="Popular titles",
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------


@router.get("/subjects")
async def opds_subjects(
    request: Request,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Navigation feed of subjects with item counts.

    Caps the list at ``limit`` (default 200) because LCSH-style vocabs can
    produce thousands of distinct labels; paginating a nav feed is awkward
    and most readers don't honor it well.
    """
    # Count items per subject, scoped to visible-to-anonymous items.
    item_count = func.count(distinct(CatalogItemSubject.catalog_item_id)).label(
        "item_count"
    )
    query = (
        select(Subject.slug, Subject.label, item_count)
        .join(
            CatalogItemSubject,
            CatalogItemSubject.subject_id == Subject.id,
        )
        .join(
            CatalogItem,
            CatalogItem.id == CatalogItemSubject.catalog_item_id,
        )
        .where(
            CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
            CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC,
            CatalogItem.status != ItemStatus.withdrawn,
        )
        .group_by(Subject.slug, Subject.label)
        .order_by(Subject.label.collate("und-x-icu").asc())
        .limit(limit)
    )
    rows = (await db.execute(query)).all()
    entries = [
        {
            "id": f"urn:l30:opds:subject:{slug}",
            "title": f"{label} ({count})",
            "href": f"/api/v1/catalog/opds/subjects/{slug}",
            "type": OPDS_ACQ_TYPE,
        }
        for slug, label, count in rows
    ]
    return _respond_nav(
        request,
        feed_id="urn:l30:opds:subjects",
        title="Browse by subject",
        entries=entries,
    )


@router.get("/subjects/{slug}")
async def opds_subject_items(
    request: Request,
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Acquisition feed of items tagged with a given subject slug."""
    # Resolve slug to a Subject so we can use its label in the feed title.
    subject = (
        await db.execute(select(Subject).where(Subject.slug == slug))
    ).scalar_one_or_none()
    if subject is None:
        raise HTTPException(status_code=404, detail="Unknown subject")

    subject_exists = (
        select(literal(1))
        .select_from(CatalogItemSubject)
        .where(
            CatalogItemSubject.catalog_item_id == CatalogItem.id,
            CatalogItemSubject.subject_id == subject.id,
        )
        .exists()
    )
    items, total = await _fetch_items(
        db,
        extra_filters=[subject_exists],
        order_by=CatalogItem.title.collate("und-x-icu").asc(),
        page=page,
        per_page=per_page,
    )
    return _respond_acq(
        request,
        feed_id=f"urn:l30:opds:subject:{slug}",
        title=f"Subject: {subject.label}",
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# Authors
# ---------------------------------------------------------------------------


# A-Z plus a bucket for everything else (digits, non-Latin scripts, "The ...").
_AUTHOR_PREFIXES = list("abcdefghijklmnopqrstuvwxyz") + ["0-9", "other"]


@router.get("/by-author")
async def opds_by_author(request: Request) -> Response:
    """Navigation feed: A-Z author-prefix index.

    Static entries -- we don't query the DB to enumerate present letters
    because the list is short and a missing letter is harmless (the
    acquisition feed just renders empty). Adding live counts would mean
    a 27-row group-by per request, which isn't worth it.
    """
    entries = [
        {
            "id": f"urn:l30:opds:by-author:{p}",
            "title": p.upper(),
            "href": f"/api/v1/catalog/opds/by-author/{p}",
            "type": OPDS_ACQ_TYPE,
        }
        for p in _AUTHOR_PREFIXES
    ]
    return _respond_nav(
        request,
        feed_id="urn:l30:opds:by-author",
        title="Browse by author",
        entries=entries,
    )


@router.get("/by-author/{prefix}")
async def opds_by_author_items(
    request: Request,
    prefix: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Acquisition feed of items by author starting with ``prefix``.

    ``prefix='0-9'`` matches any author starting with a digit;
    ``prefix='other'`` matches authors starting with a non-ASCII letter
    (anything outside ``[A-Za-z0-9]``).
    """
    p = prefix.lower()
    if p == "0-9":
        # Authors starting with any digit. We OR the ten digit prefixes
        # rather than use SIMILAR TO / regex so this works on both
        # Postgres (prod) and SQLite (test fallback).
        filt = or_(*(CatalogItem.author.ilike(f"{d}%") for d in "0123456789"))
    elif p == "other":
        # Authors whose first char is NOT A-Z or 0-9. We can't express
        # "regex NOT [A-Za-z0-9]%" portably, so AND together NOT-LIKE for
        # every Latin letter + every digit. This is a small constant
        # number of predicates (36) and the index on author still applies.
        excluded = list("abcdefghijklmnopqrstuvwxyz0123456789")
        filt = and_(
            CatalogItem.author.isnot(None),
            *(~CatalogItem.author.ilike(f"{c}%") for c in excluded),
        )
    elif len(p) == 1 and p.isalpha():
        filt = CatalogItem.author.ilike(f"{_escape_ilike(p)}%")
    else:
        raise HTTPException(
            status_code=400,
            detail="Author prefix must be a single letter, '0-9', or 'other'.",
        )

    items, total = await _fetch_items(
        db,
        extra_filters=[filt],
        order_by=CatalogItem.author.collate("und-x-icu").asc(),
        page=page,
        per_page=per_page,
    )
    return _respond_acq(
        request,
        feed_id=f"urn:l30:opds:by-author:{p}",
        title=f"Authors: {p.upper()}",
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------


@router.get("/formats")
async def opds_formats(request: Request) -> Response:
    entries = [
        {
            "id": f"urn:l30:opds:format:{t}",
            "title": t.capitalize(),
            "href": f"/api/v1/catalog/opds/formats/{t}",
            "type": OPDS_ACQ_TYPE,
        }
        for t in FORMAT_BUCKETS
    ]
    return _respond_nav(
        request,
        feed_id="urn:l30:opds:formats",
        title="Browse by format",
        entries=entries,
    )


@router.get("/formats/{item_type}")
async def opds_format_items(
    request: Request,
    item_type: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if item_type not in FORMAT_BUCKETS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown format. Supported: {', '.join(FORMAT_BUCKETS)}",
        )
    try:
        type_enum = ItemType(item_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Unknown format") from exc

    items, total = await _fetch_items(
        db,
        extra_filters=[CatalogItem.item_type == type_enum],
        order_by=CatalogItem.created_at.desc(),
        page=page,
        per_page=per_page,
    )
    return _respond_acq(
        request,
        feed_id=f"urn:l30:opds:format:{item_type}",
        title=f"Format: {item_type.capitalize()}",
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# Search (OpenSearch description + query)
# ---------------------------------------------------------------------------


@router.get("/search")
async def opds_search(
    request: Request,
    q: str | None = Query(None, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """OpenSearch description doc (no ``q``) or search results (with ``q``).

    OPDS clients discover the search URL template by hitting this endpoint
    without a query and parsing the returned OpenSearch description. They
    then substitute ``{searchTerms}`` and re-fetch.
    """
    if q is None:
        base = _base_url(request)
        template = (
            "/api/v1/catalog/opds/search?q={searchTerms}"
        )
        return Response(
            opensearch_description(
                base_url=base, search_url_template=template
            ),
            media_type=OPENSEARCH_DESC_TYPE,
        )

    # Reuse the canonical catalog search so OPDS results never drift from
    # the website's search results.
    result = await _execute_catalog_search(
        db=db,
        q=q,
        page=page,
        per_page=per_page,
        current_user=None,
        sort_by="relevance",
        sort_direction="desc",
    )
    # _execute_catalog_search returns model_dump'd dicts; we need raw rows
    # for the serializer. Re-fetch by id, preserving order, to keep
    # behavior identical (visibility, filtering) to the website search.
    item_ids = [row["id"] for row in result["items"]]
    items_by_id: dict[int, CatalogItem] = {}
    if item_ids:
        raw_query = (
            select(CatalogItem)
            .options(selectinload(CatalogItem.images))
            .where(CatalogItem.id.in_(item_ids))
        )
        for row in (await db.execute(raw_query)).scalars().all():
            items_by_id[row.id] = row
    items = [items_by_id[i] for i in item_ids if i in items_by_id]

    return _respond_acq(
        request,
        feed_id=f"urn:l30:opds:search:{q}",
        title=f"Search: {q}",
        items=items,
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
    )


# ---------------------------------------------------------------------------
# Legacy flat feed -- kept for back-compat with Palace etc.
# ---------------------------------------------------------------------------


def _escape_xml(text: Optional[str]) -> str:
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _legacy_cover_url(item: CatalogItem, base_url: str) -> Optional[str]:
    if item.images and len(item.images) > 0:
        img = item.images[0]
        if img.image_url:
            if img.image_url.startswith("http"):
                return img.image_url
            return f"{base_url}{img.image_url}"
    if item.cover_url:
        if item.cover_url.startswith("http"):
            return item.cover_url
        return f"{base_url}{item.cover_url}"
    return None


def _legacy_entry(item: CatalogItem, base_url: str) -> str:
    item_id = item.isbn or f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'l30-catalog-{item.id}')}"
    cover = _legacy_cover_url(item, base_url)
    download_url = f"{base_url}/api/v1/books/{item.id}/download"
    pub_date = f"{item.publication_year}-01-01" if item.publication_year else None
    out = f"  <entry>\n    <id>{_escape_xml(item_id)}</id>\n    <title>{_escape_xml(item.title)}</title>\n"
    if item.author:
        out += f'    <author><name>{_escape_xml(item.author)}</name></author>\n'
    if pub_date:
        out += f'    <published>{pub_date}</published>\n'
    updated = (item.updated_at if hasattr(item, "updated_at") and item.updated_at else datetime.utcnow()).isoformat()
    out += f'    <updated>{updated}Z</updated>\n'
    if item.description:
        out += f'    <summary>{_escape_xml(item.description[:500])}</summary>\n'
    if cover:
        out += f'    <link rel="cover" href="{_escape_xml(cover)}" type="image/jpeg"/>\n'
        out += f'    <link rel="thumbnail" href="{_escape_xml(cover)}" type="image/jpeg"/>\n'
    out += f'    <link rel="http://opds-spec.org/acquisition" href="{_escape_xml(download_url)}" type="application/epub+zip"/>\n'
    if item.subjects:
        for subject in item.subjects.split(","):
            subject = subject.strip()
            if subject:
                out += f'    <category term="{_escape_xml(subject)}" label="{_escape_xml(subject)}"/>\n'
    if item.publisher:
        out += f'    <dc:publisher>{_escape_xml(item.publisher)}</dc:publisher>\n'
    if item.isbn:
        out += f'    <dc:identifier>{_escape_xml(item.isbn)}</dc:identifier>\n'
    if item.page_count:
        out += f'    <dc:extent>{item.page_count}</dc:extent>\n'
    out += '  </entry>\n'
    return out


@router.get("/catalog.xml", response_class=Response)
async def get_opds_catalog(
    base_url: str = Query(
        default="https://l30.org", description="Base URL for links"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Legacy flat OPDS feed.

    Preserved exactly as-is so existing Palace Project registrations keep
    working. New consumers should hit ``/opds`` instead.
    """
    # Anonymous OPDS reader -- mirror ``_anonymous_visibility_filter`` (PUBLIC
    # only). The previous predicate let SENSITIVE items reach anonymous
    # Palace/Aldiko/etc. consumers, which no other path on this endpoint
    # family does.
    result = await db.execute(
        select(CatalogItem)
        .options(selectinload(CatalogItem.images))
        .where(
            CatalogItem.item_type == ItemType.book,
            CatalogItem.status == ItemStatus.available,
            CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
            CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC,
        )
        .order_by(CatalogItem.updated_at.desc())
    )
    catalog_items = result.scalars().all()

    feed_id = str(uuid.uuid4())
    feed_updated = datetime.utcnow().isoformat() + "Z"
    total = len(catalog_items)

    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:opds="http://opds-spec.org/2010/catalog" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f"  <id>urn:uuid:{feed_id}</id>\n"
        "  <title>L30 Library - OPDS Catalog</title>\n"
        "  <subtitle>L30 Library Digital Collection</subtitle>\n"
        f"  <updated>{feed_updated}</updated>\n\n"
        f'  <link rel="self" href="{_escape_xml(base_url)}/api/v1/catalog/opds/catalog.xml" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>\n'
        f'  <link rel="start" href="{_escape_xml(base_url)}/api/v1/catalog/opds/catalog.xml" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>\n\n'
        "  <author>\n"
        "    <name>L30 Library</name>\n"
        f"    <uri>{_escape_xml(base_url)}</uri>\n"
        "  </author>\n\n"
        f"  <dc:issued>{feed_updated}</dc:issued>\n"
        "  <dc:language>en</dc:language>\n\n"
        f"  <!-- Entries: {total} books -->\n"
    )
    for item in catalog_items:
        xml += _legacy_entry(item, base_url)
    xml += "</feed>\n"

    return Response(
        content=xml,
        media_type="application/atom+xml;profile=opds-catalog;kind=acquisition",
    )
