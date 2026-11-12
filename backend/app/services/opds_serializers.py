# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence

from lxml import etree

ATOM_NS = "http://www.w3.org/2005/Atom"
OPDS_NS = "http://opds-spec.org/2010/catalog"
DC_NS = "http://purl.org/dc/terms/"
OPENSEARCH_NS = "http://a9.com/-/spec/opensearch/1.1/"

NS_MAP = {
    None: ATOM_NS,
    "opds": OPDS_NS,
    "dcterms": DC_NS,
    "opensearch": OPENSEARCH_NS,
}

# Media types per OPDS spec.
ATOM_TYPE = "application/atom+xml"
OPDS_NAV_TYPE = "application/atom+xml;profile=opds-catalog;kind=navigation"
OPDS_ACQ_TYPE = "application/atom+xml;profile=opds-catalog;kind=acquisition"
OPDS_JSON_TYPE = "application/opds+json"
OPENSEARCH_DESC_TYPE = "application/opensearchdescription+xml"


def _iso(dt: datetime | None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat()


def _cover_links_for_item(item, base_url: str) -> list[tuple[str, str, str]]:
    has_cover = bool(
        getattr(item, "cover_url", None) or getattr(item, "images", None)
    )
    if not has_cover:
        return []
    href = f"{base_url}/api/v1/catalog/covers/{item.id}"
    return [
        ("http://opds-spec.org/image", href, "image/jpeg"),
        ("http://opds-spec.org/image/thumbnail", href, "image/jpeg"),
    ]


def _acq_links_for_item(item, base_url: str) -> list[tuple[str, str, str]]:
    borrow_href = f"{base_url}/api/v1/circulation/checkout?item_id={item.id}"
    return [
        (
            "http://opds-spec.org/acquisition/borrow",
            borrow_href,
            OPDS_ACQ_TYPE,
        ),
    ]


def _add_link(parent, rel: str, href: str, mime: str, **extra: str) -> None:
    attrs = {"rel": rel, "href": href, "type": mime}
    attrs.update({k: v for k, v in extra.items() if v is not None})
    etree.SubElement(parent, f"{{{ATOM_NS}}}link", **attrs)


def _add_entry_for_item(parent, item, base_url: str) -> None:
    entry = etree.SubElement(parent, f"{{{ATOM_NS}}}entry")
    etree.SubElement(entry, f"{{{ATOM_NS}}}id").text = f"urn:l30:item:{item.id}"
    etree.SubElement(entry, f"{{{ATOM_NS}}}title").text = item.title or ""
    if getattr(item, "author", None):
        author = etree.SubElement(entry, f"{{{ATOM_NS}}}author")
        etree.SubElement(author, f"{{{ATOM_NS}}}name").text = item.author
    etree.SubElement(entry, f"{{{ATOM_NS}}}updated").text = _iso(
        getattr(item, "updated_at", None)
    )
    if getattr(item, "description", None):
        summary = etree.SubElement(
            entry, f"{{{ATOM_NS}}}summary", type="text"
        )
        summary.text = item.description[:500]
    if getattr(item, "publisher", None):
        etree.SubElement(entry, f"{{{DC_NS}}}publisher").text = item.publisher
    if getattr(item, "isbn", None):
        etree.SubElement(entry, f"{{{DC_NS}}}identifier").text = item.isbn
    if getattr(item, "publication_year", None):
        etree.SubElement(entry, f"{{{ATOM_NS}}}published").text = (
            f"{item.publication_year}-01-01T00:00:00+00:00"
        )

    for rel, href, mime in _acq_links_for_item(item, base_url):
        _add_link(entry, rel, href, mime)
    for rel, href, mime in _cover_links_for_item(item, base_url):
        _add_link(entry, rel, href, mime)


def _serialize(feed) -> bytes:
    return etree.tostring(
        feed, xml_declaration=True, encoding="utf-8", pretty_print=True
    )


# ---------------------------------------------------------------------------
# OPDS 1.2 (Atom)
# ---------------------------------------------------------------------------


def to_opds1_acq(
    *,
    feed_id: str,
    title: str,
    self_url: str,
    items: Iterable,
    base_url: str,
    links: Sequence[dict] | None = None,
    total: int | None = None,
    page: int | None = None,
    per_page: int | None = None,
    updated: datetime | None = None,
) -> bytes:
    feed = etree.Element(f"{{{ATOM_NS}}}feed", nsmap=NS_MAP)
    etree.SubElement(feed, f"{{{ATOM_NS}}}id").text = feed_id
    etree.SubElement(feed, f"{{{ATOM_NS}}}title").text = title
    etree.SubElement(feed, f"{{{ATOM_NS}}}updated").text = _iso(updated)

    if total is not None:
        etree.SubElement(
            feed, f"{{{OPENSEARCH_NS}}}totalResults"
        ).text = str(total)
    if per_page is not None:
        etree.SubElement(
            feed, f"{{{OPENSEARCH_NS}}}itemsPerPage"
        ).text = str(per_page)
    if page is not None and per_page is not None:
        etree.SubElement(
            feed, f"{{{OPENSEARCH_NS}}}startIndex"
        ).text = str((page - 1) * per_page + 1)

    _add_link(feed, "self", self_url, OPDS_ACQ_TYPE)
    for link in links or []:
        _add_link(
            feed,
            link["rel"],
            link["href"],
            link.get("type", OPDS_ACQ_TYPE),
            title=link.get("title"),
        )

    for item in items:
        _add_entry_for_item(feed, item, base_url)

    return _serialize(feed)


def to_opds1_nav(
    *,
    feed_id: str,
    title: str,
    self_url: str,
    entries: Sequence[dict],
    base_url: str,
    links: Sequence[dict] | None = None,
    updated: datetime | None = None,
) -> bytes:
    feed = etree.Element(f"{{{ATOM_NS}}}feed", nsmap=NS_MAP)
    etree.SubElement(feed, f"{{{ATOM_NS}}}id").text = feed_id
    etree.SubElement(feed, f"{{{ATOM_NS}}}title").text = title
    etree.SubElement(feed, f"{{{ATOM_NS}}}updated").text = _iso(updated)

    _add_link(feed, "self", self_url, OPDS_NAV_TYPE)
    for link in links or []:
        _add_link(
            feed,
            link["rel"],
            link["href"],
            link.get("type", OPDS_NAV_TYPE),
            title=link.get("title"),
        )

    for ent in entries:
        entry = etree.SubElement(feed, f"{{{ATOM_NS}}}entry")
        etree.SubElement(entry, f"{{{ATOM_NS}}}id").text = ent["id"]
        etree.SubElement(entry, f"{{{ATOM_NS}}}title").text = ent["title"]
        etree.SubElement(entry, f"{{{ATOM_NS}}}updated").text = _iso(updated)
        if ent.get("summary"):
            summary = etree.SubElement(
                entry, f"{{{ATOM_NS}}}content", type="text"
            )
            summary.text = ent["summary"]
        href = ent["href"]
        if href.startswith("/"):
            href = f"{base_url}{href}"
        _add_link(
            entry,
            ent.get("rel", "subsection"),
            href,
            ent.get("type", OPDS_NAV_TYPE),
        )

    return _serialize(feed)


# ---------------------------------------------------------------------------
# OPDS 2.0 (JSON)
# ---------------------------------------------------------------------------


def _abs(url: str, base_url: str) -> str:
    return url if url.startswith("http") else f"{base_url}{url}"


def to_opds2_acq(
    *,
    feed_id: str,
    title: str,
    self_url: str,
    items: Iterable,
    base_url: str,
    links: Sequence[dict] | None = None,
    total: int | None = None,
    page: int | None = None,
    per_page: int | None = None,
) -> dict:
    pubs = []
    for item in items:
        images = [
            {"href": _abs(h, base_url), "type": m}
            for _r, h, m in _cover_links_for_item(item, base_url)[:1]
        ]
        acq_links = [
            {"rel": r, "href": _abs(h, base_url), "type": "application/json"}
            for r, h, _m in _acq_links_for_item(item, base_url)
        ]
        pub_metadata: dict = {
            "@type": "http://schema.org/Book",
            "title": item.title or "",
            "identifier": f"urn:l30:item:{item.id}",
        }
        if getattr(item, "author", None):
            pub_metadata["author"] = item.author
        if getattr(item, "description", None):
            pub_metadata["description"] = item.description[:500]
        if getattr(item, "publisher", None):
            pub_metadata["publisher"] = item.publisher
        if getattr(item, "publication_year", None):
            pub_metadata["published"] = f"{item.publication_year}-01-01"
        pubs.append(
            {"metadata": pub_metadata, "links": acq_links, "images": images}
        )

    metadata: dict = {"title": title, "identifier": feed_id}
    if total is not None:
        metadata["numberOfItems"] = total
    if per_page is not None:
        metadata["itemsPerPage"] = per_page
    if page is not None:
        metadata["currentPage"] = page

    return {
        "metadata": metadata,
        "links": [{"rel": "self", "href": self_url, "type": OPDS_JSON_TYPE}]
        + [
            {
                "rel": link["rel"],
                "href": _abs(link["href"], base_url),
                "type": link.get("type", OPDS_JSON_TYPE),
            }
            for link in (links or [])
        ],
        "publications": pubs,
    }


def to_opds2_nav(
    *,
    feed_id: str,
    title: str,
    self_url: str,
    entries: Sequence[dict],
    base_url: str,
    links: Sequence[dict] | None = None,
) -> dict:
    return {
        "metadata": {"title": title, "identifier": feed_id},
        "links": [{"rel": "self", "href": self_url, "type": OPDS_JSON_TYPE}]
        + [
            {
                "rel": link["rel"],
                "href": _abs(link["href"], base_url),
                "type": link.get("type", OPDS_JSON_TYPE),
            }
            for link in (links or [])
        ],
        "navigation": [
            {
                "title": ent["title"],
                "href": _abs(ent["href"], base_url),
                "type": ent.get("type", OPDS_JSON_TYPE),
                **(
                    {"description": ent["summary"]}
                    if ent.get("summary")
                    else {}
                ),
            }
            for ent in entries
        ],
    }


# ---------------------------------------------------------------------------
# OpenSearch description document
# ---------------------------------------------------------------------------


def opensearch_description(
    *, base_url: str, search_url_template: str
) -> bytes:
    OS = OPENSEARCH_NS
    desc = etree.Element(
        f"{{{OS}}}OpenSearchDescription", nsmap={None: OS}
    )
    etree.SubElement(desc, f"{{{OS}}}ShortName").text = "L30 catalog"
    etree.SubElement(desc, f"{{{OS}}}Description").text = (
        "Search the L30 library catalog."
    )
    etree.SubElement(desc, f"{{{OS}}}InputEncoding").text = "UTF-8"
    etree.SubElement(
        desc,
        f"{{{OS}}}Url",
        type=OPDS_ACQ_TYPE,
        template=_abs(search_url_template, base_url),
    )
    etree.SubElement(
        desc,
        f"{{{OS}}}Url",
        type=OPDS_JSON_TYPE,
        template=_abs(search_url_template, base_url),
    )
    return _serialize(desc)
