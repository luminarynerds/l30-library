# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Linked Data API Endpoints for BIBFRAME and RDF

This module provides REST API endpoints for:
- BIBFRAME Work, Instance, Item CRUD operations
- RDF serialization (JSON-LD, Turtle)
- Content negotiation for linked data clients
- MARC to BIBFRAME conversion
- Library of Congress BIBFRAME import
- Schema.org markup generation
- Authority linking (VIAF, LCNAF, Wikidata)

Content Negotiation:
- Accept: application/ld+json → JSON-LD
- Accept: text/turtle → Turtle
- Accept: application/json → Standard JSON API response

URIs follow linked data principles:
- /works/{id} → BIBFRAME Work
- /instances/{id} → BIBFRAME Instance
- /items/{id} → BIBFRAME Item
- /contributors/{id} → Contributor/Agent
- /subjects/{id} → Subject heading
"""

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from .auth import get_current_user
from .dependencies import require_staff
from ...core.rate_limit import limiter
from ...models.bibframe import (
    AuthorityLink,
    AuthoritySource,
    BibframeContributor,
    BibframeInstance,
    BibframeItem,
    BibframeSubject,
    BibframeWork,
    work_contributors,
    work_subjects,
)
from ...models.catalog import CatalogItem
from ...models.user import User
from ...schemas.bibframe import (
    AuthorityLinkCreate,
    AuthorityLinkResponse,
    BibframeExportRequest,
    ContributorCreate,
    ContributorResponse,
    ContributorUpdate,
    InstanceCreate,
    InstanceResponse,
    InstanceSearchParams,
    InstanceUpdate,
    ItemCreate,
    ItemResponse,
    ItemSearchParams,
    ItemUpdate,
    LocImportRequest,
    LocSearchRequest,
    LocSearchResponse,
    MarcToBibframeRequest,
    MarcToBibframeResponse,
    SubjectCreate,
    SubjectResponse,
    WorkCreate,
    WorkResponse,
    WorkSearchParams,
    WorkUpdate,
)
from ...schemas.linked_data import (
    InstanceListItem,
    InstancesListResponse,
    ItemListItem,
    ItemsListResponse,
    LocImportInstanceInfo,
    LocImportResponse,
    LocImportWorkInfo,
    WorkListContributor,
    WorkListItem,
    WorkListSubject,
    WorksListResponse,
)
from ...services.bibframe_rdf_service import bibframe_rdf_service
from ...services.loc_bibframe_service import loc_bibframe_service
from ...services.marc_to_bibframe_service import marc_to_bibframe_service
from ...services.schema_org_service import schema_org_service
from .auth import get_current_user

router = APIRouter(prefix="/linked-data", tags=["Linked Data"])


# ============================================================================
# Content Negotiation Helpers
# ============================================================================


def get_preferred_format(accept: Optional[str] = None) -> str:
    if not accept:
        return "json"

    accept_lower = accept.lower()

    if "application/ld+json" in accept_lower:
        return "jsonld"
    elif "text/turtle" in accept_lower:
        return "turtle"
    elif "application/n-triples" in accept_lower:
        return "ntriples"
    elif "application/rdf+xml" in accept_lower:
        return "rdfxml"
    else:
        return "json"


def create_linked_data_response(
    data: Any,
    format: str,
    status_code: int = 200,
) -> Response:
    if format == "jsonld":
        return JSONResponse(
            content=data,
            status_code=status_code,
            media_type="application/ld+json",
            headers={"Content-Type": "application/ld+json; charset=utf-8"},
        )
    elif format == "turtle":
        return Response(
            content=data if isinstance(data, str) else json.dumps(data),
            status_code=status_code,
            media_type="text/turtle",
            headers={"Content-Type": "text/turtle; charset=utf-8"},
        )
    else:
        return JSONResponse(content=data, status_code=status_code)


# ============================================================================
# Work Endpoints
# ============================================================================


@router.get("/stats")
@limiter.limit("60/minute")
async def get_linked_data_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Entity counts for the staff Linked Data dashboard."""

    async def _count(model) -> int:
        return await db.scalar(select(func.count()).select_from(model)) or 0

    return {
        "total_works": await _count(BibframeWork),
        "total_instances": await _count(BibframeInstance),
        "total_items": await _count(BibframeItem),
        "total_contributors": await _count(BibframeContributor),
        "total_subjects": await _count(BibframeSubject),
        "authority_links": await _count(AuthorityLink),
    }


