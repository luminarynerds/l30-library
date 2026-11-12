# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.cache import (
    get_cached,
    make_cache_key,
    set_cached,
)
from ....core.database import get_db
from ....core.exceptions import InternalServerError
from ....core.error_codes import ErrorCode
from ....core.branding import branding
from ....core.pagination_config import PaginationDefaults
from ....core.rate_limit import limiter
from ....models.catalog import CatalogItem, ItemStatus, ItemType
from ....models.user import User
from ....schemas.catalog import (
    CatalogAdvancedSearchResponse,
    CatalogItemResponse,
    CatalogSimpleSearchResponse,
)
from ....services.catalog_marc_service import catalog_marc_service
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter()


@router.get("/advanced-search", response_model=dict)
async def get_advanced_search_options(
    db: AsyncSession = Depends(get_db),
):
    """
    Get available options and documentation for advanced catalog search.

    Returns supported fields, operators, and example queries.
    """
    return {
        "supported_fields": ["title", "author", "artist", "director", "subject", "isbn", "publisher", "brand", "platform"],
        "supported_operators": ["AND", "OR", "NOT"],
        "filters": {
            "item_type": "book|dvd|audiobook|magazine|digital",
            "status": "available|checked_out|on_order",
            "publication_year_min": "integer",
            "publication_year_max": "integer",
            "location": "string"
        },
        "pagination": {
            "page": "integer (minimum 1)",
            "per_page": "integer (1-100, default 20)"
        },
        "example_request": {
            "queries": [
                {"field": "title", "value": "python", "operator": "AND"},
                {"field": "author", "value": "guido", "operator": "OR"}
            ],
            "filters": {
                "item_type": "book",
                "status": "available"
            }
        }
    }


