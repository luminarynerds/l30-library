# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
BIBFRAME-based public catalog API

Provides search and browsing functionality using the BIBFRAME data model.
This replaces the legacy catalog_items table for public-facing catalog operations.
"""
from app.core.logging import get_logger
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

from ...core.cache import (
    get_cached,
    make_cache_key,
    set_cached,
)
from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...models.bibframe import (
    BibframeWork,
    BibframeInstance,
    BibframeItem,
    BibframeContributor,
    BibframeSubject,
    work_contributors,
    work_subjects,
)

router = APIRouter(prefix="/bibframe-catalog", tags=["bibframe-catalog"])


# ==================== Endpoints ====================

@router.get("/search")
@limiter.limit("60/minute")
async def search_bibframe_catalog(
    request: Request,
    q: Optional[str] = Query(None, description="Full-text search query"),
    title: Optional[str] = Query(None, description="Filter by title"),
    author: Optional[str] = Query(None, description="Filter by author/creator"),
    subject: Optional[str] = Query(None, description="Filter by subject/genre"),
    genre: Optional[str] = Query(None, description="Filter by genre form"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    publication_year: Optional[int] = Query(None, description="Filter by exact publication year"),
    year_min: Optional[int] = Query(None, description="Minimum publication year"),
    year_max: Optional[int] = Query(None, description="Maximum publication year"),
    sort_by: Optional[str] = Query("relevance", description="Sort by: relevance, title, author, year"),
    sort_direction: Optional[str] = Query("desc", description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Search BIBFRAME catalog with full-text search and filtering.
    Returns works with their instances bundled together.
    """
    # Build cache key
    cache_key = make_cache_key(
        "bibframe:search",
        q=q,
        title=title,
        author=author,
        subject=subject,
        genre=genre,
        language=language,
        publication_year=publication_year,
        year_min=year_min,
        year_max=year_max,
        sort_by=sort_by,
        sort_direction=sort_direction,
        page=page,
        per_page=per_page,
    )

    # Check cache
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result

    # Build base query
    query = select(BibframeWork).distinct()
    count_query = select(func.count(BibframeWork.id.distinct()))

    # Apply filters
    if q:
        # Full-text search on multiple fields
        q_escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search = f"%{q_escaped}%"
        search_filter = or_(
            BibframeWork.title.ilike(search),
            BibframeWork.summary.ilike(search),
            BibframeWork.genre_form.ilike(search),
            BibframeWork.table_of_contents.ilike(search),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if title:
        title_escaped = title.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(BibframeWork.title.ilike(f"%{title_escaped}%"))
        count_query = count_query.where(BibframeWork.title.ilike(f"%{title_escaped}%"))

    if author:
        author_escaped = author.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        author_pattern = f"%{author_escaped}%"
        author_subquery = (
            select(work_contributors.c.work_id)
            .join(
                BibframeContributor,
                BibframeContributor.id == work_contributors.c.contributor_id,
            )
            .where(
                or_(
                    BibframeContributor.name.ilike(author_pattern),
                    BibframeContributor.name_inverted.ilike(author_pattern),
                )
            )
        )
        query = query.where(BibframeWork.id.in_(author_subquery))
        count_query = count_query.where(BibframeWork.id.in_(author_subquery))

    if subject:
        subject_escaped = subject.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        subject_pattern = f"%{subject_escaped}%"
        subject_subquery = (
            select(work_subjects.c.work_id)
            .join(
                BibframeSubject,
                BibframeSubject.id == work_subjects.c.subject_id,
            )
            .where(
                or_(
                    BibframeSubject.label.ilike(subject_pattern),
                    BibframeSubject.label_normalized.ilike(subject_pattern),
                )
            )
        )
        query = query.where(BibframeWork.id.in_(subject_subquery))
        count_query = count_query.where(BibframeWork.id.in_(subject_subquery))

    if genre:
        genre_escaped = genre.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(BibframeWork.genre_form.ilike(f"%{genre_escaped}%"))
        count_query = count_query.where(BibframeWork.genre_form.ilike(f"%{genre_escaped}%"))

    if language:
        query = query.where(BibframeWork.language == language)
        count_query = count_query.where(BibframeWork.language == language)

    if publication_year is not None:
        # Try to match the year in origin_date string
        query = query.where(BibframeWork.origin_date.ilike(f"%{publication_year}%"))
        count_query = count_query.where(BibframeWork.origin_date.ilike(f"%{publication_year}%"))

    if year_min is not None:
        # Extract year from origin_date for comparison
        query = query.where(BibframeWork.origin_date >= str(year_min))
        count_query = count_query.where(BibframeWork.origin_date >= str(year_min))

    if year_max is not None:
        query = query.where(BibframeWork.origin_date <= str(year_max))
        count_query = count_query.where(BibframeWork.origin_date <= str(year_max))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = BibframeWork.title
    if sort_by == "title":
        sort_column = BibframeWork.title
    elif sort_by == "author":
        sort_column = BibframeWork.title  # Simplified - would need contributor join
    elif sort_by == "year":
        sort_column = BibframeWork.origin_date
    # relevance defaults to id order

    if sort_direction == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    works = result.scalars().all()

    # Build response with instance/item counts
    items = []
    for work in works:
        # Get instance count
        instance_count_result = await db.execute(
            select(func.count(BibframeInstance.id)).where(
                BibframeInstance.work_id == work.id
            )
        )
        instance_count = instance_count_result.scalar() or 0

        # Get item count (items are linked through instances)
        item_count_result = await db.execute(
            select(func.count(BibframeItem.id)).where(
                BibframeItem.instance_id.in_(
                    select(BibframeInstance.id).where(BibframeInstance.work_id == work.id)
                )
            )
        )
        item_count = item_count_result.scalar() or 0

        items.append({
            "id": work.id,
            "title": work.title,
            "subtitle": work.subtitle,
            "summary": work.summary,
            "genre_form": work.genre_form,
            "language": work.language,
            "origin_date": work.origin_date,
            "dewey_classification": work.dewey_classification,
            "instance_count": instance_count,
            "item_count": item_count,
        })

    pages = (total + per_page - 1) // per_page
    response = {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }

    # Cache the result
    await set_cached(cache_key, response, ttl_seconds=3600)  # Cache for 1 hour

    return response


@router.get("/")
@limiter.limit("120/minute")
async def list_bibframe_works(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all BIBFRAME works with pagination"""
    # Cache key
    cache_key = make_cache_key("bibframe:list", page=page, per_page=per_page)
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result

    # Get total count
    total_result = await db.execute(select(func.count(BibframeWork.id)))
    total = total_result.scalar() or 0

    # Get works
    offset = (page - 1) * per_page
    query = select(BibframeWork).order_by(BibframeWork.title).offset(offset).limit(per_page)
    result = await db.execute(query)
    works = result.scalars().all()

    # Build response
    items = []
    for work in works:
        instance_count_result = await db.execute(
            select(func.count(BibframeInstance.id)).where(BibframeInstance.work_id == work.id)
        )
        instance_count = instance_count_result.scalar() or 0

        items.append({
            "id": work.id,
            "title": work.title,
            "subtitle": work.subtitle,
            "summary": work.summary,
            "genre_form": work.genre_form,
            "language": work.language,
            "origin_date": work.origin_date,
            "dewey_classification": work.dewey_classification,
            "instance_count": instance_count,
        })

    pages = (total + per_page - 1) // per_page
    response = {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }

    # Cache result
    await set_cached(cache_key, response, ttl_seconds=3600)

    return response


@router.get("/{work_id}")
async def get_bibframe_work(
    work_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single work with all its instances and items"""
    # Try cache first
    cache_key = make_cache_key("bibframe:work", work_id=work_id)
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result

    # Get work
    work = await get_or_404(db, BibframeWork, work_id, "Work not found")

    # Get instances
    instances_result = await db.execute(
        select(BibframeInstance).where(BibframeInstance.work_id == work_id)
    )
    instances = instances_result.scalars().all()

    # Get items for each instance
    instance_data = []
    for instance in instances:
        items_result = await db.execute(
            select(BibframeItem).where(BibframeItem.instance_id == instance.id)
        )
        items = items_result.scalars().all()

        instance_data.append({
            "id": instance.id,
            "title": instance.title,
            "instance_type": instance.instance_type,
            "carrier_type": instance.carrier_type,
            "media_type": instance.media_type,
            "publisher": instance.publisher,
            "publication_date": instance.publication_date,
            "isbn_13": instance.isbn_13,
            "isbn_10": instance.isbn_10,
            "items": [
                {
                    "id": item.id,
                    "barcode": item.barcode,
                    "call_number": item.call_number,
                    "library_branch": item.library_branch,
                    "circulation_status": item.circulation_status,
                }
                for item in items
            ],
        })

    response = {
        "id": work.id,
        "title": work.title,
        "subtitle": work.subtitle,
        "summary": work.summary,
        "genre_form": work.genre_form,
        "language": work.language,
        "origin_date": work.origin_date,
        "dewey_classification": work.dewey_classification,
        "lc_classification": work.lc_classification,
        "series_title": work.series_title,
        "series_number": work.series_number,
        "instances": instance_data,
    }

    # Cache result
    await set_cached(cache_key, response, ttl_seconds=3600)

    return response


@router.get("/{work_id}/linked-data")
async def get_bibframe_linked_data(
    work_id: int,
    format: Literal["jsonld", "schema-org"] = Query(
        "jsonld", description="Output format: jsonld, schema-org"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get linked data representation of a BIBFRAME work.

    Returns JSON-LD following BIBFRAME 2.0 ontology or Schema.org mapping.
    Suitable for embedding in HTML pages or serving via content negotiation.
    """
    work = await get_or_404(db, BibframeWork, work_id, "Work not found")

    # Get instances
    instances_result = await db.execute(
        select(BibframeInstance).where(BibframeInstance.work_id == work_id)
    )
    instances = list(instances_result.scalars().all())

    # Get contributors
    contributors_result = await db.execute(
        select(BibframeContributor).join(work_contributors, BibframeContributor.id == work_contributors.c.contributor_id).where(work_contributors.c.work_id == work_id)
    )
    contributors = list(contributors_result.scalars().all())

    # Get subjects
    subjects_result = await db.execute(
        select(BibframeSubject).join(work_subjects, BibframeSubject.id == work_subjects.c.subject_id).where(work_subjects.c.work_id == work_id)
    )
    subjects = list(subjects_result.scalars().all())

    if format == "schema-org":
        jsonld = _build_schema_org_jsonld(work, instances, contributors, subjects)
    else:
        jsonld = _build_bibframe_jsonld(work, instances, contributors, subjects)

    return JSONResponse(
        content=jsonld,
        media_type="application/ld+json",
    )


def _build_bibframe_jsonld(work, instances, contributors, subjects) -> dict:
    bf = "http://id.loc.gov/ontologies/bibframe/"

    jsonld = {
        "@context": {
            "bf": bf,
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        },
        "@type": "bf:Work",
        "@id": f"/api/v1/bibframe-catalog/{work.id}",
        "bf:title": {"@type": "bf:Title", "rdfs:label": work.title},
    }

    if work.subtitle:
        jsonld["bf:title"]["bf:subtitle"] = work.subtitle

    if work.summary:
        jsonld["bf:summary"] = {"@type": "bf:Summary", "rdfs:label": work.summary}

    if work.language:
        jsonld["bf:language"] = {"@id": f"http://id.loc.gov/vocabulary/languages/{work.language}"}

    if work.origin_date:
        jsonld["bf:originDate"] = work.origin_date

    classifications = []
    if work.dewey_classification:
        classifications.append({
            "@type": "bf:ClassificationDdc",
            "bf:classificationPortion": work.dewey_classification,
        })
    if work.lc_classification:
        classifications.append({
            "@type": "bf:ClassificationLcc",
            "bf:classificationPortion": work.lc_classification,
        })
    if classifications:
        jsonld["bf:classification"] = classifications

    if contributors:
        jsonld["bf:contribution"] = [
            {
                "@type": "bf:Contribution",
                "bf:agent": {"@type": "bf:Person", "rdfs:label": c.name},
                "bf:role": {"@id": f"http://id.loc.gov/vocabulary/relators/{c.contributor_type or 'aut'}"},
            }
            for c in contributors
        ]

    if subjects:
        jsonld["bf:subject"] = [
            {"@type": "bf:Topic", "rdfs:label": s.label}
            for s in subjects
        ]

    if instances:
        jsonld["bf:hasInstance"] = [
            {
                "@type": "bf:Instance",
                "@id": f"/api/v1/bibframe-catalog/{work.id}/instances/{inst.id}",
                "bf:title": {"rdfs:label": inst.title or work.title},
                **({"bf:identifiedBy": {"@type": "bf:Isbn", "rdf:value": inst.isbn_13}} if inst.isbn_13 else {}),
                **({"bf:provisionActivity": {"bf:agent": {"rdfs:label": inst.publisher}}} if inst.publisher else {}),
            }
            for inst in instances
        ]

    return jsonld


def _build_schema_org_jsonld(work, instances, contributors, subjects) -> dict:
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": work.title,
    }

    if work.summary:
        jsonld["description"] = work.summary

    if work.language:
        jsonld["inLanguage"] = work.language

    if work.origin_date:
        jsonld["datePublished"] = work.origin_date

    if contributors:
        authors = [{"@type": "Person", "name": c.name} for c in contributors]
        jsonld["author"] = authors if len(authors) > 1 else authors[0]

    if subjects:
        jsonld["about"] = [{"@type": "Thing", "name": s.label} for s in subjects]

    isbns = [inst.isbn_13 for inst in instances if inst.isbn_13]
    if isbns:
        jsonld["isbn"] = isbns[0] if len(isbns) == 1 else isbns

    publishers = [inst.publisher for inst in instances if inst.publisher]
    if publishers:
        jsonld["publisher"] = {"@type": "Organization", "name": publishers[0]}

    if work.dewey_classification:
        jsonld["additionalProperty"] = {
            "@type": "PropertyValue",
            "name": "Dewey Decimal Classification",
            "value": work.dewey_classification,
        }

    return jsonld