@router.get("/works", response_model=WorksListResponse)
@limiter.limit("60/minute")
async def list_works(
    request: Request,
    q: Optional[str] = Query(None, max_length=500),
    title: Optional[str] = Query(None, max_length=500),
    contributor: Optional[str] = Query(None, max_length=255),
    subject: Optional[str] = Query(None, max_length=255),
    language: Optional[str] = Query(None, max_length=10),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    include: Optional[str] = Query("full", pattern="^(minimal|full)$"),
    accept: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List and search BIBFRAME Works.

    Supports content negotiation:
    - Accept: application/ld+json → JSON-LD graph
    - Accept: application/json → Standard paginated response

    Query parameters:
    - include: 'minimal' skips relationship loading for faster list views,
               'full' includes all relationships (default)

    Performance optimization: Uses selectinload to prevent N+1 queries when
    include='full'. For 100 works, prevents ~200 additional queries.
    """
    # Build query with conditional relationship loading
    # Minimal mode: skip contributors/subjects to reduce query count
    if include == "minimal":
        query = select(BibframeWork)
    else:
        # Full mode: eager load all relationships in single query
        query = select(BibframeWork).options(
            selectinload(BibframeWork.contributors),
            selectinload(BibframeWork.subjects),
        )

    # Apply filters
    if q:
        safe_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                BibframeWork.title.ilike(f"%{safe_q}%"),
                BibframeWork.summary.ilike(f"%{safe_q}%"),
            )
        )
    if title:
        safe_title = title.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(BibframeWork.title.ilike(f"%{safe_title}%"))
    if language:
        query = query.where(BibframeWork.language == language)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    works = result.scalars().all()

    format = get_preferred_format(accept)

    if format == "jsonld":
        # Return JSON-LD graph
        jsonld_works = [bibframe_rdf_service.work_to_jsonld(w, embed_context=False) for w in works]
        return create_linked_data_response(
            {
                "@context": bibframe_rdf_service.JSONLD_CONTEXT,
                "@graph": jsonld_works,
            },
            format,
        )

    # Standard JSON response
    return WorksListResponse(
        items=[
            WorkListItem(
                id=w.id,
                uri=bibframe_rdf_service.get_work_uri(w),
                title=w.title,
                subtitle=w.subtitle,
                work_type=str(w.work_type) if w.work_type else None,
                language=w.language,
                contributors=[WorkListContributor(id=c.id, name=c.name) for c in w.contributors],
                subjects=[WorkListSubject(id=s.id, label=s.label) for s in w.subjects],
                created_at=None,
            )
            for w in works
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total else 0,
    )


@router.get("/works/{work_id}")
@limiter.limit("120/minute")
async def get_work(
    request: Request,
    work_id: int,
    include_instances: bool = Query(True),
    include_authorities: bool = Query(True),
    accept: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single BIBFRAME Work with content negotiation.

    Supports:
    - Accept: application/ld+json → Full JSON-LD representation
    - Accept: text/turtle → Turtle RDF
    - Accept: application/json → Standard JSON

    Performance optimization: Uses selectinload to prevent N+1 queries.
    Loads all related data in single statement:
    - Contributors and their authority links
    - Subjects and their authority links
    - Authority links for the work itself
    - Instances with their own contributors (if requested)
    """
    query = (
        select(BibframeWork)
        .where(BibframeWork.id == work_id)
        .options(
            # Load contributors and their relationships
            selectinload(BibframeWork.contributors).selectinload(
                BibframeContributor.authority_links
            ),
            # Load subjects and their relationships
            selectinload(BibframeWork.subjects),
            # Load work authority links
            selectinload(BibframeWork.authority_links),
        )
    )

    if include_instances:
        # Load instances with their contributors
        query = query.options(
            selectinload(BibframeWork.instances).selectinload(BibframeInstance.contributors)
        )

    result = await db.execute(query)
    work = result.scalar_one_or_none()

    if not work:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work not found")

    format = get_preferred_format(accept)

    if format == "jsonld":
        jsonld = bibframe_rdf_service.work_to_jsonld(
            work,
            include_instances=include_instances,
            include_authorities=include_authorities,
        )
        return create_linked_data_response(jsonld, format)

    elif format == "turtle":
        turtle = bibframe_rdf_service.work_to_turtle(
            work,
            include_instances=include_instances,
            include_authorities=include_authorities,
        )
        return create_linked_data_response(turtle, format)

    # Standard JSON
    return {
        "id": work.id,
        "uri": bibframe_rdf_service.get_work_uri(work),
        "title": work.title,
        "subtitle": work.subtitle,
        "title_sort": work.title_sort,
        "work_type": str(work.work_type) if work.work_type else None,
        "language": work.language,
        "original_language": work.original_language,
        "summary": work.summary,
        "table_of_contents": work.table_of_contents,
        "genre_form": json.loads(work.genre_form) if work.genre_form else None,
        "intended_audience": work.intended_audience,
        "dewey_classification": work.dewey_classification,
        "lc_classification": work.lc_classification,
        "series_title": work.series_title,
        "series_number": work.series_number,
        "contributors": [
            {"id": c.id, "name": c.name, "type": c.contributor_type, "viaf_id": c.viaf_id}
            for c in work.contributors
        ],
        "subjects": [
            {"id": s.id, "label": s.label, "type": s.subject_type, "lcsh_id": s.lcsh_id}
            for s in work.subjects
        ],
        "instances": [
            {"id": i.id, "title": i.title, "isbn": i.isbn_13, "publisher": i.publisher}
            for i in (work.instances or [])
        ]
        if include_instances
        else None,
        "authority_links": [
            {"source": l.source, "authority_id": l.authority_id, "uri": l.authority_uri}
            for l in work.authority_links
        ]
        if include_authorities
        else None,
        "source": work.source,
        "created_at": None,
        "updated_at": None,
    }


@router.post("/works", response_model=WorkResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_work(
    request: Request,
    work_data: WorkCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new BIBFRAME Work."""
    work = BibframeWork(
        uri=work_data.uri,
        title=work_data.title,
        title_sort=work_data.title_sort or work_data.title.lower(),
        subtitle=work_data.subtitle,
        title_variant=json.dumps(work_data.title_variant) if work_data.title_variant else None,
        work_type=work_data.work_type,
        language=work_data.language,
        original_language=work_data.original_language,
        summary=work_data.summary,
        table_of_contents=work_data.table_of_contents,
        genre_form=json.dumps(work_data.genre_form) if work_data.genre_form else None,
        intended_audience=work_data.intended_audience,
        dewey_classification=work_data.dewey_classification,
        lc_classification=work_data.lc_classification,
        series_title=work_data.series_title,
        series_number=work_data.series_number,
        origin_date=work_data.origin_date,
        origin_place=work_data.origin_place,
        notes=json.dumps(work_data.notes) if work_data.notes else None,
        source=work_data.source,
        source_record_id=work_data.source_record_id,
        catalog_item_id=work_data.catalog_item_id,
        linked_data=work_data.linked_data,
    )

    db.add(work)
    await db.commit()
    await db.refresh(work)

    # Link contributors if provided
    if work_data.contributor_ids:
        for contrib_id in work_data.contributor_ids:
            await db.execute(
                work_contributors.insert().values(work_id=work.id, contributor_id=contrib_id)
            )
        await db.commit()

    # Link subjects if provided
    if work_data.subject_ids:
        for subj_id in work_data.subject_ids:
            await db.execute(work_subjects.insert().values(work_id=work.id, subject_id=subj_id))
        await db.commit()

    return WorkResponse.model_validate(work)


@router.patch("/works/{work_id}", response_model=WorkResponse)
@limiter.limit("30/minute")
async def update_work(
    request: Request,
    work_id: int,
    work_data: WorkUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a BIBFRAME Work."""
    work = await get_or_404(db, BibframeWork, work_id, "Work not found")

    update_data = work_data.model_dump(exclude_unset=True)

    # Handle JSON fields
    if "title_variant" in update_data and update_data["title_variant"] is not None:
        update_data["title_variant"] = json.dumps(update_data["title_variant"])
    if "genre_form" in update_data and update_data["genre_form"] is not None:
        update_data["genre_form"] = json.dumps(update_data["genre_form"])
    if "notes" in update_data and update_data["notes"] is not None:
        update_data["notes"] = json.dumps(update_data["notes"])

    for field, value in update_data.items():
        setattr(work, field, value)

    await db.commit()
    await db.refresh(work)

    return WorkResponse.model_validate(work)


@router.delete("/works/{work_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_work(
    request: Request,
    work_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a BIBFRAME Work and all related data."""
    work = await get_or_404(db, BibframeWork, work_id, "Work not found")

    await db.delete(work)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Instance Endpoints
# ============================================================================


@router.get("/instances", response_model=InstancesListResponse)
@limiter.limit("60/minute")
async def list_instances(
    request: Request,
    q: Optional[str] = Query(None, max_length=500),
    isbn: Optional[str] = Query(None, max_length=17),
    publisher: Optional[str] = Query(None, max_length=255),
    year_from: Optional[int] = Query(None, ge=1),
    year_to: Optional[int] = Query(None, le=9999),
    work_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    accept: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """List and search BIBFRAME Instances."""
    query = select(BibframeInstance).options(
        selectinload(BibframeInstance.work),
        selectinload(BibframeInstance.contributors),
    )

    if q:
        safe_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(BibframeInstance.title.ilike(f"%{safe_q}%"))
    if isbn:
        safe_isbn = isbn.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                BibframeInstance.isbn_13.ilike(f"%{safe_isbn}%"),
                BibframeInstance.isbn_10.ilike(f"%{safe_isbn}%"),
            )
        )
    if publisher:
        safe_publisher = publisher.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(BibframeInstance.publisher.ilike(f"%{safe_publisher}%"))
    if year_from:
        query = query.where(BibframeInstance.publication_year >= year_from)
    if year_to:
        query = query.where(BibframeInstance.publication_year <= year_to)
    if work_id:
        query = query.where(BibframeInstance.work_id == work_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    instances = result.scalars().all()

    format = get_preferred_format(accept)

    if format == "jsonld":
        jsonld_instances = [
            bibframe_rdf_service.instance_to_jsonld(i, embed_context=False) for i in instances
        ]
        return create_linked_data_response(
            {
                "@context": bibframe_rdf_service.JSONLD_CONTEXT,
                "@graph": jsonld_instances,
            },
            format,
        )

    return InstancesListResponse(
        items=[
            InstanceListItem(
                id=i.id,
                uri=bibframe_rdf_service.get_instance_uri(i),
                title=i.title,
                isbn_13=i.isbn_13,
                publisher=i.publisher,
                publication_year=i.publication_year,
                work_id=i.work_id,
                work_title=i.work.title if i.work else None,
            )
            for i in instances
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total else 0,
    )


@router.get("/instances/{instance_id}")
@limiter.limit("120/minute")
async def get_instance(
    request: Request,
    instance_id: int,
    include_work: bool = Query(True),
    include_items: bool = Query(True),
    accept: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Get a single BIBFRAME Instance with content negotiation."""
    query = (
        select(BibframeInstance)
        .where(BibframeInstance.id == instance_id)
        .options(
            selectinload(BibframeInstance.contributors),
            selectinload(BibframeInstance.authority_links),
        )
    )

    if include_work:
        query = query.options(selectinload(BibframeInstance.work))
    if include_items:
        query = query.options(selectinload(BibframeInstance.items))

    result = await db.execute(query)
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    format = get_preferred_format(accept)

    if format == "jsonld":
        jsonld = bibframe_rdf_service.instance_to_jsonld(
            instance,
            include_work=include_work,
            include_items=include_items,
        )
        return create_linked_data_response(jsonld, format)

    elif format == "turtle":
        turtle = bibframe_rdf_service.instance_to_turtle(
            instance,
            include_work=include_work,
            include_items=include_items,
        )
        return create_linked_data_response(turtle, format)

    return {
        "id": instance.id,
        "uri": bibframe_rdf_service.get_instance_uri(instance),
        "work_id": instance.work_id,
        "title": instance.title,
        "subtitle": instance.subtitle,
        "instance_type": str(instance.instance_type) if instance.instance_type else None,
        "carrier_type": str(instance.carrier_type) if instance.carrier_type else None,
        "media_type": str(instance.media_type) if instance.media_type else None,
        "isbn_10": instance.isbn_10,
        "isbn_13": instance.isbn_13,
        "lccn": instance.lccn,
        "oclc_number": instance.oclc_number,
        "publisher": instance.publisher,
        "publisher_place": instance.publisher_place,
        "publication_year": instance.publication_year,
        "edition": instance.edition,
        "extent": instance.extent,
        "page_count": instance.page_count,
        "cover_url": instance.cover_url,
        "work": {
            "id": instance.work.id,
            "title": instance.work.title,
        }
        if instance.work
        else None,
        "items": [
            {"id": it.id, "barcode": it.barcode, "status": it.circulation_status}
            for it in (instance.items or [])
        ]
        if include_items
        else None,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
    }


@router.post("/instances", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_instance(
    request: Request,
    instance_data: InstanceCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new BIBFRAME Instance."""
    # Verify work exists
    work_result = await db.execute(
        select(BibframeWork).where(BibframeWork.id == instance_data.work_id)
    )
    if not work_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Work not found")

    instance = BibframeInstance(
        work_id=instance_data.work_id,
        uri=instance_data.uri,
        title=instance_data.title,
        subtitle=instance_data.subtitle,
        title_statement=instance_data.title_statement,
        instance_type=instance_data.instance_type,
        carrier_type=instance_data.carrier_type,
        media_type=instance_data.media_type,
        isbn_10=instance_data.isbn_10,
        isbn_13=instance_data.isbn_13,
        issn=instance_data.issn,
        lccn=instance_data.lccn,
        oclc_number=instance_data.oclc_number,
        publisher=instance_data.publisher,
        publisher_place=instance_data.publisher_place,
        publication_date=instance_data.publication_date,
        publication_year=instance_data.publication_year,
        copyright_date=instance_data.copyright_date,
        edition=instance_data.edition,
        edition_number=instance_data.edition_number,
        extent=instance_data.extent,
        dimensions=instance_data.dimensions,
        page_count=instance_data.page_count,
        digital_format=instance_data.digital_format,
        file_size=instance_data.file_size,
        access_url=instance_data.access_url,
        cover_url=instance_data.cover_url,
        thumbnail_url=instance_data.thumbnail_url,
        notes=json.dumps(instance_data.notes) if instance_data.notes else None,
        source=instance_data.source,
        source_record_id=instance_data.source_record_id,
        marc_record=instance_data.marc_record,
        catalog_item_id=instance_data.catalog_item_id,
        linked_data=instance_data.linked_data,
    )

    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    return InstanceResponse.model_validate(instance)


# ============================================================================
# Item Endpoints
# ============================================================================


@router.get("/items", response_model=ItemsListResponse)
@limiter.limit("60/minute")
async def list_items(
    request: Request,
    barcode: Optional[str] = Query(None, max_length=50),
    call_number: Optional[str] = Query(None, max_length=100),
    branch: Optional[str] = Query(None, max_length=100),
    status: Optional[str] = Query(None, max_length=50),
    instance_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List and search BIBFRAME Items."""
    query = select(BibframeItem).options(selectinload(BibframeItem.instance))

    if barcode:
        query = query.where(BibframeItem.barcode == barcode)
    if call_number:
        safe_call = call_number.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(BibframeItem.call_number.ilike(f"%{safe_call}%"))
    if branch:
        query = query.where(BibframeItem.library_branch == branch)
    if status:
        query = query.where(BibframeItem.circulation_status == status)
    if instance_id:
        query = query.where(BibframeItem.instance_id == instance_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()

    return ItemsListResponse(
        items=[
            ItemListItem(
                id=it.id,
                uri=bibframe_rdf_service.get_item_uri(it),
                barcode=it.barcode,
                call_number=it.call_number,
                branch=it.library_branch,
                location=it.shelving_location,
                status=it.circulation_status,
                instance_id=it.instance_id,
                instance_title=it.instance.title if it.instance else None,
            )
            for it in items
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total else 0,
    )


@router.get("/items/{item_id}")
@limiter.limit("120/minute")
async def get_item(
    request: Request,
    item_id: int,
    accept: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Get a single BIBFRAME Item with content negotiation."""
    query = (
        select(BibframeItem)
        .where(BibframeItem.id == item_id)
        .options(
            selectinload(BibframeItem.instance),
            selectinload(BibframeItem.authority_links),
        )
    )

    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    format = get_preferred_format(accept)

    if format == "jsonld":
        jsonld = bibframe_rdf_service.item_to_jsonld(item)
        return create_linked_data_response(jsonld, format)

    elif format == "turtle":
        turtle = bibframe_rdf_service.item_to_turtle(item)
        return create_linked_data_response(turtle, format)

    return {
        "id": item.id,
        "uri": bibframe_rdf_service.get_item_uri(item),
        "instance_id": item.instance_id,
        "barcode": item.barcode,
        "call_number": item.call_number,
        "copy_number": item.copy_number,
        "shelving_location": item.shelving_location,
        "library_branch": item.library_branch,
        "collection": item.collection,
        "circulation_status": item.circulation_status,
        "is_holdable": item.is_holdable,
        "is_loanable": item.is_loanable,
        "condition": item.condition,
        "public_note": item.public_note,
        "instance": {
            "id": item.instance.id,
            "title": item.instance.title,
        }
        if item.instance
        else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_item(
    request: Request,
    item_data: ItemCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new BIBFRAME Item."""
    # Verify instance exists
    inst_result = await db.execute(
        select(BibframeInstance).where(BibframeInstance.id == item_data.instance_id)
    )
    if not inst_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instance not found")

    item = BibframeItem(
        instance_id=item_data.instance_id,
        uri=item_data.uri,
        barcode=item_data.barcode,
        accession_number=item_data.accession_number,
        copy_number=item_data.copy_number,
        call_number=item_data.call_number,
        shelving_location=item_data.shelving_location,
        sublocation=item_data.sublocation,
        library_branch=item_data.library_branch,
        collection=item_data.collection,
        circulation_status=item_data.circulation_status,
        is_holdable=item_data.is_holdable,
        is_loanable=item_data.is_loanable,
        condition=item_data.condition,
        condition_notes=item_data.condition_notes,
        acquisition_date=item_data.acquisition_date,
        acquisition_source=item_data.acquisition_source,
        acquisition_price=item_data.acquisition_price,
        fund_code=item_data.fund_code,
        electronic_locator=item_data.electronic_locator,
        access_restrictions=item_data.access_restrictions,
        public_note=item_data.public_note,
        staff_note=item_data.staff_note,
        item_copy_id=item_data.item_copy_id,
        linked_data=item_data.linked_data,
    )

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return ItemResponse.model_validate(item)


# ============================================================================
# Contributors and Subjects
# ============================================================================


@router.get("/contributors/{contributor_id}")
@limiter.limit("120/minute")
async def get_contributor(
    request: Request,
    contributor_id: int,
    accept: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Get a Contributor with content negotiation."""
    result = await db.execute(
        select(BibframeContributor)
        .where(BibframeContributor.id == contributor_id)
        .options(selectinload(BibframeContributor.authority_links))
    )
    contributor = result.scalar_one_or_none()

    if not contributor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contributor not found")

    format = get_preferred_format(accept)

    if format == "jsonld":
        jsonld = bibframe_rdf_service.contributor_to_jsonld(contributor)
        return create_linked_data_response(jsonld, format)

    return {
        "id": contributor.id,
        "uri": bibframe_rdf_service.get_contributor_uri(contributor),
        "name": contributor.name,
        "contributor_type": contributor.contributor_type,
        "given_name": contributor.given_name,
        "family_name": contributor.family_name,
        "birth_date": contributor.birth_date,
        "death_date": contributor.death_date,
        "viaf_id": contributor.viaf_id,
        "lcnaf_id": contributor.lcnaf_id,
        "wikidata_id": contributor.wikidata_id,
        "orcid": contributor.orcid,
    }


@router.post(
    "/contributors", response_model=ContributorResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("30/minute")
async def create_contributor(
    request: Request,
    data: ContributorCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new Contributor."""
    contributor = BibframeContributor(
        uri=data.uri,
        name=data.name,
        contributor_type=data.contributor_type,
        name_inverted=data.name_inverted,
        name_sort=data.name.lower(),
        given_name=data.given_name,
        family_name=data.family_name,
        birth_date=data.birth_date,
        death_date=data.death_date,
        organization_type=data.organization_type,
        place=data.place,
        alternate_names=json.dumps(data.alternate_names) if data.alternate_names else None,
        biography=data.biography,
        viaf_id=data.viaf_id,
        lcnaf_id=data.lcnaf_id,
        isni=data.isni,
        orcid=data.orcid,
        wikidata_id=data.wikidata_id,
        linked_data=data.linked_data,
    )

    db.add(contributor)
    await db.commit()
    await db.refresh(contributor)

    return ContributorResponse.model_validate(contributor)


@router.get("/subjects/{subject_id}")
@limiter.limit("120/minute")
async def get_subject(
    request: Request,
    subject_id: int,
    accept: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Get a Subject with content negotiation."""
    subject = await get_or_404(db, BibframeSubject, subject_id, "Subject not found")

    return {
        "id": subject.id,
        "uri": bibframe_rdf_service.get_subject_uri(subject),
        "label": subject.label,
        "subject_type": subject.subject_type,
        "lcsh_id": subject.lcsh_id,
        "fast_id": subject.fast_id,
        "wikidata_id": subject.wikidata_id,
    }


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_subject(
    request: Request,
    data: SubjectCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new Subject."""
    subject = BibframeSubject(
        uri=data.uri,
        label=data.label,
        label_normalized=data.label.lower(),
        subject_type=data.subject_type,
        broader_term=data.broader_term,
        narrower_terms=json.dumps(data.narrower_terms) if data.narrower_terms else None,
        related_terms=json.dumps(data.related_terms) if data.related_terms else None,
        source=data.source,
        source_id=data.source_id,
        lcsh_id=data.lcsh_id,
        fast_id=data.fast_id,
        wikidata_id=data.wikidata_id,
        scope_note=data.scope_note,
        linked_data=data.linked_data,
    )

    db.add(subject)
    await db.commit()
    await db.refresh(subject)

    return SubjectResponse.model_validate(subject)


# ============================================================================
# Conversion and Import Endpoints
# ============================================================================


@router.post("/convert/marc-to-bibframe", response_model=MarcToBibframeResponse)
@limiter.limit("10/minute")
async def convert_marc_to_bibframe(
    request: Request,
    data: MarcToBibframeRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Convert a MARC record to BIBFRAME entities.

    Accepts MARC in XML or JSON format and creates Work, Instance,
    Contributor, and Subject records.
    """
    result = None

    if data.marc_xml:
        result = marc_to_bibframe_service.convert_marc_xml(data.marc_xml)
    elif data.marc_json:
        # For JSON, we need to convert to pymarc Record first
        # This is a simplified approach
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MARC JSON not yet supported. Use MARC XML.",
        )
    elif data.catalog_item_id:
        # Convert from existing catalog item
        catalog_item = await get_or_404(
            db, CatalogItem, data.catalog_item_id, "Catalog item not found"
        )
        result = marc_to_bibframe_service.convert_catalog_item(catalog_item)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Provide marc_xml or catalog_item_id"
        )

    if not result or not result.get("work"):
        return MarcToBibframeResponse(
            warnings=result.get("warnings", []) if result else ["Conversion failed"]
        )

    # Save entities if requested
    if data.create_entities:
        work = result["work"]
        instance = result["instance"]

        db.add(work)
        await db.flush()

        if instance:
            instance.work_id = work.id
            db.add(instance)
            await db.flush()

        # Save contributors
        for contrib in result.get("contributors", []):
            db.add(contrib)
            await db.flush()

        # Save subjects
        for subj in result.get("subjects", []):
            db.add(subj)
            await db.flush()

        await db.commit()

        # Refresh to get IDs
        await db.refresh(work)
        if instance:
            await db.refresh(instance)

    return MarcToBibframeResponse(
        work=WorkResponse.model_validate(result["work"]) if result.get("work") else None,
        instance=InstanceResponse.model_validate(result["instance"])
        if result.get("instance")
        else None,
        warnings=result.get("warnings", []),
    )


@router.post("/import/loc/search", response_model=LocSearchResponse)
@limiter.limit("10/minute")
async def search_loc_bibframe(
    request: Request,
    data: LocSearchRequest,
    current_user: User = Depends(require_staff),
):
    """
    Search Library of Congress BIBFRAME data.

    Returns a list of matching records that can be imported.
    """
    result = await loc_bibframe_service.search(
        query=data.query,
        search_type=data.search_type,
        max_results=data.max_results,
    )

    return LocSearchResponse(
        results=[
            {
                "uri": r["uri"],
                "title": r["title"],
                "contributors": r["contributors"],
                "publication_info": r.get("publication_info"),
                "identifiers": r.get("identifiers", {}),
                "work_type": r.get("work_type"),
            }
            for r in result.get("results", [])
        ],
        total_results=result.get("total_results", 0),
        query=data.query,
    )


@router.post("/import/loc", response_model=LocImportResponse)
@limiter.limit("5/minute")
async def import_from_loc(
    request: Request,
    data: LocImportRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Import a BIBFRAME record from Library of Congress.

    Fetches the record from id.loc.gov and creates local
    Work, Instance, Contributor, and Subject records.
    """
    result = await loc_bibframe_service.import_work(
        uri=data.uri,
        create_instances=data.create_instance,
        link_authorities=data.link_authorities,
    )

    if not result.get("work"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("warnings", ["Import failed"])[0],
        )

    # Save to database
    work = result["work"]
    if data.catalog_item_id:
        work.catalog_item_id = data.catalog_item_id

    db.add(work)
    await db.flush()

    # Save instances
    saved_instances = []
    for instance in result.get("instances", []):
        instance.work_id = work.id
        db.add(instance)
        await db.flush()
        saved_instances.append(instance)

    # Save contributors
    for contrib in result.get("contributors", []):
        db.add(contrib)
        await db.flush()

    # Save subjects
    for subj in result.get("subjects", []):
        db.add(subj)
        await db.flush()

    # Save authority links
    for link in result.get("authority_links", []):
        link.work_id = work.id
        db.add(link)

    await db.commit()
    await db.refresh(work)

    return LocImportResponse(
        work=LocImportWorkInfo(
            id=work.id,
            uri=work.uri,
            title=work.title,
        ),
        instances=[
            LocImportInstanceInfo(id=i.id, title=i.title, isbn=i.isbn_13) for i in saved_instances
        ],
        contributors_count=len(result.get("contributors", [])),
        subjects_count=len(result.get("subjects", [])),
        warnings=result.get("warnings", []),
    )


# ============================================================================
# Schema.org and SEO Endpoints
# ============================================================================


@router.get("/schema-org/work/{work_id}")
@limiter.limit("120/minute")
async def get_work_schema_org(
    request: Request,
    work_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get Schema.org JSON-LD for a Work.

    This markup can be embedded in HTML pages for SEO.
    """
    result = await db.execute(
        select(BibframeWork)
        .where(BibframeWork.id == work_id)
        .options(
            selectinload(BibframeWork.contributors),
            selectinload(BibframeWork.subjects),
            selectinload(BibframeWork.instances),
            selectinload(BibframeWork.authority_links),
        )
    )
    work = result.scalar_one_or_none()

    if not work:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work not found")

    schema = schema_org_service.work_to_schema_org(
        work,
        instances=work.instances,
        contributors=work.contributors,
        subjects=work.subjects,
    )

    return JSONResponse(
        content=schema,
        media_type="application/ld+json",
    )


@router.get("/schema-org/instance/{instance_id}")
@limiter.limit("120/minute")
async def get_instance_schema_org(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get Schema.org JSON-LD for an Instance."""
    result = await db.execute(
        select(BibframeInstance)
        .where(BibframeInstance.id == instance_id)
        .options(
            # instance_to_schema_org reads work.contributors -- load the nested
            # hop, not just the work, or the sync call lazy-loads it and raises
            # MissingGreenlet.
            selectinload(BibframeInstance.work).selectinload(BibframeWork.contributors),
            selectinload(BibframeInstance.items),
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    schema = schema_org_service.instance_to_schema_org(
        instance,
        work=instance.work,
        items=instance.items,
    )

    return JSONResponse(
        content=schema,
        media_type="application/ld+json",
    )


@router.get("/schema-org/catalog/{catalog_item_id}")
@limiter.limit("120/minute")
async def get_catalog_item_schema_org(
    request: Request,
    catalog_item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get Schema.org JSON-LD for an existing CatalogItem.

    Provides backward compatibility for the existing catalog system.
    """
    item = await get_or_404(db, CatalogItem, catalog_item_id, "Catalog item not found")

    schema = schema_org_service.catalog_item_to_schema_org(item)

    return JSONResponse(
        content=schema,
        media_type="application/ld+json",
    )


@router.get("/schema-org/library")
@limiter.limit("60/minute")
async def get_library_schema_org(request: Request):
    """Get Schema.org JSON-LD for the library organization."""
    schema = schema_org_service.generate_library_organization_schema()
    return JSONResponse(
        content=schema,
        media_type="application/ld+json",
    )


# ============================================================================
# Bulk Export Endpoints
# ============================================================================


@router.post("/export/rdf")
@limiter.limit("5/minute")
async def export_rdf(
    request: Request,
    data: BibframeExportRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Export BIBFRAME data in RDF format.

    Supports JSON-LD and Turtle output formats.
    """
    works = []
    instances = []
    items = []

    if data.work_ids:
        result = await db.execute(
            select(BibframeWork)
            .where(BibframeWork.id.in_(data.work_ids))
            .options(
                selectinload(BibframeWork.contributors),
                selectinload(BibframeWork.subjects),
                selectinload(BibframeWork.authority_links),
            )
        )
        works = result.scalars().all()

    if data.instance_ids:
        result = await db.execute(
            select(BibframeInstance)
            .where(BibframeInstance.id.in_(data.instance_ids))
            .options(selectinload(BibframeInstance.authority_links))
        )
        instances = result.scalars().all()

    if data.item_ids:
        result = await db.execute(select(BibframeItem).where(BibframeItem.id.in_(data.item_ids)))
        items = result.scalars().all()

    output = bibframe_rdf_service.export_graph(
        works=list(works),
        instances=list(instances),
        items=list(items),
        format=data.format,
        include_authorities=data.include_authorities,
    )

    media_type = "application/ld+json" if data.format == "jsonld" else "text/turtle"

    return Response(
        content=output,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=bibframe_export.{data.format}",
        },
    )


# ============================================================================
# Authority Linking Endpoints
# ============================================================================


@router.get("/authority-links", response_model=list[AuthorityLinkResponse])
@limiter.limit("60/minute")
async def list_authority_links(
    request: Request,
    source: str | None = None,
    work_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List authority links, optionally filtered by source or work."""
    query = select(AuthorityLink)

    if source:
        query = query.where(AuthorityLink.source == source)
    if work_id:
        query = query.where(AuthorityLink.work_id == work_id)

    result = await db.execute(query.order_by(AuthorityLink.created_at.desc()))
    return result.scalars().all()


@router.post(
    "/authority-links", response_model=AuthorityLinkResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("30/minute")
async def create_authority_link(
    request: Request,
    data: AuthorityLinkCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new authority link to an external identifier."""
    link = AuthorityLink(
        source=data.source,
        authority_id=data.authority_id,
        authority_uri=data.authority_uri,
        authority_label=data.authority_label,
        link_type=data.link_type,
        confidence=data.confidence,
        work_id=data.work_id,
        instance_id=data.instance_id,
        item_id=data.item_id,
        contributor_id=data.contributor_id,
        subject_id=data.subject_id,
    )

    db.add(link)
    await db.commit()
    await db.refresh(link)

    return AuthorityLinkResponse.model_validate(link)


@router.get("/authority-links/lookup/{source}/{authority_id}")
@limiter.limit("60/minute")
async def lookup_authority(
    request: Request,
    source: str,
    authority_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Look up entities linked to an external authority.

    Returns all Works, Instances, Contributors, and Subjects
    linked to the specified authority identifier.
    """
    try:
        authority_source = AuthoritySource(source.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown authority source: {source}"
        ) from None

    result = await db.execute(
        select(AuthorityLink).where(
            AuthorityLink.source == authority_source,
            AuthorityLink.authority_id == authority_id,
        )
    )
    links = result.scalars().all()

    return {
        "source": source,
        "authority_id": authority_id,
        "links": [
            {
                "id": l.id,
                "link_type": l.link_type,
                "work_id": l.work_id,
                "instance_id": l.instance_id,
                "item_id": l.item_id,
                "contributor_id": l.contributor_id,
                "subject_id": l.subject_id,
                "verified": l.verified,
            }
            for l in links
        ],
    }