@router.get("/export/marc", response_class=Response)
@limiter.limit("10/minute")
async def export_catalog_marc_batch(
    request: Request,
    format: str = Query("binary", description="Export format: binary or marcxml"),
    item_type: ItemType | None = Query(None, description="Filter by item type"),
    status: ItemStatus | None = Query(None, description="Filter by status"),
    location: str | None = Query(None, description="Filter by location"),
    limit: int = Query(100, ge=1, le=1000, description="Max items to export"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Export catalog items as batch MARC21 records."""
    if format not in ("binary", "marcxml"):
        raise HTTPException(status_code=400, detail="Invalid format. Use 'binary' or 'marcxml'")

    base_query = (
        select(CatalogItem)
        .options(selectinload(CatalogItem.multipart_set))
        .order_by(CatalogItem.id)
    )
    if item_type:
        base_query = base_query.where(CatalogItem.item_type == item_type)
    if status:
        base_query = base_query.where(CatalogItem.status == status)
    if location:
        location_escaped = location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        base_query = base_query.where(CatalogItem.location.ilike(f"%{location_escaped}%"))

    # Check if any items exist
    count_result = await db.execute(select(func.count()).select_from(base_query.limit(limit).subquery()))
    total = count_result.scalar_one()
    if total == 0:
        raise HTTPException(status_code=404, detail="No items matched your search. Try broadening your filters or removing some criteria.")

    # Process in batches to avoid loading all items into memory at once
    batch_size = 200
    remaining = limit

    async def generate_marc_binary():
        nonlocal remaining
        offset = 0
        try:
            while remaining > 0:
                chunk_size = min(batch_size, remaining)
                result = await db.execute(base_query.offset(offset).limit(chunk_size))
                items = result.scalars().all()
                if not items:
                    break
                records = [catalog_marc_service.create_marc_record(item) for item in items]
                yield catalog_marc_service.export_marc21_batch(records)
                remaining -= len(items)
                offset += len(items)
                if len(items) < chunk_size:
                    break
        except Exception:
            logger.exception("Failed to export batch MARC")

    async def generate_marc_xml():
        nonlocal remaining
        offset = 0
        try:
            yield b'<?xml version="1.0" encoding="UTF-8"?>\n<collection xmlns="http://www.loc.gov/MARC21/slim">\n'
            while remaining > 0:
                chunk_size = min(batch_size, remaining)
                result = await db.execute(base_query.offset(offset).limit(chunk_size))
                items = result.scalars().all()
                if not items:
                    break
                for item in items:
                    record = catalog_marc_service.create_marc_record(item)
                    xml_bytes = catalog_marc_service.export_marcxml_batch([record])
                    # Strip XML declaration and collection wrapper from individual chunks
                    xml_str = xml_bytes if isinstance(xml_bytes, str) else xml_bytes.decode("utf-8")
                    # Extract just the record elements
                    import re
                    record_matches = re.findall(r'<record>.*?</record>', xml_str, re.DOTALL)
                    for match in record_matches:
                        yield (match + "\n").encode("utf-8")
                remaining -= len(items)
                offset += len(items)
                if len(items) < chunk_size:
                    break
            yield b'</collection>\n'
        except Exception:
            logger.exception("Failed to export batch MARCXML")

    try:
        if format == "binary":
            return StreamingResponse(
                generate_marc_binary(),
                media_type="application/marc",
                headers={"Content-Disposition": f"attachment; filename={branding.CARD_PREFIX}-catalog-export-{total}-records.mrc"},
            )
        else:
            return StreamingResponse(
                generate_marc_xml(),
                media_type="application/xml",
                headers={"Content-Disposition": f"attachment; filename={branding.CARD_PREFIX}-catalog-export-{total}-records.xml"},
            )
    except Exception:
        logger.exception("Failed to export batch MARC")
        raise InternalServerError(code=ErrorCode.EXTERNAL_SERVICE_ERROR) from None


@router.post("/advanced-search", response_model=CatalogAdvancedSearchResponse)
@limiter.limit("60/minute")
async def advanced_catalog_search(  # noqa: role-check -- public catalog advanced search, rate-limited
    request: Request,
    search_params: dict,
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """
    Advanced catalog search with Boolean operators and field-specific searches.

    Request body example:
    {
        "queries": [
            {"field": "title", "value": "python", "operator": "AND"},
            {"field": "author", "value": "guido", "operator": "OR"},
            {"field": "subject", "value": "programming", "operator": "AND"}
        ],
        "filters": {
            "item_type": "book",
            "status": "available",
            "publication_year_min": 2020,
            "publication_year_max": 2024,
            "location": "Adult Fiction"
        }
    }

    Supported fields: title, author, artist, director, subject, isbn, publisher, brand, platform
    Supported operators: AND, OR, NOT
    """
    from sqlalchemy import and_, or_, not_

    queries = search_params.get("queries", [])
    filters = search_params.get("filters", {})

    if not queries:
        raise HTTPException(
            status_code=400,
            detail="Please enter a search term to get started.",
        )

    cache_key = make_cache_key(
        "catalog:advanced-search",
        search_params=search_params,
        page=page,
        per_page=per_page,
    )
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result

    # Build base query — eager load relationships to prevent N+1
    # NOTE: checkouts and holds tables don't exist in current schema
    query = select(CatalogItem).options(selectinload(CatalogItem.images))
    count_query = select(func.count(CatalogItem.id))

    # Build search conditions
    search_conditions = []

    for idx, q in enumerate(queries):
        field = q.get("field")
        value = q.get("value")
        operator = q.get("operator", "AND").upper()

        if not field or not value:
            continue

        # Escape SQL ILIKE special characters
        value_escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search = f"%{value_escaped}%"

        # Map field to database column
        field_map = {
            "title": CatalogItem.title,
            "author": CatalogItem.author,
            "artist": CatalogItem.artist,
            "director": CatalogItem.director,
            "subject": CatalogItem.subjects,
            "isbn": CatalogItem.isbn,
            "publisher": CatalogItem.publisher,
            "brand": CatalogItem.brand,
            "platform": CatalogItem.platform,
        }

        if field not in field_map:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid field: {field}. Supported: {', '.join(field_map.keys())}",
            )

        field_condition = field_map[field].ilike(search)

        # Handle NOT operator
        if operator == "NOT":
            field_condition = not_(field_condition)

        search_conditions.append({"condition": field_condition, "operator": operator})

    # Combine search conditions with operators
    if search_conditions:
        combined_condition = search_conditions[0]["condition"]

        for i in range(1, len(search_conditions)):
            condition_obj = search_conditions[i]
            operator = search_conditions[i - 1]["operator"]

            if operator == "OR":
                combined_condition = or_(combined_condition, condition_obj["condition"])
            else:  # AND (default) or NOT (already handled)
                combined_condition = and_(combined_condition, condition_obj["condition"])

        query = query.where(combined_condition)
        count_query = count_query.where(combined_condition)

    # Apply filters
    if filters.get("item_type"):
        try:
            item_type = ItemType(filters["item_type"])
            query = query.where(CatalogItem.item_type == item_type)
            count_query = count_query.where(CatalogItem.item_type == item_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid item_type: {filters['item_type']}",
            ) from None

    if filters.get("status"):
        try:
            status_filter = ItemStatus(filters["status"])
            query = query.where(CatalogItem.status == status_filter)
            count_query = count_query.where(CatalogItem.status == status_filter)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {filters['status']}",
            ) from None

    if filters.get("publication_year_min"):
        year_min = int(filters["publication_year_min"])
        query = query.where(CatalogItem.publication_year >= year_min)
        count_query = count_query.where(CatalogItem.publication_year >= year_min)

    if filters.get("publication_year_max"):
        year_max = int(filters["publication_year_max"])
        query = query.where(CatalogItem.publication_year <= year_max)
        count_query = count_query.where(CatalogItem.publication_year <= year_max)

    if filters.get("location"):
        location = filters["location"]
        location_escaped = location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(CatalogItem.location.ilike(f"%{location_escaped}%"))
        count_query = count_query.where(CatalogItem.location.ilike(f"%{location_escaped}%"))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Pagination. ICU collation for locale-aware title sort across scripts.
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(CatalogItem.title.collate("und-x-icu"))

    result = await db.execute(query)
    items = result.scalars().all()

    response_data = {
        "items": [CatalogItemResponse.model_validate(item).model_dump() for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "search_params": search_params,
    }
    await set_cached(cache_key, response_data, ttl_seconds=300)
    return response_data


@router.post("/search/advanced", response_model=CatalogSimpleSearchResponse)
@limiter.limit("60/minute")
async def simple_advanced_search(  # noqa: role-check -- public catalog simple advanced search, rate-limited
    request: Request,
    search_params: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Simplified advanced catalog search endpoint.

    Request body example:
    {
        "title": "Python",
        "author": "Smith",
        "subject": "Programming",
        "isbn": "978-0-123456-78-9",
        "publisher": "O'Reilly",
        "operator": "AND",
        "exclude_subject": "Beginner",
        "item_type": "book",
        "status": "available",
        "year_min": 2020,
        "year_max": 2024,
        "location": "Main Library",
        "page": 1,
        "per_page": 20
    }

    All fields are optional except at least one search field should be provided.
    """
    from ....services.catalog_search_service import catalog_search_service

    # Extract search parameters
    title = search_params.get("title")
    author = search_params.get("author")
    subject = search_params.get("subject")
    isbn = search_params.get("isbn")
    publisher = search_params.get("publisher")
    operator = search_params.get("operator", "AND")
    exclude_subject = search_params.get("exclude_subject")
    item_type_str = search_params.get("item_type")
    status_str = search_params.get("status")
    year_min = search_params.get("year_min")
    year_max = search_params.get("year_max")
    location = search_params.get("location")
    page = search_params.get("page", 1)
    per_page = search_params.get("per_page", 20)

    # Convert string to enums if provided
    item_type = None
    if item_type_str:
        try:
            item_type = ItemType(item_type_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid item_type: {item_type_str}",
            ) from None

    item_status = None
    if status_str:
        try:
            item_status = ItemStatus(status_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status_str}",
            ) from None

    # Perform search using the service
    items, total = await catalog_search_service.advanced_search_with_count(
        db=db,
        title=title,
        author=author,
        subject=subject,
        isbn=isbn,
        publisher=publisher,
        operator=operator,
        exclude_subject=exclude_subject,
        item_type=item_type,
        status=item_status,
        year_min=year_min,
        year_max=year_max,
        location=location,
        page=page,
        per_page=per_page,
    )

    return {
        "results": [CatalogItemResponse.model_validate(item).model_dump() for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total > 0 else 0,
    }


@router.get("/{item_id}/marc", response_class=Response)
@limiter.limit("30/minute")
async def export_item_marc(
    request: Request,
    item_id: int,
    format: str = Query("binary", description="Export format: binary, marcxml, or dc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Export a single catalog item as MARC21 record.

    Staff-only endpoint for exporting catalog records for ILS integration.

    Formats:
    - binary: MARC21 binary format (.mrc)
    - marcxml: MARCXML format
    - dc: Dublin Core XML format
    """
    result = await db.execute(
        select(CatalogItem)
        .options(selectinload(CatalogItem.multipart_set))
        .where(CatalogItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")

    try:
        if format == "binary":
            record = catalog_marc_service.create_marc_record(item)
            marc_data = catalog_marc_service.export_marc21(record)
            return Response(
                content=marc_data,
                media_type="application/marc",
                headers={
                    "Content-Disposition": f"attachment; filename={branding.CARD_PREFIX}-CAT-{item.id:08d}.mrc"
                },
            )
        elif format == "marcxml":
            record = catalog_marc_service.create_marc_record(item)
            marc_xml = catalog_marc_service.export_marcxml(record)
            return Response(
                content=marc_xml,
                media_type="application/xml",
                headers={
                    "Content-Disposition": f"attachment; filename={branding.CARD_PREFIX}-CAT-{item.id:08d}.xml"
                },
            )
        elif format == "dc":
            dc_xml = catalog_marc_service.export_dublin_core(item)
            return Response(
                content=dc_xml,
                media_type="application/xml",
                headers={
                    "Content-Disposition": f"attachment; filename={branding.CARD_PREFIX}-CAT-{item.id:08d}-dc.xml"
                },
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid format. Use 'binary', 'marcxml', or 'dc'",
            )
    except Exception:
        logger.exception(f"Failed to export MARC for item {item_id}")
        raise InternalServerError(code=ErrorCode.EXTERNAL_SERVICE_ERROR) from None
